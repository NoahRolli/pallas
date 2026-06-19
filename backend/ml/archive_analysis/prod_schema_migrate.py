"""
Phase 2/4 — Schema-Migration fuer den produktiven semantischen Archiv-Strang.

Erweitert die echte `documents`-Tabelle um die Topic-/Cluster-Spalten, legt
`archive_clusters` an und stellt `pipeline_runs` bereit (Audit-Log fuer log_run).
Phase 4 ergaenzt Layout-Koordinaten (proj_x/proj_y auf documents, hub_x/hub_y
auf archive_clusters) fuer die precompute-Variante der Ordner<->Semantisch-Ansicht.
Idempotent: mehrfaches Ausfuehren ist sicher (fehlende Spalten/Tabellen werden
ergaenzt, vorhandene unangetastet). SQLite kennt kein "ADD COLUMN IF NOT EXISTS"
-> Abgleich via PRAGMA table_info.

Aufruf:
    python3 -m backend.ml.archive_analysis.prod_schema_migrate --db data/pallas-snapshot.db
    python3 -m backend.ml.archive_analysis.prod_schema_migrate --db /data/pallas.db    (im Container)
"""
import argparse
import sqlite3

# Neue Spalten auf `documents` -- Typen 1:1 aus ml_phase1.db
DOC_COLUMNS = {
    "topic_summary":       "TEXT",
    "topic_embedding":     "BLOB",
    "topic_summary_model": "TEXT",
    "topic_summary_at":    "TIMESTAMP",
    "cluster_id":          "INTEGER",
    "silhouette":          "REAL",
    "nearest_cluster_id":  "INTEGER",
    # Phase 4 -- 2D-Layout-Koordinaten (precompute, read-only im Frontend)
    "proj_x":              "REAL",
    "proj_y":              "REAL",
}

# Phase-4-Layout-Koordinaten der Cluster-Hubs (auf `archive_clusters`).
# Eigener ALTER-Pfad noetig, weil die Tabelle in Prod schon existiert -> die
# CREATE-TABLE-DDL unten greift dort nicht mehr.
CLUSTER_COLUMNS = {
    "hub_x": "REAL",
    "hub_y": "REAL",
}

# Cluster-Metadaten (entspricht `clusters` aus ml_phase1.db; hier `archive_clusters`
# zur Abgrenzung von concept_clusters / metis_clusters)
ARCHIVE_CLUSTERS_DDL = """
CREATE TABLE IF NOT EXISTS archive_clusters (
    cluster_id      INTEGER PRIMARY KEY,
    label           TEXT,
    size            INTEGER,
    sample_size     INTEGER,
    label_model     TEXT,
    labeled_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    mean_silhouette REAL,
    hub_x           REAL,
    hub_y           REAL
)
"""

# Audit-Log -- in Prod bislang nicht vorhanden (lebte nur in ml_phase1.db).
PIPELINE_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    step        TEXT NOT NULL,
    params_json TEXT,
    result_json TEXT,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def existing_columns(con, table):
    # r[1] = Spaltenname; leeres Set, wenn Tabelle nicht existiert
    return {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}


def add_missing(con, table, columns):
    # Fuegt fehlende Spalten per ALTER TABLE hinzu, ueberspringt vorhandene.
    have = existing_columns(con, table)
    added = []
    for col, ctype in columns.items():
        if col not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {ctype}")
            added.append(col)
    return added


def migrate(db_path):
    con = sqlite3.connect(db_path)
    try:
        if not existing_columns(con, "documents"):
            raise SystemExit(f"FEHLER: Tabelle 'documents' nicht gefunden in {db_path}")

        # documents-Spalten zuerst (Tabelle existiert garantiert)
        added_docs = add_missing(con, "documents", DOC_COLUMNS)

        # archive_clusters anlegen, falls fehlend -- dann fehlende Spalten nachziehen
        # (greift, wenn die Tabelle aus einem Lauf vor Phase 4 ohne hub_x/hub_y stammt)
        con.execute(ARCHIVE_CLUSTERS_DDL)
        added_clusters = add_missing(con, "archive_clusters", CLUSTER_COLUMNS)

        con.execute(PIPELINE_RUNS_DDL)
        con.execute("CREATE INDEX IF NOT EXISTS idx_documents_cluster ON documents(cluster_id)")
        con.commit()

        # Verifikation
        docs_after = existing_columns(con, "documents")
        clusters_after = existing_columns(con, "archive_clusters")
        missing_docs = [c for c in DOC_COLUMNS if c not in docs_after]
        missing_clusters = [c for c in CLUSTER_COLUMNS if c not in clusters_after]
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        print(f"DB: {db_path}")
        print(f"Neu hinzugefuegte documents-Spalten:        {added_docs or '(keine -- bereits vorhanden)'}")
        print(f"Neu hinzugefuegte archive_clusters-Spalten: {added_clusters or '(keine -- bereits vorhanden)'}")
        print(f"Alle documents-Spalten vorhanden:        {not missing_docs}"
              + (f"  FEHLEN: {missing_docs}" if missing_docs else ""))
        print(f"Alle archive_clusters-Spalten vorhanden: {not missing_clusters}"
              + (f"  FEHLEN: {missing_clusters}" if missing_clusters else ""))
        print(f"pipeline_runs-Tabelle vorhanden:         {'pipeline_runs' in tables}")
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Phase-2/4 Prod-Schema-Migration (idempotent)")
    ap.add_argument("--db", required=True, help="Pfad zur SQLite-DB (Snapshot oder Prod)")
    migrate(ap.parse_args().db)


if __name__ == "__main__":
    main()

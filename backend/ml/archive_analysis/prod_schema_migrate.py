"""
Phase 2 — Schema-Migration fuer den produktiven semantischen Archiv-Strang.

Erweitert die echte `documents`-Tabelle um die Topic-/Cluster-Spalten, legt
`archive_clusters` an und stellt `pipeline_runs` bereit (Audit-Log fuer log_run).
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
    mean_silhouette REAL
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


def migrate(db_path):
    con = sqlite3.connect(db_path)
    try:
        have = existing_columns(con, "documents")
        if not have:
            raise SystemExit(f"FEHLER: Tabelle 'documents' nicht gefunden in {db_path}")

        added = []
        for col, ctype in DOC_COLUMNS.items():
            if col not in have:
                con.execute(f"ALTER TABLE documents ADD COLUMN {col} {ctype}")
                added.append(col)

        con.execute(ARCHIVE_CLUSTERS_DDL)
        con.execute(PIPELINE_RUNS_DDL)
        con.execute("CREATE INDEX IF NOT EXISTS idx_documents_cluster ON documents(cluster_id)")
        con.commit()

        # Verifikation
        have_after = existing_columns(con, "documents")
        missing = [c for c in DOC_COLUMNS if c not in have_after]
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        print(f"DB: {db_path}")
        print(f"Neu hinzugefuegte documents-Spalten: {added or '(keine -- bereits vorhanden)'}")
        print(f"Alle 7 Topic-/Cluster-Spalten vorhanden: {not missing}"
              + (f"  FEHLEN: {missing}" if missing else ""))
        print(f"archive_clusters-Tabelle vorhanden: {'archive_clusters' in tables}")
        print(f"pipeline_runs-Tabelle vorhanden:    {'pipeline_runs' in tables}")
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Phase-2 Prod-Schema-Migration (idempotent)")
    ap.add_argument("--db", required=True, help="Pfad zur SQLite-DB (Snapshot oder Prod)")
    migrate(ap.parse_args().db)


if __name__ == "__main__":
    main()

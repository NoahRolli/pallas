"""Pallas ML Registry — Phase 1.

Verwaltet die separate ml_phase1.db (Embeddings, Cluster, Evaluations-
Resultate). Pallas-Live-DB wird read-only attached, niemals beschrieben.

Begruendung fuer separate DB:
- ML-Output ist abgeleitet aus pallas.db, nicht Quelldaten
- Modell-Versionierung per Datei statt Tabellen-Suffix
- Re-Runs sind 'rm ml_phase1.db', nicht Migrationsskript
- Konsistent mit dem journal.db-Pattern (separater Lebenszyklus)

Standard-Pfade:
    lokal:  data/pallas-snapshot.db + data/ml_phase1.db
    olymp:  <PALLAS_DATA_DIR>/pallas.db
            + <PALLAS_DATA_DIR>/ml_phase1.db
"""

import sqlite3
from pathlib import Path
from typing import Optional


# Phase-1-Schema. Wird in init_schema() angelegt.
SCHEMA_SQL = """
-- Ein Eintrag pro Dokument im sauberen Arbeitssatz (Schritt 1: Filter).
-- Embedding wird in Schritt 3 gefuellt, cluster_id in Schritt 4.
CREATE TABLE IF NOT EXISTS archive_documents (
    document_id      INTEGER PRIMARY KEY,
    raw_text_len     INTEGER NOT NULL,
    display_name     TEXT,
    folder_id        INTEGER,
    is_pallas_anchor INTEGER NOT NULL DEFAULT 0,
    needs_chunking   INTEGER NOT NULL DEFAULT 0,
    embedding        BLOB,
    cluster_id       INTEGER,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_archive_documents_pallas_anchor
    ON archive_documents(is_pallas_anchor);

CREATE INDEX IF NOT EXISTS idx_archive_documents_cluster
    ON archive_documents(cluster_id);

-- Chunks pro Dokument fuer Schritt 2.
-- Speichert NUR Positionen (char_start/char_end), nicht den Text selbst.
-- Der Text bleibt in pallas.documents.raw_text und wird von Schritt 3
-- via substr() on-demand gelesen. Spart Speicher, vermeidet Duplikate.
-- Auch kurze Dokumente (< chunk_size) bekommen genau einen Chunk-Eintrag
-- (char_start=0, char_end=raw_text_len) -- uniform fuer einfacheren Code.
CREATE TABLE IF NOT EXISTS archive_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id     INTEGER NOT NULL,
    chunk_idx       INTEGER NOT NULL,
    char_start      INTEGER NOT NULL,
    char_end        INTEGER NOT NULL,
    chunk_text_len  INTEGER NOT NULL,
    embedding       BLOB,
    UNIQUE(document_id, chunk_idx)
);

CREATE INDEX IF NOT EXISTS idx_archive_chunks_document
    ON archive_chunks(document_id);

CREATE INDEX IF NOT EXISTS idx_archive_chunks_no_embedding
    ON archive_chunks(document_id) WHERE embedding IS NULL;

-- Metadaten pro Pipeline-Lauf: welche Filter-Schwelle, welches
-- Embedding-Modell, wieviele Docs etc. Schritt 1 schreibt den
-- ersten Eintrag, spaetere Schritte ergaenzen.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    step            TEXT NOT NULL,
    params_json     TEXT,
    result_json     TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def open_ml_db(
    ml_path: str,
    pallas_ro_path: Optional[str] = None,
) -> sqlite3.Connection:
    """Oeffnet ml_phase1.db read-write, attached pallas.db read-only.

    Pallas wird unter dem Alias 'pallas' adressierbar, z.B.:
        SELECT d.display_name
        FROM archive_documents a
        JOIN pallas.documents d ON d.id = a.document_id

    pallas_ro_path=None laesst den ATTACH weg (fuer Tests / pure
    ML-DB-Inspektion ohne Live-Daten).
    """
    ml = Path(ml_path)
    ml.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(ml)
    con.execute("PRAGMA foreign_keys = OFF")  # cross-DB FK macht SQLite eh nicht

    if pallas_ro_path is not None:
        p = Path(pallas_ro_path)
        if not p.exists():
            raise FileNotFoundError(f"Pallas-DB nicht gefunden: {p}")
        # URI-Mode 'ro' schuetzt die Live-DB hart vor Schreibzugriff.
        uri = f"file:{p.resolve()}?mode=ro"
        con.execute(f"ATTACH DATABASE '{uri}' AS pallas")

    return con


def init_schema(con: sqlite3.Connection) -> None:
    """Legt die Phase-1-Tabellen an. Idempotent (IF NOT EXISTS)."""
    con.executescript(SCHEMA_SQL)
    con.commit()


def log_run(
    con: sqlite3.Connection,
    step: str,
    params: dict,
    result: dict,
) -> int:
    """Schreibt einen Pipeline-Run-Eintrag (Schritt-Audit-Log).

    Gibt die neue run-id zurueck (fuer Verkettung in spaeteren Schritten).
    """
    import json
    cur = con.execute(
        "INSERT INTO pipeline_runs (step, params_json, result_json) "
        "VALUES (?, ?, ?)",
        (step, json.dumps(params, ensure_ascii=False),
         json.dumps(result, ensure_ascii=False)),
    )
    con.commit()
    return cur.lastrowid


def open_prod_db(db_path: str) -> sqlite3.Connection:
    """Oeffnet die Prod-pallas.db read-write fuer den produktiven Archiv-Strang.

    Anders als open_ml_db gibt es KEIN ATTACH: in Prod liegen Rohtext
    (documents.raw_text) und die berechneten Topic-/Cluster-Spalten in
    derselben Tabelle (documents), co-located -- kein Zwei-DB-Tanz noetig.
    """
    p = Path(db_path)
    if not p.exists():
        raise FileNotFoundError(f"DB nicht gefunden: {p}")
    con = sqlite3.connect(p)
    con.execute("PRAGMA foreign_keys = OFF")
    return con

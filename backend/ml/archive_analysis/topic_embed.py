"""Schritt 4.6 — Embedding der Topic-Summaries (prod-nativ).

Embedded die in Schritt 4.5 erzeugten topic_summary-Texte mit bge-m3 via
Ollama und schreibt 1024-dim float32-Vektoren in documents.topic_embedding.
Dieser Vektor ist der Clustering-Input fuer Schritt 4.

Prod-nativ: arbeitet direkt auf documents (PK id), single --db, kein ATTACH.
Der Mini-Doc-Filter muss hier nicht wiederholt werden -- er propagiert ueber
topic_summary: nur Docs mit Summary werden embedded, und Summaries gibt es
nur fuer Docs >= MIN_CHARS (siehe topic_extract). Resume via
WHERE topic_embedding IS NULL.

Aufruf:
  python3 -m backend.ml.archive_analysis.topic_embed --db data/pallas-snapshot.db --limit 10
  python3 -m backend.ml.archive_analysis.topic_embed --db /data/pallas.db --batch-size 16
"""
import argparse
import json
import struct
import sys
import time
import urllib.request

from backend.ml.registry import open_prod_db, log_run

OLLAMA_URL = "http://127.0.0.1:11434/api/embed"
MODEL = "bge-m3"
DIM = 1024


def embed_batch(texts):
    """Liste von Texten -> Liste von 1024-float-Vektoren via Ollama."""
    payload = {"model": MODEL, "input": texts}
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    vecs = body.get("embeddings")
    if not vecs or len(vecs) != len(texts):
        raise RuntimeError(
            f"Ollama lieferte {len(vecs) if vecs else 0} Vektoren "
            f"fuer {len(texts)} Inputs"
        )
    return vecs


def pack(vec):
    """1024 floats -> 4096-Byte BLOB (little-endian float32)."""
    if len(vec) != DIM:
        raise RuntimeError(f"Vektor hat {len(vec)} dims, erwartet {DIM}")
    return struct.pack(f"<{DIM}f", *vec)


def fetch_pending(con, limit):
    """Docs mit Summary aber ohne topic_embedding (Resume-faehig)."""
    q = (
        "SELECT id, topic_summary FROM documents "
        "WHERE topic_embedding IS NULL "
        "AND topic_summary IS NOT NULL AND topic_summary != ''"
    )
    if limit:
        q += f" LIMIT {int(limit)}"
    return con.execute(q).fetchall()


def run(con, batch_size, limit):
    rows = fetch_pending(con, limit)
    total = len(rows)
    print(f"Topic-Embedding: {total} Docs offen, Modell={MODEL}, "
          f"Batch={batch_size}")
    if total == 0:
        print("Nichts zu tun.")
        return
    done, t0 = 0, time.time()
    for start in range(0, total, batch_size):
        batch = rows[start:start + batch_size]
        ids = [r[0] for r in batch]
        texts = [r[1] for r in batch]
        vecs = embed_batch(texts)
        for doc_id, vec in zip(ids, vecs):
            con.execute(
                "UPDATE documents SET topic_embedding=? WHERE id=?",
                (pack(vec), doc_id),
            )
        con.commit()
        done += len(batch)
        rate = done / (time.time() - t0)
        eta = (total - done) / rate if rate else 0
        print(f"  {done}/{total}  {rate:.2f} doc/s  eta={eta/60:.1f}min", flush=True)
    log_run(con, "topic_embed", {"model": MODEL, "batch_size": batch_size},
            {"embedded": done, "total": total})
    print("Fertig.")


def main():
    p = argparse.ArgumentParser(description="Schritt 4.6 Topic-Embedding (prod-nativ)")
    p.add_argument("--db", required=True, help="Pfad zur pallas.db (Snapshot oder Prod)")
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    con = open_prod_db(args.db)
    try:
        run(con, args.batch_size, args.limit)
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())

"""Schritt 4.5 — LLM-Topic-Extraktion (prod-nativ).

Erzeugt pro Dokument eine themenfokussierte englische Kurz-Zusammenfassung
via Ollama (gemma4:e2b). Diese Summary ersetzt den Rohtext als Clustering-
Input und eliminiert das Chat-Format-Signal, das bge-m3 auf Rohtexten
dominiert (siehe Befund 1-6, Chat 80).

Prod-nativ: arbeitet direkt auf der pallas.db `documents`-Tabelle
(PK `id`, Rohtext `raw_text` co-located) -- kein ATTACH, kein Zwei-DB-Tanz.
Der Mini-Doc-Filter (MIN_CHARS=500, in Schritt 0 validiert) sitzt am Eingang;
Docs darunter bekommen nie eine Summary und fallen damit aus allen
Folge-Schritten heraus (die auf topic_summary/topic_embedding keyen).

Voraussetzung: prod_schema_migrate hat die Topic-Spalten angelegt.

Modi:
  --sample N : N Docs (laengste + zufaellig), Summaries werden nur ausgegeben,
               KEIN DB-Write. Fuer manuelle Qualitaetspruefung.
  (default)  : Full-Run mit Resume (WHERE topic_summary IS NULL), schreibt
               topic_summary + Metadaten nach documents.

Aufruf:
  python3 -m backend.ml.archive_analysis.topic_extract --db data/pallas-snapshot.db --sample 6
  python3 -m backend.ml.archive_analysis.topic_extract --db /data/pallas.db            (Full-Run)
"""
import argparse
import json
import os
import random
import sys
import time
import urllib.request
from datetime import datetime, timezone

from backend.ml.registry import open_prod_db, log_run

OLLAMA_URL = os.environ.get("OLLAMA_PIPELINE_URL", "http://127.0.0.1:11434/api/generate")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:26b")

MIN_CHARS = 500  # Schritt-1-Filter (in Schritt 0 validiert); identisch zu preprocess.py

PROMPT = (
    "Identify the subject matter of the document below. "
    "Respond with one or two dense sentences in English that name the topic "
    "and its domain or field. Do not describe the conversation or its "
    "participants. Do not list steps. State only what it is about.\n\n"
    "DOCUMENT:\n{body}\n\nTOPIC:"
)

HEAD_CHARS = 8000
TAIL_CHARS = 2000
MIN_SUMMARY_CHARS = 50
UNSURE_MARKERS = ("unclear", "cannot determine", "not enough", "unsure")

REQUIRED_COLUMNS = ("topic_summary", "topic_summary_model", "topic_summary_at")


def truncate(text):
    """Lange Docs auf Kopf+Schwanz kuerzen (gemma4:e2b Context-Limit)."""
    if len(text) <= HEAD_CHARS + TAIL_CHARS:
        return text
    return text[:HEAD_CHARS] + "\n...\n" + text[-TAIL_CHARS:]


def clean(summary):
    """Fuehrendes Label und Whitespace entfernen."""
    s = summary.strip()
    if s.upper().startswith("TOPIC:"):
        s = s[6:].strip()
    return s


def summarize(model, text):
    """Einzelnen Topic-Summary via Ollama generieren. temperature=0."""
    payload = {
        "model": model,
        "prompt": PROMPT.format(body=truncate(text)),
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return clean(body.get("response", ""))


def is_degenerate(summary):
    """Summary unbrauchbar -> Fallback auf display_name."""
    if len(summary) < MIN_SUMMARY_CHARS:
        return True
    low = summary.lower()
    return any(m in low for m in UNSURE_MARKERS)


def require_columns(con):
    """Bricht ab, wenn die Migration nicht gelaufen ist."""
    cols = {r[1] for r in con.execute("PRAGMA table_info(documents)")}
    missing = [c for c in REQUIRED_COLUMNS if c not in cols]
    if missing:
        raise SystemExit(
            f"FEHLER: Spalten {missing} fehlen auf 'documents'. Erst Migration laufen lassen:\n"
            "  python3 -m backend.ml.archive_analysis.prod_schema_migrate --db <DB>"
        )


def fetch_doc(con, doc_id):
    """raw_text + display_name aus documents (co-located, kein ATTACH)."""
    row = con.execute(
        "SELECT raw_text, display_name FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()
    return (row[0] or "", row[1] or "") if row else ("", "")


def stratified_ids(con, n):
    """QA-Sample: laengste Docs (Truncation-Test) + zufaelliger Rest, >= MIN_CHARS."""
    rows = con.execute(
        "SELECT id, length(raw_text) AS n FROM documents "
        "WHERE raw_text IS NOT NULL AND length(raw_text) >= ?",
        (MIN_CHARS,),
    ).fetchall()
    by_len = sorted(rows, key=lambda r: r[1] or 0, reverse=True)
    longs = [r[0] for r in by_len[: max(1, n // 4)]]
    longset = set(longs)
    rest = [r[0] for r in rows if r[0] not in longset]
    random.shuffle(rest)
    return (longs + rest)[:n]


def run_sample(con, model, n):
    """Summaries generieren und ausgeben, ohne DB-Write."""
    ids = stratified_ids(con, n)
    print(f"Sample: {len(ids)} Docs, Modell={model}\n")
    for doc_id in ids:
        raw, name = fetch_doc(con, doc_id)
        summary = summarize(model, raw) if raw.strip() else ""
        fb = is_degenerate(summary)
        print(f"[{doc_id}] len={len(raw)}  display_name={name!r}")
        print(f"    summary : {summary!r}")
        print(f"    fallback: {'JA -> display_name' if fb else 'nein'}\n")


def run_full(con, model, limit):
    """Full-Run mit Resume und Per-Doc-Commit."""
    require_columns(con)
    q = ("SELECT id FROM documents "
         "WHERE topic_summary IS NULL AND length(raw_text) >= ?")
    params = [MIN_CHARS]
    if limit:
        q += " LIMIT ?"
        params.append(int(limit))
    rows = con.execute(q, params).fetchall()
    total = len(rows)
    print(f"Full-Run: {total} Docs offen (>= {MIN_CHARS} Zeichen), Modell={model}")
    done, t0 = 0, time.time()
    for (doc_id,) in rows:
        raw, name = fetch_doc(con, doc_id)
        summary = summarize(model, raw) if raw.strip() else ""
        if is_degenerate(summary):
            summary = name or summary
        con.execute(
            "UPDATE documents SET topic_summary=?, topic_summary_model=?, "
            "topic_summary_at=? WHERE id=?",
            (summary, model, datetime.now(timezone.utc).isoformat(), doc_id),
        )
        con.commit()
        done += 1
        if done % 25 == 0 or done == total:
            rate = done / (time.time() - t0)
            eta = (total - done) / rate if rate else 0
            print(f"  {done}/{total}  {rate:.2f} doc/s  eta={eta/60:.1f}min", flush=True)
    log_run(con, "topic_extract", {"model": model, "min_chars": MIN_CHARS},
            {"summarized": done, "total": total})
    print("Fertig.")


def main():
    p = argparse.ArgumentParser(description="Schritt 4.5 Topic-Extraktion (prod-nativ)")
    p.add_argument("--db", required=True, help="Pfad zur pallas.db (Snapshot oder Prod)")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--sample", type=int, default=0)
    p.add_argument("--limit", type=int, default=0)
    args = p.parse_args()

    con = open_prod_db(args.db)
    try:
        if args.sample:
            run_sample(con, args.model, args.sample)
        else:
            run_full(con, args.model, args.limit)
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())

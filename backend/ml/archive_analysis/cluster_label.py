"""Schritt 5 — Cluster-Labeling (prod-nativ).

Vergibt jedem Cluster aus Schritt 4 ein kurzes englisches Themen-Label (2-4 Woerter).
Pro Cluster wird eine Stichprobe der topic_summary-Saetze an gemma4:e2b gegeben.
Labels landen in archive_clusters (eine Zeile pro Cluster) -- der Ort fuer
per-Cluster-Metriken (mean_silhouette folgt in Schritt 6).

Prod-nativ: documents (PK id) + archive_clusters, single --db, kein ATTACH.
Schema wird von prod_schema_migrate angelegt; dieser Schritt schreibt nur Daten.
"""
import argparse
import json
import os
import sys
import urllib.request

from backend.ml.registry import open_prod_db, log_run

DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "gemma4:26b")
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_PIPELINE_URL", "http://127.0.0.1:11434/api/generate")
SAMPLE_SIZE = 25

PROMPT = (
    "Below are short topic summaries of documents that were grouped into one "
    "cluster because they share a subject. Ignore boilerplate phrasing such as "
    "\"The document discusses...\" or \"This falls under the domain of...\". "
    "Identify the single shared subject and respond with ONLY a 2-4 word topic "
    "label in English. No punctuation, no quotes, no explanation.\n\n"
    "SUMMARIES:\n{summaries}\n\nLABEL:"
)


def require_clusters_table(con):
    """Bricht ab, wenn die Migration nicht gelaufen ist."""
    t = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='archive_clusters'"
    ).fetchone()
    if not t:
        raise SystemExit(
            "FEHLER: Tabelle 'archive_clusters' fehlt. Erst Migration laufen lassen:\n"
            "  python3 -m backend.ml.archive_analysis.prod_schema_migrate --db <DB>"
        )


def clean_label(raw):
    """Fuehrendes Label, Anfuehrungszeichen und Markdown entfernen."""
    s = (raw or "").strip()
    s = s.split("\n")[0].strip()
    for pre in ("LABEL:", "TOPIC:", "THEME:", "SUBJECT:", "CLUSTER:"):
        if s.upper().startswith(pre):
            s = s[len(pre):].strip()
    return s.strip(" \"'`*.-")


def label_cluster(model, url, summaries):
    """Ein Label fuer eine Cluster-Stichprobe via Ollama. temperature=0."""
    bullet = "\n".join(f"- {s.strip()}" for s in summaries)
    payload = {
        "model": model,
        "prompt": PROMPT.format(summaries=bullet),
        "stream": False,
        "think": False,
        "options": {"temperature": 0},
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return clean_label(body.get("response", ""))


def fetch_clusters(con, limit):
    """Cluster-IDs + Groessen, groesste zuerst."""
    rows = con.execute(
        "SELECT cluster_id, COUNT(*) AS n FROM documents "
        "WHERE cluster_id IS NOT NULL GROUP BY cluster_id ORDER BY n DESC"
    ).fetchall()
    return rows[:limit] if limit else rows


def fetch_summaries(con, cluster_id, sample_size):
    rows = con.execute(
        "SELECT topic_summary FROM documents "
        "WHERE cluster_id = ? AND topic_summary IS NOT NULL "
        "ORDER BY id LIMIT ?",
        (cluster_id, sample_size),
    ).fetchall()
    return [r[0] for r in rows]


def already_labeled(con, cluster_id):
    return con.execute(
        "SELECT 1 FROM archive_clusters WHERE cluster_id = ? AND label IS NOT NULL",
        (cluster_id,),
    ).fetchone() is not None


def main():
    ap = argparse.ArgumentParser(description="Schritt 5 — Cluster-Labeling (prod-nativ)")
    ap.add_argument("--db", required=True, help="Pfad zur pallas.db (Snapshot oder Prod)")
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    ap.add_argument("--limit", type=int, default=0,
                    help="nur die N groessten Cluster (0 = alle)")
    ap.add_argument("--dry-run", action="store_true",
                    help="nur ausgeben, nichts schreiben")
    ap.add_argument("--force", action="store_true",
                    help="bereits gelabelte Cluster neu labeln")
    args = ap.parse_args()

    con = open_prod_db(args.db)
    try:
        if not args.dry_run:
            require_clusters_table(con)

        clusters = fetch_clusters(con, args.limit)
        mode = "DRY-RUN" if args.dry_run else "WRITE"
        print(f"[{mode}] {len(clusters)} Cluster, sample-size={args.sample_size}, "
              f"model={args.model}")

        labeled = 0
        for cluster_id, size in clusters:
            if not args.dry_run and not args.force and already_labeled(con, cluster_id):
                print(f"[skip] {cluster_id} (n={size}) bereits gelabelt")
                continue
            summaries = fetch_summaries(con, cluster_id, args.sample_size)
            if not summaries:
                print(f"[warn] {cluster_id} (n={size}) ohne Summaries — uebersprungen")
                continue
            try:
                label = label_cluster(args.model, args.ollama_url, summaries)
            except Exception as exc:  # noqa: BLE001
                print(f"[err]  {cluster_id}: {exc}", file=sys.stderr)
                continue
            print(f"[{cluster_id:>3}] n={size:<3} sample={len(summaries):<2} -> {label!r}")
            if not args.dry_run:
                con.execute(
                    "INSERT INTO archive_clusters "
                    "(cluster_id, label, size, sample_size, label_model) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(cluster_id) DO UPDATE SET "
                    "label=excluded.label, size=excluded.size, "
                    "sample_size=excluded.sample_size, "
                    "label_model=excluded.label_model, labeled_at=CURRENT_TIMESTAMP",
                    (cluster_id, label, size, len(summaries), args.model),
                )
                con.commit()
                labeled += 1

        if not args.dry_run:
            log_run(con, "step5_cluster_label",
                    {"sample_size": args.sample_size, "model": args.model,
                     "limit": args.limit},
                    {"clusters_labeled": labeled})
        print("Dry-run fertig." if args.dry_run else f"Fertig. {labeled} Cluster gelabelt.")
    finally:
        con.close()


if __name__ == "__main__":
    main()

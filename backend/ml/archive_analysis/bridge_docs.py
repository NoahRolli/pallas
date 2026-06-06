"""Schritt 6 — Fehleranalyse / thematische Bruecken (prod-nativ).

Berechnet pro Dokument die Cosine-Silhouette s(i) auf denselben mean-centered
topic_embeddings wie das Clustering (Schritt 4). Dokumente mit niedrigem/negativem
s(i) liegen zwischen Clustern = die thematischen Bruecken-Chats.

Schreibt s(i) + naechsten Fremd-Cluster pro Doc nach documents und den
Cluster-Mittelwert nach archive_clusters. Prod-nativ: documents (PK id),
single --db, kein ATTACH. Schema gehoert der Migration; hier nur Daten.
"""
import argparse

import numpy as np

from backend.ml.registry import open_prod_db, log_run


def require_schema(con):
    """Bricht ab, wenn die Migration nicht gelaufen ist."""
    dcols = {r[1] for r in con.execute("PRAGMA table_info(documents)")}
    missing = [c for c in ("silhouette", "nearest_cluster_id") if c not in dcols]
    has_clusters = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='archive_clusters'"
    ).fetchone()
    if missing or not has_clusters:
        raise SystemExit(
            "FEHLER: Schema unvollstaendig (Migration nicht gelaufen?):\n"
            "  python3 -m backend.ml.archive_analysis.prod_schema_migrate --db <DB>"
        )


def load(con):
    rows = con.execute(
        "SELECT id, cluster_id, topic_embedding, display_name, topic_summary "
        "FROM documents "
        "WHERE cluster_id IS NOT NULL AND topic_embedding IS NOT NULL "
        "ORDER BY id"
    ).fetchall()
    doc_ids = np.array([r[0] for r in rows])
    labels = np.array([r[1] for r in rows])
    X = np.array([np.frombuffer(r[2], dtype=np.float32) for r in rows], dtype=np.float64)
    names = [r[3] for r in rows]
    summaries = [r[4] for r in rows]
    return doc_ids, labels, X, names, summaries


def cosine_distance_matrix(X):
    """Mean-Centering (wie Schritt 4) + Cosine-Distanz."""
    Xc = X - X.mean(axis=0)
    norms = np.linalg.norm(Xc, axis=1, keepdims=True)
    Xn = Xc / np.clip(norms, 1e-12, None)
    D = 1.0 - (Xn @ Xn.T)
    np.fill_diagonal(D, 0.0)
    return D


def per_doc_silhouette(D, labels):
    """Wie silhouette_cosine, aber s(i) pro Doc + naechster Fremd-Cluster.
    Singletons -> s=0, nearest=-1."""
    n = len(labels)
    uniq = np.unique(labels)
    masks = {c: (labels == c) for c in uniq}
    sizes = {c: int(m.sum()) for c, m in masks.items()}
    s = np.zeros(n)
    nearest = np.full(n, -1, dtype=int)
    for i in range(n):
        ci = labels[i]
        if sizes[ci] <= 1:
            continue
        a = D[i, masks[ci]].sum() / (sizes[ci] - 1)
        best_b, best_c = None, -1
        for c in uniq:
            if c == ci:
                continue
            b_c = D[i, masks[c]].mean()
            if best_b is None or b_c < best_b:
                best_b, best_c = b_c, c
        nearest[i] = best_c
        s[i] = (best_b - a) / max(a, best_b) if max(a, best_b) > 0 else 0.0
    return s, nearest


def main():
    ap = argparse.ArgumentParser(description="Schritt 6 — thematische Bruecken (prod-nativ)")
    ap.add_argument("--db", required=True, help="Pfad zur pallas.db (Snapshot oder Prod)")
    ap.add_argument("--top", type=int, default=25, help="wie viele Bruecken-Docs zeigen")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    con = open_prod_db(args.db)
    try:
        require_schema(con)
        doc_ids, labels, X, names, summaries = load(con)
        if len(doc_ids) == 0:
            raise SystemExit("Keine geclusterten Docs -- erst cluster_topics --k N laufen lassen.")
        print(f"{len(doc_ids)} Docs geladen, {len(np.unique(labels))} Cluster")

        D = cosine_distance_matrix(X)
        s, nearest = per_doc_silhouette(D, labels)

        labelmap = dict(con.execute("SELECT cluster_id, label FROM archive_clusters").fetchall())
        multi = nearest >= 0
        print(f"Mean Silhouette: {s[multi].mean():+.4f}  |  "
              f"negativ (s<0): {int((s[multi] < 0).sum())}  |  "
              f"nahe Null (|s|<0.02): {int((np.abs(s[multi]) < 0.02).sum())}")

        print(f"\n=== Top {args.top} Bruecken-Docs (niedrigstes s) ===")
        order = np.argsort(s)
        shown = 0
        for idx in order:
            if nearest[idx] < 0:
                continue
            own = labelmap.get(int(labels[idx]), "?")
            near = labelmap.get(int(nearest[idx]), "?")
            disp = names[idx] if names[idx] and names[idx] != "?" else (summaries[idx] or "")[:70]
            print(f"s={s[idx]:+.3f}  doc {int(doc_ids[idx]):>5}  "
                  f"[{own} -> {near}]  {disp[:70]}")
            shown += 1
            if shown >= args.top:
                break

        if args.dry_run:
            print("\nDry-run fertig (nichts geschrieben).")
            return

        for did, sv, nc in zip(doc_ids, s, nearest):
            con.execute(
                "UPDATE documents SET silhouette=?, nearest_cluster_id=? WHERE id=?",
                (float(sv), int(nc) if nc >= 0 else None, int(did)),
            )
        for c in np.unique(labels):
            con.execute("UPDATE archive_clusters SET mean_silhouette=? WHERE cluster_id=?",
                        (float(s[labels == c].mean()), int(c)))
        con.commit()
        log_run(con, "step6_bridge_docs",
                {"top": args.top},
                {"docs": int(len(doc_ids)), "mean_silhouette": float(s[multi].mean()),
                 "negative": int((s[multi] < 0).sum())})
        print(f"\nFertig. s(i) + nearest_cluster_id fuer {len(doc_ids)} Docs geschrieben.")
    finally:
        con.close()


if __name__ == "__main__":
    main()

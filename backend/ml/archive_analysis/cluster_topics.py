"""Schritt 4 — Clustering auf Topic-Embeddings (prod-nativ).

Average-Link agglomeratives Clustering (Cosine-Distanz) ueber die
topic_embedding-Vektoren aus Schritt 4.6, mit vorgeschaltetem
Mean-Centering (Entfernen der dominanten gemeinsamen Komponente). Ohne
das Centering kettet Average-Link ~900 Docs zu einem Mega-Cluster
zusammen; mit Centering zerfaellt der in sinnvolle Themen-Cluster
(Befund Chat 81).

Prod-nativ: arbeitet direkt auf documents (PK id), single --db, kein ATTACH.
Gegenueber der Offline-Variante bewusst schlank:
  - keine Linkage-Persistenz: das Feature braucht Zuordnung + Labels +
    Bruecken, nicht die Matrix; Phase-3-Re-Cluster rechnet sie transient neu.
  - keine Anker-Diagnose: war k-Wahl-Hilfe, k=100 ist fix. Pallas-Kohaerenz
    wird separat im Verifikations-Schritt geprueft.

Hinweis: Der Mean-Vektor wird nicht persistiert -- ein Re-Cluster rechnet
das Centering jedes Mal neu ueber den dann aktuellen Doc-Satz.

Zweistufig:
  --k 0  (default) : nur Diagnose (Cluster-Groesse, Singletons, Silhouette
                     pro Cut). Kein cluster_id-Write.
  --k N            : zusaetzlich cluster_id bei N Clustern schreiben.

Aufruf:
  python3 -m backend.ml.archive_analysis.cluster_topics --db data/pallas-snapshot.db
  python3 -m backend.ml.archive_analysis.cluster_topics --db /data/pallas.db --k 100
"""
import argparse
import struct
import sys

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster

from backend.ml.registry import open_prod_db, log_run

DIM = 1024
DIAG_KS = [50, 75, 90, 100, 110, 125]


def load_vectors(con):
    """topic_embedding-BLOBs -> (doc_ids, matrix)."""
    rows = con.execute(
        "SELECT id, topic_embedding FROM documents "
        "WHERE topic_embedding IS NOT NULL ORDER BY id"
    ).fetchall()
    doc_ids, vecs = [], []
    for doc_id, blob in rows:
        doc_ids.append(doc_id)
        vecs.append(struct.unpack(f"<{DIM}f", blob))
    return doc_ids, np.asarray(vecs, dtype=np.float64)


def silhouette_cosine(D, labels):
    """Mean Silhouette ueber cosine-Distanzmatrix D. Singletons -> 0."""
    n = len(labels)
    uniq = np.unique(labels)
    masks = {c: (labels == c) for c in uniq}
    sizes = {c: int(m.sum()) for c, m in masks.items()}
    s = np.zeros(n)
    for i in range(n):
        ci = labels[i]
        if sizes[ci] <= 1:
            continue
        a = D[i, masks[ci]].sum() / (sizes[ci] - 1)
        b = min(D[i, masks[c]].mean() for c in uniq if c != ci)
        s[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return float(s.mean())


def diagnose(Z, D, n):
    """Pro Cut: #Cluster, groesster, Singletons, Silhouette."""
    print(f"\nDocs: {n}")
    print(f"{'k':>5} {'groesster':>10} {'singletons':>11} {'silhouette':>11}")
    for k in DIAG_KS:
        if k > n:
            continue
        labels = fcluster(Z, t=k, criterion="maxclust")
        sizes = np.bincount(labels)[1:]
        sil = silhouette_cosine(D, labels)
        print(f"{k:>5} {int(sizes.max()):>10} {int((sizes == 1).sum()):>11} {sil:>11.3f}")


def commit_clusters(con, doc_ids, Z, k):
    labels = fcluster(Z, t=k, criterion="maxclust")
    for doc_id, lab in zip(doc_ids, labels):
        con.execute(
            "UPDATE documents SET cluster_id=? WHERE id=?",
            (int(lab), doc_id),
        )
    con.commit()
    n_clusters = int(len(set(labels)))
    print(f"\ncluster_id geschrieben fuer k={k} ({n_clusters} Cluster).")
    return n_clusters


def run(con, k):
    doc_ids, X = load_vectors(con)
    n = len(doc_ids)
    if n == 0:
        raise SystemExit("Keine topic_embedding-Vektoren -- erst topic_embed laufen lassen.")
    print(f"Geladen: {n} Topic-Vektoren ({X.shape[1]}-dim)")
    X = X - X.mean(axis=0)
    Xn = X / np.linalg.norm(X, axis=1, keepdims=True)
    D = 1.0 - Xn @ Xn.T
    np.fill_diagonal(D, 0.0)
    Z = linkage(X, method="average", metric="cosine")
    print("Linkage gebaut (method=average, metric=cosine, mean-centered).")
    diagnose(Z, D, n)
    result = {"n_docs": n, "mean_centered": True}
    if k > 0:
        result["committed_k"] = commit_clusters(con, doc_ids, Z, k)
    log_run(con, "cluster_topics", {"method": "average-centered", "k": k}, result)


def main():
    p = argparse.ArgumentParser(description="Schritt 4 Topic-Clustering (prod-nativ)")
    p.add_argument("--db", required=True, help="Pfad zur pallas.db (Snapshot oder Prod)")
    p.add_argument("--k", type=int, default=0)
    args = p.parse_args()
    con = open_prod_db(args.db)
    try:
        run(con, args.k)
    finally:
        con.close()


if __name__ == "__main__":
    sys.exit(main())

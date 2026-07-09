#!/usr/bin/env python3
"""
project_topics.py — Phase 4, Schritt 3 (von 5) des semantischen Archiv-Strangs.

Berechnet das 2D-Layout fuer die "Ordner <-> Semantisch"-Ansicht **vorab** und
**persistiert** es (Architektur-Entscheidung: Option B, nicht transient):

    archive_clusters.hub_x / hub_y   -> Position der Cluster-Inseln ("Hubs")
    documents.proj_x     / proj_y    -> Position jedes Dokuments

Design (zweistufig, deterministisch, ohne neue Dependency -- nur numpy):

  (1) HUBS: Die Cluster-Zentroide (im 1024-dim topic_embedding-Raum) werden per
      PCA (numpy-SVD) auf 2D projiziert -> Hub-Positionen. Die Trennung der
      Inseln kommt aus cluster_id (schon berechnet), NICHT aus der Hoffnung,
      dass eine globale UMAP/t-SNE-Projektion sie findet.

  (2) DOCS (lokaler Offset): Jedes Doc wird relativ zu seinem Hub platziert. Der
      Offset ist die 2D-Projektion der Abweichung (emb - centroid) auf die
      cluster-LOKALEN Hauptachsen, global so skaliert, dass eine Insel etwa
      LOCAL_FRAC des typischen Hub-Abstands fuellt (sichtbar, aber ueberlappungsarm).

  (3) BRUECKEN-DOCS (silhouette < 0): werden zwischen ihren eigenen Hub und den
      nearest_cluster_id-Hub interpoliert, gewichtet nach Silhouette -- sie sitzen
      dadurch sichtbar *zwischen* zwei Inseln.

Hinweis Mean-Centering: Das globale Mean-Centering aus dem Clustering
(X = X - X.mean(0)) ist fuers Layout ein No-Op -- PCA zentriert ohnehin, und
(emb - centroid) ist gegen eine globale Verschiebung invariant. Daher hier nicht
noetig; die Geometrie ist deckungsgleich zum Clustering.

Determinismus: SVD hat keine stabile Vorzeichen-Konvention -> wir fixieren das
Vorzeichen pro Hauptachse (betragsgroesstes Element positiv, svd_flip-Konvention).
Sonst "springt" die Karte bei Re-Runs. Bei identischer Eingabe ist das Ergebnis
reproduzierbar; das Script ist idempotent (Re-Run ueberschreibt mit gleichen
Werten) -- wichtig fuer den Phase-3-Re-Cluster.

Aufruf (im pallas-Container):
    python3 -m backend.ml.archive_analysis.project_topics --db /data/pallas.db
"""

import argparse
import sys

import numpy as np

from backend.ml.registry import open_prod_db, log_run

# --- Konstanten -------------------------------------------------------------
DIM = 1024                     # topic_embedding-Dimension (bge-m3), BLOB = 4096 Byte
EPS = 1e-9                     # Schwelle fuer "praktisch null" (Singulaerwerte etc.)

# Insel-Radius als Anteil des typischen Hub-Abstands (Median naechster-Nachbar).
DEFAULT_LOCAL_FRAC = 0.35
# Bruecken-Interpolation: t=0.5 (Mitte) .. t=BRIDGE_MAX_T (nah am Nachbar-Hub).
BRIDGE_MIN_T = 0.5
BRIDGE_MAX_T = 0.85
# Anteil des lokalen Offsets, den Bruecken-Docs als Jitter behalten
# (verhindert exaktes Ueberlappen mehrerer Bruecken zwischen demselben Paar).
BRIDGE_OFFSET_FRAC = 0.5
# Perzentil fuer die gemeinsame End-Normalisierung der Koordinaten.
NORM_PERCENTILE = 99.0


# --- Reine Numerik-Helfer (keine DB, testbar) -------------------------------

def _blob_to_vec(blob):
    """BLOB (4096 Byte, little-endian float32) -> float64-Vektor der Laenge DIM.
    Entspricht struct.unpack('<1024f', blob), nur vektorisiert."""
    v = np.frombuffer(blob, dtype="<f4")
    if v.shape[0] != DIM:
        raise ValueError(f"Embedding-Laenge {v.shape[0]} != {DIM}")
    return v.astype(np.float64)


def _svd_flip(components, scores):
    """Vorzeichen pro Hauptachse deterministisch fixieren: das betragsgroesste
    Element jeder Komponente wird positiv (svd_flip-Konvention). components und
    scores werden in-place gedreht. Null-Komponenten bleiben unveraendert."""
    for i in range(components.shape[0]):
        j = int(np.argmax(np.abs(components[i])))
        if components[i, j] < 0:
            components[i] = -components[i]
            scores[:, i] = -scores[:, i]
    return components, scores


def _pca_2d(X):
    """Zentriert X und projiziert auf die 2 staerksten Hauptachsen.
    Rueckgabe: (components[2, d], scores[n, 2]) -- Vorzeichen fixiert.
    Achsen mit ~0 Varianz ergeben eine Null-Komponente + Null-Score
    (deterministisch, z.B. wenn ein Cluster nur auf einer Linie streut)."""
    n, d = X.shape
    Xc = X - X.mean(axis=0, keepdims=True)
    # full_matrices=False: U (n, r), s (r,), Vt (r, d), r = min(n, d)
    U, s, Vt = np.linalg.svd(Xc, full_matrices=False)
    comps = np.zeros((2, d), dtype=np.float64)
    scores = np.zeros((n, 2), dtype=np.float64)
    thr = EPS * (s[0] if s.shape[0] else 0.0)
    for k in range(min(2, s.shape[0])):
        if s[k] > thr:
            comps[k] = Vt[k]
            scores[:, k] = U[:, k] * s[k]
    return _svd_flip(comps, scores)


def _median_nn_distance(pts):
    """Median-Abstand zum naechsten Nachbarn in einer 2D-Punktmenge."""
    k = pts.shape[0]
    if k < 2:
        return 1.0
    diff = pts[:, None, :] - pts[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    return float(np.median(dist.min(axis=1)))


def _rms_radius(xy):
    """Wurzel des mittleren quadratischen Radius (0 bei leerer Menge)."""
    if xy.shape[0] == 0:
        return 0.0
    return float(np.sqrt((xy ** 2).sum(axis=1).mean()))


def compute_hub_positions(centroids):
    """Zentroide (n_clusters, DIM) -> Hub-Positionen (n_clusters, 2), Rohskala."""
    _, hub_xy = _pca_2d(centroids)
    return hub_xy


def compute_local_offsets(emb, labels_idx, centroids):
    """Lokaler Offset jedes Docs = Projektion von (emb - centroid) auf die
    cluster-lokalen 2 Hauptachsen. Rueckgabe (n_docs, 2), Rohskala (noch
    ungewichtet). Singletons / varianzfreie Cluster -> Offset (0, 0)."""
    n = emb.shape[0]
    off = np.zeros((n, 2), dtype=np.float64)
    for ci in range(centroids.shape[0]):
        mask = labels_idx == ci
        if int(mask.sum()) < 2:
            continue  # Singleton sitzt exakt auf dem Hub
        D = emb[mask] - centroids[ci]        # (m, DIM), per Definition zentriert
        _, sc = _pca_2d(D)
        off[mask] = sc
    return off


def _bridge_weight(silhouette):
    """Negative Silhouette -> Interpolationsgewicht t in [BRIDGE_MIN_T, BRIDGE_MAX_T]
    Richtung Nachbar-Cluster. t=0.5 bei silhouette=0, waechst je negativer."""
    t = 0.5 - 0.5 * silhouette
    return min(max(t, BRIDGE_MIN_T), BRIDGE_MAX_T)


# --- Hauptlogik -------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Phase 4/3: 2D-Layout (hub_x/hub_y, proj_x/proj_y) vorberechnen."
    )
    ap.add_argument("--db", required=True, help="Pfad zur pallas.db")
    ap.add_argument("--local-frac", type=float, default=DEFAULT_LOCAL_FRAC,
                    help="Insel-Radius als Anteil des Median-Hub-Abstands "
                         f"(Default {DEFAULT_LOCAL_FRAC}).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur rechnen + Kennzahlen ausgeben, nichts schreiben.")
    args = ap.parse_args()

    conn = open_prod_db(args.db)
    cur = conn.cursor()

    rows = cur.execute(
        "SELECT id, topic_embedding, cluster_id, silhouette, nearest_cluster_id "
        "FROM documents "
        "WHERE topic_embedding IS NOT NULL AND cluster_id IS NOT NULL "
        "ORDER BY id"
    ).fetchall()
    if not rows:
        print("Keine Dokumente mit topic_embedding + cluster_id gefunden.",
              file=sys.stderr)
        conn.close()
        sys.exit(1)

    doc_ids, doc_cluster, doc_sil, doc_near = [], [], [], []
    embs = []
    for _id, blob, cid, sil, near in rows:
        embs.append(_blob_to_vec(blob))
        doc_ids.append(int(_id))
        doc_cluster.append(int(cid))
        doc_sil.append(float(sil) if sil is not None else 0.0)
        doc_near.append(int(near) if near is not None else None)
    emb = np.asarray(embs, dtype=np.float64)          # (n_docs, DIM)
    n_docs = emb.shape[0]

    # Cluster-Index (dicht 0..n_clusters-1) + Zentroide
    uniq = sorted(set(doc_cluster))
    cid_to_idx = {c: i for i, c in enumerate(uniq)}
    labels_idx = np.fromiter((cid_to_idx[c] for c in doc_cluster),
                             dtype=np.int64, count=n_docs)
    n_clusters = len(uniq)
    centroids = np.zeros((n_clusters, DIM), dtype=np.float64)
    for i in range(n_clusters):
        centroids[i] = emb[labels_idx == i].mean(axis=0)

    # (1) Hubs aus Zentroid-PCA
    hub_xy = compute_hub_positions(centroids)         # (n_clusters, 2), roh

    # (2) Lokale Offsets, global auf Insel-Radius skalieren
    off = compute_local_offsets(emb, labels_idx, centroids)
    hub_nn = _median_nn_distance(hub_xy)
    r_rms = _rms_radius(off[(off != 0).any(axis=1)])
    gain = (args.local_frac * hub_nn / r_rms) if r_rms > EPS else 0.0
    off *= gain

    # Positionen: default = Hub + Offset
    pos = hub_xy[labels_idx] + off

    # (3) Bruecken-Docs (silhouette < 0, gueltiger Nachbar-Hub) interpolieren
    n_bridges = 0
    for i in range(n_docs):
        near = doc_near[i]
        if doc_sil[i] < 0 and near is not None and near in cid_to_idx:
            own = int(labels_idx[i])
            oth = cid_to_idx[near]
            if oth == own:
                continue
            t = _bridge_weight(doc_sil[i])
            pos[i] = ((1.0 - t) * hub_xy[own]
                      + t * hub_xy[oth]
                      + BRIDGE_OFFSET_FRAC * off[i])
            n_bridges += 1

    # Gemeinsame End-Normalisierung (Hubs + Docs in denselben Frame)
    rad = np.sqrt((pos ** 2).sum(axis=1))
    scale = float(np.percentile(rad, NORM_PERCENTILE))
    if scale <= EPS:
        scale = 1.0
    pos_n = pos / scale
    hub_n = hub_xy / scale

    if args.dry_run:
        print(f"[dry-run] {n_docs} Docs, {n_clusters} Cluster, {n_bridges} Bruecken.")
        print(f"[dry-run] hub_nn={hub_nn:.4f}  gain={gain:.4f}  scale={scale:.4f}")
        print(f"[dry-run] Hub-Beispiele:  {np.round(hub_n[:3], 4).tolist()}")
        print(f"[dry-run] Doc-Beispiele:  {np.round(pos_n[:3], 4).tolist()}")
        conn.close()
        return

    # Schreiben (eine Transaktion)
    hub_updates = [(float(hub_n[i, 0]), float(hub_n[i, 1]), int(uniq[i]))
                   for i in range(n_clusters)]
    doc_updates = [(float(pos_n[i, 0]), float(pos_n[i, 1]), doc_ids[i])
                   for i in range(n_docs)]
    cur.executemany(
        "UPDATE archive_clusters SET hub_x=?, hub_y=? WHERE cluster_id=?",
        hub_updates,
    )
    cur.executemany(
        "UPDATE documents SET proj_x=?, proj_y=? WHERE id=?",
        doc_updates,
    )
    conn.commit()  # UPDATEs festschreiben (log_run committet danach die Audit-Zeile)

    # Lauf protokollieren (Signatur wie cluster_topics.py: positional, zwei Dicts).
    log_run(
        conn,
        "project_topics",
        {"local_frac": args.local_frac},
        {"n_docs": n_docs, "n_clusters": n_clusters, "n_bridges": n_bridges},
    )

    conn.close()
    print(f"OK: {n_docs} proj_x/proj_y + {n_clusters} hub_x/hub_y geschrieben "
          f"({n_bridges} Bruecken interpoliert).")


if __name__ == "__main__":
    main()

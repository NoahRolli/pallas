# API-Endpunkt fuer die "Ordner <-> Semantisch"-Ansicht (semantischer Archiv-Strang).
# Endpoint: GET /api/archive/layout
#
# Liefert das vorberechnete 2D-Layout (project_topics.py, Phase 4/3) in EINEM
# konsistenten Snapshot: die Cluster-Inseln (hub_x/hub_y + Label + Groesse +
# mean_silhouette) und alle Dokumente (proj_x/proj_y + cluster_id + silhouette +
# nearest_cluster_id + Titel). Beide Queries laufen in derselben Session/Transaktion
# -> das Frontend sieht nie Docs mit cluster_ids eines bereits geaenderten
# Cluster-Satzes (relevant, falls ein Full-Re-Cluster nebenher liefe).
#
# ORM read-only; die Koordinaten schreibt offline project_topics.py.
# Bewusst KEINE topic_embedding-Spalte selektieren (4 KB BLOB pro Doc).

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.models.database import get_db
from backend.models.document import Document
from backend.models.archive_cluster import ArchiveCluster

router = APIRouter(prefix="/api/archive", tags=["archive"])


def _round(value, ndigits=5):
    """Float auf ndigits runden; None bleibt None (kleinerer Payload)."""
    return round(value, ndigits) if value is not None else None


# GET /api/archive/layout — Cluster-Hubs + Doc-Positionen fuer den Toggle
@router.get("/layout")
def get_archive_layout(db: Session = Depends(get_db)):
    """2D-Layout fuer die Semantisch-Ansicht (ein konsistenter Snapshot)."""
    # Cluster-Inseln: nur solche mit berechnetem Hub.
    cluster_rows = (
        db.query(
            ArchiveCluster.cluster_id,
            ArchiveCluster.label,
            ArchiveCluster.size,
            ArchiveCluster.mean_silhouette,
            ArchiveCluster.hub_x,
            ArchiveCluster.hub_y,
        )
        .filter(ArchiveCluster.hub_x.isnot(None))
        .order_by(ArchiveCluster.cluster_id)
        .all()
    )
    clusters = [
        {
            "cluster_id": cid,
            "label": label,
            "size": size,
            "mean_silhouette": _round(msil, 4),
            "hub_x": _round(hx),
            "hub_y": _round(hy),
        }
        for cid, label, size, msil, hx, hy in cluster_rows
    ]

    # Dokumente: nur solche mit berechneter Position (im Layout enthalten).
    doc_rows = (
        db.query(
            Document.id,
            Document.display_name,
            Document.filename,
            Document.cluster_id,
            Document.silhouette,
            Document.nearest_cluster_id,
            Document.proj_x,
            Document.proj_y,
        )
        .filter(Document.proj_x.isnot(None))
        .order_by(Document.id)
        .all()
    )
    documents = [
        {
            "id": did,
            "title": display_name or filename,
            "cluster_id": cid,
            "silhouette": _round(sil, 4),
            "nearest_cluster_id": near,
            "proj_x": _round(px),
            "proj_y": _round(py),
        }
        for did, display_name, filename, cid, sil, near, px, py in doc_rows
    ]

    return {
        "clusters": clusters,
        "documents": documents,
        "counts": {"clusters": len(clusters), "documents": len(documents)},
    }

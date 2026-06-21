# Model für die Cluster-Metadaten des semantischen Archiv-Strangs (ML Phase 2).
#
# Eigene Tabelle `archive_clusters` — bewusst abgegrenzt von:
#   - concept_clusters (Konzept-Graph)
#   - metis_clusters   (Journal-Metis)
# Befüllt durch backend/ml/archive_analysis/cluster_label.py; ORM read-only.
# Spalten/Typen 1:1 aus prod_schema_migrate.py.

from sqlalchemy import Column, Integer, Text, Float, DateTime, func
from sqlalchemy.orm import relationship
from backend.models.database import Base


class ArchiveCluster(Base):
    __tablename__ = "archive_clusters"

    # Cluster-Nummer aus dem Clustering (0..99). Extern vom Pipeline-Schritt
    # vergeben → kein Autoincrement.
    cluster_id = Column(Integer, primary_key=True, autoincrement=False)

    # LLM-generiertes Label (gemma4:e2b), z.B. "AI application development"
    label = Column(Text, nullable=True)

    # Anzahl Dokumente im Cluster
    size = Column(Integer, nullable=True)

    # Stichprobengröße, aus der das Label abgeleitet wurde
    sample_size = Column(Integer, nullable=True)

    # Modell-Tag der Label-Generierung
    label_model = Column(Text, nullable=True)

    # Zeitstempel der Label-Generierung (DB-Default CURRENT_TIMESTAMP)
    labeled_at = Column(DateTime, server_default=func.now())

    # Mittlere Silhouette des Clusters
    mean_silhouette = Column(Float, nullable=True)

    # Phase 4 -- 2D-Layout-Position des Cluster-Hubs (precompute via project_topics.py)
    hub_x = Column(Float, nullable=True)
    hub_y = Column(Float, nullable=True)

    # Beziehung: alle Dokumente dieses Clusters (read-only Navigation)
    documents = relationship("Document", back_populates="archive_cluster")

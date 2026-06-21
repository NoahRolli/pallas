# Model für hochgeladene Dokumente (PDF, Word, TXT etc.)
# Dokument gehört entweder zu einem Modul ODER direkt zu einem Ordner

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Float, LargeBinary,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from backend.models.database import Base


class Document(Base):
    __tablename__ = "documents"

    # Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # Fremdschlüssel — Modul (optional, für Studien-Dokumente mit Summary)
    module_id = Column(Integer, ForeignKey("modules.id"), nullable=True)

    # Fremdschlüssel — Ordner (optional, für lose Dateien ohne Modul)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)

    # Originaler Dateiname (z.B. "Vorlesung_03.pdf")
    filename = Column(String, nullable=False)

    # Anzeigename (editierbar, fallback auf filename)
    display_name = Column(String, nullable=True)

    # Speicherpfad auf der SSD
    file_path = Column(String, nullable=False)

    # Dateityp (pdf, docx, txt)
    file_type = Column(String, nullable=False)

    # Extrahierter Rohtext aus dem Dokument — wird vom Parser befüllt
    raw_text = Column(Text, default="")

    # Zeitstempel des Uploads
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Semantischer Archiv-Strang (ML Phase 2) -------------------------
    # Befüllt durch backend/ml/archive_analysis/*; ORM-seitig read-only.
    # Spalten/Typen 1:1 aus prod_schema_migrate.py.

    # LLM-generierte Topic-Zusammenfassung (gemma4:e2b) — Basis fürs Embedding
    topic_summary = Column(Text, nullable=True)

    # bge-m3 Embedding der Summary, 1024-dim float32 als gepackte Bytes (BLOB)
    topic_embedding = Column(LargeBinary, nullable=True)

    # Modell-Tag der Summary-Generierung (z.B. "gemma4:e2b")
    topic_summary_model = Column(Text, nullable=True)

    # Zeitstempel der Summary-Generierung
    topic_summary_at = Column(DateTime, nullable=True)

    # Zugeordneter Archiv-Cluster. FK nur auf ORM-Ebene (logisch) — die
    # ALTER-TABLE-Migration konnte keinen physischen Constraint nachrüsten.
    cluster_id = Column(Integer, ForeignKey("archive_clusters.cluster_id"),
                        nullable=True, index=True)

    # Silhouette-Score der Cluster-Zuordnung (negativ = Brücken-Doc)
    silhouette = Column(Float, nullable=True)

    # Nächstgelegener alternativer Cluster (für Brücken-Analyse)
    nearest_cluster_id = Column(Integer, nullable=True)

    # Phase 4 -- 2D-Layout-Koordinaten des Docs (precompute via project_topics.py)
    proj_x = Column(Float, nullable=True)
    proj_y = Column(Float, nullable=True)

    # Beziehung: Dokument gehört optional zu einem Modul
    module = relationship("Module", back_populates="documents")

    # Beziehung: Ein Dokument kann mehrere Zusammenfassungen haben
    summaries = relationship("Summary", back_populates="document",
                             cascade="all, delete-orphan")

    # Beziehung: zugeordneter Archiv-Cluster (read-only Navigation)
    archive_cluster = relationship("ArchiveCluster", back_populates="documents")

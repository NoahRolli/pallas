# Model für verschlüsselte Tagebucheinträge
# Alle sensiblen Felder (Titel, Inhalt, Datum) werden AES-256-GCM verschlüsselt
# Ohne korrektes Passwort sind die Daten vollständig unlesbar

from sqlalchemy import Column, Integer, LargeBinary, DateTime, String
from datetime import datetime, timezone
from backend.journal.models.journal_database import JournalBase


class JournalEntry(JournalBase):
    __tablename__ = "journal_entries"

    # Primärschlüssel
    id = Column(Integer, primary_key=True, index=True)

    # Verschlüsselte Felder — gespeichert als Binärdaten (bytes)
    # Im Klartext wäre das z.B. "Heute war ein guter Tag"
    # In der DB steht nur unlesbarer Ciphertext
    encrypted_title = Column(LargeBinary, nullable=False)
    encrypted_content = Column(LargeBinary, nullable=False)

    # Auch das Datum des Eintrags wird verschlüsselt
    # So kann niemand sehen WANN geschrieben wurde
    encrypted_date = Column(LargeBinary, nullable=False)

    # Initialisierungsvektor für AES-256-GCM
    # Jeder Eintrag bekommt einen eigenen IV (niemals wiederverwenden!)
    iv = Column(LargeBinary, nullable=False)

    # GCM Authentication Tag — stellt sicher dass nichts manipuliert wurde
    # Wenn jemand den Ciphertext ändert, schlägt die Entschlüsselung fehl
    auth_tag = Column(LargeBinary, nullable=False)

    # Nicht-sensitive Metadaten (für DB-Verwaltung, nicht für den User sichtbar)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Status-Flag — ermöglicht "Papierkorb" Funktion ohne echtes Löschen
    is_deleted = Column(Integer, default=0)
# Gemeinsame Dependencies für alle Journal-Endpunkte
# Werden als Vorbedingung vor geschützten Operationen aufgerufen

from fastapi import HTTPException
from backend.journal.services.session_service import is_session_active


def require_unlocked():
    """
    Prüft ob das Journal entsperrt ist.
    Wird vor jeder Operation aufgerufen — ohne AES-Key geht nichts.
    """
    if not is_session_active():
        raise HTTPException(
            status_code=403,
            detail="Journal ist gesperrt. Bitte zuerst /api/journal/unlock aufrufen."
        )
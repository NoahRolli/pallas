# Journal Session Service
# Verwaltet die Journal-Session: Key im RAM, Unlock/Lock, Timeout.
# Der AES-Key lebt NUR im RAM und wird bei Lock oder Server-Neustart gelöscht.

import time
from dataclasses import dataclass

from backend.journal.infra.journal_config import SESSION_TIMEOUT_MINUTES
from backend.journal.services.password_service import verify_password
from backend.journal.services.crypto_service import derive_aes_key


@dataclass
class JournalSession:
    """
    Hält den AES-Key im RAM solange das Journal entsperrt ist.

    Attribute:
        aes_key: Der abgeleitete AES-256 Schlüssel (lebt nur im RAM)
        last_activity: Zeitstempel der letzten Aktivität (für Timeout)
    """
    aes_key: bytes
    last_activity: float


# Globale Session — None wenn gesperrt, JournalSession wenn entsperrt
# WICHTIG: Lebt nur im RAM, wird bei Server-Neustart gelöscht
_session: JournalSession | None = None


def unlock(password: str, stored_hash: str, salt: bytes) -> bool:
    """
    Entsperrt das Journal: prüft Passwort und leitet AES-Key ab.
    Der Key wird im RAM gehalten bis lock() aufgerufen wird.

    Args:
        password: Das eingegebene Passwort
        stored_hash: Der gespeicherte Argon2id-Hash
        salt: Der gespeicherte Salt für die Key-Ableitung

    Returns:
        True wenn erfolgreich entsperrt, False bei falschem Passwort
    """
    global _session

    if not verify_password(password, stored_hash):
        return False

    aes_key = derive_aes_key(password, salt)
    _session = JournalSession(aes_key=aes_key, last_activity=time.time())
    return True


def lock() -> None:
    """
    Sperrt das Journal: löscht den AES-Key aus dem RAM.
    Wird aufgerufen bei: manuellem Lock, Timeout, Tab-Wechsel, etc.
    """
    global _session
    _session = None


def get_session() -> JournalSession | None:
    """
    Gibt die aktuelle Session zurück, falls aktiv und nicht abgelaufen.
    Aktualisiert den Aktivitäts-Zeitstempel bei jedem Zugriff.

    Returns:
        JournalSession wenn aktiv, None wenn gesperrt oder abgelaufen
    """
    global _session

    if _session is None:
        return None

    # Timeout prüfen
    elapsed_minutes = (time.time() - _session.last_activity) / 60
    if elapsed_minutes > SESSION_TIMEOUT_MINUTES:
        lock()
        return None

    # Aktivität aktualisieren (Reset des Timeout-Timers)
    _session.last_activity = time.time()
    return _session


def is_unlocked() -> bool:
    """
    Schneller Check ob das Journal entsperrt ist.

    Returns:
        True wenn entsperrt und Session gültig
    """
    return get_session() is not None
# Journal Password Service
# Verantwortlich für Passwort-Hashing und Verifizierung mit Argon2id.
# Das Passwort wird NIE gespeichert — nur der Hash.
# Kein Passwort-Reset möglich: ohne Passwort sind die Daten verloren.

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from backend.journal.infra.journal_config import (
    ARGON2_MEMORY_COST,
    ARGON2_TIME_COST,
    ARGON2_PARALLELISM,
    ARGON2_HASH_LENGTH,
    ARGON2_SALT_LENGTH,
)

# Argon2id Hasher mit den Parametern aus journal_config.py
# Argon2id kombiniert die Stärken von Argon2i (Side-Channel-Schutz)
# und Argon2d (GPU-Cracking-Schutz)
_hasher = PasswordHasher(
    memory_cost=ARGON2_MEMORY_COST,
    time_cost=ARGON2_TIME_COST,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LENGTH,
    salt_len=ARGON2_SALT_LENGTH,
)


def hash_password(password: str) -> str:
    """
    Erstellt einen Argon2id-Hash des Passworts.
    Wird beim erstmaligen Journal-Setup aufgerufen.
    Der Hash wird in der DB gespeichert, das Passwort NICHT.

    Returns:
        Argon2id-Hash als String (enthält Salt, Parameter und Hash)
    """
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Prüft ob ein Passwort zum gespeicherten Hash passt.
    Wird beim Journal-Unlock aufgerufen.

    Returns:
        True wenn korrekt, False wenn falsch
    """
    try:
        return _hasher.verify(stored_hash, password)
    except VerifyMismatchError:
        return False
# Zentrale Model-Registry für SQLAlchemy
#
# Importiert alle Models, damit SQLAlchemy-Relationships aufgelöst werden können.
# Nötig weil Pallas relationship("Module", ...) als String referenziert — die Klasse
# muss zur Laufzeit im Class-Registry vorhanden sein, sonst knallt's beim ersten
# query() mit InvalidRequestError.
#
# Verwendung:
#   - main.py importiert dieses Modul VOR Base.metadata.create_all()
#   - CLI-Scripts importieren es VOR der ersten DB-Operation
#
# Neues Model? → hier einen Import ergänzen, NICHT in main.py oder Scripts.

# Pallas-Hauptmodels
from backend.models.module import Module  # noqa: F401
from backend.models.document import Document  # noqa: F401
from backend.models.archive_cluster import ArchiveCluster  # noqa: F401
from backend.models.summary import Summary  # noqa: F401
from backend.models.mindmap_node import MindmapNode  # noqa: F401
from backend.models.folder import Folder  # noqa: F401
from backend.models.calendar_event import CalendarEvent  # noqa: F401
from backend.models.icloud import ICloudCalendar  # noqa: F401
from backend.models.sport_entry import SportEntry  # noqa: F401
from backend.models.note import Note  # noqa: F401
from backend.models.relation import RelationType  # noqa: F401
from backend.models.git_commit import GitCommit  # noqa: F401
from backend.models.concept import (  # noqa: F401
    Concept, ConceptSource, ConceptEdge, ConceptCluster, ConceptClusterMember,
)
from backend.models.llm import (  # noqa: F401
    LLMProvider, LLMConversation, LLMMessage,
)

# Delphi-Models (Knowledge-Chat-Modul)
from backend.models.delphi_models import (  # noqa: F401
    DelphiConversation, DelphiMessage, DelphiCitation,
)

# Journal-Models (separate DB, aber gleicher Import-Mechanismus)
from backend.journal.models.journal_entry import JournalEntry  # noqa: F401
from backend.journal.models.medication import (  # noqa: F401
    Medication, IntakeLog, MedicationSettings, DoseChange,
)
from backend.journal.models.mood_cache import MoodCache  # noqa: F401
from backend.journal.models.storyline import StorylineCache  # noqa: F401
from backend.journal.models.mood_checkin import MoodCheckIn  # noqa: F401
from backend.journal.models.journal_metis_node import JournalMetisNode  # noqa: F401
from backend.journal.models.journal_metis_edge import JournalMetisEdge  # noqa: F401
from backend.journal.models.journal_metis_cluster import (  # noqa: F401
    JournalMetisCluster, JournalMetisClusterMember,
)

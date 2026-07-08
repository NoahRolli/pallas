# Unlinked Mentions — Konzeptnamen in Notes/Summaries finden
# die nicht per WikiLink oder ConceptSource verknuepft sind
# Reines String-Matching, kein AI noetig

import re
import logging
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.models.database import get_db
from backend.models.concept import Concept, ConceptSource
from backend.models.note import Note
from backend.models.summary import Summary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/concepts", tags=["concepts"])

# HTML-Tags entfernen fuer Plaintext-Suche
TAG_RE = re.compile(r"<[^>]+>")
# WikiLink-Titel aus data-wiki-title extrahieren
WIKI_TITLE_RE = re.compile(r'data-wiki-title="([^"]*)"', re.IGNORECASE)


def _strip_html(html: str) -> str:
    """HTML-Tags entfernen, Entities behalten."""
    return TAG_RE.sub(" ", html).strip()


def _extract_wiki_titles(html: str) -> set[str]:
    """Alle bereits verlinkten WikiLink-Titel aus HTML extrahieren."""
    return {t.lower() for t in WIKI_TITLE_RE.findall(html)}


def _find_mentions(text: str, name: str) -> list[str]:
    """Findet alle Vorkommen von name im Text, gibt Kontext-Snippets zurueck."""
    # Wortgrenzen-Match, case-insensitive
    pattern = re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE)
    snippets = []
    for match in pattern.finditer(text):
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        snippet = text[start:end].strip()
        if start > 0:
            snippet = "..." + snippet
        if end < len(text):
            snippet = snippet + "..."
        snippets.append(snippet)
    return snippets


# Max. Konzept-Laenge in Woertern (aus Daten: 7). N-Gramme bis hier pruefen.
_MAX_CONCEPT_WORDS = 8
# Tokenizer: Woerter + ihre Positionen im Text (fuer Snippet-Kontext).
_WORD_RE = re.compile(r"\w+", re.UNICODE)


def _snippet_at(text: str, start: int, end: int) -> str:
    """Kontext-Snippet um [start, end) — identisch zur alten _find_mentions-Logik."""
    s = max(0, start - 50)
    e = min(len(text), end + 50)
    snip = text[s:e].strip()
    if s > 0:
        snip = "..." + snip
    if e < len(text):
        snip = snip + "..."
    return snip


def _find_all_mentions(text: str, concept_names: set[str]) -> dict[str, list[str]]:
    """Scannt den Text EINMAL und findet Vorkommen ALLER concept_names.

    Ersetzt die alte Pro-Konzept-Regex-Schleife: statt fuer jeden der ~15k
    Konzeptnamen einen eigenen \b-Regex ueber den ganzen Text laufen zu lassen,
    tokenisieren wir den Text einmal und pruefen N-Gramme (Laenge 1.._MAX)
    gegen das Konzept-Set (O(1)-Lookup). Semantik bleibt Wortgrenzen-Match,
    case-insensitive — wie zuvor.
    """
    # Token mit Position (lower fuer Vergleich, Original-Positionen fuer Snippet)
    toks = [(m.group(0).lower(), m.start(), m.end()) for m in _WORD_RE.finditer(text)]
    out: dict[str, list[str]] = {}
    n = len(toks)
    for i in range(n):
        # N-Gramme ab Position i aufbauen, solange sinnvoll
        upper = min(_MAX_CONCEPT_WORDS, n - i)
        for size in range(1, upper + 1):
            phrase = " ".join(toks[i + k][0] for k in range(size))
            if phrase in concept_names:
                start = toks[i][1]
                end = toks[i + size - 1][2]
                out.setdefault(phrase, []).append(_snippet_at(text, start, end))
    return out


@router.get("/unlinked-mentions")
def get_unlinked_mentions(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=500),
):
    """Findet Konzeptnamen in Notes/Summaries ohne WikiLink oder Source-Verknuepfung.

    Ein-Durchlauf-Scan: pro Dokument wird der Text EINMAL tokenisiert und gegen
    das Konzept-Set gematcht (_find_all_mentions), statt fuer jedes der ~15k
    Konzepte einzeln einen Regex ueber den Text zu jagen. Semantik unveraendert.
    """
    # Konzepte laden (min. 3 Zeichen) -> Name(lower) -> Concept
    concepts = db.query(Concept).filter(Concept.name.isnot(None)).all()
    concept_map = {c.name.lower(): c for c in concepts if len(c.name) >= 3}
    if not concept_map:
        return {"mentions": [], "total": 0}
    concept_names = set(concept_map.keys())

    # Bestehende Source-Verknuepfungen (concept_id, type, source_id)
    linked_set = {
        (cs.concept_id, cs.source_type, cs.source_id)
        for cs in db.query(
            ConceptSource.concept_id,
            ConceptSource.source_type,
            ConceptSource.source_id,
        ).all()
    }

    mentions = []

    def _scan(source_type, source_id, source_title, html):
        wiki_titles = _extract_wiki_titles(html)
        plaintext = _strip_html(html)
        full_text = f"{source_title or ''} {plaintext}"
        found = _find_all_mentions(full_text, concept_names)
        title_lower = (source_title or "").lower()
        for name, snippets in found.items():
            if name == title_lower:            # Selbstreferenz
                continue
            if name in wiki_titles:            # bereits per WikiLink verlinkt
                continue
            concept = concept_map[name]
            if (concept.id, source_type, source_id) in linked_set:
                continue                       # bereits per ConceptSource verknuepft
            mentions.append({
                "concept_id": concept.id,
                "concept_name": concept.name,
                "source_type": source_type,
                "source_id": source_id,
                "source_title": source_title or f"{source_type.capitalize()} #{source_id}",
                "snippets": snippets[:3],
                "count": len(snippets),
            })

    for note in db.query(Note).all():
        _scan("note", note.id, note.title, note.content or "")

    for summary in db.query(Summary).all():
        _scan("summary", summary.id, summary.title, summary.content or "")

    mentions.sort(key=lambda m: m["count"], reverse=True)
    return {"mentions": mentions[:limit], "total": len(mentions)}


@router.post("/unlinked-mentions/{concept_id}/link")
def link_mention(
    concept_id: int,
    source_type: str = Query(...),
    source_id: int = Query(...),
    db: Session = Depends(get_db),
):
    """Erstellt ConceptSource-Verknuepfung fuer eine Unlinked Mention."""
    concept = db.query(Concept).filter(Concept.id == concept_id).first()
    if not concept:
        return {"error": "Konzept nicht gefunden"}

    # Pruefen ob schon verknuepft
    existing = db.query(ConceptSource).filter(
        ConceptSource.concept_id == concept_id,
        ConceptSource.source_type == source_type,
        ConceptSource.source_id == source_id,
    ).first()
    if existing:
        return {"status": "already_linked"}

    db.add(ConceptSource(
        concept_id=concept_id,
        source_type=source_type,
        source_id=source_id,
        relevance=0.7,  # Hoeher als Default weil User bestaetigt
    ))
    db.commit()
    return {"status": "linked", "concept_name": concept.name}


@router.post("/unlinked-mentions/{concept_id}/dismiss")
def dismiss_mention(
    concept_id: int,
    source_type: str = Query(...),
    source_id: int = Query(...),
):
    """Markiert einen Vorschlag als irrelevant (kein DB-Eintrag, nur im Frontend)."""
    # Dismissed werden im Frontend per localStorage gespeichert
    # Kein Backend-Eintrag noetig — spart DB-Komplexitaet
    return {"status": "dismissed"}

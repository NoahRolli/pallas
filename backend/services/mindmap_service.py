# Mindmap-Service: Baut Mindmap-Strukturen aus AI-Daten
# Speichert Knoten hierarchisch in der Datenbank
# Ermöglicht Zoom-Levels: Übersicht → Kapitel → Detail

from sqlalchemy.orm import Session
from backend.models.mindmap_node import MindmapNode
from backend.services.ai_service import generate_mindmap, deep_dive


async def create_mindmap_from_summary(
    summary_id: int,
    text: str,
    db: Session
) -> list[dict]:
    """
    Generiert eine komplette Mindmap aus einem Text via AI.
    Speichert alle Knoten in der Datenbank.
    Gibt die Baumstruktur als Liste zurück.
    """
    # AI generiert die Baumstruktur
    tree = await generate_mindmap(text)

    # Rekursiv alle Knoten in der DB speichern
    saved_nodes = []
    for node_data in tree:
        _save_node_recursive(
            node_data=node_data,
            summary_id=summary_id,
            parent_id=None,
            depth=0,
            db=db,
            saved=saved_nodes,
        )

    db.commit()
    return tree


def _save_node_recursive(
    node_data: dict,
    summary_id: int,
    parent_id: int | None,
    depth: int,
    db: Session,
    saved: list,
):
    """
    Speichert einen Knoten und seine Kinder rekursiv in der DB.
    Weist automatisch Tiefenstufen zu (0=Übersicht, 1=Kapitel, 2+=Detail).
    """
    node = MindmapNode(
        summary_id=summary_id,
        parent_id=parent_id,
        label=node_data.get("label", ""),
        detail=node_data.get("detail", ""),
        depth_level=depth,
        position_x=0.0,
        position_y=0.0,
    )
    db.add(node)
    db.flush()  # ID wird sofort vergeben, aber noch nicht committet
    saved.append(node)

    # Kinder rekursiv speichern
    for child_data in node_data.get("children", []):
        _save_node_recursive(
            node_data=child_data,
            summary_id=summary_id,
            parent_id=node.id,
            depth=depth + 1,
            db=db,
            saved=saved,
        )


async def expand_node(
    node_id: int,
    context: str,
    db: Session
) -> list[dict]:
    """
    Generiert Unterknoten für einen bestehenden Knoten (Deep Dive).
    Wird aufgerufen wenn der User in der Mindmap reinzoomt.
    """
    node = db.query(MindmapNode).filter(MindmapNode.id == node_id).first()
    if not node:
        raise ValueError(f"Knoten {node_id} nicht gefunden.")

    # AI generiert detailliertere Unterknoten
    children_data = await deep_dive(node.label, node.detail, context)

    # Neue Knoten in der DB speichern
    saved = []
    for child_data in children_data:
        _save_node_recursive(
            node_data=child_data,
            summary_id=node.summary_id,
            parent_id=node.id,
            depth=node.depth_level + 1,
            db=db,
            saved=saved,
        )

    db.commit()
    return children_data


def get_mindmap_tree(summary_id: int, db: Session) -> list[dict]:
    """
    Lädt die komplette Mindmap als Baumstruktur aus der DB.
    Baut den Baum rekursiv aus den flachen DB-Einträgen auf.
    """
    # Alle Knoten dieser Zusammenfassung laden
    nodes = db.query(MindmapNode).filter(
        MindmapNode.summary_id == summary_id
    ).all()

    if not nodes:
        return []

    # Flache Liste → Baumstruktur umwandeln
    nodes_by_id = {n.id: n for n in nodes}
    root_nodes = [n for n in nodes if n.parent_id is None]

    return [_build_tree(node, nodes_by_id) for node in root_nodes]


def _build_tree(node: MindmapNode, nodes_by_id: dict) -> dict:
    """Baut rekursiv einen Baum aus einem Knoten und seinen Kindern."""
    children = [
        n for n in nodes_by_id.values()
        if n.parent_id == node.id
    ]

    return {
        "id": node.id,
        "label": node.label,
        "detail": node.detail,
        "depth_level": node.depth_level,
        "position_x": node.position_x,
        "position_y": node.position_y,
        "children": [_build_tree(c, nodes_by_id) for c in children],
    }
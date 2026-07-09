// Typen fuer die semantische Archiv-Karte (GET /api/archive/layout).
// Spiegelt exakt den JSON-Contract von backend/api/archive.py.

// Eine Cluster-Insel (Hub) auf der Karte.
export interface ArchiveCluster {
  cluster_id: number
  label: string | null
  size: number | null
  mean_silhouette: number | null
  hub_x: number | null
  hub_y: number | null
}

// Ein Dokument-Punkt auf der Karte.
export interface ArchiveDoc {
  id: number
  title: string
  cluster_id: number | null
  silhouette: number | null
  nearest_cluster_id: number | null
  proj_x: number | null
  proj_y: number | null
}

// Vollstaendige Antwort des Layout-Endpoints.
export interface ArchiveLayout {
  clusters: ArchiveCluster[]
  documents: ArchiveDoc[]
  counts: { clusters: number; documents: number }
}

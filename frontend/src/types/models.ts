// TypeScript-Typen für alle Pallas Datenmodelle
// Diese Typen spiegeln die Backend-Models (SQLAlchemy) wider
// Sie sorgen dafür, dass VS Code Fehler erkennt wenn wir
// falsche Felder verwenden oder Typen verwechseln
//
// Beispiel: Wenn das Backend "name" als String liefert,
// und wir versehentlich module.titel schreiben, zeigt VS Code einen Fehler

// --- Studienmodul ---
// Entspricht backend/models/module.py
// Ein Modul ist ein Fach/Kurs (z.B. "Lineare Algebra")
export interface Module {
  id: number
  name: string
  description: string
  color: string              // Hex-Farbe, z.B. "#4a90d9"
  created_at: string         // ISO-Datum vom Backend
  updated_at: string
}

// Payload zum Erstellen/Aktualisieren eines Moduls
// Enthält nur die Felder die der User eingibt (ohne id, timestamps)
export interface ModuleCreate {
  name: string
  description: string
  color: string
}

// --- Dokument ---
// Entspricht backend/models/document.py
// Ein hochgeladenes Dokument innerhalb eines Moduls
export interface Document {
  id: number
  module_id: number
  filename: string
  file_path: string
  file_type: string          // z.B. "pdf", "docx", "txt"
  raw_text: string           // Extrahierter Text (vom Parser)
  uploaded_at: string
}

// --- Zusammenfassung ---
// Entspricht backend/models/summary.py
// AI-generierte Zusammenfassung eines Dokuments
export interface Summary {
  id: number
  document_id: number
  summary: string            // Der Zusammenfassungstext
  key_terms: string[]        // Liste der Schlüsselbegriffe
  ai_provider: string        // "claude" oder "ollama"
  created_at: string
}

// --- Mindmap-Knoten ---
// Entspricht backend/models/mindmap_node.py
// Ein einzelner Knoten in der Mindmap-Baumstruktur
export interface MindmapNode {
  id: number
  label: string              // Kurzbezeichnung (z.B. "Vektoren")
  detail: string             // Erklärung
  depth_level: number        // 0=Übersicht, 1=Kapitel, 2+=Detail
  position_x: number         // X-Position für das Frontend
  position_y: number         // Y-Position für das Frontend
  children: MindmapNode[]    // Rekursiv: Unterknoten
}

// --- Journal ---
// Entspricht backend/journal/models/journal_entry.py
// Ein entschlüsselter Tagebucheintrag (wie er vom Backend kommt)
export interface JournalEntry {
  id: number
  title: string              // Entschlüsselter Titel
  content: string            // Entschlüsselter Inhalt
  date: string               // Entschlüsseltes Datum (ISO)
  created_at: string
  updated_at: string
}

// Payload zum Erstellen eines neuen Eintrags
export interface JournalEntryCreate {
  title: string
  content: string
  date: string               // ISO-Format, z.B. "2026-03-11"
}

// Status des Journals (von GET /api/journal/status)
export interface JournalStatus {
  is_setup: boolean          // Wurde ein Passwort gesetzt?
  is_unlocked: boolean       // Ist die Session aktiv?
}
// Journal — Verschlüsseltes Tagebuch
// Diese Seite wird später das Herzstück der Journal-Funktionalität:
// - Passwort-Eingabe zum Entsperren
// - Liste aller entschlüsselten Einträge
// - Neuen Eintrag erstellen/bearbeiten
// - Mood-Tracking und Analyse-Ansichten

function Journal() {
  // Aktuell nur ein Platzhalter — die volle Implementierung folgt
  // wenn wir die Journal-API (auth + entries) ans Frontend anbinden
  return (
    <div>
      {/* Seitentitel */}
      <h1 className="text-3xl font-bold mb-6">Journal</h1>

      {/* Platzhalter-Text bis die Unlock-Logik implementiert ist */}
      <p className="text-gray-400">
        Verschlüsseltes Tagebuch — kommt bald.
      </p>
    </div>
  )
}

// Default Export — wird in App.tsx vom Router importiert
export default Journal
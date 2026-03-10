// Dashboard — Startseite der Pallas App
// Zeigt eine Übersicht aller Studienmodule an
// Später kommen hier hinzu:
// - Modulkarten mit Fortschrittsanzeige
// - Schnellzugriff auf letzte Zusammenfassungen
// - Upload-Button für neue Dokumente
// - Statistiken (Anzahl Module, Dokumente, Zusammenfassungen)

function Dashboard() {
  // Aktuell ein Platzhalter — wird dynamisch sobald wir
  // die Module-API (GET /api/modules/) ans Frontend anbinden
  return (
    <div>
      {/* Seitentitel */}
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {/* Platzhalter bis die Modul-Liste implementiert ist */}
      <p className="text-gray-400">
        Deine Studienmodule erscheinen hier.
      </p>
    </div>
  )
}

// Default Export — wird in App.tsx vom Router importiert
export default Dashboard

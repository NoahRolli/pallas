// Sidebar — Hauptnavigation der Pallas App
// Wird links auf jeder Seite angezeigt (via Layout.tsx)
// Enthält Links zu allen Hauptbereichen: Dashboard, Journal
// Später kommen hinzu: Modul-Liste, Settings, AI-Provider-Wechsel

import { NavLink } from 'react-router-dom'

function Sidebar() {
  // NavLink-Styling: Aktiver Link bekommt hellen Hintergrund,
  // inaktive Links sind grau und werden beim Hovern heller
  // isActive wird automatisch von React Router gesetzt
  const linkStyle = ({ isActive }: { isActive: boolean }) =>
    `block px-4 py-2 rounded-lg transition-colors ${
      isActive
        ? 'bg-white/10 text-white'           // Aktiver Link: leicht heller
        : 'text-gray-400 hover:text-white hover:bg-white/5'  // Inaktiv: grau
    }`

  return (
    // aside = semantisches HTML für Seitenleisten
    // Feste Breite (w-64 = 256px), dunkler Hintergrund, Rand rechts
    <aside className="w-64 bg-gray-900 border-r border-gray-800 p-6 flex flex-col">

      {/* Logo / App-Name */}
      <h1 className="text-2xl font-bold mb-8">Pallas</h1>

      {/* Navigation — NavLink statt <a> für Client-Side Routing
          Das heisst: Kein Seiten-Neuladen, nur der Content-Bereich wechselt */}
      <nav className="flex flex-col gap-1">
        {/* to="/" → Dashboard (Startseite) */}
        <NavLink to="/" className={linkStyle}>
          Dashboard
        </NavLink>

        {/* to="/journal" → Verschlüsseltes Tagebuch */}
        <NavLink to="/journal" className={linkStyle}>
          Journal
        </NavLink>
      </nav>

      {/* Footer mit Versionsnummer — mt-auto schiebt es ganz nach unten */}
      <div className="mt-auto text-xs text-gray-600">
        v0.1.0
      </div>
    </aside>
  )
}

// Default Export — wird in Layout.tsx importiert
export default Sidebar

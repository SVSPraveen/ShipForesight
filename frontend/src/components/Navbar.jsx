import { useState, useEffect } from 'react'
import { getHealth } from '../api'

export default function Navbar() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth({ status: 'error', models_loaded: false }))

    // Poll every 30 seconds
    const id = setInterval(() => {
      getHealth().then(setHealth).catch(() => setHealth({ status: 'error', models_loaded: false }))
    }, 30000)
    return () => clearInterval(id)
  }, [])

  const isAlive = health?.status === 'ok' && health?.models_loaded

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <a className="navbar-logo" href="/">
          <div className="logo-icon">🚚</div>
          <span className="logo-text">Ship<span>Foresight</span></span>
        </a>
        <div className="flex-row">
          {health && (
            <div className="flex-row" style={{ gap: '0.5rem' }}>
              <div className={`pulse-dot ${isAlive ? '' : 'danger'}`} />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {isAlive ? 'All systems operational' : health?.models_loaded === false ? 'Models not loaded' : 'Backend offline'}
              </span>
            </div>
          )}
          <span className="badge badge-brand" style={{ fontSize: '0.7rem' }}>v1.0</span>
        </div>
      </div>
    </nav>
  )
}

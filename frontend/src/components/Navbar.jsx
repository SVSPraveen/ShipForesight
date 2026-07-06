import { useState, useEffect } from 'react'
import { getHealth } from '../api'

export default function Navbar() {
  const [health, setHealth] = useState(null)

  useEffect(() => {
    const check = () => getHealth().then(setHealth).catch(() => setHealth({ status: 'error', models_loaded: false }))
    check()
    const id = setInterval(check, 30000)
    return () => clearInterval(id)
  }, [])

  const isAlive = health?.status === 'ok' && health?.models_loaded

  return (
    <nav className="navbar">
      <div className="logo">
        <span>📦</span>
        ShipForesight
        <span style={{ fontWeight: 400, color: '#94A3B8', fontSize: '0.75rem', marginLeft: '0.25rem' }}>v1.0</span>
      </div>
      <div className="navbar-right">
        {health && (
          <span style={{ fontSize: 12, color: isAlive ? '#4ADE80' : '#F87171', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: isAlive ? '#4ADE80' : '#F87171', display: 'inline-block' }} />
            {isAlive ? 'All systems operational' : 'Backend offline'}
          </span>
        )}
        <span style={{ fontSize: 12, color: '#64748B', background: 'rgba(255,255,255,0.08)', padding: '0.2rem 0.6rem', borderRadius: 4, border: '1px solid rgba(255,255,255,0.1)' }}>
          ML Pipeline Ready
        </span>
      </div>
    </nav>
  )
}

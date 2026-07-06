const API_KEY = import.meta.env.VITE_API_KEY || 'shipforesight_dev_key_2026'
const BASE_URL = ''   // Vite proxy forwards /predict, /health, /explain to localhost:8000

const headers = () => ({
  'Content-Type': 'application/json',
  'X-API-Key': API_KEY
})

export async function getHealth() {
  const res = await fetch(`${BASE_URL}/health`, { headers: headers() })
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function postPredict(payload) {
  const res = await fetch(`${BASE_URL}/predict`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(payload)
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    // FastAPI validation errors come as {detail: [{loc, msg, type}]}
    if (Array.isArray(err.detail)) {
      throw new Error(err.detail.map(e => `${e.loc?.slice(-1)[0] || 'field'}: ${e.msg}`).join('; '))
    }
    throw new Error(typeof err.detail === 'string' ? err.detail : `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getExplain(token, language = 'English') {
  if (!token) throw new Error('No explain token available. Run a prediction first.')
  const res = await fetch(`${BASE_URL}/explain?token=${encodeURIComponent(token)}&language=${encodeURIComponent(language)}`, {
    headers: headers()
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

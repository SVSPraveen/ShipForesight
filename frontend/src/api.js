const API_KEY = import.meta.env.VITE_API_KEY || 'dev_key_change_me'
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
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getExplain(token, language = 'English') {
  const res = await fetch(`${BASE_URL}/explain?token=${token}&language=${encodeURIComponent(language)}`, {
    headers: headers()
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

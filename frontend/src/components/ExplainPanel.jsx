import { useState } from 'react'
import { getExplain } from '../api'

const LANGUAGES = ['English', 'Hindi', 'Arabic', 'French', 'Spanish', 'German', 'Tamil', 'Marathi', 'Gujarati']

export default function ExplainPanel({ token }) {
  const [loading, setLoading] = useState(false)
  const [explanation, setExplanation] = useState(null)
  const [error, setError] = useState(null)
  const [language, setLanguage] = useState('English')

  const fetch = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getExplain(token, language)
      setExplanation(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="explain-card fade-in">
      <div className="explain-header">
        <span className="explain-title">AI Risk Explanation</span>
        <select className="lang-select" value={language} onChange={e => setLanguage(e.target.value)}>
          {LANGUAGES.map(l => <option key={l}>{l}</option>)}
        </select>
      </div>

      <div className="explain-body">
        {!explanation && !loading && !error && (
          <button className="btn-explain" onClick={fetch} disabled={!token}>
            Generate Explanation
          </button>
        )}

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#6B7280', fontSize: 13 }}>
            <div className="spinner" style={{ borderColor: '#E5E7EB', borderTopColor: '#2563EB' }} />
            Analyzing supply chain factors...
          </div>
        )}

        {error && (
          <div className="error-card">{error}</div>
        )}

        {explanation && !loading && (
          <>
            <p className="explain-text">{explanation.explanation}</p>
            <div className="explain-meta">
              <span>Model: {explanation.model_used}</span>
              <span>{explanation.explain_latency_ms?.toFixed(0)}ms</span>
            </div>
            <button className="btn-explain" style={{ marginTop: '0.75rem' }} onClick={fetch}>
              Regenerate
            </button>
          </>
        )}
      </div>
    </div>
  )
}

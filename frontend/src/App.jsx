import { useState } from 'react'
import Navbar from './components/Navbar'
import ShipmentForm, { defaultForm } from './components/ShipmentForm'
import ResultCard from './components/ResultCard'
import ExplainPanel from './components/ExplainPanel'
import MapWidget from './components/MapWidget'
import { postPredict } from './api'

export default function App() {
  const [form, setForm] = useState(defaultForm)
  const [loading, setLoading] = useState(false)
  const [prediction, setPrediction] = useState(null)
  const [error, setError] = useState(null)

  const handlePredict = async (payload) => {
    setLoading(true)
    setError(null)
    setPrediction(null)
    try {
      const res = await postPredict(payload)
      setPrediction(res)
    } catch (err) {
      // err.message may be "[object Object]" if detail is a FastAPI validation list
      let msg = err.message
      if (!msg || msg === '[object Object]') msg = 'Prediction failed. Check the backend is running.'
      try {
        const parsed = JSON.parse(msg)
        if (Array.isArray(parsed)) msg = parsed.map(e => e.msg || e.message || JSON.stringify(e)).join('; ')
        else if (parsed.detail) msg = Array.isArray(parsed.detail) ? parsed.detail.map(e => e.msg).join('; ') : parsed.detail
      } catch (e) { /* msg is already a plain string */ }
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Navbar />
      <div className="main-container">
        {/* LEFT: Form Panel */}
        <div className="form-panel">
          <ShipmentForm form={form} setForm={setForm} onSubmit={handlePredict} loading={loading} />
        </div>

        {/* RIGHT: Map + Results */}
        <div className="results-panel">
          {error && (
            <div style={{ padding: '1rem 1.5rem' }}>
              <div className="error-card">
                <b>Error:</b> {error}
              </div>
            </div>
          )}

          {/* Map always visible */}
          <div className="map-section">
            <MapWidget
              originCity={form.origin_city}
              originCountry={form.origin_country}
              destCity={form.destination_city}
              destCountry={form.destination_country}
              carrierType={form.carrier_type}
            />
          </div>

          {/* Results appear below map after prediction */}
          {prediction && (
            <div className="result-section fade-in">
              <ResultCard prediction={prediction} />
              <ExplainPanel token={prediction.explain_token} />
            </div>
          )}
        </div>
      </div>
    </>
  )
}

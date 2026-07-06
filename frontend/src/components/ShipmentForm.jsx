import { useState } from 'react'

const CARRIERS = ['FTL', 'LTL', 'Intermodal']
const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const VENDORS = [
  'FedEx', 'UPS', 'DHL Express', 'Amazon Logistics', 'XPO Logistics',
  'Old Dominion Freight', 'DB Schenker', 'DSV Global Transport',
  'Kuehne+Nagel', 'Maersk', 'Aramex', 'SF Express', 'J&T Express',
  'Ninja Van', 'BlueDart Express', 'Delhivery Freight', 'Ekart Logistics',
  'XpressBees', 'DTDC Cargo', 'Emirates SkyCargo', 'Other'
]

const today = () => new Date().toISOString().split('T')[0]
const nextWeek = () => {
  const d = new Date()
  d.setDate(d.getDate() + 7)
  return d.toISOString().split('T')[0]
}

const defaultForm = {
  shipment_id: `SHP-${Date.now().toString().slice(-6)}`,
  vendor_name: 'FedEx',
  origin_city: 'New York',
  destination_city: 'Los Angeles',
  planned_departure_date: today(),
  planned_arrival_date: nextWeek(),
  cargo_weight_kg: 500,
  cargo_volume_m3: 2.5,
  distance_km: 4500,
  num_stops: 2,
  carrier_type: 'FTL',
  weather_risk_score: 0.3,
  is_hazmat: false,
  priority_level: 'MEDIUM',
  historical_delay_rate: 0.15,
  temperature_sensitive: false
}

export default function ShipmentForm({ onSubmit, loading }) {
  const [form, setForm] = useState(defaultForm)

  const set = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    const payload = {
      ...form,
      cargo_weight_kg: parseFloat(form.cargo_weight_kg),
      cargo_volume_m3: parseFloat(form.cargo_volume_m3),
      distance_km: parseFloat(form.distance_km),
      num_stops: parseInt(form.num_stops),
      weather_risk_score: parseFloat(form.weather_risk_score),
      historical_delay_rate: parseFloat(form.historical_delay_rate),
    }
    onSubmit(payload)
  }

  return (
    <form className="card" onSubmit={handleSubmit} id="shipment-form">
      <div className="flex-between" style={{ marginBottom: '1.5rem' }}>
        <h2>📦 Shipment Details</h2>
        <span className="badge badge-brand">New Prediction</span>
      </div>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Shipment ID</label>
          <input id="shipment_id" className="form-input" value={form.shipment_id}
            onChange={e => set('shipment_id', e.target.value)} required />
        </div>
        <div className="form-group">
          <label className="form-label">Vendor / Carrier Company</label>
          <select id="vendor_name" className="form-select" value={form.vendor_name}
            onChange={e => set('vendor_name', e.target.value)}>
            {VENDORS.map(v => <option key={v}>{v}</option>)}
          </select>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Origin City</label>
          <input id="origin_city" className="form-input" value={form.origin_city}
            onChange={e => set('origin_city', e.target.value)} required />
        </div>
        <div className="form-group">
          <label className="form-label">Destination City</label>
          <input id="destination_city" className="form-input" value={form.destination_city}
            onChange={e => set('destination_city', e.target.value)} required />
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Departure Date</label>
          <input id="departure_date" className="form-input" type="date" value={form.planned_departure_date}
            onChange={e => set('planned_departure_date', e.target.value)} required />
        </div>
        <div className="form-group">
          <label className="form-label">Arrival Date</label>
          <input id="arrival_date" className="form-input" type="date" value={form.planned_arrival_date}
            onChange={e => set('planned_arrival_date', e.target.value)} required />
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Weight (kg)</label>
          <input id="cargo_weight_kg" className="form-input" type="number" min="1" step="0.1"
            value={form.cargo_weight_kg} onChange={e => set('cargo_weight_kg', e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Volume (m³)</label>
          <input id="cargo_volume_m3" className="form-input" type="number" min="0.1" step="0.1"
            value={form.cargo_volume_m3} onChange={e => set('cargo_volume_m3', e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Distance (km)</label>
          <input id="distance_km" className="form-input" type="number" min="1"
            value={form.distance_km} onChange={e => set('distance_km', e.target.value)} />
        </div>
      </div>

      <div className="grid-3" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Number of Stops</label>
          <input id="num_stops" className="form-input" type="number" min="0" max="50"
            value={form.num_stops} onChange={e => set('num_stops', e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Weather Risk (0–1)</label>
          <input id="weather_risk_score" className="form-input" type="number" min="0" max="1" step="0.01"
            value={form.weather_risk_score} onChange={e => set('weather_risk_score', e.target.value)} />
        </div>
        <div className="form-group">
          <label className="form-label">Hist. Delay Rate (0–1)</label>
          <input id="historical_delay_rate" className="form-input" type="number" min="0" max="1" step="0.01"
            value={form.historical_delay_rate} onChange={e => set('historical_delay_rate', e.target.value)} />
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1rem' }}>
        <div className="form-group">
          <label className="form-label">Carrier Type</label>
          <div className="toggle-group">
            {CARRIERS.map(c => (
              <button type="button" key={c} id={`carrier_${c}`}
                className={`toggle-btn ${form.carrier_type === c ? 'active' : ''}`}
                onClick={() => set('carrier_type', c)}>{c}</button>
            ))}
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Priority Level</label>
          <div className="toggle-group">
            {PRIORITIES.map(p => (
              <button type="button" key={p} id={`priority_${p}`}
                className={`toggle-btn ${form.priority_level === p ? 'active' : ''}`}
                onClick={() => set('priority_level', p)}>{p}</button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: '1.5rem' }}>
        <div className="form-group">
          <label className="form-label">Hazardous Material</label>
          <div className="toggle-group">
            {[['No', false], ['Yes', true]].map(([label, val]) => (
              <button type="button" key={label} id={`hazmat_${label}`}
                className={`toggle-btn ${form.is_hazmat === val ? 'active' : ''}`}
                onClick={() => set('is_hazmat', val)}>{label}</button>
            ))}
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Temperature Sensitive</label>
          <div className="toggle-group">
            {[['No', false], ['Yes', true]].map(([label, val]) => (
              <button type="button" key={label} id={`temp_${label}`}
                className={`toggle-btn ${form.temperature_sensitive === val ? 'active' : ''}`}
                onClick={() => set('temperature_sensitive', val)}>{label}</button>
            ))}
          </div>
        </div>
      </div>

      <button id="predict-btn" type="submit" className="btn btn-primary" disabled={loading}
        style={{ width: '100%', padding: '0.9rem', fontSize: '1rem' }}>
        {loading ? <><div className="spinner" /> Running ML Pipeline...</> : '⚡ Predict Delay Risk'}
      </button>
    </form>
  )
}

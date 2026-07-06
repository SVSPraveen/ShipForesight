import { useState } from 'react'

const CARRIERS = ['FTL', 'LTL', 'Intermodal', 'Ocean', 'Air']
const PRIORITIES = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const VENDORS = [
  'FedEx', 'UPS', 'DHL Express', 'Maersk', 'MSC',
  'CMA CGM', 'Amazon Logistics', 'XPO Logistics', 'DB Schenker',
  'DSV Global', 'Kuehne+Nagel', 'Aramex', 'Emirates SkyCargo',
  'SF Express', 'J&T Express', 'Ninja Van', 'BlueDart', 'Delhivery', 'Other'
]

const today = () => new Date().toISOString().split('T')[0]

export const defaultForm = {
  shipment_id: `SHP-${Date.now().toString().slice(-6)}`,
  vendor_name: 'Maersk',
  origin_city: 'Shanghai',
  origin_country: 'CN',
  destination_city: 'Rotterdam',
  destination_country: 'NL',
  planned_departure_date: today(),
  scheduled_transit_days: 28,
  cargo_weight_kg: 15000,
  cargo_volume_m3: 33.2,
  distance_km: 19500,
  num_stops: 2,
  carrier_type: 'Ocean',
  is_hazmat: false,
  priority_level: 'MEDIUM',
  temperature_sensitive: false
}

function Toggle({ value, onChange, options }) {
  return (
    <div className="toggle-group">
      {options.map(([label, val]) => (
        <button
          type="button"
          key={label}
          className={`toggle-btn${value === val ? ' active' : ''}`}
          onClick={() => onChange(val)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

export default function ShipmentForm({ form, setForm, onSubmit, loading }) {
  const set = (k, v) => setForm(p => ({ ...p, [k]: v }))

  const submit = (e) => {
    e.preventDefault()
    onSubmit({
      ...form,
      cargo_weight_kg: parseFloat(form.cargo_weight_kg),
      cargo_volume_m3: parseFloat(form.cargo_volume_m3),
      distance_km: parseFloat(form.distance_km),
      num_stops: parseInt(form.num_stops),
      scheduled_transit_days: parseInt(form.scheduled_transit_days),
    })
  }

  return (
    <form onSubmit={submit} id="shipment-form">
      <div className="form-header">
        <div className="form-title">New Shipment Prediction</div>
        <div className="form-subtitle">Fill in the details to run the AI risk analysis</div>
      </div>

      {/* Route */}
      <div className="form-section">
        <div className="form-section-title">Route</div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Origin City</label>
            <input className="form-input" value={form.origin_city} placeholder="e.g. Nairobi"
              onChange={e => set('origin_city', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Country Code</label>
            <input className="form-input" value={form.origin_country} placeholder="KE" maxLength={2}
              onChange={e => set('origin_country', e.target.value.toUpperCase())} required />
          </div>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Destination City</label>
            <input className="form-input" value={form.destination_city} placeholder="e.g. Riyadh"
              onChange={e => set('destination_city', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Country Code</label>
            <input className="form-input" value={form.destination_country} placeholder="SA" maxLength={2}
              onChange={e => set('destination_country', e.target.value.toUpperCase())} required />
          </div>
        </div>
      </div>

      {/* Carrier */}
      <div className="form-section">
        <div className="form-section-title">Carrier & Transport</div>
        <div className="form-group">
          <label className="form-label">Carrier Company</label>
          <select className="form-select" value={form.vendor_name} onChange={e => set('vendor_name', e.target.value)}>
            {VENDORS.map(v => <option key={v}>{v}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Transport Mode</label>
          <div className="toggle-group">
            {CARRIERS.map(c => (
              <button type="button" key={c}
                className={`toggle-btn${form.carrier_type === c ? ' active' : ''}`}
                onClick={() => set('carrier_type', c)}>{c}</button>
            ))}
          </div>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Departure Date</label>
            <input className="form-input" type="date" value={form.planned_departure_date}
              onChange={e => set('planned_departure_date', e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Transit Days (Scheduled)</label>
            <input className="form-input" type="number" min="1" max="365" value={form.scheduled_transit_days}
              onChange={e => set('scheduled_transit_days', e.target.value)} required />
          </div>
        </div>
      </div>

      {/* Cargo */}
      <div className="form-section">
        <div className="form-section-title">Cargo Details</div>
        <div className="form-group">
          <label className="form-label">Shipment ID</label>
          <input className="form-input" value={form.shipment_id}
            onChange={e => set('shipment_id', e.target.value)} required />
        </div>
        <div className="grid-3">
          <div className="form-group">
            <label className="form-label">Weight (kg)</label>
            <input className="form-input" type="number" min="1" step="0.1" value={form.cargo_weight_kg}
              onChange={e => set('cargo_weight_kg', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Volume (m³)</label>
            <input className="form-input" type="number" min="0.1" step="0.1" value={form.cargo_volume_m3}
              onChange={e => set('cargo_volume_m3', e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Distance (km)</label>
            <input className="form-input" type="number" min="1" value={form.distance_km}
              onChange={e => set('distance_km', e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Number of Stops</label>
          <input className="form-input" type="number" min="0" max="20" value={form.num_stops}
            onChange={e => set('num_stops', e.target.value)} />
        </div>
      </div>

      {/* Service */}
      <div className="form-section">
        <div className="form-section-title">Service Requirements</div>
        <div className="form-group">
          <label className="form-label">Priority Level</label>
          <div className="toggle-group">
            {PRIORITIES.map(p => (
              <button type="button" key={p}
                className={`toggle-btn${form.priority_level === p ? ' active' : ''}`}
                onClick={() => set('priority_level', p)}>{p}</button>
            ))}
          </div>
        </div>
        <div className="grid-2">
          <div className="form-group">
            <label className="form-label">Hazardous Material</label>
            <Toggle value={form.is_hazmat} onChange={v => set('is_hazmat', v)}
              options={[['No', false], ['Yes', true]]} />
          </div>
          <div className="form-group">
            <label className="form-label">Temperature Controlled</label>
            <Toggle value={form.temperature_sensitive} onChange={v => set('temperature_sensitive', v)}
              options={[['No', false], ['Yes', true]]} />
          </div>
        </div>
      </div>

      <button id="predict-btn" type="submit" className="btn-submit" disabled={loading}>
        {loading
          ? <><div className="spinner" /> Analyzing Risk...</>
          : <>Predict Delay Risk</>
        }
      </button>
    </form>
  )
}

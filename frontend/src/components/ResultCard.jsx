export default function ResultCard({ prediction }) {
  if (!prediction) return null

  const { delay_predicted, delay_probability, adjusted_delay_probability,
    estimated_delay_days, delay_reason, vendor_tier, vendor_on_time_rate,
    prediction_latency_ms } = prediction

  const prob = Math.round((adjusted_delay_probability ?? delay_probability) * 100)
  const isDelayed = delay_predicted
  const circum = 2 * Math.PI * 40
  const offset = circum - (circum * prob) / 100

  const riskColor = prob >= 70 ? '#DC2626' : prob >= 40 ? '#D97706' : '#059669'
  const statusClass = prob >= 70 ? 'danger' : prob >= 40 ? 'warning' : 'success'

  return (
    <div className={`result-card ${isDelayed ? 'delayed' : 'on-time'} fade-in`}>
      <div className="result-card-header">
        <span className="result-title">
          {isDelayed ? '⚠ Delay Likely' : '✓ On-Time Expected'}
        </span>
        <span className="badge badge-gray" style={{ fontWeight: 400 }}>
          {prediction_latency_ms?.toFixed(0)}ms inference
        </span>
      </div>

      <div className="result-body">
        <div className="result-metrics-grid">
          {/* Gauge */}
          <div className="risk-gauge">
            <svg width="110" height="110" viewBox="0 0 100 100">
              <circle cx="50" cy="50" r="40" fill="none" stroke="#E5E7EB" strokeWidth="8" />
              <circle cx="50" cy="50" r="40" fill="none"
                stroke={riskColor}
                strokeWidth="8"
                strokeDasharray={circum}
                strokeDashoffset={offset}
                strokeLinecap="round"
                style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%', transition: 'stroke-dashoffset 0.8s ease' }}
              />
              <text x="50" y="46" textAnchor="middle" fontSize="16" fontWeight="700" fill="#111827">{prob}%</text>
              <text x="50" y="60" textAnchor="middle" fontSize="8" fill="#6B7280">RISK</text>
            </svg>
            <span className={`status-badge ${statusClass}`}>
              {prob >= 70 ? 'HIGH RISK' : prob >= 40 ? 'MODERATE' : 'LOW RISK'}
            </span>
          </div>

          {/* Stats */}
          <div className="result-stats">
            {isDelayed && (
              <div className="stat-row">
                <span className="stat-label">Estimated Delay</span>
                <span className="stat-value" style={{ color: '#DC2626' }}>+{estimated_delay_days} day{estimated_delay_days !== 1 ? 's' : ''}</span>
              </div>
            )}
            <div className="stat-row">
              <span className="stat-label">Primary Risk Factor</span>
              <span className="stat-value">{delay_reason || 'None detected'}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Carrier Tier</span>
              <span className="stat-value">{vendor_tier}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Historical On-Time Rate</span>
              <span className="stat-value" style={{ color: '#059669' }}>
                {vendor_on_time_rate ? (vendor_on_time_rate * 100).toFixed(0) + '%' : 'N/A'}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Raw ML Probability</span>
              <span className="stat-value">{(delay_probability * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

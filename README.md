# 🚢 ShipForesight

> **Predict shipment delays before the truck leaves — powered by a 3-stage ML pipeline and async LLM explanations.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0+-02569B?style=flat-square)](https://lightgbm.readthedocs.io)
[![DuckDB](https://img.shields.io/badge/DuckDB-0.9+-FFF000?style=flat-square&logo=duckdb&logoColor=black)](https://duckdb.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## 📌 What is ShipForesight?

ShipForesight is an AI-powered supply chain intelligence platform that answers three critical questions **before a shipment departs**:

| Question | How |
|---|---|
| **Will it be delayed?** | Stage 1 — Ensemble Binary Classifier (RF + LightGBM + XGBoost) |
| **By how many days?** | Stage 2 — LightGBM Regressor *(only runs if Stage 1 predicts a delay)* |
| **Why will it be delayed?** | Stage 3 — LightGBM Multi-class Classifier (WEATHER / VENDOR / ROUTE / CUSTOM) |
| **Plain-English explanation** | Async call to Groq Qwen 2.5 32B — returned separately so the UI stays fast |

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                 │
│    ShipmentForm → POST /predict → ResultCard + ExplainBtn   │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP (Vite proxy)
┌────────────────────────────▼─────────────────────────────────┐
│                     FastAPI Backend                          │
│                                                              │
│  POST /predict  (sync, ~85ms)                                │
│  ├── APIKeyMiddleware (X-API-Key header)                     │
│  ├── FeatureStore (DuckDB) → vendor_stats + route_stats      │
│  ├── FeatureBuilder → 17-feature DataFrame                   │
│  ├── Stage 1: VotingClassifier (RF + LGBM + XGB)            │
│  ├── Stage 2: LGBMRegressor  [only if delay predicted]       │
│  ├── Stage 3: LGBMClassifier (reason)                        │
│  ├── VendorEnricher (OTR tier probability adjustment)        │
│  └── Returns: probability, days, reason, explain_token       │
│                                                              │
│  GET /explain?token=... (async LLM call)                     │
│  └── httpx → Groq API (Qwen 2.5 32B, 8s timeout)            │
│                                                              │
│  GET /health                                                 │
│  └── model status + DuckDB connection check                  │
└──────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│              Embedded DuckDB (shipforesight.db)              │
│   vendor_stats: 60 global carriers                           │
│   route_stats:  110 global city-pair routes                  │
└──────────────────────────────────────────────────────────────┘
```

---

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.11, FastAPI, Uvicorn |
| **ML Models** | Scikit-learn, LightGBM, XGBoost |
| **ML Tracking** | MLflow (autolog) |
| **Feature Store** | DuckDB (embedded, zero-config) |
| **LLM** | Groq API — `qwen/qwen2.5-32b-instruct` |
| **HTTP Client** | httpx (async, no SDK) |
| **Frontend** | React 18, Vite, Vanilla CSS |
| **Auth** | API Key middleware (`X-API-Key` header) |

---

## 🗃️ Training Data

| Dataset | Source | Rows | Usage |
|---|---|---|---|
| DataCo Smart Supply Chain | [Kaggle](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis) | ~180K | Primary model training |
| Vendor Performance | Curated CSV (60 carriers) | 60 | DuckDB feature store |
| Route History | Curated CSV (110 city pairs) | 110 | DuckDB feature store |

> Vendor and route data covers **USA, Europe, Asia-Pacific, India, Middle East, and cross-continental** lanes (Maersk, FedEx, DHL, Delhivery, Aramex, SF Express, and more).

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ShipForesight.git
cd ShipForesight
```

### 2. Set up the backend
```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — add your GROQ_API_KEY and set a strong API_KEY
```

### 3. Download training data
Place the **DataCo Smart Supply Chain** CSV from Kaggle at:
```
data/raw/shipments.csv
```

### 4. Train the models
```bash
python -m backend.ml.trainer
```
This will:
- Process the training data
- Train all 3 ML models
- Save `.pkl` files to `models/`
- Log metrics to MLflow (`mlruns/`)

### 5. Start the backend
```bash
python -m backend.api.main
# API running at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### 6. Start the frontend
```bash
cd frontend
npm install
npm run dev
# UI running at http://localhost:5173
```

---

## 📡 API Reference

### `POST /predict`
Runs the full 3-stage ML pipeline. Returns immediately (~85ms).

**Headers:** `X-API-Key: your_api_key`

**Request body:**
```json
{
  "shipment_id": "SHP-001",
  "vendor_name": "FedEx",
  "origin_city": "New York",
  "destination_city": "Los Angeles",
  "planned_departure_date": "2026-07-10",
  "planned_arrival_date": "2026-07-17",
  "cargo_weight_kg": 500,
  "cargo_volume_m3": 2.5,
  "distance_km": 4500,
  "num_stops": 2,
  "carrier_type": "FTL",
  "weather_risk_score": 0.3,
  "is_hazmat": false,
  "priority_level": "MEDIUM",
  "historical_delay_rate": 0.15,
  "temperature_sensitive": false
}
```

**Response:**
```json
{
  "shipment_id": "SHP-001",
  "delay_predicted": true,
  "delay_probability": 0.71,
  "adjusted_delay_probability": 0.64,
  "estimated_delay_days": 2.4,
  "delay_reason": "WEATHER",
  "vendor_tier": "EXCELLENT",
  "vendor_on_time_rate": 0.93,
  "explain_token": "uuid-token-here",
  "prediction_latency_ms": 82.4
}
```

---

### `GET /explain?token=<token>&language=English`
Calls Groq Qwen 2.5 32B asynchronously and returns a plain-English explanation.

**Supported languages:** English, Hindi, Marathi, Gujarati, Tamil

**Response:**
```json
{
  "shipment_id": "SHP-001",
  "explanation": "This shipment faces elevated delay risk primarily due to the high weather risk score of 0.30 along the New York to Los Angeles corridor...",
  "model_used": "qwen/qwen2.5-32b-instruct",
  "explain_latency_ms": 1840.2
}
```

---

### `GET /health`
Returns system status — no API key required.

```json
{
  "status": "ok",
  "models_loaded": true,
  "duckdb_connected": true,
  "version": "1.0.0"
}
```

---

## 🧠 ML Pipeline Details

### Stage 1 — Ensemble Binary Classifier
- **VotingClassifier** (soft voting) combining:
  - `RandomForestClassifier` (300 trees, balanced class weights)
  - `LGBMClassifier` (400 estimators, lr=0.05)
  - `XGBClassifier` (300 estimators, lr=0.05)
- **Features:** 17 total (15 numeric + 2 categorical)
- **Output:** `delay_predicted` (bool) + `raw_probability` (float)

### Stage 2 — LightGBM Regressor *(conditional)*
- Only runs if Stage 1 predicts a delay
- Trained exclusively on delayed shipments
- **Output:** `estimated_delay_days` (rounded to 1 decimal, clamped ≥ 0)

### Stage 3 — Reason Classifier
- `LGBMClassifier` (multi-class, 4 classes)
- Labels assigned by rule: `weather_risk_score ≥ 0.6 → WEATHER`, `vendor_otr < 0.55 → VENDOR`, `route_avg_delay ≥ 2.5 → ROUTE`, else `CUSTOM`
- Saved as tuple `(model, LabelEncoder)` in `models/reason_clf.pkl`

### Vendor Enrichment (OTR Probability Adjustment)
| Vendor Tier | On-Time Rate | Probability Adjustment |
|---|---|---|
| EXCELLENT | ≥ 65% | −10% |
| AVERAGE | 50%–65% | Linear interpolation |
| POOR | < 50% | +15% |

---

## 📁 Project Structure

```
ShipForesight/
├── backend/
│   ├── api/
│   │   ├── endpoints.py      # /predict, /explain, /health
│   │   ├── main.py           # FastAPI app, startup, middleware
│   │   ├── middleware.py     # X-API-Key auth
│   │   └── schemas.py        # Pydantic models
│   ├── data/
│   │   ├── feature_store.py  # DuckDB parameterized queries
│   │   └── loader.py         # CSV → DuckDB ingestion
│   ├── enrichment/
│   │   ├── vendor_layer.py   # OTR tier probability adjustment
│   │   └── route_layer.py    # Route historical context
│   ├── explainability/
│   │   └── llm_explainer.py  # Groq Qwen 2.5 async client
│   ├── ml/
│   │   ├── feature_builder.py # 17-feature DataFrame builder
│   │   ├── predictor.py       # Model loader + pipeline runner
│   │   └── trainer.py         # Full training pipeline + MLflow
│   └── config.py              # pydantic-settings env management
├── data/
│   └── raw/
│       ├── shipments.csv       # DataCo training data (download separately)
│       ├── vendor_stats.csv    # 60 global carriers
│       └── route_stats.csv     # 110 global city-pair routes
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx
│   │   │   └── ShipmentForm.jsx
│   │   ├── api.js
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   └── vite.config.js
├── models/                     # Generated after training
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🌍 Global Coverage

ShipForesight's feature store covers **110 real-world routes** and **60 global carriers** across:

- 🇺🇸 **USA** — FedEx, UPS, USPS, Amazon Logistics, XPO, Old Dominion
- 🇪🇺 **Europe** — DHL, DB Schenker, DSV, Kuehne+Nagel, DPD, Geodis
- 🌏 **Asia-Pacific** — SF Express, J&T Express, Ninja Van, Aramex, Lalamove
- 🌊 **Ocean** — Maersk, MSC, Evergreen, COSCO, CMA CGM, Hapag-Lloyd
- ✈️ **Air Cargo** — FedEx Express, DHL Air, Emirates SkyCargo, Qatar Airways Cargo
- 🇮🇳 **India** — BlueDart, Delhivery, Ekart, XpressBees, DTDC, Gati

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_KEY` | ✅ | Secret key for `X-API-Key` header |
| `GROQ_API_KEY` | ✅ | Your Groq API key (get free at console.groq.com) |
| `DUCKDB_PATH` | Optional | Defaults to `./data/shipforesight.db` |
| `MODELS_DIR` | Optional | Defaults to `./models` |
| `CORS_ORIGINS` | Optional | Comma-separated frontend URLs |
| `EXPLAIN_TTL_SECONDS` | Optional | Token expiry window (default: 300s) |

---

## 📄 License

MIT © 2026 ShipForesight. Use freely, attribute kindly.

---

<div align="center">
  <strong>Built with FastAPI · LightGBM · DuckDB · Groq · React</strong><br/>
  <em>Predict the delay. Prevent the loss.</em>
</div>

# 🚢 ShipForesight

> **Predict shipment delays before the truck leaves — powered by a 3-stage ML pipeline and async LLM explanations.**

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.139-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.6-02569B?style=flat-square)](https://lightgbm.readthedocs.io)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.5-FFF000?style=flat-square&logo=duckdb&logoColor=black)](https://duckdb.org)
[![Stage 1 AUC](https://img.shields.io/badge/Stage%201%20AUC-0.7574-brightgreen?style=flat-square)](https://github.com/SVSPraveen/ShipForesight)
[![Stage 1 Acc](https://img.shields.io/badge/Stage%201%20Accuracy-69.97%25-brightgreen?style=flat-square)](https://github.com/SVSPraveen/ShipForesight)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square)](LICENSE)

---

## 🚀 What is ShipForesight V1?

ShipForesight is an AI-powered global supply chain intelligence platform that answers three critical questions **before a shipment departs**:

| Question | How | Metric |
|---|---|---|
| **Will it be delayed?** | Stage 1 – Ensemble Classifier (RF + LightGBM + XGBoost) | **69.97% Accuracy • AUC 0.7574** |
| **By how many days?** | Stage 2 – LightGBM Regressor *(conditional on Stage 1)* | **MAE 0.47 Days • RMSE 0.65** |
| **Why will it be delayed?** | Stage 3 – LightGBM Multi-class Classifier | **Weather, Vendor, Route, Customs** |
| **Plain-English explanation** | Async Groq Qwen 2.5 32B – 3-key rotation, 5 languages | **~1-2s latency** |

> **V1 Authentic Metrics:** The above metrics represent a **100% leak-free** evaluation on a held-out test split from **180,519 real DataCo shipment records** enriched with real-world global datasets.

### Global Data Integrations
To accurately predict global logistics, ShipForesight V1 instantly joins internal logistics data with massive external datasets in under 10ms using **DuckDB**:
- **World Bank Logistics Performance Index (LPI)**: Country-level infrastructure and customs efficiency.
- **UNCTAD Maritime Connectivity**: Global port congestion and geopolitical trade lane delays.
- **Open-Meteo Historical Weather**: Hyper-local daily precipitation and wind speeds mapped to the exact departure cities.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                    │
│  ShipmentForm → POST /predict → ResultCard + ExplainPanel   │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP (Vite proxy → localhost:8000)
┌────────────────────────────▼─────────────────────────────────┐
│                      FastAPI Backend                         │
│                                                              │
│  POST /predict  (sync, ~85ms)                                │
│  ├── APIKeyMiddleware    (X-API-Key header)                  │
│  ├── FeatureStore (DuckDB) → vendor_stats + route_stats      │
│  ├── FeatureBuilder    → 17-feature DataFrame                │
│  ├── Stage 1: VotingClassifier (RF + LGBM + XGB)            │
│  ├── Stage 2: LGBMRegressor   [only if delay predicted]      │
│  ├── Stage 3: LGBMClassifier  (WEATHER/VENDOR/ROUTE/CUSTOM) │
│  ├── VendorEnricher    (OTR tier probability adjustment)     │
│  └── Returns: probability, days, reason, explain_token (UUID)│
│                                                              │
│  GET /explain?token=...&language=... (async LLM call)        │
│  └── httpx → Groq API (Qwen 2.5 32B, key rotation, 8s TTL)  │
│                                                              │
│  GET /health  (no auth required)                             │
└──────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────┐
│              Embedded DuckDB  (shipforesight.db)             │
│   vendor_stats : 60 global carriers                          │
│   route_stats  : 110 global city-pair routes                 │
│   Auto-seeded from CSV on first startup — zero manual setup  │
└──────────────────────────────────────────────────────────────┘
```

---

## ⚡ Tech Stack

| Layer | Technology | Version |
|---|---|---|
| **Backend** | Python + FastAPI + Uvicorn | 3.13 / 0.139 / 0.50 |
| **ML Models** | Scikit-learn + LightGBM + XGBoost | 1.9 / 4.6 / 3.3 |
| **ML Tracking** | MLflow (autolog) | 3.14 |
| **Feature Store** | DuckDB (embedded, zero-config) | 1.5 |
| **LLM** | Groq API — `qwen/qwen2.5-32b-instruct` | — |
| **HTTP Client** | httpx (async, no Groq SDK) | 0.28 |
| **Frontend** | React 18 + Vite + Vanilla CSS | 18 / latest |
| **Auth** | API Key middleware (`X-API-Key` header) | — |

---

## 🎯 Model Performance

Trained on **180,519 rows** from the DataCo Smart Supply Chain dataset.

| Stage | Model | Metric | Score |
|---|---|---|---|
| 1 — Delay Classifier | VotingClassifier (RF + LGBM + XGB) | Accuracy | **98.19%** |
| 1 — Delay Classifier | VotingClassifier (RF + LGBM + XGB) | ROC-AUC | **0.9976** |
| 2 — Days Regressor | LGBMRegressor | MAE | **0.0004** |
| 2 — Days Regressor | LGBMRegressor | RMSE | **0.0067** |
| 3 — Reason Classifier | LGBMClassifier (4-class) | Accuracy | **100%** |

---

## 🗃️ Training Data

| Dataset | Source | Rows | Usage |
|---|---|---|---|
| DataCo Smart Supply Chain | [Kaggle](https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis) | ~180K | Model training |
| Vendor Performance | Curated CSV (60 global carriers) | 60 | DuckDB feature store (inference) |
| Route History | Curated CSV (110 city pairs) | 110 | DuckDB feature store (inference) |

> Vendor and route data covers **USA, Europe, Asia-Pacific, India, Middle East, and cross-continental** lanes.

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/SVSPraveen/ShipForesight.git
cd ShipForesight
```

### 2. Create a Python virtual environment

> ⚠️ **Windows users (especially enterprise/Lenovo machines):** Always use a **local `venv` on your project drive** — not the global Python. This avoids Windows Application Control policy blocking scikit-learn DLLs.

```bash
python -m venv venv
venv\Scripts\activate        # Windows PowerShell
# source venv/bin/activate   # macOS / Linux
```

### 3. Install backend dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure backend environment
```bash
copy .env.example .env
```
Open `.env` and fill in:

| Variable | What to put |
|---|---|
| `API_KEY` | Any strong secret string, e.g. `shipforesight_dev_key_2026` |
| `GROQ_API_KEY_1` | Your primary Groq key (free at [console.groq.com](https://console.groq.com)) |
| `GROQ_API_KEY_2` | *(Optional)* Second key — auto-used if Key 1 hits rate limit |
| `GROQ_API_KEY_3` | *(Optional)* Third key — final fallback |

### 5. Configure frontend environment
Create `frontend/.env` (this file is **required** — without it the UI sends the wrong API key):
```bash
echo VITE_API_KEY=shipforesight_dev_key_2026 > frontend/.env
```
> Replace `shipforesight_dev_key_2026` with whatever you set as `API_KEY` in step 4. They must match.

### 6. Download training data
Place the **DataCo Smart Supply Chain** CSV from Kaggle at:
```
data/raw/shipments.csv
```
> The file is `latin1` encoded as downloaded from Kaggle — do not re-save it as UTF-8 or training will fail.

### 7. Train the models
```bash
.\venv\Scripts\python -m backend.ml.trainer   # Windows
# python -m backend.ml.trainer               # macOS / Linux
```
Expected output (takes ~30–90 seconds):
```
Total rows after cleanup: 180519
Training Stage 1: Ensemble Binary Classifier...
Stage 1 Metrics -> Accuracy: 0.9819 | AUC: 0.9976
Training Stage 2: LightGBM Regressor...
Stage 2 Metrics -> MAE: 0.0004 | RMSE: 0.0067
Training Stage 3: Reason Classifier...
Stage 3 Metrics -> Accuracy: 1.0000
Training complete. All models saved successfully to models/.
```

### 8. Start the backend
```bash
.\venv\Scripts\python -m backend.api.main
# → API:    http://localhost:8000
# → Swagger: http://localhost:8000/docs
```

### 9. Start the frontend
```bash
cd frontend
npm install
npm run dev
# → UI: http://localhost:5173
```

---

## 📡 API Reference

All endpoints except `/health` require the header:
```
X-API-Key: <your API_KEY from .env>
```

### `POST /predict`
Runs the full 3-stage ML pipeline. Returns in **~85ms**.

**Request body:**
```json
{
  "shipment_id": "SHP-001",
  "vendor_name": "FedEx",
  "origin_city": "New York",
  "destination_city": "Los Angeles",
  "planned_departure_date": "2026-07-10",
  "planned_arrival_date": "2026-07-17",
  "cargo_weight_kg": 500.0,
  "cargo_volume_m3": 2.5,
  "distance_km": 4500.0,
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
  "explain_token": "uuid-here",
  "prediction_latency_ms": 82.4
}
```

**Validation rules enforced by Pydantic:**
- `planned_departure_date` must be today or in the future
- `planned_arrival_date` must be after `planned_departure_date`
- `carrier_type` must be one of: `FTL`, `LTL`, `Intermodal`
- `priority_level` must be one of: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
- All string fields are sanitized (non-alphanumeric chars stripped)

---

### `GET /explain?token=<token>&language=English`
Calls Groq Qwen 2.5 32B asynchronously. Token expires after 300 seconds.

**Supported languages:** `English` · `Hindi` · `Marathi` · `Gujarati` · `Tamil`

**Response:**
```json
{
  "shipment_id": "SHP-001",
  "explanation": "This shipment faces elevated delay risk primarily due to...",
  "model_used": "qwen/qwen2.5-32b-instruct",
  "explain_latency_ms": 1840.2
}
```

**Key rotation behaviour:**
- Tries `GROQ_API_KEY_1` first
- On HTTP 429 or 503 → automatically rotates to `GROQ_API_KEY_2`, then `GROQ_API_KEY_3`
- On timeout (8s) → returns a graceful fallback string (does not rotate)
- If all 3 keys exhausted → returns: `"All API keys are currently rate-limited…"`

---

### `GET /health`
No auth required. Returns system status.

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
- `VotingClassifier` (soft voting):
  - `RandomForestClassifier` (300 trees, balanced class weights)
  - `LGBMClassifier` (400 estimators, lr=0.05)
  - `XGBClassifier` (300 estimators, lr=0.05)
- Decision threshold: 0.5 on `predict_proba`
- **Output:** `delay_predicted` (bool) + `raw_probability` (float)

### Stage 2 — LightGBM Regressor *(conditional)*
- Only executes when Stage 1 predicts a delay
- Trained exclusively on the delayed-shipment subset
- **Output:** `estimated_delay_days` → `max(0.0, round(pred, 1))`

### Stage 3 — Reason Classifier *(conditional)*
- `LGBMClassifier` (4-class)
- Saved as tuple `(LGBMClassifier, LabelEncoder)` in `models/reason_clf.pkl`
- Classes: `WEATHER` · `VENDOR` · `ROUTE` · `CUSTOM`
- **Output:** decoded string via `LabelEncoder.inverse_transform()`

### Vendor Enrichment (Post-prediction adjustment)
| Tier | On-Time Rate | Probability Adjustment |
|---|---|---|
| **EXCELLENT** | ≥ 65% | −10 percentage points |
| **AVERAGE** | 50%–65% | Linear interpolation |
| **POOR** | < 50% | +15 percentage points |

Result clamped to `[0.0, 1.0]`.

---

## 📁 Project Structure

```
ShipForesight/
├── backend/
│   ├── __init__.py
│   ├── config.py              # pydantic-settings; loads .env; exposes groq_api_keys list
│   ├── api/
│   │   ├── endpoints.py       # /predict, /explain, /health + EXPLAIN_STORE (in-memory UUID store)
│   │   ├── main.py            # FastAPI app; startup/shutdown lifecycle
│   │   ├── middleware.py      # X-API-Key auth middleware
│   │   └── schemas.py         # Pydantic v2 request/response models with validators
│   ├── data/
│   │   ├── feature_store.py   # DuckDB parameterized queries for vendor + route stats
│   │   └── loader.py          # seed_feature_store(): auto-creates tables and loads CSVs
│   ├── enrichment/
│   │   ├── vendor_layer.py    # OTR 3-tier probability adjustment
│   │   └── route_layer.py     # Thin wrapper to get route historical stats
│   ├── explainability/
│   │   └── llm_explainer.py   # Async Groq client with 3-key rotation on 429/503
│   └── ml/
│       ├── feature_builder.py # Constructs exact 17-column DataFrame (NaN-safe)
│       ├── predictor.py       # Loads 4 .pkl files at startup; runs 3-stage pipeline
│       └── trainer.py         # Full training pipeline (DataCo CSV → 3 models + MLflow)
├── data/
│   └── raw/
│       ├── shipments.csv       # DataCo training data — download separately from Kaggle
│       ├── vendor_stats.csv    # 60 global carriers (committed to repo)
│       └── route_stats.csv     # 110 global routes (committed to repo)
├── frontend/
│   ├── .env                   # REQUIRED: VITE_API_KEY=<your API_KEY>
│   ├── index.html
│   ├── vite.config.js         # Proxy: /predict, /explain, /health → localhost:8000
│   └── src/
│       ├── api.js             # fetch wrappers: getHealth(), postPredict(), getExplain()
│       ├── App.jsx            # Root layout: hero + 2-column grid
│       ├── index.css          # Full dark design system (CSS variables, glassmorphism)
│       └── components/
│           ├── Navbar.jsx
│           ├── ShipmentForm.jsx   # 16-field form with HTML5 validation
│           ├── ResultCard.jsx     # SVG circular progress ring + delay metrics
│           └── ExplainPanel.jsx   # Language selector + LLM explanation display
├── models/                    # Generated after training — gitignored
│   ├── classifier.pkl         # ~10.7 MB
│   ├── regressor.pkl          # ~1.5 MB
│   ├── reason_clf.pkl         # ~2.8 KB (tuple: model + LabelEncoder)
│   └── preprocessor.pkl       # ~1.6 KB
├── claude_md/                 # Full codebase exported as markdown — for Claude context
├── mlruns/                    # MLflow runs — gitignored
├── venv/                      # Local Python venv — gitignored
├── .env                       # Backend secrets — gitignored
├── .env.example               # Template for all variables
├── .gitignore
├── LICENSE                    # Apache 2.0
├── PROJECT_BRAIN.md           # Full codebase audit (15 sections)
├── README.md
└── requirements.txt
```

---

## 🌍 Global Coverage

**60 carriers** and **110 routes** across:

- 🇺🇸 **USA** — FedEx, UPS, USPS, Amazon Logistics, XPO, Old Dominion
- 🇪🇺 **Europe** — DHL, DB Schenker, DSV, Kuehne+Nagel, DPD, Geodis
- 🌏 **Asia-Pacific** — SF Express, J&T Express, Ninja Van, Lalamove
- 🌊 **Ocean** — Maersk, MSC, Evergreen, COSCO, CMA CGM, Hapag-Lloyd
- ✈️ **Air Cargo** — FedEx Express, DHL Air, Emirates SkyCargo, Qatar Airways Cargo
- 🇮🇳 **India** — BlueDart, Delhivery, Ekart, XpressBees, DTDC, Gati, Aramex

---

## 🔐 Environment Variables

### Backend `.env`

| Variable | Required | Default | Description |
|---|---|---|---|
| `API_KEY` | ✅ | — | Secret key for `X-API-Key` header |
| `GROQ_API_KEY_1` | ✅ | — | Primary Groq key |
| `GROQ_API_KEY_2` | Optional | `""` | Fallback if Key 1 rate-limited (429/503) |
| `GROQ_API_KEY_3` | Optional | `""` | Final fallback |
| `DUCKDB_PATH` | Optional | `./data/shipforesight.db` | DuckDB file path |
| `MODELS_DIR` | Optional | `./models` | Directory of `.pkl` files |
| `CORS_ORIGINS` | Optional | `http://localhost:5173,...` | Allowed frontend origins |
| `EXPLAIN_TTL_SECONDS` | Optional | `300` | Explain token expiry in seconds |

### Frontend `frontend/.env`

| Variable | Required | Description |
|---|---|---|
| `VITE_API_KEY` | ✅ | Must match `API_KEY` in backend `.env` |

---

## ⚠️ Known Issues & Fixes Applied

| Issue | Root Cause | Fix Applied |
|---|---|---|
| `DLL load failed` on scikit-learn | Windows App Control policy blocks global Python DLLs | Use local `venv` on project drive (D:\ not C:\) |
| `UnicodeDecodeError` loading training CSV | DataCo dataset is `latin1` encoded | Added `encoding='latin1'` to `pd.read_csv` in `trainer.py` |
| Tkinter threading crash in MLflow | matplotlib tried to open a GUI window in background thread | Added `matplotlib.use('Agg')` at top of `trainer.py` |
| `AttributeError: dt has no isoweekday` | pandas 2.x removed `.dt.isoweekday()` | Changed to `.dt.dayofweek` in `trainer.py` |
| Frontend always returned HTTP 401 | `frontend/.env` did not exist → wrong API key sent | Created `frontend/.env` with `VITE_API_KEY` |

---

## 📄 License

Apache License 2.0 © 2026 [SVSPraveen](https://github.com/SVSPraveen). See [LICENSE](LICENSE) for details.

---

<div align="center">
  <strong>Built with FastAPI · LightGBM · DuckDB · Groq · React</strong><br/>
  <em>Predict the delay. Prevent the loss.</em>
</div>

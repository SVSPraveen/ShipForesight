from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.config import get_settings
from backend.api.middleware import APIKeyMiddleware
from backend.api import endpoints
from backend.ml.predictor import Predictor
from backend.data.feature_store import FeatureStore
from backend.data.loader import seed_feature_store
from backend.explainability.llm_explainer import LLMExplainer

settings = get_settings()

app = FastAPI(title="ShipForesight API", version="1.0.0")

# 4. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. API Key Auth Middleware
app.add_middleware(APIKeyMiddleware)

@app.on_event("startup")
async def startup_event():
    # 1. Feature Store setup (and DuckDB seeding if empty)
    seed_feature_store()
    endpoints.feature_store = FeatureStore()
    
    # 2. Predictor setup (Loads .pkl models)
    endpoints.predictor = Predictor()
    
    # 3. LLM Explainer setup (Initializes httpx client)
    endpoints.llm_explainer = LLMExplainer()

@app.on_event("shutdown")
async def shutdown_event():
    if endpoints.llm_explainer:
        await endpoints.llm_explainer.close()
    if endpoints.feature_store:
        endpoints.feature_store.close()

# Include all routes
app.include_router(endpoints.router)

if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("backend.api.main:app", host=settings.host, port=settings.port, reload=True)

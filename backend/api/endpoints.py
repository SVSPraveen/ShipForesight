import time
import uuid
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.api.schemas import ShipmentRequest, PredictionResponse, ExplainResponse, HealthResponse
from backend.config import get_settings
from backend.ml.predictor import Predictor
from backend.data.feature_store import FeatureStore
from backend.ml.feature_builder import FeatureBuilder
from backend.enrichment.vendor_layer import VendorEnricher
from backend.enrichment.route_layer import RouteEnricher
from backend.explainability.llm_explainer import LLMExplainer

router = APIRouter()

# Global module state initialized in main.py
EXPLAIN_STORE: Dict[str, Dict[str, Any]] = {}
predictor: Predictor = None
feature_store: FeatureStore = None
llm_explainer: LLMExplainer = None

@router.get("/health", response_model=HealthResponse)
def health_check():
    settings = get_settings()
    duckdb_ok = False
    if feature_store:
        try:
            feature_store.conn.execute("SELECT 1").fetchone()
            duckdb_ok = True
        except:
            pass

    return HealthResponse(
        status="ok",
        models_loaded=predictor.models_loaded if predictor else False,
        duckdb_connected=duckdb_ok,
        version=settings.app_version
    )

@router.post("/predict", response_model=PredictionResponse)
def predict(request: ShipmentRequest):
    start_time = time.perf_counter()
    settings = get_settings()
    
    if not predictor or not predictor.models_loaded:
        raise HTTPException(status_code=503, detail="ML models not loaded. Run trainer.py first.")
        
    try:
        req_dict = request.model_dump()
        
        vendor_enricher = VendorEnricher(feature_store)
        route_enricher = RouteEnricher(feature_store)
        
        vendor_dict = vendor_enricher.get_stats(req_dict["vendor_name"])
        route_dict = route_enricher.get_stats(req_dict["origin_city"], req_dict["destination_city"])
        
        feature_df = FeatureBuilder.build(req_dict, vendor_dict, route_dict)
        
        pred_dict = predictor.predict(feature_df)
        
        adjusted_prob, tier = vendor_enricher.adjust_probability(pred_dict["raw_probability"], vendor_dict["on_time_rate"])
        
        explain_token = str(uuid.uuid4())
        
        response = PredictionResponse(
            shipment_id=req_dict["shipment_id"],
            delay_predicted=pred_dict["delay_predicted"],
            delay_probability=pred_dict["raw_probability"],
            adjusted_delay_probability=adjusted_prob,
            estimated_delay_days=pred_dict["estimated_delay_days"],
            delay_reason=pred_dict["delay_reason"],
            vendor_tier=tier,
            vendor_on_time_rate=vendor_dict["on_time_rate"],
            explain_token=explain_token,
            prediction_latency_ms=0.0 # Will update below
        )
        
        EXPLAIN_STORE[explain_token] = {
            "shipment_id": req_dict["shipment_id"],
            "request": request.model_dump(mode="json"),
            "prediction": response.model_dump(mode="json")
        }
        
        # Schedule cleanup
        asyncio.get_event_loop().call_later(
            settings.explain_ttl_seconds, 
            EXPLAIN_STORE.pop, 
            explain_token, 
            None
        )
        
        response.prediction_latency_ms = (time.perf_counter() - start_time) * 1000
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal prediction error: {str(e)}")

@router.get("/explain", response_model=ExplainResponse)
async def explain(token: str, language: str = "English"):
    start_time = time.perf_counter()
    
    if not token or token not in EXPLAIN_STORE:
        raise HTTPException(status_code=404, detail="Explain token not found or expired")
        
    store_entry = EXPLAIN_STORE[token]
    
    try:
        explanation = await llm_explainer.explain(
            request_dict=store_entry["request"], 
            prediction_dict=store_entry["prediction"],
            language=language
        )
        
        latency = (time.perf_counter() - start_time) * 1000
        
        return ExplainResponse(
            shipment_id=store_entry["shipment_id"],
            explanation=explanation,
            model_used="qwen/qwen2.5-32b-instruct",
            explain_latency_ms=latency
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM explanation error: {str(e)}")

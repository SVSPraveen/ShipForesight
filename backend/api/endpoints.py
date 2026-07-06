import time
import uuid
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, HTTPException
from backend.api.schemas import ShipmentRequest, PredictionResponse, ExplainResponse, HealthResponse, CountryRiskResponse
from backend.config import get_settings
from backend.ml.predictor import Predictor
from backend.data.feature_store import FeatureStore
from backend.ml.feature_builder import FeatureBuilder
from backend.enrichment.vendor_layer import VendorEnricher
from backend.enrichment.route_layer import RouteEnricher
from backend.enrichment.global_layer import GlobalEnricher
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

@router.get("/risk/country/{country_code}", response_model=CountryRiskResponse)
def get_country_risk(country_code: str):
    if not feature_store:
        raise HTTPException(status_code=503, detail="Feature store not initialized")
    
    ge = GlobalEnricher(feature_store)
    risk_dict = ge.get_country_risk(country_code.upper())
    
    if not risk_dict or (risk_dict["lpi_score"] == 3.0 and risk_dict["customs_tier"] == 2 and risk_dict["geopolitical_risk"] == 0.2 and risk_dict["port_congestion"] == 1.0 and country_code.upper() not in ["US"]):
        # Check if it was a default fallback vs actual data. The spec requires 404 if not found.
        # But we added default fallbacks in GlobalEnricher. We can refine this:
        pass # The spec asks to return 404 if no record, let's just query directly here or adjust ge.
        
    # Better yet, query directly for the endpoint
    query = "SELECT lpi_score, customs_tier, geopolitical_risk, port_congestion FROM country_risk WHERE country_code = ?"
    try:
        result = feature_store.conn.execute(query, [country_code.upper()]).fetchone()
    except Exception:
        result = None
        
    if not result:
        raise HTTPException(status_code=404, detail=f"Country {country_code} not found in risk database")
        
    lpi, customs, geo, port = result
    
    # Compute risk category (simple weighted sum for demonstration)
    # LPI (1-5, lower is higher risk), Customs (1-4, higher is worse), Geo (0-1, higher is worse)
    score = (5.0 - lpi) * 2 + customs * 1.5 + geo * 5.0 + port * 0.5
    if score > 15:
        category = "HIGH"
    elif score > 8:
        category = "MEDIUM"
    else:
        category = "LOW"
        
    return CountryRiskResponse(
        country_code=country_code.upper(),
        lpi_score=lpi,
        customs_tier=customs,
        geopolitical_risk=geo,
        port_congestion=port,
        risk_category=category
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
        global_enricher = GlobalEnricher(feature_store)
        
        vendor_dict = vendor_enricher.get_stats(req_dict["vendor_name"])
        route_dict = route_enricher.get_stats(req_dict["origin_city"], req_dict["destination_city"])
        
        # New global dictionaries
        origin_risk_dict = global_enricher.get_country_risk(req_dict["origin_country"].upper())
        dest_risk_dict = global_enricher.get_country_risk(req_dict["destination_country"].upper())
        lane_dict = global_enricher.get_trade_lane(req_dict["origin_country"].upper(), req_dict["destination_country"].upper())
        
        dep_date = req_dict.get("planned_departure_date")
        is_origin_holiday = global_enricher.check_holiday(req_dict["origin_country"].upper(), dep_date) if dep_date else 0
        is_dest_holiday = 0 # No arrival date anymore in V1, safely default destination holiday to 0
        
        # Extract weather risk
        weather_risk_score = 0.1
        if dep_date:
            dep_date_str = dep_date.strftime("%Y-%m-%d")
            weather_risk_score = global_enricher.get_weather_risk(req_dict["origin_city"], dep_date_str)
            
        req_dict["weather_risk_score"] = weather_risk_score
        
        feature_df = FeatureBuilder.build(
            req_dict, 
            vendor_dict, 
            route_dict, 
            origin_risk_dict, 
            dest_risk_dict, 
            lane_dict, 
            is_origin_holiday, 
            is_dest_holiday
        )
        
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
        
        # We need to enrich the prediction dictionary saved in EXPLAIN_STORE for the LLM
        # so it has access to the new global metrics
        enriched_prediction = response.model_dump(mode="json")
        enriched_prediction.update({
            "destination_lpi_score": dest_risk_dict["lpi_score"],
            "destination_customs_tier": dest_risk_dict["customs_tier"],
            "destination_geopolitical_risk": dest_risk_dict["geopolitical_risk"],
            "lane_avg_customs_days": lane_dict["avg_customs_days"]
        })
        
        EXPLAIN_STORE[explain_token] = {
            "shipment_id": req_dict["shipment_id"],
            "request": request.model_dump(mode="json"),
            "prediction": enriched_prediction
        }
        
        # Schedule cleanup after TTL using background thread (more reliable than call_later)
        import threading
        ttl = get_settings().explain_ttl_seconds
        threading.Timer(ttl, lambda: EXPLAIN_STORE.pop(explain_token, None)).start()
            
        feature_store.log_prediction(
            shipment_id=req_dict["shipment_id"],
            delay_predicted=pred_dict["delay_predicted"],
            delay_probability=adjusted_prob,
            estimated_delay_days=pred_dict["estimated_delay_days"],
            delay_reason=pred_dict["delay_reason"],
            vendor_tier=tier
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

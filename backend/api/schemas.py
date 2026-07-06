import re
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, field_validator, model_validator

def sanitize_string(value: str) -> str:
    return re.sub(r'[^a-zA-Z0-9\s_\-]', '', str(value)).strip()

class ShipmentRequest(BaseModel):
    shipment_id: str = Field(..., min_length=1, max_length=64)
    vendor_name: str = Field(..., min_length=1, max_length=128)
    origin_city: str = Field(..., min_length=1, max_length=64)
    destination_city: str = Field(..., min_length=1, max_length=64)
    planned_departure_date: date
    planned_arrival_date: date
    cargo_weight_kg: float = Field(..., gt=0.0, le=50000.0)
    cargo_volume_m3: float = Field(..., gt=0.0, le=200.0)
    distance_km: float = Field(..., gt=0.0, le=20000.0)
    num_stops: int = Field(..., ge=0, le=50)
    carrier_type: Literal["FTL", "LTL", "Intermodal"]
    weather_risk_score: float = Field(..., ge=0.0, le=1.0)
    is_hazmat: bool
    priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    historical_delay_rate: float = Field(..., ge=0.0, le=1.0)
    temperature_sensitive: bool

    @field_validator("shipment_id", "vendor_name", "origin_city", "destination_city", mode="before")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Sanitizes incoming strings before Pydantic parses them."""
        return sanitize_string(v)

    @model_validator(mode="after")
    def validate_dates(self):
        """Cross-validates departure and arrival dates."""
        if self.planned_departure_date < date.today():
            raise ValueError("planned_departure_date must be today or in the future")
        if self.planned_arrival_date <= self.planned_departure_date:
            raise ValueError("planned_arrival_date must be after planned_departure_date")
        return self

class PredictionResponse(BaseModel):
    shipment_id: str
    delay_predicted: bool
    delay_probability: float
    adjusted_delay_probability: float
    estimated_delay_days: float
    delay_reason: str
    vendor_tier: str
    vendor_on_time_rate: float
    explain_token: str
    prediction_latency_ms: float

class ExplainResponse(BaseModel):
    shipment_id: str
    explanation: str
    model_used: str
    explain_latency_ms: float

class HealthResponse(BaseModel):
    status: str
    models_loaded: bool
    duckdb_connected: bool
    version: str

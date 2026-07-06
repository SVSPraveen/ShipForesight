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
    origin_country: str = Field(..., min_length=2, max_length=64, description="ISO country code or name")
    destination_city: str = Field(..., min_length=1, max_length=64)
    destination_country: str = Field(..., min_length=2, max_length=64, description="ISO country code or name")
    planned_departure_date: date
    scheduled_transit_days: int = Field(..., gt=0, le=365)
    cargo_weight_kg: float = Field(..., gt=0.0, le=50000.0)
    cargo_volume_m3: float = Field(..., gt=0.0, le=200.0)
    distance_km: float = Field(..., gt=0.0, le=25000.0)
    num_stops: int = Field(default=1, ge=0, le=50)
    carrier_type: Literal["FTL", "LTL", "Intermodal", "Ocean", "Air"]
    is_hazmat: bool
    priority_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    temperature_sensitive: bool

    @field_validator("shipment_id", "vendor_name", "origin_city", "destination_city", mode="before")
    @classmethod
    def sanitize_strings(cls, v: str) -> str:
        """Sanitizes incoming strings before Pydantic parses them."""
        return sanitize_string(v)

    @model_validator(mode="after")
    def validate_dates(self):
        """Cross-validates departure date."""
        if self.planned_departure_date < date.today():
            raise ValueError("planned_departure_date must be today or in the future")
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

class CountryRiskResponse(BaseModel):
    country_code: str
    lpi_score: float
    customs_tier: int
    geopolitical_risk: float
    port_congestion: float
    risk_category: str

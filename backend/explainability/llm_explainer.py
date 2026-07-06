import httpx
import re
from typing import Dict, Any
from backend.config import get_settings

class LLMExplainer:
    def __init__(self):
        self.settings = get_settings()
        # Hard timeout of 8 seconds as specified in your prompt
        self._client = httpx.AsyncClient(timeout=8.0)

    async def close(self):
        """Close the async HTTP client gracefully."""
        await self._client.aclose()

    @staticmethod
    def _sanitize_string(val: str) -> str:
        """Strip all non-alphanumeric characters except spaces, dashes, underscores."""
        return re.sub(r'[^a-zA-Z0-9\s_\-]', '', str(val)).strip()

    async def explain(self, request_dict: Dict[str, Any], prediction_dict: Dict[str, Any], language: str = "English") -> str:
        """
        Calls Groq API asynchronously using Qwen 2.5 32B model.
        Supports English, Hindi, Marathi, Gujarati, and Tamil.
        Returns a fallback string if it times out or fails.
        """
        # Validate language support
        supported_langs = {"English", "Hindi", "Marathi", "Gujarati", "Tamil"}
        if language not in supported_langs:
            language = "English"

        # Sanitize all strings before building prompt to ensure safety
        shipment_id = self._sanitize_string(request_dict.get("shipment_id", ""))
        origin_city = self._sanitize_string(request_dict.get("origin_city", ""))
        destination_city = self._sanitize_string(request_dict.get("destination_city", ""))
        vendor_name = self._sanitize_string(request_dict.get("vendor_name", ""))
        carrier_type = self._sanitize_string(request_dict.get("carrier_type", ""))
        priority_level = self._sanitize_string(request_dict.get("priority_level", ""))
        delay_reason = self._sanitize_string(prediction_dict.get("delay_reason", ""))
        vendor_tier = self._sanitize_string(prediction_dict.get("vendor_tier", ""))

        # Safe extraction of non-strings
        distance_km = float(request_dict.get("distance_km", 0.0))
        planned_transit_days = int(request_dict.get("planned_transit_days", 1))
        weather_risk_score = float(request_dict.get("weather_risk_score", 0.0))
        is_hazmat = bool(request_dict.get("is_hazmat", False))
        
        vendor_on_time_rate = float(prediction_dict.get("vendor_on_time_rate", 0.0))
        adjusted_delay_probability = float(prediction_dict.get("adjusted_delay_probability", 0.0))
        delay_predicted = bool(prediction_dict.get("delay_predicted", False))
        estimated_delay_days = float(prediction_dict.get("estimated_delay_days", 0.0))

        # Build prompt using strictly sanitized inputs
        delay_status_str = "be delayed" if delay_predicted else "arrive on time"
        
        prompt = (
            f"Shipment {shipment_id} from {origin_city} to {destination_city} via vendor {vendor_name}.\n"
            f"Carrier type: {carrier_type}. Distance: {distance_km} km. Planned transit: {planned_transit_days} days.\n"
            f"Weather risk score: {weather_risk_score:.2f}. Hazmat: {is_hazmat}. Priority: {priority_level}.\n"
            f"Vendor on-time rate: {vendor_on_time_rate:.1%}. Vendor tier: {vendor_tier}.\n"
            f"ML prediction - delay: {delay_predicted}. Estimated delay: {estimated_delay_days} days. Reason category: {delay_reason}.\n"
            f"Adjusted delay probability: {adjusted_delay_probability:.1%}.\n"
            f"In 2 to 4 sentences, explain why this shipment is predicted to {delay_status_str} and what the supply chain manager should do about it.\n"
            f"IMPORTANT: You MUST write your explanation in the {language} language."
        )

        payload = {
            "model": "qwen/qwen2.5-32b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a supply chain analyst. Be concise. Maximum 4 sentences. No bullet points."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 200,
            "temperature": 0.3
        }
        
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = await self._client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            response_json = response.json()
            return response_json["choices"][0]["message"]["content"].strip()
            
        except httpx.TimeoutException:
            return f"Explanation generation timed out (exceeded 8 seconds). ML predicted delay: {delay_predicted}. Please try again later."
        except Exception as e:
            return f"Failed to generate explanation due to an upstream error. ML predicted delay: {delay_predicted}."

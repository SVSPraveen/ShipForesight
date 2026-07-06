import httpx
import re
import logging
from typing import Dict, Any
from backend.config import get_settings

logger = logging.getLogger(__name__)

# HTTP status codes that signal rate-limit / quota exhaustion
_RATE_LIMIT_CODES = {429, 503}

class LLMExplainer:
    def __init__(self):
        self.settings = get_settings()
        self._keys = self.settings.groq_api_keys  # list of 1–3 keys
        # Hard timeout of 8 seconds as specified
        self._client = httpx.AsyncClient(timeout=8.0)

    async def close(self):
        """Close the async HTTP client gracefully."""
        await self._client.aclose()

    @staticmethod
    def _sanitize_string(val: str) -> str:
        """Strip all non-alphanumeric characters except spaces, dashes, underscores."""
        return re.sub(r'[^a-zA-Z0-9\s_\-]', '', str(val)).strip()

    async def _call_groq(self, payload: Dict, key: str) -> str:
        """Make one attempt to the Groq API with the given key."""
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        response = await self._client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json=payload,
            headers=headers
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    async def explain(
        self,
        request_dict: Dict[str, Any],
        prediction_dict: Dict[str, Any],
        language: str = "English"
    ) -> str:
        """
        Calls Groq API asynchronously using Qwen 2.5 32B.
        Automatically rotates through up to 3 API keys on rate-limit (429/503).
        Supports English, Hindi, Marathi, Gujarati, and Tamil.
        Returns a fallback string on timeout or total failure.
        """
        supported_langs = {"English", "Hindi", "Marathi", "Gujarati", "Tamil", "Arabic", "French", "Spanish", "German"}
        if language not in supported_langs:
            language = "English"

        # --- Sanitize all string inputs ---
        shipment_id       = self._sanitize_string(request_dict.get("shipment_id", ""))
        origin_city       = self._sanitize_string(request_dict.get("origin_city", ""))
        destination_city  = self._sanitize_string(request_dict.get("destination_city", ""))
        vendor_name       = self._sanitize_string(request_dict.get("vendor_name", ""))
        carrier_type      = self._sanitize_string(request_dict.get("carrier_type", ""))
        priority_level    = self._sanitize_string(request_dict.get("priority_level", ""))
        delay_reason      = self._sanitize_string(prediction_dict.get("delay_reason", ""))
        vendor_tier       = self._sanitize_string(prediction_dict.get("vendor_tier", ""))

        # --- Safe extraction of numeric values ---
        distance_km               = float(request_dict.get("distance_km", 0.0))
        planned_transit_days      = int(request_dict.get("planned_transit_days", 1))
        weather_risk_score        = float(request_dict.get("weather_risk_score", 0.0))
        is_hazmat                 = bool(request_dict.get("is_hazmat", False))
        vendor_on_time_rate       = float(prediction_dict.get("vendor_on_time_rate", 0.0))
        adjusted_delay_probability = float(prediction_dict.get("adjusted_delay_probability", 0.0))
        delay_predicted           = bool(prediction_dict.get("delay_predicted", False))
        estimated_delay_days      = float(prediction_dict.get("estimated_delay_days", 0.0))

        origin_country    = self._sanitize_string(request_dict.get("origin_country", "US"))
        destination_country = self._sanitize_string(request_dict.get("destination_country", "US"))
        
        destination_lpi_score = float(prediction_dict.get("destination_lpi_score", 3.0))
        destination_customs_tier = int(prediction_dict.get("destination_customs_tier", 2))
        destination_geopolitical_risk = float(prediction_dict.get("destination_geopolitical_risk", 0.2))
        lane_avg_customs_days = float(prediction_dict.get("lane_avg_customs_days", 2.5))

        delay_status_str = "be delayed" if delay_predicted else "arrive on time"

        prompt = (
            f"Shipment {shipment_id} from {origin_city}, {origin_country} to {destination_city}, {destination_country} via vendor {vendor_name}.\n"
            f"Carrier type: {carrier_type}. Distance: {distance_km} km. Planned transit: {planned_transit_days} days.\n"
            f"Weather risk score: {weather_risk_score:.2f}. Hazmat: {is_hazmat}. Priority: {priority_level}.\n"
            f"Vendor on-time rate: {vendor_on_time_rate:.1%}. Vendor tier: {vendor_tier}.\n"
            f"Cross-border context: Destination LPI Score is {destination_lpi_score:.1f}/5.0. "
            f"Customs Tier: {destination_customs_tier}/4. Geopolitical Risk: {destination_geopolitical_risk:.2f}. "
            f"Historical avg customs delay for this lane: {lane_avg_customs_days:.1f} days.\n"
            f"ML prediction - delay: {delay_predicted}. Estimated delay: {estimated_delay_days} days. Reason category: {delay_reason}.\n"
            f"Adjusted delay probability: {adjusted_delay_probability:.1%}.\n"
            f"In 2 to 4 sentences, explain why this shipment is predicted to {delay_status_str} "
            f"and what the supply chain manager should do about it, specifically addressing any customs or geopolitical risks if applicable.\n"
            f"IMPORTANT: You MUST write your explanation in the {language} language."
        )

        payload = {
            "model": "llama3-70b-8192",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a supply chain risk analyst. Be concise, factual, and professional. Maximum 4 sentences. No bullet points. No markdown."
                },
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 250,
            "temperature": 0.3
        }

        # --- Key rotation loop ---
        last_error = None
        for idx, key in enumerate(self._keys):
            key_label = f"Key {idx + 1}"
            try:
                logger.debug(f"LLMExplainer: trying {key_label} (last 6: ...{key[-6:]})")
                result = await self._call_groq(payload, key)
                if idx > 0:
                    logger.info(f"LLMExplainer: succeeded on {key_label} after {idx} rotation(s)")
                return result

            except httpx.TimeoutException:
                logger.warning(f"LLMExplainer: {key_label} timed out — not rotating (timeout is global)")
                return (
                    f"Explanation generation timed out (exceeded 8 seconds). "
                    f"ML predicted delay: {delay_predicted}. Please try again later."
                )

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status in _RATE_LIMIT_CODES and idx < len(self._keys) - 1:
                    logger.warning(
                        f"LLMExplainer: {key_label} hit rate-limit (HTTP {status}), "
                        f"rotating to Key {idx + 2}…"
                    )
                    last_error = e
                    continue  # try next key
                else:
                    logger.error(f"LLMExplainer: {key_label} failed with HTTP {status}")
                    # Try fallback model if primary fails
                    if status == 404:
                        try:
                            payload["model"] = "llama-3.1-8b-instant"
                            result = await self._call_groq(payload, key)
                            return result
                        except Exception:
                            pass
                    return (
                        f"Failed to generate explanation (HTTP {status}). "
                        f"ML predicted delay: {delay_predicted}."
                    )

            except Exception as e:
                logger.error(f"LLMExplainer: {key_label} raised unexpected error: {e}")
                last_error = e
                continue

        # All keys exhausted
        logger.error(f"LLMExplainer: all {len(self._keys)} keys failed. Last error: {last_error}")
        return (
            f"All API keys are currently rate-limited or unavailable. "
            f"ML predicted delay: {delay_predicted}. Please try again in a few minutes."
        )

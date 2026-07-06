from typing import Tuple
from backend.data.feature_store import FeatureStore

class VendorEnricher:
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def get_stats(self, vendor_name: str) -> dict:
        """Fetches vendor stats from the FeatureStore."""
        return self.feature_store.get_vendor_stats(vendor_name)

    @staticmethod
    def adjust_probability(raw_probability: float, on_time_rate: float) -> Tuple[float, str]:
        """
        Adjusts the ML probability based on the vendor's on-time rate.
        Implements the exact OTR rules from Section 5 of the spec.
        Returns: (adjusted_probability, vendor_tier_string)
        """
        if on_time_rate >= 0.65:
            adjusted = raw_probability - 0.10
            tier = "EXCELLENT"
        elif on_time_rate >= 0.50:
            # Linear interpolation: 0 adjustment at OTR=0.50, -0.10 adjustment at OTR=0.65
            t = (on_time_rate - 0.50) / (0.65 - 0.50)   # t in [0.0, 1.0]
            adjusted = raw_probability + t * (-0.10)
            tier = "AVERAGE"
        else:
            adjusted = raw_probability + 0.15
            tier = "POOR"
            
        # Clamp probability to valid range [0.0, 1.0]
        adjusted_probability = max(0.0, min(1.0, adjusted))
        
        return adjusted_probability, tier

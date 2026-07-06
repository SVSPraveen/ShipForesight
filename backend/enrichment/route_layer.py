from backend.data.feature_store import FeatureStore

class RouteEnricher:
    def __init__(self, feature_store: FeatureStore):
        self.feature_store = feature_store

    def get_stats(self, origin: str, destination: str) -> dict:
        """Fetches route stats from the FeatureStore."""
        return self.feature_store.get_route_stats(origin, destination)

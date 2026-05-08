from __future__ import annotations

from .schemas import (
    EstimateTransportTimesRequest,
    GetWeatherWindowRequest,
    PlanRouteRequest,
    RecommendDestinationsRequest,
    ResolveGeographyRequest,
    SearchLocationsRequest,
)
from .providers.amap import AmapWebClient
from .services.geography import GeographyService
from .services.location_search import LocationSearchService
from .services.recommendation import DestinationRecommendationService
from .services.routing import RoutingService
from .services.transport import TransportService
from .services.weather import WeatherService


class TravelToolsFacade:
    def __init__(self, provider: AmapWebClient) -> None:
        self.location_search_service = LocationSearchService(provider)
        self.geography_service = GeographyService(provider, self.location_search_service)
        self.recommendation_service = DestinationRecommendationService(self.geography_service)
        self.transport_service = TransportService(provider, self.geography_service)
        self.weather_service = WeatherService(provider, self.geography_service)
        self.routing_service = RoutingService(self.geography_service, self.transport_service)

    async def search_locations(self, request: SearchLocationsRequest):
        return await self.location_search_service.search(request)

    async def recommend_destinations(self, request: RecommendDestinationsRequest):
        return await self.recommendation_service.recommend(request)

    async def get_weather_window(self, request: GetWeatherWindowRequest):
        return await self.weather_service.get_weather_window(request)

    async def resolve_geography(self, request: ResolveGeographyRequest):
        return await self.geography_service.resolve_geography(request)

    async def estimate_transport_times(self, request: EstimateTransportTimesRequest):
        return await self.transport_service.estimate(request)

    async def plan_route(self, request: PlanRouteRequest):
        return await self.routing_service.plan_route(request)

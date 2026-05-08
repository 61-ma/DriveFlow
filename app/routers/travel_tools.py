from __future__ import annotations

from fastapi import APIRouter

from ..travel_tools.registry import TravelToolsRegistry
from ..travel_tools.schemas import (
    EstimateTransportTimesRequest,
    GetWeatherWindowRequest,
    PlanRouteRequest,
    RecommendDestinationsRequest,
    ResolveGeographyRequest,
    SearchLocationsRequest,
)

router = APIRouter(prefix="/api/tools", tags=["travel-tools"])
registry = TravelToolsRegistry()


@router.post("/locations/search")
async def search_locations(payload: SearchLocationsRequest):
    return await registry.execute_tool_async("search_locations", payload.model_dump(mode="json"))


@router.post("/destinations/recommend")
async def recommend_destinations(payload: RecommendDestinationsRequest):
    return await registry.execute_tool_async("recommend_destinations", payload.model_dump(mode="json"))


@router.post("/weather/window")
async def get_weather_window(payload: GetWeatherWindowRequest):
    return await registry.execute_tool_async("get_weather_window", payload.model_dump(mode="json"))


@router.post("/geo/resolve")
async def resolve_geography(payload: ResolveGeographyRequest):
    return await registry.execute_tool_async("resolve_geography", payload.model_dump(mode="json"))


@router.post("/transport/estimate")
async def estimate_transport_times(payload: EstimateTransportTimesRequest):
    return await registry.execute_tool_async("estimate_transport_times", payload.model_dump(mode="json"))


@router.post("/routes/plan")
async def plan_route(payload: PlanRouteRequest):
    return await registry.execute_tool_async("plan_route", payload.model_dump(mode="json"))


@router.get("/metadata")
async def metadata():
    return registry.get_metadata()

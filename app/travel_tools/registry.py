from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from .enums import TravelMode
from .errors import ToolError, TravelToolException
from .facade import TravelToolsFacade
from .providers.amap import AmapWebClient
from .schemas import (
    EstimateTransportTimesData,
    EstimateTransportTimesRequest,
    GetWeatherWindowData,
    GetWeatherWindowRequest,
    MetadataResponse,
    PlanRouteData,
    PlanRouteRequest,
    RecommendDestinationsData,
    RecommendDestinationsRequest,
    ResolveGeographyData,
    ResolveGeographyRequest,
    SearchLocationsData,
    SearchLocationsRequest,
    ToolEnvelope,
    ToolMetadata,
    ToolSource,
)
from .settings import TravelToolsSettings


@dataclass
class ToolSpec:
    name: str
    description: str
    request_model: type
    handler: Callable[[Any], Awaitable[Any]]


class TravelToolsRegistry:
    def __init__(
        self,
        *,
        settings: TravelToolsSettings | None = None,
        provider: AmapWebClient | None = None,
    ) -> None:
        self.settings = settings or TravelToolsSettings()
        self.provider = provider or AmapWebClient(self.settings)
        self.facade = TravelToolsFacade(self.provider)
        self._tools: dict[str, ToolSpec] = {
            "search_locations": ToolSpec(
                name="search_locations",
                description="Search departure cities, destination cities, stations, airports, and POIs.",
                request_model=SearchLocationsRequest,
                handler=self.facade.search_locations,
            ),
            "recommend_destinations": ToolSpec(
                name="recommend_destinations",
                description="Recommend travel destinations based on preferences, budget, travel time, and travel modes.",
                request_model=RecommendDestinationsRequest,
                handler=self.facade.recommend_destinations,
            ),
            "get_weather_window": ToolSpec(
                name="get_weather_window",
                description="Fetch weather and temperature information for a travel date window.",
                request_model=GetWeatherWindowRequest,
                handler=self.facade.get_weather_window,
            ),
            "resolve_geography": ToolSpec(
                name="resolve_geography",
                description="Resolve a location name or coordinates into normalized geography information.",
                request_model=ResolveGeographyRequest,
                handler=self.facade.resolve_geography,
            ),
            "estimate_transport_times": ToolSpec(
                name="estimate_transport_times",
                description="Estimate travel time and distance between multiple origins and destinations.",
                request_model=EstimateTransportTimesRequest,
                handler=self.facade.estimate_transport_times,
            ),
            "plan_route": ToolSpec(
                name="plan_route",
                description="Plan ordered or optimized routes across multiple stops.",
                request_model=PlanRouteRequest,
                handler=self.facade.plan_route,
            ),
        }

    def get_openai_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": spec.name,
                    "description": spec.description,
                    "parameters": spec.request_model.model_json_schema(),
                },
            }
            for spec in self._tools.values()
        ]

    def get_metadata(self) -> MetadataResponse:
        return MetadataResponse(
            provider="amap",
            supported_modes=[
                TravelMode.FLIGHT,
                TravelMode.HIGH_SPEED_RAIL,
                TravelMode.DRIVING,
                TravelMode.TRANSIT,
                TravelMode.WALKING,
                TravelMode.BICYCLING,
            ],
            tools=[
                ToolMetadata(
                    name=spec.name,
                    description=spec.description,
                    parameters=spec.request_model.model_json_schema(),
                )
                for spec in self._tools.values()
            ],
            capability_matrix={
                "search_locations": ["input_tips", "poi_search", "geocode"],
                "recommend_destinations": ["curated_profiles", "geocode_validation"],
                "get_weather_window": ["weather_live", "weather_forecast_limited_horizon"],
                "resolve_geography": ["geocode", "reverse_geocode"],
                "estimate_transport_times": ["distance_matrix", "driving", "walking", "transit", "railway_detection", "flight_unsupported"],
                "plan_route": ["ordered_routing", "greedy_optimization", "round_trip"],
            },
        )

    async def execute_tool_async(self, tool_name: str, payload: dict[str, Any]) -> ToolEnvelope:
        spec = self._tools[tool_name]
        validated = spec.request_model.model_validate(payload)
        try:
            result = await spec.handler(validated)
            data = self._serialize_result(tool_name, result)
            warnings = []
            if isinstance(result, list):
                for item in result:
                    warnings.extend(getattr(item, "warnings", []))
            else:
                warnings.extend(getattr(result, "warnings", []))
            return ToolEnvelope(
                ok=True,
                tool_name=tool_name,
                data=data,
                warnings=list(dict.fromkeys(warnings)),
                errors=[],
                source=ToolSource(provider="amap", capability_flags=self.get_metadata().capability_matrix.get(tool_name, [])),
            )
        except TravelToolException as exc:
            return ToolEnvelope(
                ok=False,
                tool_name=tool_name,
                data={},
                warnings=[],
                errors=[exc.to_error()],
                source=ToolSource(provider="amap", capability_flags=self.get_metadata().capability_matrix.get(tool_name, [])),
            )
        except Exception as exc:
            return ToolEnvelope(
                ok=False,
                tool_name=tool_name,
                data={},
                warnings=[],
                errors=[ToolError(code="unexpected_error", message=str(exc))],
                source=ToolSource(provider="amap", capability_flags=self.get_metadata().capability_matrix.get(tool_name, [])),
            )

    def execute_tool(self, tool_name: str, payload: dict[str, Any]) -> ToolEnvelope:
        return asyncio.run(self.execute_tool_async(tool_name, payload))

    @staticmethod
    def _serialize_result(tool_name: str, result: Any) -> dict[str, Any]:
        if tool_name == "search_locations":
            return SearchLocationsData(candidates=result).model_dump(mode="json")
        if tool_name == "recommend_destinations":
            return RecommendDestinationsData(recommended_destinations=result).model_dump(mode="json")
        if tool_name == "get_weather_window":
            return GetWeatherWindowData(weather_window=result).model_dump(mode="json")
        if tool_name == "resolve_geography":
            return ResolveGeographyData(geography=result).model_dump(mode="json")
        if tool_name == "estimate_transport_times":
            return EstimateTransportTimesData(estimates=result).model_dump(mode="json")
        if tool_name == "plan_route":
            return PlanRouteData(route_plan=result).model_dump(mode="json")
        return {}


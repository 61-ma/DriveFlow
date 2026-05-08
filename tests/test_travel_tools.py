import asyncio
import importlib
import unittest

from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.travel_tools.data.destinations import CURATED_DESTINATIONS
from app.travel_tools.enums import TravelMode
from app.travel_tools.errors import ProviderAuthError
from app.travel_tools.registry import TravelToolsRegistry
from app.travel_tools.schemas import (
    EstimateTransportTimesRequest,
    GetWeatherWindowRequest,
    LocationLookupInput,
    PlanRouteRequest,
    RecommendDestinationsRequest,
    SearchLocationsRequest,
    TravelAgentContext,
    TravelTimeWindow,
)
from app.travel_tools.settings import TravelToolsSettings

travel_tools_router = importlib.import_module("app.routers.travel_tools")


class MockAmapProvider:
    LOCATION_DATA = {
        "上海": {
            "name": "上海",
            "formatted_address": "上海市黄浦区",
            "province": "上海市",
            "city": "上海市",
            "district": "黄浦区",
            "adcode": "310101",
            "citycode": "021",
            "longitude": 121.4737,
            "latitude": 31.2304,
        },
        "北海": {
            "name": "北海",
            "formatted_address": "广西壮族自治区北海市",
            "province": "广西壮族自治区",
            "city": "北海市",
            "district": "海城区",
            "adcode": "450502",
            "citycode": "0779",
            "longitude": 109.1202,
            "latitude": 21.4811,
        },
        "三亚": {
            "name": "三亚",
            "formatted_address": "海南省三亚市",
            "province": "海南省",
            "city": "三亚市",
            "district": "天涯区",
            "adcode": "460204",
            "citycode": "0899",
            "longitude": 109.5119,
            "latitude": 18.2528,
        },
        "厦门": {
            "name": "厦门",
            "formatted_address": "福建省厦门市",
            "province": "福建省",
            "city": "厦门市",
            "district": "思明区",
            "adcode": "350203",
            "citycode": "0592",
            "longitude": 118.0894,
            "latitude": 24.4798,
        },
        "杭州": {
            "name": "杭州",
            "formatted_address": "浙江省杭州市",
            "province": "浙江省",
            "city": "杭州市",
            "district": "西湖区",
            "adcode": "330106",
            "citycode": "0571",
            "longitude": 120.1551,
            "latitude": 30.2741,
        },
        "苏州": {
            "name": "苏州",
            "formatted_address": "江苏省苏州市",
            "province": "江苏省",
            "city": "苏州市",
            "district": "姑苏区",
            "adcode": "320508",
            "citycode": "0512",
            "longitude": 120.5853,
            "latitude": 31.2989,
        },
    }

    async def input_tips(
        self,
        keywords: str,
        *,
        city: str | None = None,
        city_limit: bool = False,
        limit: int = 10,
    ) -> dict:
        if keywords == "上海":
            return {
                "tips": [
                    self._tip_payload("上海", poi_id="tip-shanghai"),
                    self._tip_payload("上海", poi_id="tip-shanghai"),
                ][:limit]
            }
        if keywords in self.LOCATION_DATA:
            return {"tips": [self._tip_payload(keywords, poi_id=f"tip-{keywords}")][:limit]}
        return {"tips": []}

    async def poi_search(
        self,
        keywords: str,
        *,
        city: str | None = None,
        page_size: int = 10,
    ) -> dict:
        if keywords == "上海":
            return {
                "pois": [
                    self._poi_payload("上海", poi_id="tip-shanghai"),
                    self._poi_payload("上海", poi_id="poi-second"),
                ][:page_size]
            }
        if keywords in self.LOCATION_DATA:
            return {"pois": [self._poi_payload(keywords, poi_id=f"poi-{keywords}")][:page_size]}
        return {"pois": []}

    async def geocode(
        self,
        address: str,
        *,
        city: str | None = None,
    ) -> dict:
        location = self.LOCATION_DATA[address]
        return {
            "geocodes": [
                {
                    "formatted_address": location["formatted_address"],
                    "province": location["province"],
                    "city": location["city"],
                    "district": location["district"],
                    "adcode": location["adcode"],
                    "location": self._location_string(address),
                }
            ]
        }

    async def reverse_geocode(self, longitude: float, latitude: float) -> dict:
        for key, location in self.LOCATION_DATA.items():
            if location["longitude"] == longitude and location["latitude"] == latitude:
                return {
                    "regeocode": {
                        "formatted_address": location["formatted_address"],
                        "addressComponent": {
                            "province": location["province"],
                            "city": location["city"],
                            "district": location["district"],
                            "adcode": location["adcode"],
                            "citycode": location["citycode"],
                        },
                    }
                }
        raise AssertionError("unexpected coordinates")

    async def weather(self, city: str, *, extensions: str) -> dict:
        if extensions == "base":
            return {
                "lives": [
                    {
                        "weather": "晴",
                        "temperature": "26",
                        "humidity": "60",
                        "reporttime": "2026-05-09 10:00:00",
                    }
                ]
            }
        return {
            "forecasts": [
                {
                    "casts": [
                        {
                            "date": "2026-06-01",
                            "dayweather": "晴",
                            "nightweather": "多云",
                            "daytemp": "29",
                            "nighttemp": "24",
                            "daywind": "3级",
                            "nightwind": "2级",
                        },
                        {
                            "date": "2026-06-02",
                            "dayweather": "多云",
                            "nightweather": "小雨",
                            "daytemp": "28",
                            "nighttemp": "23",
                            "daywind": "3级",
                            "nightwind": "2级",
                        },
                        {
                            "date": "2026-06-03",
                            "dayweather": "小雨",
                            "nightweather": "阴",
                            "daytemp": "27",
                            "nighttemp": "22",
                            "daywind": "4级",
                            "nightwind": "3级",
                        },
                        {
                            "date": "2026-06-04",
                            "dayweather": "阴",
                            "nightweather": "阴",
                            "daytemp": "26",
                            "nighttemp": "22",
                            "daywind": "3级",
                            "nightwind": "2级",
                        },
                    ]
                }
            ]
        }

    async def distance_matrix(
        self,
        origins: list[str],
        destination: str,
        *,
        route_type: str = "driving",
    ) -> dict:
        origin = origins[0]
        distance = 180000 if origin != destination else 0
        duration = 7200 if origin != destination else 0
        return {"results": [{"distance": str(distance), "duration": str(duration)}]}

    async def route(
        self,
        *,
        mode: str,
        origin: str,
        destination: str,
        city: str | None = None,
        cityd: str | None = None,
    ) -> dict:
        if mode == "walking":
            return {"route": {"paths": [{"distance": "1200", "duration": "900"}]}}
        if mode == "bicycling":
            return {"data": {"paths": [{"distance": "3500", "duration": "1200"}]}}
        if mode == "high_speed_rail":
            return {
                "route": {
                    "transits": [
                        {
                            "distance": "1300000",
                            "duration": "14400",
                            "cost": "560",
                            "segments": [{"railway": {"trip": "G100"}}],
                        }
                    ]
                }
            }
        if mode == "transit":
            return {
                "route": {
                    "transits": [
                        {
                            "distance": "8000",
                            "duration": "2400",
                            "cost": "6",
                            "segments": [{"bus": {"name": "地铁1号线"}}],
                        }
                    ]
                }
            }
        raise AssertionError(f"unexpected mode: {mode}")

    @classmethod
    def _tip_payload(cls, location_name: str, *, poi_id: str) -> dict:
        location = cls.LOCATION_DATA[location_name]
        return {
            "name": location["name"],
            "district": location["city"],
            "address": location["district"],
            "location": cls._location_string(location_name),
            "adcode": location["adcode"],
            "citycode": location["citycode"],
            "id": poi_id,
            "typecode": "090000",
        }

    @classmethod
    def _poi_payload(cls, location_name: str, *, poi_id: str) -> dict:
        location = cls.LOCATION_DATA[location_name]
        return {
            "name": location["name"],
            "adname": location["district"],
            "cityname": location["city"],
            "pname": location["province"],
            "adcode": location["adcode"],
            "citycode": location["citycode"],
            "id": poi_id,
            "location": cls._location_string(location_name),
            "typecode": "090000",
        }

    @classmethod
    def _location_string(cls, location_name: str) -> str:
        location = cls.LOCATION_DATA[location_name]
        return f"{location['longitude']},{location['latitude']}"


class AuthFailureProvider(MockAmapProvider):
    async def input_tips(
        self,
        keywords: str,
        *,
        city: str | None = None,
        city_limit: bool = False,
        limit: int = 10,
    ) -> dict:
        raise ProviderAuthError(
            code="provider_auth_failed",
            message="AMAP_WEB_KEY is not configured",
        )


class TravelToolSchemaTestCase(unittest.TestCase):
    def test_travel_agent_context_normalizes_input_aliases(self) -> None:
        context = TravelAgentContext.model_validate(
            {
                "departure_city": "上海",
                "travel_time": {
                    "start_date": "2026-06-01",
                    "end_date": "2026-06-07",
                },
                "budget": {"currency": "CNY", "max_budget": 8000},
                "preferences": ["海边", "美食", "自然风景", "低拥挤度"],
                "travel_mode": ["飞机", "高铁"],
                "people_count": 2,
                "pace": "轻松",
            }
        )

        self.assertEqual([mode.value for mode in context.travel_mode], ["flight", "high_speed_rail"])
        self.assertEqual(context.pace.value, "relaxed")
        self.assertEqual(context.travel_time.trip_days, 7)

    def test_travel_time_window_rejects_invalid_date_range(self) -> None:
        with self.assertRaises(ValidationError):
            TravelTimeWindow.model_validate(
                {
                    "start_date": "2026-06-07",
                    "end_date": "2026-06-01",
                }
            )

    def test_location_lookup_requires_query_or_coordinates(self) -> None:
        with self.assertRaises(ValidationError):
            LocationLookupInput.model_validate({})


class TravelToolsRegistryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = TravelToolsRegistry(
            settings=TravelToolsSettings(amap_web_key="test-key"),
            provider=MockAmapProvider(),
        )

    def test_get_openai_tools_exposes_all_supported_functions(self) -> None:
        tools = self.registry.get_openai_tools()
        tool_names = [item["function"]["name"] for item in tools]

        self.assertEqual(len(tools), 6)
        self.assertCountEqual(
            tool_names,
            [
                "search_locations",
                "recommend_destinations",
                "get_weather_window",
                "resolve_geography",
                "estimate_transport_times",
                "plan_route",
            ],
        )

    def test_execute_tool_returns_standard_envelope(self) -> None:
        envelope = asyncio.run(
            self.registry.execute_tool_async(
                "search_locations",
                {"query": "上海", "limit": 5},
            )
        )

        self.assertTrue(envelope.ok)
        self.assertEqual(envelope.tool_name, "search_locations")
        self.assertEqual(envelope.source.provider, "amap")
        self.assertEqual(len(envelope.data["candidates"]), 2)

    def test_execute_tool_maps_provider_errors_to_structured_errors(self) -> None:
        registry = TravelToolsRegistry(
            settings=TravelToolsSettings(amap_web_key="test-key"),
            provider=AuthFailureProvider(),
        )

        envelope = asyncio.run(
            registry.execute_tool_async(
                "search_locations",
                {"query": "上海", "limit": 5},
            )
        )

        self.assertFalse(envelope.ok)
        self.assertEqual(envelope.errors[0].code, "provider_auth_failed")
        self.assertEqual(envelope.errors[0].message, "AMAP_WEB_KEY is not configured")


class TravelToolServicesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = MockAmapProvider()
        self.registry = TravelToolsRegistry(
            settings=TravelToolsSettings(amap_web_key="test-key"),
            provider=self.provider,
        )
        self.location_search_service = self.registry.facade.location_search_service
        self.recommendation_service = self.registry.facade.recommendation_service
        self.weather_service = self.registry.facade.weather_service
        self.transport_service = self.registry.facade.transport_service
        self.routing_service = self.registry.facade.routing_service

    def test_location_search_deduplicates_candidates(self) -> None:
        candidates = asyncio.run(
            self.location_search_service.search(
                SearchLocationsRequest(query="上海", limit=5)
            )
        )

        self.assertEqual(len(candidates), 2)
        self.assertEqual(candidates[0].location_ref.name, "上海")
        self.assertEqual(candidates[1].location_ref.poi_id, "poi-second")

    def test_recommendation_reflects_budget_pace_and_exclusions(self) -> None:
        keep_destination = "北海"
        excluded = [
            item.destination
            for item in CURATED_DESTINATIONS
            if item.destination != keep_destination
        ]

        low_budget_result = asyncio.run(
            self.recommendation_service.recommend(
                RecommendDestinationsRequest(
                    context=TravelAgentContext.model_validate(
                        {
                            "departure_city": "上海",
                            "travel_time": {
                                "start_date": "2026-06-01",
                                "end_date": "2026-06-07",
                            },
                            "budget": {"currency": "CNY", "max_budget": 2000},
                            "preferences": ["海边", "低拥挤度"],
                            "travel_mode": ["高铁"],
                            "people_count": 2,
                            "pace": "relaxed",
                        }
                    ),
                    limit=5,
                    exclude_destinations=excluded,
                )
            )
        )
        high_budget_result = asyncio.run(
            self.recommendation_service.recommend(
                RecommendDestinationsRequest(
                    context=TravelAgentContext.model_validate(
                        {
                            "departure_city": "上海",
                            "travel_time": {
                                "start_date": "2026-06-01",
                                "end_date": "2026-06-07",
                            },
                            "budget": {"currency": "CNY", "max_budget": 20000},
                            "preferences": ["海边", "低拥挤度"],
                            "travel_mode": ["高铁"],
                            "people_count": 2,
                            "pace": "relaxed",
                        }
                    ),
                    limit=5,
                    exclude_destinations=excluded,
                )
            )
        )
        balanced_pace_result = asyncio.run(
            self.recommendation_service.recommend(
                RecommendDestinationsRequest(
                    context=TravelAgentContext.model_validate(
                        {
                            "departure_city": "上海",
                            "travel_time": {
                                "start_date": "2026-06-01",
                                "end_date": "2026-06-07",
                            },
                            "budget": {"currency": "CNY", "max_budget": 20000},
                            "preferences": ["海边", "低拥挤度"],
                            "travel_mode": ["高铁"],
                            "people_count": 2,
                            "pace": "balanced",
                        }
                    ),
                    limit=5,
                    exclude_destinations=excluded,
                )
            )
        )

        self.assertEqual([item.destination for item in low_budget_result], [keep_destination])
        self.assertIsNotNone(low_budget_result[0].location_ref)
        self.assertLess(
            low_budget_result[0].score_breakdown.budget,
            high_budget_result[0].score_breakdown.budget,
        )
        self.assertGreater(
            high_budget_result[0].score_breakdown.pace,
            balanced_pace_result[0].score_breakdown.pace,
        )

    def test_weather_window_marks_missing_dates_beyond_provider_horizon(self) -> None:
        weather_window = asyncio.run(
            self.weather_service.get_weather_window(
                GetWeatherWindowRequest(
                    location=LocationLookupInput(query="上海"),
                    start_date="2026-06-01",
                    end_date="2026-06-06",
                )
            )
        )

        self.assertEqual(len(weather_window.forecast_days), 4)
        self.assertEqual(
            [item.isoformat() for item in weather_window.missing_dates],
            ["2026-06-05", "2026-06-06"],
        )
        self.assertIn("forecast_window_exceeds_provider_horizon", weather_window.warnings)

    def test_transport_flight_returns_structured_degradation(self) -> None:
        estimate = asyncio.run(
            self.transport_service.estimate(
                EstimateTransportTimesRequest(
                    origins=[LocationLookupInput(query="上海")],
                    destinations=[LocationLookupInput(query="北海")],
                    modes=["飞机"],
                )
            )
        )

        self.assertEqual(len(estimate), 1)
        self.assertFalse(estimate[0].available)
        self.assertEqual(estimate[0].provider_route_type, "unsupported")
        self.assertIn("mode_not_supported_by_current_provider", estimate[0].warnings)

    def test_transport_same_point_returns_zero_cost_leg(self) -> None:
        origin = asyncio.run(self.registry.facade.geography_service.resolve_lookup(LocationLookupInput(query="上海")))

        estimate = asyncio.run(
            self.transport_service.estimate_leg(
                origin,
                origin,
                mode=TravelMode.DRIVING,
            )
        )

        self.assertEqual(estimate.distance_meters, 0)
        self.assertEqual(estimate.duration_seconds, 0)
        self.assertEqual(estimate.provider_route_type, "same_point")

    def test_route_plan_preserves_input_order_when_not_optimized(self) -> None:
        route_plan = asyncio.run(
            self.routing_service.plan_route(
                PlanRouteRequest(
                    stops=[
                        LocationLookupInput(query="上海"),
                        LocationLookupInput(query="杭州"),
                        LocationLookupInput(query="苏州"),
                    ],
                    mode="driving",
                    ordered=False,
                    optimize=False,
                )
            )
        )

        self.assertEqual(
            [stop.location_ref.name for stop in route_plan.stops],
            ["上海", "杭州", "苏州"],
        )
        self.assertIn(
            "Input marked unordered but optimize is disabled; kept original order",
            route_plan.optimization_notes,
        )


class TravelToolsApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.original_registry = travel_tools_router.registry
        travel_tools_router.registry = TravelToolsRegistry(
            settings=TravelToolsSettings(amap_web_key="test-key"),
            provider=MockAmapProvider(),
        )
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()
        travel_tools_router.registry = self.original_registry

    def test_metadata_route_is_available(self) -> None:
        response = self.client.get("/api/tools/metadata")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["provider"], "amap")
        self.assertEqual(len(payload["tools"]), 6)

    def test_location_search_route_returns_tool_envelope(self) -> None:
        response = self.client.post(
            "/api/tools/locations/search",
            json={"query": "上海", "limit": 5},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["tool_name"], "search_locations")
        self.assertEqual(len(payload["data"]["candidates"]), 2)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator

from .enums import Pace, TravelMode
from .errors import ToolError
from .normalizers import normalize_pace, normalize_travel_mode


class MatchType(str, Enum):
    CITY = "city"
    DISTRICT = "district"
    POI = "poi"
    STATION = "station"
    AIRPORT = "airport"


class CrowdLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BudgetBand(str, Enum):
    BUDGET = "budget"
    MID = "mid"
    PREMIUM = "premium"


class Coordinates(BaseModel):
    longitude: float
    latitude: float


class TravelTimeWindow(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_window(self) -> "TravelTimeWindow":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be later than or equal to start_date")
        return self

    @property
    def trip_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


class BudgetLimit(BaseModel):
    currency: str = "CNY"
    max_budget: int = Field(gt=0)


class TravelAgentContext(BaseModel):
    departure_city: str
    travel_time: TravelTimeWindow
    budget: BudgetLimit
    preferences: list[str] = Field(default_factory=list)
    travel_mode: list[TravelMode] = Field(default_factory=list)
    people_count: int = Field(default=1, gt=0)
    pace: Pace = Pace.BALANCED

    @model_validator(mode="before")
    @classmethod
    def normalize_fields(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        travel_mode = values.get("travel_mode")
        if travel_mode:
            values["travel_mode"] = [normalize_travel_mode(item) for item in travel_mode]
        pace = values.get("pace")
        if pace:
            values["pace"] = normalize_pace(pace)
        return values


class LocationRef(BaseModel):
    name: str
    display_name: str
    adcode: str | None = None
    citycode: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    poi_id: str | None = None
    source: str = "amap"
    confidence: float = 0.5

    @property
    def coordinate_string(self) -> str:
        if self.longitude is None or self.latitude is None:
            return ""
        return f"{self.longitude},{self.latitude}"


class LocationCandidate(BaseModel):
    location_ref: LocationRef
    match_type: MatchType
    query_text: str
    matched_fields: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    preference: float = 0.0
    season: float = 0.0
    budget: float = 0.0
    transport: float = 0.0
    pace: float = 0.0


class DestinationProfile(BaseModel):
    destination: str
    theme_tags: list[str]
    best_months: list[int]
    budget_band: BudgetBand
    daily_budget_per_person: int
    crowd_level: CrowdLevel
    transport_friendliness: list[TravelMode]
    notes: str


class RecommendedDestination(BaseModel):
    destination: str
    location_ref: LocationRef | None = None
    profile: DestinationProfile
    score: float
    score_breakdown: ScoreBreakdown
    why_recommended: list[str] = Field(default_factory=list)
    estimated_total_cost: int


class CurrentWeather(BaseModel):
    weather: str | None = None
    temperature_celsius: int | None = None
    humidity: str | None = None
    report_time: str | None = None


class ForecastDay(BaseModel):
    date: date
    day_weather: str | None = None
    night_weather: str | None = None
    day_temp_celsius: int | None = None
    night_temp_celsius: int | None = None
    day_wind: str | None = None
    night_wind: str | None = None


class WeatherWindow(BaseModel):
    location_ref: LocationRef
    current_weather: CurrentWeather | None = None
    forecast_days: list[ForecastDay] = Field(default_factory=list)
    covered_dates: list[date] = Field(default_factory=list)
    missing_dates: list[date] = Field(default_factory=list)
    coverage_end_date: date | None = None
    warnings: list[str] = Field(default_factory=list)


class GeoResolution(BaseModel):
    location_ref: LocationRef
    aliases: list[str] = Field(default_factory=list)
    nearby_hints: list[str] = Field(default_factory=list)


class TransportLegEstimate(BaseModel):
    origin: LocationRef
    destination: LocationRef
    mode: TravelMode
    distance_meters: int | None = None
    duration_seconds: int | None = None
    price_estimate: float | None = None
    available: bool = True
    provider_route_type: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RouteStop(BaseModel):
    order: int
    location_ref: LocationRef


class RouteSegment(BaseModel):
    origin: LocationRef
    destination: LocationRef
    mode: TravelMode
    distance_meters: int | None = None
    duration_seconds: int | None = None
    provider_route_type: str | None = None
    warnings: list[str] = Field(default_factory=list)


class RoutePlan(BaseModel):
    ordered: bool
    optimized: bool
    mode: TravelMode
    round_trip: bool = False
    stops: list[RouteStop]
    segments: list[RouteSegment]
    total_distance_meters: int = 0
    total_duration_seconds: int = 0
    optimization_notes: list[str] = Field(default_factory=list)


class ToolSource(BaseModel):
    provider: str
    capability_flags: list[str] = Field(default_factory=list)


class ToolEnvelope(BaseModel):
    ok: bool
    tool_name: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[ToolError] = Field(default_factory=list)
    source: ToolSource


class ToolMetadata(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class MetadataResponse(BaseModel):
    provider: str
    supported_modes: list[TravelMode]
    tools: list[ToolMetadata]
    capability_matrix: dict[str, list[str]]


class LocationLookupInput(BaseModel):
    query: str | None = None
    longitude: float | None = None
    latitude: float | None = None
    city_hint: str | None = None

    @model_validator(mode="after")
    def validate_one_of(self) -> "LocationLookupInput":
        has_query = bool(self.query)
        has_coordinates = self.longitude is not None and self.latitude is not None
        if not has_query and not has_coordinates:
            raise ValueError("Either query or both longitude/latitude must be provided")
        return self


class SearchLocationsRequest(BaseModel):
    query: str
    role: str = "destination"
    city_hint: str | None = None
    city_limit: bool = False
    limit: int = Field(default=5, ge=1, le=10)


class SearchLocationsData(BaseModel):
    candidates: list[LocationCandidate]


class RecommendDestinationsRequest(BaseModel):
    context: TravelAgentContext
    limit: int = Field(default=5, ge=1, le=10)
    exclude_destinations: list[str] = Field(default_factory=list)


class RecommendDestinationsData(BaseModel):
    recommended_destinations: list[RecommendedDestination]


class GetWeatherWindowRequest(BaseModel):
    location: LocationLookupInput
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def validate_window(self) -> "GetWeatherWindowRequest":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be later than or equal to start_date")
        return self


class GetWeatherWindowData(BaseModel):
    weather_window: WeatherWindow


class ResolveGeographyRequest(BaseModel):
    location_name: str | None = None
    coordinates: Coordinates | None = None

    @model_validator(mode="after")
    def validate_source(self) -> "ResolveGeographyRequest":
        if not self.location_name and not self.coordinates:
            raise ValueError("Either location_name or coordinates must be provided")
        return self


class ResolveGeographyData(BaseModel):
    geography: GeoResolution


class EstimateTransportTimesRequest(BaseModel):
    origins: list[LocationLookupInput]
    destinations: list[LocationLookupInput]
    modes: list[TravelMode]

    @model_validator(mode="before")
    @classmethod
    def normalize_modes(cls, values: Any) -> Any:
        if isinstance(values, dict) and values.get("modes"):
            values["modes"] = [normalize_travel_mode(item) for item in values["modes"]]
        return values


class EstimateTransportTimesData(BaseModel):
    estimates: list[TransportLegEstimate]


class PlanRouteRequest(BaseModel):
    stops: list[LocationLookupInput] = Field(min_length=2, max_length=10)
    mode: TravelMode = TravelMode.DRIVING
    ordered: bool = True
    round_trip: bool = False
    optimize: bool = False

    @model_validator(mode="before")
    @classmethod
    def normalize_mode(cls, values: Any) -> Any:
        if isinstance(values, dict) and values.get("mode"):
            values["mode"] = normalize_travel_mode(values["mode"])
        return values


class PlanRouteData(BaseModel):
    route_plan: RoutePlan

from __future__ import annotations

from datetime import timedelta

from ..data.destinations import CURATED_DESTINATIONS
from ..enums import Pace, TravelMode
from ..schemas import (
    DestinationProfile,
    RecommendDestinationsRequest,
    RecommendedDestination,
    ScoreBreakdown,
)
from .geography import GeographyService

PREFERENCE_ALIASES = {
    "自然风景": "自然风景",
    "自然风光": "自然风景",
    "山水": "自然风景",
    "海边": "海边",
    "美食": "美食",
    "低拥挤度": "低拥挤度",
    "慢节奏": "慢节奏",
    "城市休闲": "城市休闲",
    "人文": "人文",
}


class DestinationRecommendationService:
    def __init__(self, geography_service: GeographyService) -> None:
        self.geography_service = geography_service

    async def recommend(self, request: RecommendDestinationsRequest) -> list[RecommendedDestination]:
        trip_days = request.context.travel_time.trip_days
        travel_months = _travel_months(request.context.travel_time.start_date, request.context.travel_time.end_date)
        normalized_preferences = [_normalize_preference(item) for item in request.context.preferences]
        requested_modes = request.context.travel_mode or [TravelMode.HIGH_SPEED_RAIL]

        scored: list[RecommendedDestination] = []
        for profile in CURATED_DESTINATIONS:
            if profile.destination in request.exclude_destinations:
                continue
            estimated_total_cost = profile.daily_budget_per_person * trip_days * request.context.people_count
            estimated_total_cost += int(request.context.budget.max_budget * 0.15)

            score_breakdown = ScoreBreakdown(
                preference=self._preference_score(profile, normalized_preferences),
                season=self._season_score(profile, travel_months),
                budget=self._budget_score(estimated_total_cost, request.context.budget.max_budget),
                transport=self._transport_score(profile, requested_modes),
                pace=self._pace_score(profile, request.context.pace),
            )
            score = round(
                score_breakdown.preference
                + score_breakdown.season
                + score_breakdown.budget
                + score_breakdown.transport
                + score_breakdown.pace,
                2,
            )
            why = self._reasons(profile, normalized_preferences, requested_modes, score_breakdown)
            scored.append(
                RecommendedDestination(
                    destination=profile.destination,
                    profile=profile,
                    score=score,
                    score_breakdown=score_breakdown,
                    why_recommended=why,
                    estimated_total_cost=estimated_total_cost,
                )
            )

        ranked = sorted(scored, key=lambda item: item.score, reverse=True)[: request.limit]
        for item in ranked:
            try:
                item.location_ref = await self.geography_service.resolve_lookup(
                    self._lookup_for_destination(item.profile)
                )
            except Exception:
                item.location_ref = None
        return ranked

    @staticmethod
    def _lookup_for_destination(profile: DestinationProfile):
        from ..schemas import LocationLookupInput

        return LocationLookupInput(query=profile.destination)

    @staticmethod
    def _preference_score(profile: DestinationProfile, preferences: list[str]) -> float:
        if not preferences:
            return 20.0
        matches = 0
        for preference in preferences:
            if preference in profile.theme_tags:
                matches += 1
            elif preference == "低拥挤度" and profile.crowd_level.value == "low":
                matches += 1
            elif preference == "慢节奏" and "慢节奏" in profile.theme_tags:
                matches += 1
        return round(40.0 * matches / len(preferences), 2)

    @staticmethod
    def _season_score(profile: DestinationProfile, travel_months: set[int]) -> float:
        if not travel_months:
            return 10.0
        hits = len(travel_months.intersection(set(profile.best_months)))
        return round(20.0 * hits / len(travel_months), 2)

    @staticmethod
    def _budget_score(estimated_total_cost: int, max_budget: int) -> float:
        if estimated_total_cost <= max_budget:
            return 20.0
        overflow_ratio = min((estimated_total_cost - max_budget) / max_budget, 1.0)
        return round(max(0.0, 20.0 * (1.0 - overflow_ratio)), 2)

    @staticmethod
    def _transport_score(profile: DestinationProfile, requested_modes: list[TravelMode]) -> float:
        if not requested_modes:
            return 10.0
        supported = len(set(requested_modes).intersection(set(profile.transport_friendliness)))
        return round(15.0 * supported / len(requested_modes), 2)

    @staticmethod
    def _pace_score(profile: DestinationProfile, pace: Pace) -> float:
        if pace == Pace.RELAXED:
            if "慢节奏" in profile.theme_tags or profile.crowd_level.value == "low":
                return 5.0
            return 2.0
        if pace == Pace.FAST_PACED:
            if profile.crowd_level.value == "high":
                return 4.0
            return 3.0
        return 4.0

    @staticmethod
    def _reasons(
        profile: DestinationProfile,
        preferences: list[str],
        requested_modes: list[TravelMode],
        score_breakdown: ScoreBreakdown,
    ) -> list[str]:
        reasons: list[str] = []
        matched_preferences = [item for item in preferences if item in profile.theme_tags]
        if matched_preferences:
            reasons.append(f"匹配偏好：{'、'.join(matched_preferences)}")
        if "低拥挤度" in preferences and profile.crowd_level.value == "low":
            reasons.append("拥挤度较低，更适合轻松行程")
        supported_modes = [mode.value for mode in requested_modes if mode in profile.transport_friendliness]
        if supported_modes:
            reasons.append(f"交通可达性较好：{', '.join(supported_modes)}")
        reasons.append(f"综合得分 {score_breakdown.preference + score_breakdown.season + score_breakdown.budget + score_breakdown.transport + score_breakdown.pace:.1f}")
        return reasons


def _travel_months(start_date, end_date) -> set[int]:
    cursor = start_date
    months: set[int] = set()
    while cursor <= end_date:
        months.add(cursor.month)
        cursor += timedelta(days=1)
    return months


def _normalize_preference(preference: str) -> str:
    return PREFERENCE_ALIASES.get(preference, preference)


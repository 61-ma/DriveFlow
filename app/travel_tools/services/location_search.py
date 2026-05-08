from __future__ import annotations

from ..errors import ProviderNoResultError
from ..schemas import LocationCandidate, LocationRef, MatchType, SearchLocationsRequest


class LocationSearchService:
    def __init__(self, provider) -> None:
        self.provider = provider

    async def search(self, request: SearchLocationsRequest) -> list[LocationCandidate]:
        candidates: list[LocationCandidate] = []
        seen: set[str] = set()

        try:
            tips = await self.provider.input_tips(
                request.query,
                city=request.city_hint,
                city_limit=request.city_limit,
                limit=request.limit,
            )
        except ProviderNoResultError:
            tips = {"tips": []}

        for tip in tips.get("tips", []):
            candidate = self._candidate_from_tip(tip, request.query)
            if not candidate:
                continue
            dedupe_key = self._candidate_key(candidate)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            candidates.append(candidate)

        if len(candidates) < request.limit:
            try:
                poi_search = await self.provider.poi_search(
                    request.query,
                    city=request.city_hint,
                    page_size=request.limit,
                )
            except ProviderNoResultError:
                poi_search = {"pois": []}
            for poi in poi_search.get("pois", []):
                candidate = self._candidate_from_poi(poi, request.query)
                dedupe_key = self._candidate_key(candidate)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                candidates.append(candidate)
                if len(candidates) >= request.limit:
                    break

        if not candidates:
            geocode = await self.provider.geocode(request.query, city=request.city_hint)
            geocodes = geocode.get("geocodes", [])
            for item in geocodes[: request.limit]:
                candidate = self._candidate_from_geocode(item, request.query)
                dedupe_key = self._candidate_key(candidate)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                candidates.append(candidate)

        return candidates[: request.limit]

    @staticmethod
    def _candidate_from_tip(tip: dict, query: str) -> LocationCandidate | None:
        name = (tip.get("name") or "").strip()
        if not name:
            return None
        longitude, latitude = _split_location(tip.get("location"))
        location_ref = LocationRef(
            name=name,
            display_name=_display_name(name, tip.get("district"), tip.get("address")),
            adcode=tip.get("adcode"),
            citycode=tip.get("citycode"),
            province=None,
            city=tip.get("district"),
            district=tip.get("district"),
            longitude=longitude,
            latitude=latitude,
            poi_id=tip.get("id"),
            confidence=0.82,
        )
        return LocationCandidate(
            location_ref=location_ref,
            match_type=_infer_match_type(name, tip.get("typecode")),
            query_text=query,
            matched_fields=["name", "district"],
        )

    @staticmethod
    def _candidate_from_poi(poi: dict, query: str) -> LocationCandidate:
        longitude, latitude = _split_location(poi.get("location"))
        name = poi.get("name", "")
        location_ref = LocationRef(
            name=name,
            display_name=_display_name(name, poi.get("adname"), poi.get("cityname")),
            adcode=poi.get("adcode"),
            citycode=poi.get("citycode"),
            province=poi.get("pname"),
            city=poi.get("cityname"),
            district=poi.get("adname"),
            longitude=longitude,
            latitude=latitude,
            poi_id=poi.get("id"),
            confidence=0.9,
        )
        return LocationCandidate(
            location_ref=location_ref,
            match_type=_infer_match_type(name, poi.get("typecode")),
            query_text=query,
            matched_fields=["name", "city", "district"],
        )

    @staticmethod
    def _candidate_from_geocode(item: dict, query: str) -> LocationCandidate:
        longitude, latitude = _split_location(item.get("location"))
        city_value = item.get("city")
        city_name = city_value if isinstance(city_value, str) else ",".join(city_value or [])
        name = item.get("formatted_address") or item.get("district") or query
        location_ref = LocationRef(
            name=query,
            display_name=name,
            adcode=item.get("adcode"),
            province=item.get("province"),
            city=city_name,
            district=item.get("district"),
            longitude=longitude,
            latitude=latitude,
            confidence=0.78,
        )
        return LocationCandidate(
            location_ref=location_ref,
            match_type=MatchType.CITY,
            query_text=query,
            matched_fields=["formatted_address"],
        )

    @staticmethod
    def _candidate_key(candidate: LocationCandidate) -> str:
        location_ref = candidate.location_ref
        if location_ref.poi_id:
            return f"poi:{location_ref.poi_id}"
        if location_ref.coordinate_string:
            return f"coord:{location_ref.coordinate_string}|{location_ref.name}"
        return f"name:{location_ref.display_name}"


def _split_location(raw_value: str | None) -> tuple[float | None, float | None]:
    if not raw_value or "," not in raw_value:
        return None, None
    longitude_str, latitude_str = raw_value.split(",", 1)
    return float(longitude_str), float(latitude_str)


def _display_name(name: str, district: str | None, address: str | None) -> str:
    parts = [part for part in [district, address] if part]
    if not parts:
        return name
    return f"{name} ({' / '.join(parts)})"


def _infer_match_type(name: str, type_code: str | None) -> MatchType:
    lowered_name = name.lower()
    if "机场" in name or "airport" in lowered_name:
        return MatchType.AIRPORT
    if "站" in name or "station" in lowered_name:
        return MatchType.STATION
    if type_code and type_code.startswith("190"):
        return MatchType.STATION
    if type_code and type_code.startswith("230"):
        return MatchType.AIRPORT
    if type_code and type_code.startswith("090"):
        return MatchType.CITY
    return MatchType.POI

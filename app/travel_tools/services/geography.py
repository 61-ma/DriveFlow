from __future__ import annotations

from ..errors import ProviderNoResultError, ToolInputError
from ..schemas import (
    GeoResolution,
    LocationLookupInput,
    LocationRef,
    ResolveGeographyRequest,
    SearchLocationsRequest,
)
from .location_search import LocationSearchService, _split_location


class GeographyService:
    def __init__(self, provider, location_search: LocationSearchService) -> None:
        self.provider = provider
        self.location_search = location_search

    async def resolve_lookup(self, lookup: LocationLookupInput) -> LocationRef:
        if lookup.query:
            candidates = await self.location_search.search(
                SearchLocationsRequest(
                    query=lookup.query,
                    city_hint=lookup.city_hint,
                    limit=1,
                )
            )
            if not candidates:
                raise ProviderNoResultError(
                    code="provider_no_result",
                    message=f"No location found for query: {lookup.query}",
                )
            return candidates[0].location_ref

        regeo = await self.provider.reverse_geocode(lookup.longitude, lookup.latitude)
        return self._location_from_regeo(regeo, lookup.longitude, lookup.latitude)

    async def resolve_geography(self, request: ResolveGeographyRequest) -> GeoResolution:
        if request.location_name:
            location_ref = await self.resolve_lookup(LocationLookupInput(query=request.location_name))
        elif request.coordinates:
            location_ref = await self.resolve_lookup(
                LocationLookupInput(
                    longitude=request.coordinates.longitude,
                    latitude=request.coordinates.latitude,
                )
            )
        else:
            raise ToolInputError(code="invalid_input", message="Missing location input")

        aliases = [item for item in {location_ref.name, location_ref.city, location_ref.district} if item]
        nearby_hints = [item for item in {location_ref.province, location_ref.city, location_ref.district} if item]
        return GeoResolution(location_ref=location_ref, aliases=aliases, nearby_hints=nearby_hints)

    @staticmethod
    def _location_from_regeo(
        payload: dict,
        longitude: float | None,
        latitude: float | None,
    ) -> LocationRef:
        regeo = payload.get("regeocode", {})
        component = regeo.get("addressComponent", {})
        return LocationRef(
            name=regeo.get("formatted_address") or component.get("district") or "已解析地点",
            display_name=regeo.get("formatted_address") or component.get("district") or "已解析地点",
            adcode=component.get("adcode"),
            citycode=component.get("citycode"),
            province=component.get("province"),
            city=_extract_city_name(component.get("city")),
            district=component.get("district"),
            longitude=longitude,
            latitude=latitude,
            confidence=0.88,
        )


def _extract_city_name(raw_city) -> str | None:
    if isinstance(raw_city, list):
        return ",".join(raw_city) if raw_city else None
    return raw_city

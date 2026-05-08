from __future__ import annotations

from ..enums import TravelMode
from ..schemas import (
    EstimateTransportTimesRequest,
    LocationRef,
    TransportLegEstimate,
)
from .geography import GeographyService


class TransportService:
    def __init__(self, provider, geography_service: GeographyService) -> None:
        self.provider = provider
        self.geography_service = geography_service

    async def estimate(self, request: EstimateTransportTimesRequest) -> list[TransportLegEstimate]:
        origins = [await self.geography_service.resolve_lookup(item) for item in request.origins]
        destinations = [await self.geography_service.resolve_lookup(item) for item in request.destinations]
        estimates: list[TransportLegEstimate] = []
        for origin in origins:
            for destination in destinations:
                for mode in request.modes:
                    estimates.append(await self.estimate_leg(origin, destination, mode))
        return estimates

    async def estimate_leg(
        self,
        origin: LocationRef,
        destination: LocationRef,
        mode: TravelMode,
    ) -> TransportLegEstimate:
        if origin.coordinate_string == destination.coordinate_string:
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_meters=0,
                duration_seconds=0,
                provider_route_type="same_point",
            )

        if mode == TravelMode.FLIGHT:
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                available=False,
                provider_route_type="unsupported",
                warnings=["mode_not_supported_by_current_provider"],
            )

        if mode == TravelMode.DRIVING:
            payload = await self.provider.distance_matrix(
                [origin.coordinate_string],
                destination.coordinate_string,
                route_type="driving",
            )
            result = (payload.get("results") or [{}])[0]
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_meters=_safe_int(result.get("distance")),
                duration_seconds=_safe_int(result.get("duration")),
                provider_route_type="distance_matrix_driving",
            )

        if mode == TravelMode.WALKING:
            payload = await self.provider.route(
                mode="walking",
                origin=origin.coordinate_string,
                destination=destination.coordinate_string,
            )
            path = ((payload.get("route") or {}).get("paths") or [{}])[0]
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_meters=_safe_int(path.get("distance")),
                duration_seconds=_safe_int(path.get("duration")),
                provider_route_type="walking",
            )

        if mode == TravelMode.BICYCLING:
            payload = await self.provider.route(
                mode="bicycling",
                origin=origin.coordinate_string,
                destination=destination.coordinate_string,
            )
            route = payload.get("data") or payload.get("route") or {}
            paths = route.get("paths") or [route]
            path = paths[0] if paths else {}
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                distance_meters=_safe_int(path.get("distance")),
                duration_seconds=_safe_int(path.get("duration")),
                provider_route_type="bicycling",
            )

        transit_payload = await self.provider.route(
            mode="high_speed_rail" if mode == TravelMode.HIGH_SPEED_RAIL else "transit",
            origin=origin.coordinate_string,
            destination=destination.coordinate_string,
            city=origin.citycode or origin.city or origin.name,
            cityd=destination.citycode or destination.city or destination.name,
        )
        transits = ((transit_payload.get("route") or {}).get("transits") or [])
        transit = transits[0] if transits else {}
        segments = transit.get("segments") or []
        has_railway = any(segment.get("railway") for segment in segments)
        if mode == TravelMode.HIGH_SPEED_RAIL and not has_railway:
            return TransportLegEstimate(
                origin=origin,
                destination=destination,
                mode=mode,
                available=False,
                provider_route_type="transit_without_railway",
                warnings=["railway_segment_not_found"],
            )
        warnings: list[str] = []
        if mode == TravelMode.HIGH_SPEED_RAIL and has_railway:
            warnings.append("railway_segment_detected_from_transit_route")
        return TransportLegEstimate(
            origin=origin,
            destination=destination,
            mode=mode,
            distance_meters=_safe_int(transit.get("distance")),
            duration_seconds=_safe_int(transit.get("duration")),
            price_estimate=_safe_float(transit.get("cost")),
            provider_route_type="transit_integrated",
            warnings=warnings,
        )


def _safe_int(value) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def _safe_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


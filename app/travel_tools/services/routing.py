from __future__ import annotations

from ..errors import ToolInputError
from ..schemas import PlanRouteRequest, RoutePlan, RouteSegment, RouteStop
from .geography import GeographyService
from .transport import TransportService


class RoutingService:
    def __init__(self, geography_service: GeographyService, transport_service: TransportService) -> None:
        self.geography_service = geography_service
        self.transport_service = transport_service

    async def plan_route(self, request: PlanRouteRequest) -> RoutePlan:
        if request.optimize and len(request.stops) > 10:
            raise ToolInputError(
                code="too_many_stops",
                message="Route optimization supports at most 10 stops",
            )

        resolved_stops = [await self.geography_service.resolve_lookup(item) for item in request.stops]
        ordered_locations = resolved_stops
        optimization_notes: list[str] = []

        if not request.ordered and request.optimize and len(resolved_stops) > 2:
            ordered_locations = await self._optimize_locations(resolved_stops, request.mode)
            optimization_notes.append("Used greedy nearest-neighbor optimization for intermediate stops")
        elif not request.ordered:
            optimization_notes.append("Input marked unordered but optimize is disabled; kept original order")

        segments: list[RouteSegment] = []
        segment_pairs = list(zip(ordered_locations, ordered_locations[1:]))
        if request.round_trip:
            segment_pairs.append((ordered_locations[-1], ordered_locations[0]))

        for origin, destination in segment_pairs:
            leg = await self.transport_service.estimate_leg(origin, destination, request.mode)
            segments.append(
                RouteSegment(
                    origin=origin,
                    destination=destination,
                    mode=request.mode,
                    distance_meters=leg.distance_meters,
                    duration_seconds=leg.duration_seconds,
                    provider_route_type=leg.provider_route_type,
                    warnings=leg.warnings,
                )
            )

        return RoutePlan(
            ordered=request.ordered,
            optimized=request.optimize,
            mode=request.mode,
            round_trip=request.round_trip,
            stops=[
                RouteStop(order=index + 1, location_ref=location)
                for index, location in enumerate(ordered_locations)
            ],
            segments=segments,
            total_distance_meters=sum(item.distance_meters or 0 for item in segments),
            total_duration_seconds=sum(item.duration_seconds or 0 for item in segments),
            optimization_notes=optimization_notes,
        )

    async def _optimize_locations(self, locations, mode):
        start = locations[0]
        end = locations[-1]
        remaining = locations[1:-1]
        ordered = [start]
        current = start
        while remaining:
            best_index = 0
            best_cost = None
            for index, candidate in enumerate(remaining):
                leg = await self.transport_service.estimate_leg(current, candidate, mode)
                cost = leg.duration_seconds if leg.duration_seconds is not None else float("inf")
                if best_cost is None or cost < best_cost:
                    best_cost = cost
                    best_index = index
            ordered.append(remaining.pop(best_index))
            current = ordered[-1]
        ordered.append(end)
        return ordered


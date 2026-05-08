from __future__ import annotations

from enum import Enum


class Pace(str, Enum):
    RELAXED = "relaxed"
    BALANCED = "balanced"
    FAST_PACED = "fast_paced"


class TravelMode(str, Enum):
    FLIGHT = "flight"
    HIGH_SPEED_RAIL = "high_speed_rail"
    DRIVING = "driving"
    TRANSIT = "transit"
    WALKING = "walking"
    BICYCLING = "bicycling"


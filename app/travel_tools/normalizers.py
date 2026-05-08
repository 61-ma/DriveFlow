from __future__ import annotations

from .enums import Pace, TravelMode

TRAVEL_MODE_ALIASES = {
    "飞机": TravelMode.FLIGHT,
    "航班": TravelMode.FLIGHT,
    "flight": TravelMode.FLIGHT,
    "高铁": TravelMode.HIGH_SPEED_RAIL,
    "火车": TravelMode.HIGH_SPEED_RAIL,
    "rail": TravelMode.HIGH_SPEED_RAIL,
    "high_speed_rail": TravelMode.HIGH_SPEED_RAIL,
    "自驾": TravelMode.DRIVING,
    "driving": TravelMode.DRIVING,
    "公交": TravelMode.TRANSIT,
    "地铁": TravelMode.TRANSIT,
    "transit": TravelMode.TRANSIT,
    "步行": TravelMode.WALKING,
    "walking": TravelMode.WALKING,
    "骑行": TravelMode.BICYCLING,
    "bicycling": TravelMode.BICYCLING,
}

PACE_ALIASES = {
    "relaxed": Pace.RELAXED,
    "balanced": Pace.BALANCED,
    "fast_paced": Pace.FAST_PACED,
    "轻松": Pace.RELAXED,
    "休闲": Pace.RELAXED,
    "平衡": Pace.BALANCED,
    "均衡": Pace.BALANCED,
    "紧凑": Pace.FAST_PACED,
}


def normalize_travel_mode(value: str | TravelMode) -> TravelMode:
    if isinstance(value, TravelMode):
        return value
    normalized = TRAVEL_MODE_ALIASES.get(value.strip())
    if normalized:
        return normalized
    raise ValueError(f"Unsupported travel mode: {value}")


def normalize_pace(value: str | Pace) -> Pace:
    if isinstance(value, Pace):
        return value
    normalized = PACE_ALIASES.get(value.strip())
    if normalized:
        return normalized
    raise ValueError(f"Unsupported pace: {value}")

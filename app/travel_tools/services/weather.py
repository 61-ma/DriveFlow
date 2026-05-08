from __future__ import annotations

from datetime import timedelta

from ..schemas import (
    CurrentWeather,
    ForecastDay,
    GetWeatherWindowRequest,
    WeatherWindow,
)
from .geography import GeographyService


class WeatherService:
    def __init__(self, provider, geography_service: GeographyService) -> None:
        self.provider = provider
        self.geography_service = geography_service

    async def get_weather_window(self, request: GetWeatherWindowRequest) -> WeatherWindow:
        location_ref = await self.geography_service.resolve_lookup(request.location)
        city_code = location_ref.adcode or location_ref.citycode or location_ref.city or location_ref.name

        live_payload = await self.provider.weather(city_code, extensions="base")
        forecast_payload = await self.provider.weather(city_code, extensions="all")

        live_item = (live_payload.get("lives") or [{}])[0]
        current_weather = CurrentWeather(
            weather=live_item.get("weather"),
            temperature_celsius=_safe_int(live_item.get("temperature")),
            humidity=live_item.get("humidity"),
            report_time=live_item.get("reporttime"),
        )

        casts = []
        forecasts = forecast_payload.get("forecasts") or []
        if forecasts:
            casts = forecasts[0].get("casts", [])

        forecast_days: list[ForecastDay] = []
        covered_dates = []
        for cast in casts:
            cast_date = _safe_date(cast.get("date"))
            if cast_date is None:
                continue
            if request.start_date <= cast_date <= request.end_date:
                forecast_days.append(
                    ForecastDay(
                        date=cast_date,
                        day_weather=cast.get("dayweather"),
                        night_weather=cast.get("nightweather"),
                        day_temp_celsius=_safe_int(cast.get("daytemp")),
                        night_temp_celsius=_safe_int(cast.get("nighttemp")),
                        day_wind=cast.get("daywind"),
                        night_wind=cast.get("nightwind"),
                    )
                )
                covered_dates.append(cast_date)

        requested_dates = []
        cursor = request.start_date
        while cursor <= request.end_date:
            requested_dates.append(cursor)
            cursor += timedelta(days=1)

        covered_date_set = set(covered_dates)
        missing_dates = [item for item in requested_dates if item not in covered_date_set]
        warnings: list[str] = []
        coverage_end_date = max(covered_dates) if covered_dates else None
        if missing_dates:
            warnings.append("forecast_window_exceeds_provider_horizon")

        return WeatherWindow(
            location_ref=location_ref,
            current_weather=current_weather,
            forecast_days=forecast_days,
            covered_dates=covered_dates,
            missing_dates=missing_dates,
            coverage_end_date=coverage_end_date,
            warnings=warnings,
        )


def _safe_int(value) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _safe_date(value: str | None):
    if not value:
        return None
    from datetime import date

    return date.fromisoformat(value)


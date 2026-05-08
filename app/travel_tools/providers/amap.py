from __future__ import annotations

import json
from typing import Any

import httpx

from ..cache import TTLMemoryCache
from ..errors import (
    ProviderAuthError,
    ProviderNoResultError,
    ProviderRateLimitError,
    ProviderResponseError,
)
from ..settings import TravelToolsSettings


class AmapWebClient:
    def __init__(
        self,
        settings: TravelToolsSettings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self._client = client
        self._cache: TTLMemoryCache[dict[str, Any]] = TTLMemoryCache()

    async def input_tips(
        self,
        keywords: str,
        *,
        city: str | None = None,
        city_limit: bool = False,
        limit: int = 10,
    ) -> dict[str, Any]:
        params = {
            "keywords": keywords,
            "datatype": "all",
            "citylimit": "true" if city_limit else "false",
        }
        if city:
            params["city"] = city
        data = await self._request_json("/v3/assistant/inputtips", params, ttl_seconds=900)
        tips = data.get("tips", [])[:limit]
        return {"tips": tips}

    async def poi_search(
        self,
        keywords: str,
        *,
        city: str | None = None,
        page_size: int = 10,
    ) -> dict[str, Any]:
        params = {
            "keywords": keywords,
            "offset": page_size,
            "extensions": "base",
        }
        if city:
            params["city"] = city
        return await self._request_json("/v3/place/text", params, ttl_seconds=900)

    async def geocode(
        self,
        address: str,
        *,
        city: str | None = None,
    ) -> dict[str, Any]:
        params = {"address": address}
        if city:
            params["city"] = city
        return await self._request_json("/v3/geocode/geo", params, ttl_seconds=86400)

    async def reverse_geocode(
        self,
        longitude: float,
        latitude: float,
    ) -> dict[str, Any]:
        params = {
            "location": f"{longitude},{latitude}",
            "extensions": "all",
        }
        return await self._request_json("/v3/geocode/regeo", params, ttl_seconds=86400)

    async def weather(self, city: str, *, extensions: str) -> dict[str, Any]:
        params = {"city": city, "extensions": extensions}
        return await self._request_json("/v3/weather/weatherInfo", params, ttl_seconds=1800)

    async def distance_matrix(
        self,
        origins: list[str],
        destination: str,
        *,
        route_type: str = "driving",
    ) -> dict[str, Any]:
        params = {
            "origins": "|".join(origins),
            "destination": destination,
            "type": self._distance_type(route_type),
        }
        return await self._request_json("/v3/distance", params, ttl_seconds=900)

    async def route(
        self,
        *,
        mode: str,
        origin: str,
        destination: str,
        city: str | None = None,
        cityd: str | None = None,
    ) -> dict[str, Any]:
        path, params = self._route_params(
            mode=mode,
            origin=origin,
            destination=destination,
            city=city,
            cityd=cityd,
        )
        return await self._request_json(path, params, ttl_seconds=900)

    def _route_params(
        self,
        *,
        mode: str,
        origin: str,
        destination: str,
        city: str | None,
        cityd: str | None,
    ) -> tuple[str, dict[str, Any]]:
        if mode == "driving":
            return "/v3/direction/driving", {"origin": origin, "destination": destination}
        if mode == "walking":
            return "/v3/direction/walking", {"origin": origin, "destination": destination}
        if mode == "bicycling":
            return "/v4/direction/bicycling", {"origin": origin, "destination": destination}
        if mode in {"transit", "high_speed_rail"}:
            params: dict[str, Any] = {"origin": origin, "destination": destination}
            if city:
                params["city"] = city
            if cityd:
                params["cityd"] = cityd
            return "/v3/direction/transit/integrated", params
        raise ValueError(f"Unsupported route mode: {mode}")

    @staticmethod
    def _distance_type(route_type: str) -> str:
        return {
            "driving": "1",
            "walking": "3",
            "transit": "0",
        }.get(route_type, "1")

    async def _request_json(
        self,
        path: str,
        params: dict[str, Any],
        *,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        if not self.settings.amap_web_key:
            raise ProviderAuthError(
                code="provider_auth_failed",
                message="AMAP_WEB_KEY is not configured",
            )

        request_params = dict(params)
        request_params["key"] = self.settings.amap_web_key
        cache_key = json.dumps([path, sorted(request_params.items())], ensure_ascii=False)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        response_payload: dict[str, Any] | None = None
        last_exception: Exception | None = None
        for _ in range(self.settings.amap_max_retries + 1):
            try:
                response = await self._send_request(path, request_params)
                response.raise_for_status()
                response_payload = response.json()
                self._raise_for_payload_errors(response_payload)
                self._cache.set(cache_key, response_payload, ttl_seconds)
                return response_payload
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                if 500 <= exc.response.status_code < 600:
                    continue
                raise ProviderResponseError(
                    code="provider_http_error",
                    message="Provider returned unexpected status code",
                    details={"status_code": exc.response.status_code},
                ) from exc
            except httpx.HTTPError as exc:
                last_exception = exc
                continue

        raise ProviderResponseError(
            code="provider_unavailable",
            message="Provider request failed after retries",
            details={"exception": str(last_exception), "path": path, "params": params},
        )

    async def _send_request(self, path: str, params: dict[str, Any]) -> httpx.Response:
        if self._client is not None:
            return await self._client.get(path, params=params)
        async with httpx.AsyncClient(
            base_url=self.settings.amap_base_url,
            timeout=self.settings.amap_timeout_seconds,
        ) as client:
            return await client.get(path, params=params)

    def _raise_for_payload_errors(self, payload: dict[str, Any]) -> None:
        if payload.get("status") == "1":
            return

        info = payload.get("info", "")
        info_code = payload.get("infocode", "")
        details = {"info": info, "infocode": info_code}
        if info_code in {"10001", "10003", "10004", "10008", "10009", "10010"}:
            raise ProviderAuthError(
                code="provider_auth_failed",
                message="Provider authentication failed",
                details=details,
            )
        if info_code in {"10019", "10020", "10021", "10044"} or "LIMIT" in info.upper():
            raise ProviderRateLimitError(
                code="provider_rate_limited",
                message="Provider rate limit reached",
                details=details,
            )
        if info_code in {"30000", "30001"}:
            raise ProviderNoResultError(
                code="provider_no_result",
                message="Provider returned no result",
                details=details,
            )
        raise ProviderResponseError(
            code="provider_response_invalid",
            message="Provider returned an invalid payload",
            details=details,
        )

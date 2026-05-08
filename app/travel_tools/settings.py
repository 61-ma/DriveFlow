from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class TravelToolsSettings(BaseSettings):
    amap_web_key: str = ""
    amap_base_url: str = "https://restapi.amap.com"
    amap_timeout_seconds: float = 3.0
    amap_max_retries: int = 2
    travel_tools_cache_ttl_seconds: int = 900

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )


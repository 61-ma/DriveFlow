from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class TravelToolException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_error(self) -> ToolError:
        return ToolError(code=self.code, message=self.message, details=self.details)


class ProviderAuthError(TravelToolException):
    pass


class ProviderRateLimitError(TravelToolException):
    pass


class ProviderNoResultError(TravelToolException):
    pass


class ProviderResponseError(TravelToolException):
    pass


class ToolInputError(TravelToolException):
    pass


from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Stage(str, Enum):
    INITIATED = "initiated"
    CONFIRMING_INFO = "confirming_info"
    PLAN_GENERATED = "plan_generated"
    REVISING_PLAN = "revising_plan"
    PLAN_CONFIRMED = "plan_confirmed"
    SHARED = "shared"


class QuickAction(BaseModel):
    label: str
    value: str
    kind: str = "message"


class ConversationTurn(BaseModel):
    role: str
    text: str


class TravelRequest(BaseModel):
    destination: str | None = None
    days: int | None = None
    departure_city: str | None = None
    date_range: str | None = None
    budget: int | None = None
    preferences: list[str] = Field(default_factory=list)
    travel_style: str | None = None


class ItineraryDay(BaseModel):
    day: int
    city: str
    theme: str
    highlights: list[str] = Field(default_factory=list)
    transport: str
    hotel_level: str
    estimated_cost: int


class TravelPlan(BaseModel):
    title: str
    summary: str
    days: list[ItineraryDay] = Field(default_factory=list)
    total_estimated_cost: int
    tips: list[str] = Field(default_factory=list)


class ConversationState(BaseModel):
    session_id: str
    stage: Stage = Stage.INITIATED
    request: TravelRequest = Field(default_factory=TravelRequest)
    missing_slots: list[str] = Field(default_factory=list)
    plan: TravelPlan | None = None
    history: list[ConversationTurn] = Field(default_factory=list)


class MessageRequest(BaseModel):
    session_id: str
    text: str


class RevisionRequest(BaseModel):
    session_id: str
    user_feedback: str


class SessionActionRequest(BaseModel):
    session_id: str


class AssistantResponse(BaseModel):
    session_id: str
    stage: Stage
    message: str
    collected_info: dict[str, str] = Field(default_factory=dict)
    missing_info: list[str] = Field(default_factory=list)
    plan: TravelPlan | None = None
    actions: list[QuickAction] = Field(default_factory=list)
    history: list[ConversationTurn] = Field(default_factory=list)


class SceneHint(BaseModel):
    title: str
    utterance: str
    note: str


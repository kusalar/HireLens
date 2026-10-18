import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import (
    CalendarProviderType,
    CalendarSyncStatus,
    CalendarSyncDirection,
    CalendarSyncOperation,
    MeetingProviderType,
)


class CalendarConnectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    user_id: uuid.UUID
    provider: CalendarProviderType
    provider_account_id: Optional[str] = None
    provider_account_email: Optional[str] = None
    selected_calendar_id: str
    selected_calendar_name: str
    is_active: bool
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CalendarConnectionInitRequest(BaseModel):
    provider: CalendarProviderType
    redirect_uri: Optional[str] = None


class CalendarConnectionInitResponse(BaseModel):
    authorization_url: str
    state: str


class CalendarConnectionCallbackRequest(BaseModel):
    code: str
    state: str
    redirect_uri: Optional[str] = None


class CalendarItemRead(BaseModel):
    id: str
    name: str
    primary: bool = False
    read_only: bool = False


class CalendarSelectionUpdate(BaseModel):
    calendar_id: str = Field(..., min_length=1)
    calendar_name: str = Field(..., min_length=1)


class CalendarSyncLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    connection_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    direction: CalendarSyncDirection
    operation: CalendarSyncOperation
    status: str
    details: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime


class CalendarEventMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_id: uuid.UUID
    provider: CalendarProviderType
    meeting_link: Optional[str] = None
    meeting_provider: MeetingProviderType
    sync_status: CalendarSyncStatus
    last_synced_at: Optional[datetime] = None
    last_error: Optional[str] = None


class GenerateMeetingLinkRequest(BaseModel):
    meeting_provider: MeetingProviderType = MeetingProviderType.GOOGLE_MEET

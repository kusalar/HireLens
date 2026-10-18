import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import NotificationType, NotificationDeliveryStatus


class NotificationRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    recipient_user_id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[uuid.UUID] = None
    is_read: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    created_at_ist: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationRead]
    total: int
    unread_count: int
    page: int
    page_size: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationPreferenceRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    email_enabled: bool
    interview_notifications_enabled: bool
    application_status_notifications_enabled: bool
    candidate_email_updates_enabled: bool
    default_timezone: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationPreferenceUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    interview_notifications_enabled: Optional[bool] = None
    application_status_notifications_enabled: Optional[bool] = None
    candidate_email_updates_enabled: Optional[bool] = None
    default_timezone: Optional[str] = Field(None, min_length=2, max_length=50)


class EmailDeliveryLogRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    recipient_email: str
    event_type: str
    subject: str
    provider: str
    status: NotificationDeliveryStatus
    attempt_count: int
    last_attempt_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime
    created_at_ist: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class EmailDeliveryLogListResponse(BaseModel):
    items: List[EmailDeliveryLogRead]
    total: int
    page: int
    page_size: int

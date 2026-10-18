import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.models.enums import NotificationDeliveryStatus, UserRole
from app.core.timezone import format_ist
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationRead,
    NotificationListResponse,
    NotificationUnreadCountResponse,
    NotificationPreferenceRead,
    NotificationPreferenceUpdate,
    EmailDeliveryLogRead,
    EmailDeliveryLogListResponse,
)

router = APIRouter()


def _format_notification_read(notif) -> NotificationRead:
    return NotificationRead(
        id=notif.id,
        agency_id=notif.agency_id,
        recipient_user_id=notif.recipient_user_id,
        notification_type=notif.notification_type,
        title=notif.title,
        message=notif.message,
        related_entity_type=notif.related_entity_type,
        related_entity_id=notif.related_entity_id,
        is_read=notif.is_read,
        created_at=notif.created_at,
        read_at=notif.read_at,
        created_at_ist=format_ist(notif.created_at),
    )


def _format_delivery_log_read(log) -> EmailDeliveryLogRead:
    return EmailDeliveryLogRead(
        id=log.id,
        agency_id=log.agency_id,
        recipient_email=log.recipient_email,
        event_type=log.event_type,
        subject=log.subject,
        provider=log.provider,
        status=log.status,
        attempt_count=log.attempt_count,
        last_attempt_at=log.last_attempt_at,
        delivered_at=log.delivered_at,
        error_message=log.error_message,
        created_at=log.created_at,
        created_at_ist=format_ist(log.created_at),
    )


@router.get("", response_model=NotificationListResponse)
def list_my_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List in-app notifications for the authenticated user, scoped strictly to their agency."""
    service = NotificationService(db, current_user.agency_id)
    skip = (page - 1) * page_size
    items, total = service.list_user_notifications(
        current_user=current_user,
        unread_only=unread_only,
        skip=skip,
        limit=page_size,
    )
    unread_count = service.get_unread_count(current_user)
    return NotificationListResponse(
        items=[_format_notification_read(item) for item in items],
        total=total,
        unread_count=unread_count,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the real-time unread notification count for the navbar badge."""
    service = NotificationService(db, current_user.agency_id)
    count = service.get_unread_count(current_user)
    return NotificationUnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a specific notification as read. Fails if the notification belongs to another user."""
    service = NotificationService(db, current_user.agency_id)
    item = service.mark_as_read(notification_id, current_user)
    return _format_notification_read(item)


@router.post("/mark-all-read")
def mark_all_notifications_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all unread notifications as read for the current authenticated user."""
    service = NotificationService(db, current_user.agency_id)
    count = service.mark_all_read(current_user)
    return {"message": "All notifications marked as read", "marked_count": count}


@router.get("/settings", response_model=NotificationPreferenceRead)
def get_agency_notification_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the agency's notification preferences."""
    service = NotificationService(db, current_user.agency_id)
    return service.get_preferences(current_user)


@router.put("/settings", response_model=NotificationPreferenceRead)
def update_agency_notification_settings(
    data: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update notification preferences for the agency. Restricted to OWNER and ADMIN users."""
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER or ADMIN users can configure agency notification settings.",
        )
    service = NotificationService(db, current_user.agency_id)
    return service.update_preferences(
        current_user=current_user,
        email_enabled=data.email_enabled,
        interview_notifications_enabled=data.interview_notifications_enabled,
        application_status_notifications_enabled=data.application_status_notifications_enabled,
        candidate_email_updates_enabled=data.candidate_email_updates_enabled,
        default_timezone=data.default_timezone,
    )


@router.get("/delivery-logs", response_model=EmailDeliveryLogListResponse)
def list_email_delivery_logs(
    status_filter: Optional[NotificationDeliveryStatus] = Query(None, alias="status"),
    event_type: Optional[str] = Query(None),
    recipient_email: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List administrative email delivery logs. Restricted to OWNER and ADMIN users."""
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER or ADMIN users can view email delivery logs.",
        )
    service = NotificationService(db, current_user.agency_id)
    skip = (page - 1) * page_size
    items, total = service.list_delivery_logs(
        current_user=current_user,
        status_filter=status_filter,
        event_type=event_type,
        recipient_email=recipient_email,
        skip=skip,
        limit=page_size,
    )
    return EmailDeliveryLogListResponse(
        items=[_format_delivery_log_read(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/delivery-logs/{log_id}/retry", response_model=EmailDeliveryLogRead)
def retry_delivery_log(
    log_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retry a failed email delivery log. Restricted to OWNER and ADMIN users."""
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only OWNER or ADMIN users can retry email deliveries.",
        )
    service = NotificationService(db, current_user.agency_id)
    log = service.retry_delivery_log(log_id, current_user)
    return _format_delivery_log_read(log)

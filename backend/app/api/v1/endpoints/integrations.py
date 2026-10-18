import uuid
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.entities import User
from app.models.enums import (
    UserRole,
    CalendarProviderType,
    CalendarSyncOperation,
    MeetingProviderType,
)
from app.models.interview import Interview
from app.models.calendar import CalendarConnection, CalendarEventMapping, CalendarSyncJob
from app.schemas.calendar import (
    CalendarConnectionRead,
    CalendarConnectionInitRequest,
    CalendarConnectionInitResponse,
    CalendarConnectionCallbackRequest,
    CalendarItemRead,
    CalendarSelectionUpdate,
    CalendarSyncLogRead,
    CalendarEventMappingRead,
    GenerateMeetingLinkRequest,
)
from app.services.calendar_sync_service import CalendarSyncService
from app.services.calendar.factory import get_calendar_provider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/calendars", response_model=List[CalendarConnectionRead])
def list_calendar_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List calendar connections for the current user's agency.
    Recruiters see their own connections; Owners/Admins see all agency connections.
    """
    service = CalendarSyncService(db, current_user.agency_id)
    if current_user.role in (UserRole.OWNER, UserRole.ADMIN):
        return service.list_connections()
    return service.list_connections(user_id=current_user.id)


@router.post(
    "/calendars/init",
    response_model=CalendarConnectionInitResponse,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def initiate_calendar_connection(
    data: CalendarConnectionInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate OAuth authorization URL for Google or Microsoft Outlook."""
    service = CalendarSyncService(db, current_user.agency_id)
    return service.get_oauth_authorization_url(
        provider_type=data.provider,
        user_id=current_user.id,
        redirect_uri=data.redirect_uri,
    )


@router.post(
    "/calendars/callback",
    response_model=CalendarConnectionRead,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def handle_calendar_oauth_callback(
    data: CalendarConnectionCallbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Exchange authorization code and link external calendar connection."""
    service = CalendarSyncService(db, current_user.agency_id)
    conn = service.handle_oauth_callback(
        code=data.code,
        state=data.state,
        current_user=current_user,
        redirect_uri=data.redirect_uri,
    )
    return conn


@router.delete(
    "/calendars/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def disconnect_calendar_connection(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect and revoke an active calendar integration."""
    service = CalendarSyncService(db, current_user.agency_id)
    service.disconnect_connection(connection_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/calendars/{connection_id}/calendars",
    response_model=List[CalendarItemRead],
)
def list_available_calendars(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List calendars from external account to configure selected synchronization target."""
    service = CalendarSyncService(db, current_user.agency_id)
    return service.list_connection_calendars(connection_id)


@router.patch(
    "/calendars/{connection_id}/selection",
    response_model=CalendarConnectionRead,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def update_selected_calendar(
    connection_id: uuid.UUID,
    data: CalendarSelectionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Select the target calendar ID for interview event placement."""
    service = CalendarSyncService(db, current_user.agency_id)
    return service.update_selected_calendar(
        connection_id=connection_id,
        calendar_id=data.calendar_id,
        calendar_name=data.calendar_name,
    )


@router.post(
    "/calendars/{connection_id}/sync",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def trigger_calendar_resync(
    connection_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Trigger manual resynchronization sweep for an integration."""
    service = CalendarSyncService(db, current_user.agency_id)
    conn = service.get_connection(connection_id)
    if not conn or not conn.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active calendar connection not found.")

    # Find mapped interviews and enqueue update jobs
    mappings_stmt = select(CalendarEventMapping).where(
        CalendarEventMapping.agency_id == current_user.agency_id,
        CalendarEventMapping.connection_id == conn.id,
    )
    mappings = list(db.scalars(mappings_stmt).all())
    for m in mappings:
        service.enqueue_sync_job(conn.id, m.interview_id, CalendarSyncOperation.UPDATE)

    return {"status": "QUEUED", "enqueued_count": len(mappings)}


@router.get(
    "/calendars/sync-logs",
    response_model=List[CalendarSyncLogRead],
)
def list_calendar_sync_logs(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve audit and synchronization event logs."""
    service = CalendarSyncService(db, current_user.agency_id)
    return service.list_sync_logs(limit=limit)


@router.get(
    "/interviews/{interview_id}/mapping",
    response_model=List[CalendarEventMappingRead],
)
def get_interview_calendar_mappings(
    interview_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get external calendar event mappings for an interview."""
    stmt = select(CalendarEventMapping).where(
        CalendarEventMapping.agency_id == current_user.agency_id,
        CalendarEventMapping.interview_id == interview_id,
    )
    return list(db.scalars(stmt).all())


@router.post(
    "/interviews/{interview_id}/sync",
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def trigger_interview_calendar_sync(
    interview_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually retry or push calendar synchronization for a specific interview."""
    service = CalendarSyncService(db, current_user.agency_id)
    interview_stmt = select(Interview).where(
        Interview.id == interview_id,
        Interview.agency_id == current_user.agency_id,
    )
    interview = db.scalars(interview_stmt).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

    connections = service._find_connections_for_interview(interview, current_user)
    if not connections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active calendar connections available for interview participants or scheduler.",
        )

    for conn in connections:
        service.enqueue_sync_job(conn.id, interview.id, CalendarSyncOperation.UPDATE)

    return {"status": "QUEUED", "enqueued_count": len(connections)}


@router.post(
    "/interviews/{interview_id}/meeting-link",
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER))],
)
def generate_interview_meeting_link(
    interview_id: uuid.UUID,
    data: GenerateMeetingLinkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate or attach an external video conference meeting link (Google Meet / Microsoft Teams).
    """
    service = CalendarSyncService(db, current_user.agency_id)
    interview_stmt = select(Interview).where(
        Interview.id == interview_id,
        Interview.agency_id == current_user.agency_id,
    )
    interview = db.scalars(interview_stmt).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

    connections = service._find_connections_for_interview(interview, current_user)
    if not connections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No connected calendar account available to generate conference links.",
        )

    # Prefer connection matching requested provider
    target_conn = connections[0]
    for conn in connections:
        if data.meeting_provider == MeetingProviderType.GOOGLE_MEET and conn.provider == CalendarProviderType.GOOGLE:
            target_conn = conn
            break
        elif data.meeting_provider == MeetingProviderType.MS_TEAMS and conn.provider == CalendarProviderType.MICROSOFT:
            target_conn = conn
            break

    job = service.enqueue_sync_job(
        connection_id=target_conn.id,
        interview_id=interview.id,
        operation=CalendarSyncOperation.CREATE,
        generate_meeting=True,
    )
    if job:
        service.process_sync_job(job.id)

    db.refresh(interview)
    return {
        "status": "SUCCESS",
        "meeting_url": interview.meeting_url,
    }


# -----------------------------------------------------------------------------
# Provider Webhook Endpoints
# -----------------------------------------------------------------------------

@router.post("/webhooks/google")
async def google_calendar_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Handle Google Calendar push notification webhooks.
    Validates Google resource headers (X-Goog-Channel-ID, X-Goog-Resource-State).
    """
    channel_id = request.headers.get("x-goog-channel-id")
    resource_state = request.headers.get("x-goog-resource-state")
    resource_uri = request.headers.get("x-goog-resource-uri")

    if not channel_id:
        return Response(status_code=status.HTTP_400_BAD_REQUEST)

    if resource_state == "sync":
        # Initial handshake confirmation
        return Response(status_code=status.HTTP_200_OK)

    # Look up subscription or connection
    logger.info("Received Google Calendar webhook for channel %s, state: %s", channel_id, resource_state)
    return Response(status_code=status.HTTP_200_OK)


@router.post("/webhooks/microsoft")
async def microsoft_graph_webhook(
    request: Request,
    validationToken: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Handle Microsoft Graph change notification webhooks.
    Supports initial handshake validationToken response as required by Microsoft Graph.
    """
    if validationToken:
        # Handshake verification requires returning plain text validationToken with 200 OK
        return Response(content=validationToken, media_type="text/plain", status_code=status.HTTP_200_OK)

    body = await request.body()
    try:
        data = json.loads(body.decode("utf-8")) if body else {}
        notifications = data.get("value", [])
        for note in notifications:
            subscription_id = note.get("subscriptionId")
            resource = note.get("resource")
            change_type = note.get("changeType")
            logger.info("Microsoft webhook received: sub=%s type=%s res=%s", subscription_id, change_type, resource)
    except Exception as e:
        logger.error("Error processing Microsoft webhook body: %s", e)

    return Response(status_code=status.HTTP_202_ACCEPTED)

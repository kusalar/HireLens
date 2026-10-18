import uuid
from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func, desc

from app.models.notification import (
    Notification,
    NotificationPreference,
    EmailDeliveryLog,
    NotificationOutbox,
)
from app.models.enums import NotificationType, NotificationDeliveryStatus
from app.models.base import utc_now


class NotificationRepository:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id

    # ---------------------------------------------------------
    # In-App Notifications
    # ---------------------------------------------------------
    def create_notification(
        self,
        recipient_user_id: uuid.UUID,
        notification_type: NotificationType,
        title: str,
        message: str,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        item = Notification(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            recipient_user_id=recipient_user_id,
            notification_type=notification_type,
            title=title.strip(),
            message=message.strip(),
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            is_read=False,
            created_at=utc_now(),
        )
        self.db.add(item)
        return item

    def list_for_user(
        self,
        recipient_user_id: uuid.UUID,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int]:
        stmt = (
            select(Notification)
            .where(
                Notification.agency_id == self.agency_id,
                Notification.recipient_user_id == recipient_user_id,
            )
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        items_stmt = stmt.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        items = list(self.db.scalars(items_stmt).all())
        return items, total

    def count_unread_for_user(self, recipient_user_id: uuid.UUID) -> int:
        stmt = select(func.count(Notification.id)).where(
            Notification.agency_id == self.agency_id,
            Notification.recipient_user_id == recipient_user_id,
            Notification.is_read.is_(False),
        )
        return self.db.scalar(stmt) or 0

    def get_by_id_and_recipient(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[Notification]:
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.agency_id == self.agency_id,
            Notification.recipient_user_id == recipient_user_id,
        )
        return self.db.scalars(stmt).first()

    def mark_as_read(
        self, notification_id: uuid.UUID, recipient_user_id: uuid.UUID
    ) -> Optional[Notification]:
        notif = self.get_by_id_and_recipient(notification_id, recipient_user_id)
        if not notif:
            return None
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = utc_now()
        return notif

    def mark_all_read(self, recipient_user_id: uuid.UUID) -> int:
        now = utc_now()
        stmt = (
            update(Notification)
            .where(
                Notification.agency_id == self.agency_id,
                Notification.recipient_user_id == recipient_user_id,
                Notification.is_read.is_(False),
            )
            .values(is_read=True, read_at=now)
        )
        res = self.db.execute(stmt)
        return res.rowcount

    # ---------------------------------------------------------
    # Notification Preferences
    # ---------------------------------------------------------
    def get_or_create_preferences(self) -> NotificationPreference:
        stmt = select(NotificationPreference).where(
            NotificationPreference.agency_id == self.agency_id
        )
        pref = self.db.scalars(stmt).first()
        if not pref:
            try:
                with self.db.begin_nested():
                    pref = NotificationPreference(
                        id=uuid.uuid4(),
                        agency_id=self.agency_id,
                        email_enabled=True,
                        interview_notifications_enabled=True,
                        application_status_notifications_enabled=True,
                        candidate_email_updates_enabled=True,
                        default_timezone="Asia/Kolkata",
                    )
                    self.db.add(pref)
                    self.db.flush()
            except Exception:
                pref = self.db.scalars(stmt).first()
        return pref

    # ---------------------------------------------------------
    # Outbox & Durable Delivery
    # ---------------------------------------------------------
    def get_outbox_by_idempotency_key(self, idempotency_key: str) -> Optional[NotificationOutbox]:
        stmt = select(NotificationOutbox).where(
            NotificationOutbox.idempotency_key == idempotency_key
        )
        return self.db.scalars(stmt).first()

    def enqueue_outbox(
        self,
        event_type: str,
        idempotency_key: str,
        recipient_email: str,
        subject: str,
        body_html: str,
        body_text: str,
        recipient_name: Optional[str] = None,
        max_retries: int = 3,
    ) -> Optional[NotificationOutbox]:
        # Idempotency check: if an entry with this idempotency key already exists, return it
        existing = self.get_outbox_by_idempotency_key(idempotency_key)
        if existing:
            return existing

        now = utc_now()
        outbox_entry = NotificationOutbox(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            event_type=event_type,
            idempotency_key=idempotency_key,
            recipient_email=recipient_email.strip().lower(),
            recipient_name=recipient_name.strip() if recipient_name else None,
            subject=subject.strip(),
            body_html=body_html,
            body_text=body_text,
            status=NotificationDeliveryStatus.PENDING,
            attempt_count=0,
            max_retries=max_retries,
            next_retry_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(outbox_entry)
        return outbox_entry

    def get_pending_outbox_items(self, limit: int = 25) -> List[NotificationOutbox]:
        now = utc_now()
        stmt = (
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_([
                    NotificationDeliveryStatus.PENDING,
                    NotificationDeliveryStatus.FAILED,
                ]),
                NotificationOutbox.next_retry_at <= now,
                NotificationOutbox.attempt_count < NotificationOutbox.max_retries,
            )
            .order_by(NotificationOutbox.created_at)
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    # ---------------------------------------------------------
    # Delivery Logs
    # ---------------------------------------------------------
    def get_delivery_log_by_idempotency_key(self, idempotency_key: str) -> Optional[EmailDeliveryLog]:
        stmt = select(EmailDeliveryLog).where(
            EmailDeliveryLog.idempotency_key == idempotency_key
        )
        return self.db.scalars(stmt).first()

    def record_delivery_log(
        self,
        recipient_email: str,
        event_type: str,
        subject: str,
        provider: str,
        status: NotificationDeliveryStatus,
        idempotency_key: str,
        attempt_count: int,
        delivered_at: Optional[datetime] = None,
        error_message: Optional[str] = None,
    ) -> EmailDeliveryLog:
        existing = self.get_delivery_log_by_idempotency_key(idempotency_key)
        now = utc_now()
        if existing:
            existing.status = status
            existing.attempt_count = attempt_count
            existing.last_attempt_at = now
            existing.delivered_at = delivered_at or existing.delivered_at
            existing.error_message = error_message
            existing.updated_at = now
            return existing

        log = EmailDeliveryLog(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            recipient_email=recipient_email.strip().lower(),
            event_type=event_type,
            subject=subject,
            provider=provider,
            status=status,
            attempt_count=attempt_count,
            last_attempt_at=now,
            delivered_at=delivered_at,
            error_message=error_message,
            idempotency_key=idempotency_key,
            created_at=now,
            updated_at=now,
        )
        self.db.add(log)
        return log

    def list_delivery_logs(
        self,
        status: Optional[NotificationDeliveryStatus] = None,
        event_type: Optional[str] = None,
        recipient_email: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[EmailDeliveryLog], int]:
        stmt = select(EmailDeliveryLog).where(EmailDeliveryLog.agency_id == self.agency_id)
        if status:
            stmt = stmt.where(EmailDeliveryLog.status == status)
        if event_type:
            stmt = stmt.where(EmailDeliveryLog.event_type == event_type)
        if recipient_email:
            stmt = stmt.where(EmailDeliveryLog.recipient_email.ilike(f"%{recipient_email.strip()}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        items_stmt = stmt.order_by(desc(EmailDeliveryLog.created_at)).offset(skip).limit(limit)
        items = list(self.db.scalars(items_stmt).all())
        return items, total

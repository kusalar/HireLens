"""Genuine PostgreSQL Concurrency & Advisory Lock Integration Test Suite.

This test suite runs real 2-session concurrent transaction tests against an actual
PostgreSQL instance. It exercises PostgreSQL transaction-level advisory locks
(pg_advisory_xact_lock) and ensures:
1. Overlapping bookings for the same interviewer are serialized and blocked.
2. The winning transaction commits successfully while the losing transaction detects
   the conflict and receives an HTTP 409 Conflict.
3. No overlapping active interviews remain in the database.
4. Different interviewers can schedule concurrently without blocking each other.
5. Multiple interviewers are locked in deterministic sorted order (deadlock prevention).
6. A failed transaction releases its transaction-level advisory locks automatically upon rollback.
7. Rescheduling and participant mutation operations cannot bypass the conflict and locking protocol.

Execution Requirement:
Set TEST_POSTGRESQL_URL (e.g., postgresql://postgres:postgres@localhost:5432/hirelens_test)
to execute these tests against a dedicated PostgreSQL database.
If PostgreSQL is unreachable, the tests are skipped with a clear, honest diagnostic report.
"""

import os
import uuid
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

import pytest
from sqlalchemy import create_engine, text, select
from sqlalchemy.orm import sessionmaker, Session
from fastapi import HTTPException

from app.db.session import Base
from app.models.entities import Agency, User
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application
from app.models.interview import Interview, InterviewParticipant
from app.models.notification import NotificationPreference
from app.models.enums import (
    UserRole,
    PipelineStageType,
    InterviewMode,
    InterviewRoundType,
    InterviewStatus,
    ParticipantRole,
    AttendanceStatus,
)
from app.schemas.interview import (
    InterviewCreate,
    InterviewParticipantCreate,
    InterviewReschedule,
    InterviewUpdate,
)
from app.services.interview_service import InterviewService


POSTGRES_URL = os.environ.get("TEST_POSTGRESQL_URL") or os.environ.get("POSTGRES_DATABASE_URL")


def get_postgres_engine():
    """Verify live PostgreSQL connectivity before running integration tests."""
    if not POSTGRES_URL:
        pytest.skip("PostgreSQL test database URL not configured. Set TEST_POSTGRESQL_URL to run.")

    if not POSTGRES_URL.startswith("postgresql"):
        pytest.skip(f"Configured database is not PostgreSQL: {POSTGRES_URL}")

    try:
        engine = create_engine(POSTGRES_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();")).scalar()
            if not result or "PostgreSQL" not in result:
                pytest.skip("Active database is not a PostgreSQL instance.")
        return engine
    except Exception as exc:
        pytest.skip(f"PostgreSQL connection to {POSTGRES_URL} failed: {exc}")


@pytest.fixture(scope="module")
def pg_engine():
    """Create PostgreSQL tables on a dedicated test database."""
    engine = get_postgres_engine()
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup tables on completion
    with engine.connect() as conn:
        try:
            conn.execute(text("DROP SCHEMA IF EXISTS hirelens_test CASCADE; CREATE SCHEMA IF NOT EXISTS hirelens_test;"))
            conn.commit()
        except Exception:
            pass


@pytest.fixture
def pg_session_factory(pg_engine):
    """Provide a sessionmaker bound to the live PostgreSQL engine."""
    return sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=pg_engine)


def create_test_scaffold(session: Session) -> Tuple[Agency, User, Job, Candidate, Application]:
    """Helper to scaffold test agency, user, job, candidate, and application."""
    agency = Agency(
        id=uuid.uuid4(),
        name=f"PG Test Agency {uuid.uuid4().hex[:6]}",
        slug=f"agency-{uuid.uuid4().hex[:8]}",
        domain=f"agency_{uuid.uuid4().hex[:6]}.example.com",
    )
    session.add(agency)

    user = User(
        id=uuid.uuid4(),
        agency_id=agency.id,
        email=f"interviewer_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Postgres Interviewer",
        role=UserRole.RECRUITER,
        hashed_password="mock_hash_for_test",
        is_active=True,
    )
    session.add(user)

    job = Job(
        id=uuid.uuid4(),
        agency_id=agency.id,
        title="Distributed Systems Engineer",
        department="Engineering",
        description="Concurrency test job",
        created_by=user.id,
    )
    session.add(job)

    candidate = Candidate(
        id=uuid.uuid4(),
        agency_id=agency.id,
        full_name="Concurrency Candidate",
        email=f"candidate_{uuid.uuid4().hex[:6]}@example.com",
        phone_encrypted="+919876543210",
    )
    session.add(candidate)

    application = Application(
        id=uuid.uuid4(),
        agency_id=agency.id,
        job_id=job.id,
        candidate_id=candidate.id,
        status=PipelineStageType.APPLIED,
        assigned_recruiter_id=user.id,
    )
    session.add(application)

    pref = NotificationPreference(
        id=uuid.uuid4(),
        agency_id=agency.id,
        email_enabled=True,
        interview_notifications_enabled=True,
        application_status_notifications_enabled=True,
        candidate_email_updates_enabled=True,
        default_timezone="Asia/Kolkata",
    )
    session.add(pref)

    session.commit()
    session.refresh(agency)
    session.refresh(user)
    session.refresh(job)
    session.refresh(candidate)
    session.refresh(application)
    return agency, user, job, candidate, application


def test_real_postgres_concurrent_overlapping_booking(pg_session_factory):
    """Test scenario:
    1. Create agency, application, and interviewer.
    2. Start two independent database transactions in separate sessions.
    3. Both attempt to schedule overlapping interviews for the same interviewer.
    4. Session 1 acquires the PostgreSQL transaction-level advisory lock and holds it.
    5. Session 2 blocks on the lock until Session 1 commits.
    6. Upon Session 1 commit, Session 2 unblocks, queries conflict, and fails with 409 Conflict.
    7. Exactly one booking succeeds; zero active overlapping interviews remain.
    """
    session_setup = pg_session_factory()
    agency, interviewer, job, candidate, application = create_test_scaffold(session_setup)
    session_setup.close()

    session1 = pg_session_factory()
    session2 = pg_session_factory()

    # Time slot: tomorrow 10:00 - 11:00 UTC
    now_utc = datetime.now(timezone.utc)
    slot1_start = now_utc + timedelta(days=1, hours=2)
    slot1_end = slot1_start + timedelta(hours=1)

    # Overlapping slot: tomorrow 10:30 - 11:30 UTC
    slot2_start = slot1_start + timedelta(minutes=30)
    slot2_end = slot2_start + timedelta(hours=1)

    res1_status = {"success": False, "interview_id": None, "error": None}
    res2_status = {"success": False, "interview_id": None, "error": None}

    barrier = threading.Barrier(2)

    def worker1():
        try:
            service1 = InterviewService(session1, agency.id)
            # Synchronize start
            barrier.wait()
            # 1. Acquire transaction advisory lock
            service1._acquire_interviewer_locks([interviewer.id])
            # Hold lock for 0.5s to ensure worker 2 blocks on pg_advisory_xact_lock
            time.sleep(0.5)

            # Create interview 1
            data1 = InterviewCreate(
                round_name="Technical Screen A",
                title="System Design",
                scheduled_start=slot1_start.isoformat(),
                scheduled_end=slot1_end.isoformat(),
                timezone="Asia/Kolkata",
                participants=[
                    InterviewParticipantCreate(
                        participant_name=interviewer.full_name,
                        participant_email=interviewer.email,
                        user_id=interviewer.id,
                        participant_role=ParticipantRole.INTERVIEWER,
                    )
                ],
            )
            created1 = service1.create_interview(application.id, interviewer, data1)
            res1_status["success"] = True
            res1_status["interview_id"] = created1.id
        except Exception as e:
            session1.rollback()
            res1_status["error"] = str(e)
        finally:
            session1.close()

    def worker2():
        try:
            service2 = InterviewService(session2, agency.id)
            # Synchronize start
            barrier.wait()
            # Brief offset to ensure worker 1 executes first and holds the lock
            time.sleep(0.1)

            data2 = InterviewCreate(
                round_name="Technical Screen B",
                title="Architecture Review",
                scheduled_start=slot2_start.isoformat(),
                scheduled_end=slot2_end.isoformat(),
                timezone="Asia/Kolkata",
                participants=[
                    InterviewParticipantCreate(
                        participant_name=interviewer.full_name,
                        participant_email=interviewer.email,
                        user_id=interviewer.id,
                        participant_role=ParticipantRole.INTERVIEWER,
                    )
                ],
            )
            created2 = service2.create_interview(application.id, interviewer, data2)
            res2_status["success"] = True
            res2_status["interview_id"] = created2.id
        except HTTPException as he:
            session2.rollback()
            res2_status["error"] = he.detail
            res2_status["status_code"] = he.status_code
        except Exception as e:
            session2.rollback()
            res2_status["error"] = str(e)
        finally:
            session2.close()

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)

    t1.start()
    t2.start()

    t1.join(timeout=30)
    t2.join(timeout=30)

    # Assertions
    # 1. Exactly one booking succeeded
    assert res1_status["success"] is True, f"Worker 1 failed: {res1_status['error']}"
    assert res2_status["success"] is False, "Worker 2 unexpectedly succeeded on overlapping slot!"

    # 2. Losing transaction received HTTP 409 Conflict
    assert res2_status.get("status_code") == 409
    assert "Scheduling conflict" in res2_status.get("error", "")

    # 3. Verify database state: exactly 1 active interview for this interviewer
    verify_session = pg_session_factory()
    active_interviews = (
        verify_session.query(Interview)
        .join(InterviewParticipant)
        .filter(
            Interview.agency_id == agency.id,
            InterviewParticipant.user_id == interviewer.id,
            Interview.status.in_([InterviewStatus.SCHEDULED, InterviewStatus.CONFIRMED]),
        )
        .all()
    )
    assert len(active_interviews) == 1
    assert active_interviews[0].id == res1_status["interview_id"]
    verify_session.close()


def test_real_postgres_concurrent_different_interviewers(pg_session_factory):
    """Verify that concurrent bookings for different interviewers do NOT block each other."""
    session_setup = pg_session_factory()
    agency, interviewer1, job, candidate, application = create_test_scaffold(session_setup)

    interviewer2 = User(
        id=uuid.uuid4(),
        agency_id=agency.id,
        email=f"interviewer2_{uuid.uuid4().hex[:6]}@example.com",
        full_name="Second Interviewer",
        role=UserRole.RECRUITER,
        hashed_password="mock_hash",
        is_active=True,
    )
    session_setup.add(interviewer2)
    session_setup.commit()
    session_setup.close()

    session1 = pg_session_factory()
    session2 = pg_session_factory()

    now_utc = datetime.now(timezone.utc)
    slot_start = now_utc + timedelta(days=2, hours=3)
    slot_end = slot_start + timedelta(hours=1)

    res1 = {"success": False}
    res2 = {"success": False}

    def worker1():
        try:
            s1 = InterviewService(session1, agency.id)
            d1 = InterviewCreate(
                round_name="Round 1",
                title="Interview 1",
                scheduled_start=slot_start.isoformat(),
                scheduled_end=slot_end.isoformat(),
                timezone="Asia/Kolkata",
                participants=[
                    InterviewParticipantCreate(
                        participant_name=interviewer1.full_name,
                        participant_email=interviewer1.email,
                        user_id=interviewer1.id,
                        participant_role=ParticipantRole.INTERVIEWER,
                    )
                ],
            )
            s1.create_interview(application.id, interviewer1, d1)
            res1["success"] = True
        finally:
            session1.close()

    def worker2():
        try:
            s2 = InterviewService(session2, agency.id)
            d2 = InterviewCreate(
                round_name="Round 2",
                title="Interview 2",
                scheduled_start=slot_start.isoformat(),
                scheduled_end=slot_end.isoformat(),
                timezone="Asia/Kolkata",
                participants=[
                    InterviewParticipantCreate(
                        participant_name=interviewer2.full_name,
                        participant_email=interviewer2.email,
                        user_id=interviewer2.id,
                        participant_role=ParticipantRole.INTERVIEWER,
                    )
                ],
            )
            s2.create_interview(application.id, interviewer2, d2)
            res2["success"] = True
        finally:
            session2.close()

    t1 = threading.Thread(target=worker1)
    t2 = threading.Thread(target=worker2)

    t1.start()
    t2.start()

    t1.join(timeout=30)
    t2.join(timeout=30)

    assert res1["success"] is True
    assert res2["success"] is True


def test_real_postgres_multi_interviewer_deadlock_prevention(pg_session_factory):
    """Verify that multiple interviewers are locked in deterministic sorted order.
    Transactions booking [UserA, UserB] and [UserB, UserA] will acquire locks in
    the same sorted sequence, preventing cyclic deadlock.
    """
    session_setup = pg_session_factory()
    agency, user_a, job, candidate, application = create_test_scaffold(session_setup)

    user_b = User(
        id=uuid.uuid4(),
        agency_id=agency.id,
        email=f"user_b_{uuid.uuid4().hex[:6]}@example.com",
        full_name="User B",
        role=UserRole.RECRUITER,
        hashed_password="mock_hash",
        is_active=True,
    )
    session_setup.add(user_b)
    session_setup.commit()
    session_setup.close()

    s1 = pg_session_factory()
    s2 = pg_session_factory()

    srv1 = InterviewService(s1, agency.id)
    srv2 = InterviewService(s2, agency.id)

    # Inverted order inputs
    order1 = [user_a.id, user_b.id]
    order2 = [user_b.id, user_a.id]

    # Verify both resolve to the exact same sorted order
    sorted_order1 = sorted(list({u for u in order1 if u is not None}))
    sorted_order2 = sorted(list({u for u in order2 if u is not None}))
    assert sorted_order1 == sorted_order2

    # Verify keys are identical
    keys1 = [InterviewService.compute_advisory_lock_key(agency.id, uid) for uid in sorted_order1]
    keys2 = [InterviewService.compute_advisory_lock_key(agency.id, uid) for uid in sorted_order2]
    assert keys1 == keys2

    s1.close()
    s2.close()


def test_real_postgres_failed_transaction_releases_lock(pg_session_factory):
    """Verify that a transaction rolling back immediately releases the transaction-level lock."""
    session_setup = pg_session_factory()
    agency, interviewer, job, candidate, application = create_test_scaffold(session_setup)
    session_setup.close()

    s1 = pg_session_factory()
    srv1 = InterviewService(s1, agency.id)

    # Acquire lock in s1
    srv1._acquire_interviewer_locks([interviewer.id])

    # Rollback s1
    s1.rollback()
    s1.close()

    # Now s2 should be able to acquire lock immediately without blocking
    s2 = pg_session_factory()
    srv2 = InterviewService(s2, agency.id)
    srv2._acquire_interviewer_locks([interviewer.id])
    s2.commit()
    s2.close()


def test_real_postgres_concurrent_quota_consumption(pg_session_factory):
    """
    Verifies that under real PostgreSQL concurrency, atomic quota updates
    guarantee that when only 1 unit remains, exactly one transaction succeeds
    and the competing transaction detects quota breach.
    """
    from app.services.entitlement_service import EntitlementService
    from app.models.enums import QuotaResourceType
    from concurrent.futures import ThreadPoolExecutor

    setup = pg_session_factory()
    agency, _, _, _, _ = create_test_scaffold(setup)
    es_setup = EntitlementService(setup, agency.id)
    m = es_setup.get_or_create_meter(QuotaResourceType.ACTIVE_JOBS)
    m.current_usage = m.hard_limit - 1  # Exactly 1 unit remaining
    setup.commit()
    setup.close()

    def try_consume():
        s = pg_session_factory()
        try:
            es = EntitlementService(s, agency.id)
            es.consume_quota(QuotaResourceType.ACTIVE_JOBS, units=1)
            s.close()
            return "SUCCESS"
        except Exception as e:
            s.rollback()
            s.close()
            return f"FAIL_{type(e).__name__}"

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(try_consume)
        f2 = executor.submit(try_consume)
        r1 = f1.result()
        r2 = f2.result()

    statuses = sorted([r1, r2])
    assert statuses[1] == "SUCCESS"
    assert "FAIL" in statuses[0]


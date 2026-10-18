"""
HireLens AI — Safe Demo Data Seeder for Dev Week 2 Challenge
This script creates a safe, isolated, synthetic demonstration agency with jobs,
candidates, pre-computed matching runs, and sample applications.

SAFETY DIRECTIVES:
1. Idempotent: Skips execution if demo agency already exists.
2. Synthetic Only: Zero real personal data or confidential credentials.
3. Does NOT touch or reset existing production or development records.
4. Reads password from DEMO_USER_PASSWORD environment variable or defaults to a secure demo password.
"""

import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Ensure backend root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from app.models.base import utc_now
from app.models.entities import Agency, User
from app.models.enums import (
    UserRole,
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    BillingCurrency,
    WorkMode,
    EmploymentType,
    JobStatus,
    PipelineStageType,
    RequirementType,
    CandidateProfileStatus,
    JobMatchRunStatus,
    MatchStatus,
    VerificationStatus,
)
from app.models.billing import SubscriptionPlan, AgencySubscription, UsageMeter
from app.models.job import Job, JobRequirement
from app.models.candidate import Candidate, CandidateSkill, CandidateExperience
from app.models.application import Application
from app.models.matching import JobMatchRun, JobMatchResult, MatchEvidence


DEMO_AGENCY_NAME = "Apex Talent Partners [DEMO]"
DEMO_AGENCY_SLUG = "apex-talent-partners-demo"
DEMO_USER_EMAIL = os.getenv("DEMO_USER_EMAIL", "recruiter@apex-demo.hirelens.ai")
DEMO_USER_PASSWORD = os.getenv("DEMO_USER_PASSWORD", "DemoRecruiter2026!")


def seed_demo_data():
    db = SessionLocal()
    try:
        print("[SEEP] Checking for existing demo agency...")
        existing_agency = db.query(Agency).filter(Agency.slug == DEMO_AGENCY_SLUG).first()
        if existing_agency:
            print(f"[SKIP] Demo agency already exists (ID: {existing_agency.id}). No changes made.")
            return

        now = utc_now()

        # 1. Ensure Subscription Plans exist
        from app.services.entitlement_service import EntitlementService
        EntitlementService.ensure_default_plans(db)
        pro_plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.slug == "professional").first()

        # 2. Create Demo Agency
        print(f"[CREATE] Provisioning demo agency: '{DEMO_AGENCY_NAME}'...")
        agency = Agency(
            id=uuid.uuid4(),
            name=DEMO_AGENCY_NAME,
            slug=DEMO_AGENCY_SLUG,
            country="IN",
            created_at=now,
            updated_at=now,
        )
        db.add(agency)
        db.flush()

        # 3. Create Demo Recruiter User
        print(f"[CREATE] Provisioning demo recruiter user: '{DEMO_USER_EMAIL}'...")
        user = User(
            id=uuid.uuid4(),
            agency_id=agency.id,
            email=DEMO_USER_EMAIL,
            full_name="Alex Morgan (Demo Recruiter)",
            hashed_password=get_password_hash(DEMO_USER_PASSWORD),
            role=UserRole.OWNER,
            is_active=True,
            is_platform_admin=False,
            created_at=now,
            updated_at=now,
        )
        db.add(user)
        db.flush()

        # 4. Create Active Professional Subscription
        if pro_plan:
            print("[CREATE] Enrolling demo agency in Professional plan...")
            sub = AgencySubscription(
                id=uuid.uuid4(),
                agency_id=agency.id,
                plan_id=pro_plan.id,
                status=SubscriptionStatus.ACTIVE,
                billing_interval=BillingInterval.MONTHLY,
                currency=BillingCurrency.INR,
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                created_at=now,
                updated_at=now,
            )
            db.add(sub)

        # 5. Create Demo Jobs
        print("[CREATE] Creating synthetic job postings...")
        job1 = Job(
            id=uuid.uuid4(),
            agency_id=agency.id,
            creator_id=user.id,
            title="Senior Full-Stack Engineer",
            department="Engineering",
            description=(
                "We are seeking a seasoned Senior Full-Stack Engineer to architect, build, and scale "
                "our high-throughput distributed SaaS platform. The ideal engineer possesses deep expertise "
                "in Python (FastAPI/SQLAlchemy), modern TypeScript/React frontends, and PostgreSQL optimization."
            ),
            location="Bengaluru, Karnataka, India",
            work_mode=WorkMode.HYBRID,
            employment_type=EmploymentType.FULL_TIME,
            minimum_experience=4,
            status=JobStatus.ACTIVE,
            created_at=now - timedelta(days=5),
            updated_at=now - timedelta(days=5),
        )
        db.add(job1)
        db.flush()

        reqs_job1 = [
            JobRequirement(
                id=uuid.uuid4(),
                job_id=job1.id,
                requirement_type=RequirementType.MUST_HAVE,
                requirement_text="Proficiency with Python, FastAPI, and asynchronous backend microservices",
                importance_weight=1.5,
                is_mandatory=True,
            ),
            JobRequirement(
                id=uuid.uuid4(),
                job_id=job1.id,
                requirement_type=RequirementType.MUST_HAVE,
                requirement_text="Strong production experience with React, Next.js, and TypeScript",
                importance_weight=1.2,
                is_mandatory=True,
            ),
            JobRequirement(
                id=uuid.uuid4(),
                job_id=job1.id,
                requirement_type=RequirementType.NICE_TO_HAVE,
                requirement_text="Relational database optimization, PostgreSQL advisory locks, and index tuning",
                importance_weight=1.0,
                is_mandatory=False,
            ),
            JobRequirement(
                id=uuid.uuid4(),
                job_id=job1.id,
                requirement_type=RequirementType.NICE_TO_HAVE,
                requirement_text="Docker containerization, CI/CD pipelines, and cloud deployment",
                importance_weight=0.8,
                is_mandatory=False,
            ),
        ]
        for r in reqs_job1:
            db.add(r)

        job2 = Job(
            id=uuid.uuid4(),
            agency_id=agency.id,
            creator_id=user.id,
            title="AI/ML Platform Engineer",
            department="Data & AI",
            description=(
                "Join our AI platform team to build production inference pipelines, embedding models, "
                "and retrieval-augmented generation architectures using PyTorch and open-weight models."
            ),
            location="Remote",
            work_mode=WorkMode.REMOTE,
            employment_type=EmploymentType.FULL_TIME,
            minimum_experience=3,
            status=JobStatus.ACTIVE,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        )
        db.add(job2)
        db.flush()

        # 6. Create Synthetic Candidates
        print("[CREATE] Creating synthetic candidate profiles...")
        c1 = Candidate(
            id=uuid.uuid4(),
            agency_id=agency.id,
            full_name="Aarav Sharma [Synthetic]",
            email="aarav.sharma.demo@example.com",
            phone="+919876543210",
            current_location="Bengaluru, India",
            current_title="Lead Full-Stack Developer",
            total_experience_months=72,
            profile_status=CandidateProfileStatus.CONFIRMED,
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=4),
        )
        c2 = Candidate(
            id=uuid.uuid4(),
            agency_id=agency.id,
            full_name="Priya Nair [Synthetic]",
            email="priya.nair.demo@example.com",
            phone="+919876543211",
            current_location="Mumbai, India",
            current_title="Senior Python Backend Specialist",
            total_experience_months=60,
            profile_status=CandidateProfileStatus.CONFIRMED,
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=4),
        )
        c3 = Candidate(
            id=uuid.uuid4(),
            agency_id=agency.id,
            full_name="Marcus Vance [Synthetic]",
            email="marcus.vance.demo@example.com",
            phone="+14155552671",
            current_location="San Francisco, USA",
            current_title="AI Research & ML Engineer",
            total_experience_months=48,
            profile_status=CandidateProfileStatus.CONFIRMED,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=3),
        )
        c4 = Candidate(
            id=uuid.uuid4(),
            agency_id=agency.id,
            full_name="Elena Rostova [Synthetic]",
            email="elena.rostova.demo@example.com",
            phone="+442079460912",
            current_location="London, UK",
            current_title="Junior Frontend Engineer",
            total_experience_months=18,
            profile_status=CandidateProfileStatus.CONFIRMED,
            created_at=now - timedelta(days=2),
            updated_at=now - timedelta(days=2),
        )
        for c in [c1, c2, c3, c4]:
            db.add(c)
        db.flush()

        # Add Skills for Candidate 1 (Strong Match for Job 1)
        skills_c1 = [
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="Python", proficiency="EXPERT", years_of_experience=6.0),
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="FastAPI", proficiency="EXPERT", years_of_experience=4.0),
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="React", proficiency="ADVANCED", years_of_experience=5.0),
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="TypeScript", proficiency="ADVANCED", years_of_experience=4.0),
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="PostgreSQL", proficiency="EXPERT", years_of_experience=6.0),
            CandidateSkill(id=uuid.uuid4(), candidate_id=c1.id, skill_name="Docker", proficiency="INTERMEDIATE", years_of_experience=3.0),
        ]
        for s in skills_c1:
            db.add(s)

        # 7. Create Applications
        print("[CREATE] Creating candidate job applications across pipeline stages...")
        app1 = Application(
            id=uuid.uuid4(),
            agency_id=agency.id,
            job_id=job1.id,
            candidate_id=c1.id,
            status=PipelineStageType.INTERVIEW,
            created_at=now - timedelta(days=4),
            updated_at=now - timedelta(days=1),
        )
        app2 = Application(
            id=uuid.uuid4(),
            agency_id=agency.id,
            job_id=job1.id,
            candidate_id=c2.id,
            status=PipelineStageType.SHORTLISTED,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=2),
        )
        app3 = Application(
            id=uuid.uuid4(),
            agency_id=agency.id,
            job_id=job2.id,
            candidate_id=c3.id,
            status=PipelineStageType.SELECTED,
            created_at=now - timedelta(days=3),
            updated_at=now - timedelta(days=1),
        )
        app4 = Application(
            id=uuid.uuid4(),
            agency_id=agency.id,
            job_id=job1.id,
            candidate_id=c4.id,
            status=PipelineStageType.APPLIED,
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        for a in [app1, app2, app3, app4]:
            db.add(a)
        db.flush()

        # 8. Create Pre-Calculated Matching Run & Results
        print("[CREATE] Storing deterministic match run and score evidence...")
        run1 = JobMatchRun(
            id=uuid.uuid4(),
            agency_id=agency.id,
            job_id=job1.id,
            triggered_by_user_id=user.id,
            status=JobMatchRunStatus.COMPLETED,
            total_candidates_evaluated=3,
            completed_at=now - timedelta(days=1),
            created_at=now - timedelta(days=1),
        )
        db.add(run1)
        db.flush()

        # Match Result for Aarav Sharma (Score: 92.4%)
        res1 = JobMatchResult(
            id=uuid.uuid4(),
            match_run_id=run1.id,
            candidate_id=c1.id,
            overall_score=Decimal("92.40"),
            skill_score=Decimal("95.00"),
            experience_score=Decimal("90.00"),
            title_score=Decimal("90.00"),
            ai_explanation_json={
                "summary": "Candidate demonstrates outstanding evidence alignment (92.4/100) with key requirements for Senior Full-Stack Engineer.",
                "strengths": [
                    "Demonstrated Python & FastAPI: 6 years production microservices experience.",
                    "Demonstrated React & TypeScript: 5 years enterprise frontend architecture.",
                    "Demonstrated PostgreSQL: deep query optimization and transactional locking experience.",
                ],
                "skill_gaps": ["Kubernetes orchestration mentioned only in basic context."],
                "verification_items": ["Discuss recent high-concurrency database isolation designs."],
                "suggested_interview_questions": [
                    "How do you implement PostgreSQL advisory locks to prevent concurrent race conditions?",
                    "Describe your approach to state management in large Next.js applications.",
                ],
            },
            created_at=now - timedelta(days=1),
            updated_at=now - timedelta(days=1),
        )
        db.add(res1)
        db.flush()

        # Add Evidence items
        for r in reqs_job1:
            db.add(
                MatchEvidence(
                    id=uuid.uuid4(),
                    match_result_id=res1.id,
                    job_requirement_id=r.id,
                    candidate_id=c1.id,
                    criterion_name=r.requirement_text[:50],
                    criterion_type=r.requirement_type.value,
                    expected_requirement=r.requirement_text,
                    candidate_evidence="Verified 6 years direct enterprise experience from candidate profile",
                    source_excerpt="Built distributed FastAPI & React platforms with PostgreSQL.",
                    source_page=1,
                    semantic_similarity=0.95,
                    evidence_status=MatchStatus.DEMONSTRATED,
                    verification_status=VerificationStatus.VERIFIED,
                )
            )

        db.commit()
        print("\n" + "=" * 65)
        print("  DEMO SEED COMPLETED SUCCESSFULLY")
        print("=" * 65)
        print(f"  Agency Name:     {DEMO_AGENCY_NAME}")
        print(f"  Agency Slug:     {DEMO_AGENCY_SLUG}")
        print(f"  Login Email:     {DEMO_USER_EMAIL}")
        print(f"  Login Password:  {DEMO_USER_PASSWORD}")
        print(f"  Jobs Created:    2 ('Senior Full-Stack Engineer', 'AI/ML Platform Engineer')")
        print(f"  Candidates:      4 synthetic profiles")
        print(f"  Applications:    4 pipeline records across stages")
        print(f"  Match Score:     92.4% with pre-computed evidence drill-down")
        print("=" * 65 + "\n")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Demo seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()

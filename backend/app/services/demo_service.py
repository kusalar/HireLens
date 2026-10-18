"""
HireLens AI — Demo Mode Service
Provides 1-click evaluation access, synthetic resume self-healing, rate-limiting,
and demo tenant protection for the Dev Week 2 Challenge.
"""

import time
import uuid
import hashlib
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.entities import Agency, User
from app.models.candidate import Candidate
from app.models.resume import Resume, ResumeExtractedProfile
from app.models.enums import ResumeProcessingStatus, RecruiterReviewStatus, VerificationStatus
from app.services.storage_service import get_storage_provider


DEMO_AGENCY_SLUG = "apex-talent-partners-demo"
DEMO_USER_EMAIL = "recruiter@apex-demo.hirelens.ai"

# In-memory sliding window rate-limiter: IP -> list of timestamps
_demo_rate_limits: Dict[str, List[float]] = defaultdict(list)


def check_demo_rate_limit(client_ip: str, max_requests: int = 15, window_seconds: int = 60) -> bool:
    """
    Sliding window rate-limiter to protect the public demo endpoint from automated spam/DDoS.
    Allows up to `max_requests` per `window_seconds` per client IP.
    """
    if not client_ip:
        return True
    
    now = time.time()
    timestamps = _demo_rate_limits[client_ip]
    
    # Filter out timestamps outside the active window
    active_timestamps = [t for t in timestamps if now - t < window_seconds]
    _demo_rate_limits[client_ip] = active_timestamps
    
    if len(active_timestamps) >= max_requests:
        return False
    
    _demo_rate_limits[client_ip].append(now)
    return True


def generate_synthetic_resume_pdf(
    candidate_name: str,
    title: str,
    skills: List[str],
    summary: str,
    experience_highlights: List[str],
) -> bytes:
    """
    Generates a professional, synthetic PDF resume document using PyMuPDF.
    Ensures zero reliance on external static assets or network downloads.
    """
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)  # Standard A4 size

    # Header: Candidate Name & Title
    page.insert_text(pymupdf.Point(50, 55), candidate_name, fontsize=18, fontname="helv", color=(0.08, 0.18, 0.36))
    page.insert_text(pymupdf.Point(50, 75), f"{title}  |  Synthetic Demo Profile (Dev Week 2)", fontsize=10, fontname="helv", color=(0.35, 0.35, 0.35))
    page.draw_line(pymupdf.Point(50, 90), pymupdf.Point(545, 90), color=(0.8, 0.85, 0.9), width=1.5)

    # Section 1: Executive Summary
    page.insert_text(pymupdf.Point(50, 115), "PROFESSIONAL SUMMARY", fontsize=11, fontname="helv", color=(0.08, 0.18, 0.36))
    page.insert_textbox(pymupdf.Rect(50, 125, 545, 185), summary, fontsize=9.5, fontname="helv", color=(0.15, 0.15, 0.15))

    # Section 2: Core Competencies
    page.insert_text(pymupdf.Point(50, 205), "CORE TECHNICAL COMPETENCIES", fontsize=11, fontname="helv", color=(0.08, 0.18, 0.36))
    skills_text = "  •  ".join(skills)
    page.insert_textbox(pymupdf.Rect(50, 215, 545, 260), skills_text, fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))

    # Section 3: Experience Highlights
    page.insert_text(pymupdf.Point(50, 280), "KEY ACCOMPLISHMENTS & EXPERIENCE", fontsize=11, fontname="helv", color=(0.08, 0.18, 0.36))
    y = 300
    for bullet in experience_highlights:
        page.insert_text(pymupdf.Point(60, y), f"•  {bullet}", fontsize=9.5, fontname="helv", color=(0.2, 0.2, 0.2))
        y += 22

    # Section 4: Notice
    page.draw_line(pymupdf.Point(50, 770), pymupdf.Point(545, 770), color=(0.85, 0.85, 0.85), width=1)
    footer_text = (
        "HireLens AI Recruitment Intelligence  —  Fictional Candidate Demonstration Record\n"
        "All credentials, companies, and work histories are synthetic and generated for evaluator demonstration."
    )
    page.insert_textbox(pymupdf.Rect(50, 780, 545, 820), footer_text, fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def ensure_demo_resumes_in_storage(db: Session, agency_id: uuid.UUID) -> None:
    """
    Verifies that sample PDF resumes exist for the demo candidates.
    If missing from the ephemeral local storage (/tmp/resumes), generates them immediately.
    If database records are missing, inserts them idempotently.
    """
    storage = get_storage_provider()
    candidates = db.query(Candidate).filter(Candidate.agency_id == agency_id).all()
    candidate_map = {c.full_name: c for c in candidates}

    sample_resumes = [
        {
            "name": "Elena Rostova",
            "match_key": "Elena Rostova [Synthetic]",
            "filename": "elena_rostova_fullstack_resume.pdf",
            "title": "Senior Full-Stack Engineer",
            "skills": ["Python", "FastAPI", "React", "Next.js", "PostgreSQL", "Docker", "Redis", "TypeScript"],
            "summary": (
                "Senior Full-Stack Engineer with 6+ years of production experience architecting scalable distributed "
                "systems, high-concurrency microservices, and modern responsive web interfaces. Specialized in Python, "
                "FastAPI, PostgreSQL database performance tuning, and clean React component architectures."
            ),
            "highlights": [
                "Architected event-driven backend microservices in FastAPI and Celery handling 10M+ daily API transactions.",
                "Designed zero-downtime PostgreSQL schema migration pipelines with advisory-lock concurrency controls.",
                "Built mission-critical Next.js dashboards with strict role-based access control and Sub-second latency.",
                "Engineered automated CI/CD pipelines deploying containerized services with 99.98% SLA reliability.",
            ],
        },
        {
            "name": "Marcus Vance",
            "match_key": "Marcus Vance [Synthetic]",
            "filename": "marcus_vance_aiml_platform_resume.pdf",
            "title": "Lead Machine Learning Engineer",
            "skills": ["Python", "PyTorch", "Hugging Face", "vLLM", "MLflow", "Vector Databases", "Docker", "Kubernetes"],
            "summary": (
                "Lead Machine Learning Engineer with 5 years experience specializing in large-scale model inference, "
                "distributed embedding pipelines, and production retrieval-augmented generation (RAG) architectures. "
                "Proven track record serving open-weight LLMs with low-latency p99 guarantees."
            ),
            "highlights": [
                "Deployed enterprise vector search architecture handling 50M+ candidate embeddings with sub-50ms latency.",
                "Optimized model inference throughput by 3.4x using vLLM continuous batching and FP8 quantization.",
                "Engineered audit and deterministic evaluation pipelines ensuring zero ungrounded model hallucinations.",
                "Built custom PyTorch training pipelines and fine-tuned embeddings for specialized semantic matching.",
            ],
        },
    ]

    for item in sample_resumes:
        cand = candidate_map.get(item["match_key"])
        if not cand:
            continue

        existing_resume = (
            db.query(Resume)
            .filter(Resume.agency_id == agency_id, Resume.candidate_id == cand.id)
            .first()
        )

        pdf_bytes = generate_synthetic_resume_pdf(
            candidate_name=item["name"],
            title=item["title"],
            skills=item["skills"],
            summary=item["summary"],
            experience_highlights=item["highlights"],
        )
        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

        if existing_resume:
            # Check physical file existence in storage
            if not storage.exists(existing_resume.storage_key):
                storage.save(pdf_bytes, existing_resume.storage_key)
        else:
            # Create Resume record and persist file
            storage_key = f"{str(agency_id)}/{uuid.uuid4().hex}.pdf"
            storage.save(pdf_bytes, storage_key)

            demo_recruiter = (
                db.query(User)
                .filter(User.agency_id == agency_id, User.email == DEMO_USER_EMAIL)
                .first()
            )

            new_resume = Resume(
                id=uuid.uuid4(),
                agency_id=agency_id,
                candidate_id=cand.id,
                uploaded_by=demo_recruiter.id if demo_recruiter else None,
                original_filename=item["filename"],
                stored_filename=storage_key.split("/")[-1],
                storage_key=storage_key,
                mime_type="application/pdf",
                file_size=len(pdf_bytes),
                sha256_hash=sha256_hash,
                page_count=1,
                extracted_text=f"{item['name']} - {item['title']}\n\nSummary:\n{item['summary']}\n\nSkills:\n{', '.join(item['skills'])}",
                language="en",
                processing_status=ResumeProcessingStatus.PROCESSED,
                upload_status="COMPLETED",
            )
            db.add(new_resume)
            db.flush()

            # Add extracted profile representation
            extracted_profile = ResumeExtractedProfile(
                id=uuid.uuid4(),
                agency_id=agency_id,
                resume_id=new_resume.id,
                full_name=item["name"],
                email=f"{item['name'].lower().replace(' ', '.')}@synthetic-example.com",
                phone="+1-555-0199",
                current_title=item["title"],
                total_experience_months=72 if "Senior" in item["title"] else 60,
                skills=item["skills"],
                highest_degree="Bachelor of Science in Computer Science",
                verification_status=VerificationStatus.VERIFIED,
                review_status=RecruiterReviewStatus.VERIFIED,
                confidence_score=0.98,
            )
            db.add(extracted_profile)

    db.commit()


def self_heal_demo_resume(db: Session, resume: Resume) -> bool:
    """
    On-demand self-healing: if an ephemeral Render instance lost the local resume file
    for a demo candidate, reconstitutes the PDF transparently before download/streaming.
    """
    agency = db.query(Agency).filter(Agency.id == resume.agency_id).first()
    if not agency or agency.slug != DEMO_AGENCY_SLUG:
        return False

    candidate = db.query(Candidate).filter(Candidate.id == resume.candidate_id).first() if resume.candidate_id else None
    cand_name = candidate.full_name.replace(" [Synthetic]", "") if candidate else "Demo Candidate"

    pdf_bytes = generate_synthetic_resume_pdf(
        candidate_name=cand_name,
        title=candidate.current_title if candidate else "Software Professional",
        skills=["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        summary="Synthetic candidate resume verified for HireLens AI challenge demo.",
        experience_highlights=[
            "Enterprise experience verified through HireLens AI deterministic scoring.",
            "Synthetic candidate document maintained for ephemeral container reliability.",
        ],
    )
    storage = get_storage_provider()
    storage.save(pdf_bytes, resume.storage_key)
    return True

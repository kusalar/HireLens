import json
from typing import Dict, Any, List, Optional
from app.schemas.matching import MatchExplanationSchema
from app.services.matching_engine import MatchScoringResult
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.enums import MatchStatus
from app.services.ai_provider_service import get_ai_provider


class MatchExplanationService:
    """
    Coordinates evidence-grounded AI explanations for matching results.
    Never allows AI to calculate or modify scores.
    Gracefully falls back to deterministic factual explanations when AI is offline.
    """

    def __init__(self):
        self.ai_provider = get_ai_provider()

    def _build_fallback_explanation(
        self,
        job: Job,
        candidate: Candidate,
        scoring: MatchScoringResult,
    ) -> MatchExplanationSchema:
        return self.generate_explanation(job, candidate, scoring)

    def generate_explanation(
        self,
        job: Job,
        candidate: Candidate,
        scoring: MatchScoringResult,
    ) -> MatchExplanationSchema:

        # 1. Structure the verified evidence payload
        demonstrated = []
        partial = []
        missing = []
        verification = []

        for ev in scoring.evidences:
            item = {
                "criterion": ev.criterion_name,
                "type": ev.criterion_type,
                "expected": ev.expected_requirement,
                "evidence": ev.candidate_evidence,
                "excerpt": ev.source_excerpt,
                "page": ev.source_page,
            }
            if ev.evidence_status == MatchStatus.DEMONSTRATED:
                demonstrated.append(item)
            elif ev.evidence_status == MatchStatus.PARTIAL:
                item["similarity"] = ev.semantic_similarity
                partial.append(item)
            elif ev.evidence_status == MatchStatus.NOT_FOUND:
                missing.append(item)
            elif ev.evidence_status == MatchStatus.NEEDS_VERIFICATION:
                verification.append(item)

        payload = {
            "job_title": job.title,
            "job_department": job.department,
            "overall_score": scoring.overall_score,
            "dimensions": {
                "required_skills": scoring.required_skills_score,
                "relevant_experience": scoring.experience_score,
                "preferred_skills": scoring.preferred_skills_score,
                "project_relevance": scoring.project_relevance_score,
                "other_criteria": scoring.other_criteria_score,
            },
            "demonstrated_items": demonstrated,
            "partial_items": partial,
            "missing_items": missing,
            "verification_items": verification,
        }

        # 2. Attempt AI explanation
        try:
            if hasattr(self.ai_provider, "explain_match"):
                res = self.ai_provider.explain_match(payload)
                if res and res.success and res.data:
                    return res.data
        except Exception:
            pass

        # 3. Deterministic Grounded Fallback (when AI is offline or returns invalid output)
        return self._generate_deterministic_explanation(job, candidate, scoring, demonstrated, partial, missing, verification)

    def _generate_deterministic_explanation(
        self,
        job: Job,
        candidate: Candidate,
        scoring: MatchScoringResult,
        demonstrated: List[Dict[str, Any]],
        partial: List[Dict[str, Any]],
        missing: List[Dict[str, Any]],
        verification: List[Dict[str, Any]],
    ) -> MatchExplanationSchema:
        """
        Deterministic, evidence-grounded explanation when AI is unavailable.
        Zero hallucination, zero score fabrication.
        """
        # Summary
        if scoring.overall_score >= 75.0:
            summary = (
                f"Candidate demonstrates strong evidence alignment ({scoring.overall_score:.1f}/100) with key requirements for {job.title}. "
                f"Demonstrated {len(demonstrated)} core criteria with direct resume context."
            )
        elif scoring.overall_score >= 50.0:
            summary = (
                f"Candidate shows moderate alignment ({scoring.overall_score:.1f}/100) with '{job.title}'. "
                f"{len(demonstrated)} criteria demonstrated, with {len(partial)} partial associations and {len(verification)} items requiring recruiter clarification."
            )
        else:
            summary = (
                f"Candidate has limited documented overlap ({scoring.overall_score:.1f}/100) with job requirements for {job.title}. "
                f"{len(missing)} requirements lack verified evidence in current resume records."
            )

        # Strengths
        strengths = []
        for d in demonstrated[:4]:
            excerpt_note = f" (page {d['page']})" if d.get("page") else ""
            strengths.append(f"Demonstrated {d['criterion']}: confirmed via {d.get('evidence') or 'resume'}{excerpt_note}.")

        if not strengths:
            strengths.append("Foundational professional background documented in candidate profile.")

        # Gaps
        skill_gaps = []
        for m in missing[:3]:
            skill_gaps.append(f"No direct evidence found for '{m['criterion']}' in candidate records.")
        for p in partial[:2]:
            skill_gaps.append(f"Partial alignment on '{p['criterion']}': related background '{p.get('evidence')}' noted.")

        # Verification items
        verification_items = []
        for v in verification[:3]:
            verification_items.append(f"Verify depth of experience in '{v['criterion']}' during screening.")
        if not verification_items and missing:
            verification_items.append(f"Inquire if candidate has unlisted experience in: {', '.join(m['criterion'] for m in missing[:2])}.")

        # Suggested Questions
        questions = []
        if missing:
            questions.append(f"Could you elaborate on any professional experience or hands-on projects you have with {missing[0]['criterion']}?")
        if partial:
            questions.append(f"How have you applied your knowledge in {partial[0].get('evidence') or partial[0]['criterion']} in past production environments?")
        if demonstrated:
            questions.append(f"Walk me through a challenging problem you solved using {demonstrated[0]['criterion']}.")
        questions.append("What aspects of this role's core responsibilities align most closely with your career trajectory?")

        return MatchExplanationSchema(
            summary=summary,
            strengths=strengths,
            skill_gaps=skill_gaps,
            verification_items=verification_items,
            suggested_interview_questions=questions,
        )

import json
import math
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
import uuid

from app.models.enums import RequirementType, MatchStatus, VerificationStatus
from app.models.job import Job, JobRequirement
from app.models.candidate import Candidate, CandidateSkill, CandidateExperience, CandidateEducation
from app.models.resume import Resume, ResumeExtractedProfile, ResumeEvidence
from app.services.skill_normalization_service import skill_normalizer
from app.services.embedding_service import get_embedding_provider, BaseEmbeddingProvider


@dataclass
class ScoringConfig:
    scoring_version: str = "v1.0"
    required_skills_weight: float = 0.40
    experience_weight: float = 0.25
    preferred_skills_weight: float = 0.15
    project_relevance_weight: float = 0.10
    other_criteria_weight: float = 0.10

    # Evidence status numeric multipliers (heuristics)
    val_demonstrated: float = 1.0
    val_partial: float = 0.5
    val_needs_verification: float = 0.25
    val_not_found: float = 0.0

    # Semantic similarity thresholds
    semantic_high_threshold: float = 0.78
    semantic_partial_threshold: float = 0.60


@dataclass
class MatchEvidenceData:
    criterion_name: str
    criterion_type: str  # REQUIRED_SKILL, PREFERRED_SKILL, EXPERIENCE, PROJECT, OTHER
    expected_requirement: str
    evidence_status: MatchStatus
    candidate_evidence: Optional[str] = None
    job_requirement_id: Optional[uuid.UUID] = None
    source_resume_id: Optional[uuid.UUID] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    semantic_similarity: Optional[float] = None
    score_contribution: float = 0.0
    explanation: Optional[str] = None
    verification_status: VerificationStatus = VerificationStatus.UNREVIEWED


@dataclass
class MatchScoringResult:
    overall_score: float
    required_skills_score: float
    experience_score: float
    preferred_skills_score: float
    project_relevance_score: float
    other_criteria_score: float
    matched_requirements_count: int
    partial_requirements_count: int
    missing_requirements_count: int
    needs_verification_count: int
    evidences: List[MatchEvidenceData] = field(default_factory=list)
    scoring_version: str = "v1.0"


class DeterministicMatchingEngine:
    """
    Deterministic recruitment matching engine.
    Calculates dimensional alignment scores strictly using verifiable evidence and Python heuristics.
    Never delegates score calculation to an LLM.
    """

    def __init__(
        self,
        config: Optional[ScoringConfig] = None,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
    ):
        self.config = config or ScoringConfig()
        self.embedding = embedding_provider or get_embedding_provider()

    def score_candidate_for_job(
        self,
        job: Job,
        candidate: Candidate,
        resumes: Optional[List[Resume]] = None,
        latest_extracted_profile: Optional[ResumeExtractedProfile] = None,
        resume_evidences: Optional[List[ResumeEvidence]] = None,
    ) -> MatchScoringResult:
        resumes = resumes or []
        resume_evidences = resume_evidences or []

        # Partition job requirements into mandatory vs preferred
        req_skills: List[JobRequirement] = []
        pref_skills: List[JobRequirement] = []
        other_criteria: List[JobRequirement] = []

        for req in (job.requirements or []):
            rtype = getattr(req, "requirement_type", None) or RequirementType.SKILL
            if rtype == RequirementType.SKILL:
                if req.is_mandatory:
                    req_skills.append(req)
                else:
                    pref_skills.append(req)
            else:
                other_criteria.append(req)


        # 1. Evaluate Required Skills
        req_score, req_evs = self._evaluate_skills(
            job_requirements=req_skills,
            candidate=candidate,
            resume_evidences=resume_evidences,
            is_mandatory=True,
        )

        # 2. Evaluate Preferred Skills
        pref_score, pref_evs = self._evaluate_skills(
            job_requirements=pref_skills,
            candidate=candidate,
            resume_evidences=resume_evidences,
            is_mandatory=False,
        )

        # 3. Evaluate Experience
        exp_score, exp_evs = self._evaluate_experience(
            job=job,
            candidate=candidate,
            resumes=resumes,
        )

        # 4. Evaluate Project Relevance
        proj_score, proj_evs = self._evaluate_projects(
            job=job,
            candidate=candidate,
            extracted_profile=latest_extracted_profile,
            resumes=resumes,
        )

        # 5. Evaluate Other Criteria (Education, Work Mode, Location)
        other_score, other_evs = self._evaluate_other_criteria(
            job=job,
            candidate=candidate,
            other_requirements=other_criteria,
            resumes=resumes,
        )

        all_evidences = req_evs + pref_evs + exp_evs + proj_evs + other_evs

        # Calculate counts
        matched_count = sum(1 for e in all_evidences if e.evidence_status == MatchStatus.DEMONSTRATED)
        partial_count = sum(1 for e in all_evidences if e.evidence_status == MatchStatus.PARTIAL)
        missing_count = sum(1 for e in all_evidences if e.evidence_status == MatchStatus.NOT_FOUND)
        needs_verif_count = sum(1 for e in all_evidences if e.evidence_status == MatchStatus.NEEDS_VERIFICATION)

        # Weighted Overall Score with dynamic weight re-normalization if dimension has no requirements
        active_weights = {
            "req": self.config.required_skills_weight if req_skills else 0.0,
            "exp": self.config.experience_weight,
            "pref": self.config.preferred_skills_weight if pref_skills else 0.0,
            "proj": self.config.project_relevance_weight,
            "other": self.config.other_criteria_weight,
        }
        total_active_weight = sum(active_weights.values())
        if total_active_weight == 0.0:
            total_active_weight = 1.0

        overall = (
            (req_score * active_weights["req"])
            + (exp_score * active_weights["exp"])
            + (pref_score * active_weights["pref"])
            + (proj_score * active_weights["proj"])
            + (other_score * active_weights["other"])
        ) / total_active_weight

        # Bounded between 0.0 and 100.0
        clamped_overall = max(0.0, min(100.0, round(overall, 1)))

        return MatchScoringResult(
            overall_score=clamped_overall,
            required_skills_score=max(0.0, min(100.0, round(req_score, 1))),
            experience_score=max(0.0, min(100.0, round(exp_score, 1))),
            preferred_skills_score=max(0.0, min(100.0, round(pref_score, 1))),
            project_relevance_score=max(0.0, min(100.0, round(proj_score, 1))),
            other_criteria_score=max(0.0, min(100.0, round(other_score, 1))),
            matched_requirements_count=matched_count,
            partial_requirements_count=partial_count,
            missing_requirements_count=missing_count,
            needs_verification_count=needs_verif_count,
            evidences=all_evidences,
            scoring_version=self.config.scoring_version,
        )

    def _evaluate_skills(
        self,
        job_requirements: List[JobRequirement],
        candidate: Candidate,
        resume_evidences: List[ResumeEvidence],
        is_mandatory: bool,
    ) -> Tuple[float, List[MatchEvidenceData]]:
        if not job_requirements:
            return 100.0, []

        evidences: List[MatchEvidenceData] = []
        total_importance = sum(max(0.1, r.importance_weight) for r in job_requirements)
        if total_importance <= 0.0:
            total_importance = float(len(job_requirements))

        weighted_points = 0.0
        crit_type = "REQUIRED_SKILL" if is_mandatory else "PREFERRED_SKILL"

        # Build candidate skills map (normalized -> skill object)
        candidate_skills_map: Dict[str, CandidateSkill] = {}
        for cs in (candidate.skills or []):
            norm = skill_normalizer.normalize(cs.normalized_skill or cs.skill_name).lower()
            candidate_skills_map[norm] = cs

        for req in job_requirements:
            req_norm = skill_normalizer.normalize(req.normalized_skill or req.requirement_text).lower()
            normalized_weight = max(0.1, req.importance_weight) / total_importance

            # 1. Exact canonical skill match
            matched_skill = None
            for cand_norm, cs in candidate_skills_map.items():
                if cand_norm == req_norm or skill_normalizer.are_skills_equivalent(cand_norm, req_norm):
                    matched_skill = cs
                    break

            # Check resume evidence records for supporting excerpt
            supporting_evidence: Optional[ResumeEvidence] = None
            for rev in resume_evidences:
                if rev.field_name.startswith("skill:") and skill_normalizer.are_skills_equivalent(
                    rev.field_name.split(":", 1)[1], req_norm
                ):
                    supporting_evidence = rev
                    break

            if matched_skill:
                # Skill present in profile
                has_excerpt = bool(matched_skill.evidence or (supporting_evidence and supporting_evidence.source_excerpt))
                excerpt = matched_skill.evidence or (supporting_evidence.source_excerpt if supporting_evidence else None)
                page = matched_skill.source_page or (supporting_evidence.source_page if supporting_evidence else None)
                source_res_id = supporting_evidence.resume_id if supporting_evidence else None

                if has_excerpt:
                    status = MatchStatus.DEMONSTRATED
                    contrib = self.config.val_demonstrated
                    expl = f"Explicitly demonstrated in resume with supporting excerpt on page {page or 1}."
                else:
                    status = MatchStatus.NEEDS_VERIFICATION
                    contrib = self.config.val_needs_verification
                    expl = "Skill listed on profile but lacks verifiable resume context. Recruiter verification advised."

                evidences.append(
                    MatchEvidenceData(
                        criterion_name=req.requirement_text,
                        criterion_type=crit_type,
                        expected_requirement=req.requirement_text,
                        evidence_status=status,
                        candidate_evidence=matched_skill.skill_name,
                        job_requirement_id=req.id,
                        source_resume_id=source_res_id,
                        source_page=page,
                        source_excerpt=excerpt,
                        semantic_similarity=1.0,
                        score_contribution=round(contrib * normalized_weight * 100, 2),
                        explanation=expl,
                        verification_status=(
                            supporting_evidence.verification_status
                            if supporting_evidence
                            else VerificationStatus.UNREVIEWED
                        ),
                    )
                )
                weighted_points += contrib * normalized_weight
            else:
                # 2. Semantic association check across candidate skills
                best_sim = 0.0
                best_cand_skill = None
                for cand_norm, cs in candidate_skills_map.items():
                    sim = self.embedding.calculate_text_similarity(cand_norm, req_norm)
                    if sim > best_sim:
                        best_sim = sim
                        best_cand_skill = cs

                # Check if candidate has attributable supporting evidence for this related skill
                has_attributable_related_evidence = False
                if best_cand_skill:
                    has_attributable_related_evidence = bool(
                        best_cand_skill.evidence or
                        any(
                            rev.source_excerpt for rev in resume_evidences
                            if rev.field_name.startswith("skill:") and
                            skill_normalizer.are_skills_equivalent(rev.field_name.split(":", 1)[1], best_cand_skill.skill_name)
                        )
                    )

                # STRICT RULE: Semantic similarity alone NEVER establishes a demonstrated or partial skill.
                # High similarity without attributable evidence CANNOT independently produce DEMONSTRATED or PARTIAL.
                if has_attributable_related_evidence and best_sim >= self.config.semantic_high_threshold:
                    # Actual attributable evidence exists for a closely related adjacent skill
                    status = MatchStatus.PARTIAL
                    contrib = self.config.val_partial
                    expl = (
                        f"Attributable evidence found for adjacent skill '{best_cand_skill.skill_name}' "
                        f"(similarity assistance score: {best_sim:.2f}). Partial credit awarded for demonstrated related background."
                    )
                    weighted_points += contrib * normalized_weight
                elif best_sim >= self.config.semantic_partial_threshold:
                    # Semantic association surfaced, but lacks attributable evidence -> NEEDS_VERIFICATION (0 credit)
                    status = MatchStatus.NEEDS_VERIFICATION
                    contrib = 0.0
                    expl = (
                        f"Potential semantic association identified with candidate skill '{best_cand_skill.skill_name}' ({best_sim:.2f}). "
                        "Similarity alone is an assistance signal and does not establish qualification. Recruiter verification required."
                    )
                else:
                    # Not found
                    status = MatchStatus.NOT_FOUND
                    contrib = 0.0
                    expl = "No direct supporting evidence located in current records (does not imply candidate lacks ability)."

                evidences.append(
                    MatchEvidenceData(
                        criterion_name=req.requirement_text,
                        criterion_type=crit_type,
                        expected_requirement=req.requirement_text,
                        evidence_status=status,
                        candidate_evidence=best_cand_skill.skill_name if best_cand_skill and status != MatchStatus.NOT_FOUND else None,
                        job_requirement_id=req.id,
                        semantic_similarity=round(best_sim, 2) if best_sim > 0.0 else None,
                        score_contribution=round(contrib * normalized_weight * 100, 2),
                        explanation=expl,
                        verification_status=VerificationStatus.UNREVIEWED,
                    )
                )


        dimension_score = weighted_points * 100.0
        return dimension_score, evidences

    def _evaluate_experience(
        self,
        job: Job,
        candidate: Candidate,
        resumes: List[Resume],
    ) -> Tuple[float, List[MatchEvidenceData]]:
        """
        Evaluates candidate work history for relevance to job title & responsibilities.
        Avoids naive total-months comparison when candidate experience is unrelated.
        Does not penalize employment gaps.
        """
        min_years = job.minimum_experience or 0
        min_months = min_years * 12

        experiences: List[CandidateExperience] = candidate.experiences or []
        source_res_id = resumes[0].id if resumes else None

        if not experiences and (candidate.total_experience_months or 0) == 0:
            # Incomplete data -> NEEDS_VERIFICATION instead of assuming 0
            ev = MatchEvidenceData(
                criterion_name="Work History Completeness",
                criterion_type="EXPERIENCE",
                expected_requirement=f"{min_years}+ years relevant experience for {job.title}",
                evidence_status=MatchStatus.NEEDS_VERIFICATION,
                candidate_evidence=None,
                source_resume_id=source_res_id,
                score_contribution=25.0,
                explanation="No structured experience entries provided on profile. Verification needed from resume.",
                verification_status=VerificationStatus.UNREVIEWED,
            )
            return 25.0, [ev]

        # Calculate relevance of each past role to target job title and description
        job_target_text = f"{job.title} {job.department or ''} {job.responsibilities or ''}"
        relevant_role_count = 0
        max_role_relevance = 0.0
        relevant_descriptions = []

        for exp in experiences:
            role_text = f"{exp.job_title} {exp.description or ''}"
            sim = self.embedding.calculate_text_similarity(role_text, job_target_text)
            if sim > max_role_relevance:
                max_role_relevance = sim
            if sim >= 0.50:
                relevant_role_count += 1
                relevant_descriptions.append(f"{exp.job_title} at {exp.company}")

        cand_months = candidate.total_experience_months or (len(experiences) * 12)

        # Baseline duration ratio
        if min_months > 0:
            duration_ratio = min(1.0, cand_months / min_months)
        else:
            duration_ratio = 1.0

        # Experience score blends relevant role alignment with duration ratio
        if max_role_relevance >= 0.70:
            relevance_factor = 1.0
        elif max_role_relevance >= 0.50:
            relevance_factor = 0.75
        elif max_role_relevance >= 0.35:
            relevance_factor = 0.45
        else:
            relevance_factor = 0.20  # Mostly unrelated experience (e.g. Sales for Python Eng)

        exp_score = duration_ratio * relevance_factor * 100.0

        if exp_score >= 80.0:
            status = MatchStatus.DEMONSTRATED
            expl = f"Demonstrated {cand_months // 12} years experience with high relevance to {job.title}."
        elif exp_score >= 45.0:
            status = MatchStatus.PARTIAL
            expl = f"Partial alignment: experience meets duration but includes partially related roles ({', '.join(relevant_descriptions[:2]) or 'partially related'})."
        elif candidate.total_experience_months and candidate.total_experience_months > 0 and relevance_factor < 0.3:
            status = MatchStatus.PARTIAL
            expl = "Candidate has work experience, but roles show low domain overlap with the target job criteria."
        else:
            status = MatchStatus.NEEDS_VERIFICATION
            expl = "Experience details require recruiter clarification against specific job responsibilities."

        ev = MatchEvidenceData(
            criterion_name="Relevant Experience",
            criterion_type="EXPERIENCE",
            expected_requirement=f"{min_years}+ years relevant experience for '{job.title}'",
            evidence_status=status,
            candidate_evidence=f"{cand_months // 12} years total across {len(experiences)} roles",
            source_resume_id=source_res_id,
            semantic_similarity=round(max_role_relevance, 2),
            score_contribution=round(exp_score, 1),
            explanation=expl,
            verification_status=VerificationStatus.UNREVIEWED,
        )
        return exp_score, [ev]

    def _evaluate_projects(
        self,
        job: Job,
        candidate: Candidate,
        extracted_profile: Optional[ResumeExtractedProfile],
        resumes: List[Resume],
    ) -> Tuple[float, List[MatchEvidenceData]]:
        """
        Evaluates candidate projects from extracted profile JSON against job responsibilities.
        """
        source_res_id = resumes[0].id if resumes else None
        job_context = f"{job.title} {job.responsibilities or ''} {job.description or ''}"

        projects_list = []
        if extracted_profile and extracted_profile.structured_extraction_json:
            try:
                data = json.loads(extracted_profile.structured_extraction_json)
                projects_list = data.get("projects", [])
            except Exception:
                pass

        if not projects_list:
            ev = MatchEvidenceData(
                criterion_name="Project Portfolio",
                criterion_type="PROJECT",
                expected_requirement=f"Practical projects demonstrating alignment with {job.title}",
                evidence_status=MatchStatus.NOT_FOUND,
                candidate_evidence=None,
                source_resume_id=source_res_id,
                score_contribution=0.0,
                explanation="No specific technical projects detailed in resume extraction.",
                verification_status=VerificationStatus.UNREVIEWED,
            )
            # Default neutral score for projects if not explicitly requested
            return 50.0, [ev]

        best_sim = 0.0
        best_proj = None
        for p in projects_list:
            p_name = p.get("project_name", "")
            p_desc = p.get("description", "")
            p_tech = " ".join(p.get("technologies", []))
            full_p = f"{p_name} {p_desc} {p_tech}"
            sim = self.embedding.calculate_text_similarity(full_p, job_context)
            if sim > best_sim:
                best_sim = sim
                best_proj = p

        if best_sim >= 0.70:
            status = MatchStatus.DEMONSTRATED
            score = 100.0
            expl = f"Demonstrated high relevance in project '{best_proj.get('project_name')}'."
        elif best_sim >= 0.50:
            status = MatchStatus.PARTIAL
            score = 65.0
            expl = f"Partially aligned project '{best_proj.get('project_name')}' with relevant technologies."
        else:
            status = MatchStatus.PARTIAL
            score = 40.0
            expl = f"Projects present ({len(projects_list)} total) with moderate overlap to job domain."

        ev = MatchEvidenceData(
            criterion_name="Relevant Projects",
            criterion_type="PROJECT",
            expected_requirement=f"Relevant project experience for {job.title}",
            evidence_status=status,
            candidate_evidence=best_proj.get("project_name") if best_proj else f"{len(projects_list)} projects listed",
            source_resume_id=source_res_id,
            source_excerpt=best_proj.get("description") if best_proj else None,
            semantic_similarity=round(best_sim, 2),
            score_contribution=round(score, 1),
            explanation=expl,
            verification_status=VerificationStatus.UNREVIEWED,
        )
        return score, [ev]

    def _evaluate_other_criteria(
        self,
        job: Job,
        candidate: Candidate,
        other_requirements: List[JobRequirement],
        resumes: List[Resume],
    ) -> Tuple[float, List[MatchEvidenceData]]:
        """
        Evaluates education, location/work-mode, and custom requirements.
        """
        evidences: List[MatchEvidenceData] = []
        source_res_id = resumes[0].id if resumes else None

        points = 0.0
        items_count = 0

        # 1. Location / Work Mode alignment
        items_count += 1
        work_mode_str = (
            job.work_mode.value
            if hasattr(job.work_mode, "value")
            else str(job.work_mode or "")
        ).upper()

        if work_mode_str == "REMOTE":
            points += 1.0
            evidences.append(
                MatchEvidenceData(
                    criterion_name="Work Mode",
                    criterion_type="OTHER",
                    expected_requirement="Remote Eligible",
                    evidence_status=MatchStatus.DEMONSTRATED,
                    candidate_evidence=f"Location: {candidate.current_location or 'Not specified'} (Remote role)",
                    score_contribution=100.0,
                    explanation="Job is remote, no geographical barrier.",
                )
            )
        elif candidate.current_location and job.location:

            sim = self.embedding.calculate_text_similarity(candidate.current_location, job.location)
            if sim > 0.7 or candidate.current_location.lower() in job.location.lower():
                points += 1.0
                status = MatchStatus.DEMONSTRATED
                expl = f"Candidate location '{candidate.current_location}' aligns with job location '{job.location}'."
            else:
                points += 0.5
                status = MatchStatus.PARTIAL
                expl = f"Candidate in '{candidate.current_location}', job in '{job.location}'. Verify relocation or commuting readiness."
            evidences.append(
                MatchEvidenceData(
                    criterion_name="Location Alignment",
                    criterion_type="OTHER",
                    expected_requirement=f"Location: {job.location}",
                    evidence_status=status,
                    candidate_evidence=candidate.current_location,
                    score_contribution=round(points * 100, 1),
                    explanation=expl,
                )
            )
        else:
            points += 0.75
            evidences.append(
                MatchEvidenceData(
                    criterion_name="Location Alignment",
                    criterion_type="OTHER",
                    expected_requirement=f"Location: {job.location or 'Flexible'}",
                    evidence_status=MatchStatus.NEEDS_VERIFICATION,
                    candidate_evidence=candidate.current_location,
                    score_contribution=75.0,
                    explanation="Candidate location not fully verified against job location.",
                )
            )

        # 2. Education requirements
        educations = candidate.educations or []
        for req in other_requirements:
            items_count += 1
            if req.requirement_type == RequirementType.EDUCATION:
                if educations:
                    # Candidate has education records
                    deg = f"{educations[0].qualification} in {educations[0].field_of_study or ''}"
                    sim = self.embedding.calculate_text_similarity(deg, req.requirement_text)
                    if sim >= 0.65:
                        points += 1.0
                        status = MatchStatus.DEMONSTRATED
                        expl = f"Verified degree: {deg} at {educations[0].institution}."
                    else:
                        points += 0.75
                        status = MatchStatus.PARTIAL
                        expl = f"Candidate holds {deg}; verify equivalence to {req.requirement_text}."
                    evidences.append(
                        MatchEvidenceData(
                            criterion_name=req.requirement_text,
                            criterion_type="OTHER",
                            expected_requirement=req.requirement_text,
                            evidence_status=status,
                            candidate_evidence=deg,
                            source_resume_id=source_res_id,
                            job_requirement_id=req.id,
                            score_contribution=round(points * 100 / items_count, 1),
                            explanation=expl,
                        )
                    )
                else:
                    points += 0.25
                    evidences.append(
                        MatchEvidenceData(
                            criterion_name=req.requirement_text,
                            criterion_type="OTHER",
                            expected_requirement=req.requirement_text,
                            evidence_status=MatchStatus.NEEDS_VERIFICATION,
                            candidate_evidence=None,
                            job_requirement_id=req.id,
                            score_contribution=25.0,
                            explanation="No formal degree records entered; verify education on original resume.",
                        )
                    )
            else:
                # Custom requirement
                points += 0.5
                evidences.append(
                    MatchEvidenceData(
                        criterion_name=req.requirement_text,
                        criterion_type="OTHER",
                        expected_requirement=req.requirement_text,
                        evidence_status=MatchStatus.NEEDS_VERIFICATION,
                        candidate_evidence=None,
                        job_requirement_id=req.id,
                        score_contribution=50.0,
                        explanation=f"Custom criteria '{req.requirement_text}' requires recruiter evaluation.",
                    )
                )

        score = (points / max(1, items_count)) * 100.0
        return score, evidences

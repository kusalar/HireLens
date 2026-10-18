from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    agency,
    jobs,
    candidates,
    resumes,
    matching,
    applications,
    interviews,
    notifications,
    analytics,
    integrations,
    copilot,
    workflows,
    predictive,
    governance,
    billing,
    platform,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(agency.router, prefix="/agency", tags=["Agency"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Job Management"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["Candidate Management"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["Resume Processing"])
api_router.include_router(matching.router, prefix="/matching", tags=["Matching Intelligence"])
api_router.include_router(applications.router, prefix="/applications", tags=["Applications"])
api_router.include_router(applications.job_router, prefix="/jobs", tags=["Job Applications"])
api_router.include_router(applications.candidate_router, prefix="/candidates", tags=["Candidate Applications"])
api_router.include_router(applications.recruiter_router, prefix="/recruiters", tags=["Recruiter Applications"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(interviews.app_interview_router, prefix="/applications", tags=["Application Interviews"])
api_router.include_router(interviews.recruiter_interview_router, prefix="/recruiters", tags=["Recruiter Interviews"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications & Communication"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Recruitment Intelligence & Analytics"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Calendar & External Integrations"])
api_router.include_router(copilot.router, prefix="/copilot", tags=["AI Recruitment Copilot"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflow Automation & Orchestration"])
api_router.include_router(predictive.router, prefix="/predictive-analytics", tags=["Predictive Intelligence & Workforce Planning"])
api_router.include_router(governance.router, prefix="/governance", tags=["Enterprise Security, Compliance & Governance"])
api_router.include_router(billing.router, prefix="/billing", tags=["Enterprise SaaS Billing, Subscriptions & Monetization"])
api_router.include_router(platform.router, prefix="/platform", tags=["Platform Administration & Global Governance"])





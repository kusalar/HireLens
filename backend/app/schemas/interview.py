import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, EmailStr
from app.models.enums import (
    InterviewMode,
    InterviewStatus,
    InterviewRoundType,
    ParticipantRole,
    AttendanceStatus,
    FeedbackRecommendation,
    PipelineStageType,
)


class InterviewParticipantCreate(BaseModel):
    user_id: Optional[uuid.UUID] = None
    participant_name: str = Field(..., min_length=1, max_length=150)
    participant_email: EmailStr
    participant_role: ParticipantRole = ParticipantRole.INTERVIEWER
    attendance_status: AttendanceStatus = AttendanceStatus.INVITED


class InterviewParticipantRead(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    participant_name: str
    participant_email: str
    participant_role: ParticipantRole
    attendance_status: AttendanceStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewFeedbackCreate(BaseModel):
    overall_rating: int = Field(..., ge=1, le=5)
    recommendation: FeedbackRecommendation
    technical_assessment: Optional[str] = None
    communication_assessment: Optional[str] = None
    problem_solving_assessment: Optional[str] = None
    role_specific_assessment: Optional[str] = None
    strengths: Optional[List[str]] = None
    concerns: Optional[List[str]] = None
    detailed_feedback: str = Field(..., min_length=1)
    is_private: bool = False


class InterviewFeedbackUpdate(BaseModel):
    overall_rating: Optional[int] = Field(None, ge=1, le=5)
    recommendation: Optional[FeedbackRecommendation] = None
    technical_assessment: Optional[str] = None
    communication_assessment: Optional[str] = None
    problem_solving_assessment: Optional[str] = None
    role_specific_assessment: Optional[str] = None
    strengths: Optional[List[str]] = None
    concerns: Optional[List[str]] = None
    detailed_feedback: Optional[str] = None
    is_private: Optional[bool] = None


class InterviewFeedbackRead(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    reviewer_id: uuid.UUID
    reviewer_name: Optional[str] = None
    reviewer_role: Optional[str] = None
    overall_rating: int
    recommendation: FeedbackRecommendation
    technical_assessment: Optional[str] = None
    communication_assessment: Optional[str] = None
    problem_solving_assessment: Optional[str] = None
    role_specific_assessment: Optional[str] = None
    strengths: List[str] = []
    concerns: List[str] = []
    detailed_feedback: str
    is_private: bool
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewHistoryRead(BaseModel):
    id: uuid.UUID
    interview_id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InterviewCreate(BaseModel):
    round_name: str = Field(..., min_length=1, max_length=100)
    round_type: InterviewRoundType = InterviewRoundType.TECHNICAL
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    interview_mode: InterviewMode = InterviewMode.ONLINE
    scheduled_start: datetime
    scheduled_end: datetime
    timezone: str = "Asia/Kolkata"
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    participants: List[InterviewParticipantCreate] = []


class InterviewUpdate(BaseModel):
    round_name: Optional[str] = None
    round_type: Optional[InterviewRoundType] = None
    title: Optional[str] = None
    description: Optional[str] = None
    interview_mode: Optional[InterviewMode] = None
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    participants: Optional[List[InterviewParticipantCreate]] = None


class InterviewReschedule(BaseModel):
    scheduled_start: datetime
    scheduled_end: datetime
    timezone: str = "Asia/Kolkata"
    reason: str = Field(..., min_length=1)


class InterviewCancel(BaseModel):
    reason: str = Field(..., min_length=1)


class InterviewComplete(BaseModel):
    notes: Optional[str] = None


class InterviewRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    application_id: uuid.UUID
    round_name: str
    round_type: InterviewRoundType
    title: str
    description: Optional[str] = None
    interview_mode: InterviewMode
    scheduled_start: datetime
    scheduled_end: datetime
    timezone: str
    location: Optional[str] = None
    meeting_url: Optional[str] = None
    status: InterviewStatus
    version: int
    created_by: Optional[uuid.UUID] = None
    created_by_name: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Contextual Denormalized fields
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_email: Optional[str] = None
    application_status: Optional[PipelineStageType] = None

    # Summarized children
    participants: List[InterviewParticipantRead] = []
    feedbacks_count: int = 0
    average_rating: Optional[float] = None
    scheduled_start_ist: Optional[str] = None
    scheduled_end_ist: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class InterviewDetailRead(BaseModel):
    interview: InterviewRead
    participants: List[InterviewParticipantRead] = []
    feedbacks: List[InterviewFeedbackRead] = []
    history: List[InterviewHistoryRead] = []
    feedbacks_count: int = 0
    average_rating: Optional[float] = None
    user_can_submit_feedback: bool = False
    user_has_submitted_feedback: bool = False


class InterviewListResponse(BaseModel):
    items: List[InterviewRead]
    total: int = 0
    status_counts: Dict[str, int] = {}


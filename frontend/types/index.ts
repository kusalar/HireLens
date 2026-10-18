export type WorkMode = "ONSITE" | "HYBRID" | "REMOTE";
export type EmploymentType = "FULL_TIME" | "PART_TIME" | "CONTRACT" | "INTERNSHIP";
export type JobStatus = "DRAFT" | "ACTIVE" | "PAUSED" | "ARCHIVED" | "CLOSED";
export type RequirementType = "SKILL" | "EXPERIENCE" | "EDUCATION" | "CERTIFICATION" | "LOCATION" | "OTHER";
export type CandidateProfileStatus = "ACTIVE" | "ARCHIVED" | "PLACED" | "INACTIVE";

export interface JobRequirement {
  id?: string;
  job_id?: string;
  requirement_text: string;
  normalized_skill?: string;
  requirement_type: RequirementType;
  importance_weight: number;
  is_mandatory: boolean;
  created_at?: string;
}

export interface Job {
  id: string;
  agency_id: string;
  created_by?: string;
  title: string;
  department?: string;
  description?: string;
  responsibilities?: string;
  location?: string;
  work_mode: WorkMode;
  employment_type: EmploymentType;
  minimum_experience: number;
  maximum_experience?: number;
  status: JobStatus;
  created_at: string;
  updated_at?: string;
  requirements?: JobRequirement[];
  requirements_count?: number;
}

export interface CandidateSkill {
  id?: string;
  candidate_id?: string;
  skill_name: string;
  normalized_skill?: string;
  proficiency?: string;
  evidence?: string;
}

export interface CandidateExperience {
  id?: string;
  candidate_id?: string;
  company: string;
  job_title: string;
  start_date?: string;
  end_date?: string;
  description?: string;
}

export interface CandidateEducation {
  id?: string;
  candidate_id?: string;
  institution: string;
  qualification: string;
  field_of_study?: string;
  start_year?: number;
  end_year?: number;
}

export interface RecruiterNote {
  id: string;
  candidate_id: string;
  agency_id: string;
  created_by?: string;
  note: string;
  created_at: string;
  updated_at?: string;
  author_name?: string;
}

export interface Candidate {
  id: string;
  agency_id: string;
  full_name: string;
  email?: string;
  phone_encrypted?: string;
  current_title?: string;
  total_experience_months: number;
  current_location?: string;
  professional_summary?: string;
  profile_status: CandidateProfileStatus;
  created_at: string;
  updated_at?: string;
  skills_preview?: string[];
  skills?: CandidateSkill[];
  experiences?: CandidateExperience[];
  educations?: CandidateEducation[];
  notes?: RecruiterNote[];
}

export type ResumeProcessingStatus =
  | "UPLOADED"
  | "QUEUED"
  | "EXTRACTING"
  | "EXTRACTED"
  | "PARSING"
  | "REVIEW_REQUIRED"
  | "COMPLETED"
  | "FAILED";

export type VerificationStatus = "UNREVIEWED" | "VERIFIED" | "CORRECTED" | "REJECTED";
export type RecruiterReviewStatus = "PENDING" | "VERIFIED" | "CORRECTED" | "REJECTED";

export interface Resume {
  id: string;
  agency_id: string;
  candidate_id?: string;
  uploaded_by?: string;
  original_filename: string;
  stored_filename?: string;
  mime_type: string;
  file_size: number;
  sha256_hash: string;
  page_count?: number;
  language?: string;
  processing_status: ResumeProcessingStatus;
  upload_status: string;
  error_message?: string;
  created_at: string;
  updated_at?: string;
  candidate_name?: string;
}

export interface ResumeParseRun {
  id: string;
  resume_id: string;
  provider: string;
  model_name: string;
  model_version?: string;
  extraction_method: string;
  status: string;
  started_at: string;
  completed_at?: string;
  processing_duration_ms?: number;
  error_code?: string;
  error_message?: string;
  created_at: string;
}

export interface ExtractedSkillItem {
  skill_name: string;
  proficiency?: string;
  evidence?: string;
  source_page?: number;
}

export interface ExtractedExperienceItem {
  company: string;
  job_title: string;
  start_date?: string;
  end_date?: string;
  description?: string;
  evidence?: string;
  source_page?: number;
}

export interface ExtractedEducationItem {
  institution: string;
  qualification: string;
  field_of_study?: string;
  start_year?: number;
  end_year?: number;
  evidence?: string;
  source_page?: number;
}

export interface ResumeExtractedProfile {
  id: string;
  resume_id: string;
  parse_run_id: string;
  agency_id: string;
  extracted_name?: string;
  extracted_email?: string;
  extracted_phone?: string;
  extracted_location?: string;
  extracted_current_title?: string;
  extracted_summary?: string;
  extracted_experience_months?: number;
  structured_data?: {
    candidate_name?: string;
    email?: string;
    phone?: string;
    location?: string;
    current_title?: string;
    professional_summary?: string;
    total_experience_months?: number;
    skills?: ExtractedSkillItem[];
    experiences?: ExtractedExperienceItem[];
    educations?: ExtractedEducationItem[];
    languages?: string[];
    confidence_score?: number;
  };
  overall_confidence?: number;
  recruiter_review_status: RecruiterReviewStatus;
  created_at: string;
  updated_at?: string;
}

export interface ResumeEvidence {
  id: string;
  parse_run_id: string;
  resume_id: string;
  field_name: string;
  extracted_value: string;
  corrected_value?: string;
  source_page?: number;
  source_excerpt?: string;
  confidence?: number;
  verification_status: VerificationStatus;
  created_at: string;
}

export interface CandidateMatchSuggestion {
  candidate_id: string;
  full_name: string;
  email?: string;
  current_title?: string;
  match_reason: string;
}

export interface ResumeDetailResponse {
  resume: Resume;
  current_profile?: ResumeExtractedProfile;
  parse_runs: ResumeParseRun[];
  evidences: ResumeEvidence[];
  possible_matching_candidates: CandidateMatchSuggestion[];
}

export interface FileUploadResult {
  filename: string;
  status: "SUCCESS" | "DUPLICATE" | "REJECTED";
  resume_id?: string;
  resume?: Resume;
  error?: string;
  existing_resume_id?: string;
}

export interface BulkUploadResponse {
  total_files: number;
  successful_count: number;
  failed_count: number;
  duplicate_count: number;
  results: FileUploadResult[];
}

export type JobMatchRunStatus =
  | "PENDING"
  | "PROCESSING"
  | "COMPLETED"
  | "PARTIALLY_COMPLETED"
  | "FAILED";

export type MatchEvidenceStatus =
  | "DEMONSTRATED"
  | "PARTIAL"
  | "NOT_FOUND"
  | "NEEDS_VERIFICATION";

export interface JobMatchRun {
  id: string;
  agency_id: string;
  job_id: string;
  initiated_by?: string;
  scoring_version: string;
  matching_provider: string;
  embedding_model?: string;
  candidate_count: number;
  completed_count: number;
  failed_count: number;
  status: JobMatchRunStatus;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
  created_at: string;
}

export interface MatchEvidence {
  id: string;
  agency_id: string;
  match_result_id: string;
  job_requirement_id?: string;
  criterion_name: string;
  criterion_type: string;
  expected_requirement: string;
  evidence_status: MatchEvidenceStatus;
  candidate_evidence?: string;
  source_resume_id?: string;
  source_page?: number;
  source_excerpt?: string;
  semantic_similarity?: number;
  score_contribution: number;
  explanation?: string;
  verification_status: VerificationStatus;
  created_at: string;
}

export interface JobMatchResult {
  id: string;
  agency_id: string;
  job_id: string;
  candidate_id: string;
  match_run_id: string;
  overall_score: number;
  required_skills_score: number;
  experience_score: number;
  preferred_skills_score: number;
  project_relevance_score: number;
  other_criteria_score: number;
  matched_requirements_count: number;
  partial_requirements_count: number;
  missing_requirements_count: number;
  needs_verification_count: number;
  explanation?: string;
  strengths: string[];
  skill_gaps: string[];
  verification_items: string[];
  suggested_questions: string[];
  scoring_version: string;
  status: string;
  created_at: string;
  updated_at: string;
  candidate_name?: string;
  candidate_title?: string;
  candidate_email?: string;
  candidate_location?: string;
  job_title?: string;
  source_fingerprint?: string;
  is_stale?: boolean;
}


export interface JobMatchListResponse {
  items: JobMatchResult[];
  total: number;
  page: number;
  page_size: number;
  latest_run?: JobMatchRun;
}

export interface JobMatchResultDetailResponse {
  result: JobMatchResult;
  evidences: MatchEvidence[];
  run?: JobMatchRun;
  source_resumes?: Array<Record<string, unknown>>;
}

// -------------------------------------------------------------
// Phase 5: Recruitment Workspace & Application Pipeline
// -------------------------------------------------------------

export type PipelineStageType =
  | "APPLIED"
  | "UNDER_REVIEW"
  | "SHORTLISTED"
  | "INTERVIEW"
  | "SELECTED"
  | "REJECTED"
  | "ON_HOLD"
  | "WITHDRAWN";

export interface Application {
  id: string;
  agency_id: string;
  job_id: string;
  candidate_id: string;
  status: PipelineStageType;
  source?: string;
  applied_at: string;
  shortlisted_at?: string;
  last_activity_at: string;
  assigned_recruiter_id?: string;
  assigned_recruiter_name?: string;
  recruiter_summary?: string;
  archived_at?: string;
  created_at: string;
  updated_at?: string;
  candidate_name?: string;
  candidate_title?: string;
  candidate_email?: string;
  candidate_location?: string;
  total_experience_months?: number;
  job_title?: string;
  latest_match_score?: number;
  is_stale_match?: boolean;
}

export interface ApplicationStageHistory {
  id: string;
  application_id: string;
  previous_stage?: PipelineStageType;
  new_stage: PipelineStageType;
  changed_by?: string;
  changed_by_name?: string;
  reason?: string;
  created_at: string;
}

export interface ApplicationNote {
  id: string;
  application_id: string;
  author_id?: string;
  author_name?: string;
  content: string;
  created_at: string;
  updated_at?: string;
}

export interface ApplicationActivity {
  id: string;
  action: string;
  user_id?: string;
  user_name?: string;
  details?: string;
  created_at: string;
}

export interface ApplicationListResponse {
  items: Application[];
  total: number;
  stage_counts: Record<PipelineStageType, number>;
}

export interface ApplicationDetailResponse {
  application: Application;
  candidate: Candidate;
  job: Job;
  stage_history: ApplicationStageHistory[];
  notes: ApplicationNote[];
  activity: ApplicationActivity[];
  latest_match_result?: JobMatchResult;
  match_evidences?: MatchEvidence[];
}

export interface CandidateComparisonItem {
  candidate_id: string;
  candidate_name: string;
  current_title?: string;
  total_experience_months: number;
  application_id?: string;
  application_status?: PipelineStageType;
  overall_score?: number;
  required_skills_score?: number;
  experience_score?: number;
  preferred_skills_score?: number;
  project_relevance_score?: number;
  other_criteria_score?: number;
  matched_requirements_count: number;
  partial_requirements_count: number;
  missing_requirements_count: number;
  needs_verification_count: number;
  strengths: string[];
  skill_gaps: string[];
  verification_items: string[];
  is_stale: boolean;
  scoring_version?: string;
  evaluated_at?: string;
}

export interface CandidateComparisonResponse {
  job_id: string;
  job_title: string;
  candidates: CandidateComparisonItem[];
  criteria_matrix: Array<{
    requirement_id: string;
    requirement_text: string;
    requirement_type: string;
    is_mandatory: boolean;
    importance_weight: number;
    evaluations: Record<
      string,
      {
        evidence_status: string;
        candidate_evidence?: string;
        semantic_similarity?: number;
        verification_status: string;
      }
    >;
  }>;
}

export interface PipelineDashboardStats {
  total_active_applications: number;
  stage_counts: Record<PipelineStageType, number>;
  recent_activities: Array<{
    id: string;
    action: string;
    resource_id?: string;
    details?: string;
    user_name: string;
    created_at: string;
  }>;
  job_summaries: Array<{
    job_id: string;
    job_title: string;
    job_status: string;
    active_applications_count: number;
  }>;
}

// -------------------------------------------------------------
// Phase 6: Interview & Scheduling Workspace Types
// -------------------------------------------------------------

export type InterviewMode = "ONLINE" | "IN_PERSON" | "PHONE";

export type InterviewStatus =
  | "DRAFT"
  | "SCHEDULED"
  | "CONFIRMED"
  | "COMPLETED"
  | "CANCELLED"
  | "RESCHEDULED";

export type InterviewRoundType =
  | "INITIAL_SCREENING"
  | "TECHNICAL"
  | "SYSTEM_DESIGN"
  | "HIRING_MANAGER"
  | "HR_BEHAVIORAL"
  | "CULTURE_FIT"
  | "FINAL_ROUND"
  | "OTHER";

export type ParticipantRole = "INTERVIEWER" | "RECRUITER" | "OBSERVER";

export type AttendanceStatus =
  | "INVITED"
  | "ACCEPTED"
  | "DECLINED"
  | "TENTATIVE"
  | "ATTENDED"
  | "ABSENT";

export type FeedbackRecommendation =
  | "STRONG_YES"
  | "YES"
  | "MAYBE"
  | "NO"
  | "STRONG_NO";

export interface InterviewParticipant {
  id: string;
  interview_id: string;
  user_id?: string | null;
  participant_name: string;
  participant_email: string;
  participant_role: ParticipantRole;
  attendance_status: AttendanceStatus;
  created_at: string;
}

export interface InterviewFeedback {
  id: string;
  interview_id: string;
  reviewer_id: string;
  reviewer_name?: string | null;
  overall_rating: number;
  recommendation: FeedbackRecommendation;
  technical_assessment?: number | null;
  communication_assessment?: number | null;
  problem_solving_assessment?: number | null;
  role_specific_assessment?: number | null;
  strengths?: string | null;
  concerns?: string | null;
  detailed_feedback?: string | null;
  submitted_at: string;
  created_at: string;
  updated_at?: string | null;
}

export interface InterviewHistory {
  id: string;
  interview_id: string;
  agency_id: string;
  actor_id?: string | null;
  actor_name?: string | null;
  action: string;
  previous_value?: string | null;
  new_value?: string | null;
  reason?: string | null;
  created_at: string;
}

export interface Interview {
  id: string;
  agency_id: string;
  application_id: string;
  round_name: string;
  round_type: InterviewRoundType;
  title: string;
  description?: string | null;
  interview_mode: InterviewMode;
  scheduled_start: string;
  scheduled_end: string;
  timezone: string;
  location?: string | null;
  meeting_url?: string | null;
  status: InterviewStatus;
  created_by?: string | null;
  created_at: string;
  updated_at?: string | null;
  cancelled_at?: string | null;
  cancellation_reason?: string | null;
  version: number;
  candidate_name?: string | null;
  candidate_id?: string | null;
  candidate_email?: string | null;
  job_title?: string | null;
  job_id?: string | null;
  participants: InterviewParticipant[];
  feedbacks?: InterviewFeedback[];
  feedback_count: number;
  participant_count: number;
}

export interface InterviewListResponse {
  items: Interview[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface InterviewStatusCounts {
  total: number;
  upcoming: number;
  today: number;
  completed: number;
  cancelled: number;
}

// ======================================================================
// Phase 8: Recruitment Intelligence & Analytics Types
// ======================================================================

export type PeriodPreset =
  | "TODAY"
  | "LAST_7_DAYS"
  | "LAST_30_DAYS"
  | "LAST_90_DAYS"
  | "THIS_MONTH"
  | "PREVIOUS_MONTH"
  | "THIS_QUARTER"
  | "CUSTOM";

export type ExpenseCategory =
  | "JOB_ADVERTISING"
  | "RECRUITMENT_PLATFORMS"
  | "AGENCY_FEES"
  | "ASSESSMENT_COSTS"
  | "INTERVIEW_EXPENSES"
  | "OTHER";

export interface ReportingPeriodInfo {
  preset: PeriodPreset;
  start_date: string;
  end_date: string;
  start_date_ist: string;
  end_date_ist: string;
  timezone: string;
}

export interface AnalyticsOverviewResponse {
  reporting_period: ReportingPeriodInfo;
  total_active_jobs: number;
  total_candidates: number;
  total_applications: number;
  applications_in_period: number;
  interviews_scheduled: number;
  interviews_completed: number;
  active_applications: number;
  successful_hires: number;
  metric_tooltips: Record<string, string>;
}

export interface FunnelStageItem {
  stage: string;
  label: string;
  current_count: number;
  entered_count: number;
  drop_off_count: number;
  conversion_from_previous_percent?: number | null;
  conversion_from_applied_percent?: number | null;
}

export interface RecruitmentFunnelResponse {
  reporting_period: ReportingPeriodInfo;
  stages: FunnelStageItem[];
  overall_application_to_hire_rate: number;
  total_applications_evaluated: number;
  funnel_methodology: string;
}

export interface TimeToHireStats {
  average_days?: number | null;
  median_days?: number | null;
  min_days?: number | null;
  max_days?: number | null;
  hired_sample_size: number;
  calculation_notes: string;
}

export interface InterviewConversionStats {
  total_applications_considered: number;
  total_interviews_conducted: number;
  interviews_per_application: number;
  applications_with_interviews: number;
  interview_to_hire_count: number;
  interview_to_hire_rate: number;
  cancelled_interviews_excluded: number;
}

export interface HiringPerformanceResponse {
  reporting_period: ReportingPeriodInfo;
  time_to_hire: TimeToHireStats;
  interview_conversion: InterviewConversionStats;
}

export interface JobPerformanceItem {
  job_id: string;
  job_title: string;
  department?: string | null;
  status: string;
  applications_count: number;
  interviews_count: number;
  hires_count: number;
  conversion_rate: number;
  created_at: string;
}

export interface JobAnalyticsResponse {
  reporting_period: ReportingPeriodInfo;
  total_jobs_evaluated: number;
  jobs_with_zero_applications: number;
  jobs: JobPerformanceItem[];
}

export interface RecruiterPerformanceItem {
  recruiter_id: string;
  recruiter_name: string;
  recruiter_email: string;
  role: string;
  applications_handled: number;
  active_workload: number;
  interviews_coordinated: number;
  attributable_hires: number;
  avg_time_to_hire_days?: number | null;
}

export interface RecruiterAnalyticsResponse {
  reporting_period: ReportingPeriodInfo;
  recruiters: RecruiterPerformanceItem[];
  attribution_rule: string;
}

export interface SourcePerformanceItem {
  source: string;
  candidates_count: number;
  applications_count: number;
  interviews_count: number;
  hires_count: number;
  conversion_rate: number;
}

export interface SourceAnalyticsResponse {
  reporting_period: ReportingPeriodInfo;
  sources: SourcePerformanceItem[];
  unattributed_candidates_count: number;
  unattributed_applications_count: number;
  attribution_notes: string;
}

export interface ExpenseCategoryItem {
  category: string;
  amount: number;
  currency: string;
  percentage: number;
}

export interface CostAnalyticsResponse {
  reporting_period: ReportingPeriodInfo;
  has_cost_data: boolean;
  status_message: string;
  cost_per_hire_by_currency: Record<string, number | null>;
  total_expenses_by_currency: Record<string, number>;
  expenses_by_category: ExpenseCategoryItem[];
  total_attributable_hires: number;
  currency_notes: string;
}

export interface RecruitmentExpense {
  id: string;
  agency_id: string;
  job_id?: string | null;
  job_title?: string | null;
  title: string;
  amount: number;
  currency: string;
  category: ExpenseCategory;
  expense_date: string;
  description?: string | null;
  created_by?: string | null;
  creator_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ExpenseListResponse {
  items: RecruitmentExpense[];
  total: number;
  skip: number;
  limit: number;
}

export interface TrendPoint {
  date: string;
  applications: number;
  interviews_scheduled: number;
  interviews_completed: number;
  hires: number;
}

export interface AnalyticsTrendsResponse {
  reporting_period: ReportingPeriodInfo;
  data_points: TrendPoint[];
}

export interface AIInsightsResponse {
  generated_at: string;
  summary: string;
  key_findings: string[];
  bottlenecks: string[];
  operational_recommendations: string[];
  provider_used: string;
  is_ai_available: boolean;
  grounding_disclaimer: string;
}

// -------------------------------------------------------------
// Phase 9: Calendar & External Integrations
// -------------------------------------------------------------
export type CalendarProviderType = "GOOGLE" | "MICROSOFT" | "MOCK";
export type CalendarSyncStatus = "SYNCED" | "PENDING" | "FAILED" | "CANCELLED";
export type MeetingProviderType = "GOOGLE_MEET" | "MS_TEAMS" | "NONE";

export interface CalendarConnection {
  id: string;
  agency_id: string;
  user_id: string;
  provider: CalendarProviderType;
  provider_account_id?: string | null;
  provider_account_email?: string | null;
  selected_calendar_id: string;
  selected_calendar_name: string;
  is_active: boolean;
  last_synced_at?: string | null;
  last_error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CalendarItem {
  id: string;
  name: string;
  primary: boolean;
  read_only: boolean;
}

export interface CalendarSyncLog {
  id: string;
  agency_id: string;
  connection_id?: string | null;
  interview_id?: string | null;
  direction: "OUTBOUND" | "INBOUND";
  operation: "CREATE" | "UPDATE" | "CANCEL" | "RESYNC";
  status: string;
  details?: string | null;
  error_message?: string | null;
  created_at: string;
}

export interface CalendarEventMapping {
  id: string;
  interview_id: string;
  provider: CalendarProviderType;
  meeting_link?: string | null;
  meeting_provider: MeetingProviderType;
  sync_status: CalendarSyncStatus;
  last_synced_at?: string | null;
  last_error?: string | null;
}

// --- Phase 10: AI Recruitment Copilot Types ---

export type CopilotActionType =
  | "CHAT"
  | "JOB_DESCRIPTION_GENERATE"
  | "JOB_DESCRIPTION_IMPROVE"
  | "JOB_DESCRIPTION_ANALYZE"
  | "CANDIDATE_COMPARE"
  | "INTERVIEW_PREPARE"
  | "ANALYTICS_EXPLAIN";

export type CopilotMessageRole = "USER" | "ASSISTANT" | "SYSTEM";

export type CopilotContextType =
  | "AGENCY_OVERVIEW"
  | "JOB"
  | "CANDIDATE"
  | "APPLICATION"
  | "INTERVIEW"
  | "ANALYTICS";

export interface CopilotSourceRef {
  type: string;
  id?: string | null;
  label: string;
  details?: string | null;
}

export interface CopilotMessage {
  id: string;
  conversation_id: string;
  role: CopilotMessageRole;
  content: string;
  sources?: CopilotSourceRef[] | null;
  context_snapshot?: string | null;
  model_used?: string | null;
  created_at: string;
}

export interface CopilotConversation {
  id: string;
  agency_id: string;
  user_id: string;
  title: string;
  context_type: CopilotContextType;
  context_id?: string | null;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
  message_count: number;
  messages?: CopilotMessage[];
}

export interface JobDescriptionGenerateRequest {
  title: string;
  department?: string | null;
  seniority_level?: string;
  required_skills: string[];
  preferred_skills?: string[];
  experience_min: number;
  experience_max?: number | null;
  location?: string | null;
  work_mode: string;
  employment_type: string;
  responsibilities?: string[];
  additional_context?: string | null;
}

export interface JobDescriptionGenerateResponse {
  title: string;
  department?: string | null;
  overview: string;
  responsibilities: string[];
  required_qualifications: string[];
  preferred_qualifications: string[];
  skills: string[];
  experience_expectations: string;
  work_arrangement: string;
  full_text: string;
  is_draft: boolean;
  disclaimer: string;
  provider_used: string;
}

export interface JobDescriptionImproveRequest {
  title?: string | null;
  existing_description: string;
  focus_areas?: string[];
}

export interface JobDescriptionImproveResponse {
  improved_description: string;
  changes_made: string[];
  bias_findings: string[];
  unrealistic_requirements_removed: string[];
  is_draft: boolean;
  provider_used: string;
}

export interface JobDescriptionQualityDimension {
  dimension: string;
  score: number;
  status: "EXCELLENT" | "GOOD" | "NEEDS_IMPROVEMENT";
  findings: string[];
  suggestions: string[];
}

export interface JobDescriptionQualityReport {
  job_id?: string | null;
  overall_score: number;
  dimensions: JobDescriptionQualityDimension[];
  detected_biases: string[];
  recommendations: string[];
}

export interface CopilotCandidateComparisonItem {
  candidate_id: string;
  candidate_name: string;
  current_title?: string | null;
  total_experience_months: number;
  deterministic_match_score?: number | null;
  demonstrated_skills: string[];
  missing_or_partial_skills: string[];
  verified_education?: string | null;
  key_strengths: string[];
  areas_for_verification: string[];
  interview_readiness: string;
}

export interface CopilotCandidateComparisonResponse {
  job_id: string;
  job_title: string;
  candidate_count: number;
  candidates: CopilotCandidateComparisonItem[];
  comparative_summary: string;
  methodology_disclaimer: string;
}

export interface InterviewPrepQuestion {
  category: "TECHNICAL" | "BEHAVIORAL" | "SITUATIONAL" | "ROLE_SPECIFIC";
  question: string;
  target_skill_or_competency: string;
  what_to_look_for: string;
}

export interface InterviewPrepResponse {
  interview_id: string;
  candidate_name: string;
  job_title: string;
  round_name: string;
  round_type: string;
  scheduled_time: string;
  candidate_experience_summary: string;
  skills_to_explore: string[];
  questions: InterviewPrepQuestion[];
  areas_requiring_clarification: string[];
  suggested_structure: string[];
  evaluation_guidance: string[];
  disclaimer: string;
}

export interface AnalyticsExplainResponse {
  reporting_period: Record<string, any>;
  summary: string;
  funnel_insights: string[];
  time_to_hire_insights: string[];
  sourcing_insights: string[];
  operational_recommendations: string[];
  verified_metrics_snapshot: Record<string, any>;
  provider_used: string;
}

// -------------------------------------------------------------
// Phase 11: Workflow Automation & Orchestration Types
// -------------------------------------------------------------

export type WorkflowTriggerType =
  | "CANDIDATE_CREATED"
  | "RESUME_PROCESSED"
  | "CANDIDATE_MATCHED"
  | "APPLICATION_SUBMITTED"
  | "APPLICATION_STAGE_CHANGED"
  | "INTERVIEW_SCHEDULED"
  | "INTERVIEW_RESCHEDULED"
  | "INTERVIEW_COMPLETED"
  | "FEEDBACK_SUBMITTED"
  | "CANDIDATE_INACTIVE";

export type WorkflowActionType =
  | "SEND_CANDIDATE_COMMUNICATION"
  | "NOTIFY_RECRUITERS"
  | "GENERATE_INTERVIEW_PREP"
  | "CREATE_RECRUITER_TASK"
  | "TRIGGER_CALENDAR_SYNC"
  | "GENERATE_ANALYTICS_EVENT"
  | "REQUEST_HUMAN_APPROVAL";

export type WorkflowExecutionStatus =
  | "PENDING"
  | "RUNNING"
  | "WAITING_FOR_APPROVAL"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED"
  | "EXPIRED";

export type WorkflowStepStatus =
  | "PENDING"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "SKIPPED"
  | "WAITING_APPROVAL";

export type WorkflowApprovalStatus = "PENDING" | "APPROVED" | "REJECTED" | "EXPIRED";

export type RecruiterTaskStatus = "PENDING" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type RecruiterTaskPriority = "LOW" | "MEDIUM" | "HIGH" | "URGENT";

export type ConditionOperator =
  | "EQUALS"
  | "NOT_EQUALS"
  | "GREATER_THAN"
  | "GREATER_THAN_OR_EQUAL"
  | "LESS_THAN"
  | "LESS_THAN_OR_EQUAL"
  | "CONTAINS"
  | "NOT_CONTAINS"
  | "IN"
  | "NOT_IN"
  | "EXISTS"
  | "NOT_EXISTS";

export interface ConditionLeaf {
  field: string;
  operator: ConditionOperator;
  value?: any;
}

export interface ConditionGroup {
  logical_operator: "AND" | "OR";
  conditions: Array<ConditionLeaf | ConditionGroup>;
}

export interface WorkflowActionStepConfig {
  action_type: WorkflowActionType;
  step_index?: number;
  description?: string;
  requires_approval?: boolean;
  approval_role?: string;
  email_subject?: string;
  email_body_template?: string;
  notification_title?: string;
  notification_message?: string;
  task_title?: string;
  task_description?: string;
  task_priority?: RecruiterTaskPriority;
  task_due_days?: number;
  calendar_operation?: string;
  event_name?: string;
  delay_minutes?: number;
}

export interface WorkflowDefinition {
  trigger_config?: Record<string, any>;
  conditions?: ConditionGroup | null;
  actions: WorkflowActionStepConfig[];
}

export interface WorkflowVersionRead {
  id: string;
  workflow_id: string;
  version_number: number;
  definition: WorkflowDefinition;
  change_summary?: string | null;
  created_by_user_id?: string | null;
  created_at: string;
}

export interface RecruitmentWorkflow {
  id: string;
  agency_id: string;
  name: string;
  description?: string | null;
  trigger_type: WorkflowTriggerType;
  is_active: boolean;
  created_by_user_id?: string | null;
  created_at: string;
  updated_at: string;
  current_version?: WorkflowVersionRead | null;
  execution_count?: number;
}

export interface WorkflowListResponse {
  items: RecruitmentWorkflow[];
  total: number;
}

export interface WorkflowExecutionStepRead {
  id: string;
  execution_id: string;
  step_index: number;
  action_type: WorkflowActionType;
  status: WorkflowStepStatus;
  action_config?: Record<string, any>;
  output_payload?: Record<string, any> | null;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface WorkflowExecutionRead {
  id: string;
  agency_id: string;
  workflow_id: string;
  workflow_name?: string | null;
  workflow_version_id?: string | null;
  trigger_event: WorkflowTriggerType;
  trigger_entity_type: string;
  trigger_entity_id?: string | null;
  status: WorkflowExecutionStatus;
  idempotency_key: string;
  retry_count: number;
  error_message?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  steps: WorkflowExecutionStepRead[];
}

export interface WorkflowExecutionListResponse {
  items: WorkflowExecutionRead[];
  total: number;
}

export interface WorkflowApprovalRead {
  id: string;
  agency_id: string;
  execution_id: string;
  step_id?: string | null;
  title: string;
  description?: string | null;
  status: WorkflowApprovalStatus;
  requested_action: WorkflowActionType;
  action_payload?: Record<string, any> | null;
  assigned_role: string;
  assigned_user_id?: string | null;
  approved_by_user_id?: string | null;
  rejection_reason?: string | null;
  expires_at?: string | null;
  decided_at?: string | null;
  created_at: string;
  workflow_name?: string | null;
}

export interface WorkflowApprovalListResponse {
  items: WorkflowApprovalRead[];
  total: number;
}

export interface RecruiterTaskRead {
  id: string;
  agency_id: string;
  title: string;
  description?: string | null;
  priority: RecruiterTaskPriority;
  status: RecruiterTaskStatus;
  assigned_to_user_id?: string | null;
  assigned_to_name?: string | null;
  created_by_user_id?: string | null;
  candidate_id?: string | null;
  candidate_name?: string | null;
  job_id?: string | null;
  job_title?: string | null;
  application_id?: string | null;
  interview_id?: string | null;
  due_date?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecruiterTaskListResponse {
  items: RecruiterTaskRead[];
  total: number;
}

export interface WorkflowMonitoringStats {
  total_workflows: number;
  active_workflows: number;
  total_executions: number;
  successful_executions: number;
  failed_executions: number;
  pending_approvals: number;
  average_duration_ms: number;
  retry_count: number;
  success_rate_percent: number;
  recent_executions: WorkflowExecutionRead[];
}

// ======================================================================
// Phase 12: Predictive Recruitment Intelligence & Workforce Planning Types
// ======================================================================

export type ModelType =
  | "TIME_TO_HIRE"
  | "HIRING_DEMAND"
  | "STAGE_DURATION"
  | "CANDIDATE_DROP_OFF";

export type PredictionAlgorithm =
  | "RIDGE_REGRESSION"
  | "RANDOM_FOREST"
  | "EXPONENTIAL_SMOOTHING"
  | "BASELINE_EMPIRICAL";

export type ForecastType =
  | "TIME_TO_HIRE"
  | "DEMAND_30D"
  | "DEMAND_60D"
  | "DEMAND_90D"
  | "APPLICATION_VOLUME";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW" | "PRELIMINARY";

export type RecruitmentRiskType =
  | "PIPELINE_DEFICIT"
  | "STAGE_STAGNATION"
  | "DROP_OFF_VULNERABILITY"
  | "SCHEDULING_BOTTLENECK"
  | "EXPENSE_OVERRUN";

export type RiskSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type RiskStatus = "OPEN" | "ACKNOWLEDGED" | "MITIGATED" | "DISMISSED";

export type RecruiterUtilizationStatus = "OPTIMAL" | "OVERLOADED" | "UNDERUTILIZED";

export interface ModelVersionRead {
  id: string;
  agency_id: string;
  model_type: ModelType;
  algorithm: PredictionAlgorithm;
  version_tag: string;
  training_sample_size: number;
  evaluation_metrics?: Record<string, any> | null;
  hyperparameters?: Record<string, any> | null;
  feature_names?: string[] | null;
  is_active: boolean;
  trained_at: string;
  created_at: string;
}

export interface ForecastRead {
  id: string;
  agency_id: string;
  job_id?: string | null;
  job_title?: string | null;
  department?: string | null;
  forecast_type: ForecastType;
  predicted_value: number;
  confidence_lower: number;
  confidence_upper: number;
  confidence_level: ConfidenceLevel;
  is_baseline_fallback: boolean;
  explanation?: string | null;
  factors?: string[] | null;
  model_version_id?: string | null;
  horizon_days: number;
  forecast_date: string;
  created_at: string;
}

export interface RecruitmentRiskRead {
  id: string;
  agency_id: string;
  risk_type: RecruitmentRiskType;
  severity: RiskSeverity;
  status: RiskStatus;
  title: string;
  description: string;
  job_id?: string | null;
  job_title?: string | null;
  candidate_id?: string | null;
  candidate_name?: string | null;
  application_id?: string | null;
  recruiter_id?: string | null;
  recruiter_name?: string | null;
  evidence_payload?: Record<string, any> | null;
  recommended_action: string;
  confidence_score: number;
  acknowledged_by_user_id?: string | null;
  resolution_notes?: string | null;
  detected_at: string;
  resolved_at?: string | null;
  created_at: string;
}

export interface CapacitySnapshotRead {
  id: string;
  agency_id: string;
  recruiter_id: string;
  recruiter_name?: string | null;
  recruiter_email?: string | null;
  active_applications_count: number;
  upcoming_interviews_count: number;
  open_requisitions_count: number;
  workload_index: number;
  utilization_status: RecruiterUtilizationStatus;
  recommendations?: string[] | null;
  snapshot_date: string;
  created_at: string;
}

export interface PredictiveOverviewResponse {
  active_jobs_count: number;
  active_applications_count: number;
  average_predicted_time_to_hire_days: number;
  demand_next_30d_hires: number;
  open_risks_count: number;
  critical_risks_count: number;
  top_risks: RecruitmentRiskRead[];
  capacity_summary: {
    total_tracked_recruiters: number;
    overloaded_count: number;
    underutilized_count: number;
    workload_balanced: boolean;
  };
  model_governance: {
    version_tag: string;
    algorithm: string;
    training_samples: number;
    trained_at: string;
  };
  ai_strategic_brief?: string | null;
  last_refreshed_at: string;
  timezone: string;
}

export interface DepartmentTimeToHire {
  department: string;
  predicted_days: number;
  confidence_lower: number;
  confidence_upper: number;
  sample_size: number;
  is_fallback: boolean;
}

export interface TimeToHireForecastResponse {
  overall_agency_predicted_days: number;
  historical_average_days: number;
  sample_size: number;
  is_baseline_fallback: boolean;
  confidence_interval: {
    lower_days: number;
    upper_days: number;
  };
  by_department: DepartmentTimeToHire[];
  by_job: ForecastRead[];
  explanation?: string | null;
}

export interface DepartmentDemand {
  department: string;
  demand_30d: number;
  demand_60d: number;
  demand_90d: number;
  expected_applications_30d: number;
}

export interface HiringDemandForecastResponse {
  demand_30d: number;
  demand_60d: number;
  demand_90d: number;
  expected_application_volume_30d: number;
  historical_trend_direction: string;
  department_breakdown: DepartmentDemand[];
  confidence_level: ConfidenceLevel;
  historical_vs_predicted_data: Array<{
    period: string;
    actual_jobs?: number | null;
    predicted_jobs?: number | null;
  }>;
  explanation?: string | null;
}

export interface StageCycleTime {
  stage: string;
  stage_label: string;
  median_duration_days: number;
  average_duration_days: number;
  p90_duration_days: number;
  current_active_candidates: number;
  is_bottleneck: boolean;
  benchmark_days: number;
}

export interface BottleneckAnalysisResponse {
  stagnant_stages: StageCycleTime[];
  interview_scheduling_delays: Array<{
    department: string;
    average_days_to_schedule: number;
    benchmark_days: number;
    pending_interviews_count: number;
    status: string;
  }>;
  recommendations: string[];
  ai_explanation?: string | null;
}

export interface RecruiterCapacityResponse {
  recruiters: CapacitySnapshotRead[];
  agency_average_workload: number;
  imbalance_detected: boolean;
  redistribution_recommendations: string[];
}

// =============================================================================
// Phase 13: Enterprise Security, Compliance & Governance Types
// =============================================================================

export type AuditEventCategory =
  | "AUTH"
  | "ACCESS_CONTROL"
  | "DATA_ACCESS"
  | "DATA_EXPORT"
  | "ADMIN_ACTION"
  | "PRIVACY_OP"
  | "RETENTION_OP"
  | "AI_GOVERNANCE";

export type AuditSeverity = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type ConsentType =
  | "DATA_PROCESSING"
  | "COMMUNICATION"
  | "AI_ASSESSMENT"
  | "THIRD_PARTY_SHARING";

export type PrivacyRequestType =
  | "DATA_ACCESS"
  | "DATA_RECTIFICATION"
  | "DATA_DELETION"
  | "RESTRICT_PROCESSING";

export type PrivacyRequestStatus =
  | "PENDING"
  | "UNDER_REVIEW"
  | "COMPLETED"
  | "REJECTED";

export type RetentionCategory =
  | "CANDIDATE_DATA"
  | "RESUME_DOCUMENTS"
  | "INTERVIEW_RECORDS"
  | "NOTIFICATIONS"
  | "AUDIT_LOGS"
  | "AI_CONVERSATIONS";

export type RetentionAction = "DELETE" | "ANONYMIZE" | "ARCHIVE";

export type RetentionExecutionType = "DRY_RUN" | "MANUAL_LIVE" | "SCHEDULED_SWEEP";

export type RetentionStatus = "SUCCESS" | "FAILED" | "PARTIAL";

export interface UserSessionRead {
  id: string;
  user_id: string;
  user_email: string;
  user_role: string;
  device_info?: string | null;
  ip_address?: string | null;
  is_active: boolean;
  last_activity_at: string;
  expires_at: string;
  created_at: string;
  revoked_at?: string | null;
}

export interface SecurityAuditEventRead {
  id: string;
  agency_id: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  event_category: AuditEventCategory;
  severity: AuditSeverity;
  action: string;
  resource_type?: string | null;
  resource_id?: string | null;
  details?: Record<string, any> | null;
  ip_address?: string | null;
  user_agent?: string | null;
  created_at: string;
}

export interface SecurityAuditEventListResponse {
  total: number;
  skip: number;
  limit: number;
  items: SecurityAuditEventRead[];
}

export interface CandidateConsentRecordRead {
  id: string;
  agency_id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_email?: string | null;
  consent_type: ConsentType;
  is_granted: boolean;
  policy_version: string;
  purpose: string;
  channel: string;
  granted_at: string;
  withdrawn_at?: string | null;
  metadata?: Record<string, any> | null;
}

export interface CandidatePrivacyRequestRead {
  id: string;
  agency_id: string;
  candidate_id?: string | null;
  candidate_name?: string | null;
  candidate_email?: string | null;
  request_type: PrivacyRequestType;
  status: PrivacyRequestStatus;
  requested_by_email: string;
  request_details?: string | null;
  has_legal_hold: boolean;
  legal_hold_reason?: string | null;
  resolution_notes?: string | null;
  handled_by_user_id?: string | null;
  handler_name?: string | null;
  created_at: string;
  resolved_at?: string | null;
}

export interface AIGovernancePolicyRead {
  id: string;
  agency_id: string;
  allowed_providers: string[];
  max_tokens_per_request: number;
  monthly_token_budget: number;
  require_pii_masking: boolean;
  safety_filter_enabled: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface AIUsageMetricsResponse {
  period_start: string;
  period_end: string;
  total_tokens: number;
  monthly_budget: number;
  budget_utilization_pct: number;
  total_requests: number;
  fallback_count: number;
  safety_block_count: number;
  provider_breakdown: Record<string, { requests: number; tokens: number; estimated_cost_usd: number }>;
}

export interface DataRetentionPolicyRead {
  id: string;
  agency_id: string;
  category: RetentionCategory;
  retention_period_days: number;
  action: RetentionAction;
  is_active: boolean;
  created_at: string;
  updated_at?: string | null;
}

export interface RetentionDryRunPreview {
  category: RetentionCategory;
  retention_period_days: number;
  action: RetentionAction;
  cutoff_date: string;
  eligible_count: number;
  exempt_legal_hold_count: number;
  preview_notice: string;
}

export interface RetentionExecutionLogRead {
  id: string;
  agency_id: string;
  policy_id?: string | null;
  category: RetentionCategory;
  execution_type: RetentionExecutionType;
  action_taken: RetentionAction;
  records_evaluated: number;
  records_affected: number;
  records_exempted_legal_hold: number;
  status: RetentionStatus;
  details?: Record<string, any> | null;
  executed_by_user_id?: string | null;
  executor_email?: string | null;
  created_at: string;
}

export interface GovernanceOverviewResponse {
  active_sessions_count: number;
  security_events_last_24h: number;
  critical_events_count: number;
  pending_privacy_requests: number;
  active_legal_holds: number;
  ai_monthly_token_consumption: number;
  ai_budget_utilization_pct: number;
  active_retention_policies_count: number;
  last_retention_run_at?: string | null;
}

// =============================================================================
// Phase 14: Enterprise SaaS Monetization, Subscription & Billing Types
// =============================================================================

export type SubscriptionTier =
  | "FREE"
  | "STARTER"
  | "PROFESSIONAL"
  | "BUSINESS"
  | "ENTERPRISE";

export type SubscriptionStatus =
  | "ACTIVE"
  | "TRIALING"
  | "PAST_DUE"
  | "CANCELED"
  | "EXPIRED"
  | "INCOMPLETE";

export type BillingInterval = "MONTHLY" | "ANNUAL";

export type PaymentGateway = "RAZORPAY" | "STRIPE" | "MOCK";

export type InvoiceStatus =
  | "DRAFT"
  | "ISSUED"
  | "PAID"
  | "VOID"
  | "UNCOLLECTIBLE";

export type QuotaResourceType =
  | "ACTIVE_JOBS"
  | "RECRUITERS"
  | "CANDIDATES_MONTHLY"
  | "RESUME_STORAGE_MB"
  | "AI_TOKENS_MONTHLY"
  | "INTERVIEWS_MONTHLY"
  | "WORKFLOW_RUNS_MONTHLY";

export type BillingCurrency = "INR" | "USD";

export interface SubscriptionPlanRead {
  id: string;
  name: string;
  slug: string;
  tier: SubscriptionTier;
  billing_interval: BillingInterval;
  price_inr: number;
  price_usd: number;
  max_active_jobs: number;
  max_recruiters: number;
  max_candidates_monthly: number;
  max_resume_storage_mb: number;
  max_ai_tokens_monthly: number;
  max_interviews_monthly: number;
  max_workflow_runs_monthly: number;
  features: Record<string, any>;
  is_active: boolean;
}

export interface AgencySubscriptionRead {
  id: string;
  agency_id: string;
  plan_id: string;
  plan_name: string;
  plan_slug: string;
  tier: SubscriptionTier;
  status: SubscriptionStatus;
  billing_interval: BillingInterval;
  currency: BillingCurrency;
  current_period_start: string;
  current_period_end: string;
  trial_end?: string | null;
  cancel_at_period_end: boolean;
  canceled_at?: string | null;
  payment_gateway: PaymentGateway;
  is_in_grace_period: boolean;
}

export interface UsageMeterRead {
  resource_type: QuotaResourceType;
  current_usage: number;
  soft_limit: number;
  hard_limit: number;
  is_unlimited: boolean;
  utilization_pct: number;
  is_soft_limit_exceeded: boolean;
  is_hard_limit_exceeded: boolean;
}

export interface UsageOverviewResponse {
  agency_id: string;
  plan_name: string;
  tier: SubscriptionTier;
  period_start: string;
  period_end: string;
  meters: Record<string, UsageMeterRead>;
  has_warnings: boolean;
  has_exhausted_quotas: boolean;
}

export interface CheckoutSessionResponse {
  session_id: string;
  order_id?: string | null;
  gateway: PaymentGateway;
  amount: number;
  currency: BillingCurrency;
  checkout_url?: string | null;
  publishable_key?: string | null;
  plan_name: string;
  plan_slug: string;
  billing_interval: BillingInterval;
}

export interface PaymentVerificationResponse {
  success: boolean;
  subscription_status: SubscriptionStatus;
  transaction_id: string;
  message: string;
  invoice_number?: string | null;
}

export interface InvoiceLineItemRead {
  id: string;
  description: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface BillingInvoiceRead {
  id: string;
  invoice_number: string;
  status: InvoiceStatus;
  currency: BillingCurrency;
  subtotal: number;
  tax_rate_pct: number;
  tax_amount: number;
  total_amount: number;
  customer_name: string;
  customer_email: string;
  customer_gstin?: string | null;
  is_domestic_india: boolean;
  paid_at?: string | null;
  due_date?: string | null;
  download_url: string;
  created_at: string;
}

export interface BillingInvoiceDetailRead extends BillingInvoiceRead {
  customer_address?: string | null;
  line_items: InvoiceLineItemRead[];
}

export interface AgencyBillingProfileRead {
  id: string;
  agency_id: string;
  legal_name: string;
  billing_email: string;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state_province?: string | null;
  postal_code?: string | null;
  country: string;
  gstin?: string | null;
  currency: BillingCurrency;
  is_gstin_valid: boolean;
  updated_at?: string | null;
}

export type SubscriptionPlan = SubscriptionPlanRead;
export type AgencySubscription = AgencySubscriptionRead;
export type AgencyUsageOverview = UsageOverviewResponse;
export type BillingInvoice = BillingInvoiceRead;
export type AgencyBillingProfile = AgencyBillingProfileRead;
export type CheckoutInitiationResponse = CheckoutSessionResponse;

export interface PaymentTransaction {
  id: string;
  payment_gateway: string;
  gateway_order_id?: string | null;
  gateway_transaction_id?: string | null;
  amount: number;
  currency: string;
  status: string;
  created_at: string;
}


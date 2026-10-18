"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  ShieldCheck,
  ShieldAlert,
  RefreshCw,
  ExternalLink,
  BookOpen,
  User,
  Briefcase,
  FileText,
  MessageSquare,
  Flame,
  Award,
  Kanban,
  UserPlus,
  X,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Job,
  JobMatchResultDetailResponse,
  MatchEvidence,
  JobMatchResult,
  Application,
  ApplicationListResponse,
  PipelineStageType,
} from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function CandidateMatchDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;
  const candidateId = params?.candidateId as string;

  const [job, setJob] = useState<Job | null>(null);
  const [detail, setDetail] = useState<JobMatchResultDetailResponse | null>(null);
  const [existingApp, setExistingApp] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Application creation modal state
  const [showAppModal, setShowAppModal] = useState(false);
  const [modalStage, setModalStage] = useState<PipelineStageType>("APPLIED");
  const [modalNote, setModalNote] = useState("");
  const [submittingApp, setSubmittingApp] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [jobRes, detailRes, appsRes] = await Promise.all([
        apiClient<Job>(`/jobs/${jobId}`),
        apiClient<JobMatchResultDetailResponse>(`/jobs/${jobId}/matches/${candidateId}`),
        apiClient<ApplicationListResponse>(`/jobs/${jobId}/applications?limit=100`).catch(() => ({
          items: [],
          total: 0,
          stage_counts: {} as any,
        })),
      ]);
      setJob(jobRes);
      setDetail(detailRes);

      const foundApp = appsRes.items.find((a) => a.candidate_id === candidateId);
      setExistingApp(foundApp || null);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate match detail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId && candidateId) {
      fetchData();
    }
  }, [jobId, candidateId]);

  const handleRefreshExplanation = async () => {
    if (!detail?.result?.id) return;
    setActionLoading("explanation");
    setActionMessage(null);
    setError(null);
    try {
      const updatedResult: JobMatchResult = await apiClient<JobMatchResult>(
        `/matching/results/${detail.result.id}/refresh-explanation`,
        { method: "POST" }
      );
      setDetail((prev) => (prev ? { ...prev, result: updatedResult } : null));
      setActionMessage("AI match explanation successfully refreshed from latest evidence.");
    } catch (err: any) {
      setError(err.message || "Failed to refresh explanation.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRecalculate = async () => {
    if (!detail?.result?.id) return;
    setActionLoading("recalculate");
    setActionMessage(null);
    setError(null);
    try {
      const updatedResult: JobMatchResult = await apiClient<JobMatchResult>(
        `/matching/results/${detail.result.id}/recalculate`,
        { method: "POST", body: JSON.stringify({ scoring_version: "v1.0" }) }
      );
      setDetail((prev) => (prev ? { ...prev, result: updatedResult } : null));
      setActionMessage("Match score and dimension breakdown successfully recalculated.");
    } catch (err: any) {
      setError(err.message || "Failed to recalculate score.");
    } finally {
      setActionLoading(null);
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingApp(true);
    setError(null);
    try {
      const newApp = await apiClient<Application>(`/jobs/${jobId}/applications`, {
        method: "POST",
        body: JSON.stringify({
          candidate_id: candidateId,
          status: modalStage,
          source: "MATCHING_ENGINE",
          initial_note: modalNote.trim() || undefined,
        }),
      });
      setExistingApp(newApp);
      setActionMessage(
        `Application created in stage '${modalStage.replace("_", " ")}'.`
      );
      setShowAppModal(false);
      setModalNote("");
    } catch (err: any) {
      setError(err.message || "Failed to create application for candidate.");
    } finally {
      setSubmittingApp(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "DEMONSTRATED":
        return {
          label: "Demonstrated",
          cls: "bg-emerald-50 text-emerald-800 border-emerald-200",
          icon: CheckCircle2,
        };
      case "PARTIAL":
        return {
          label: "Partial Evidence",
          cls: "bg-blue-50 text-blue-800 border-blue-200",
          icon: HelpCircle,
        };
      case "NEEDS_VERIFICATION":
        return {
          label: "Needs Verification",
          cls: "bg-amber-50 text-amber-800 border-amber-200",
          icon: ShieldAlert,
        };
      default:
        return {
          label: "Evidence Not Found",
          cls: "bg-slate-100 text-slate-700 border-slate-200",
          icon: AlertCircle,
        };
    }
  };

  if (loading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-slate-500 space-y-2">
        <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs font-medium">Loading match breakdown...</span>
      </div>
    );
  }

  if (error || !detail?.result) {
    return (
      <div className="max-w-2xl p-6 bg-red-50 border border-red-200 rounded-xl text-red-800 space-y-3">
        <p className="font-semibold">{error || "Match result not found."}</p>
        <Link
          href={`/jobs/${jobId}/matches`}
          className="text-xs font-bold text-red-900 underline inline-block"
        >
          Return to matches list
        </Link>
      </div>
    );
  }

  const result = detail.result;
  const evidences = detail.evidences || [];

  return (
    <div className="max-w-6xl space-y-6">
      {/* Navigation */}
      <div className="flex items-center justify-between">
        <Link
          href={`/jobs/${jobId}/matches`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Matches List</span>
        </Link>

        <Link
          href={`/jobs/${jobId}/pipeline`}
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-lg transition-colors border border-slate-300 shadow-xs"
        >
          <Kanban className="w-3.5 h-3.5 text-blue-600" />
          <span>View Pipeline Kanban</span>
        </Link>
      </div>

      {/* Messages */}
      {actionMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800 text-xs font-medium flex items-center space-x-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-800 text-xs font-medium flex items-center space-x-2">
          <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Header Profile Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              Scoring Engine {result.scoring_version}
            </span>
            <span className="text-xs text-slate-400">
              Evaluated {formatDateTime(result.updated_at || result.created_at)}
            </span>
            {existingApp && (
              <Link
                href={`/applications/${existingApp.id}`}
                className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 inline-flex items-center gap-1 transition-colors"
              >
                <span>Pipeline Stage: {existingApp.status.replace("_", " ")}</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            )}
          </div>

          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {result.candidate_name || "Candidate"}
          </h1>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-600">
            {result.candidate_title && <span>{result.candidate_title}</span>}
            {result.candidate_location && <span>• {result.candidate_location}</span>}
            {result.candidate_email && <span>• {result.candidate_email}</span>}
            <Link
              href={`/candidates/${candidateId}`}
              className="text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-1 ml-1"
            >
              <span>View Master Profile</span>
              <ExternalLink className="w-3 h-3" />
            </Link>
          </div>
          <div className="text-xs text-slate-500 pt-1">
            Matching for Position: <span className="font-semibold text-slate-800">{job?.title}</span>
          </div>
        </div>

        {/* Big Score Widget & Actions */}
        <div className="flex flex-col items-end space-y-3 shrink-0">
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center min-w-[140px]">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              Evidence Alignment
            </div>
            <div className="text-4xl font-black text-slate-900 tracking-tight mt-1">
              {Math.round(result.overall_score)}
              <span className="text-sm font-normal text-slate-400">/100</span>
            </div>
            <div className="text-[10px] text-slate-400 mt-0.5">
              Deterministic Calculation
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {!existingApp ? (
              <button
                onClick={() => {
                  setModalStage(result.overall_score >= 70 ? "SHORTLISTED" : "APPLIED");
                  setShowAppModal(true);
                }}
                className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
              >
                <UserPlus className="w-3.5 h-3.5" />
                <span>Add to Pipeline / Shortlist</span>
              </button>
            ) : (
              <Link
                href={`/applications/${existingApp.id}`}
                className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold text-slate-800 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors border border-slate-200"
              >
                <span>Go to Application</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            )}

            <button
              onClick={handleRefreshExplanation}
              disabled={actionLoading !== null}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
            >
              <Sparkles className={`w-3.5 h-3.5 ${actionLoading === "explanation" ? "animate-spin" : ""}`} />
              <span>Refresh AI</span>
            </button>
            <button
              onClick={handleRecalculate}
              disabled={actionLoading !== null}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-lg transition-colors"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${actionLoading === "recalculate" ? "animate-spin" : ""}`} />
              <span>Recalculate</span>
            </button>
          </div>
        </div>
      </div>

      {/* Five Dimension Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Required Skills (40%)
          </div>
          <div className="text-xl font-black text-slate-900 mt-1">
            {Math.round(result.required_skills_score)}%
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-blue-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, result.required_skills_score)}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Experience (25%)
          </div>
          <div className="text-xl font-black text-slate-900 mt-1">
            {Math.round(result.experience_score)}%
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-emerald-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, result.experience_score)}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Preferred Skills (15%)
          </div>
          <div className="text-xl font-black text-slate-900 mt-1">
            {Math.round(result.preferred_skills_score)}%
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-indigo-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, result.preferred_skills_score)}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Projects (10%)
          </div>
          <div className="text-xl font-black text-slate-900 mt-1">
            {Math.round(result.project_relevance_score)}%
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-amber-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, result.project_relevance_score)}%` }}
            ></div>
          </div>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs">
          <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider">
            Other Criteria (10%)
          </div>
          <div className="text-xl font-black text-slate-900 mt-1">
            {Math.round(result.other_criteria_score)}%
          </div>
          <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2 overflow-hidden">
            <div
              className="bg-slate-600 h-1.5 rounded-full"
              style={{ width: `${Math.min(100, result.other_criteria_score)}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* AI Grounded Explanation Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-blue-600" />
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            AI-Assisted Match Explanation
          </h2>
        </div>

        {result.explanation ? (
          <div className="p-4 bg-slate-50 border border-slate-100 rounded-xl text-slate-800 text-xs leading-relaxed">
            {result.explanation}
          </div>
        ) : (
          <div className="text-xs text-slate-400 italic">No explanation generated yet.</div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Key Strengths */}
          <div className="p-4 bg-emerald-50/50 border border-emerald-100 rounded-xl space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-emerald-900">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span>Demonstrated Strengths</span>
            </div>
            {result.strengths && result.strengths.length > 0 ? (
              <ul className="space-y-1 text-xs text-emerald-800 list-disc list-inside">
                {result.strengths.map((str, idx) => (
                  <li key={idx}>{str}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic">No documented strengths recorded.</p>
            )}
          </div>

          {/* Skill Gaps */}
          <div className="p-4 bg-slate-50 border border-slate-200/70 rounded-xl space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-slate-900">
              <AlertCircle className="w-3.5 h-3.5 text-slate-500" />
              <span>Gaps / Missing Evidence</span>
            </div>
            {result.skill_gaps && result.skill_gaps.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-700 list-disc list-inside">
                {result.skill_gaps.map((gap, idx) => (
                  <li key={idx}>{gap}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic">No notable skill gaps noted.</p>
            )}
          </div>

          {/* Verification Items */}
          <div className="p-4 bg-amber-50/50 border border-amber-100 rounded-xl space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-amber-900">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
              <span>Items Requiring Recruiter Verification</span>
            </div>
            {result.verification_items && result.verification_items.length > 0 ? (
              <ul className="space-y-1 text-xs text-amber-800 list-disc list-inside">
                {result.verification_items.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic">No verification items flagged.</p>
            )}
          </div>

          {/* Suggested Interview Questions */}
          <div className="p-4 bg-blue-50/50 border border-blue-100 rounded-xl space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-bold text-blue-900">
              <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
              <span>Targeted Interview Questions</span>
            </div>
            {result.suggested_questions && result.suggested_questions.length > 0 ? (
              <ul className="space-y-1 text-xs text-blue-800 list-disc list-inside">
                {result.suggested_questions.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic">No interview questions generated.</p>
            )}
          </div>
        </div>
      </div>

      {/* Criterion-Level Evidence Breakdown */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div className="space-y-0.5">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Criterion-Level Verified Evidence
            </h2>
            <p className="text-xs text-slate-500">
              Traceable records mapping job requirements to candidate source documents.
            </p>
          </div>
          <span className="text-xs font-medium text-slate-500">
            {evidences.length} criteria evaluated
          </span>
        </div>

        {evidences.length === 0 ? (
          <div className="text-xs text-slate-400 py-6 text-center italic">
            No criterion-level evidence records stored for this match.
          </div>
        ) : (
          <div className="divide-y divide-slate-100 border border-slate-100 rounded-xl overflow-hidden">
            {evidences.map((ev) => {
              const badge = getStatusBadge(ev.evidence_status);
              const Icon = badge.icon;
              return (
                <div key={ev.id} className="p-4 space-y-2.5 bg-white hover:bg-slate-50/50 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-slate-900">{ev.criterion_name}</span>
                      <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                        {ev.criterion_type}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {ev.semantic_similarity !== null && ev.semantic_similarity !== undefined && (
                        <span className="text-[11px] text-slate-500 font-mono">
                          similarity: {Math.round(ev.semantic_similarity * 100)}%
                        </span>
                      )}
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border flex items-center gap-1 ${badge.cls}`}>
                        <Icon className="w-3 h-3" />
                        {badge.label}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                    <div className="bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        Expected Requirement
                      </span>
                      <p className="text-slate-700">{ev.expected_requirement}</p>
                    </div>

                    <div className="bg-slate-50/70 p-2.5 rounded-lg border border-slate-100">
                      <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                        Candidate Evidence
                      </span>
                      <p className="text-slate-800 font-medium">
                        {ev.candidate_evidence || "No explicit evidence found in candidate record."}
                      </p>
                    </div>
                  </div>

                  {ev.source_excerpt && (
                    <div className="p-2.5 bg-blue-50/40 border border-blue-100 rounded-lg text-xs space-y-1">
                      <div className="flex items-center justify-between text-[11px] text-blue-900 font-semibold">
                        <span className="flex items-center gap-1">
                          <BookOpen className="w-3 h-3 text-blue-600" />
                          Source Resume Excerpt
                        </span>
                        {ev.source_page && (
                          <span className="font-mono text-[10px] text-blue-700">
                            Page {ev.source_page}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-700 italic font-mono text-[11px]">
                        &ldquo;{ev.source_excerpt}&rdquo;
                      </p>
                    </div>
                  )}

                  {ev.explanation && (
                    <div className="text-[11px] text-slate-500">
                      <span className="font-semibold text-slate-700">Rationale: </span>
                      {ev.explanation}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recruiter Assistance Disclaimer */}
      <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center text-xs text-slate-500">
        <span className="font-semibold text-slate-700">Recruiter Assistance Disclaimer:</span> This score represents evidence alignment based strictly on documented records in the HireLens system. HireLens provides assistive intelligence; scores do not constitute automated hiring, ranking, or rejection decisions.
      </div>

      {/* Add Application Modal */}
      {showAppModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Create Application for Candidate
              </h3>
              <button
                onClick={() => setShowAppModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Create an application for <strong className="text-slate-800">{result.candidate_name}</strong> for the role <strong className="text-slate-800">{job?.title}</strong>.
            </p>

            <form onSubmit={handleCreateApplication} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Select Initial Pipeline Stage
                </label>
                <select
                  value={modalStage}
                  onChange={(e) => setModalStage(e.target.value as PipelineStageType)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="APPLIED">APPLIED (General Pool)</option>
                  <option value="UNDER_REVIEW">UNDER REVIEW (Initial Review)</option>
                  <option value="SHORTLISTED">SHORTLISTED (Direct Shortlist)</option>
                  <option value="INTERVIEW">INTERVIEW (Schedule Technical Screen)</option>
                  <option value="ON_HOLD">ON HOLD (Reserve for Later)</option>
                </select>
                <p className="text-[10px] text-slate-400 mt-1">
                  Creating an application does not automatically shortlist candidates; you choose the appropriate action.
                </p>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Initial Recruiter Note (Optional)
                </label>
                <textarea
                  rows={2}
                  value={modalNote}
                  onChange={(e) => setModalNote(e.target.value)}
                  placeholder="e.g., Sourced from evidence matching score of 82%..."
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>

              <div className="flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowAppModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingApp}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs disabled:opacity-50"
                >
                  {submittingApp ? "Creating..." : "Confirm & Create Application"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  User,
  Briefcase,
  Calendar,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldAlert,
  Archive,
  Edit3,
  MessageSquare,
  History,
  Activity,
  UserCheck,
  Tag,
  ExternalLink,
  ChevronRight,
  BookOpen,
  Send,
  Plus,
  Video,
  Star,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  ApplicationDetailResponse,
  PipelineStageType,
  ApplicationNote,
  ApplicationStageHistory,
  Interview,
  InterviewListResponse,
} from "@/types";
import { formatDateTime } from "@/lib/utils";
import {
  formatDateIST,
  formatTimeIST,
  formatDateTimeIST,
  formatInterviewTimeRange,
} from "@/lib/timezone";

const ALL_STAGES: PipelineStageType[] = [
  "APPLIED",
  "UNDER_REVIEW",
  "SHORTLISTED",
  "INTERVIEW",
  "SELECTED",
  "ON_HOLD",
  "REJECTED",
  "WITHDRAWN",
];

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const applicationId = params?.id as string;

  const [detail, setDetail] = useState<ApplicationDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  // Stage transition form state
  const [targetStage, setTargetStage] = useState<PipelineStageType>("UNDER_REVIEW");
  const [transitionReason, setTransitionReason] = useState("");
  const [submittingTransition, setSubmittingTransition] = useState(false);

  // Note form state
  const [newNoteContent, setNewNoteContent] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);

  // Recruiter assignment state
  const [assigningRecruiter, setAssigningRecruiter] = useState(false);

  // Phase 6: Interviews state
  const [interviews, setInterviews] = useState<Interview[]>([]);

  const fetchApplicationData = async () => {
    try {
      const [appData, membersData, interviewsData]: [ApplicationDetailResponse, any[], InterviewListResponse] =
        await Promise.all([
          apiClient<ApplicationDetailResponse>(`/applications/${applicationId}`),
          apiClient<any[]>("/agency/members").catch(() => []),
          apiClient<any>(`/applications/${applicationId}/interviews`).catch(() => []),
        ]);
      setDetail(appData);
      setMembers(membersData);
      setInterviews(Array.isArray(interviewsData) ? interviewsData : (interviewsData?.items || []));
      if (appData.application.status) {
        setTargetStage(appData.application.status);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load application details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (applicationId) {
      fetchApplicationData();
    }
  }, [applicationId]);

  const handleStageTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detail || targetStage === detail.application.status) return;
    setSubmittingTransition(true);
    setActionMessage(null);
    setError(null);
    try {
      await apiClient(`/applications/${applicationId}/transition`, {
        method: "POST",
        body: JSON.stringify({
          new_stage: targetStage,
          reason: transitionReason.trim() || undefined,
        }),
      });
      setTransitionReason("");
      setActionMessage(`Application stage updated to ${targetStage.replace("_", " ")}.`);
      await fetchApplicationData();
    } catch (err: any) {
      setError(err.message || "Failed to update application stage.");
    } finally {
      setSubmittingTransition(false);
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNoteContent.trim()) return;
    setSubmittingNote(true);
    setError(null);
    try {
      const addedNote: ApplicationNote = await apiClient(
        `/applications/${applicationId}/notes`,
        {
          method: "POST",
          body: JSON.stringify({ content: newNoteContent.trim() }),
        }
      );
      setDetail((prev) =>
        prev
          ? {
              ...prev,
              notes: [addedNote, ...prev.notes],
            }
          : null
      );
      setNewNoteContent("");
      setActionMessage("Recruiter note recorded.");
    } catch (err: any) {
      setError(err.message || "Failed to add recruiter note.");
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleAssignRecruiter = async (recruiterId: string) => {
    setAssigningRecruiter(true);
    setError(null);
    try {
      await apiClient(`/applications/${applicationId}`, {
        method: "PATCH",
        body: JSON.stringify({
          assigned_recruiter_id: recruiterId || null,
        }),
      });
      setActionMessage("Recruiter assignment updated.");
      await fetchApplicationData();
    } catch (err: any) {
      setError(err.message || "Failed to assign recruiter.");
    } finally {
      setAssigningRecruiter(false);
    }
  };

  const handleToggleArchive = async () => {
    if (!detail) return;
    const isCurrentlyArchived = !!detail.application.archived_at;
    if (
      !confirm(
        isCurrentlyArchived
          ? "Restore this application to active pipeline?"
          : "Archive this application?"
      )
    ) {
      return;
    }
    try {
      await apiClient(`/applications/${applicationId}`, {
        method: "PATCH",
        body: JSON.stringify({
          archived: !isCurrentlyArchived,
        }),
      });
      setActionMessage(
        isCurrentlyArchived ? "Application restored." : "Application archived."
      );
      await fetchApplicationData();
    } catch (err: any) {
      setError(err.message || "Failed to update archive status.");
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-500 space-y-3">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs font-medium">Loading application workspace...</span>
      </div>
    );
  }

  if (error && !detail) {
    return (
      <div className="max-w-2xl p-6 bg-red-50 border border-red-200 rounded-xl text-red-800 space-y-3">
        <p className="font-semibold">{error}</p>
        <Link href="/jobs" className="text-xs font-bold text-red-900 underline block">
          Return to jobs listing
        </Link>
      </div>
    );
  }

  if (!detail) return null;

  const app = detail.application;
  const cand = detail.candidate;
  const job = detail.job;
  const match = detail.latest_match_result;
  const evidences = detail.match_evidences || [];

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/jobs/${job.id}/pipeline`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Kanban: {job.title}</span>
        </Link>

        <div className="flex items-center space-x-2">
          <Link
            href={`/candidates/${cand.id}`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-lg transition-colors border border-slate-300 shadow-xs"
          >
            <User className="w-3.5 h-3.5" />
            <span>Master Profile</span>
            <ExternalLink className="w-3 h-3 text-slate-400" />
          </Link>
          <Link
            href={`/jobs/${job.id}`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-lg transition-colors border border-slate-300 shadow-xs"
          >
            <Briefcase className="w-3.5 h-3.5" />
            <span>Job Specs</span>
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {actionMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-emerald-800 text-xs shadow-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{actionMessage}</span>
        </div>
      )}
      {error && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-red-800 text-xs shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Hero Header Card */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-start justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center space-x-2.5">
            <span
              className={`text-xs font-bold px-2.5 py-0.5 rounded-full border uppercase ${
                app.status === "SELECTED"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : app.status === "SHORTLISTED"
                  ? "bg-purple-50 text-purple-700 border-purple-200"
                  : app.status === "INTERVIEW"
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : app.status === "REJECTED"
                  ? "bg-rose-50 text-rose-700 border-rose-200"
                  : "bg-blue-50 text-blue-700 border-blue-200"
              }`}
            >
              Stage: {app.status.replace("_", " ")}
            </span>
            {app.archived_at && (
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-100 text-slate-500 uppercase">
                Archived
              </span>
            )}
            <span className="text-xs text-slate-400 font-mono">
              Applied {formatDateTime(app.applied_at)}
            </span>
          </div>

          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {cand.full_name}
          </h1>

          <p className="text-xs text-slate-500">
            Applying for: <span className="font-semibold text-slate-800">{job.title}</span> • Source: {app.source || "Direct"}
          </p>

          {app.recruiter_summary && (
            <div className="p-2.5 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-100 italic">
              Recruiter Summary: &ldquo;{app.recruiter_summary}&rdquo;
            </div>
          )}
        </div>

        {/* Action Controls & Recruiter Assignment */}
        <div className="flex flex-col md:items-end space-y-3 shrink-0">
          <div className="flex items-center space-x-2">
            <label className="text-xs text-slate-500 font-medium">Recruiter:</label>
            <select
              value={app.assigned_recruiter_id || ""}
              onChange={(e) => handleAssignRecruiter(e.target.value)}
              disabled={assigningRecruiter}
              className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="">Unassigned</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name} ({m.role})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={handleToggleArchive}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
            >
              <Archive className="w-3.5 h-3.5" />
              <span>{app.archived_at ? "Restore" : "Archive"}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Grid Layout: Main Left Column & Sidebar Right Column */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Quick Stage Transition Box */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <ChevronRight className="w-4 h-4 text-blue-600" />
                Transition Application Stage
              </h2>
              <span className="text-xs text-slate-400">
                Current: <strong className="text-slate-700">{app.status.replace("_", " ")}</strong>
              </span>
            </div>

            <form onSubmit={handleStageTransition} className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                    Select Target Stage
                  </label>
                  <select
                    value={targetStage}
                    onChange={(e) => setTargetStage(e.target.value as PipelineStageType)}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-semibold"
                  >
                    {ALL_STAGES.map((s) => (
                      <option key={s} value={s}>
                        {s.replace("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                    Transition Reason / Notes (Optional)
                  </label>
                  <input
                    type="text"
                    value={transitionReason}
                    onChange={(e) => setTransitionReason(e.target.value)}
                    placeholder="e.g., Passed technical phone screen"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={submittingTransition || targetStage === app.status}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-xs transition-colors flex items-center space-x-1"
                >
                  <span>{submittingTransition ? "Transitioning..." : "Apply Stage Transition"}</span>
                </button>
              </div>
            </form>
          </div>

          {/* Candidate Profile Summary */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-blue-600" />
                Master Candidate Profile Summary
              </h2>
              <Link
                href={`/candidates/${cand.id}`}
                className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
              >
                <span>Full Profile</span>
                <ExternalLink className="w-3 h-3" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Email Address</span>
                <span className="font-semibold text-slate-800">{cand.email || "Not specified"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Location</span>
                <span className="font-semibold text-slate-800">{cand.current_location || "Not specified"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Current Designation</span>
                <span className="font-semibold text-slate-800">{cand.current_title || "Not specified"}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Total Experience</span>
                <span className="font-semibold text-slate-800">
                  {cand.total_experience_months
                    ? `${Math.floor(cand.total_experience_months / 12)} years (${cand.total_experience_months} months)`
                    : "Not specified"}
                </span>
              </div>
            </div>

            {cand.professional_summary && (
              <div className="pt-2 border-t border-slate-100">
                <span className="text-slate-400 block text-[11px] mb-1">Professional Summary</span>
                <p className="text-xs text-slate-700 leading-relaxed bg-slate-50/70 p-3 rounded-lg border border-slate-100">
                  {cand.professional_summary}
                </p>
              </div>
            )}
          </div>

          {/* Phase 4 Matching Result & Grounded Evidence */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                Matching Intelligence & Evidence Alignment
              </h2>
              {match && (
                <Link
                  href={`/jobs/${job.id}/matches/${cand.id}`}
                  className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
                >
                  <span>Detailed Match Breakdown</span>
                  <ChevronRight className="w-3 h-3" />
                </Link>
              )}
            </div>

            {!match ? (
              <div className="p-6 text-center text-xs text-slate-400 italic bg-slate-50 rounded-xl">
                No matching run executed yet for this candidate and job. Run the matching engine from the matches view to score alignment.
              </div>
            ) : (
              <div className="space-y-4">
                {/* Score Banner */}
                <div className="flex flex-col sm:flex-row items-center justify-between p-4 bg-slate-50/80 rounded-xl border border-slate-200/70 gap-4">
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                      Evidence Alignment Score
                    </span>
                    <div className="flex items-baseline space-x-2">
                      <span className="text-3xl font-black text-slate-900">
                        {Math.round(match.overall_score)}
                      </span>
                      <span className="text-xs text-slate-400">/ 100</span>
                      {match.is_stale && (
                        <span className="text-[10px] font-bold text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                          Stale
                        </span>
                      )}
                    </div>
                  </div>

                  {/* 5-Dimension Summary */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-center text-xs">
                    <div className="p-2 bg-white rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase block">Req</span>
                      <span className="font-bold text-slate-800">{Math.round(match.required_skills_score)}%</span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase block">Exp</span>
                      <span className="font-bold text-slate-800">{Math.round(match.experience_score)}%</span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase block">Pref</span>
                      <span className="font-bold text-slate-800">{Math.round(match.preferred_skills_score)}%</span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase block">Proj</span>
                      <span className="font-bold text-slate-800">{Math.round(match.project_relevance_score)}%</span>
                    </div>
                    <div className="p-2 bg-white rounded-lg border border-slate-200">
                      <span className="text-[10px] text-slate-400 uppercase block">Other</span>
                      <span className="font-bold text-slate-800">{Math.round(match.other_criteria_score)}%</span>
                    </div>
                  </div>
                </div>

                {/* Explanation */}
                {match.explanation && (
                  <p className="text-xs text-slate-700 italic bg-white p-3 rounded-lg border border-slate-200/80">
                    &ldquo;{match.explanation}&rdquo;
                  </p>
                )}

                {/* Key Strengths & Gaps */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="p-3 bg-emerald-50/50 rounded-lg border border-emerald-100">
                    <span className="text-[10px] font-bold text-emerald-900 uppercase tracking-wider block mb-1">
                      Demonstrated Strengths
                    </span>
                    {match.strengths && match.strengths.length > 0 ? (
                      <ul className="space-y-0.5 list-disc list-inside text-emerald-800">
                        {match.strengths.map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-slate-400 italic">None documented</span>
                    )}
                  </div>

                  <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/70">
                    <span className="text-[10px] font-bold text-slate-900 uppercase tracking-wider block mb-1">
                      Identified Gaps
                    </span>
                    {match.skill_gaps && match.skill_gaps.length > 0 ? (
                      <ul className="space-y-0.5 list-disc list-inside text-slate-700">
                        {match.skill_gaps.map((g, idx) => (
                          <li key={idx}>{g}</li>
                        ))}
                      </ul>
                    ) : (
                      <span className="text-slate-400 italic">None documented</span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Phase 6: Interview Rounds Card */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center space-x-2">
                <Calendar className="w-4 h-4 text-blue-600" />
                <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Interview Rounds ({interviews.length})
                </h2>
              </div>

              <Link
                href="/interviews"
                className="inline-flex items-center space-x-1 px-2.5 py-1 text-xs font-semibold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200 transition-colors"
              >
                <Plus className="w-3 h-3" />
                <span>Schedule Round</span>
              </Link>
            </div>

            {interviews.length === 0 ? (
              <div className="text-center py-6 space-y-2">
                <Calendar className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-xs text-slate-500">No interview rounds scheduled for this application yet.</p>
                <Link
                  href="/interviews"
                  className="inline-flex items-center space-x-1 text-xs font-semibold text-blue-600 hover:text-blue-800"
                >
                  <span>Open Interview Workspace to Schedule</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {interviews.map((iv) => (
                  <div
                    key={iv.id}
                    className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 hover:border-blue-200 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
                  >
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-slate-900 text-sm">{iv.round_name}</span>
                        <span className="px-2 py-0.5 text-[10px] font-semibold bg-slate-200 text-slate-700 rounded">
                          {iv.round_type.replace("_", " ")}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                            iv.status === "CONFIRMED"
                              ? "bg-emerald-100 text-emerald-800 border-emerald-200"
                              : iv.status === "SCHEDULED"
                              ? "bg-blue-100 text-blue-800 border-blue-200"
                              : iv.status === "COMPLETED"
                              ? "bg-slate-200 text-slate-800 border-slate-300"
                              : iv.status === "CANCELLED"
                              ? "bg-rose-100 text-rose-800 border-rose-200"
                              : "bg-amber-100 text-amber-800 border-amber-200"
                          }`}
                        >
                          {iv.status}
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-3 text-slate-500 text-[11px]">
                        <span className="font-medium text-slate-700">
                          {formatDateIST(iv.scheduled_start, {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })}{" "}
                          •{" "}
                          {formatInterviewTimeRange(iv.scheduled_start, iv.scheduled_end, iv.timezone)}
                        </span>
                        <span>•</span>
                        <span>Mode: {iv.interview_mode}</span>
                        {iv.participants && iv.participants.length > 0 && (
                          <>
                            <span>•</span>
                            <span>{iv.participants.map((p) => p.participant_name).join(", ")}</span>
                          </>
                        )}
                      </div>

                      {iv.feedback_count > 0 && (
                        <span className="inline-block mt-1 text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                          {iv.feedback_count} Reviewer Feedback Submitted
                        </span>
                      )}
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <Link
                        href={`/interviews/${iv.id}`}
                        className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-white hover:bg-blue-50 border border-blue-200 rounded-lg shadow-xs transition-colors"
                      >
                        <span>View / Feedback</span>
                        <ChevronRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Column: Stage History Timeline, Notes, & Activity History */}
        <div className="space-y-6">
          {/* Recruiter Notes Card */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
              Recruiter Notes ({detail.notes.length})
            </h2>

            {/* Add Note Form */}
            <form onSubmit={handleAddNote} className="space-y-2">
              <textarea
                rows={2}
                value={newNoteContent}
                onChange={(e) => setNewNoteContent(e.target.value)}
                placeholder="Log recruitment notes, interview feedback..."
                className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
              ></textarea>
              <button
                type="submit"
                disabled={submittingNote || !newNoteContent.trim()}
                className="w-full py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50 rounded-lg transition-colors flex items-center justify-center space-x-1"
              >
                <Plus className="w-3 h-3" />
                <span>{submittingNote ? "Adding..." : "Add Note"}</span>
              </button>
            </form>

            {/* Notes List */}
            <div className="space-y-2.5 max-h-72 overflow-y-auto divide-y divide-slate-100">
              {detail.notes.length === 0 ? (
                <p className="text-xs text-slate-400 py-2 italic text-center">
                  No notes recorded yet.
                </p>
              ) : (
                detail.notes.map((n) => (
                  <div key={n.id} className="pt-2 text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-slate-400">
                      <span className="font-semibold text-slate-700">{n.author_name}</span>
                      <span>{formatDateTime(n.created_at)}</span>
                    </div>
                    <p className="text-slate-800 bg-slate-50/70 p-2 rounded border border-slate-100">
                      {n.content}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Immutable Stage History Timeline */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <History className="w-3.5 h-3.5 text-blue-600" />
              Stage Transition Timeline
            </h2>

            <div className="space-y-3 relative border-l-2 border-slate-100 ml-2 pl-4">
              {detail.stage_history.map((hist, idx) => (
                <div key={hist.id} className="relative text-xs space-y-0.5">
                  <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-blue-500 border-2 border-white shadow-xs"></div>
                  <div className="flex items-center space-x-1 font-semibold text-slate-800">
                    {hist.previous_stage ? (
                      <>
                        <span className="text-slate-500">{hist.previous_stage}</span>
                        <span>→</span>
                        <span className="text-blue-600">{hist.new_stage}</span>
                      </>
                    ) : (
                      <span className="text-blue-600">{hist.new_stage} (Initial)</span>
                    )}
                  </div>
                  <div className="text-[10px] text-slate-400 flex items-center justify-between">
                    <span>By {hist.changed_by_name || "Recruiter"}</span>
                    <span>{formatDateTime(hist.created_at)}</span>
                  </div>
                  {hist.reason && (
                    <p className="text-[11px] text-slate-600 italic bg-slate-50 p-1.5 rounded">
                      &ldquo;{hist.reason}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Audit Activity Trail */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-blue-600" />
              Audit Log Trail
            </h2>

            <div className="space-y-2 max-h-64 overflow-y-auto text-xs">
              {detail.activity.map((act) => (
                <div
                  key={act.id}
                  className="p-2 bg-slate-50 rounded border border-slate-100 flex items-start justify-between text-[11px]"
                >
                  <div className="space-y-0.5">
                    <span className="font-bold text-slate-800">{act.action}</span>
                    <p className="text-slate-500">By {act.user_name || "System"}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 shrink-0 font-mono">
                    {formatTimeIST(act.created_at)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

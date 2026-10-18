"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Calendar,
  Clock,
  Video,
  MapPin,
  Phone,
  Users,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  ShieldCheck,
  UserCheck,
  Sparkles,
  RefreshCw,
  Star,
  History,
  FileText,
  AlertTriangle,
  Copy,
  Check,
  Send,
  Edit2,
  Lock,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Interview,
  InterviewFeedback,
  InterviewHistory,
  InterviewMode,
  InterviewStatus,
  InterviewRoundType,
  FeedbackRecommendation,
} from "@/types";
import { formatDateTime } from "@/lib/utils";
import {
  formatDateIST,
  formatTimeIST,
  formatDateTimeIST,
  formatInterviewTimeRange,
  formatDateForPicker,
  formatTimeForPicker,
  DEFAULT_TIMEZONE,
  IST_LABEL,
} from "@/lib/timezone";

const RECOMMENDATIONS: { key: FeedbackRecommendation; label: string; color: string }[] = [
  { key: "STRONG_YES", label: "Strong Yes — Hire", color: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  { key: "YES", label: "Yes — Recommend", color: "bg-blue-100 text-blue-800 border-blue-300" },
  { key: "MAYBE", label: "Maybe / Mixed", color: "bg-amber-100 text-amber-800 border-amber-300" },
  { key: "NO", label: "No — Do Not Recommend", color: "bg-rose-100 text-rose-800 border-rose-300" },
  { key: "STRONG_NO", label: "Strong No — Definite Reject", color: "bg-red-200 text-red-900 border-red-400" },
];

export default function InterviewDetailPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.id as string;

  const [interview, setInterview] = useState<Interview | null>(null);
  const [feedbacks, setFeedbacks] = useState<InterviewFeedback[]>([]);
  const [histories, setHistories] = useState<InterviewHistory[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [copiedLink, setCopiedLink] = useState(false);

  const [calendarMappings, setCalendarMappings] = useState<any[]>([]);
  const [syncingCalendar, setSyncingCalendar] = useState(false);
  const [generatingMeet, setGeneratingMeet] = useState(false);

  const handleRetryCalendarSync = async () => {
    try {
      setSyncingCalendar(true);
      setError(null);
      await apiClient(`/integrations/interviews/${interviewId}/sync`, { method: "POST" });
      setSuccessMessage("Calendar synchronization enqueued.");
      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to trigger calendar sync.");
    } finally {
      setSyncingCalendar(false);
    }
  };

  const handleGenerateMeetingLink = async (provider: "GOOGLE_MEET" | "MS_TEAMS") => {
    try {
      setGeneratingMeet(true);
      setError(null);
      const res = await apiClient<{ status: string; meeting_url?: string }>(
        `/integrations/interviews/${interviewId}/meeting-link`,
        {
          method: "POST",
          body: JSON.stringify({ meeting_provider: provider }),
        }
      );
      if (res.meeting_url) {
        setSuccessMessage("Meeting link generated and attached!");
        fetchInterviewDetails();
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate meeting link.");
    } finally {
      setGeneratingMeet(false);
    }
  };

  // Reschedule Modal State

  const [showRescheduleModal, setShowRescheduleModal] = useState(false);
  const [rescheduleData, setRescheduleData] = useState({
    date: "",
    start_time: "",
    end_time: "",
    timezone: "Asia/Kolkata",
    reason: "",
  });
  const [rescheduleSubmitting, setRescheduleSubmitting] = useState(false);
  const [rescheduleConflict, setRescheduleConflict] = useState<string | null>(null);

  // Cancel Modal State
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  // Action submitting state
  const [actionSubmitting, setActionSubmitting] = useState(false);

  // Feedback Form State
  const [myFeedback, setMyFeedback] = useState<InterviewFeedback | null>(null);
  const [feedbackForm, setFeedbackForm] = useState<{
    overall_rating: number;
    recommendation: FeedbackRecommendation;
    technical_assessment: number;
    communication_assessment: number;
    problem_solving_assessment: number;
    role_specific_assessment: number;
    strengths: string;
    concerns: string;
    detailed_feedback: string;
  }>({
    overall_rating: 4,
    recommendation: "YES",
    technical_assessment: 4,
    communication_assessment: 4,
    problem_solving_assessment: 4,
    role_specific_assessment: 4,
    strengths: "",
    concerns: "",
    detailed_feedback: "",
  });
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);

  const fetchInterviewDetails = async () => {
    try {
      const [intData, fbData, histData, meData, calData] = await Promise.all([
        apiClient<Interview>(`/interviews/${interviewId}`),
        apiClient<InterviewFeedback[]>(`/interviews/${interviewId}/feedback`).catch(() => []),
        apiClient<InterviewHistory[]>(`/interviews/${interviewId}/history`).catch(() => []),
        apiClient<any>("/auth/me").catch(() => null),
        apiClient<any[]>(`/integrations/interviews/${interviewId}/mapping`).catch(() => []),
      ]);

      setInterview(intData);
      setFeedbacks(fbData);
      setHistories(histData);
      setCurrentUser(meData);
      setCalendarMappings(calData || []);


      // Check if current user already submitted feedback
      if (meData) {
        const existing = fbData.find((f) => f.reviewer_id === meData.id);
        if (existing) {
          setMyFeedback(existing);
          setFeedbackForm({
            overall_rating: existing.overall_rating,
            recommendation: existing.recommendation,
            technical_assessment: existing.technical_assessment || 3,
            communication_assessment: existing.communication_assessment || 3,
            problem_solving_assessment: existing.problem_solving_assessment || 3,
            role_specific_assessment: existing.role_specific_assessment || 3,
            strengths: existing.strengths || "",
            concerns: existing.concerns || "",
            detailed_feedback: existing.detailed_feedback || "",
          });
        }
      }

      // Pre-fill reschedule form defaults
      if (intData) {
        const tz = intData.timezone || DEFAULT_TIMEZONE;
        setRescheduleData({
          date: formatDateForPicker(intData.scheduled_start, tz),
          start_time: formatTimeForPicker(intData.scheduled_start, tz),
          end_time: formatTimeForPicker(intData.scheduled_end, tz),
          timezone: tz,
          reason: "",
        });
      }
    } catch (err: any) {
      setError(err.message || "Failed to load interview details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (interviewId) {
      fetchInterviewDetails();
    }
  }, [interviewId]);

  const handleCopyMeetingUrl = () => {
    if (interview?.meeting_url) {
      navigator.clipboard.writeText(interview.meeting_url);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  // Status transitions
  const handleConfirm = async () => {
    setActionSubmitting(true);
    setError(null);
    try {
      await apiClient(`/interviews/${interviewId}/confirm`, { method: "POST" });
      setSuccessMessage("Interview confirmed successfully.");
      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to confirm interview.");
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleComplete = async () => {
    setActionSubmitting(true);
    setError(null);
    try {
      await apiClient(`/interviews/${interviewId}/complete`, { method: "POST" });
      setSuccessMessage("Interview marked as completed! Interviewers can now finalize feedback.");
      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to complete interview.");
    } finally {
      setActionSubmitting(false);
    }
  };

  const handleRescheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRescheduleConflict(null);

    const scheduled_start = `${rescheduleData.date}T${rescheduleData.start_time}:00`;
    const scheduled_end = `${rescheduleData.date}T${rescheduleData.end_time}:00`;

    if (scheduled_end <= scheduled_start) {
      setRescheduleConflict("End time must be after start time.");
      return;
    }

    setRescheduleSubmitting(true);
    try {
      await apiClient(`/interviews/${interviewId}/reschedule`, {
        method: "POST",
        body: JSON.stringify({
          scheduled_start,
          scheduled_end,
          timezone: rescheduleData.timezone,
          reason: rescheduleData.reason || "Rescheduled by recruiter",
        }),
      });

      setShowRescheduleModal(false);
      setSuccessMessage("Interview rescheduled successfully!");
      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("Conflict") || err.message?.includes("overlap")) {
        setRescheduleConflict(err.message || "Interviewer schedule conflict detected. Please pick another slot.");
      } else {
        setRescheduleConflict(err.message || "Failed to reschedule interview.");
      }
    } finally {
      setRescheduleSubmitting(false);
    }
  };

  const openRescheduleModal = () => {
    if (interview) {
      const tz = interview.timezone || DEFAULT_TIMEZONE;
      setRescheduleData({
        date: formatDateForPicker(interview.scheduled_start, tz),
        start_time: formatTimeForPicker(interview.scheduled_start, tz),
        end_time: formatTimeForPicker(interview.scheduled_end, tz),
        timezone: tz,
        reason: "",
      });
      setRescheduleConflict(null);
    }
    setShowRescheduleModal(true);
  };

  const handleCancelSubmit = async (e: React.FormEvent) => {

    e.preventDefault();
    if (!cancelReason.trim()) {
      setError("A cancellation reason is required.");
      return;
    }

    setCancelSubmitting(true);
    try {
      await apiClient(`/interviews/${interviewId}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason: cancelReason.trim() }),
      });

      setShowCancelModal(false);
      setSuccessMessage("Interview cancelled.");
      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to cancel interview.");
    } finally {
      setCancelSubmitting(false);
    }
  };

  const handleFeedbackSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedbackSubmitting(true);
    setError(null);

    try {
      if (myFeedback) {
        // Update existing feedback
        await apiClient(`/interviews/${interviewId}/feedback/${myFeedback.id}`, {
          method: "PATCH",
          body: JSON.stringify(feedbackForm),
        });
        setSuccessMessage("Your interview evaluation has been updated.");
      } else {
        // Submit new feedback
        await apiClient(`/interviews/${interviewId}/feedback`, {
          method: "POST",
          body: JSON.stringify(feedbackForm),
        });
        setSuccessMessage("Your interview evaluation has been submitted.");
      }

      fetchInterviewDetails();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to submit feedback.");
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center shadow-xs max-w-5xl mx-auto my-12">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-xs text-slate-500">Loading interview workspace...</p>
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16 space-y-3">
        <AlertCircle className="w-10 h-10 text-red-500 mx-auto" />
        <h2 className="text-lg font-bold text-slate-900">Interview Not Found</h2>
        <p className="text-xs text-slate-500">
          The requested interview could not be loaded or you do not have permission to view it.
        </p>
        <Link
          href="/interviews"
          className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Interviews</span>
        </Link>
      </div>
    );
  }

  const isCompleted = interview.status === "COMPLETED";
  const isCancelled = interview.status === "CANCELLED";
  const isScheduled = interview.status === "SCHEDULED" || interview.status === "RESCHEDULED";

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-16">
      {/* Top Breadcrumb & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/interviews"
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-blue-700 px-2 py-0.5 bg-blue-50 rounded border border-blue-200">
                {interview.round_name}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {interview.round_type.replace("_", " ")}
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight mt-0.5">
              {interview.title}
            </h1>
          </div>
        </div>

        {/* State Transition Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {interview.status === "SCHEDULED" && (
            <button
              onClick={handleConfirm}
              disabled={actionSubmitting}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 rounded-lg shadow-xs transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Confirm Schedule</span>
            </button>
          )}

          {!isCompleted && !isCancelled && (
            <button
              onClick={openRescheduleModal}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg shadow-xs transition-colors"
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Reschedule</span>
            </button>
          )}

          {(interview.status === "CONFIRMED" || interview.status === "SCHEDULED") && (
            <button
              onClick={handleComplete}
              disabled={actionSubmitting}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Mark as Completed</span>
            </button>
          )}

          {!isCompleted && !isCancelled && (
            <button
              onClick={() => setShowCancelModal(true)}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-rose-200 rounded-lg transition-colors"
            >
              <XCircle className="w-3.5 h-3.5" />
              <span>Cancel</span>
            </button>
          )}
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-emerald-800 text-xs shadow-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}
      {error && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-red-800 text-xs shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Grid Layout: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Columns: Interview Details & History */}
        <div className="lg:col-span-2 space-y-6">
          {/* Main Logistics Card */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-5">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Status
                </span>
                <span
                  className={`inline-block mt-1 px-3 py-0.5 text-xs font-bold rounded-full border ${
                    interview.status === "CONFIRMED"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                      : interview.status === "SCHEDULED"
                      ? "bg-blue-50 text-blue-700 border-blue-200"
                      : interview.status === "COMPLETED"
                      ? "bg-slate-100 text-slate-800 border-slate-300"
                      : interview.status === "CANCELLED"
                      ? "bg-rose-50 text-rose-700 border-rose-200"
                      : "bg-amber-50 text-amber-700 border-amber-200"
                  }`}
                >
                  {interview.status}
                </span>
              </div>

              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Interview Mode
                </span>
                <span className="inline-flex items-center space-x-1.5 mt-1 text-xs font-semibold text-slate-800">
                  {interview.interview_mode === "ONLINE" && <Video className="w-3.5 h-3.5 text-blue-600" />}
                  {interview.interview_mode === "IN_PERSON" && <MapPin className="w-3.5 h-3.5 text-emerald-600" />}
                  {interview.interview_mode === "PHONE" && <Phone className="w-3.5 h-3.5 text-purple-600" />}
                  <span>{interview.interview_mode}</span>
                </span>
              </div>

              <div>
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Timezone
                </span>
                <span className="mt-1 text-xs font-mono text-slate-700 block">
                  {interview.timezone}
                </span>
              </div>
            </div>

            {/* Application & Candidate Context */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-100 grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Candidate</span>
                <span className="font-bold text-slate-900 text-sm">
                  {interview.candidate_name || "Application Candidate"}
                </span>
                {interview.candidate_email && (
                  <span className="text-slate-500 block text-[11px]">{interview.candidate_email}</span>
                )}
              </div>

              <div>
                <span className="text-slate-400 block text-[11px]">Job & Application</span>
                <span className="font-semibold text-slate-800 text-sm block">
                  {interview.job_title || "Designated Job"}
                </span>
                <Link
                  href={`/applications/${interview.application_id}`}
                  className="text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-1 mt-0.5"
                >
                  <span>View Application Workspace</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>
            </div>

            {/* Timing & Calendar Slot */}
            <div className="space-y-2">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-blue-600" />
                <span>Scheduled Time Slot</span>
              </h3>
              <div className="p-3 bg-blue-50/60 border border-blue-100 rounded-xl flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                <div>
                  <span className="font-bold text-slate-900 text-sm block">
                    {formatDateIST(interview.scheduled_start, {
                      weekday: "long",
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                  <span className="text-slate-600 font-medium">
                    {formatInterviewTimeRange(
                      interview.scheduled_start,
                      interview.scheduled_end,
                      interview.timezone
                    )}
                  </span>
                </div>

                {interview.meeting_url && (
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={handleCopyMeetingUrl}
                      className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg shadow-xs hover:bg-slate-50"
                    >
                      {copiedLink ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>{copiedLink ? "Copied" : "Copy Link"}</span>
                    </button>
                    <a
                      href={interview.meeting_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs"
                    >
                      <Video className="w-3.5 h-3.5" />
                      <span>Join Call</span>
                    </a>
                  </div>
                )}
              </div>
            </div>

            {/* External Calendar Synchronization & Meeting Links */}
            <div className="space-y-2 pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-blue-600" />
                  <span>External Calendar Synchronization</span>
                </h3>
                <Link
                  href="/settings/integrations"
                  className="text-[11px] font-medium text-blue-600 hover:text-blue-800 flex items-center gap-0.5"
                >
                  <span>Integrations Settings</span>
                  <ExternalLink className="w-3 h-3" />
                </Link>
              </div>

              <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl space-y-3 text-xs">
                {calendarMappings && calendarMappings.length > 0 ? (
                  calendarMappings.map((m) => (
                    <div key={m.id} className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-800">
                          {m.provider === "GOOGLE" ? "Google Calendar" : m.provider === "MICROSOFT" ? "Microsoft Outlook" : "External Calendar"}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            m.sync_status === "SYNCED"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : m.sync_status === "PENDING"
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}
                        >
                          {m.sync_status}
                        </span>
                        {m.last_synced_at && (
                          <span className="text-[11px] text-slate-400 font-mono">
                            Synced {new Date(m.last_synced_at).toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata" })} IST
                          </span>
                        )}
                      </div>
                      <button
                        onClick={handleRetryCalendarSync}
                        disabled={syncingCalendar}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition shadow-2xs"
                      >
                        <RefreshCw className={`w-3 h-3 ${syncingCalendar ? "animate-spin" : ""}`} />
                        <span>Sync Now</span>
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <span className="text-slate-500">
                      No calendar events mapped yet. Synchronize with connected calendar accounts.
                    </span>
                    <button
                      onClick={handleRetryCalendarSync}
                      disabled={syncingCalendar}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium transition shadow-2xs shrink-0"
                    >
                      <RefreshCw className={`w-3 h-3 ${syncingCalendar ? "animate-spin" : ""}`} />
                      <span>Push to Calendar</span>
                    </button>
                  </div>
                )}

                {/* Meeting Link Generator if meeting url is empty */}
                {!interview.meeting_url && interview.interview_mode === "ONLINE" && (
                  <div className="pt-2 border-t border-slate-200/60 flex flex-wrap items-center gap-2">
                    <span className="text-[11px] text-slate-500 font-medium">Attach Video Conference:</span>
                    <button
                      onClick={() => handleGenerateMeetingLink("GOOGLE_MEET")}
                      disabled={generatingMeet}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200 text-xs font-medium transition"
                    >
                      <Video className="w-3 h-3" />
                      <span>Google Meet</span>
                    </button>
                    <button
                      onClick={() => handleGenerateMeetingLink("MS_TEAMS")}
                      disabled={generatingMeet}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-sky-50 text-sky-700 hover:bg-sky-100 border border-sky-200 text-xs font-medium transition"
                    >
                      <Video className="w-3 h-3" />
                      <span>Microsoft Teams</span>
                    </button>
                  </div>
                )}
              </div>
            </div>


            {/* Location if In-Person */}
            {interview.location && (
              <div className="text-xs space-y-1">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  Physical Location
                </span>
                <p className="text-slate-800 bg-slate-50 p-2.5 rounded-lg border border-slate-100 flex items-center gap-1.5">
                  <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                  <span>{interview.location}</span>
                </p>
              </div>
            )}

            {/* Description / Instructions */}
            {interview.description && (
              <div className="text-xs space-y-1">
                <span className="text-slate-400 font-bold uppercase tracking-wider text-[11px]">
                  Instructions & Focus Areas
                </span>
                <p className="text-slate-700 bg-slate-50 p-3 rounded-lg border border-slate-100 leading-relaxed">
                  {interview.description}
                </p>
              </div>
            )}

            {/* Cancellation Notice if Cancelled */}
            {interview.status === "CANCELLED" && (
              <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-xs text-rose-800 space-y-1">
                <strong className="block font-semibold">Interview Cancelled</strong>
                <p>Reason: {interview.cancellation_reason || "No reason specified"}</p>
                {interview.cancelled_at && (
                  <span className="text-[11px] text-rose-600 block">
                    Cancelled on {formatDateTime(interview.cancelled_at)}
                  </span>
                )}
              </div>
            )}
          </div>

          {/* Assigned Participants Card */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3">
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
              <Users className="w-3.5 h-3.5 text-blue-600" />
              <span>Assigned Participants ({interview.participants.length})</span>
            </h3>

            <div className="divide-y divide-slate-100">
              {interview.participants.map((p) => (
                <div key={p.id} className="py-2.5 flex items-center justify-between text-xs">
                  <div>
                    <span className="font-semibold text-slate-800 block">{p.participant_name}</span>
                    <span className="text-slate-400 text-[11px]">{p.participant_email}</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="px-2 py-0.5 text-[10px] font-bold rounded bg-slate-100 text-slate-600">
                      {p.participant_role}
                    </span>
                    <span className="px-2 py-0.5 text-[10px] font-semibold rounded bg-blue-50 text-blue-700">
                      {p.attendance_status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Scheduling History Audit Timeline */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <History className="w-3.5 h-3.5 text-blue-600" />
                <span>Interview Lifecycle & Scheduling History</span>
              </h3>
              <span className="text-[11px] text-slate-400 font-mono">Immutable Log</span>
            </div>

            {histories.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No historical changes logged yet.</p>
            ) : (
              <div className="space-y-3">
                {histories.map((h) => (
                  <div key={h.id} className="flex items-start space-x-3 text-xs">
                    <div className="w-2 h-2 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                    <div className="flex-1 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-slate-800 uppercase">{h.action}</span>
                        <span className="text-slate-400">{formatDateTime(h.created_at)}</span>
                      </div>
                      {h.reason && (
                        <p className="text-slate-700 mt-1 font-medium text-xs">
                          Reason: &ldquo;{h.reason}&rdquo;
                        </p>
                      )}
                      {h.previous_value && h.new_value && (
                        <div className="text-[11px] text-slate-500 mt-1 font-mono">
                          <span>{h.previous_value}</span> &rarr; <span>{h.new_value}</span>
                        </div>
                      )}
                      {h.actor_name && (
                        <span className="text-[10px] text-slate-400 block mt-1">
                          By: {h.actor_name}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right 1 Column: Structured Interview Feedback */}
        <div className="space-y-6">
          {/* Feedback Form Card */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                  <Star className="w-3.5 h-3.5 text-amber-500 fill-amber-500" />
                  <span>{myFeedback ? "Your Evaluation (Submitted)" : "Submit Evaluation"}</span>
                </h3>
                <p className="text-[11px] text-slate-500">
                  {myFeedback ? "You can update your evaluation anytime." : "Assess candidate performance for this round."}
                </p>
              </div>
            </div>

            <form onSubmit={handleFeedbackSubmit} className="space-y-3.5">
              {/* Overall Rating (1-5) */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Overall Rating (1–5) *
                </label>
                <div className="flex items-center space-x-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() => setFeedbackForm({ ...feedbackForm, overall_rating: star })}
                      className="p-1 hover:scale-110 transition-transform"
                    >
                      <Star
                        className={`w-6 h-6 ${
                          star <= feedbackForm.overall_rating
                            ? "text-amber-500 fill-amber-500"
                            : "text-slate-300"
                        }`}
                      />
                    </button>
                  ))}
                  <span className="text-xs font-bold text-slate-700 ml-2">
                    {feedbackForm.overall_rating} / 5
                  </span>
                </div>
              </div>

              {/* Recommendation */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Hiring Recommendation *
                </label>
                <select
                  value={feedbackForm.recommendation}
                  onChange={(e) =>
                    setFeedbackForm({
                      ...feedbackForm,
                      recommendation: e.target.value as FeedbackRecommendation,
                    })
                  }
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {RECOMMENDATIONS.map((r) => (
                    <option key={r.key} value={r.key}>
                      {r.label}
                    </option>
                  ))}
                </select>
              </div>

              {/* Sub-Criteria Assessments */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                  Category Breakdown (1–5)
                </span>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <label className="text-[11px] text-slate-600 block">Technical Skills</label>
                    <select
                      value={feedbackForm.technical_assessment}
                      onChange={(e) =>
                        setFeedbackForm({
                          ...feedbackForm,
                          technical_assessment: parseInt(e.target.value),
                        })
                      }
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded p-1.5"
                    >
                      {[1, 2, 3, 4, 5].map((v) => (
                        <option key={v} value={v}>
                          {v} - {v === 5 ? "Exceptional" : v === 1 ? "Inadequate" : "Proficient"}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-600 block">Communication</label>
                    <select
                      value={feedbackForm.communication_assessment}
                      onChange={(e) =>
                        setFeedbackForm({
                          ...feedbackForm,
                          communication_assessment: parseInt(e.target.value),
                        })
                      }
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded p-1.5"
                    >
                      {[1, 2, 3, 4, 5].map((v) => (
                        <option key={v} value={v}>
                          {v} / 5
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-600 block">Problem Solving</label>
                    <select
                      value={feedbackForm.problem_solving_assessment}
                      onChange={(e) =>
                        setFeedbackForm({
                          ...feedbackForm,
                          problem_solving_assessment: parseInt(e.target.value),
                        })
                      }
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded p-1.5"
                    >
                      {[1, 2, 3, 4, 5].map((v) => (
                        <option key={v} value={v}>
                          {v} / 5
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] text-slate-600 block">Role Fit</label>
                    <select
                      value={feedbackForm.role_specific_assessment}
                      onChange={(e) =>
                        setFeedbackForm({
                          ...feedbackForm,
                          role_specific_assessment: parseInt(e.target.value),
                        })
                      }
                      className="w-full text-xs bg-slate-50 border border-slate-200 rounded p-1.5"
                    >
                      {[1, 2, 3, 4, 5].map((v) => (
                        <option key={v} value={v}>
                          {v} / 5
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Strengths & Concerns */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Key Strengths
                </label>
                <textarea
                  rows={2}
                  value={feedbackForm.strengths}
                  onChange={(e) => setFeedbackForm({ ...feedbackForm, strengths: e.target.value })}
                  placeholder="Highlights, positive responses, deep domain grasp..."
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Concerns / Flags
                </label>
                <textarea
                  rows={2}
                  value={feedbackForm.concerns}
                  onChange={(e) => setFeedbackForm({ ...feedbackForm, concerns: e.target.value })}
                  placeholder="Areas for improvement, missing competencies..."
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Detailed Notes & Feedback
                </label>
                <textarea
                  rows={3}
                  value={feedbackForm.detailed_feedback}
                  onChange={(e) =>
                    setFeedbackForm({ ...feedbackForm, detailed_feedback: e.target.value })
                  }
                  placeholder="Comprehensive assessment notes for the hiring team..."
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="pt-2">
                <button
                  type="submit"
                  disabled={feedbackSubmitting}
                  className="w-full py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-xs transition-colors flex items-center justify-center space-x-1.5"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>
                    {feedbackSubmitting
                      ? "Submitting..."
                      : myFeedback
                      ? "Update Feedback"
                      : "Submit Interview Feedback"}
                  </span>
                </button>
              </div>
            </form>
          </div>

          {/* Submitted Feedbacks List */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-2">
              <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <FileText className="w-3.5 h-3.5 text-blue-600" />
                <span>All Reviewer Feedbacks ({feedbacks.length})</span>
              </h3>
              <div className="flex items-center space-x-1 text-[10px] text-slate-400">
                <Lock className="w-3 h-3" />
                <span>Private & RBAC-Protected</span>
              </div>
            </div>

            {feedbacks.length === 0 ? (
              <p className="text-xs text-slate-400 italic">No feedback submitted yet.</p>
            ) : (
              <div className="space-y-4">
                {feedbacks.map((fb) => (
                  <div
                    key={fb.id}
                    className="p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 space-y-2 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-800">
                        {fb.reviewer_name || "Authorized Reviewer"}
                      </span>
                      <div className="flex items-center space-x-1">
                        {[1, 2, 3, 4, 5].map((s) => (
                          <Star
                            key={s}
                            className={`w-3.5 h-3.5 ${
                              s <= fb.overall_rating
                                ? "text-amber-500 fill-amber-500"
                                : "text-slate-300"
                            }`}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span
                        className={`px-2 py-0.5 text-[10px] font-bold rounded-full border ${
                          RECOMMENDATIONS.find((r) => r.key === fb.recommendation)?.color ||
                          "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {fb.recommendation.replace("_", " ")}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        Submitted {formatDateTime(fb.submitted_at)}
                      </span>
                    </div>

                    {fb.strengths && (
                      <div>
                        <span className="text-[10px] font-bold text-emerald-700 uppercase">
                          Strengths:
                        </span>
                        <p className="text-slate-700 text-xs mt-0.5">{fb.strengths}</p>
                      </div>
                    )}

                    {fb.concerns && (
                      <div>
                        <span className="text-[10px] font-bold text-rose-700 uppercase">
                          Concerns:
                        </span>
                        <p className="text-slate-700 text-xs mt-0.5">{fb.concerns}</p>
                      </div>
                    )}

                    {fb.detailed_feedback && (
                      <div className="pt-1 border-t border-slate-200/60">
                        <span className="text-[10px] font-bold text-slate-500 uppercase">
                          Comments:
                        </span>
                        <p className="text-slate-700 text-xs mt-0.5 italic">
                          &ldquo;{fb.detailed_feedback}&rdquo;
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Reschedule Modal */}
      {showRescheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900">Reschedule Interview</h3>
              <button
                onClick={() => setShowRescheduleModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {rescheduleConflict && (
              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg text-amber-900 text-xs flex items-start space-x-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{rescheduleConflict}</span>
              </div>
            )}

            <div className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-[11px] text-slate-600 flex items-center justify-between">
              <span>Timezone:</span>
              <span className="font-semibold text-slate-800">
                {rescheduleData.timezone || "Asia/Kolkata"}{" "}
                {(!rescheduleData.timezone || rescheduleData.timezone === "Asia/Kolkata") ? "(IST, UTC+05:30)" : ""}
              </span>
            </div>

            <form onSubmit={handleRescheduleSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  New Date ({rescheduleData.timezone === "Asia/Kolkata" ? "IST" : rescheduleData.timezone}) *
                </label>
                <input
                  type="date"
                  required
                  value={rescheduleData.date}
                  onChange={(e) => setRescheduleData({ ...rescheduleData, date: e.target.value })}
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                    Start Time ({rescheduleData.timezone === "Asia/Kolkata" ? "IST" : rescheduleData.timezone}) *
                  </label>
                  <input
                    type="time"
                    required
                    value={rescheduleData.start_time}
                    onChange={(e) =>
                      setRescheduleData({ ...rescheduleData, start_time: e.target.value })
                    }
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                    End Time ({rescheduleData.timezone === "Asia/Kolkata" ? "IST" : rescheduleData.timezone}) *
                  </label>
                  <input
                    type="time"
                    required
                    value={rescheduleData.end_time}
                    onChange={(e) =>
                      setRescheduleData({ ...rescheduleData, end_time: e.target.value })
                    }
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  Reschedule Reason (Required) *
                </label>
                <input
                  type="text"
                  required
                  value={rescheduleData.reason}
                  onChange={(e) =>
                    setRescheduleData({ ...rescheduleData, reason: e.target.value })
                  }
                  placeholder="e.g. Candidate requested alternate slot"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRescheduleModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rescheduleSubmitting}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg"
                >
                  {rescheduleSubmitting ? "Validating..." : "Confirm Reschedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Cancel Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="text-base font-bold text-slate-900 text-rose-600">Cancel Interview</h3>
              <button
                onClick={() => setShowCancelModal(false)}
                className="p-1 text-slate-400 hover:text-slate-600 rounded-lg"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-500">
              The interview record and audit history will be permanently preserved. A cancellation reason is mandatory.
            </p>

            <form onSubmit={handleCancelSubmit} className="space-y-3">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase mb-1">
                  Cancellation Reason *
                </label>
                <textarea
                  rows={3}
                  required
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="e.g. Candidate withdrew application / Role filled / Scheduling conflict"
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800"
                />
              </div>

              <div className="flex justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCancelModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Keep Interview
                </button>
                <button
                  type="submit"
                  disabled={cancelSubmitting}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 rounded-lg"
                >
                  {cancelSubmitting ? "Cancelling..." : "Confirm Cancellation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Calendar,
  Clock,
  Video,
  MapPin,
  Phone,
  Search,
  Filter,
  Plus,
  Users,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ExternalLink,
  ChevronRight,
  MoreVertical,
  CalendarDays,
  Sparkles,
  UserCheck,
  RefreshCw,
  MessageSquare,
  ShieldAlert,
  ArrowRight,
  AlertTriangle,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Interview,
  InterviewListResponse,
  InterviewStatusCounts,
  InterviewMode,
  InterviewStatus,
  InterviewRoundType,
  ParticipantRole,
} from "@/types";
import { formatDateTime } from "@/lib/utils";
import {
  formatDateIST,
  formatTimeIST,
  formatDateTimeIST,
  formatInterviewTimeRange,
  formatDateForPicker,
  IST_LABEL,
  DEFAULT_TIMEZONE,
} from "@/lib/timezone";

const ROUND_TYPES: { key: InterviewRoundType; label: string }[] = [
  { key: "INITIAL_SCREENING", label: "Initial Screening" },
  { key: "TECHNICAL", label: "Technical Round" },
  { key: "SYSTEM_DESIGN", label: "System Design" },
  { key: "HIRING_MANAGER", label: "Hiring Manager" },
  { key: "HR_BEHAVIORAL", label: "HR / Behavioral" },
  { key: "CULTURE_FIT", label: "Culture Fit" },
  { key: "FINAL_ROUND", label: "Final Round" },
  { key: "OTHER", label: "Other" },
];

const MODES: { key: InterviewMode; label: string }[] = [
  { key: "ONLINE", label: "Online (Video Call)" },
  { key: "IN_PERSON", label: "In-Person (Office)" },
  { key: "PHONE", label: "Phone Call" },
];

const TIMEZONES = [
  "Asia/Kolkata",
  "UTC",
  "America/New_York",
  "America/Los_Angeles",
  "America/Chicago",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Singapore",
  "Asia/Dubai",
  "Australia/Sydney",
];

export default function InterviewsPage() {
  const router = useRouter();

  // Data states
  const [interviews, setInterviews] = useState<Interview[]>([]);
  const [counts, setCounts] = useState<InterviewStatusCounts>({
    total: 0,
    upcoming: 0,
    today: 0,
    completed: 0,
    cancelled: 0,
  });
  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<any[]>([]);
  const [applications, setApplications] = useState<any[]>([]);

  // Filter states
  const [activeTab, setActiveTab] = useState<"all" | "upcoming" | "today" | "completed" | "cancelled">("upcoming");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedMode, setSelectedMode] = useState<string>("ALL");
  const [selectedRoundType, setSelectedRoundType] = useState<string>("ALL");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Scheduling Modal State
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleSubmitting, setScheduleSubmitting] = useState(false);
  const [conflictWarning, setConflictWarning] = useState<string | null>(null);

  const [formData, setFormData] = useState<{
    application_id: string;
    title: string;
    round_name: string;
    round_type: InterviewRoundType;
    interview_mode: InterviewMode;
    date: string;
    start_time: string;
    end_time: string;
    timezone: string;
    meeting_url: string;
    location: string;
    description: string;
    selected_interviewers: string[];
    selected_observers: string[];
  }>({
    application_id: "",
    title: "Technical Interview Round",
    round_name: "Technical Assessment",
    round_type: "TECHNICAL",
    interview_mode: "ONLINE",
    date: formatDateForPicker(new Date(Date.now() + 86400000)),
    start_time: "14:00",
    end_time: "15:00",
    timezone: "Asia/Kolkata",
    meeting_url: "https://meet.google.com/",
    location: "",
    description: "",
    selected_interviewers: [],
    selected_observers: [],
  });

  const fetchData = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      // Build query params
      const params = new URLSearchParams();
      if (activeTab === "upcoming") params.append("upcoming_only", "true");
      else if (activeTab === "today") params.append("today_only", "true");
      else if (activeTab === "completed") params.append("status", "COMPLETED");
      else if (activeTab === "cancelled") params.append("status", "CANCELLED");

      if (selectedMode !== "ALL") params.append("interview_mode", selectedMode);
      if (selectedRoundType !== "ALL") params.append("round_type", selectedRoundType);
      if (searchQuery.trim()) params.append("search", searchQuery.trim());
      params.append("page_size", "50");

      const [listRes, countsRes, membersRes, appsRes] = await Promise.all([
        apiClient<InterviewListResponse>(`/interviews?${params.toString()}`),
        apiClient<InterviewStatusCounts>("/interviews/status-counts").catch(() => ({
          total: 0,
          upcoming: 0,
          today: 0,
          completed: 0,
          cancelled: 0,
        })),
        apiClient<any[]>("/agency/members").catch(() => []),
        apiClient<any>("/applications?page_size=100").catch(() => ({ items: [] })),
      ]);

      setInterviews(listRes.items || []);
      setCounts(countsRes);
      setMembers(membersRes || []);
      setApplications(appsRes.items || []);
    } catch (err: any) {
      setErrorMessage(err.message || "Failed to load interviews.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, selectedMode, selectedRoundType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchData();
  };

  const openScheduleModal = (appId?: string) => {
    setConflictWarning(null);
    setFormData((prev) => ({
      ...prev,
      application_id: appId || (applications[0]?.id || ""),
      selected_interviewers: members.length > 0 ? [members[0].id] : [],
    }));
    setShowScheduleModal(true);
  };

  const handleCreateInterview = async (e: React.FormEvent) => {
    e.preventDefault();
    setConflictWarning(null);
    setErrorMessage(null);

    if (!formData.application_id) {
      setConflictWarning("Please select an active application to schedule this interview.");
      return;
    }

    if (!formData.date || !formData.start_time || !formData.end_time) {
      setConflictWarning("Please specify valid start and end dates/times.");
      return;
    }

    // Build ISO timestamps
    const scheduled_start = `${formData.date}T${formData.start_time}:00`;
    const scheduled_end = `${formData.date}T${formData.end_time}:00`;

    if (scheduled_end <= scheduled_start) {
      setConflictWarning("Scheduled end time must be after scheduled start time.");
      return;
    }

    // Build participants list
    const participants: any[] = [];
    formData.selected_interviewers.forEach((mId) => {
      const mem = members.find((m) => m.id === mId);
      if (mem) {
        participants.push({
          user_id: mem.id,
          participant_name: mem.full_name,
          participant_email: mem.email,
          participant_role: "INTERVIEWER",
        });
      }
    });

    formData.selected_observers.forEach((mId) => {
      const mem = members.find((m) => m.id === mId);
      if (mem && !participants.some((p) => p.user_id === mem.id)) {
        participants.push({
          user_id: mem.id,
          participant_name: mem.full_name,
          participant_email: mem.email,
          participant_role: "OBSERVER",
        });
      }
    });

    const payload = {
      title: formData.title,
      round_name: formData.round_name,
      round_type: formData.round_type,
      interview_mode: formData.interview_mode,
      scheduled_start,
      scheduled_end,
      timezone: formData.timezone,
      meeting_url: formData.interview_mode === "ONLINE" ? formData.meeting_url : null,
      location: formData.interview_mode === "IN_PERSON" ? formData.location : null,
      description: formData.description || null,
      participants,
    };

    setScheduleSubmitting(true);
    try {
      await apiClient(`/applications/${formData.application_id}/interviews`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setShowScheduleModal(false);
      setSuccessMessage("Interview successfully scheduled!");
      fetchData();
      setTimeout(() => setSuccessMessage(null), 4000);
    } catch (err: any) {
      if (err.status === 409 || err.message?.includes("Conflict") || err.message?.includes("overlap")) {
        setConflictWarning(err.message || "Interviewer scheduling conflict detected. Please adjust the timing.");
      } else {
        setConflictWarning(err.message || "Failed to schedule interview.");
      }
    } finally {
      setScheduleSubmitting(false);
    }
  };

  const getStatusBadge = (status: InterviewStatus) => {
    switch (status) {
      case "CONFIRMED":
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">CONFIRMED</span>;
      case "SCHEDULED":
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-blue-100 text-blue-800 border border-blue-200">SCHEDULED</span>;
      case "COMPLETED":
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-slate-100 text-slate-800 border border-slate-300">COMPLETED</span>;
      case "CANCELLED":
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-rose-100 text-rose-800 border border-rose-200">CANCELLED</span>;
      case "RESCHEDULED":
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-amber-100 text-amber-800 border border-amber-200">RESCHEDULED</span>;
      default:
        return <span className="px-2.5 py-0.5 text-[11px] font-bold rounded-full bg-slate-100 text-slate-700">{status}</span>;
    }
  };

  const getModeIcon = (mode: InterviewMode) => {
    switch (mode) {
      case "ONLINE":
        return <Video className="w-3.5 h-3.5 text-blue-600" />;
      case "IN_PERSON":
        return <MapPin className="w-3.5 h-3.5 text-emerald-600" />;
      case "PHONE":
        return <Phone className="w-3.5 h-3.5 text-purple-600" />;
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Interview Workspace</h1>
            <span className="text-xs font-semibold px-2 py-0.5 bg-blue-50 text-blue-700 rounded-md border border-blue-200">
              Phase 6
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Coordinate, schedule, conduct, and evaluate application interviews across all active jobs.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => fetchData()}
            className="p-2 text-slate-600 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
            title="Refresh"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            onClick={() => openScheduleModal()}
            className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Schedule Interview</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-emerald-800 text-xs shadow-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-red-800 text-xs shadow-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Upcoming</span>
            <Clock className="w-4 h-4 text-blue-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1">{counts.upcoming}</p>
          <span className="text-[11px] text-blue-600 font-medium">Scheduled & Confirmed</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Today</span>
            <CalendarDays className="w-4 h-4 text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1">{counts.today}</p>
          <span className="text-[11px] text-amber-600 font-medium">Requires Immediate Action</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Completed</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1">{counts.completed}</p>
          <span className="text-[11px] text-emerald-600 font-medium">Ready for Feedback</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">Total Rounds</span>
            <Calendar className="w-4 h-4 text-purple-600" />
          </div>
          <p className="text-2xl font-bold text-slate-900 mt-1">{counts.total}</p>
          <span className="text-[11px] text-purple-600 font-medium">All Time Interviews</span>
        </div>
      </div>

      {/* Tabs & Filters */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 border-b border-slate-100 pb-3">
          {/* Tab Navigation */}
          <div className="flex items-center space-x-1 overflow-x-auto">
            <button
              onClick={() => setActiveTab("upcoming")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeTab === "upcoming"
                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Upcoming ({counts.upcoming})
            </button>
            <button
              onClick={() => setActiveTab("today")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeTab === "today"
                  ? "bg-amber-50 text-amber-700 border border-amber-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Today ({counts.today})
            </button>
            <button
              onClick={() => setActiveTab("completed")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeTab === "completed"
                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Completed ({counts.completed})
            </button>
            <button
              onClick={() => setActiveTab("cancelled")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeTab === "cancelled"
                  ? "bg-rose-50 text-rose-700 border border-rose-200"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              Cancelled ({counts.cancelled})
            </button>
            <button
              onClick={() => setActiveTab("all")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors whitespace-nowrap ${
                activeTab === "all"
                  ? "bg-slate-100 text-slate-800 font-bold"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              All ({counts.total})
            </button>
          </div>

          {/* Search Box */}
          <form onSubmit={handleSearchSubmit} className="relative min-w-[260px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search candidate, job, interviewer..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </form>
        </div>

        {/* Filter dropdowns */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={selectedMode}
            onChange={(e) => setSelectedMode(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Modes</option>
            <option value="ONLINE">Online (Video)</option>
            <option value="IN_PERSON">In-Person</option>
            <option value="PHONE">Phone Call</option>
          </select>

          <select
            value={selectedRoundType}
            onChange={(e) => setSelectedRoundType(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Round Types</option>
            {ROUND_TYPES.map((r) => (
              <option key={r.key} value={r.key}>
                {r.label}
              </option>
            ))}
          </select>

          {(selectedMode !== "ALL" || selectedRoundType !== "ALL" || searchQuery) && (
            <button
              onClick={() => {
                setSelectedMode("ALL");
                setSelectedRoundType("ALL");
                setSearchQuery("");
                fetchData();
              }}
              className="text-xs text-blue-600 hover:text-blue-800 font-medium underline"
            >
              Reset Filters
            </button>
          )}
        </div>
      </div>

      {/* Interviews List */}
      {loading ? (
        <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center shadow-xs">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-xs text-slate-500">Loading interview rounds...</p>
        </div>
      ) : interviews.length === 0 ? (
        <div className="bg-white rounded-xl border border-slate-200/80 p-12 text-center shadow-xs space-y-3">
          <Calendar className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-800">No interviews found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            {activeTab === "upcoming"
              ? "There are no upcoming interviews scheduled right now. Schedule an interview round for any active candidate."
              : "No interviews match the current filters. Try adjusting your search query or status tab."}
          </p>
          <button
            onClick={() => openScheduleModal()}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Schedule New Interview</span>
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {interviews.map((interview) => (
            <div
              key={interview.id}
              className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-200 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              {/* Left Column: Round & Candidate Info */}
              <div className="space-y-2 min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-xs font-bold text-blue-700 px-2.5 py-0.5 bg-blue-50 rounded-md border border-blue-100">
                    {interview.round_name}
                  </span>
                  <span className="text-[11px] font-medium text-slate-500 px-2 py-0.5 bg-slate-100 rounded-md">
                    {interview.round_type.replace("_", " ")}
                  </span>
                  {getStatusBadge(interview.status)}
                  <span className="flex items-center space-x-1 text-[11px] text-slate-600 px-2 py-0.5 bg-slate-50 rounded border border-slate-200">
                    {getModeIcon(interview.interview_mode)}
                    <span>{interview.interview_mode}</span>
                  </span>
                </div>

                <div>
                  <h3 className="text-base font-semibold text-slate-900 truncate">
                    {interview.title}
                  </h3>
                  <div className="text-xs text-slate-500 flex flex-wrap items-center gap-x-2 gap-y-1 mt-0.5">
                    <span>Candidate:</span>
                    <Link
                      href={`/applications/${interview.application_id}`}
                      className="font-semibold text-slate-800 hover:text-blue-600 hover:underline"
                    >
                      {interview.candidate_name || "Application Candidate"}
                    </Link>
                    <span>•</span>
                    <span>Role:</span>
                    <span className="font-semibold text-slate-800">{interview.job_title || "Designated Job"}</span>
                  </div>
                </div>

                {/* Timing & Location */}
                <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                  <div className="flex items-center space-x-1.5">
                    <Calendar className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-medium text-slate-800">
                      {formatDateIST(interview.scheduled_start, {
                        weekday: "short",
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>

                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    <span className="font-medium text-slate-800">
                      {formatInterviewTimeRange(
                        interview.scheduled_start,
                        interview.scheduled_end,
                        interview.timezone
                      )}
                    </span>
                  </div>

                  {interview.meeting_url && (
                    <a
                      href={interview.meeting_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <Video className="w-3.5 h-3.5" />
                      <span>Join Meeting</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}

                  {interview.location && (
                    <div className="flex items-center space-x-1 text-slate-600">
                      <MapPin className="w-3.5 h-3.5 text-slate-400" />
                      <span>{interview.location}</span>
                    </div>
                  )}
                </div>

                {/* Participants & Feedback Badge */}
                <div className="flex flex-wrap items-center gap-3 pt-1 text-xs">
                  <div className="flex items-center space-x-1.5 text-slate-500">
                    <Users className="w-3.5 h-3.5 text-slate-400" />
                    <span>
                      {interview.participants.length > 0
                        ? interview.participants.map((p) => p.participant_name).join(", ")
                        : "No interviewers assigned"}
                    </span>
                  </div>

                  {interview.feedback_count > 0 && (
                    <span className="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-[11px] font-semibold rounded-full border border-emerald-200">
                      {interview.feedback_count} Feedback Submitted
                    </span>
                  )}
                </div>
              </div>

              {/* Right Column: Actions */}
              <div className="flex md:flex-col items-center md:items-end justify-between gap-2 shrink-0 border-t md:border-t-0 pt-3 md:pt-0">
                <Link
                  href={`/interviews/${interview.id}`}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-300 rounded-lg shadow-xs transition-colors"
                >
                  <span>View & Feedback</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>

                <Link
                  href={`/applications/${interview.application_id}`}
                  className="text-[11px] text-blue-600 hover:text-blue-800 font-medium inline-flex items-center gap-1"
                >
                  <span>Go to Application</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Schedule Interview Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs overflow-y-auto">
          <div className="bg-white rounded-2xl max-w-2xl w-full p-6 shadow-xl border border-slate-200 my-8 space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-lg font-bold text-slate-900">Schedule Interview Round</h2>
                <p className="text-xs text-slate-500">
                  Assign interviewers and configure timing for an active application.
                </p>
              </div>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
              >
                <XCircle className="w-5 h-5" />
              </button>
            </div>

            {conflictWarning && (
              <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start space-x-2.5 text-amber-900 text-xs shadow-xs">
                <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600 mt-0.5" />
                <div>
                  <strong className="block font-semibold">Scheduling Conflict Detected</strong>
                  <span>{conflictWarning}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleCreateInterview} className="space-y-4">
              {/* Application Selector */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Candidate Application *
                </label>
                <select
                  value={formData.application_id}
                  onChange={(e) => setFormData({ ...formData, application_id: e.target.value })}
                  required
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
                >
                  <option value="">Select Candidate Application...</option>
                  {applications.map((app) => (
                    <option key={app.id} value={app.id}>
                      {app.candidate_name || "Candidate"} — {app.job_title || "Job"} ({app.status})
                    </option>
                  ))}
                </select>
              </div>

              {/* Round Details */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Round Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.title}
                    onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                    placeholder="e.g. Round 2: Technical Deep Dive"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Round Type *
                  </label>
                  <select
                    value={formData.round_type}
                    onChange={(e) =>
                      setFormData({ ...formData, round_type: e.target.value as InterviewRoundType })
                    }
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {ROUND_TYPES.map((r) => (
                      <option key={r.key} value={r.key}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Mode & Timezone */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Interview Mode *
                  </label>
                  <select
                    value={formData.interview_mode}
                    onChange={(e) =>
                      setFormData({ ...formData, interview_mode: e.target.value as InterviewMode })
                    }
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {MODES.map((m) => (
                      <option key={m.key} value={m.key}>
                        {m.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Timezone (Default: Asia/Kolkata — IST) *
                  </label>
                  <select
                    value={formData.timezone}
                    onChange={(e) => setFormData({ ...formData, timezone: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  >
                    {TIMEZONES.map((tz) => (
                      <option key={tz} value={tz}>
                        {tz} {tz === "Asia/Kolkata" ? "(IST, UTC+05:30)" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Date & Time */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Interview Date ({formData.timezone === "Asia/Kolkata" ? "IST" : formData.timezone}) *
                  </label>
                  <input
                    type="date"
                    required
                    value={formData.date}
                    onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Start Time ({formData.timezone === "Asia/Kolkata" ? "IST" : formData.timezone}) *
                  </label>
                  <input
                    type="time"
                    required
                    value={formData.start_time}
                    onChange={(e) => setFormData({ ...formData, start_time: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    End Time ({formData.timezone === "Asia/Kolkata" ? "IST" : formData.timezone}) *
                  </label>
                  <input
                    type="time"
                    required
                    value={formData.end_time}
                    onChange={(e) => setFormData({ ...formData, end_time: e.target.value })}
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>

              {/* Meeting Link or Physical Location */}
              {formData.interview_mode === "ONLINE" && (
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Meeting URL (Google Meet, Zoom, Teams)
                  </label>
                  <input
                    type="url"
                    value={formData.meeting_url}
                    onChange={(e) => setFormData({ ...formData, meeting_url: e.target.value })}
                    placeholder="https://meet.google.com/xyz-abcd-efg"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono"
                  />
                </div>
              )}

              {formData.interview_mode === "IN_PERSON" && (
                <div>
                  <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Office Location / Room Address
                  </label>
                  <input
                    type="text"
                    value={formData.location}
                    onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                    placeholder="e.g. Conference Room A, Level 4, Tech Park"
                    className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              )}

              {/* Assigned Interviewers */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Assign Interviewers (Agency Team) *
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto p-2.5 bg-slate-50 border border-slate-200 rounded-lg">
                  {members.map((member) => (
                    <label
                      key={member.id}
                      className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer p-1 rounded hover:bg-slate-100"
                    >
                      <input
                        type="checkbox"
                        checked={formData.selected_interviewers.includes(member.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setFormData({
                              ...formData,
                              selected_interviewers: [...formData.selected_interviewers, member.id],
                            });
                          } else {
                            setFormData({
                              ...formData,
                              selected_interviewers: formData.selected_interviewers.filter(
                                (id) => id !== member.id
                              ),
                            });
                          }
                        }}
                        className="rounded text-blue-600 focus:ring-blue-500"
                      />
                      <span>
                        {member.full_name} ({member.role})
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Notes / Description */}
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Interview Notes / Candidate Instructions (Optional)
                </label>
                <textarea
                  rows={2}
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Focus areas, coding exercise guidelines, or instructions for the candidate..."
                  className="w-full text-xs bg-slate-50 border border-slate-300 rounded-lg p-2.5 text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Form Buttons */}
              <div className="flex justify-end space-x-2 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowScheduleModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={scheduleSubmitting}
                  className="px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg shadow-xs transition-colors flex items-center space-x-1"
                >
                  <span>{scheduleSubmitting ? "Checking Conflicts & Scheduling..." : "Confirm & Schedule"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

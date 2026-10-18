"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Kanban,
  Search,
  Filter,
  User,
  Briefcase,
  Clock,
  Sparkles,
  ChevronRight,
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ExternalLink,
  GitCompare,
  SlidersHorizontal,
  ShieldAlert,
  HelpCircle,
  X,
  Calendar,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Job,
  Application,
  ApplicationListResponse,
  PipelineStageType,
} from "@/types";
import { formatDateTime } from "@/lib/utils";
import { formatDateIST } from "@/lib/timezone";

const STAGES: {
  key: PipelineStageType;
  title: string;
  color: string;
  bg: string;
  border: string;
  badge: string;
}[] = [
  {
    key: "APPLIED",
    title: "Applied",
    color: "text-blue-700",
    bg: "bg-blue-50/50",
    border: "border-blue-200/80",
    badge: "bg-blue-100 text-blue-800",
  },
  {
    key: "UNDER_REVIEW",
    title: "Under Review",
    color: "text-indigo-700",
    bg: "bg-indigo-50/50",
    border: "border-indigo-200/80",
    badge: "bg-indigo-100 text-indigo-800",
  },
  {
    key: "SHORTLISTED",
    title: "Shortlisted",
    color: "text-purple-700",
    bg: "bg-purple-50/50",
    border: "border-purple-200/80",
    badge: "bg-purple-100 text-purple-800",
  },
  {
    key: "INTERVIEW",
    title: "Interview",
    color: "text-amber-700",
    bg: "bg-amber-50/50",
    border: "border-amber-200/80",
    badge: "bg-amber-100 text-amber-800",
  },
  {
    key: "SELECTED",
    title: "Selected",
    color: "text-emerald-700",
    bg: "bg-emerald-50/50",
    border: "border-emerald-200/80",
    badge: "bg-emerald-100 text-emerald-800",
  },
  {
    key: "ON_HOLD",
    title: "On Hold",
    color: "text-orange-700",
    bg: "bg-orange-50/50",
    border: "border-orange-200/80",
    badge: "bg-orange-100 text-orange-800",
  },
  {
    key: "REJECTED",
    title: "Rejected",
    color: "text-rose-700",
    bg: "bg-rose-50/50",
    border: "border-rose-200/80",
    badge: "bg-rose-100 text-rose-800",
  },
  {
    key: "WITHDRAWN",
    title: "Withdrawn",
    color: "text-slate-600",
    bg: "bg-slate-50/70",
    border: "border-slate-200",
    badge: "bg-slate-200 text-slate-700",
  },
];

export default function JobPipelineKanbanPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [stageCounts, setStageCounts] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [recruiterFilter, setRecruiterFilter] = useState("ALL");
  const [draggingAppId, setDraggingAppId] = useState<string | null>(null);
  const [dragOverStage, setDragOverStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  // Transition modal state
  const [transitionModalApp, setTransitionModalApp] = useState<{
    app: Application;
    targetStage: PipelineStageType;
  } | null>(null);
  const [transitionReason, setTransitionReason] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  const fetchPipelineData = async () => {
    try {
      const [jobData, appData]: [Job, ApplicationListResponse] = await Promise.all([
        apiClient<Job>(`/jobs/${jobId}`),
        apiClient<ApplicationListResponse>(`/jobs/${jobId}/applications?limit=100`),
      ]);
      setJob(jobData);
      setApplications(appData.items);
      setStageCounts(appData.stage_counts || {});
    } catch (err: any) {
      setError(err.message || "Failed to load pipeline applications.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchPipelineData();
    }
  }, [jobId]);

  // Recruiter options from current applications
  const recruiterOptions = useMemo(() => {
    const map = new Map<string, string>();
    applications.forEach((a) => {
      if (a.assigned_recruiter_id && a.assigned_recruiter_name) {
        map.set(a.assigned_recruiter_id, a.assigned_recruiter_name);
      }
    });
    return Array.from(map.entries());
  }, [applications]);

  // Filter applications
  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const nameMatch = app.candidate_name?.toLowerCase().includes(q);
        const titleMatch = app.candidate_title?.toLowerCase().includes(q);
        const emailMatch = app.candidate_email?.toLowerCase().includes(q);
        if (!nameMatch && !titleMatch && !emailMatch) return false;
      }
      if (recruiterFilter !== "ALL") {
        if (app.assigned_recruiter_id !== recruiterFilter) return false;
      }
      return true;
    });
  }, [applications, searchQuery, recruiterFilter]);

  // Group applications by stage
  const appsByStage = useMemo(() => {
    const record: Record<PipelineStageType, Application[]> = {
      APPLIED: [],
      UNDER_REVIEW: [],
      SHORTLISTED: [],
      INTERVIEW: [],
      SELECTED: [],
      ON_HOLD: [],
      REJECTED: [],
      WITHDRAWN: [],
    };
    filteredApps.forEach((a) => {
      if (record[a.status]) {
        record[a.status].push(a);
      }
    });
    return record;
  }, [filteredApps]);

  const executeStageTransition = async (
    appId: string,
    targetStage: PipelineStageType,
    reason?: string
  ) => {
    const currentApp = applications.find((a) => a.id === appId);
    if (!currentApp || currentApp.status === targetStage) return;

    const previousStage = currentApp.status;
    setError(null);

    // Optimistic UI update
    setApplications((prev) =>
      prev.map((item) =>
        item.id === appId
          ? {
              ...item,
              status: targetStage,
              shortlisted_at:
                targetStage === "SHORTLISTED"
                  ? new Date().toISOString()
                  : item.shortlisted_at,
              last_activity_at: new Date().toISOString(),
            }
          : item
      )
    );

    try {
      const updatedApp = await apiClient<Application>(
        `/applications/${appId}/transition`,
        {
          method: "POST",
          body: JSON.stringify({
            new_stage: targetStage,
            reason: reason || undefined,
          }),
        }
      );
      // Replace with confirmed backend payload
      setApplications((prev) =>
        prev.map((item) => (item.id === appId ? updatedApp : item))
      );
      setSuccessToast(
        `${currentApp.candidate_name} moved to ${targetStage.replace("_", " ")}.`
      );
      setTimeout(() => setSuccessToast(null), 4000);
    } catch (err: any) {
      // Rollback on failure
      setApplications((prev) =>
        prev.map((item) =>
          item.id === appId ? { ...item, status: previousStage } : item
        )
      );
      setError(err.message || "Failed to update pipeline stage. Rolled back.");
    }
  };

  // Drag and Drop handlers
  const handleDragStart = (e: React.DragEvent, appId: string) => {
    e.dataTransfer.setData("text/plain", appId);
    setDraggingAppId(appId);
  };

  const handleDragOver = (e: React.DragEvent, stageKey: string) => {
    e.preventDefault();
    setDragOverStage(stageKey);
  };

  const handleDragLeave = (stageKey: string) => {
    if (dragOverStage === stageKey) {
      setDragOverStage(null);
    }
  };

  const handleDrop = async (e: React.DragEvent, targetStage: PipelineStageType) => {
    e.preventDefault();
    setDragOverStage(null);
    const appId = e.dataTransfer.getData("text/plain") || draggingAppId;
    setDraggingAppId(null);
    if (!appId) return;

    const app = applications.find((a) => a.id === appId);
    if (!app || app.status === targetStage) return;

    // Prompt optional note/reason modal for critical stages like REJECTED or ON_HOLD
    if (targetStage === "REJECTED" || targetStage === "ON_HOLD" || targetStage === "WITHDRAWN") {
      setTransitionModalApp({ app, targetStage });
      setTransitionReason("");
    } else {
      await executeStageTransition(appId, targetStage);
    }
  };

  const handleConfirmModalTransition = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!transitionModalApp) return;
    setTransitioning(true);
    try {
      await executeStageTransition(
        transitionModalApp.app.id,
        transitionModalApp.targetStage,
        transitionReason.trim() || undefined
      );
      setTransitionModalApp(null);
    } finally {
      setTransitioning(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-500 space-y-3">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs font-medium">Loading recruitment workspace pipeline...</span>
      </div>
    );
  }

  return (
    <div className="space-y-5 max-w-[100vw] overflow-x-hidden">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Job: {job?.title || "Job Details"}</span>
        </Link>

        <div className="flex items-center space-x-2">
          <Link
            href={`/jobs/${jobId}/matches`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Matches</span>
          </Link>

          <Link
            href={`/jobs/${jobId}/compare`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 rounded-lg transition-colors border border-slate-300 shadow-xs"
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Compare Candidates</span>
          </Link>
        </div>
      </div>

      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
              <Kanban className="w-3 h-3" />
              Recruitment Pipeline
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {job?.title} ({job?.department || "General"})
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Application Pipeline Kanban
          </h1>
          <p className="text-xs text-slate-500">
            Real-time stage transitions with audit history, evidence scores, and tenant isolation.
          </p>
        </div>

        {/* Total Active Counter */}
        <div className="flex items-center space-x-3 shrink-0">
          <div className="bg-slate-50 border border-slate-200 px-4 py-2 rounded-xl text-center">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Total Applications
            </span>
            <span className="text-xl font-black text-slate-900">
              {applications.length}
            </span>
          </div>

          <button
            onClick={fetchPipelineData}
            title="Refresh pipeline"
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-red-800 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}
      {successToast && (
        <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center space-x-2 text-emerald-800 text-xs shadow-xs animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
          <span>{successToast}</span>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-3.5 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search candidates or titles..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-slate-800 placeholder-slate-400"
          />
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
            <Filter className="w-3.5 h-3.5" />
            <span>Assigned Recruiter:</span>
          </div>
          <select
            value={recruiterFilter}
            onChange={(e) => setRecruiterFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Recruiters</option>
            {recruiterOptions.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* 8-Column Horizontal Kanban Board */}
      <div className="overflow-x-auto pb-6">
        <div className="flex gap-4 min-w-[1700px]">
          {STAGES.map((col) => {
            const stageApps = appsByStage[col.key] || [];
            const isOver = dragOverStage === col.key;

            return (
              <div
                key={col.key}
                onDragOver={(e) => handleDragOver(e, col.key)}
                onDragLeave={() => handleDragLeave(col.key)}
                onDrop={(e) => handleDrop(e, col.key)}
                className={`w-[210px] shrink-0 rounded-xl border flex flex-col transition-all ${
                  col.border
                } ${col.bg} ${
                  isOver ? "ring-2 ring-blue-500 ring-offset-2 bg-blue-50/80" : ""
                }`}
              >
                {/* Column Header */}
                <div className="p-3 border-b border-slate-200/70 flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className={`text-xs font-bold uppercase tracking-wider ${col.color}`}>
                      {col.title}
                    </span>
                    <span className={`text-[11px] font-bold px-1.5 py-0.2 rounded-full ${col.badge}`}>
                      {stageApps.length}
                    </span>
                  </div>
                </div>

                {/* Card Container */}
                <div className="p-2 flex-1 space-y-2.5 min-h-[480px]">
                  {stageApps.length === 0 ? (
                    <div className="h-32 border border-dashed border-slate-200 rounded-lg flex items-center justify-center p-3 text-center">
                      <span className="text-[11px] text-slate-400">
                        Drop candidate here
                      </span>
                    </div>
                  ) : (
                    stageApps.map((app) => (
                      <div
                        key={app.id}
                        draggable
                        onDragStart={(e) => handleDragStart(e, app.id)}
                        className={`bg-white rounded-lg border border-slate-200/90 p-3 shadow-xs hover:border-blue-400 hover:shadow-sm transition-all cursor-grab active:cursor-grabbing space-y-2.5 ${
                          draggingAppId === app.id ? "opacity-40" : ""
                        }`}
                      >
                        {/* Header: Candidate Name & Link */}
                        <div className="flex items-start justify-between gap-1">
                          <Link
                            href={`/applications/${app.id}`}
                            className="text-xs font-bold text-slate-900 hover:text-blue-600 transition-colors leading-tight"
                          >
                            {app.candidate_name || "Candidate"}
                          </Link>
                          <Link
                            href={`/applications/${app.id}`}
                            title="View application"
                            className="text-slate-400 hover:text-slate-600 shrink-0"
                          >
                            <ExternalLink className="w-3 h-3" />
                          </Link>
                        </div>

                        {/* Title & Experience */}
                        <div className="space-y-0.5 text-[11px] text-slate-500">
                          {app.candidate_title && (
                            <p className="truncate font-medium text-slate-700">
                              {app.candidate_title}
                            </p>
                          )}
                          <p>
                            {app.total_experience_months
                              ? `${Math.floor(app.total_experience_months / 12)}y exp`
                              : "Experience not specified"}
                          </p>
                        </div>

                        {/* Phase 4 Match Score Badge */}
                        {app.latest_match_score !== null && app.latest_match_score !== undefined && (
                          <div className="pt-1 border-t border-slate-100 flex items-center justify-between">
                            <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                              <Sparkles className="w-3 h-3 text-blue-500" />
                              Match
                            </span>
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                app.latest_match_score >= 75
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                  : app.latest_match_score >= 50
                                  ? "bg-blue-50 text-blue-700 border border-blue-200"
                                  : "bg-amber-50 text-amber-700 border border-amber-200"
                              }`}
                            >
                              {Math.round(app.latest_match_score)}%
                              {app.is_stale_match && " (stale)"}
                            </span>
                          </div>
                        )}

                        {/* Recruiter & Date */}
                        <div className="text-[10px] text-slate-400 flex items-center justify-between pt-1 border-t border-slate-100">
                          <span className="truncate max-w-[100px]" title={app.assigned_recruiter_name || "Unassigned"}>
                            {app.assigned_recruiter_name || "Unassigned"}
                          </span>
                          <span>{app.applied_at ? formatDateIST(app.applied_at) : ""}</span>
                        </div>

                        {/* Phase 6 Interview Badge for Interview Stage */}
                        {col.key === "INTERVIEW" && (
                          <div className="pt-1 border-t border-slate-100">
                            <Link
                              href={`/applications/${app.id}`}
                              className="text-[10px] text-amber-800 bg-amber-50 hover:bg-amber-100 px-2 py-0.5 rounded border border-amber-200 flex items-center justify-between font-semibold transition-colors"
                            >
                              <span className="flex items-center gap-1">
                                <Calendar className="w-3 h-3 text-amber-600" />
                                <span>Interview Workspace</span>
                              </span>
                              <ChevronRight className="w-3 h-3" />
                            </Link>
                          </div>
                        )}

                        {/* Accessibility: Stage Select Dropdown Alternative */}
                        <div className="pt-1 border-t border-slate-100 flex items-center justify-between gap-1">
                          <span className="text-[9px] uppercase font-bold text-slate-400">Move:</span>
                          <select
                            value={app.status}
                            onChange={(e) => {
                              const target = e.target.value as PipelineStageType;
                              if (target === app.status) return;
                              if (
                                target === "REJECTED" ||
                                target === "ON_HOLD" ||
                                target === "WITHDRAWN"
                              ) {
                                setTransitionModalApp({ app, targetStage: target });
                                setTransitionReason("");
                              } else {
                                executeStageTransition(app.id, target);
                              }
                            }}
                            className="text-[10px] bg-slate-50 border border-slate-200 rounded px-1 py-0.5 text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500"
                            aria-label={`Change stage for ${app.candidate_name}`}
                          >
                            {STAGES.map((s) => (
                              <option key={s.key} value={s.key}>
                                {s.title}
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Transition Reason Modal */}
      {transitionModalApp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Confirm Stage Transition
              </h3>
              <button
                onClick={() => setTransitionModalApp(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Moving <span className="font-semibold text-slate-800">{transitionModalApp.app.candidate_name}</span> to{" "}
              <span className="font-bold text-blue-700">{transitionModalApp.targetStage.replace("_", " ")}</span>.
              Please provide an optional note or reason for the audit trail.
            </p>

            <form onSubmit={handleConfirmModalTransition} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Reason / Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  value={transitionReason}
                  onChange={(e) => setTransitionReason(e.target.value)}
                  placeholder="e.g., Candidate requested salary above range / on hold pending hiring freeze..."
                  className="w-full text-xs p-2.5 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-800"
                ></textarea>
              </div>

              <div className="flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setTransitionModalApp(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={transitioning}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs disabled:opacity-50"
                >
                  {transitioning ? "Updating..." : "Confirm Stage Move"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

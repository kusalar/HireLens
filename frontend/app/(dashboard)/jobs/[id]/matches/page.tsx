"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Sparkles,
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Clock,
  ChevronRight,
  RefreshCw,
  ExternalLink,
  ShieldAlert,
  SlidersHorizontal,
  FileText,
  User,
  Layers,
  Award,
  Kanban,
  GitCompare,
  UserPlus,
  X,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Job,
  JobMatchResult,
  JobMatchRun,
  JobMatchListResponse,
  Application,
  ApplicationListResponse,
  PipelineStageType,
} from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function JobMatchesPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [matchData, setMatchData] = useState<JobMatchListResponse | null>(null);
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [matchingRunning, setMatchingRunning] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [minScoreFilter, setMinScoreFilter] = useState<number | "ALL">("ALL");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Add to pipeline modal state
  const [modalCandidate, setModalCandidate] = useState<JobMatchResult | null>(null);
  const [modalStage, setModalStage] = useState<PipelineStageType>("APPLIED");
  const [modalNote, setModalNote] = useState("");
  const [submittingApp, setSubmittingApp] = useState(false);

  const fetchJobAndMatches = async () => {
    setLoading(true);
    try {
      const [jobRes, matchesRes, appsRes] = await Promise.all([
        apiClient<Job>(`/jobs/${jobId}`),
        apiClient<JobMatchListResponse>(`/jobs/${jobId}/matches?limit=100`),
        apiClient<ApplicationListResponse>(`/jobs/${jobId}/applications?limit=100`).catch(() => ({
          items: [],
          total: 0,
          stage_counts: {} as any,
        })),
      ]);
      setJob(jobRes);
      setMatchData(matchesRes);
      setApplications(appsRes.items || []);
    } catch (err: any) {
      setError(err.message || "Failed to load matching candidates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchJobAndMatches();
    }
  }, [jobId]);

  const handleStartMatching = async () => {
    setMatchingRunning(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const run: JobMatchRun = await apiClient<JobMatchRun>(`/jobs/${jobId}/match`, {
        method: "POST",
      });
      setSuccessMessage(
        `Matching run completed: ${run.completed_count} candidate(s) scored in ${
          run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : "<1s"
        }.`
      );
      const matchesRes = await apiClient<JobMatchListResponse>(`/jobs/${jobId}/matches?limit=100`);
      setMatchData(matchesRes);
    } catch (err: any) {
      setError(err.message || "Failed to execute matching run.");
    } finally {
      setMatchingRunning(false);
    }
  };

  const handleCreateApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalCandidate) return;
    setSubmittingApp(true);
    setError(null);
    try {
      const newApp = await apiClient<Application>(`/jobs/${jobId}/applications`, {
        method: "POST",
        body: JSON.stringify({
          candidate_id: modalCandidate.candidate_id,
          status: modalStage,
          source: "MATCHING_ENGINE",
          initial_note: modalNote.trim() || undefined,
        }),
      });
      setApplications((prev) => [...prev, newApp]);
      setSuccessMessage(
        `Application created for ${modalCandidate.candidate_name} in stage '${modalStage.replace("_", " ")}'.`
      );
      setModalCandidate(null);
      setModalNote("");
    } catch (err: any) {
      setError(err.message || "Failed to create application for candidate.");
    } finally {
      setSubmittingApp(false);
    }
  };

  const applicationsByCandidateId = useMemo(() => {
    const map = new Map<string, Application>();
    applications.forEach((a) => {
      map.set(a.candidate_id, a);
    });
    return map;
  }, [applications]);

  const filteredMatches = useMemo(() => {
    if (!matchData?.items) return [];
    return matchData.items.filter((item) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const nameMatch = item.candidate_name?.toLowerCase().includes(q);
        const titleMatch = item.candidate_title?.toLowerCase().includes(q);
        const expMatch = item.explanation?.toLowerCase().includes(q);
        if (!nameMatch && !titleMatch && !expMatch) return false;
      }
      if (minScoreFilter !== "ALL") {
        if (item.overall_score < minScoreFilter) return false;
      }
      return true;
    });
  }, [matchData, searchQuery, minScoreFilter]);

  const getAlignmentBadge = (score: number) => {
    if (score >= 75) {
      return {
        label: "Strong Evidence Alignment",
        bg: "bg-emerald-50 text-emerald-800 border-emerald-200",
        barBg: "bg-emerald-500",
      };
    } else if (score >= 50) {
      return {
        label: "Partial Evidence Alignment",
        bg: "bg-blue-50 text-blue-800 border-blue-200",
        barBg: "bg-blue-500",
      };
    } else {
      return {
        label: "Additional Verification Needed",
        bg: "bg-amber-50 text-amber-800 border-amber-200",
        barBg: "bg-amber-500",
      };
    }
  };

  return (
    <div className="max-w-6xl space-y-6">
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
            href={`/jobs/${jobId}/pipeline`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
          >
            <Kanban className="w-3.5 h-3.5" />
            <span>Pipeline Kanban</span>
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
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="space-y-1.5">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              Matching Intelligence
            </span>
            {matchData?.latest_run && (
              <span className="text-xs text-slate-500 flex items-center gap-1 font-mono">
                <Clock className="w-3 h-3" />
                Last run: {formatDateTime(matchData.latest_run.created_at)}
              </span>
            )}
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Candidate Matching & Explainable Scoring
          </h1>
          <p className="text-xs text-slate-500 max-w-2xl">
            Deterministic scoring across required skills, experience, preferred criteria, and projects.
            HireLens is recruiter-assistance software — scores reflect documented evidence alignment, not automatic hiring decisions.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={handleStartMatching}
            disabled={matchingRunning}
            className="inline-flex items-center space-x-2 px-4 py-2.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 rounded-lg shadow-xs transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${matchingRunning ? "animate-spin" : ""}`} />
            <span>{matchingRunning ? "Evaluating Candidates..." : "Run Matching Engine"}</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-start space-x-3 text-red-800 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-600" />
          <span>{error}</span>
        </div>
      )}
      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-start space-x-3 text-emerald-800 text-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0 mt-0.5 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search candidates, titles, or evidence..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:bg-white transition-all text-slate-800 placeholder-slate-400"
          />
        </div>

        <div className="flex items-center space-x-3 w-full sm:w-auto">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500">
            <Filter className="w-3.5 h-3.5" />
            <span>Score threshold:</span>
          </div>
          <select
            value={minScoreFilter}
            onChange={(e) => setMinScoreFilter(e.target.value === "ALL" ? "ALL" : Number(e.target.value))}
            className="text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="ALL">All Candidates ({matchData?.items?.length || 0})</option>
            <option value={75}>Strong Alignment (75%+)</option>
            <option value={50}>Moderate Alignment (50%+)</option>
            <option value={25}>Initial Evidence (25%+)</option>
          </select>
        </div>
      </div>

      {/* Candidates Match List */}
      {loading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500 space-y-2">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs font-medium">Loading match results...</span>
        </div>
      ) : filteredMatches.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-3">
          <Layers className="w-10 h-10 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-800">No matching candidate records found</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {matchData?.items?.length === 0
              ? "Run the matching engine above to discover candidate evidence alignment for this role."
              : "Try adjusting your search criteria or score threshold filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredMatches.map((res) => {
            const badge = getAlignmentBadge(res.overall_score);
            const existingApp = applicationsByCandidateId.get(res.candidate_id);

            return (
              <div
                key={res.id}
                className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-300 transition-all space-y-4"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        href={`/candidates/${res.candidate_id}`}
                        className="text-base font-bold text-slate-900 hover:text-blue-600 transition-colors"
                      >
                        {res.candidate_name || "Candidate"}
                      </Link>
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badge.bg}`}>
                        {badge.label}
                      </span>
                      {existingApp && (
                        <Link
                          href={`/applications/${existingApp.id}`}
                          className="text-[11px] font-bold px-2 py-0.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 inline-flex items-center gap-1 transition-colors"
                        >
                          <span>Pipeline: {existingApp.status.replace("_", " ")}</span>
                          <ExternalLink className="w-2.5 h-2.5" />
                        </Link>
                      )}
                    </div>
                    <div className="text-xs text-slate-500 flex flex-wrap gap-x-3 gap-y-1">
                      {res.candidate_title && <span>{res.candidate_title}</span>}
                      {res.candidate_location && <span>• {res.candidate_location}</span>}
                      {res.candidate_email && <span>• {res.candidate_email}</span>}
                    </div>
                  </div>

                  {/* Score Indicator & Actions */}
                  <div className="flex items-center space-x-3 shrink-0">
                    <div className="text-right">
                      <div className="text-2xl font-black text-slate-900 tracking-tight">
                        {Math.round(res.overall_score)}
                        <span className="text-xs font-normal text-slate-400">/100</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">
                        v{res.scoring_version}
                      </div>
                    </div>

                    {!existingApp ? (
                      <button
                        onClick={() => {
                          setModalCandidate(res);
                          setModalStage(res.overall_score >= 70 ? "SHORTLISTED" : "APPLIED");
                          setModalNote("");
                        }}
                        className="inline-flex items-center space-x-1 px-3 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
                      >
                        <UserPlus className="w-3.5 h-3.5" />
                        <span>Add to Pipeline</span>
                      </button>
                    ) : (
                      <Link
                        href={`/applications/${existingApp.id}`}
                        className="inline-flex items-center space-x-1 px-3 py-2 text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-lg transition-colors"
                      >
                        <span>View Application</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </Link>
                    )}

                    <Link
                      href={`/jobs/${jobId}/matches/${res.candidate_id}`}
                      className="inline-flex items-center space-x-1 px-3 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-100"
                    >
                      <span>Evidence Breakdown</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </div>

                {/* Score Progress Breakdown */}
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-2 border-t border-slate-100">
                  <div className="p-2 bg-slate-50/70 rounded-lg">
                    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                      Req Skills (40%)
                    </div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {Math.round(res.required_skills_score)}%
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50/70 rounded-lg">
                    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                      Experience (25%)
                    </div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {Math.round(res.experience_score)}%
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50/70 rounded-lg">
                    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                      Pref Skills (15%)
                    </div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {Math.round(res.preferred_skills_score)}%
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50/70 rounded-lg">
                    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                      Projects (10%)
                    </div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {Math.round(res.project_relevance_score)}%
                    </div>
                  </div>
                  <div className="p-2 bg-slate-50/70 rounded-lg">
                    <div className="text-[10px] font-medium text-slate-500 uppercase tracking-wider">
                      Other (10%)
                    </div>
                    <div className="text-xs font-bold text-slate-800 mt-0.5">
                      {Math.round(res.other_criteria_score)}%
                    </div>
                  </div>
                </div>

                {/* Requirement Counts Summary */}
                <div className="flex flex-wrap items-center gap-3 text-xs pt-1">
                  <span className="flex items-center text-emerald-700 gap-1 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    {res.matched_requirements_count} Demonstrated
                  </span>
                  {res.partial_requirements_count > 0 && (
                    <span className="flex items-center text-blue-700 gap-1 font-medium">
                      <HelpCircle className="w-3.5 h-3.5 text-blue-600" />
                      {res.partial_requirements_count} Partial
                    </span>
                  )}
                  {res.needs_verification_count > 0 && (
                    <span className="flex items-center text-amber-700 gap-1 font-medium">
                      <ShieldAlert className="w-3.5 h-3.5 text-amber-600" />
                      {res.needs_verification_count} Needs Verification
                    </span>
                  )}
                  {res.missing_requirements_count > 0 && (
                    <span className="flex items-center text-slate-500 gap-1">
                      <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
                      {res.missing_requirements_count} Missing Evidence
                    </span>
                  )}
                </div>

                {/* AI Grounded Explanation Snippet */}
                {res.explanation && (
                  <div className="p-3 bg-slate-50 rounded-lg text-xs text-slate-700 border border-slate-100 italic">
                    &ldquo;{res.explanation}&rdquo;
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Add to Pipeline Modal */}
      {modalCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">
                Create Job Application
              </h3>
              <button
                onClick={() => setModalCandidate(null)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600">
              Create an application for <strong className="text-slate-800">{modalCandidate.candidate_name}</strong> for position <strong className="text-slate-800">{job?.title}</strong>.
              Match Score: <span className="font-bold text-blue-600">{Math.round(modalCandidate.overall_score)}/100</span>.
            </p>

            <form onSubmit={handleCreateApplication} className="space-y-4">
              <div>
                <label className="block text-[11px] font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Choose Initial Pipeline Stage
                </label>
                <select
                  value={modalStage}
                  onChange={(e) => setModalStage(e.target.value as PipelineStageType)}
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="APPLIED">APPLIED (General Application)</option>
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
                  placeholder="e.g., Sourced via deterministic matching engine with 80% evidence match..."
                  className="w-full text-xs p-2 bg-slate-50 border border-slate-300 rounded-lg text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                ></textarea>
              </div>

              <div className="flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setModalCandidate(null)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingApp}
                  className="px-4 py-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs disabled:opacity-50"
                >
                  {submittingApp ? "Adding..." : "Add to Pipeline"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

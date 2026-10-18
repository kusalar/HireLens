"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  GitCompare,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldAlert,
  Clock,
  Layers,
  ChevronRight,
  ExternalLink,
  BookOpen,
  Filter,
  Check,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  Job,
  CandidateComparisonResponse,
  CandidateComparisonItem,
  ApplicationListResponse,
} from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function CandidateComparisonPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [comparisonData, setComparisonData] = useState<CandidateComparisonResponse | null>(null);
  const [allAvailableCandidates, setAllAvailableCandidates] = useState<Array<{ id: string; name: string; title?: string }>>([]);
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [evaluating, setEvaluating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInitialData = async () => {
    setLoading(true);
    try {
      const [jobData, appsData]: [Job, ApplicationListResponse] = await Promise.all([
        apiClient<Job>(`/jobs/${jobId}`),
        apiClient<ApplicationListResponse>(`/jobs/${jobId}/applications?limit=100`),
      ]);
      setJob(jobData);

      const candidateList = appsData.items.map((a) => ({
        id: a.candidate_id,
        name: a.candidate_name || "Candidate",
        title: a.candidate_title,
      }));
      setAllAvailableCandidates(candidateList);

      // Check query param candidate_ids or default to first 3
      const paramCandIds = searchParams.get("candidates")?.split(",").filter(Boolean);
      const initialIds = paramCandIds && paramCandIds.length > 0
        ? paramCandIds
        : candidateList.slice(0, 3).map((c) => c.id);

      setSelectedCandidateIds(initialIds);

      if (initialIds.length > 0) {
        await executeComparison(initialIds);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load candidate comparison data.");
    } finally {
      setLoading(false);
    }
  };

  const executeComparison = async (candIds: string[]) => {
    if (candIds.length === 0) {
      setComparisonData(null);
      return;
    }
    setEvaluating(true);
    setError(null);
    try {
      const compRes: CandidateComparisonResponse = await apiClient<CandidateComparisonResponse>(
        `/jobs/${jobId}/compare`,
        {
          method: "POST",
          body: JSON.stringify({ candidate_ids: candIds }),
        }
      );
      setComparisonData(compRes);
    } catch (err: any) {
      setError(err.message || "Failed to evaluate candidate comparison.");
    } finally {
      setEvaluating(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchInitialData();
    }
  }, [jobId]);

  const toggleCandidateSelection = (candId: string) => {
    let updated: string[];
    if (selectedCandidateIds.includes(candId)) {
      if (selectedCandidateIds.length <= 1) return; // Keep at least one
      updated = selectedCandidateIds.filter((id) => id !== candId);
    } else {
      if (selectedCandidateIds.length >= 4) {
        alert("You can compare up to 4 candidates side-by-side.");
        return;
      }
      updated = [...selectedCandidateIds, candId];
    }
    setSelectedCandidateIds(updated);
    executeComparison(updated);
  };

  const getEvidenceBadge = (status: string) => {
    switch (status) {
      case "DEMONSTRATED":
        return {
          label: "Demonstrated",
          cls: "bg-emerald-50 text-emerald-800 border-emerald-200",
          icon: CheckCircle2,
        };
      case "PARTIAL":
        return {
          label: "Partial",
          cls: "bg-blue-50 text-blue-800 border-blue-200",
          icon: HelpCircle,
        };
      case "NEEDS_VERIFICATION":
        return {
          label: "Verify",
          cls: "bg-amber-50 text-amber-800 border-amber-200",
          icon: ShieldAlert,
        };
      default:
        return {
          label: "Missing",
          cls: "bg-slate-100 text-slate-600 border-slate-200",
          icon: AlertCircle,
        };
    }
  };

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-500 space-y-3">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs font-medium">Loading candidate comparison workspace...</span>
      </div>
    );
  }

  const candidates = comparisonData?.candidates || [];
  const criteriaMatrix = comparisonData?.criteria_matrix || [];

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Navigation Breadcrumb */}
      <div className="flex items-center justify-between">
        <Link
          href={`/jobs/${jobId}/pipeline`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Kanban Pipeline</span>
        </Link>

        <div className="flex items-center space-x-2">
          <Link
            href={`/jobs/${jobId}/matches`}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-200"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Matches</span>
          </Link>
        </div>
      </div>

      {/* Header Banner */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
              <GitCompare className="w-3 h-3" />
              Side-by-Side Comparison
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Job: {job?.title}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Candidate Evidence & Dimension Comparison
          </h1>
          <p className="text-xs text-slate-500 max-w-3xl">
            Compare overall evidence alignment, individual scoring dimensions, demonstrated strengths,
            missing evidence, and job requirement fulfillment. HireLens provides assistive intelligence;
            the highest score does not automatically represent the best hire.
          </p>
        </div>
      </div>

      {/* Candidate Selector Bar */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-500" />
            Select Candidates to Compare (Max 4):
          </span>
          <span className="text-xs text-slate-400 font-medium">
            {selectedCandidateIds.length} candidate(s) selected
          </span>
        </div>

        {allAvailableCandidates.length === 0 ? (
          <p className="text-xs text-slate-400 italic">
            No candidate applications available yet for this position.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {allAvailableCandidates.map((cand) => {
              const isSelected = selectedCandidateIds.includes(cand.id);
              return (
                <button
                  key={cand.id}
                  onClick={() => toggleCandidateSelection(cand.id)}
                  className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    isSelected
                      ? "bg-blue-600 text-white border-blue-600 shadow-xs"
                      : "bg-slate-50 text-slate-700 border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <span className="font-semibold">{cand.name}</span>
                  {cand.title && (
                    <span className={`text-[10px] ${isSelected ? "text-blue-200" : "text-slate-400"}`}>
                      ({cand.title})
                    </span>
                  )}
                  {isSelected && <Check className="w-3 h-3 ml-1" />}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl flex items-center space-x-2 text-red-800 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Comparison Grid */}
      {evaluating ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-500 space-y-2">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs font-medium">Evaluating side-by-side evidence matrix...</span>
        </div>
      ) : candidates.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center space-y-2">
          <Layers className="w-8 h-8 text-slate-300 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-800">Select candidates above to compare</h3>
          <p className="text-xs text-slate-500">
            Choose up to 4 candidates from this job opening to view a deep evidence alignment breakdown.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Candidate Profile & Score Cards Matrix */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {candidates.map((cand) => (
              <div
                key={cand.candidate_id}
                className={`bg-white rounded-xl border p-5 shadow-xs flex flex-col justify-between space-y-4 ${
                  cand.is_stale ? "border-amber-300 bg-amber-50/20" : "border-slate-200/80"
                }`}
              >
                <div className="space-y-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <Link
                        href={`/candidates/${cand.candidate_id}`}
                        className="text-sm font-bold text-slate-900 hover:text-blue-600 transition-colors"
                      >
                        {cand.candidate_name}
                      </Link>
                      <p className="text-xs text-slate-500 mt-0.5">{cand.current_title || "Designation not set"}</p>
                    </div>
                    {cand.application_status && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 uppercase">
                        {cand.application_status.replace("_", " ")}
                      </span>
                    )}
                  </div>

                  {/* Staleness Warning */}
                  {cand.is_stale && (
                    <div className="p-2 bg-amber-50 border border-amber-200 rounded text-[11px] text-amber-800 flex items-center gap-1 font-medium">
                      <Clock className="w-3 h-3 text-amber-600 shrink-0" />
                      <span>Result stale: candidate/job modified</span>
                    </div>
                  )}

                  {/* Overall Score */}
                  <div className="p-3 bg-slate-50 rounded-xl text-center border border-slate-100">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                      Overall Evidence Alignment
                    </span>
                    <div className="text-3xl font-black text-slate-900 mt-0.5">
                      {typeof cand.overall_score === "number"
                        ? Math.round(cand.overall_score)
                        : "--"}
                      <span className="text-xs font-normal text-slate-400">/100</span>
                    </div>
                    {cand.scoring_version && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        v{cand.scoring_version}
                      </span>
                    )}
                  </div>

                  {/* Five Scoring Dimensions */}
                  <div className="space-y-1.5 pt-2 border-t border-slate-100 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Required Skills (40%):</span>
                      <span className="font-bold text-slate-800">
                        {typeof cand.required_skills_score === "number"
                          ? `${Math.round(cand.required_skills_score)}%`
                          : "--"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Experience (25%):</span>
                      <span className="font-bold text-slate-800">
                        {typeof cand.experience_score === "number"
                          ? `${Math.round(cand.experience_score)}%`
                          : "--"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Preferred Skills (15%):</span>
                      <span className="font-bold text-slate-800">
                        {typeof cand.preferred_skills_score === "number"
                          ? `${Math.round(cand.preferred_skills_score)}%`
                          : "--"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Projects (10%):</span>
                      <span className="font-bold text-slate-800">
                        {typeof cand.project_relevance_score === "number"
                          ? `${Math.round(cand.project_relevance_score)}%`
                          : "--"}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-500">Other Criteria (10%):</span>
                      <span className="font-bold text-slate-800">
                        {typeof cand.other_criteria_score === "number"
                          ? `${Math.round(cand.other_criteria_score)}%`
                          : "--"}
                      </span>
                    </div>
                  </div>

                  {/* Evidence Counts */}
                  <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-[11px]">
                    <div className="bg-emerald-50/60 p-2 rounded text-emerald-800 font-medium">
                      ✓ {cand.matched_requirements_count} Demonstrated
                    </div>
                    <div className="bg-blue-50/60 p-2 rounded text-blue-800 font-medium">
                      ~ {cand.partial_requirements_count} Partial
                    </div>
                    <div className="bg-amber-50/60 p-2 rounded text-amber-800 font-medium">
                      ! {cand.needs_verification_count} Needs Verify
                    </div>
                    <div className="bg-slate-100 p-2 rounded text-slate-600 font-medium">
                      ✕ {cand.missing_requirements_count} Missing
                    </div>
                  </div>

                  {/* Demonstrated Strengths */}
                  <div className="pt-2 border-t border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                      Top Strengths
                    </span>
                    {cand.strengths.length > 0 ? (
                      <ul className="text-xs text-slate-700 list-disc list-inside space-y-0.5">
                        {cand.strengths.slice(0, 3).map((s, idx) => (
                          <li key={idx} className="truncate">{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic">None recorded</p>
                    )}
                  </div>

                  {/* Missing Evidence / Gaps */}
                  <div className="pt-2 border-t border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
                      Gaps / Missing
                    </span>
                    {cand.skill_gaps.length > 0 ? (
                      <ul className="text-xs text-slate-700 list-disc list-inside space-y-0.5">
                        {cand.skill_gaps.slice(0, 3).map((g, idx) => (
                          <li key={idx} className="truncate">{g}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic">No notable gaps</p>
                    )}
                  </div>

                  {/* Recruiter Verification Items */}
                  <div className="pt-2 border-t border-slate-100 space-y-1">
                    <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">
                      Verification Needs
                    </span>
                    {cand.verification_items.length > 0 ? (
                      <ul className="text-xs text-amber-800 list-disc list-inside space-y-0.5">
                        {cand.verification_items.slice(0, 2).map((v, idx) => (
                          <li key={idx} className="truncate">{v}</li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-slate-400 italic">None flagged</p>
                    )}
                  </div>
                </div>

                <div className="pt-2">
                  <Link
                    href={`/jobs/${jobId}/matches/${cand.candidate_id}`}
                    className="w-full py-1.5 text-center text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg block transition-colors border border-blue-100"
                  >
                    View Full Evidence Detail
                  </Link>
                </div>
              </div>
            ))}
          </div>

          {/* Side-by-Side Criteria Fulfillment Matrix */}
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="p-4 border-b border-slate-100">
              <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Job Criteria Requirement Matrix
              </h3>
              <p className="text-xs text-slate-500">
                Direct side-by-side comparison of candidate evidence against each job requirement.
              </p>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50/80 border-b border-slate-200/80 text-slate-600 uppercase text-[10px] font-bold tracking-wider">
                  <tr>
                    <th className="py-3 px-4 w-72">Job Requirement</th>
                    {candidates.map((c) => (
                      <th key={c.candidate_id} className="py-3 px-4">
                        {c.candidate_name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {criteriaMatrix.map((row) => (
                    <tr key={row.requirement_id} className="hover:bg-slate-50/50">
                      <td className="py-3 px-4 align-top">
                        <div className="space-y-1">
                          <p className="font-semibold text-slate-900">{row.requirement_text}</p>
                          <div className="flex items-center space-x-2 text-[10px]">
                            <span className="font-mono text-slate-500">{row.requirement_type}</span>
                            {row.is_mandatory ? (
                              <span className="text-rose-600 font-bold">Mandatory</span>
                            ) : (
                              <span className="text-slate-400">Preferred</span>
                            )}
                          </div>
                        </div>
                      </td>

                      {candidates.map((c) => {
                        const ev = row.evaluations[c.candidate_id];
                        const badge = getEvidenceBadge(ev?.evidence_status || "NOT_FOUND");
                        const Icon = badge.icon;

                        return (
                          <td key={c.candidate_id} className="py-3 px-4 align-top space-y-1">
                            <span
                              className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${badge.cls}`}
                            >
                              <Icon className="w-3 h-3" />
                              {badge.label}
                            </span>
                            {ev?.candidate_evidence && (
                              <p className="text-[11px] text-slate-700 leading-tight">
                                {ev.candidate_evidence}
                              </p>
                            )}
                            {ev?.semantic_similarity !== null && ev?.semantic_similarity !== undefined && (
                              <span className="text-[10px] text-slate-400 font-mono block">
                                similarity: {Math.round(ev.semantic_similarity * 100)}%
                              </span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Assistive Intelligence Notice */}
          <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-center text-xs text-slate-500">
            <span className="font-semibold text-slate-700">Recruiter Decision Guidance:</span> HireLens provides evidence-grounded scoring to assist your review process. The highest evidence score does not automatically constitute the best hire. Evaluate candidates comprehensively based on interviews and team context.
          </div>
        </div>
      )}
    </div>
  );
}

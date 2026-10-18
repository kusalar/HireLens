"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Kanban,
  Briefcase,
  Users,
  ChevronRight,
  ArrowRight,
  Sparkles,
  GitCompare,
  Clock,
  Layers,
  CheckCircle2,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { PipelineDashboardStats, Job } from "@/types";

export default function AgencyPipelineHubPage() {
  const [stats, setStats] = useState<PipelineDashboardStats | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [statsData, jobsData]: [PipelineDashboardStats, Job[]] = await Promise.all([
          apiClient<PipelineDashboardStats>("/applications/dashboard/stats"),
          apiClient<Job[]>("/jobs?limit=100"),
        ]);
        setStats(statsData);
        setJobs(jobsData);
      } catch (err) {
        console.error("Failed to load pipeline hub:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  if (loading) {
    return (
      <div className="py-24 flex flex-col items-center justify-center text-slate-500 space-y-3">
        <div className="w-7 h-7 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-xs font-medium">Loading agency recruitment pipelines...</span>
      </div>
    );
  }

  const stageCounts = stats?.stage_counts || {
    APPLIED: 0,
    UNDER_REVIEW: 0,
    SHORTLISTED: 0,
    INTERVIEW: 0,
    SELECTED: 0,
    ON_HOLD: 0,
    REJECTED: 0,
    WITHDRAWN: 0,
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Hero Header */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center gap-1">
              <Kanban className="w-3 h-3" />
              Recruitment Workspace
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Agency Application Pipelines
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Manage stage progression, interviews, shortlists, and candidate decisions across active openings.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="bg-slate-50 border border-slate-200 px-4 py-2.5 rounded-xl text-center">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Active Candidates in Pipeline
            </span>
            <span className="text-2xl font-black text-slate-900">
              {stats?.total_active_applications || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Aggregate Stage Metric Chips */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
        <div className="bg-white rounded-xl border border-blue-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">
            Applied
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.APPLIED || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-indigo-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider block">
            Under Review
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.UNDER_REVIEW || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-purple-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider block">
            Shortlisted
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.SHORTLISTED || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-amber-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">
            Interview
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.INTERVIEW || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-emerald-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">
            Selected
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.SELECTED || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-orange-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-orange-700 uppercase tracking-wider block">
            On Hold
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.ON_HOLD || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-rose-200/80 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">
            Rejected
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.REJECTED || 0}
          </span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-xs text-center">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
            Withdrawn
          </span>
          <span className="text-xl font-bold text-slate-900 mt-1 block">
            {stageCounts.WITHDRAWN || 0}
          </span>
        </div>
      </div>

      {/* Per-Job Pipeline Cards */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Position Pipeline Workspaces
            </h2>
            <p className="text-xs text-slate-500">
              Select an open role to launch its interactive 8-stage Kanban board.
            </p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 rounded-full text-slate-700">
            {jobs.length} Positions
          </span>
        </div>

        {jobs.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400 italic">
            No job positions created yet in your agency workspace.
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {jobs.map((j) => {
              const summary = stats?.job_summaries.find((s) => s.job_id === j.id);
              const appCount = summary?.active_applications_count || 0;

              return (
                <div
                  key={j.id}
                  className="p-5 px-6 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-slate-50/60 transition-colors"
                >
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2.5">
                      <h3 className="text-base font-bold text-slate-900">
                        {j.title}
                      </h3>
                      <span
                        className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase ${
                          j.status === "ACTIVE"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : "bg-slate-100 text-slate-600 border-slate-200"
                        }`}
                      >
                        {j.status}
                      </span>
                    </div>

                    <p className="text-xs text-slate-500">
                      {j.department || "General Department"} • {j.location || "Remote"} ({j.work_mode}) • Min {j.minimum_experience} yrs
                    </p>
                  </div>

                  <div className="flex items-center space-x-3 shrink-0">
                    <div className="text-right mr-2">
                      <span className="text-sm font-bold text-slate-900 block">
                        {appCount}
                      </span>
                      <span className="text-[10px] text-slate-400">
                        active applications
                      </span>
                    </div>

                    <Link
                      href={`/jobs/${j.id}/pipeline`}
                      className="inline-flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-xs transition-colors"
                    >
                      <Kanban className="w-3.5 h-3.5" />
                      <span>Open Kanban</span>
                      <ArrowRight className="w-3.5 h-3.5 ml-1" />
                    </Link>

                    <Link
                      href={`/jobs/${j.id}/matches`}
                      className="inline-flex items-center space-x-1 px-3 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition-colors"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                      <span>Matches</span>
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

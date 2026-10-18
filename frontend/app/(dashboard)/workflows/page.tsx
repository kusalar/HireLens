"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  GitFork,
  Plus,
  Play,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
  BarChart2,
  ShieldCheck,
  CheckSquare,
  Search,
  Filter,
  Trash2,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  RecruitmentWorkflow,
  WorkflowListResponse,
  WorkflowTriggerType,
} from "@/types";

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<RecruitmentWorkflow[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTrigger, setSelectedTrigger] = useState<string>("ALL");

  useEffect(() => {
    loadWorkflows();
  }, []);

  async function loadWorkflows() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<WorkflowListResponse>("/workflows");
      setWorkflows(res.items || []);
    } catch (e: any) {
      setErrorBanner("Failed to load recruitment workflows: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleActive(workflow: RecruitmentWorkflow) {
    try {
      await apiClient(`/workflows/${workflow.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !workflow.is_active }),
      });
      setWorkflows((prev) =>
        prev.map((w) =>
          w.id === workflow.id ? { ...w, is_active: !w.is_active } : w
        )
      );
      setSuccessBanner(
        `Workflow '${workflow.name}' ${!workflow.is_active ? "activated" : "deactivated"}.`
      );
      setTimeout(() => setSuccessBanner(null), 4000);
    } catch (e: any) {
      setErrorBanner("Failed to update workflow: " + e.message);
    }
  }

  async function handleDelete(workflow: RecruitmentWorkflow) {
    if (!confirm(`Are you sure you want to delete workflow '${workflow.name}'?`)) {
      return;
    }
    try {
      await apiClient(`/workflows/${workflow.id}`, { method: "DELETE" });
      setWorkflows((prev) => prev.filter((w) => w.id !== workflow.id));
      setSuccessBanner(`Workflow '${workflow.name}' deleted.`);
      setTimeout(() => setSuccessBanner(null), 4000);
    } catch (e: any) {
      setErrorBanner("Failed to delete workflow: " + e.message);
    }
  }

  const filteredWorkflows = workflows.filter((w) => {
    const matchesSearch =
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (w.description && w.description.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesTrigger =
      selectedTrigger === "ALL" || w.trigger_type === selectedTrigger;
    return matchesSearch && matchesTrigger;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <GitFork className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              Recruitment Workflow Automation
            </h1>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Automate operational recruitment sequences while preserving human authority over hiring decisions.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Link
            href="/workflows/monitoring"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 transition"
          >
            <BarChart2 className="w-4 h-4 text-gray-500" />
            Monitoring
          </Link>
          <Link
            href="/approvals"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-amber-200 bg-amber-50 hover:bg-amber-100 text-amber-800 transition"
          >
            <ShieldCheck className="w-4 h-4 text-amber-600" />
            Approvals
          </Link>
          <Link
            href="/tasks"
            className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-blue-200 bg-blue-50 hover:bg-blue-100 text-blue-800 transition"
          >
            <CheckSquare className="w-4 h-4 text-blue-600" />
            Tasks
          </Link>
          <Link
            href="/workflows/new"
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            Create Workflow
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {errorBanner && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between text-red-800 text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-600" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-red-500 hover:text-red-700">
            &times;
          </button>
        </div>
      )}

      {successBanner && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center justify-between text-emerald-800 text-sm">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="text-emerald-500 hover:text-emerald-700">
            &times;
          </button>
        </div>
      )}

      {/* Search & Filters */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            placeholder="Search workflows by name..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedTrigger}
            onChange={(e) => setSelectedTrigger(e.target.value)}
            className="text-xs border border-gray-300 rounded-lg px-3 py-2 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="ALL">All Trigger Events</option>
            <option value="CANDIDATE_CREATED">Candidate Created</option>
            <option value="RESUME_PROCESSED">Resume Processed</option>
            <option value="CANDIDATE_MATCHED">Candidate Matched</option>
            <option value="APPLICATION_SUBMITTED">Application Submitted</option>
            <option value="APPLICATION_STAGE_CHANGED">Application Stage Changed</option>
            <option value="INTERVIEW_SCHEDULED">Interview Scheduled</option>
            <option value="INTERVIEW_RESCHEDULED">Interview Rescheduled</option>
            <option value="INTERVIEW_COMPLETED">Interview Completed</option>
            <option value="FEEDBACK_SUBMITTED">Feedback Submitted</option>
            <option value="CANDIDATE_INACTIVE">Candidate Inactive</option>
          </select>
        </div>
      </div>

      {/* Workflow List */}
      {loading ? (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-200">
          <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-sm">Loading recruitment workflows...</p>
        </div>
      ) : filteredWorkflows.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-gray-200 shadow-sm">
          <GitFork className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-900">No recruitment workflows found</h3>
          <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
            Create automated rules to trigger candidate communications, interview prep briefs, and recruiter tasks.
          </p>
          <Link
            href="/workflows/new"
            className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition"
          >
            <Plus className="w-4 h-4" />
            Create First Workflow
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredWorkflows.map((wf) => (
            <div
              key={wf.id}
              className={`bg-white rounded-xl border p-5 shadow-sm transition hover:shadow-md flex flex-col justify-between ${
                wf.is_active ? "border-gray-200" : "border-gray-200 bg-gray-50/50 opacity-80"
              }`}
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        wf.is_active ? "bg-emerald-500" : "bg-gray-300"
                      }`}
                    />
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {wf.trigger_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <span className="text-xs font-medium text-gray-400">
                    v{wf.current_version?.version_number || 1}
                  </span>
                </div>

                <h3 className="text-base font-semibold text-gray-900 mt-3 line-clamp-1">
                  {wf.name}
                </h3>
                <p className="text-xs text-gray-500 mt-1 line-clamp-2 min-h-[32px]">
                  {wf.description || "No description provided."}
                </p>

                {/* Steps count & actions summary */}
                <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-gray-400" />
                    {wf.current_version?.definition.actions?.length || 0} configured action(s)
                  </span>
                  <span>{wf.execution_count || 0} runs</span>
                </div>
              </div>

              <div className="mt-5 pt-3 border-t border-gray-100 flex items-center justify-between">
                <button
                  type="button"
                  onClick={() => handleToggleActive(wf)}
                  className={`text-xs font-semibold px-2.5 py-1 rounded-md border transition ${
                    wf.is_active
                      ? "text-gray-600 bg-white border-gray-200 hover:bg-gray-50"
                      : "text-emerald-700 bg-emerald-50 border-emerald-200 hover:bg-emerald-100"
                  }`}
                >
                  {wf.is_active ? "Deactivate" : "Activate"}
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDelete(wf)}
                    title="Delete workflow"
                    className="p-1.5 text-gray-400 hover:text-red-600 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <Link
                    href={`/workflows/${wf.id}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                  >
                    View Details
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

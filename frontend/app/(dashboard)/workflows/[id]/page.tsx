"use client";

import React, { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import {
  GitFork,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Layers,
  Play,
  RotateCcw,
  ShieldCheck,
  CheckSquare,
  FileText,
  Calendar,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  RecruitmentWorkflow,
  WorkflowExecutionRead,
  WorkflowExecutionListResponse,
} from "@/types";

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [workflow, setWorkflow] = useState<RecruitmentWorkflow | null>(null);
  const [executions, setExecutions] = useState<WorkflowExecutionRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Test trigger state
  const [showTestModal, setShowTestModal] = useState(false);
  const [testEntityType, setTestEntityType] = useState("candidate");
  const [testEntityId, setTestEntityId] = useState("");
  const [triggering, setTriggering] = useState(false);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  async function loadData() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const wf = await apiClient<RecruitmentWorkflow>(`/workflows/${id}`);
      setWorkflow(wf);

      const execs = await apiClient<WorkflowExecutionListResponse>(
        `/workflows/executions?workflow_id=${id}`
      );
      setExecutions(execs.items || []);
    } catch (e: any) {
      setErrorBanner("Failed to load workflow details: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleActive() {
    if (!workflow) return;
    try {
      await apiClient(`/workflows/${workflow.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !workflow.is_active }),
      });
      setWorkflow((prev) => (prev ? { ...prev, is_active: !prev.is_active } : null));
      setSuccessBanner(
        `Workflow ${!workflow.is_active ? "activated" : "deactivated"} successfully.`
      );
      setTimeout(() => setSuccessBanner(null), 4000);
    } catch (e: any) {
      setErrorBanner("Failed to update status: " + e.message);
    }
  }

  async function handleRunTest(e: React.FormEvent) {
    e.preventDefault();
    if (!testEntityId.trim()) {
      setErrorBanner("Please provide an entity UUID to trigger test.");
      return;
    }
    setTriggering(true);
    setErrorBanner(null);
    try {
      await apiClient(`/workflows/${id}/trigger`, {
        method: "POST",
        body: JSON.stringify({
          entity_type: testEntityType,
          entity_id: testEntityId.trim(),
        }),
      });
      setShowTestModal(false);
      setSuccessBanner("Test execution triggered. Refreshing execution history...");
      setTimeout(() => setSuccessBanner(null), 4000);
      loadData();
    } catch (e: any) {
      setErrorBanner("Failed to trigger test: " + e.message);
    } finally {
      setTriggering(false);
    }
  }

  function formatIST(isoDate?: string | null) {
    if (!isoDate) return "—";
    try {
      const d = new Date(isoDate);
      return (
        d.toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: true,
        }) + " IST"
      );
    } catch {
      return isoDate;
    }
  }

  if (loading) {
    return (
      <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-200">
        <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
        <p className="text-sm">Loading workflow details...</p>
      </div>
    );
  }

  if (!workflow) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-gray-200">
        <AlertCircle className="w-8 h-8 text-red-500 mx-auto mb-2" />
        <h2 className="text-base font-semibold text-gray-900">Workflow Not Found</h2>
        <Link
          href="/workflows"
          className="mt-4 inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Workflows
        </Link>
      </div>
    );
  }

  const definition = workflow.current_version?.definition;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/workflows"
            className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-gray-900">{workflow.name}</h1>
              <span
                className={`text-[11px] font-bold px-2 py-0.5 rounded-full ${
                  workflow.is_active
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-gray-100 text-gray-600 border border-gray-200"
                }`}
              >
                {workflow.is_active ? "Active" : "Inactive"}
              </span>
              <span className="text-xs text-gray-400 font-mono">
                v{workflow.current_version?.version_number || 1}
              </span>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Triggered on{" "}
              <span className="font-semibold text-gray-700">
                {workflow.trigger_type.replace(/_/g, " ")}
              </span>{" "}
              • Created {formatIST(workflow.created_at)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleToggleActive}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 transition"
          >
            {workflow.is_active ? "Deactivate" : "Activate"}
          </button>
          <button
            type="button"
            onClick={() => setShowTestModal(true)}
            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition flex items-center gap-1.5"
          >
            <Play className="w-3.5 h-3.5" />
            Run Test Execution
          </button>
        </div>
      </div>

      {errorBanner && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-sm">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorBanner}</span>
        </div>
      )}

      {successBanner && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-emerald-800 text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>{successBanner}</span>
        </div>
      )}

      {/* Grid: Definition Overview & Execution History */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Workflow Definition */}
        <div className="lg:col-span-1 space-y-5">
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <h2 className="text-sm font-bold text-gray-900 border-b pb-2 flex items-center gap-1.5">
              <Layers className="w-4 h-4 text-indigo-600" />
              Workflow Configuration
            </h2>

            <div>
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
                Trigger Event
              </span>
              <span className="text-xs font-semibold px-2 py-1 rounded bg-indigo-50 text-indigo-700 border border-indigo-100 inline-block">
                {workflow.trigger_type}
              </span>
            </div>

            <div>
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
                Conditions Evaluated
              </span>
              {definition?.conditions?.conditions && definition.conditions.conditions.length > 0 ? (
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200 space-y-1">
                  <span className="text-[10px] font-bold text-gray-400 uppercase">
                    Logic: {definition.conditions.logical_operator}
                  </span>
                  {definition.conditions.conditions.map((c: any, i: number) => (
                    <div key={i} className="text-xs font-mono text-gray-700">
                      • {c.field} {c.operator} {String(c.value ?? "")}
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-xs text-gray-500 italic">
                  Always triggers (no conditions defined)
                </span>
              )}
            </div>

            <div>
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block mb-1">
                Sequential Actions ({definition?.actions?.length || 0})
              </span>
              <div className="space-y-2">
                {definition?.actions?.map((act, i) => (
                  <div
                    key={i}
                    className="p-2.5 rounded-lg border border-gray-200 bg-gray-50 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-gray-800">
                        {i + 1}. {act.action_type.replace(/_/g, " ")}
                      </span>
                      {act.requires_approval && (
                        <span className="text-[10px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                          Requires Approval
                        </span>
                      )}
                    </div>
                    {act.description && (
                      <p className="text-[11px] text-gray-500">{act.description}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Execution History */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white p-5 rounded-xl border border-gray-200 shadow-sm space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h2 className="text-base font-bold text-gray-900">Execution History</h2>
                <p className="text-xs text-gray-500">
                  Audit trail of all automated runs for this workflow
                </p>
              </div>
              <button
                type="button"
                onClick={loadData}
                className="p-1.5 text-gray-400 hover:text-gray-600 transition"
                title="Refresh"
              >
                <RotateCcw className="w-4 h-4" />
              </button>
            </div>

            {executions.length === 0 ? (
              <div className="p-8 text-center text-gray-400">
                <Clock className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">No executions recorded yet for this workflow.</p>
                <p className="text-xs mt-1">
                  Use "Run Test Execution" above to test the workflow with an existing entity.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {executions.map((exec) => (
                  <div key={exec.id} className="py-3.5 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded ${
                            exec.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : exec.status === "WAITING_FOR_APPROVAL"
                              ? "bg-amber-50 text-amber-700 border border-amber-200"
                              : exec.status === "FAILED"
                              ? "bg-red-50 text-red-700 border border-red-200"
                              : "bg-gray-100 text-gray-700 border border-gray-200"
                          }`}
                        >
                          {exec.status}
                        </span>
                        <span className="text-xs font-medium text-gray-900">
                          Triggered by {exec.trigger_entity_type}
                        </span>
                      </div>
                      <span className="text-xs text-gray-400">
                        {formatIST(exec.created_at)}
                      </span>
                    </div>

                    {exec.error_message && (
                      <p className="text-xs text-red-600 bg-red-50 p-2 rounded border border-red-100 font-mono">
                        Error: {exec.error_message}
                      </p>
                    )}

                    {/* Steps execution preview */}
                    {exec.steps && exec.steps.length > 0 && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1">
                        {exec.steps.map((st) => (
                          <div
                            key={st.id}
                            className="bg-gray-50 border border-gray-200/80 rounded p-2 text-[11px]"
                          >
                            <div className="font-semibold text-gray-700 truncate">
                              {st.action_type}
                            </div>
                            <div className="flex items-center justify-between text-gray-400 mt-1">
                              <span>Step {st.step_index + 1}</span>
                              <span
                                className={`font-bold ${
                                  st.status === "COMPLETED"
                                    ? "text-emerald-600"
                                    : st.status === "WAITING_APPROVAL"
                                    ? "text-amber-600"
                                    : "text-gray-500"
                                }`}
                              >
                                {st.status}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Manual Test Trigger Modal */}
      {showTestModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-gray-900">Test Workflow Execution</h3>
            <p className="text-xs text-gray-500">
              Trigger this workflow on demand for a specified candidate, application, or interview.
            </p>

            <form onSubmit={handleRunTest} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Entity Type
                </label>
                <select
                  value={testEntityType}
                  onChange={(e) => setTestEntityType(e.target.value)}
                  className="w-full text-xs border border-gray-300 rounded px-3 py-2 bg-white"
                >
                  <option value="candidate">Candidate</option>
                  <option value="application">Application</option>
                  <option value="interview">Interview</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Entity UUID *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 550e8400-e29b-41d4-a716-446655440000"
                  value={testEntityId}
                  onChange={(e) => setTestEntityId(e.target.value)}
                  className="w-full text-xs font-mono border border-gray-300 rounded px-3 py-2"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setShowTestModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold rounded border text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={triggering}
                  className="px-4 py-1.5 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm disabled:opacity-50"
                >
                  {triggering ? "Executing..." : "Execute Test"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

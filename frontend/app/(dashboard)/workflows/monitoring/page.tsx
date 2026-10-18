"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  BarChart2,
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  RotateCcw,
  ShieldCheck,
  CheckSquare,
  Activity,
  Layers,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { WorkflowMonitoringStats, WorkflowExecutionRead } from "@/types";

export default function WorkflowMonitoringPage() {
  const [stats, setStats] = useState<WorkflowMonitoringStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [selectedExec, setSelectedExec] = useState<WorkflowExecutionRead | null>(null);

  useEffect(() => {
    loadMonitoringStats();
  }, []);

  async function loadMonitoringStats() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const data = await apiClient<WorkflowMonitoringStats>("/workflows/monitoring/stats");
      setStats(data);
    } catch (e: any) {
      setErrorBanner("Failed to load workflow monitoring statistics: " + e.message);
    } finally {
      setLoading(false);
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
              <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
                <BarChart2 className="w-5 h-5" />
              </div>
              <h1 className="text-xl font-bold text-gray-900">Workflow Monitoring Dashboard</h1>
            </div>
            <p className="text-xs text-gray-500 mt-0.5">
              Live operational metrics, execution durations, and automated sequence auditing.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={loadMonitoringStats}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 transition"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Refresh Metrics
          </button>
        </div>
      </div>

      {errorBanner && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-sm">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorBanner}</span>
        </div>
      )}

      {loading && !stats ? (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-200">
          <div className="w-6 h-6 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-sm">Loading monitoring telemetry...</p>
        </div>
      ) : stats ? (
        <>
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Total Workflows
              </span>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {stats.total_workflows}
              </div>
              <span className="text-[11px] text-emerald-600 font-medium">
                {stats.active_workflows} active
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Total Executions
              </span>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {stats.total_executions}
              </div>
              <span className="text-[11px] text-gray-500">All-time</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Success Rate
              </span>
              <div className="text-2xl font-bold text-emerald-600 mt-1">
                {stats.success_rate_percent}%
              </div>
              <span className="text-[11px] text-gray-500 font-medium">
                {stats.successful_executions} completed
              </span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Failed Runs
              </span>
              <div className="text-2xl font-bold text-red-600 mt-1">
                {stats.failed_executions}
              </div>
              <span className="text-[11px] text-gray-500">Errors recorded</span>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Pending Approvals
              </span>
              <div className="text-2xl font-bold text-amber-600 mt-1">
                {stats.pending_approvals}
              </div>
              <Link href="/approvals" className="text-[11px] text-indigo-600 hover:underline">
                Review queue &rarr;
              </Link>
            </div>

            <div className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm">
              <span className="text-[11px] font-semibold text-gray-400 uppercase tracking-wider block">
                Total Retries
              </span>
              <div className="text-2xl font-bold text-gray-900 mt-1">
                {stats.retry_count}
              </div>
              <span className="text-[11px] text-gray-500">Celery backoffs</span>
            </div>
          </div>

          {/* Recent Executions Stream */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-4 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-bold text-gray-900">Recent Automated Executions</h2>
                <p className="text-xs text-gray-500">Live operational telemetry across all active workflows</p>
              </div>
            </div>

            {stats.recent_executions.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-sm">
                No recent executions found.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-50 text-gray-500 uppercase tracking-wider border-b border-gray-200">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Workflow</th>
                      <th className="py-3 px-4 font-semibold">Trigger Event</th>
                      <th className="py-3 px-4 font-semibold">Status</th>
                      <th className="py-3 px-4 font-semibold">Steps</th>
                      <th className="py-3 px-4 font-semibold">Timestamp (IST)</th>
                      <th className="py-3 px-4 font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {stats.recent_executions.map((exec) => (
                      <tr key={exec.id} className="hover:bg-gray-50 transition">
                        <td className="py-3 px-4 font-semibold text-gray-900">
                          {exec.workflow_name || "Workflow"}
                        </td>
                        <td className="py-3 px-4">
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-100">
                            {exec.trigger_event}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
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
                        </td>
                        <td className="py-3 px-4 text-gray-500 font-mono">
                          {exec.steps?.length || 0} step(s)
                        </td>
                        <td className="py-3 px-4 text-gray-500">
                          {formatIST(exec.created_at)}
                        </td>
                        <td className="py-3 px-4">
                          <button
                            type="button"
                            onClick={() => setSelectedExec(exec)}
                            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                          >
                            Details &rarr;
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      ) : null}

      {/* Execution Drilldown Modal */}
      {selectedExec && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  Execution Telemetry Details
                </h3>
                <span className="text-[11px] text-gray-400 font-mono">
                  {selectedExec.id}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedExec(null)}
                className="text-gray-400 hover:text-gray-600 text-lg"
              >
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div className="grid grid-cols-2 gap-2 bg-gray-50 p-3 rounded-lg border border-gray-200">
                <div>
                  <span className="text-gray-400 block">Workflow</span>
                  <span className="font-semibold text-gray-900">{selectedExec.workflow_name || "—"}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Status</span>
                  <span className="font-bold text-gray-900">{selectedExec.status}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Trigger Event</span>
                  <span className="font-mono text-gray-900">{selectedExec.trigger_event}</span>
                </div>
                <div>
                  <span className="text-gray-400 block">Created At</span>
                  <span className="text-gray-700">{formatIST(selectedExec.created_at)}</span>
                </div>
              </div>

              {selectedExec.error_message && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-red-700 font-mono text-[11px]">
                  <strong>Error:</strong> {selectedExec.error_message}
                </div>
              )}

              <div>
                <h4 className="font-bold text-gray-900 mb-2">Executed Steps</h4>
                <div className="space-y-2">
                  {selectedExec.steps?.map((step) => (
                    <div
                      key={step.id}
                      className="p-3 rounded-lg border border-gray-200 bg-gray-50 space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-gray-800">
                          Step {step.step_index + 1}: {step.action_type}
                        </span>
                        <span className="font-bold text-gray-600">{step.status}</span>
                      </div>
                      {step.error_message && (
                        <p className="text-red-600 font-mono text-[11px]">{step.error_message}</p>
                      )}
                      {step.output_payload && (
                        <pre className="text-[10px] bg-white p-2 rounded border border-gray-200 overflow-x-auto text-gray-600">
                          {JSON.stringify(step.output_payload, null, 2)}
                        </pre>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="pt-3 border-t flex justify-end">
              <button
                type="button"
                onClick={() => setSelectedExec(null)}
                className="px-4 py-1.5 text-xs font-semibold rounded bg-gray-100 hover:bg-gray-200 text-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

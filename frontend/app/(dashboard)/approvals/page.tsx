"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
  Layers,
  ArrowRight,
  RotateCcw,
  UserCheck,
  ExternalLink,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  WorkflowApprovalRead,
  WorkflowApprovalListResponse,
  WorkflowApprovalStatus,
} from "@/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<WorkflowApprovalRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<WorkflowApprovalStatus>("PENDING");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Reject modal state
  const [rejectingApproval, setRejectingApproval] = useState<WorkflowApprovalRead | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);

  useEffect(() => {
    loadApprovals();
  }, [activeTab]);

  async function loadApprovals() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<WorkflowApprovalListResponse>(
        `/workflows/approvals?status=${activeTab}`
      );
      setApprovals(res.items || []);
    } catch (e: any) {
      setErrorBanner("Failed to load approval queue: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(approval: WorkflowApprovalRead) {
    if (!confirm(`Are you sure you want to approve '${approval.title}'? This will execute the action immediately.`)) {
      return;
    }
    setSubmittingDecision(true);
    setErrorBanner(null);
    try {
      await apiClient(`/workflows/approvals/${approval.id}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision: "APPROVE" }),
      });
      setSuccessBanner(`Approval request '${approval.title}' approved and executed.`);
      setTimeout(() => setSuccessBanner(null), 4000);
      loadApprovals();
    } catch (e: any) {
      setErrorBanner("Failed to approve request: " + e.message);
    } finally {
      setSubmittingDecision(false);
    }
  }

  async function handleRejectSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rejectingApproval) return;
    if (!rejectionReason.trim()) {
      setErrorBanner("A mandatory rejection reason is required.");
      return;
    }

    setSubmittingDecision(true);
    setErrorBanner(null);
    try {
      await apiClient(`/workflows/approvals/${rejectingApproval.id}/decision`, {
        method: "POST",
        body: JSON.stringify({
          decision: "REJECT",
          rejection_reason: rejectionReason.trim(),
        }),
      });
      setSuccessBanner(`Approval request rejected.`);
      setTimeout(() => setSuccessBanner(null), 4000);
      setRejectingApproval(null);
      setRejectionReason("");
      loadApprovals();
    } catch (e: any) {
      setErrorBanner("Failed to reject request: " + e.message);
    } finally {
      setSubmittingDecision(false);
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
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-50 text-amber-600 rounded-lg">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">
              Human Approval & Review Queue
            </h1>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Authorize or reject sensitive automated workflow actions. Automated actions pause until human approval is recorded.
          </p>
        </div>

        <button
          type="button"
          onClick={loadApprovals}
          className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg border border-gray-300 bg-white hover:bg-gray-50 text-gray-700 transition"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          Refresh Queue
        </button>
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

      {/* Filter Tabs */}
      <div className="border-b border-gray-200 flex gap-4">
        {(["PENDING", "APPROVED", "REJECTED", "EXPIRED"] as WorkflowApprovalStatus[]).map(
          (st) => (
            <button
              key={st}
              onClick={() => setActiveTab(st)}
              className={`pb-3 text-xs font-bold border-b-2 transition uppercase tracking-wider ${
                activeTab === st
                  ? "border-amber-600 text-amber-700"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {st}
            </button>
          )
        )}
      </div>

      {/* Approvals List */}
      {loading ? (
        <div className="p-12 text-center text-gray-500 bg-white rounded-xl border border-gray-200">
          <div className="w-6 h-6 border-2 border-amber-600 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-sm">Loading approval requests...</p>
        </div>
      ) : approvals.length === 0 ? (
        <div className="p-12 text-center bg-white rounded-xl border border-gray-200 shadow-sm">
          <ShieldCheck className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-gray-900">
            No {activeTab.toLowerCase()} approval requests
          </h3>
          <p className="text-sm text-gray-500 mt-1 max-w-sm mx-auto">
            Sensitive actions requiring recruiter or administrator sign-off will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((appr) => (
            <div
              key={appr.id}
              className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm space-y-3"
            >
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                      appr.status === "PENDING"
                        ? "bg-amber-50 text-amber-800 border border-amber-200"
                        : appr.status === "APPROVED"
                        ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                        : appr.status === "REJECTED"
                        ? "bg-red-50 text-red-800 border border-red-200"
                        : "bg-gray-100 text-gray-700 border border-gray-200"
                    }`}
                  >
                    {appr.status}
                  </span>
                  <span className="text-xs font-semibold text-gray-500">
                    Workflow: {appr.workflow_name || "Workflow Execution"}
                  </span>
                </div>
                <div className="text-xs text-gray-400">
                  Requested {formatIST(appr.created_at)}
                  {appr.expires_at && ` • Expires ${formatIST(appr.expires_at)}`}
                </div>
              </div>

              <div>
                <h3 className="text-base font-bold text-gray-900">{appr.title}</h3>
                {appr.description && (
                  <p className="text-xs text-gray-600 mt-1">{appr.description}</p>
                )}
              </div>

              {/* Action Payload Preview */}
              <div className="bg-gray-50 p-3 rounded-lg border border-gray-200/80 text-xs text-gray-700 space-y-1">
                <span className="font-semibold text-gray-500 text-[11px] block uppercase tracking-wider">
                  Target Action: {appr.requested_action}
                </span>
                {appr.action_payload && (
                  <pre className="text-[11px] font-mono text-gray-600 bg-white p-2 rounded border border-gray-200 overflow-x-auto">
                    {JSON.stringify(appr.action_payload, null, 2)}
                  </pre>
                )}
              </div>

              {appr.rejection_reason && (
                <div className="p-3 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                  <strong>Rejection Reason:</strong> {appr.rejection_reason}
                </div>
              )}

              {/* Action Buttons for Pending */}
              {appr.status === "PENDING" && (
                <div className="pt-2 border-t border-gray-100 flex items-center justify-end gap-2">
                  <button
                    type="button"
                    disabled={submittingDecision}
                    onClick={() => {
                      setRejectingApproval(appr);
                      setRejectionReason("");
                    }}
                    className="px-3.5 py-1.5 text-xs font-semibold rounded-lg border border-red-300 text-red-700 hover:bg-red-50 transition"
                  >
                    Reject
                  </button>
                  <button
                    type="button"
                    disabled={submittingDecision}
                    onClick={() => handleApprove(appr)}
                    className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition disabled:opacity-50"
                  >
                    Approve & Execute
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Reject Reason Modal */}
      {rejectingApproval && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-gray-900">
              Reject Workflow Approval Request
            </h3>
            <p className="text-xs text-gray-500">
              Please provide a mandatory explanation for rejecting this automated sequence. The workflow execution will be cancelled.
            </p>

            <form onSubmit={handleRejectSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-700 mb-1">
                  Rejection Reason *
                </label>
                <textarea
                  required
                  rows={3}
                  placeholder="e.g. Candidate salary expectations exceed approved requisition budget..."
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  className="w-full text-xs border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-red-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setRejectingApproval(null)}
                  className="px-3 py-1.5 text-xs font-semibold rounded border text-gray-600 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingDecision || !rejectionReason.trim()}
                  className="px-4 py-1.5 text-xs font-semibold rounded bg-red-600 hover:bg-red-700 text-white shadow-sm disabled:opacity-50"
                >
                  Confirm Rejection
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

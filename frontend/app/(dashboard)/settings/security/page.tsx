"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldCheck,
  ShieldAlert,
  Key,
  Users,
  Eye,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Clock,
  Filter,
  Search,
  Lock,
  Cpu,
  Archive,
  Database,
  FileText,
  UserCheck,
  Laptop,
  Globe,
  Sliders,
  ChevronRight,
  Info,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  GovernanceOverviewResponse,
  SecurityAuditEventRead,
  SecurityAuditEventListResponse,
  UserSessionRead,
  CandidateConsentRecordRead,
  CandidatePrivacyRequestRead,
  AIGovernancePolicyRead,
  AIUsageMetricsResponse,
  DataRetentionPolicyRead,
  RetentionDryRunPreview,
  RetentionExecutionLogRead,
  AuditEventCategory,
  AuditSeverity,
  PrivacyRequestStatus,
  PrivacyRequestType,
  RetentionCategory,
  RetentionAction,
} from "@/types";

type SecurityTab =
  | "overview"
  | "audit"
  | "sessions"
  | "privacy"
  | "consent"
  | "ai"
  | "retention";

export default function SecurityGovernancePage() {
  const [activeTab, setActiveTab] = useState<SecurityTab>("overview");
  const [user, setUser] = useState<any>(null);
  const [isOwnerOrAdmin, setIsOwnerOrAdmin] = useState<boolean>(false);

  // Global State
  const [overview, setOverview] = useState<GovernanceOverviewResponse | null>(null);
  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // Tab 1: Audit Events Explorer
  const [auditEvents, setAuditEvents] = useState<SecurityAuditEventRead[]>([]);
  const [auditTotal, setAuditTotal] = useState<number>(0);
  const [auditPage, setAuditPage] = useState<number>(1);
  const [auditCategory, setAuditCategory] = useState<string>("");
  const [auditSeverity, setAuditSeverity] = useState<string>("");
  const [loadingAudit, setLoadingAudit] = useState<boolean>(false);
  const [selectedAudit, setSelectedAudit] = useState<SecurityAuditEventRead | null>(null);

  // Tab 2: Sessions
  const [sessions, setSessions] = useState<UserSessionRead[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);

  // Tab 3: Privacy Requests & Legal Holds
  const [privacyRequests, setPrivacyRequests] = useState<CandidatePrivacyRequestRead[]>([]);
  const [loadingPrivacy, setLoadingPrivacy] = useState<boolean>(false);
  const [legalHoldModal, setLegalHoldModal] = useState<CandidatePrivacyRequestRead | null>(null);
  const [legalHoldReason, setLegalHoldReason] = useState<string>("");

  // Tab 4: Consent History
  const [consentRecords, setConsentRecords] = useState<CandidateConsentRecordRead[]>([]);
  const [loadingConsent, setLoadingConsent] = useState<boolean>(false);

  // Tab 5: AI Governance & Controls
  const [aiPolicy, setAiPolicy] = useState<AIGovernancePolicyRead | null>(null);
  const [aiUsage, setAiUsage] = useState<AIUsageMetricsResponse | null>(null);
  const [loadingAI, setLoadingAI] = useState<boolean>(false);
  const [savingAIPolicy, setSavingAIPolicy] = useState<boolean>(false);

  // Tab 6: Retention Policies
  const [retentionPolicies, setRetentionPolicies] = useState<DataRetentionPolicyRead[]>([]);
  const [retentionLogs, setRetentionLogs] = useState<RetentionExecutionLogRead[]>([]);
  const [loadingRetention, setLoadingRetention] = useState<boolean>(false);
  const [dryRunPreview, setDryRunPreview] = useState<RetentionDryRunPreview | null>(null);
  const [previewingCategory, setPreviewingCategory] = useState<string | null>(null);

  const clearMessages = () => {
    setActionSuccess(null);
    setActionError(null);
  };

  // Helper: Format IST timestamp
  const formatIST = (dateStr?: string | null) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return new Intl.DateTimeFormat("en-IN", {
        timeZone: "Asia/Kolkata",
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
        hour12: true,
      }).format(d) + " IST";
    } catch {
      return dateStr;
    }
  };

  // Initial user & overview load
  useEffect(() => {
    async function loadUser() {
      try {
        const u: any = await apiClient("/auth/me");
        setUser(u);
        const admin = u.role === "OWNER" || u.role === "ADMIN";
        setIsOwnerOrAdmin(admin);
      } catch (e) {
        console.error("Auth error:", e);
      }
    }
    loadUser();
    loadOverview();
  }, []);

  const loadOverview = async () => {
    setLoadingOverview(true);
    try {
      const data: GovernanceOverviewResponse = await apiClient("/governance/overview");
      setOverview(data);
    } catch (e: any) {
      console.error("Overview error:", e);
    } finally {
      setLoadingOverview(false);
    }
  };

  // Tab Loaders
  const loadAuditEvents = useCallback(async () => {
    setLoadingAudit(true);
    try {
      let q = `/governance/audit-events?skip=${(auditPage - 1) * 20}&limit=20`;
      if (auditCategory) q += `&category=${auditCategory}`;
      if (auditSeverity) q += `&severity=${auditSeverity}`;
      const res: SecurityAuditEventListResponse = await apiClient(q);
      setAuditEvents(res.items);
      setAuditTotal(res.total);
    } catch (e: any) {
      setActionError(e.message || "Failed to load audit events.");
    } finally {
      setLoadingAudit(false);
    }
  }, [auditPage, auditCategory, auditSeverity]);

  const loadSessions = useCallback(async () => {
    setLoadingSessions(true);
    try {
      const res: UserSessionRead[] = await apiClient("/governance/sessions");
      setSessions(res);
    } catch (e: any) {
      setActionError(e.message || "Failed to load sessions.");
    } finally {
      setLoadingSessions(false);
    }
  }, []);

  const loadPrivacyRequests = useCallback(async () => {
    setLoadingPrivacy(true);
    try {
      const res: CandidatePrivacyRequestRead[] = await apiClient("/governance/privacy-requests");
      setPrivacyRequests(res);
    } catch (e: any) {
      setActionError(e.message || "Failed to load privacy requests.");
    } finally {
      setLoadingPrivacy(false);
    }
  }, []);

  const loadConsentRecords = useCallback(async () => {
    setLoadingConsent(true);
    try {
      const res: CandidateConsentRecordRead[] = await apiClient("/governance/consent-records");
      setConsentRecords(res);
    } catch (e: any) {
      setActionError(e.message || "Failed to load consent records.");
    } finally {
      setLoadingConsent(false);
    }
  }, []);

  const loadAIData = useCallback(async () => {
    setLoadingAI(true);
    try {
      const [p, u] = await Promise.all([
        apiClient<AIGovernancePolicyRead>("/governance/ai-policy"),
        apiClient<AIUsageMetricsResponse>("/governance/ai-usage"),
      ]);
      setAiPolicy(p);
      setAiUsage(u);
    } catch (e: any) {
      setActionError(e.message || "Failed to load AI governance data.");
    } finally {
      setLoadingAI(false);
    }
  }, []);

  const loadRetentionData = useCallback(async () => {
    setLoadingRetention(true);
    try {
      const [policies, logs] = await Promise.all([
        apiClient<DataRetentionPolicyRead[]>("/governance/retention-policies"),
        apiClient<RetentionExecutionLogRead[]>("/governance/retention-logs"),
      ]);
      setRetentionPolicies(policies);
      setRetentionLogs(logs);
    } catch (e: any) {
      setActionError(e.message || "Failed to load retention policies.");
    } finally {
      setLoadingRetention(false);
    }
  }, []);

  // Fetch when active tab changes
  useEffect(() => {
    clearMessages();
    if (activeTab === "audit") loadAuditEvents();
    if (activeTab === "sessions") loadSessions();
    if (activeTab === "privacy") loadPrivacyRequests();
    if (activeTab === "consent") loadConsentRecords();
    if (activeTab === "ai") loadAIData();
    if (activeTab === "retention") loadRetentionData();
  }, [activeTab, loadAuditEvents, loadSessions, loadPrivacyRequests, loadConsentRecords, loadAIData, loadRetentionData]);

  // Actions: Sessions
  const handleRevokeSession = async (sessionId: string) => {
    clearMessages();
    try {
      await apiClient(`/governance/sessions/${sessionId}/revoke`, { method: "POST" });
      setActionSuccess("Session successfully revoked.");
      loadSessions();
      loadOverview();
    } catch (e: any) {
      setActionError(e.message || "Failed to revoke session.");
    }
  };

  const handleGlobalLogout = async () => {
    if (!confirm("Are you sure you want to invalidate all active sessions across your agency? Users will be required to re-authenticate.")) return;
    clearMessages();
    try {
      await apiClient("/governance/sessions/global-logout", { method: "POST" });
      setActionSuccess("Global logout executed. All active tokens have been invalidated.");
      loadSessions();
      loadOverview();
    } catch (e: any) {
      setActionError(e.message || "Failed to execute global logout.");
    }
  };

  // Actions: Privacy & Legal Hold
  const handleUpdatePrivacyStatus = async (
    requestId: string,
    status: PrivacyRequestStatus,
    resolutionNotes?: string
  ) => {
    clearMessages();
    try {
      await apiClient(`/governance/privacy-requests/${requestId}`, {
        method: "PATCH",
        body: JSON.stringify({ status, resolution_notes: resolutionNotes || `Processed as ${status}` }),
      });
      setActionSuccess(`Privacy request updated to ${status}.`);
      loadPrivacyRequests();
      loadOverview();
    } catch (e: any) {
      setActionError(e.message || "Failed to update request.");
    }
  };

  const handleToggleLegalHold = async () => {
    if (!legalHoldModal) return;
    clearMessages();
    try {
      const newHoldState = !legalHoldModal.has_legal_hold;
      await apiClient(`/governance/privacy-requests/${legalHoldModal.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          has_legal_hold: newHoldState,
          legal_hold_reason: newHoldState ? legalHoldReason : null,
        }),
      });
      setActionSuccess(newHoldState ? "Legal hold applied. Deletion blocked." : "Legal hold removed.");
      setLegalHoldModal(null);
      setLegalHoldReason("");
      loadPrivacyRequests();
      loadOverview();
    } catch (e: any) {
      setActionError(e.message || "Failed to toggle legal hold.");
    }
  };

  // Actions: Consent
  const handleWithdrawConsent = async (consentId: string) => {
    if (!confirm("Withdraw consent for this candidate? Processing under this purpose will be restricted.")) return;
    clearMessages();
    try {
      await apiClient(`/governance/consent-records/${consentId}/withdraw`, { method: "POST" });
      setActionSuccess("Consent withdrawn successfully.");
      loadConsentRecords();
    } catch (e: any) {
      setActionError(e.message || "Failed to withdraw consent.");
    }
  };

  // Actions: AI Policy
  const handleSaveAIPolicy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!aiPolicy) return;
    setSavingAIPolicy(true);
    clearMessages();
    try {
      const updated = await apiClient<AIGovernancePolicyRead>("/governance/ai-policy", {
        method: "PUT",
        body: JSON.stringify({
          allowed_providers: aiPolicy.allowed_providers,
          max_tokens_per_request: aiPolicy.max_tokens_per_request,
          monthly_token_budget: aiPolicy.monthly_token_budget,
          require_pii_masking: aiPolicy.require_pii_masking,
          safety_filter_enabled: aiPolicy.safety_filter_enabled,
        }),
      });
      setAiPolicy(updated);
      setActionSuccess("AI Governance policy saved successfully.");
      loadAIData();
    } catch (e: any) {
      setActionError(e.message || "Failed to update AI policy.");
    } finally {
      setSavingAIPolicy(false);
    }
  };

  // Actions: Retention
  const handleRetentionDryRun = async (category: RetentionCategory) => {
    setPreviewingCategory(category);
    clearMessages();
    try {
      const res: RetentionDryRunPreview = await apiClient(`/governance/retention-policies/${category}/dry-run`);
      setDryRunPreview(res);
    } catch (e: any) {
      setActionError(e.message || "Dry-run preview failed.");
    } finally {
      setPreviewingCategory(null);
    }
  };

  const handleExecuteRetention = async (category: RetentionCategory) => {
    if (!confirm(`Are you sure you want to execute LIVE data retention for ${category}? Eligible records will be processed according to configured retention action. This operation is immutable.`)) return;
    clearMessages();
    try {
      const res = await apiClient<{ affected: number; exempt: number }>(`/governance/retention-policies/${category}/execute`, {
        method: "POST",
      });
      setActionSuccess(`Retention sweep executed. ${res.affected} records affected, ${res.exempt} records protected under legal hold.`);
      setDryRunPreview(null);
      loadRetentionData();
      loadOverview();
    } catch (e: any) {
      setActionError(e.message || "Retention execution failed.");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <ShieldCheck className="w-7 h-7 text-indigo-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Enterprise Security, Compliance & Governance
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Complete visibility over security audits, session access, candidate privacy requests, AI telemetry, and lifecycle data retention.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
            <Lock className="w-3.5 h-3.5 mr-1" />
            ISO 27001 / SOC 2 Ready
          </span>
          <button
            onClick={() => {
              loadOverview();
              if (activeTab === "audit") loadAuditEvents();
              if (activeTab === "sessions") loadSessions();
              if (activeTab === "privacy") loadPrivacyRequests();
              if (activeTab === "consent") loadConsentRecords();
              if (activeTab === "ai") loadAIData();
              if (activeTab === "retention") loadRetentionData();
            }}
            className="p-2 text-slate-500 hover:text-slate-900 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
            title="Refresh workspace"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Global Alerts */}
      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start space-x-2.5 animate-in fade-in-50">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">{actionSuccess}</p>
          </div>
          <button onClick={() => setActionSuccess(null)} className="text-emerald-700 hover:text-emerald-900 font-bold">&times;</button>
        </div>
      )}

      {actionError && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-2.5 animate-in fade-in-50">
          <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Security Operation Warning</p>
            <p className="text-xs text-rose-700 mt-0.5">{actionError}</p>
          </div>
          <button onClick={() => setActionError(null)} className="text-rose-700 hover:text-rose-900 font-bold">&times;</button>
        </div>
      )}

      {/* Navigation Tabs */}
      <div className="flex overflow-x-auto border-b border-slate-200 gap-2 pb-px text-sm font-medium">
        {[
          { id: "overview", label: "Overview", icon: ShieldCheck },
          { id: "audit", label: "Audit Event Explorer", icon: Eye },
          { id: "sessions", label: "Session & Access", icon: Laptop },
          { id: "privacy", label: "Privacy & Legal Holds", icon: UserCheck },
          { id: "consent", label: "Consent Registry", icon: CheckCircle2 },
          { id: "ai", label: "AI Governance & Usage", icon: Cpu },
          { id: "retention", label: "Data Retention & Lifecycle", icon: Archive },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as SecurityTab)}
              className={`flex items-center space-x-2 px-4 py-2.5 border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? "border-indigo-600 text-indigo-600 font-semibold bg-indigo-50/50"
                  : "border-transparent text-slate-500 hover:text-slate-900 hover:border-slate-300"
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* =========================================================================
          TAB 0: OVERVIEW
      ========================================================================= */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {loadingOverview ? (
            <div className="p-8 text-center text-slate-500">Loading governance metrics...</div>
          ) : overview ? (
            <>
              {/* Metric Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Active Sessions</span>
                    <Laptop className="w-5 h-5 text-indigo-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">
                    {overview.active_sessions_count}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Live authorized devices</p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Security Events (24h)</span>
                    <Eye className="w-5 h-5 text-blue-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">
                    {overview.security_events_last_24h}
                  </div>
                  <div className="flex items-center text-xs mt-1">
                    <span className={overview.critical_events_count > 0 ? "text-rose-600 font-semibold" : "text-emerald-600"}>
                      {overview.critical_events_count} critical alerts
                    </span>
                  </div>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Privacy & Legal Holds</span>
                    <UserCheck className="w-5 h-5 text-amber-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">
                    {overview.pending_privacy_requests}
                  </div>
                  <p className="text-xs text-amber-600 font-medium mt-1">
                    {overview.active_legal_holds} active legal holds
                  </p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 uppercase">AI Token Budget</span>
                    <Cpu className="w-5 h-5 text-purple-500" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900 mt-2">
                    {overview.ai_budget_utilization_pct.toFixed(1)}%
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {overview.ai_monthly_token_consumption.toLocaleString()} tokens consumed
                  </p>
                </div>
              </div>

              {/* Compliance Badges & Posture */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
                <h2 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  <span>Enterprise Compliance Readiness</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="font-semibold text-sm text-slate-800">DPDP Act (India) Compliant Architecture</div>
                    <p className="text-xs text-slate-500 mt-1">
                      Candidate consent timestamps, withdrawal logs, explicit purpose tagging, and right-to-erasure workflows with legal hold safeguarding.
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="font-semibold text-sm text-slate-800">Server-Side Session Revocation</div>
                    <p className="text-xs text-slate-500 mt-1">
                      Stateless JWT tokens are cryptographically paired with active server-side database sessions (`sid`), guaranteeing instantaneous revocation upon logout.
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 border border-slate-100">
                    <div className="font-semibold text-sm text-slate-800">Automated Data Retention & Dry-Runs</div>
                    <p className="text-xs text-slate-500 mt-1">
                      Multi-category lifecycle retention policies with Celery automation, dry-run simulation, and immutable audit logs.
                    </p>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* =========================================================================
          TAB 1: AUDIT EVENT EXPLORER
      ========================================================================= */}
      {activeTab === "audit" && (
        <div className="space-y-4">
          {/* Filters */}
          <div className="flex flex-col sm:flex-row gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-600 block mb-1">Event Category</label>
              <select
                value={auditCategory}
                onChange={(e) => {
                  setAuditCategory(e.target.value);
                  setAuditPage(1);
                }}
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Categories</option>
                <option value="AUTH">Authentication (AUTH)</option>
                <option value="ACCESS_CONTROL">Access Control</option>
                <option value="DATA_ACCESS">Data Access</option>
                <option value="DATA_EXPORT">Data Export</option>
                <option value="ADMIN_ACTION">Admin Actions</option>
                <option value="PRIVACY_OP">Privacy & Consent</option>
                <option value="RETENTION_OP">Retention Operations</option>
                <option value="AI_GOVERNANCE">AI Governance</option>
              </select>
            </div>

            <div className="flex-1">
              <label className="text-xs font-semibold text-slate-600 block mb-1">Severity</label>
              <select
                value={auditSeverity}
                onChange={(e) => {
                  setAuditSeverity(e.target.value);
                  setAuditPage(1);
                }}
                className="w-full text-sm border border-slate-300 rounded-lg p-2 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">All Severities</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>
          </div>

          {/* Audit Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex justify-between items-center">
              <h3 className="font-semibold text-slate-900 text-sm">Security Audit Trail ({auditTotal} events)</h3>
              <span className="text-xs text-slate-500">Immutable write-once log</span>
            </div>

            {loadingAudit ? (
              <div className="p-8 text-center text-slate-500">Loading audit events...</div>
            ) : auditEvents.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No audit events match your filters.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Timestamp (IST)</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Severity</th>
                      <th className="px-4 py-3">Actor</th>
                      <th className="px-4 py-3">IP / Details</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {auditEvents.map((e) => (
                      <tr key={e.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap font-medium text-slate-800">
                          {formatIST(e.created_at)}
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span className="inline-block px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-800">
                            {e.event_category}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-semibold text-slate-900">{e.action}</td>
                        <td className="px-4 py-3 whitespace-nowrap">
                          <span
                            className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                              e.severity === "CRITICAL"
                                ? "bg-rose-100 text-rose-800"
                                : e.severity === "HIGH"
                                ? "bg-amber-100 text-amber-800"
                                : e.severity === "MEDIUM"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {e.severity}
                          </span>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap text-slate-700">
                          {e.actor_email || "System"}
                        </td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => setSelectedAudit(e)}
                            className="text-indigo-600 hover:text-indigo-800 font-semibold underline"
                          >
                            View Metadata
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {auditTotal > 20 && (
              <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex justify-between items-center text-xs text-slate-600">
                <span>
                  Showing page {auditPage} of {Math.ceil(auditTotal / 20)}
                </span>
                <div className="flex space-x-2">
                  <button
                    disabled={auditPage <= 1}
                    onClick={() => setAuditPage((p) => p - 1)}
                    className="px-2.5 py-1 bg-white border border-slate-300 rounded disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    disabled={auditPage * 20 >= auditTotal}
                    onClick={() => setAuditPage((p) => p + 1)}
                    className="px-2.5 py-1 bg-white border border-slate-300 rounded disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Audit Details Modal */}
          {selectedAudit && (
            <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="font-bold text-slate-900">Audit Event Metadata</h3>
                  <button
                    onClick={() => setSelectedAudit(null)}
                    className="text-slate-400 hover:text-slate-600 font-bold"
                  >
                    &times;
                  </button>
                </div>
                <div className="text-xs space-y-2 text-slate-700">
                  <div><strong>ID:</strong> {selectedAudit.id}</div>
                  <div><strong>Action:</strong> {selectedAudit.action}</div>
                  <div><strong>Actor:</strong> {selectedAudit.actor_email || "System"} ({selectedAudit.actor_user_id || "N/A"})</div>
                  <div><strong>Timestamp (IST):</strong> {formatIST(selectedAudit.created_at)}</div>
                  <div><strong>IP Address:</strong> {selectedAudit.ip_address || "N/A"}</div>
                  <div><strong>User Agent:</strong> {selectedAudit.user_agent || "N/A"}</div>
                  <div><strong>Resource:</strong> {selectedAudit.resource_type} ({selectedAudit.resource_id || "N/A"})</div>
                  <div>
                    <strong>Sanitized Payload / Details:</strong>
                    <pre className="mt-1 p-2 bg-slate-50 border rounded text-[11px] overflow-x-auto text-slate-800">
                      {JSON.stringify(selectedAudit.details || {}, null, 2)}
                    </pre>
                  </div>
                </div>
                <div className="pt-2 flex justify-end">
                  <button
                    onClick={() => setSelectedAudit(null)}
                    className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 2: SESSIONS & ACCESS
      ========================================================================= */}
      {activeTab === "sessions" && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Active Authorized Sessions</h3>
              <p className="text-xs text-slate-500">
                Server-side session management. Revoking a session immediately invalidates the associated JWT token.
              </p>
            </div>
            {isOwnerOrAdmin && (
              <button
                onClick={handleGlobalLogout}
                className="px-3.5 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors flex items-center space-x-1.5"
              >
                <Key className="w-3.5 h-3.5" />
                <span>Global Logout (Revoke All)</span>
              </button>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            {loadingSessions ? (
              <div className="p-8 text-center text-slate-500">Loading active sessions...</div>
            ) : sessions.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No active sessions found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">User</th>
                      <th className="px-4 py-3">Role</th>
                      <th className="px-4 py-3">Device / Browser</th>
                      <th className="px-4 py-3">IP Address</th>
                      <th className="px-4 py-3">Last Active (IST)</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {sessions.map((s) => (
                      <tr key={s.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-900">{s.user_email}</td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                            {s.user_role}
                          </span>
                        </td>
                        <td className="px-4 py-3 max-w-xs truncate text-slate-700" title={s.device_info || "Unknown"}>
                          {s.device_info || "Desktop / Browser"}
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-600">{s.ip_address || "127.0.0.1"}</td>
                        <td className="px-4 py-3 whitespace-nowrap">{formatIST(s.last_activity_at)}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            s.is_active ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-500"
                          }`}>
                            {s.is_active ? "ACTIVE" : "REVOKED"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {s.is_active && (
                            <button
                              onClick={() => handleRevokeSession(s.id)}
                              className="px-2.5 py-1 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50 border border-rose-200 rounded font-medium transition-colors"
                            >
                              Revoke
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 3: PRIVACY REQUESTS & LEGAL HOLDS
      ========================================================================= */}
      {activeTab === "privacy" && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Candidate Privacy Requests & Legal Holds</h3>
              <p className="text-xs text-slate-500">
                Process candidate rights requests (access, correction, erasure). Active legal holds strictly prevent data destruction.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            {loadingPrivacy ? (
              <div className="p-8 text-center text-slate-500">Loading privacy requests...</div>
            ) : privacyRequests.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No privacy requests in queue.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Created (IST)</th>
                      <th className="px-4 py-3">Candidate</th>
                      <th className="px-4 py-3">Request Type</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Legal Hold</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {privacyRequests.map((pr) => (
                      <tr key={pr.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap">{formatIST(pr.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900">{pr.candidate_name || pr.requested_by_email}</div>
                          <div className="text-[11px] text-slate-500">{pr.requested_by_email}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-slate-800">{pr.request_type}</span>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            pr.status === "COMPLETED"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : pr.status === "REJECTED"
                              ? "bg-rose-50 text-rose-700 border border-rose-200"
                              : "bg-amber-50 text-amber-700 border border-amber-200"
                          }`}>
                            {pr.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {pr.has_legal_hold ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800 border border-rose-300">
                              <ShieldAlert className="w-3 h-3 mr-1" />
                              HOLD ACTIVE
                            </span>
                          ) : (
                            <span className="text-slate-400 text-xs">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-right space-x-1">
                          {isOwnerOrAdmin && (
                            <>
                              <button
                                onClick={() => {
                                  setLegalHoldModal(pr);
                                  setLegalHoldReason(pr.legal_hold_reason || "");
                                }}
                                className="px-2 py-1 text-xs border border-slate-300 rounded hover:bg-slate-50"
                              >
                                {pr.has_legal_hold ? "Edit Hold" : "Apply Hold"}
                              </button>
                              {pr.status === "PENDING" && (
                                <button
                                  onClick={() => handleUpdatePrivacyStatus(pr.id, "COMPLETED")}
                                  className="px-2 py-1 text-xs bg-indigo-50 border border-indigo-200 text-indigo-700 rounded hover:bg-indigo-100 font-medium"
                                >
                                  Fulfill Request
                                </button>
                              )}
                            </>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Legal Hold Modal */}
          {legalHoldModal && (
            <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6 space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="font-bold text-slate-900 flex items-center space-x-2">
                    <ShieldAlert className="w-5 h-5 text-amber-600" />
                    <span>Legal Hold Management</span>
                  </h3>
                  <button onClick={() => setLegalHoldModal(null)} className="text-slate-400 font-bold">&times;</button>
                </div>
                <div className="text-xs text-slate-600 space-y-3">
                  <p>
                    Applying a legal hold preserves all records associated with candidate <strong>{legalHoldModal.candidate_name || legalHoldModal.requested_by_email}</strong>. Deletion or anonymization sweeps will strictly exempt this candidate.
                  </p>
                  <div>
                    <label className="font-semibold block mb-1">Reason for Legal Hold:</label>
                    <textarea
                      rows={3}
                      value={legalHoldReason}
                      onChange={(e) => setLegalHoldReason(e.target.value)}
                      placeholder="e.g., Active litigation, compliance review, pending audit inquiry..."
                      className="w-full border border-slate-300 rounded p-2 text-xs"
                    />
                  </div>
                </div>
                <div className="flex justify-between pt-2">
                  <button
                    onClick={() => setLegalHoldModal(null)}
                    className="px-3 py-1.5 border border-slate-300 text-xs rounded hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleToggleLegalHold}
                    className={`px-4 py-1.5 text-xs font-semibold rounded text-white ${
                      legalHoldModal.has_legal_hold ? "bg-slate-700 hover:bg-slate-800" : "bg-rose-600 hover:bg-rose-700"
                    }`}
                  >
                    {legalHoldModal.has_legal_hold ? "Remove Legal Hold" : "Enforce Legal Hold"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 4: CONSENT REGISTRY
      ========================================================================= */}
      {activeTab === "consent" && (
        <div className="space-y-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Candidate Consent Registry</h3>
              <p className="text-xs text-slate-500">
                Auditable records of candidate consent grants, policy versions, and withdrawal timestamps.
              </p>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            {loadingConsent ? (
              <div className="p-8 text-center text-slate-500">Loading consent records...</div>
            ) : consentRecords.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No consent records found.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Granted (IST)</th>
                      <th className="px-4 py-3">Candidate</th>
                      <th className="px-4 py-3">Consent Type</th>
                      <th className="px-4 py-3">Policy Version</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {consentRecords.map((cr) => (
                      <tr key={cr.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap">{formatIST(cr.granted_at)}</td>
                        <td className="px-4 py-3">
                          <div className="font-semibold text-slate-900">{cr.candidate_name || "Candidate"}</div>
                          <div className="text-[11px] text-slate-500">{cr.candidate_email}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className="font-medium text-slate-800">{cr.consent_type}</span>
                        </td>
                        <td className="px-4 py-3 font-mono text-slate-500">{cr.policy_version}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            cr.is_granted ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-500"
                          }`}>
                            {cr.is_granted ? "ACTIVE" : `WITHDRAWN (${formatIST(cr.withdrawn_at)})`}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right">
                          {cr.is_granted && isOwnerOrAdmin && (
                            <button
                              onClick={() => handleWithdrawConsent(cr.id)}
                              className="px-2 py-1 text-xs border border-rose-200 text-rose-600 rounded hover:bg-rose-50"
                            >
                              Withdraw
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* =========================================================================
          TAB 5: AI GOVERNANCE & USAGE CONTROLS
      ========================================================================= */}
      {activeTab === "ai" && (
        <div className="space-y-6">
          {loadingAI ? (
            <div className="p-8 text-center text-slate-500">Loading AI governance metrics...</div>
          ) : (
            <>
              {/* Telemetry Summary */}
              {aiUsage && (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Monthly Consumption</span>
                    <div className="text-2xl font-bold text-slate-900 mt-2">
                      {aiUsage.total_tokens.toLocaleString()}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">Tokens consumed this cycle</p>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Budget Cap</span>
                    <div className="text-2xl font-bold text-slate-900 mt-2">
                      {aiUsage.monthly_budget.toLocaleString()}
                    </div>
                    <div className="text-xs text-indigo-600 font-semibold mt-1">
                      {aiUsage.budget_utilization_pct.toFixed(1)}% utilized
                    </div>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Provider Fallbacks</span>
                    <div className="text-2xl font-bold text-slate-900 mt-2">{aiUsage.fallback_count}</div>
                    <p className="text-xs text-slate-500 mt-1">Automatic failovers</p>
                  </div>

                  <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Safety Blocks</span>
                    <div className="text-2xl font-bold text-slate-900 mt-2">{aiUsage.safety_block_count}</div>
                    <p className="text-xs text-emerald-600 font-medium mt-1">PII / prompt safety activations</p>
                  </div>
                </div>
              )}

              {/* Policy Configuration Form */}
              {aiPolicy && (
                <form onSubmit={handleSaveAIPolicy} className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
                  <div className="border-b pb-4">
                    <h3 className="font-bold text-slate-900 text-base flex items-center space-x-2">
                      <Cpu className="w-5 h-5 text-indigo-600" />
                      <span>AI Model & Provider Governance Policy</span>
                    </h3>
                    <p className="text-xs text-slate-500 mt-1">
                      Control which AI backends are permitted, enforce token limits, and mandate PII sanitization.
                    </p>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="text-xs font-semibold text-slate-700 block mb-2">Permitted AI Providers</label>
                      <div className="space-y-2">
                        {["OLLAMA", "HOSTED_OPEN_WEIGHT", "DEEPSEEK", "ANTHROPIC"].map((p) => {
                          const isChecked = aiPolicy.allowed_providers.includes(p);
                          return (
                            <label key={p} className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                              <input
                                type="checkbox"
                                disabled={!isOwnerOrAdmin}
                                checked={isChecked}
                                onChange={(e) => {
                                  let next = [...aiPolicy.allowed_providers];
                                  if (e.target.checked) next.push(p);
                                  else next = next.filter((item) => item !== p);
                                  setAiPolicy({ ...aiPolicy, allowed_providers: next });
                                }}
                                className="rounded text-indigo-600 focus:ring-indigo-500"
                              />
                              <span className="font-medium">{p}</span>
                            </label>
                          );
                        })}
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <label className="text-xs font-semibold text-slate-700 block mb-1">
                          Max Tokens Per Request
                        </label>
                        <input
                          type="number"
                          disabled={!isOwnerOrAdmin}
                          value={aiPolicy.max_tokens_per_request}
                          onChange={(e) =>
                            setAiPolicy({ ...aiPolicy, max_tokens_per_request: parseInt(e.target.value) || 1000 })
                          }
                          className="w-full text-xs border border-slate-300 rounded p-2"
                        />
                      </div>

                      <div>
                        <label className="text-xs font-semibold text-slate-700 block mb-1">
                          Monthly Token Cap
                        </label>
                        <input
                          type="number"
                          disabled={!isOwnerOrAdmin}
                          value={aiPolicy.monthly_token_budget}
                          onChange={(e) =>
                            setAiPolicy({ ...aiPolicy, monthly_token_budget: parseInt(e.target.value) || 100000 })
                          }
                          className="w-full text-xs border border-slate-300 rounded p-2"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="border-t pt-4 flex flex-col sm:flex-row gap-4">
                    <label className="flex items-center space-x-2 text-xs text-slate-700">
                      <input
                        type="checkbox"
                        disabled={!isOwnerOrAdmin}
                        checked={aiPolicy.require_pii_masking}
                        onChange={(e) => setAiPolicy({ ...aiPolicy, require_pii_masking: e.target.checked })}
                        className="rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="font-semibold">Mandate Candidate PII Masking Before AI Inference</span>
                    </label>

                    <label className="flex items-center space-x-2 text-xs text-slate-700">
                      <input
                        type="checkbox"
                        disabled={!isOwnerOrAdmin}
                        checked={aiPolicy.safety_filter_enabled}
                        onChange={(e) => setAiPolicy({ ...aiPolicy, safety_filter_enabled: e.target.checked })}
                        className="rounded text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="font-semibold">Enable Anti-Injection & Safety Guardrails</span>
                    </label>
                  </div>

                  {isOwnerOrAdmin && (
                    <div className="flex justify-end pt-2">
                      <button
                        type="submit"
                        disabled={savingAIPolicy}
                        className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
                      >
                        {savingAIPolicy ? "Saving Policy..." : "Update AI Policy"}
                      </button>
                    </div>
                  )}
                </form>
              )}
            </>
          )}
        </div>
      )}

      {/* =========================================================================
          TAB 6: DATA RETENTION & LIFECYCLE
      ========================================================================= */}
      {activeTab === "retention" && (
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs flex justify-between items-center">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">Automated Data Retention & Lifecycle Policies</h3>
              <p className="text-xs text-slate-500">
                Safe preview dry-run support, explicit legal-hold exemptions, and automated Celery execution.
              </p>
            </div>
          </div>

          {/* Retention Policies Table */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h4 className="font-semibold text-slate-900 text-sm">Configured Retention Categories</h4>
            </div>

            {loadingRetention ? (
              <div className="p-8 text-center text-slate-500">Loading retention policies...</div>
            ) : retentionPolicies.length === 0 ? (
              <div className="p-8 text-center text-slate-500">No retention policies configured.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Retention Period</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {retentionPolicies.map((rp) => (
                      <tr key={rp.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 font-semibold text-slate-900">{rp.category}</td>
                        <td className="px-4 py-3">{rp.retention_period_days} Days</td>
                        <td className="px-4 py-3 font-mono">{rp.action}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            rp.is_active ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-slate-100 text-slate-500"
                          }`}>
                            {rp.is_active ? "ACTIVE" : "PAUSED"}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          <button
                            onClick={() => handleRetentionDryRun(rp.category)}
                            disabled={previewingCategory === rp.category}
                            className="px-2.5 py-1 text-xs border border-indigo-200 text-indigo-700 rounded hover:bg-indigo-50 font-medium"
                          >
                            {previewingCategory === rp.category ? "Scanning..." : "Dry-Run Preview"}
                          </button>
                          {isOwnerOrAdmin && (
                            <button
                              onClick={() => handleExecuteRetention(rp.category)}
                              className="px-2.5 py-1 text-xs bg-rose-50 border border-rose-200 text-rose-700 rounded hover:bg-rose-100 font-semibold"
                            >
                              Live Execute
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Dry Run Preview Modal */}
          {dryRunPreview && (
            <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6 space-y-4">
                <div className="flex justify-between items-center border-b pb-3">
                  <h3 className="font-bold text-slate-900 flex items-center space-x-2">
                    <Archive className="w-5 h-5 text-indigo-600" />
                    <span>Dry-Run Preview: {dryRunPreview.category}</span>
                  </h3>
                  <button onClick={() => setDryRunPreview(null)} className="text-slate-400 font-bold">&times;</button>
                </div>
                <div className="text-xs text-slate-700 space-y-3">
                  <div className="p-3 bg-amber-50 border border-amber-200 rounded text-amber-800">
                    <p className="font-semibold">{dryRunPreview.preview_notice}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-50 rounded border">
                      <span className="text-slate-500">Cutoff Date (IST):</span>
                      <div className="font-semibold text-slate-900 mt-1">{formatIST(dryRunPreview.cutoff_date)}</div>
                    </div>
                    <div className="p-3 bg-slate-50 rounded border">
                      <span className="text-slate-500">Configured Action:</span>
                      <div className="font-semibold text-slate-900 mt-1">{dryRunPreview.action}</div>
                    </div>
                    <div className="p-3 bg-slate-50 rounded border">
                      <span className="text-slate-500">Records Eligible:</span>
                      <div className="font-bold text-indigo-600 text-lg mt-1">{dryRunPreview.eligible_count}</div>
                    </div>
                    <div className="p-3 bg-slate-50 rounded border">
                      <span className="text-slate-500">Exempt (Legal Holds):</span>
                      <div className="font-bold text-rose-600 text-lg mt-1">{dryRunPreview.exempt_legal_hold_count}</div>
                    </div>
                  </div>
                </div>
                <div className="flex justify-between pt-2">
                  <button
                    onClick={() => setDryRunPreview(null)}
                    className="px-4 py-2 border border-slate-300 rounded text-xs text-slate-700 hover:bg-slate-50"
                  >
                    Close Preview
                  </button>
                  {isOwnerOrAdmin && (
                    <button
                      onClick={() => handleExecuteRetention(dryRunPreview.category)}
                      className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded text-xs font-semibold"
                    >
                      Execute Live Sweep
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Retention Execution History Logs */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200">
              <h4 className="font-semibold text-slate-900 text-sm">Retention Execution History</h4>
            </div>

            {retentionLogs.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-xs">No prior retention sweeps recorded.</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs text-slate-600">
                  <thead className="bg-slate-50 text-slate-700 uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-3">Timestamp (IST)</th>
                      <th className="px-4 py-3">Category</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Affected</th>
                      <th className="px-4 py-3">Legal Hold Exempt</th>
                      <th className="px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {retentionLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-4 py-3 whitespace-nowrap">{formatIST(log.created_at)}</td>
                        <td className="px-4 py-3 font-semibold text-slate-800">{log.category}</td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700">
                            {log.execution_type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono">{log.action_taken}</td>
                        <td className="px-4 py-3 font-semibold text-indigo-600">{log.records_affected}</td>
                        <td className="px-4 py-3 font-semibold text-rose-600">{log.records_exempted_legal_hold}</td>
                        <td className="px-4 py-3">
                          <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                            log.status === "SUCCESS"
                              ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                              : "bg-rose-50 text-rose-700 border border-rose-200"
                          }`}>
                            {log.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  ShieldAlert,
  Building,
  Users,
  CreditCard,
  Activity,
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  Server,
  Database,
  HardDrive,
  FileText,
  Lock,
  Eye,
  Sliders,
  DollarSign,
  TrendingUp,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface PlatformOverview {
  total_agencies: number;
  active_agencies: number;
  suspended_agencies: number;
  total_users: number;
  active_users: number;
  total_jobs: number;
  active_jobs: number;
  total_candidates: number;
  total_applications: number;
  total_interviews: number;
  total_resumes_processed: number;
  subscriptions_by_tier: Record<string, number>;
  subscriptions_by_status: Record<string, number>;

  mrr_inr: number;
  mrr_usd: number;
  arr_inr: number;
  arr_usd: number;
  total_revenue_inr: number;
  total_revenue_usd: number;
  total_invoices_paid: number;
  system_status: string;
}

interface PlatformAgency {
  id: string;
  name: string;
  slug: string;
  domain?: string;
  country: string;
  is_active: boolean;
  created_at: string;
  user_count: number;
  job_count: number;
  candidate_count: number;
  current_plan: string;
  subscription_status: string;
}

interface AuditLogItem {
  id: string;
  agency_id: string;
  agency_name?: string;
  actor_user_id?: string;
  actor_email?: string;
  event_category: string;
  severity: string;
  action: string;
  resource_type: string;
  resource_id?: string;
  details?: Record<string, any>;
  ip_address?: string;
  created_at: string;
}

interface SystemHealth {
  status: string;
  database: Record<string, any>;
  redis: Record<string, any>;
  celery: Record<string, any>;
  storage: Record<string, any>;
  timestamp: string;
}

export default function PlatformSuperAdminPage() {
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [activeTab, setActiveTab] = useState<"agencies" | "audits" | "health">("agencies");

  // Overview State
  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState(true);

  // Agencies State
  const [agencies, setAgencies] = useState<PlatformAgency[]>([]);
  const [totalAgencies, setTotalAgencies] = useState(0);
  const [agencyPage, setAgencyPage] = useState(1);
  const [agencySearch, setAgencySearch] = useState("");
  const [agencyStatusFilter, setAgencyStatusFilter] = useState("");
  const [loadingAgencies, setLoadingAgencies] = useState(false);

  // Agency Detail Modal
  const [selectedAgencyDetail, setSelectedAgencyDetail] = useState<any>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Suspend/Reactivate Modal
  const [targetAgency, setTargetAgency] = useState<PlatformAgency | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [actionInProgress, setActionInProgress] = useState(false);

  // Audit Logs State
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditPage, setAuditPage] = useState(1);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditSearch, setAuditSearch] = useState("");
  const [loadingAudits, setLoadingAudits] = useState(false);

  // System Health State
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);

  // Load Current User & Check Permissions
  useEffect(() => {
    async function loadUser() {
      try {
        const u: any = await apiClient("/auth/me");
        setCurrentUser(u);
      } catch (err) {
        console.error("Auth check failed:", err);
      } finally {
        setLoadingUser(false);
      }
    }
    loadUser();
  }, []);

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const data: any = await apiClient("/platform/overview");
      setOverview(data);
    } catch (err) {
      console.error("Failed to load overview:", err);
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  const loadAgencies = useCallback(async () => {
    setLoadingAgencies(true);
    try {
      const params = new URLSearchParams({
        page: agencyPage.toString(),
        page_size: "15",
      });
      if (agencySearch) params.append("search", agencySearch);
      if (agencyStatusFilter) params.append("status", agencyStatusFilter);

      const res: any = await apiClient(`/platform/agencies?${params.toString()}`);
      setAgencies(res.items || []);
      setTotalAgencies(res.total || 0);
    } catch (err) {
      console.error("Failed to load agencies:", err);
    } finally {
      setLoadingAgencies(false);
    }
  }, [agencyPage, agencySearch, agencyStatusFilter]);

  const loadAuditLogs = useCallback(async () => {
    setLoadingAudits(true);
    try {
      const params = new URLSearchParams({
        page: auditPage.toString(),
        page_size: "20",
      });
      if (auditSearch) params.append("search", auditSearch);

      const res: any = await apiClient(`/platform/audit-logs?${params.toString()}`);
      setAuditLogs(res.items || []);
      setAuditTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to load audits:", err);
    } finally {
      setLoadingAudits(false);
    }
  }, [auditPage, auditSearch]);

  const loadHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const res: any = await apiClient("/platform/health");
      setSystemHealth(res);
    } catch (err) {
      console.error("Failed to load health probe:", err);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser?.is_platform_admin) {
      loadOverview();
      loadAgencies();
    }
  }, [currentUser, loadOverview, loadAgencies]);

  useEffect(() => {
    if (currentUser?.is_platform_admin) {
      if (activeTab === "audits") loadAuditLogs();
      if (activeTab === "health") loadHealth();
    }
  }, [activeTab, currentUser, loadAuditLogs, loadHealth]);

  const handleInspectAgency = async (agencyId: string) => {
    setLoadingDetail(true);
    try {
      const data: any = await apiClient(`/platform/agencies/${agencyId}`);
      setSelectedAgencyDetail(data);
    } catch (err) {
      alert("Failed to load agency details.");
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleToggleAgencyStatus = async () => {
    if (!targetAgency || !statusReason.trim()) {
      alert("Please enter a valid justification reason for this administrative action.");
      return;
    }
    setActionInProgress(true);
    try {
      const newStatus = !targetAgency.is_active;
      await apiClient(`/platform/agencies/${targetAgency.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          is_active: newStatus,
          reason: statusReason,
        }),
      });
      alert(`Agency successfully ${newStatus ? "reactivated" : "suspended"}.`);
      setTargetAgency(null);
      setStatusReason("");
      loadAgencies();
      loadOverview();
    } catch (err: any) {
      alert(err.message || "Action failed.");
    } finally {
      setActionInProgress(false);
    }
  };

  if (loadingUser) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  // Privilege Guard
  if (!currentUser?.is_platform_admin) {
    return (
      <div className="max-w-2xl mx-auto my-16 p-8 bg-white border border-rose-200 rounded-xl shadow-sm text-center">
        <div className="w-16 h-16 bg-rose-50 text-rose-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <ShieldAlert className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Platform Super Admin Required</h1>
        <p className="text-slate-600 mb-6 leading-relaxed">
          Access to the global platform administration control plane is restricted strictly to verified
          Platform Administrators. Ordinary agency owners, recruiters, and tenants cannot access cross-tenant statistics.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800 transition"
        >
          Return to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-16">
      {/* Platform Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-6">
        <div>
          <div className="flex items-center space-x-3 mb-1">
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Global Platform Administration</h1>
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-purple-100 text-purple-800 border border-purple-200">
              PLATFORM SUPER ADMIN
            </span>
          </div>
          <p className="text-sm text-slate-500">
            Multi-tenant SaaS governance, cross-tenant telemetry, agency lifecycle controls, and system operations.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => {
              loadOverview();
              if (activeTab === "agencies") loadAgencies();
              if (activeTab === "audits") loadAuditLogs();
              if (activeTab === "health") loadHealth();
            }}
            className="inline-flex items-center px-3.5 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition"
          >
            <RefreshCw className="w-4 h-4 mr-2 text-slate-500" />
            Refresh Telemetry
          </button>
        </div>
      </div>

      {/* Global Telemetry KPI Cards */}
      {overview && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Agencies Directory</span>
              <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                <Building className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl font-bold text-slate-900">{overview.total_agencies}</span>
              <span className="text-xs text-emerald-600 font-semibold">{overview.active_agencies} active</span>
              {overview.suspended_agencies > 0 && (
                <span className="text-xs text-rose-500 font-semibold">({overview.suspended_agencies} suspended)</span>
              )}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Total Recruiters: <span className="font-semibold text-slate-700">{overview.total_users}</span>
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">MRR / Recurring Rev</span>
              <div className="w-8 h-8 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <TrendingUp className="w-4 h-4" />
              </div>
            </div>
            <div className="space-y-1">
              <div className="text-lg font-bold text-slate-900">
                ₹{overview.mrr_inr.toLocaleString("en-IN")} <span className="text-xs text-slate-500 font-normal">/mo</span>
              </div>
              <div className="text-sm font-semibold text-slate-600">
                ${overview.mrr_usd.toLocaleString("en-US")} <span className="text-xs text-slate-400 font-normal">USD /mo</span>
              </div>
            </div>
            <div className="mt-2 text-xs text-slate-500">
              ARR: ₹{overview.arr_inr.toLocaleString("en-IN")}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Gross Platform Billing</span>
              <div className="w-8 h-8 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center">
                <CreditCard className="w-4 h-4" />
              </div>
            </div>
            <div className="text-lg font-bold text-slate-900">
              ₹{overview.total_revenue_inr.toLocaleString("en-IN")}
            </div>
            <div className="text-xs text-slate-500 mt-1">
              Paid Invoices: <span className="font-semibold text-slate-700">{overview.total_invoices_paid}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {Object.entries(overview.subscriptions_by_tier).map(([tier, count]) => (
                <span key={tier} className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                  {tier}: {count}
                </span>
              ))}
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">System Operational Probe</span>
              <div className="w-8 h-8 rounded-lg bg-teal-50 text-teal-600 flex items-center justify-center">
                <Server className="w-4 h-4" />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="text-base font-bold text-slate-900">{overview.system_status}</span>
            </div>
            <div className="mt-3 text-xs text-slate-500 space-y-0.5">
              <div>Total Resumes: <span className="font-semibold text-slate-700">{overview.total_resumes_processed}</span></div>
              <div>Active Jobs: <span className="font-semibold text-slate-700">{overview.active_jobs}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab("agencies")}
            className={`pb-4 px-1 text-sm font-semibold border-b-2 transition ${
              activeTab === "agencies"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Registered Agencies ({totalAgencies})
          </button>
          <button
            onClick={() => setActiveTab("audits")}
            className={`pb-4 px-1 text-sm font-semibold border-b-2 transition ${
              activeTab === "audits"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Cross-Tenant Audit Explorer
          </button>
          <button
            onClick={() => setActiveTab("health")}
            className={`pb-4 px-1 text-sm font-semibold border-b-2 transition ${
              activeTab === "health"
                ? "border-purple-600 text-purple-600"
                : "border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300"
            }`}
          >
            Infrastructure & Health Probes
          </button>
        </nav>
      </div>

      {/* TAB 1: AGENCIES DIRECTORY */}
      {activeTab === "agencies" && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search agency name, slug, domain..."
                value={agencySearch}
                onChange={(e) => {
                  setAgencySearch(e.target.value);
                  setAgencyPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div className="flex items-center space-x-3 w-full sm:w-auto">
              <select
                value={agencyStatusFilter}
                onChange={(e) => {
                  setAgencyStatusFilter(e.target.value);
                  setAgencyPage(1);
                }}
                className="px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-purple-500"
              >
                <option value="">All Statuses</option>
                <option value="ACTIVE">Active Only</option>
                <option value="SUSPENDED">Suspended Only</option>
              </select>
            </div>
          </div>

          {/* Agencies Table */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <th className="py-3 px-4">Agency</th>
                    <th className="py-3 px-4">Slug / Domain</th>
                    <th className="py-3 px-4">Country</th>
                    <th className="py-3 px-4">Members</th>
                    <th className="py-3 px-4">Active Jobs</th>
                    <th className="py-3 px-4">Plan Tier</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-sm">
                  {loadingAgencies ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-slate-500">
                        Loading registered agencies...
                      </td>
                    </tr>
                  ) : agencies.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="py-8 text-center text-slate-500">
                        No agencies found matching your search.
                      </td>
                    </tr>
                  ) : (
                    agencies.map((agency) => (
                      <tr key={agency.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-3.5 px-4 font-semibold text-slate-900">
                          {agency.name}
                        </td>
                        <td className="py-3.5 px-4 font-mono text-xs text-slate-500">
                          /{agency.slug} {agency.domain ? `(${agency.domain})` : ""}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600 font-semibold text-xs">
                          {agency.country}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">
                          {agency.user_count}
                        </td>
                        <td className="py-3.5 px-4 text-slate-600">
                          {agency.job_count}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-800">
                            {agency.current_plan}
                          </span>
                        </td>
                        <td className="py-3.5 px-4">
                          {agency.is_active ? (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                              Active
                            </span>
                          ) : (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">
                              Suspended
                            </span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 text-right space-x-2">
                          <button
                            onClick={() => handleInspectAgency(agency.id)}
                            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded hover:bg-slate-50"
                          >
                            <Eye className="w-3.5 h-3.5 mr-1" />
                            Inspect
                          </button>
                          <button
                            onClick={() => {
                              setTargetAgency(agency);
                              setStatusReason("");
                            }}
                            className={`inline-flex items-center px-2.5 py-1 text-xs font-medium rounded ${
                              agency.is_active
                                ? "text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100"
                                : "text-emerald-700 bg-emerald-50 border border-emerald-200 hover:bg-emerald-100"
                            }`}
                          >
                            {agency.is_active ? "Suspend" : "Reactivate"}
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalAgencies > 15 && (
              <div className="flex items-center justify-between p-4 border-t border-slate-200 text-sm">
                <span className="text-slate-500">
                  Showing {(agencyPage - 1) * 15 + 1} to {Math.min(agencyPage * 15, totalAgencies)} of {totalAgencies} agencies
                </span>
                <div className="flex space-x-2">
                  <button
                    disabled={agencyPage <= 1}
                    onClick={() => setAgencyPage((p) => p - 1)}
                    className="px-3 py-1 border border-slate-300 rounded bg-white text-slate-700 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    disabled={agencyPage * 15 >= totalAgencies}
                    onClick={() => setAgencyPage((p) => p + 1)}
                    className="px-3 py-1 border border-slate-300 rounded bg-white text-slate-700 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AUDIT LOG EXPLORER */}
      {activeTab === "audits" && (
        <div className="space-y-4">
          <div className="flex gap-3 bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
              <input
                type="text"
                placeholder="Search action, actor email, resource..."
                value={auditSearch}
                onChange={(e) => {
                  setAuditSearch(e.target.value);
                  setAuditPage(1);
                }}
                className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                    <th className="py-3 px-4">Timestamp (IST)</th>
                    <th className="py-3 px-4">Agency</th>
                    <th className="py-3 px-4">Actor</th>
                    <th className="py-3 px-4">Category</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Action</th>
                    <th className="py-3 px-4">Resource</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 text-xs font-mono">
                  {loadingAudits ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                        Loading cross-tenant audit events...
                      </td>
                    </tr>
                  ) : auditLogs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                        No security audit logs found.
                      </td>
                    </tr>
                  ) : (
                    auditLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50/60 transition">
                        <td className="py-3 px-4 text-slate-500 whitespace-nowrap">
                          {new Date(log.created_at).toLocaleString("en-IN", {
                            timeZone: "Asia/Kolkata",
                          })}
                        </td>
                        <td className="py-3 px-4 font-sans font-semibold text-slate-900">
                          {log.agency_name || "Unknown"}
                        </td>
                        <td className="py-3 px-4 text-slate-600">
                          {log.actor_email || "System"}
                        </td>
                        <td className="py-3 px-4">
                          <span className="font-sans font-semibold px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-700">
                            {log.event_category}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`font-sans font-bold px-2 py-0.5 rounded text-[10px] uppercase ${
                              log.severity === "HIGH" || log.severity === "CRITICAL"
                                ? "bg-rose-100 text-rose-800"
                                : log.severity === "MEDIUM"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-slate-100 text-slate-700"
                            }`}
                          >
                            {log.severity}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-semibold text-slate-800">
                          {log.action}
                        </td>
                        <td className="py-3 px-4 text-slate-500">
                          {log.resource_type} {log.resource_id ? `#${log.resource_id.substring(0, 8)}` : ""}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: INFRASTRUCTURE & HEALTH PROBES */}
      {activeTab === "health" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-slate-900">System Infrastructure Probes</h2>
              <p className="text-sm text-slate-500">Direct operational metrics across relational database, broker, and storage volumes.</p>
            </div>
            <button
              onClick={loadHealth}
              disabled={loadingHealth}
              className="inline-flex items-center px-3 py-1.5 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 font-medium"
            >
              <RefreshCw className={`w-4 h-4 mr-1.5 ${loadingHealth ? "animate-spin" : ""}`} />
              Re-probe
            </button>
          </div>

          {systemHealth && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <Database className="w-5 h-5 text-blue-600" />
                    <h3 className="font-semibold text-slate-900">Relational Database</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-emerald-100 text-emerald-800">
                    {systemHealth.database.status}
                  </span>
                </div>
                <div className="text-sm space-y-2 text-slate-600 font-mono text-xs">
                  <div>Dialect: <span className="font-semibold text-slate-900">{systemHealth.database.dialect}</span></div>
                  <div>Query Latency: <span className="font-semibold text-slate-900">{systemHealth.database.latency_ms} ms</span></div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <Server className="w-5 h-5 text-purple-600" />
                    <h3 className="font-semibold text-slate-900">Redis & Task Broker</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-blue-100 text-blue-800">
                    {systemHealth.redis.status}
                  </span>
                </div>
                <div className="text-sm space-y-2 text-slate-600 font-mono text-xs">
                  <div>Broker URL: <span className="font-semibold text-slate-900">{systemHealth.redis.broker_url}</span></div>
                  <div>Celery Status: <span className="font-semibold text-slate-900">{systemHealth.celery.status}</span></div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <HardDrive className="w-5 h-5 text-emerald-600" />
                    <h3 className="font-semibold text-slate-900">Resume & Document Storage</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-emerald-100 text-emerald-800">
                    {systemHealth.storage.status}
                  </span>
                </div>
                <div className="text-sm space-y-2 text-slate-600 font-mono text-xs">
                  <div>Storage Type: <span className="font-semibold text-slate-900">{systemHealth.storage.type}</span></div>
                  <div>Local Path: <span className="font-semibold text-slate-900">{systemHealth.storage.path}</span></div>
                  <div>Free Disk Space: <span className="font-semibold text-slate-900">{systemHealth.storage.free_mb} MB</span></div>
                </div>
              </div>

              <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <Activity className="w-5 h-5 text-amber-600" />
                    <h3 className="font-semibold text-slate-900">Probe Metadata</h3>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-bold uppercase bg-emerald-100 text-emerald-800">
                    ONLINE
                  </span>
                </div>
                <div className="text-sm space-y-2 text-slate-600 font-mono text-xs">
                  <div>Timestamp: <span className="font-semibold text-slate-900">{systemHealth.timestamp}</span></div>
                  <div>Overall Health: <span className="font-semibold text-emerald-600">{systemHealth.status}</span></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* SUSPEND / REACTIVATE MODAL */}
      {targetAgency && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
            <h3 className="text-lg font-bold text-slate-900 mb-2">
              {targetAgency.is_active ? "Suspend Agency Tenant" : "Reactivate Agency Tenant"}
            </h3>
            <p className="text-sm text-slate-600 mb-4">
              {targetAgency.is_active
                ? `Suspending "${targetAgency.name}" immediately blocks all associated recruiters from logging in or executing actions.`
                : `Reactivating "${targetAgency.name}" restores immediate access for all its recruiters.`}
            </p>
            <div className="mb-4">
              <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                Audit Reason / Justification *
              </label>
              <textarea
                rows={3}
                required
                value={statusReason}
                onChange={(e) => setStatusReason(e.target.value)}
                placeholder="Provide compliance or operational rationale for this privileged action..."
                className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              />
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setTargetAgency(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-sm text-slate-700 font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                disabled={actionInProgress || !statusReason.trim()}
                onClick={handleToggleAgencyStatus}
                className={`px-4 py-2 rounded-lg text-sm font-semibold text-white ${
                  targetAgency.is_active ? "bg-rose-600 hover:bg-rose-700" : "bg-emerald-600 hover:bg-emerald-700"
                } disabled:opacity-50`}
              >
                {actionInProgress ? "Applying..." : targetAgency.is_active ? "Confirm Suspension" : "Confirm Reactivation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* INSPECT AGENCY MODAL */}
      {selectedAgencyDetail && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6 shadow-xl border border-slate-200 space-y-6">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <div>
                <h3 className="text-xl font-bold text-slate-900">{selectedAgencyDetail.name}</h3>
                <p className="text-xs font-mono text-slate-500">/{selectedAgencyDetail.slug} • ID: {selectedAgencyDetail.id}</p>
              </div>
              <button
                onClick={() => setSelectedAgencyDetail(null)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {/* Subscription & Profile Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
                <span className="text-xs text-slate-500 uppercase font-semibold">Active Plan</span>
                <p className="text-base font-bold text-slate-900 mt-1">
                  {selectedAgencyDetail.subscription?.plan_name || "Free"}
                </p>
                <span className="text-xs text-emerald-600 font-medium">
                  Status: {selectedAgencyDetail.subscription?.status || "ACTIVE"}
                </span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
                <span className="text-xs text-slate-500 uppercase font-semibold">Recruiting Volume</span>
                <p className="text-base font-bold text-slate-900 mt-1">
                  {selectedAgencyDetail.active_jobs_count} Jobs
                </p>
                <span className="text-xs text-slate-500 font-medium">
                  {selectedAgencyDetail.total_candidates_count} Candidates
                </span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
                <span className="text-xs text-slate-500 uppercase font-semibold">Billing GSTIN</span>
                <p className="text-sm font-mono font-bold text-slate-900 mt-1">
                  {selectedAgencyDetail.billing_profile?.gstin || "Not Registered"}
                </p>
                <span className="text-xs text-slate-500 font-medium">
                  {selectedAgencyDetail.country}
                </span>
              </div>
            </div>

            {/* Members Roster */}
            <div>
              <h4 className="text-sm font-bold text-slate-900 uppercase mb-3">Team Members ({selectedAgencyDetail.users.length})</h4>
              <div className="border border-slate-200 rounded-lg overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500">
                    <tr>
                      <th className="py-2.5 px-3">Name</th>
                      <th className="py-2.5 px-3">Email</th>
                      <th className="py-2.5 px-3">Role</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {selectedAgencyDetail.users.map((u: any) => (
                      <tr key={u.id}>
                        <td className="py-2 px-3 font-semibold text-slate-800">{u.full_name}</td>
                        <td className="py-2 px-3 text-slate-600 font-mono">{u.email}</td>
                        <td className="py-2 px-3 font-semibold">{u.role}</td>
                        <td className="py-2 px-3">
                          <span className={`px-1.5 py-0.5 rounded ${u.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"}`}>
                            {u.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-slate-200">
              <button
                onClick={() => setSelectedAgencyDetail(null)}
                className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm font-medium hover:bg-slate-800"
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

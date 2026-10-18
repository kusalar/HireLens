"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Settings,
  Bell,
  Mail,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ShieldAlert,
  Save,
  Globe,
  RefreshCw,
  Lock,
  CreditCard,
  Building,
  Users,
  Plus,
  Trash2,
  TrendingUp,
  UserCheck,
  UserX,
  Briefcase,
  Calendar,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface NotificationPreferences {
  id: string;
  agency_id: string;
  email_enabled: boolean;
  interview_notifications_enabled: boolean;
  application_status_notifications_enabled: boolean;
  candidate_email_updates_enabled: boolean;
  default_timezone: string;
  updated_at: string;
}

interface DeliveryLogItem {
  id: string;
  recipient_email: string;
  event_type: string;
  subject: string;
  provider: string;
  status: string;
  attempt_count: number;
  last_attempt_at?: string;
  delivered_at?: string;
  error_message?: string;
  created_at: string;
  created_at_ist?: string;
}

interface AgencyOverview {
  agency: {
    id: string;
    name: string;
    slug: string;
    domain?: string;
    country: string;
    is_active: boolean;
    created_at: string;
  };
  total_members: number;
  members_by_role: Record<string, number>;
  active_jobs_count: number;
  total_candidates_count: number;
  total_applications_count: number;
  interviews_this_month_count: number;
  subscription_tier: string;
  subscription_status: string;
  billing_interval: string;
  current_period_end?: string;
  soft_quota_warning: boolean;
}

interface MemberItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

interface InvitationItem {
  id: string;
  email: string;
  role: string;
  status: string;
  expires_at: string;
  created_at: string;
}

export default function AgencySettingsPage() {
  const [activeTab, setActiveTab] = useState<"overview" | "members" | "preferences" | "logs">("overview");
  const [user, setUser] = useState<any>(null);

  // Agency Overview State
  const [overview, setOverview] = useState<AgencyOverview | null>(null);
  const [loadingOverview, setLoadingOverview] = useState<boolean>(true);

  // Team Members State
  const [members, setMembers] = useState<MemberItem[]>([]);
  const [invitations, setInvitations] = useState<InvitationItem[]>([]);
  const [loadingMembers, setLoadingMembers] = useState<boolean>(false);
  const [showInviteModal, setShowInviteModal] = useState<boolean>(false);
  const [inviteEmail, setInviteEmail] = useState<string>("");
  const [inviteRole, setInviteRole] = useState<string>("RECRUITER");
  const [inviting, setInviting] = useState<boolean>(false);

  // Preferences State
  const [prefs, setPrefs] = useState<NotificationPreferences | null>(null);
  const [loadingPrefs, setLoadingPrefs] = useState<boolean>(false);
  const [savingPrefs, setSavingPrefs] = useState<boolean>(false);
  const [prefSaveSuccess, setPrefSaveSuccess] = useState<boolean>(false);
  const [prefError, setPrefError] = useState<string | null>(null);

  // Delivery Logs State
  const [logs, setLogs] = useState<DeliveryLogItem[]>([]);
  const [logsTotal, setLogsTotal] = useState<number>(0);
  const [logsPage, setLogsPage] = useState<number>(1);
  const [logsPageSize] = useState<number>(20);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loadingLogs, setLoadingLogs] = useState<boolean>(false);
  const [retryingLogId, setRetryingLogId] = useState<string | null>(null);
  const [logsError, setLogsError] = useState<string | null>(null);

  useEffect(() => {
    async function loadUser() {
      try {
        const u: any = await apiClient("/auth/me");
        setUser(u);
      } catch (err) {
        console.error("Failed to load user:", err);
      }
    }
    loadUser();
  }, []);

  const loadOverview = useCallback(async () => {
    setLoadingOverview(true);
    try {
      const data: any = await apiClient("/agency/overview");
      setOverview(data);
    } catch (err) {
      console.error("Failed to load overview:", err);
    } finally {
      setLoadingOverview(false);
    }
  }, []);

  const loadMembersAndInvites = useCallback(async () => {
    setLoadingMembers(true);
    try {
      const [membersData, invitesData]: [any, any] = await Promise.all([
        apiClient("/agency/members"),
        apiClient("/agency/invitations"),
      ]);
      setMembers(membersData || []);
      setInvitations(invitesData || []);
    } catch (err) {
      console.error("Failed to load members:", err);
    } finally {
      setLoadingMembers(false);
    }
  }, []);

  const loadPreferences = useCallback(async () => {
    setLoadingPrefs(true);
    setPrefError(null);
    try {
      const data: any = await apiClient("/notifications/settings");
      setPrefs(data);
    } catch (err: any) {
      setPrefError(err.message || "Failed to load notification settings.");
    } finally {
      setLoadingPrefs(false);
    }
  }, []);

  const loadDeliveryLogs = useCallback(async () => {
    setLoadingLogs(true);
    setLogsError(null);
    try {
      const query = new URLSearchParams({
        page: logsPage.toString(),
        page_size: logsPageSize.toString(),
      });
      if (statusFilter) {
        query.append("status", statusFilter);
      }
      const data: any = await apiClient(`/notifications/delivery-logs?${query.toString()}`);
      setLogs(data.items || []);
      setLogsTotal(data.total || 0);
    } catch (err: any) {
      setLogsError(err.message || "Failed to load delivery logs.");
    } finally {
      setLoadingLogs(false);
    }
  }, [logsPage, logsPageSize, statusFilter]);

  useEffect(() => {
    if (activeTab === "overview") loadOverview();
    if (activeTab === "members") loadMembersAndInvites();
    if (activeTab === "preferences") loadPreferences();
    if (activeTab === "logs" && (user?.role === "OWNER" || user?.role === "ADMIN")) {
      loadDeliveryLogs();
    }
  }, [activeTab, user, loadOverview, loadMembersAndInvites, loadPreferences, loadDeliveryLogs]);

  const handleInviteMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    try {
      await apiClient("/agency/members/invite", {
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail.trim(),
          role: inviteRole,
        }),
      });
      alert(`Invitation sent to ${inviteEmail}`);
      setShowInviteModal(false);
      setInviteEmail("");
      loadMembersAndInvites();
    } catch (err: any) {
      alert(err.message || "Failed to send invitation.");
    } finally {
      setInviting(false);
    }
  };

  const handleToggleMemberStatus = async (memberId: string, currentActive: boolean) => {
    try {
      await apiClient(`/agency/members/${memberId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ is_active: !currentActive }),
      });
      loadMembersAndInvites();
    } catch (err: any) {
      alert(err.message || "Failed to update member status.");
    }
  };

  const handleUpdateRole = async (memberId: string, newRole: string) => {
    try {
      await apiClient(`/agency/members/${memberId}/role?new_role=${newRole}`, {
        method: "PATCH",
      });
      loadMembersAndInvites();
    } catch (err: any) {
      alert(err.message || "Failed to update role.");
    }
  };

  const handleRevokeInvite = async (inviteId: string) => {
    if (!confirm("Revoke this invitation?")) return;
    try {
      await apiClient(`/agency/invitations/${inviteId}`, {
        method: "DELETE",
      });
      loadMembersAndInvites();
    } catch (err: any) {
      alert(err.message || "Failed to revoke invitation.");
    }
  };

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prefs) return;
    setSavingPrefs(true);
    setPrefError(null);
    setPrefSaveSuccess(false);

    try {
      const updated: any = await apiClient("/notifications/settings", {
        method: "PUT",
        body: JSON.stringify({
          email_enabled: prefs.email_enabled,
          interview_notifications_enabled: prefs.interview_notifications_enabled,
          application_status_notifications_enabled: prefs.application_status_notifications_enabled,
          candidate_email_updates_enabled: prefs.candidate_email_updates_enabled,
          default_timezone: prefs.default_timezone,
        }),
      });
      setPrefs(updated);
      setPrefSaveSuccess(true);
      setTimeout(() => setPrefSaveSuccess(false), 4000);
    } catch (err: any) {
      setPrefError(err.message || "Failed to save preferences.");
    } finally {
      setSavingPrefs(false);
    }
  };

  const handleRetryEmail = async (logId: string) => {
    setRetryingLogId(logId);
    try {
      await apiClient(`/notifications/delivery-logs/${logId}/retry`, {
        method: "POST",
      });
      loadDeliveryLogs();
    } catch (err: any) {
      alert(err.message || "Failed to retry email delivery.");
    } finally {
      setRetryingLogId(null);
    }
  };

  const isOwnerOrAdmin = user?.role === "OWNER" || user?.role === "ADMIN";
  const isOwner = user?.role === "OWNER";

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center space-x-2.5">
            <Settings className="w-6 h-6 text-slate-700" />
            <span>Agency Administration</span>
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage organization members, RBAC permissions, hiring activity, and system preferences.
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <Link
            href="/settings/billing"
            className="px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center space-x-1.5 text-emerald-700 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 shadow-sm"
          >
            <CreditCard className="w-3.5 h-3.5 text-emerald-600" />
            <span>Billing Workspace &rarr;</span>
          </Link>
          <Link
            href="/settings/security"
            className="px-3.5 py-2 text-xs font-semibold rounded-lg transition-colors flex items-center space-x-1.5 text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 shadow-sm"
          >
            <Lock className="w-3.5 h-3.5 text-indigo-600" />
            <span>Governance & Security &rarr;</span>
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-8">
        <button
          onClick={() => setActiveTab("overview")}
          className={`pb-3 text-sm font-semibold border-b-2 flex items-center space-x-2 transition ${
            activeTab === "overview"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Building className="w-4 h-4" />
          <span>Overview</span>
        </button>
        <button
          onClick={() => setActiveTab("members")}
          className={`pb-3 text-sm font-semibold border-b-2 flex items-center space-x-2 transition ${
            activeTab === "members"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Team & Recruiters</span>
        </button>
        <button
          onClick={() => setActiveTab("preferences")}
          className={`pb-3 text-sm font-semibold border-b-2 flex items-center space-x-2 transition ${
            activeTab === "preferences"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Bell className="w-4 h-4" />
          <span>Preferences</span>
        </button>
        <button
          onClick={() => setActiveTab("logs")}
          className={`pb-3 text-sm font-semibold border-b-2 flex items-center space-x-2 transition ${
            activeTab === "logs"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-slate-500 hover:text-slate-700"
          }`}
        >
          <Mail className="w-4 h-4" />
          <span>Email Logs</span>
        </button>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {loadingOverview ? (
            <div className="py-12 text-center text-slate-500 text-sm">Loading agency overview...</div>
          ) : overview ? (
            <>
              {/* Soft limit alert */}
              {overview.soft_quota_warning && (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-start space-x-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="font-bold">Resource Quota Warning</p>
                    <p className="text-xs text-amber-700 mt-0.5">
                      Your agency has reached 80% or more of one or more monthly subscription allowances. Visit the Billing Workspace to expand limits.
                    </p>
                  </div>
                </div>
              )}

              {/* KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between text-slate-500 mb-2">
                    <span className="text-xs font-semibold uppercase">Active Jobs</span>
                    <Briefcase className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{overview.active_jobs_count}</div>
                  <p className="text-xs text-slate-500 mt-1">Open positions currently hiring</p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between text-slate-500 mb-2">
                    <span className="text-xs font-semibold uppercase">Total Candidates</span>
                    <Users className="w-4 h-4 text-purple-600" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{overview.total_candidates_count}</div>
                  <p className="text-xs text-slate-500 mt-1">In agency talent repository</p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between text-slate-500 mb-2">
                    <span className="text-xs font-semibold uppercase">Pipeline Ingests</span>
                    <TrendingUp className="w-4 h-4 text-emerald-600" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{overview.total_applications_count}</div>
                  <p className="text-xs text-slate-500 mt-1">Applications across all stages</p>
                </div>

                <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                  <div className="flex items-center justify-between text-slate-500 mb-2">
                    <span className="text-xs font-semibold uppercase">Interviews (Month)</span>
                    <Calendar className="w-4 h-4 text-amber-600" />
                  </div>
                  <div className="text-2xl font-bold text-slate-900">{overview.interviews_this_month_count}</div>
                  <p className="text-xs text-slate-500 mt-1">Scheduled in current period</p>
                </div>
              </div>

              {/* Agency Details Card */}
              <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm space-y-4">
                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                  <h3 className="font-bold text-slate-900 text-base">Organization Profile</h3>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase bg-emerald-100 text-emerald-800">
                    {overview.agency.is_active ? "Active Agency" : "Suspended"}
                  </span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <span className="text-xs text-slate-500 uppercase font-semibold">Agency Name</span>
                    <p className="font-bold text-slate-800 mt-0.5">{overview.agency.name}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase font-semibold">Slug Identifier</span>
                    <p className="font-mono text-xs text-slate-700 mt-0.5">/{overview.agency.slug}</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase font-semibold">Subscription Plan</span>
                    <p className="font-bold text-blue-600 mt-0.5">{overview.subscription_tier} ({overview.billing_interval})</p>
                  </div>
                  <div>
                    <span className="text-xs text-slate-500 uppercase font-semibold">Country Standard</span>
                    <p className="font-semibold text-slate-800 mt-0.5">{overview.agency.country}</p>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* TAB 2: TEAM & RECRUITERS */}
      {activeTab === "members" && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900">Agency Members & Recruiters</h2>
              <p className="text-xs text-slate-500">Manage user access, role assignments, and member status.</p>
            </div>
            {isOwnerOrAdmin && (
              <button
                onClick={() => setShowInviteModal(true)}
                className="inline-flex items-center px-3.5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                Invite Member
              </button>
            )}
          </div>

          {/* Members Table */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Member Name</th>
                  <th className="py-3 px-4">Email</th>
                  <th className="py-3 px-4">Role</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loadingMembers ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-slate-500">
                      Loading team members...
                    </td>
                  </tr>
                ) : (
                  members.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50/60 transition">
                      <td className="py-3.5 px-4 font-semibold text-slate-900">
                        {m.full_name} {m.id === user?.id && <span className="text-xs text-blue-600 font-normal">(You)</span>}
                      </td>
                      <td className="py-3.5 px-4 text-slate-600 font-mono text-xs">{m.email}</td>
                      <td className="py-3.5 px-4">
                        {isOwner && m.role !== "OWNER" && m.id !== user?.id ? (
                          <select
                            value={m.role}
                            onChange={(e) => handleUpdateRole(m.id, e.target.value)}
                            className="text-xs font-semibold border border-slate-300 rounded px-2 py-1 bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                          >
                            <option value="ADMIN">ADMIN</option>
                            <option value="RECRUITER">RECRUITER</option>
                            <option value="VIEWER">VIEWER</option>
                          </select>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold uppercase bg-slate-100 text-slate-800">
                            {m.role}
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${
                            m.is_active ? "bg-emerald-100 text-emerald-800" : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {m.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {isOwnerOrAdmin && m.role !== "OWNER" && m.id !== user?.id && (
                          <button
                            onClick={() => handleToggleMemberStatus(m.id, m.is_active)}
                            className={`text-xs font-semibold px-2.5 py-1 rounded border transition ${
                              m.is_active
                                ? "text-rose-600 border-rose-200 hover:bg-rose-50"
                                : "text-emerald-600 border-emerald-200 hover:bg-emerald-50"
                            }`}
                          >
                            {m.is_active ? "Deactivate" : "Activate"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pending Invitations */}
          {invitations.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-800 uppercase">Pending Invitations ({invitations.length})</h3>
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase">
                    <tr>
                      <th className="py-2.5 px-4">Invited Email</th>
                      <th className="py-2.5 px-4">Assigned Role</th>
                      <th className="py-2.5 px-4">Status</th>
                      <th className="py-2.5 px-4">Expires At</th>
                      <th className="py-2.5 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {invitations.map((inv) => (
                      <tr key={inv.id}>
                        <td className="py-2.5 px-4 font-mono text-slate-800">{inv.email}</td>
                        <td className="py-2.5 px-4 font-semibold">{inv.role}</td>
                        <td className="py-2.5 px-4">
                          <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-medium">
                            {inv.status}
                          </span>
                        </td>
                        <td className="py-2.5 px-4 text-slate-500">
                          {new Date(inv.expires_at).toLocaleDateString("en-IN")}
                        </td>
                        <td className="py-2.5 px-4 text-right">
                          {isOwnerOrAdmin && inv.status === "PENDING" && (
                            <button
                              onClick={() => handleRevokeInvite(inv.id)}
                              className="text-rose-600 hover:text-rose-800 font-medium"
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
            </div>
          )}

          {/* Invite Modal */}
          {showInviteModal && (
            <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
              <div className="bg-white rounded-xl max-w-md w-full p-6 shadow-xl border border-slate-200">
                <h3 className="text-lg font-bold text-slate-900 mb-2">Invite New Team Member</h3>
                <p className="text-xs text-slate-500 mb-4">
                  An invitation link will be created. The user can join your agency and participate according to their assigned role.
                </p>
                <form onSubmit={handleInviteMember} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      required
                      placeholder="colleague@agency.com"
                      value={inviteEmail}
                      onChange={(e) => setInviteEmail(e.target.value)}
                      className="w-full p-2.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                      Role
                    </label>
                    <select
                      value={inviteRole}
                      onChange={(e) => setInviteRole(e.target.value)}
                      className="w-full p-2.5 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="RECRUITER">RECRUITER (Standard Candidate & Job Management)</option>
                      <option value="ADMIN">ADMIN (Full Team & Settings Administration)</option>
                      <option value="VIEWER">VIEWER (Read-Only Recruitment Access)</option>
                    </select>
                  </div>
                  <div className="flex justify-end space-x-3 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowInviteModal(false)}
                      className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={inviting || !inviteEmail.trim()}
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold disabled:opacity-50"
                    >
                      {inviting ? "Sending..." : "Send Invitation"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: PREFERENCES */}
      {activeTab === "preferences" && (
        <div className="space-y-6">
          {!isOwnerOrAdmin && (
            <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm flex items-start space-x-2.5">
              <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Read-Only Mode</p>
                <p className="text-xs text-amber-700 mt-0.5">
                  Your current role ({user?.role || "VIEWER"}) can view settings. Only agency OWNER or ADMIN users can modify notification preferences.
                </p>
              </div>
            </div>
          )}

          {prefError && (
            <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-2.5">
              <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="font-semibold">Error updating settings</p>
                <p className="text-xs text-rose-700 mt-0.5">{prefError}</p>
              </div>
            </div>
          )}

          {prefSaveSuccess && (
            <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start space-x-2.5 animate-in fade-in-50">
              <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold">Settings Saved</p>
                <p className="text-xs text-emerald-700 mt-0.5">
                  Agency notification preferences have been successfully updated.
                </p>
              </div>
            </div>
          )}

          {loadingPrefs ? (
            <div className="py-16 text-center text-slate-400 text-sm">Loading agency settings...</div>
          ) : prefs ? (
            <form onSubmit={handleSavePreferences} className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
                <h3 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3">
                  Notification Dispatch Toggles
                </h3>
                <div className="space-y-4">
                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      disabled={!isOwnerOrAdmin}
                      checked={prefs.email_enabled}
                      onChange={(e) => setPrefs({ ...prefs, email_enabled: e.target.checked })}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-slate-900">Global Email Dispatch</span>
                      <p className="text-xs text-slate-500">Master switch enabling outbound transactional notifications for your agency.</p>
                    </div>
                  </label>

                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      disabled={!isOwnerOrAdmin}
                      checked={prefs.interview_notifications_enabled}
                      onChange={(e) => setPrefs({ ...prefs, interview_notifications_enabled: e.target.checked })}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-slate-900">Interview Notifications</span>
                      <p className="text-xs text-slate-500">Send automatic booking confirmations, calendar updates, and reminder notices to interviewers.</p>
                    </div>
                  </label>

                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      disabled={!isOwnerOrAdmin}
                      checked={prefs.application_status_notifications_enabled}
                      onChange={(e) => setPrefs({ ...prefs, application_status_notifications_enabled: e.target.checked })}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-slate-900">Recruiter Pipeline Alerts</span>
                      <p className="text-xs text-slate-500">Notify recruiters when candidate stages transition across the hiring workflow.</p>
                    </div>
                  </label>

                  <label className="flex items-start space-x-3 cursor-pointer">
                    <input
                      type="checkbox"
                      disabled={!isOwnerOrAdmin}
                      checked={prefs.candidate_email_updates_enabled}
                      onChange={(e) => setPrefs({ ...prefs, candidate_email_updates_enabled: e.target.checked })}
                      className="mt-1 h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                    />
                    <div>
                      <span className="text-sm font-medium text-slate-900">Candidate Email Updates</span>
                      <p className="text-xs text-slate-500">Dispatch automated stage update emails to candidates upon status changes.</p>
                    </div>
                  </label>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
                <h3 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3 flex items-center space-x-2">
                  <Globe className="w-4 h-4 text-slate-500" />
                  <span>Timezone Configuration</span>
                </h3>
                <div className="max-w-md">
                  <label className="block text-xs font-semibold text-slate-700 uppercase mb-1">
                    Default Organization Timezone
                  </label>
                  <select
                    disabled={!isOwnerOrAdmin}
                    value={prefs.default_timezone}
                    onChange={(e) => setPrefs({ ...prefs, default_timezone: e.target.value })}
                    className="w-full p-2.5 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    <option value="Asia/Kolkata">Asia/Kolkata (IST - UTC+05:30) [HireLens Default]</option>
                    <option value="UTC">UTC (Coordinated Universal Time)</option>
                    <option value="America/New_York">America/New_York (EST/EDT)</option>
                    <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                    <option value="Europe/London">Europe/London (GMT/BST)</option>
                  </select>
                </div>
              </div>

              {isOwnerOrAdmin && (
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={savingPrefs}
                    className="inline-flex items-center px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold shadow-sm transition disabled:opacity-50"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    {savingPrefs ? "Saving..." : "Save Preferences"}
                  </button>
                </div>
              )}
            </form>
          ) : null}
        </div>
      )}

      {/* TAB 4: DELIVERY LOGS */}
      {activeTab === "logs" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">Email Delivery Outbox Audit</h2>
            <button
              onClick={loadDeliveryLogs}
              disabled={loadingLogs}
              className="inline-flex items-center px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 text-slate-500 ${loadingLogs ? "animate-spin" : ""}`} />
              Refresh Logs
            </button>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-sans font-semibold uppercase">
                <tr>
                  <th className="py-2.5 px-3">Recipient</th>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Attempts</th>
                  <th className="py-2.5 px-3">Created At (IST)</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {loadingLogs ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">Loading email delivery logs...</td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">No email delivery logs recorded yet.</td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-slate-50/60 transition">
                      <td className="py-2.5 px-3 text-slate-800">{log.recipient_email}</td>
                      <td className="py-2.5 px-3 font-sans font-medium text-slate-700">{log.event_type}</td>
                      <td className="py-2.5 px-3 font-sans">
                        <span
                          className={`px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                            log.status === "DELIVERED"
                              ? "bg-emerald-100 text-emerald-800"
                              : log.status === "FAILED" || log.status === "DEAD_LETTER"
                              ? "bg-rose-100 text-rose-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {log.status}
                        </span>
                      </td>
                      <td className="py-2.5 px-3 text-slate-600">{log.attempt_count}</td>
                      <td className="py-2.5 px-3 text-slate-500">
                        {log.created_at_ist || new Date(log.created_at).toLocaleString("en-IN")}
                      </td>
                      <td className="py-2.5 px-3 text-right font-sans">
                        {(log.status === "FAILED" || log.status === "DEAD_LETTER") && isOwnerOrAdmin && (
                          <button
                            disabled={retryingLogId === log.id}
                            onClick={() => handleRetryEmail(log.id)}
                            className="text-blue-600 hover:text-blue-800 text-xs font-semibold disabled:opacity-50"
                          >
                            {retryingLogId === log.id ? "Retrying..." : "Retry"}
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

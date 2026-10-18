"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Users,
  FileCheck2,
  Sparkles,
  ShieldCheck,
  UserPlus,
  Mail,
  CheckCircle2,
  AlertCircle,
  Kanban,
  Activity,
  ArrowRight,
  Clock,
  Layers,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { formatTimeIST } from "@/lib/timezone";
import { PipelineDashboardStats } from "@/types";

export default function DashboardOverviewPage() {
  const [agency, setAgency] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [jobCount, setJobCount] = useState<number>(0);
  const [candidateCount, setCandidateCount] = useState<number>(0);
  const [pipelineStats, setPipelineStats] = useState<PipelineDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("RECRUITER");
  const [inviteStatus, setInviteStatus] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [submittingInvite, setSubmittingInvite] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const [agencyData, membersData, jobsData, candidatesData, pipeData]: any = await Promise.all([
        apiClient("/agency/profile"),
        apiClient("/agency/members"),
        apiClient("/jobs"),
        apiClient("/candidates"),
        apiClient<PipelineDashboardStats>("/applications/dashboard/stats").catch(() => null),
      ]);
      setAgency(agencyData);
      setMembers(membersData);
      setJobCount(jobsData.length);
      setCandidateCount(candidatesData.length);
      setPipelineStats(pipeData);
    } catch (err: any) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteStatus(null);
    setSubmittingInvite(true);
    try {
      await apiClient("/agency/members/invite", {
        method: "POST",
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      setInviteStatus({ type: "success", message: `Invitation dispatched to ${inviteEmail}` });
      setInviteEmail("");
      fetchDashboardData();
    } catch (err: any) {
      setInviteStatus({ type: "error", message: err.message || "Failed to invite member" });
    } finally {
      setSubmittingInvite(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center space-x-2 text-slate-500 py-12">
        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm">Loading agency overview...</span>
      </div>
    );
  }

  const stageCounts = pipelineStats?.stage_counts || {
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
    <div className="space-y-8 max-w-7xl">
      {/* Welcome Hero */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
              Agency Workspace
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Country: {agency?.country}
            </span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            {agency?.name}
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Recruitment Intelligence: Find the right candidate. Not just the right keywords.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="px-3.5 py-2 rounded-lg bg-slate-50 border border-slate-200 text-xs">
            <span className="text-slate-500 block">Security Guard</span>
            <span className="font-semibold text-slate-900 flex items-center mt-0.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 mr-1" />
              Tenant Isolated
            </span>
          </div>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Link
          href="/pipeline"
          className="group bg-white hover:border-blue-400 rounded-xl border border-slate-200/80 p-5 shadow-xs transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider group-hover:text-blue-600 transition-colors">
              Active Applications
            </span>
            <Kanban className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900">
            {pipelineStats?.total_active_applications || 0}
          </div>
          <p className="text-xs text-slate-400 mt-1">Candidates in recruitment pipeline</p>
        </Link>

        <Link
          href="/jobs"
          className="group bg-white hover:border-blue-400 rounded-xl border border-slate-200/80 p-5 shadow-xs transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider group-hover:text-blue-600 transition-colors">
              Active Jobs
            </span>
            <Briefcase className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{jobCount}</div>
          <p className="text-xs text-slate-400 mt-1">Manage positions & criteria</p>
        </Link>

        <Link
          href="/candidates"
          className="group bg-white hover:border-blue-400 rounded-xl border border-slate-200/80 p-5 shadow-xs transition-all"
        >
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider group-hover:text-blue-600 transition-colors">
              Candidate Pool
            </span>
            <Users className="w-4 h-4 text-slate-400 group-hover:text-blue-600 transition-colors" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{candidateCount}</div>
          <p className="text-xs text-slate-400 mt-1">Managed talent profiles</p>
        </Link>

        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Team Members</span>
            <Users className="w-4 h-4 text-slate-400" />
          </div>
          <div className="text-2xl font-bold text-slate-900">{members.length}</div>
          <p className="text-xs text-slate-400 mt-1">Active agency users</p>
        </div>
      </div>

      {/* Actual Application Pipeline Stage Breakdown (Section I requirement) */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Kanban className="w-4 h-4 text-blue-600" />
              Recruitment Pipeline Stages
            </h2>
            <p className="text-xs text-slate-500">Live agency-wide application distribution across all 8 pipeline stages</p>
          </div>
          <Link
            href="/pipeline"
            className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center gap-1"
          >
            <span>View All Pipelines</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <div className="bg-blue-50/60 border border-blue-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-blue-700 uppercase tracking-wider block">
              Applied
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.APPLIED || 0}
            </span>
          </div>

          <div className="bg-indigo-50/60 border border-indigo-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider block">
              Under Review
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.UNDER_REVIEW || 0}
            </span>
          </div>

          <div className="bg-purple-50/60 border border-purple-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-purple-700 uppercase tracking-wider block">
              Shortlisted
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.SHORTLISTED || 0}
            </span>
          </div>

          <div className="bg-amber-50/60 border border-amber-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-amber-700 uppercase tracking-wider block">
              Interview
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.INTERVIEW || 0}
            </span>
          </div>

          <div className="bg-emerald-50/60 border border-emerald-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block">
              Selected
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.SELECTED || 0}
            </span>
          </div>

          <div className="bg-orange-50/60 border border-orange-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-orange-700 uppercase tracking-wider block">
              On Hold
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.ON_HOLD || 0}
            </span>
          </div>

          <div className="bg-rose-50/60 border border-rose-200/80 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block">
              Rejected
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.REJECTED || 0}
            </span>
          </div>

          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 text-center">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">
              Withdrawn
            </span>
            <span className="text-xl font-bold text-slate-900 mt-0.5 block">
              {stageCounts.WITHDRAWN || 0}
            </span>
          </div>
        </div>
      </div>

      {/* Per-Job Pipeline Summaries & Recent Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Per-Job Pipeline Summaries */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                Position Pipeline Workspaces
              </h2>
              <p className="text-xs text-slate-500">Live candidate volume per active position</p>
            </div>
            <Link
              href="/pipeline"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800"
            >
              Open Pipeline Hub
            </Link>
          </div>

          <div className="divide-y divide-slate-100">
            {(!pipelineStats?.job_summaries || pipelineStats.job_summaries.length === 0) ? (
              <p className="p-6 text-xs text-slate-400 italic text-center">
                No active positions or applications recorded yet.
              </p>
            ) : (
              pipelineStats.job_summaries.slice(0, 5).map((jobSum) => (
                <div
                  key={jobSum.job_id}
                  className="p-4 px-6 flex items-center justify-between hover:bg-slate-50/50 transition-colors"
                >
                  <div className="space-y-0.5">
                    <p className="text-sm font-bold text-slate-900">{jobSum.job_title}</p>
                    <span className="text-[10px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200 uppercase">
                      {jobSum.job_status}
                    </span>
                  </div>

                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <span className="text-sm font-bold text-slate-900 block">
                        {jobSum.active_applications_count}
                      </span>
                      <span className="text-[10px] text-slate-400">candidates</span>
                    </div>

                    <Link
                      href={`/jobs/${jobSum.job_id}/pipeline`}
                      className="inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg transition-colors border border-blue-100"
                    >
                      <Kanban className="w-3 h-3" />
                      <span>Kanban</span>
                    </Link>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right 1 Col: Recent Recruitment Activity */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-4 h-4 text-blue-600" />
              Recruitment Activity
            </h2>
          </div>
          <p className="text-xs text-slate-500">Live audit events recorded by authorized recruiters</p>

          <div className="space-y-2.5 max-h-72 overflow-y-auto divide-y divide-slate-100">
            {(!pipelineStats?.recent_activities || pipelineStats.recent_activities.length === 0) ? (
              <p className="text-xs text-slate-400 py-4 italic text-center">
                No recruitment actions logged yet.
              </p>
            ) : (
              pipelineStats.recent_activities.slice(0, 8).map((act) => (
                <div key={act.id} className="pt-2 text-xs space-y-0.5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-slate-800">
                      {act.action.replace(/_/g, " ")}
                    </span>
                    <span className="text-[10px] text-slate-400 font-mono">
                      {formatTimeIST(act.created_at)}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500">By {act.user_name}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Team Management Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Team Members List */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold text-slate-900">Agency Team & Access Roles</h2>
              <p className="text-xs text-slate-500">Authorized recruiters and administrators</p>
            </div>
            <span className="text-xs bg-slate-100 text-slate-700 px-2.5 py-1 rounded-full font-medium">
              {members.length} Members
            </span>
          </div>

          <div className="divide-y divide-slate-100">
            {members.map((member) => (
              <div key={member.id} className="p-4 px-6 flex items-center justify-between hover:bg-slate-50/50">
                <div className="flex items-center space-x-3">
                  <div className="h-9 w-9 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs uppercase">
                    {member.full_name?.slice(0, 2) || "U"}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-900">{member.full_name}</p>
                    <p className="text-xs text-slate-500">{member.email}</p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider border ${
                      member.role === "OWNER"
                        ? "bg-purple-50 text-purple-700 border-purple-200"
                        : member.role === "ADMIN"
                        ? "bg-blue-50 text-blue-700 border-blue-200"
                        : "bg-slate-100 text-slate-700 border-slate-200"
                    }`}
                  >
                    {member.role}
                  </span>
                  <span className="text-xs text-slate-400">
                    Joined {formatDateTime(member.created_at)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Invite Member Box */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-6 h-fit">
          <div className="flex items-center space-x-2 mb-4">
            <UserPlus className="w-5 h-5 text-blue-600" />
            <h3 className="text-sm font-semibold text-slate-900">Invite Team Member</h3>
          </div>
          <p className="text-xs text-slate-500 mb-5">
            Send an invitation to a recruiter or administrator to join this agency workspace.
          </p>

          {inviteStatus && (
            <div
              className={`mb-4 p-3 rounded-md text-xs flex items-center space-x-2 ${
                inviteStatus.type === "success"
                  ? "bg-emerald-50 text-emerald-800 border border-emerald-200"
                  : "bg-red-50 text-red-800 border border-red-200"
              }`}
            >
              {inviteStatus.type === "success" ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              ) : (
                <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              )}
              <span>{inviteStatus.message}</span>
            </div>
          )}

          <form onSubmit={handleInvite} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Recruiter Email
              </label>
              <input
                type="email"
                required
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                placeholder="colleague@agency.com"
                className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-md shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Assigned Role
              </label>
              <select
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-white border border-slate-300 rounded-md shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600"
              >
                <option value="RECRUITER">RECRUITER (Manage jobs & candidates)</option>
                <option value="ADMIN">ADMIN (Recruitment ops & users)</option>
                <option value="VIEWER">VIEWER (Read-only access)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={submittingInvite}
              className="w-full py-2 px-4 bg-slate-900 hover:bg-slate-800 text-white font-medium text-xs rounded-md shadow flex items-center justify-center space-x-1.5 transition-colors disabled:opacity-50"
            >
              <Mail className="w-3.5 h-3.5" />
              <span>{submittingInvite ? "Inviting..." : "Send Invitation"}</span>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

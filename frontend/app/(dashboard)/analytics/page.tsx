"use client";

import React, { useEffect, useState, useMemo } from "react";
import {
  BarChart3,
  TrendingUp,
  Users,
  Briefcase,
  Calendar,
  IndianRupee,
  Sparkles,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  AlertTriangle,
  Layers,
  PieChart,
  Info,
  Plus,
  Trash2,
  Clock,
  Target,
  ShieldAlert,
  RefreshCw,
  FileText,
  ChevronRight,
  X,
  UserCheck,
  Building,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { formatDateIST, formatDateTimeIST, formatDateForPicker } from "@/lib/timezone";
import {
  PeriodPreset,
  ReportingPeriodInfo,
  AnalyticsOverviewResponse,
  RecruitmentFunnelResponse,
  HiringPerformanceResponse,
  JobAnalyticsResponse,
  RecruiterAnalyticsResponse,
  SourceAnalyticsResponse,
  CostAnalyticsResponse,
  RecruitmentExpense,
  ExpenseListResponse,
  AnalyticsTrendsResponse,
  AIInsightsResponse,
  Job,
  ExpenseCategory,
} from "@/types";

type TabKey = "overview" | "funnel" | "jobs" | "recruiters" | "sources" | "costs" | "insights";

export default function AnalyticsWorkspacePage() {
  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [period, setPeriod] = useState<PeriodPreset>("LAST_30_DAYS");
  const [customStart, setCustomStart] = useState<string>("");
  const [customEnd, setCustomEnd] = useState<string>("");

  // Filter selections
  const [selectedJobId, setSelectedJobId] = useState<string>("");
  const [selectedRecruiterId, setSelectedRecruiterId] = useState<string>("");
  const [selectedSource, setSelectedSource] = useState<string>("");

  // Data states
  const [overview, setOverview] = useState<AnalyticsOverviewResponse | null>(null);
  const [funnel, setFunnel] = useState<RecruitmentFunnelResponse | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrendsResponse | null>(null);
  const [hiring, setHiring] = useState<HiringPerformanceResponse | null>(null);
  const [jobsData, setJobsData] = useState<JobAnalyticsResponse | null>(null);
  const [recruitersData, setRecruitersData] = useState<RecruiterAnalyticsResponse | null>(null);
  const [sourcesData, setSourcesData] = useState<SourceAnalyticsResponse | null>(null);
  const [costsData, setCostsData] = useState<CostAnalyticsResponse | null>(null);
  const [expensesList, setExpensesList] = useState<RecruitmentExpense[]>([]);
  const [aiInsights, setAiInsights] = useState<AIInsightsResponse | null>(null);

  // Metadata dropdown options
  const [jobsList, setJobsList] = useState<Job[]>([]);
  const [membersList, setMembersList] = useState<any[]>([]);
  const [currentUser, setCurrentUser] = useState<any>(null);

  // Loading & Error states
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingInsights, setLoadingInsights] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Expense modal state
  const [showExpenseModal, setShowExpenseModal] = useState<boolean>(false);
  const [submittingExpense, setSubmittingExpense] = useState<boolean>(false);
  const [expenseFormError, setExpenseFormError] = useState<string | null>(null);
  const [expenseFormData, setExpenseFormData] = useState({
    title: "",
    amount: "",
    currency: "INR",
    category: "JOB_ADVERTISING" as ExpenseCategory,
    expense_date: formatDateForPicker(new Date()),
    job_id: "",
    description: "",
  });

  const canManageExpenses = currentUser?.role === "OWNER" || currentUser?.role === "ADMIN";

  // Build query string based on filters
  const buildQuery = useMemo(() => {
    const params = new URLSearchParams();
    params.set("period", period);
    if (period === "CUSTOM" && customStart && customEnd) {
      params.set("start_date", customStart);
      params.set("end_date", customEnd);
    }
    if (selectedJobId) params.set("job_id", selectedJobId);
    if (selectedRecruiterId) params.set("recruiter_id", selectedRecruiterId);
    if (selectedSource) params.set("source", selectedSource);
    return params.toString();
  }, [period, customStart, customEnd, selectedJobId, selectedRecruiterId, selectedSource]);

  // Initial load: current user, jobs, members
  useEffect(() => {
    async function loadInitialMetadata() {
      try {
        const [me, jobs, members] = await Promise.all([
          apiClient<any>("/auth/me").catch(() => null),
          apiClient<Job[]>("/jobs?limit=100").catch(() => []),
          apiClient<any[]>("/agency/members").catch(() => []),
        ]);
        setCurrentUser(me);
        setJobsList(jobs);
        setMembersList(members);
      } catch (err: any) {
        console.error("Failed to load initial metadata", err);
      }
    }
    loadInitialMetadata();
  }, []);

  // Fetch all analytics datasets
  const fetchAllAnalytics = async () => {
    if (period === "CUSTOM" && (!customStart || !customEnd)) {
      return; // wait for user to pick both dates
    }

    setLoading(true);
    setError(null);

    try {
      const q = buildQuery;
      const [
        ovRes,
        fnRes,
        trRes,
        hpRes,
        jbRes,
        rcRes,
        scRes,
        csRes,
        expRes,
      ] = await Promise.all([
        apiClient<AnalyticsOverviewResponse>(`/analytics/overview?${q}`),
        apiClient<RecruitmentFunnelResponse>(`/analytics/funnel?${q}`),
        apiClient<AnalyticsTrendsResponse>(`/analytics/trends?${q}`),
        apiClient<HiringPerformanceResponse>(`/analytics/hiring-performance?${q}`),
        apiClient<JobAnalyticsResponse>(`/analytics/jobs?${q}`),
        apiClient<RecruiterAnalyticsResponse>(`/analytics/recruiters?${q}`),
        apiClient<SourceAnalyticsResponse>(`/analytics/sources?${q}`),
        apiClient<CostAnalyticsResponse>(`/analytics/costs?${q}`),
        apiClient<ExpenseListResponse>(`/analytics/expenses?limit=50`),
      ]);

      setOverview(ovRes);
      setFunnel(fnRes);
      setTrends(trRes);
      setHiring(hpRes);
      setJobsData(jbRes);
      setRecruitersData(rcRes);
      setSourcesData(scRes);
      setCostsData(csRes);
      setExpensesList(expRes.items);
    } catch (err: any) {
      console.error("Error fetching analytics:", err);
      setError(err.message || "Failed to load recruitment analytics.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAllAnalytics();
  }, [buildQuery]);

  // Fetch AI Insights on demand or tab activation
  const fetchAiInsights = async () => {
    setLoadingInsights(true);
    try {
      const q = buildQuery;
      const res = await apiClient<AIInsightsResponse>(`/analytics/insights?${q}`, {
        method: "POST",
        body: JSON.stringify({ focus_area: "general_operational_review" }),
      });
      setAiInsights(res);
    } catch (err: any) {
      console.error("AI Insights error:", err);
    } finally {
      setLoadingInsights(false);
    }
  };

  useEffect(() => {
    if (activeTab === "insights" && !aiInsights && !loading) {
      fetchAiInsights();
    }
  }, [activeTab, loading]);

  // Expense creation
  const handleCreateExpense = async (e: React.FormEvent) => {
    e.preventDefault();
    setExpenseFormError(null);
    setSubmittingExpense(true);

    const amountNum = parseFloat(expenseFormData.amount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setExpenseFormError("Amount must be a positive number.");
      setSubmittingExpense(false);
      return;
    }

    try {
      await apiClient("/analytics/expenses", {
        method: "POST",
        body: JSON.stringify({
          title: expenseFormData.title,
          amount: amountNum,
          currency: expenseFormData.currency,
          category: expenseFormData.category,
          expense_date: new Date(expenseFormData.expense_date).toISOString(),
          job_id: expenseFormData.job_id || null,
          description: expenseFormData.description || null,
        }),
      });

      setShowExpenseModal(false);
      setExpenseFormData({
        title: "",
        amount: "",
        currency: "INR",
        category: "JOB_ADVERTISING",
        expense_date: formatDateForPicker(new Date()),
        job_id: "",
        description: "",
      });

      // Refresh costs and ledger
      fetchAllAnalytics();
    } catch (err: any) {
      setExpenseFormError(err.message || "Failed to record expense.");
    } finally {
      setSubmittingExpense(false);
    }
  };

  // Expense deletion
  const handleDeleteExpense = async (id: string) => {
    if (!confirm("Are you sure you want to delete this recruitment expense?")) return;
    try {
      await apiClient(`/analytics/expenses/${id}`, { method: "DELETE" });
      fetchAllAnalytics();
    } catch (err: any) {
      alert(err.message || "Failed to delete expense.");
    }
  };

  const handleResetFilters = () => {
    setPeriod("LAST_30_DAYS");
    setCustomStart("");
    setCustomEnd("");
    setSelectedJobId("");
    setSelectedRecruiterId("");
    setSelectedSource("");
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* 1. Header & Controls */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <div className="flex items-center space-x-3">
              <div className="h-10 w-10 rounded-lg bg-blue-50 border border-blue-200/60 flex items-center justify-center text-blue-600">
                <BarChart3 className="w-5 h-5" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                  Recruitment Intelligence & Analytics
                </h1>
                <p className="text-xs text-slate-500 mt-0.5">
                  Production-grade hiring metrics, stage conversions, recruiter workload, and unit economics.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Period Selector */}
            <div className="flex items-center space-x-1.5 bg-slate-50 border border-slate-200 rounded-lg p-1">
              <Calendar className="w-4 h-4 text-slate-400 ml-2" />
              <select
                id="analytics-period-select"
                value={period}
                onChange={(e) => setPeriod(e.target.value as PeriodPreset)}
                className="bg-transparent text-xs font-semibold text-slate-700 py-1.5 pr-6 pl-1 focus:outline-hidden"
              >
                <option value="TODAY">Today (IST)</option>
                <option value="LAST_7_DAYS">Last 7 Days</option>
                <option value="LAST_30_DAYS">Last 30 Days</option>
                <option value="LAST_90_DAYS">Last 90 Days</option>
                <option value="THIS_MONTH">This Month</option>
                <option value="PREVIOUS_MONTH">Previous Month</option>
                <option value="THIS_QUARTER">This Quarter</option>
                <option value="CUSTOM">Custom Range...</option>
              </select>
            </div>

            {/* Refresh Button */}
            <button
              onClick={() => fetchAllAnalytics()}
              disabled={loading}
              title="Refresh Analytics"
              className="p-2 border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-600 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-blue-600" : ""}`} />
            </button>

            {/* Log Expense (OWNER / ADMIN) */}
            {canManageExpenses && (
              <button
                onClick={() => setShowExpenseModal(true)}
                className="flex items-center space-x-1.5 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Log Expense</span>
              </button>
            )}
          </div>
        </div>

        {/* Custom Date Pickers */}
        {period === "CUSTOM" && (
          <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-3">
            <span className="text-xs font-medium text-slate-600">Custom Range (Asia/Kolkata):</span>
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-blue-500"
            />
            <span className="text-xs text-slate-400">to</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="text-xs border border-slate-200 rounded-md px-2.5 py-1.5 text-slate-700 focus:outline-blue-500"
            />
            {(!customStart || !customEnd) && (
              <span className="text-[11px] text-amber-600 font-medium">
                * Please select both start and end dates.
              </span>
            )}
          </div>
        )}

        {/* Global Filter Bar */}
        <div className="mt-4 pt-4 border-t border-slate-100 flex flex-wrap items-center gap-3">
          <div className="flex items-center space-x-1 text-slate-400 text-xs font-medium mr-1">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Job Filter */}
          <select
            id="filter-job-select"
            value={selectedJobId}
            onChange={(e) => setSelectedJobId(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-slate-50 text-slate-700 focus:outline-blue-500"
          >
            <option value="">All Jobs</option>
            {jobsList.map((j) => (
              <option key={j.id} value={j.id}>
                {j.title}
              </option>
            ))}
          </select>

          {/* Recruiter Filter */}
          <select
            id="filter-recruiter-select"
            value={selectedRecruiterId}
            onChange={(e) => setSelectedRecruiterId(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-slate-50 text-slate-700 focus:outline-blue-500"
          >
            <option value="">All Recruiters</option>
            {membersList.map((m) => (
              <option key={m.id} value={m.id}>
                {m.full_name} ({m.role})
              </option>
            ))}
          </select>

          {/* Source Filter */}
          <select
            id="filter-source-select"
            value={selectedSource}
            onChange={(e) => setSelectedSource(e.target.value)}
            className="text-xs border border-slate-200 rounded-lg px-2.5 py-1.5 bg-slate-50 text-slate-700 focus:outline-blue-500"
          >
            <option value="">All Candidate Sources</option>
            <option value="DIRECT_APPLICATION">Direct Application</option>
            <option value="LINKEDIN">LinkedIn</option>
            <option value="REFERRAL">Referral</option>
            <option value="JOB_BOARD">Job Board</option>
            <option value="CAREER_PAGE">Career Page</option>
            <option value="RESUME_UPLOAD">Resume Upload</option>
            <option value="AGENCY">Agency</option>
          </select>

          {/* Clear Filters */}
          {(selectedJobId || selectedRecruiterId || selectedSource || period !== "LAST_30_DAYS") && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-rose-600 hover:text-rose-700 font-medium underline flex items-center space-x-1 ml-auto"
            >
              <X className="w-3 h-3" />
              <span>Reset Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* 2. Navigation Tabs */}
      <div className="flex border-b border-slate-200 space-x-6 overflow-x-auto text-sm font-medium text-slate-600">
        {[
          { key: "overview", label: "Executive Overview", icon: BarChart3 },
          { key: "funnel", label: "Recruitment Funnel", icon: Layers },
          { key: "jobs", label: "Job Performance", icon: Briefcase },
          { key: "recruiters", label: "Recruiter Workload", icon: Users },
          { key: "sources", label: "Candidate Sources", icon: PieChart },
          { key: "costs", label: "Cost Per Hire & ROI", icon: IndianRupee },
          { key: "insights", label: "AI Grounded Insights", icon: Sparkles },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as TabKey)}
              className={`flex items-center space-x-2 py-3 border-b-2 font-medium transition-colors whitespace-nowrap ${
                isActive
                  ? "border-blue-600 text-blue-600 font-semibold"
                  : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? "text-blue-600" : "text-slate-400"}`} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 flex items-center space-x-3 text-rose-700 text-xs">
          <ShieldAlert className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && !overview ? (
        <div className="py-24 flex flex-col items-center justify-center space-y-3 text-slate-400">
          <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-xs font-medium">Aggregating recruitment metrics...</span>
        </div>
      ) : (
        <>
          {/* ========================================================== */}
          {/* TAB 1: EXECUTIVE OVERVIEW                                  */}
          {/* ========================================================== */}
          {activeTab === "overview" && overview && (
            <div className="space-y-6">
              {/* KPI Cards Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <KPICard
                  title="Active Job Openings"
                  value={overview.total_active_jobs}
                  subtitle="Published & live"
                  icon={Briefcase}
                  color="blue"
                  tooltip={overview.metric_tooltips.total_active_jobs}
                />
                <KPICard
                  title="Applications Received"
                  value={overview.applications_in_period}
                  subtitle={`Total all-time: ${overview.total_applications}`}
                  icon={FileText}
                  color="indigo"
                  tooltip={overview.metric_tooltips.applications_in_period}
                />
                <KPICard
                  title="Completed Interviews"
                  value={overview.interviews_completed}
                  subtitle={`Scheduled: ${overview.interviews_scheduled}`}
                  icon={Calendar}
                  color="violet"
                  tooltip={overview.metric_tooltips.interviews_completed}
                />
                <KPICard
                  title="Successful Hires"
                  value={overview.successful_hires}
                  subtitle="Terminal Selected stage"
                  icon={CheckCircle2}
                  color="emerald"
                  tooltip={overview.metric_tooltips.successful_hires}
                />
              </div>

              {/* Secondary Metric Bar */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-100/60 p-4 rounded-xl border border-slate-200/60">
                <div className="text-left">
                  <span className="text-[11px] text-slate-500 uppercase font-semibold">Active Pipeline Workload</span>
                  <p className="text-base font-bold text-slate-800 mt-0.5">{overview.active_applications} candidates</p>
                </div>
                <div className="text-left">
                  <span className="text-[11px] text-slate-500 uppercase font-semibold">Total Talent Pool</span>
                  <p className="text-base font-bold text-slate-800 mt-0.5">{overview.total_candidates} registered</p>
                </div>
                <div className="text-left">
                  <span className="text-[11px] text-slate-500 uppercase font-semibold">Median Time-To-Hire</span>
                  <p className="text-base font-bold text-slate-800 mt-0.5">
                    {hiring?.time_to_hire.median_days !== null && hiring?.time_to_hire.median_days !== undefined
                      ? `${hiring.time_to_hire.median_days} days`
                      : "Insufficient hires"}
                  </p>
                </div>
                <div className="text-left">
                  <span className="text-[11px] text-slate-500 uppercase font-semibold">Overall Conversion</span>
                  <p className="text-base font-bold text-emerald-600 mt-0.5">
                    {funnel?.overall_application_to_hire_rate}%
                  </p>
                </div>
              </div>

              {/* Trends & Quick Funnel Split */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Trends Chart */}
                <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="text-sm font-bold text-slate-900">Application & Hiring Trends</h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Daily time-series volume for {overview.reporting_period.start_date_ist} to {overview.reporting_period.end_date_ist}
                      </p>
                    </div>
                    <div className="flex items-center space-x-4 text-xs font-medium">
                      <span className="flex items-center space-x-1.5 text-blue-600">
                        <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block"></span>
                        <span>Applications</span>
                      </span>
                      <span className="flex items-center space-x-1.5 text-emerald-600">
                        <span className="w-2.5 h-2.5 rounded-full bg-emerald-600 inline-block"></span>
                        <span>Hires</span>
                      </span>
                    </div>
                  </div>

                  <TrendChart dataPoints={trends?.data_points || []} />
                </div>

                {/* Funnel Snapshot Widget */}
                <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">Recruitment Funnel Velocity</h3>
                    <p className="text-xs text-slate-400 mt-0.5 mb-4">
                      Stage conversions across evaluated applications
                    </p>

                    <div className="space-y-3">
                      {funnel?.stages.slice(0, 5).map((st) => (
                        <div key={st.stage} className="text-xs">
                          <div className="flex justify-between font-medium text-slate-700 mb-1">
                            <span>{st.label}</span>
                            <span className="font-semibold">{st.entered_count} entered ({st.current_count} active)</span>
                          </div>
                          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                            <div
                              className="bg-blue-600 h-2 rounded-full"
                              style={{
                                width: `${Math.min(100, st.conversion_from_applied_percent || (st.entered_count > 0 ? 100 : 0))}%`,
                              }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={() => setActiveTab("funnel")}
                    className="mt-6 flex items-center justify-center space-x-1.5 w-full py-2 bg-slate-50 hover:bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg border border-slate-200 transition-colors"
                  >
                    <span>View In-Depth Funnel & Drop-offs</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* TAB 2: RECRUITMENT FUNNEL                                  */}
          {/* ========================================================== */}
          {activeTab === "funnel" && funnel && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                  <div>
                    <h2 className="text-base font-bold text-slate-900">End-to-End Recruitment Funnel</h2>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Actual application transitions recorded through immutable stage history logs.
                    </p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 px-3.5 py-1.5 rounded-lg flex items-center space-x-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span className="text-xs font-bold text-emerald-800">
                      Overall Hire Rate: {funnel.overall_application_to_hire_rate}%
                    </span>
                  </div>
                </div>

                {/* Interactive Funnel Flow */}
                <div className="space-y-4">
                  {funnel.stages.map((stage, idx) => (
                    <div
                      key={stage.stage}
                      className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 hover:bg-slate-50 transition-colors"
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                        <div className="flex items-center space-x-2.5">
                          <span className="w-6 h-6 rounded-full bg-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center">
                            {idx + 1}
                          </span>
                          <span className="text-sm font-bold text-slate-800">{stage.label}</span>
                        </div>
                        <div className="flex items-center space-x-3 text-xs">
                          <span className="font-semibold text-slate-700">
                            {stage.entered_count} entered
                          </span>
                          <span className="text-slate-400">|</span>
                          <span className="text-slate-500">
                            {stage.current_count} currently in stage
                          </span>
                          {stage.drop_off_count > 0 && (
                            <>
                              <span className="text-slate-400">|</span>
                              <span className="text-rose-600 font-semibold">
                                {stage.drop_off_count} drop-offs
                              </span>
                            </>
                          )}
                        </div>
                      </div>

                      {/* Bar and conversion chips */}
                      <div className="w-full bg-slate-200/70 rounded-full h-3 overflow-hidden mb-2">
                        <div
                          className="bg-blue-600 h-3 rounded-full transition-all duration-500"
                          style={{
                            width: `${Math.min(100, stage.conversion_from_applied_percent || (stage.entered_count > 0 ? 100 : 0))}%`,
                          }}
                        ></div>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                        <span>
                          {stage.conversion_from_previous_percent !== null
                            ? `${stage.conversion_from_previous_percent}% passed from previous stage`
                            : "Top of Funnel Entry"}
                        </span>
                        <span>
                          {stage.conversion_from_applied_percent !== null
                            ? `${stage.conversion_from_applied_percent}% of total applicants reached here`
                            : ""}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="mt-6 p-4 rounded-lg bg-blue-50/60 border border-blue-100 text-xs text-blue-900 flex items-start space-x-2.5">
                  <Info className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold">Calculation Methodology:</span>
                    <p className="mt-0.5 text-blue-800/90 leading-relaxed">
                      {funnel.funnel_methodology}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* TAB 3: JOB PERFORMANCE                                     */}
          {/* ========================================================== */}
          {activeTab === "jobs" && jobsData && (
            <div className="space-y-6">
              {jobsData.jobs_with_zero_applications > 0 && (
                <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 flex items-center space-x-3 text-amber-800 text-xs">
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                  <span>
                    <strong>Attention:</strong> {jobsData.jobs_with_zero_applications} active job requisition(s) currently have zero applicants. Review job description clarity or distribute across additional recruitment channels.
                  </span>
                </div>
              )}

              <div className="bg-white rounded-xl border border-slate-200/80 overflow-hidden shadow-xs">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Job Requisition Performance Ledger</h3>
                  <span className="text-xs text-slate-400 font-medium">
                    Total Evaluated: {jobsData.total_jobs_evaluated}
                  </span>
                </div>

                {jobsData.jobs.length === 0 ? (
                  <div className="py-16 text-center text-slate-400 text-xs">
                    No jobs match the current filter criteria.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-600">
                      <thead className="bg-slate-50/80 text-slate-700 font-semibold border-b border-slate-200/60 uppercase tracking-wider text-[11px]">
                        <tr>
                          <th className="px-6 py-3">Job Title & Dept</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Applications</th>
                          <th className="px-4 py-3">Interviews</th>
                          <th className="px-4 py-3">Hires</th>
                          <th className="px-4 py-3">Hire Conversion</th>
                          <th className="px-6 py-3">Created</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {jobsData.jobs.map((j) => (
                          <tr key={j.job_id} className="hover:bg-slate-50/60 transition-colors">
                            <td className="px-6 py-3.5">
                              <span className="font-semibold text-slate-900 block">{j.job_title}</span>
                              <span className="text-slate-400 text-[11px]">{j.department || "General"}</span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span
                                className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                                  j.status === "ACTIVE"
                                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                    : "bg-slate-100 text-slate-600"
                                }`}
                              >
                                {j.status}
                              </span>
                            </td>
                            <td className="px-4 py-3.5 font-medium">
                              {j.applications_count === 0 ? (
                                <span className="text-rose-600 font-semibold">0 applicants</span>
                              ) : (
                                j.applications_count
                              )}
                            </td>
                            <td className="px-4 py-3.5 font-medium">{j.interviews_count}</td>
                            <td className="px-4 py-3.5 font-semibold text-emerald-700">{j.hires_count}</td>
                            <td className="px-4 py-3.5">
                              <div className="flex items-center space-x-2">
                                <span className="font-semibold text-slate-800">{j.conversion_rate}%</span>
                                <div className="w-16 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                                  <div
                                    className="bg-emerald-600 h-1.5 rounded-full"
                                    style={{ width: `${Math.min(100, j.conversion_rate)}%` }}
                                  ></div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-3.5 text-slate-400">
                              {formatDateIST(j.created_at)}
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

          {/* ========================================================== */}
          {/* TAB 4: RECRUITER PERFORMANCE                               */}
          {/* ========================================================== */}
          {activeTab === "recruiters" && recruitersData && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">Recruiter Operational Workload & Attribution</h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Attributed workload, interviews coordinated, and verified candidate placements.
                    </p>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-600">
                    <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 text-[11px] uppercase">
                      <tr>
                        <th className="px-6 py-3">Recruiter</th>
                        <th className="px-4 py-3">Role</th>
                        <th className="px-4 py-3">Applications Handled</th>
                        <th className="px-4 py-3">Active Pipeline Workload</th>
                        <th className="px-4 py-3">Interviews Coordinated</th>
                        <th className="px-4 py-3">Attributable Hires</th>
                        <th className="px-6 py-3">Avg Time-To-Hire</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {recruitersData.recruiters.map((r) => (
                        <tr key={r.recruiter_id} className="hover:bg-slate-50/50">
                          <td className="px-6 py-3.5">
                            <span className="font-semibold text-slate-900 block">{r.recruiter_name}</span>
                            <span className="text-slate-400 text-[11px]">{r.recruiter_email}</span>
                          </td>
                          <td className="px-4 py-3.5">
                            <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-600">
                              {r.role}
                            </span>
                          </td>
                          <td className="px-4 py-3.5 font-medium">{r.applications_handled}</td>
                          <td className="px-4 py-3.5 font-medium">
                            <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-semibold border border-blue-100">
                              {r.active_workload} active
                            </span>
                          </td>
                          <td className="px-4 py-3.5 font-medium">{r.interviews_coordinated}</td>
                          <td className="px-4 py-3.5 font-bold text-emerald-700">{r.attributable_hires}</td>
                          <td className="px-6 py-3.5 text-slate-600">
                            {r.avg_time_to_hire_days !== null ? `${r.avg_time_to_hire_days} days` : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                <div className="mt-4 p-3 bg-slate-50 rounded-lg text-[11px] text-slate-500">
                  <span className="font-semibold">Attribution Rule: </span>
                  {recruitersData.attribution_rule}
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* TAB 5: CANDIDATE SOURCES                                   */}
          {/* ========================================================== */}
          {activeTab === "sources" && sourcesData && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Source Breakdown Table */}
                <div className="md:col-span-2 bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
                  <h3 className="text-sm font-bold text-slate-900 mb-1">Candidate Sourcing Effectiveness</h3>
                  <p className="text-xs text-slate-400 mb-4">
                    Comparison of application volume, interview throughput, and hire conversion across recorded sources.
                  </p>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-600">
                      <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 text-[11px] uppercase">
                        <tr>
                          <th className="px-4 py-3">Source Channel</th>
                          <th className="px-3 py-3">Candidates</th>
                          <th className="px-3 py-3">Applications</th>
                          <th className="px-3 py-3">Interviews</th>
                          <th className="px-3 py-3">Hires</th>
                          <th className="px-4 py-3">Conversion Rate</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {sourcesData.sources.map((s) => (
                          <tr key={s.source} className="hover:bg-slate-50/50">
                            <td className="px-4 py-3.5 font-bold text-slate-900 flex items-center space-x-2">
                              <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                              <span>{s.source}</span>
                            </td>
                            <td className="px-3 py-3.5">{s.candidates_count}</td>
                            <td className="px-3 py-3.5 font-medium">{s.applications_count}</td>
                            <td className="px-3 py-3.5 font-medium">{s.interviews_count}</td>
                            <td className="px-3 py-3.5 font-bold text-emerald-600">{s.hires_count}</td>
                            <td className="px-4 py-3.5 font-semibold text-slate-800">
                              {s.conversion_rate}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Sourcing Integrity Panel */}
                <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-slate-900 mb-1">Attribution Integrity</h3>
                    <p className="text-xs text-slate-400 mb-4">
                      HireLens strictly displays verified source attribution without guessing or synthesizing origins.
                    </p>

                    <div className="space-y-3">
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                        <span className="text-[11px] text-slate-500 uppercase font-semibold">Unattributed Candidates</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {sourcesData.unattributed_candidates_count} profiles
                        </p>
                      </div>

                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60">
                        <span className="text-[11px] text-slate-500 uppercase font-semibold">Unattributed Applications</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {sourcesData.unattributed_applications_count} submissions
                        </p>
                      </div>
                    </div>
                  </div>

                  <p className="text-[11px] text-slate-400 mt-4 leading-relaxed">
                    {sourcesData.attribution_notes}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* TAB 6: COST PER HIRE & RECRUITMENT EXPENSES                 */}
          {/* ========================================================== */}
          {activeTab === "costs" && costsData && (
            <div className="space-y-6">
              {/* Cost Summary Banner */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Cost Per Hire Card(s) */}
                {Object.keys(costsData.cost_per_hire_by_currency).length > 0 ? (
                  Object.entries(costsData.cost_per_hire_by_currency).map(([curr, cph]) => (
                    <div key={curr} className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
                      <span className="text-xs font-semibold text-slate-500 uppercase">
                        Cost Per Hire ({curr})
                      </span>
                      <p className="text-2xl font-bold text-slate-900 mt-1">
                        {cph !== null ? `${curr} ${cph.toLocaleString()}` : "N/A (0 hires)"}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Total {curr} spend: {costsData.total_expenses_by_currency[curr]?.toLocaleString() || 0}
                      </p>
                    </div>
                  ))
                ) : (
                  <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
                    <span className="text-xs font-semibold text-slate-500 uppercase">Cost Per Hire</span>
                    <p className="text-base font-semibold text-slate-400 mt-1">Insufficient cost data</p>
                    <p className="text-[11px] text-slate-400 mt-1">Log expenses to calculate metric</p>
                  </div>
                )}

                <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Attributable Hires</span>
                  <p className="text-2xl font-bold text-emerald-600 mt-1">{costsData.total_attributable_hires}</p>
                  <p className="text-[11px] text-slate-400 mt-1">In selected reporting period</p>
                </div>

                <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs">
                  <span className="text-xs font-semibold text-slate-500 uppercase">Status & Precision</span>
                  <p className="text-xs font-medium text-slate-700 mt-1">{costsData.status_message}</p>
                  <p className="text-[10px] text-slate-400 mt-1">Currencies strictly isolated</p>
                </div>
              </div>

              {/* Expense Ledger Table */}
              <div className="bg-white rounded-xl border border-slate-200/80 overflow-hidden shadow-xs">
                <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="text-sm font-bold text-slate-900">Recruitment Expenses Ledger</h3>
                  {canManageExpenses && (
                    <button
                      onClick={() => setShowExpenseModal(true)}
                      className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-xs font-semibold transition-colors flex items-center space-x-1"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add Expense</span>
                    </button>
                  )}
                </div>

                {expensesList.length === 0 ? (
                  <div className="py-16 text-center text-slate-400 text-xs">
                    No recruitment expenses recorded yet. Click "Add Expense" to log recruiting platform, ad, or agency costs.
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs text-slate-600">
                      <thead className="bg-slate-50 text-slate-700 font-semibold border-b border-slate-200 text-[11px] uppercase">
                        <tr>
                          <th className="px-6 py-3">Title & Job</th>
                          <th className="px-4 py-3">Category</th>
                          <th className="px-4 py-3">Amount</th>
                          <th className="px-4 py-3">Date</th>
                          <th className="px-4 py-3">Logged By</th>
                          {canManageExpenses && <th className="px-6 py-3 text-right">Actions</th>}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {expensesList.map((exp) => (
                          <tr key={exp.id} className="hover:bg-slate-50/50">
                            <td className="px-6 py-3.5">
                              <span className="font-semibold text-slate-900 block">{exp.title}</span>
                              <span className="text-slate-400 text-[11px]">
                                {exp.job_title ? `Associated: ${exp.job_title}` : "Agency-wide"}
                              </span>
                            </td>
                            <td className="px-4 py-3.5">
                              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700">
                                {exp.category.replace(/_/g, " ")}
                              </span>
                            </td>
                            <td className="px-4 py-3.5 font-bold text-slate-900">
                              {exp.currency} {exp.amount.toLocaleString()}
                            </td>
                            <td className="px-4 py-3.5 text-slate-500">
                              {formatDateIST(exp.expense_date)}
                            </td>
                            <td className="px-4 py-3.5 text-slate-500">
                              {exp.creator_name || "Admin"}
                            </td>
                            {canManageExpenses && (
                              <td className="px-6 py-3.5 text-right">
                                <button
                                  onClick={() => handleDeleteExpense(exp.id)}
                                  className="text-slate-400 hover:text-rose-600 p-1 rounded"
                                  title="Delete Expense"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </td>
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ========================================================== */}
          {/* TAB 7: AI GROUNDED RECRUITMENT INSIGHTS                     */}
          {/* ========================================================== */}
          {activeTab === "insights" && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 rounded-xl bg-violet-50 border border-violet-200 flex items-center justify-center text-violet-600 shadow-xs">
                      <Sparkles className="w-5 h-5" />
                    </div>
                    <div>
                      <h2 className="text-base font-bold text-slate-900">AI-Assisted Recruitment Operational Review</h2>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Factual interpretations and operational bottlenecks synthesized from verified database metrics.
                      </p>
                    </div>
                  </div>

                  <button
                    onClick={fetchAiInsights}
                    disabled={loadingInsights}
                    className="flex items-center space-x-1.5 px-3 py-1.5 border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg transition-colors"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingInsights ? "animate-spin text-blue-600" : ""}`} />
                    <span>Regenerate Analysis</span>
                  </button>
                </div>

                {loadingInsights ? (
                  <div className="py-20 flex flex-col items-center justify-center space-y-3 text-slate-400">
                    <div className="w-8 h-8 border-2 border-violet-600 border-t-transparent rounded-full animate-spin"></div>
                    <span className="text-xs font-medium">Synthesizing verified recruitment analytics...</span>
                  </div>
                ) : aiInsights ? (
                  <div className="space-y-6">
                    {/* Executive Summary Card */}
                    <div className="p-5 rounded-xl bg-gradient-to-r from-violet-50/60 to-blue-50/40 border border-violet-100">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-violet-700 block mb-1">
                        Executive Summary
                      </span>
                      <p className="text-sm text-slate-800 leading-relaxed font-medium">
                        "{aiInsights.summary}"
                      </p>
                    </div>

                    {/* Key Findings & Bottlenecks Split */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Key Findings */}
                      <div className="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80">
                        <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs mb-3">
                          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                          <span>Key Measured Observations</span>
                        </div>
                        <ul className="space-y-2 text-xs text-slate-600">
                          {aiInsights.key_findings.map((f, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <span className="text-blue-500 font-bold">•</span>
                              <span>{f}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Process Bottlenecks */}
                      <div className="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80">
                        <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs mb-3">
                          <AlertTriangle className="w-4 h-4 text-amber-500" />
                          <span>Identified Pipeline Bottlenecks</span>
                        </div>
                        <ul className="space-y-2 text-xs text-slate-600">
                          {aiInsights.bottlenecks.map((b, i) => (
                            <li key={i} className="flex items-start space-x-2">
                              <span className="text-amber-500 font-bold">•</span>
                              <span>{b}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>

                    {/* Operational Recommendations */}
                    <div className="p-5 rounded-xl bg-slate-50/60 border border-slate-200/80">
                      <div className="flex items-center space-x-2 text-slate-900 font-bold text-xs mb-3">
                        <Target className="w-4 h-4 text-blue-600" />
                        <span>Recommended Operational Interventions</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        {aiInsights.operational_recommendations.map((rec, i) => (
                          <div key={i} className="bg-white p-3.5 rounded-lg border border-slate-200 text-xs text-slate-700 leading-snug">
                            <span className="font-bold text-blue-600 block mb-1">Step {i + 1}</span>
                            {rec}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Grounding & Provider Disclaimer */}
                    <div className="p-4 rounded-lg bg-slate-100 border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between text-xs text-slate-500 gap-2">
                      <div className="flex items-center space-x-2">
                        <Info className="w-4 h-4 text-slate-400 shrink-0" />
                        <span>{aiInsights.grounding_disclaimer}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-white border border-slate-300 font-mono text-[10px] text-slate-600 whitespace-nowrap">
                        Provider: {aiInsights.provider_used}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="py-16 text-center text-slate-400 text-xs">
                    Click "Regenerate Analysis" to produce grounded AI insights.
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* ============================================================ */}
      {/* EXPENSE LOGGING MODAL (OWNER / ADMIN)                        */}
      {/* ============================================================ */}
      {showExpenseModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full border border-slate-200 shadow-xl overflow-hidden animate-in fade-in-50 zoom-in-95">
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <IndianRupee className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-base">Record Recruitment Expense</h3>
              </div>
              <button
                onClick={() => setShowExpenseModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1 rounded"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateExpense} className="p-6 space-y-4">
              {expenseFormError && (
                <div className="p-3 bg-rose-50 border border-rose-200 text-rose-700 text-xs rounded-lg">
                  {expenseFormError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Expense Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. LinkedIn Job Posting Slot"
                  value={expenseFormData.title}
                  onChange={(e) => setExpenseFormData({ ...expenseFormData, title: e.target.value })}
                  className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Amount *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    required
                    placeholder="25000"
                    value={expenseFormData.amount}
                    onChange={(e) => setExpenseFormData({ ...expenseFormData, amount: e.target.value })}
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Currency *
                  </label>
                  <select
                    value={expenseFormData.currency}
                    onChange={(e) => setExpenseFormData({ ...expenseFormData, currency: e.target.value })}
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600 bg-white"
                  >
                    <option value="INR">INR (₹)</option>
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Expense Category *
                  </label>
                  <select
                    value={expenseFormData.category}
                    onChange={(e) =>
                      setExpenseFormData({
                        ...expenseFormData,
                        category: e.target.value as ExpenseCategory,
                      })
                    }
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600 bg-white"
                  >
                    <option value="JOB_ADVERTISING">Job Advertising</option>
                    <option value="RECRUITMENT_PLATFORMS">Recruitment Platforms</option>
                    <option value="AGENCY_FEES">Agency Fees</option>
                    <option value="ASSESSMENT_COSTS">Assessment Costs</option>
                    <option value="INTERVIEW_EXPENSES">Interview Expenses</option>
                    <option value="OTHER">Other Expenses</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Date of Expense *
                  </label>
                  <input
                    type="date"
                    required
                    value={expenseFormData.expense_date}
                    onChange={(e) =>
                      setExpenseFormData({ ...expenseFormData, expense_date: e.target.value })
                    }
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Associated Job (Optional)
                </label>
                <select
                  value={expenseFormData.job_id}
                  onChange={(e) => setExpenseFormData({ ...expenseFormData, job_id: e.target.value })}
                  className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600 bg-white"
                >
                  <option value="">General Agency Expense (Unlinked)</option>
                  {jobsList.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description / Notes (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Additional context or invoice reference..."
                  value={expenseFormData.description}
                  onChange={(e) =>
                    setExpenseFormData({ ...expenseFormData, description: e.target.value })
                  }
                  className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 text-slate-800 focus:outline-blue-600"
                ></textarea>
              </div>

              <div className="pt-2 flex items-center justify-end space-x-2">
                <button
                  type="button"
                  onClick={() => setShowExpenseModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingExpense}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold transition-colors shadow-xs"
                >
                  {submittingExpense ? "Recording..." : "Record Expense"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// Reusable KPI Card Component
// ----------------------------------------------------------------------
function KPICard({
  title,
  value,
  subtitle,
  icon: Icon,
  color,
  tooltip,
}: {
  title: string;
  value: number;
  subtitle: string;
  icon: any;
  color: "blue" | "indigo" | "violet" | "emerald";
  tooltip?: string;
}) {
  const colorStyles = {
    blue: "bg-blue-50 text-blue-600 border-blue-100",
    indigo: "bg-indigo-50 text-indigo-600 border-indigo-100",
    violet: "bg-violet-50 text-violet-600 border-violet-100",
    emerald: "bg-emerald-50 text-emerald-600 border-emerald-100",
  }[color];

  return (
    <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between relative group">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">{title}</span>
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center border ${colorStyles}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-2">
        <span className="text-2xl font-extrabold text-slate-900 tracking-tight">{value}</span>
        <p className="text-[11px] text-slate-400 mt-0.5">{subtitle}</p>
      </div>

      {tooltip && (
        <div className="absolute left-4 -bottom-10 z-40 hidden group-hover:block bg-slate-900 text-white text-[11px] py-1 px-2.5 rounded-md shadow-md max-w-xs whitespace-normal pointer-events-none">
          {tooltip}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------------
// SVG Trend Chart Component
// ----------------------------------------------------------------------
function TrendChart({
  dataPoints,
}: {
  dataPoints: { date: string; applications: number; hires: number }[];
}) {
  if (dataPoints.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-slate-400 text-xs">
        No time-series data recorded for this date window.
      </div>
    );
  }

  const maxVal = Math.max(1, ...dataPoints.map((d) => Math.max(d.applications, d.hires)));
  const height = 200;
  const width = 600;
  const padX = 40;
  const padY = 20;

  const chartW = width - padX * 2;
  const chartH = height - padY * 2;

  const xStep = dataPoints.length > 1 ? chartW / (dataPoints.length - 1) : chartW;

  const appCoords = dataPoints.map((d, i) => {
    const x = padX + i * xStep;
    const y = padY + chartH - (d.applications / maxVal) * chartH;
    return { x, y, val: d.applications, date: d.date };
  });

  const hireCoords = dataPoints.map((d, i) => {
    const x = padX + i * xStep;
    const y = padY + chartH - (d.hires / maxVal) * chartH;
    return { x, y, val: d.hires, date: d.date };
  });

  const appPath = appCoords.reduce((acc, c, i) => `${acc} ${i === 0 ? "M" : "L"} ${c.x} ${c.y}`, "");
  const hirePath = hireCoords.reduce((acc, c, i) => `${acc} ${i === 0 ? "M" : "L"} ${c.x} ${c.y}`, "");

  return (
    <div className="w-full overflow-x-auto">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-56">
        {/* Horizontal grid lines */}
        {[0, 0.5, 1].map((pct, i) => {
          const y = padY + chartH - pct * chartH;
          return (
            <g key={i}>
              <line x1={padX} y1={y} x2={width - padX} y2={y} stroke="#f1f5f9" strokeDasharray="4 4" />
              <text x={padX - 8} y={y + 3} textAnchor="end" fontSize="10" fill="#94a3b8">
                {Math.round(pct * maxVal)}
              </text>
            </g>
          );
        })}

        {/* Applications Line */}
        <path d={appPath} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinecap="round" />
        {appCoords.map((c, i) => (
          <circle key={`app-${i}`} cx={c.x} cy={c.y} r="3" fill="#2563eb" />
        ))}

        {/* Hires Line */}
        <path d={hirePath} fill="none" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" />
        {hireCoords.map((c, i) => (
          <circle key={`hire-${i}`} cx={c.x} cy={c.y} r="3" fill="#10b981" />
        ))}

        {/* Date labels at bottom */}
        {dataPoints.map((d, i) => {
          if (dataPoints.length > 14 && i % Math.ceil(dataPoints.length / 7) !== 0) return null;
          const x = padX + i * xStep;
          return (
            <text
              key={`label-${i}`}
              x={x}
              y={height - 2}
              textAnchor="middle"
              fontSize="9"
              fill="#94a3b8"
            >
              {d.date.slice(5)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}

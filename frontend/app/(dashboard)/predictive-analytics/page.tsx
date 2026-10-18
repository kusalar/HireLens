"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  TrendingUp,
  Clock,
  AlertTriangle,
  Users,
  BrainCircuit,
  BarChart2,
  RefreshCw,
  ShieldAlert,
  CheckCircle,
  XCircle,
  HelpCircle,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Sparkles,
  Info,
  Calendar,
  Briefcase,
  User,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  PredictiveOverviewResponse,
  TimeToHireForecastResponse,
  HiringDemandForecastResponse,
  BottleneckAnalysisResponse,
  RecruitmentRiskRead,
  RecruiterCapacityResponse,
  ModelVersionRead,
  RiskStatus,
  RiskSeverity,
} from "@/types";

type ActiveTab = "overview" | "time-to-hire" | "demand" | "bottlenecks" | "risks" | "capacity" | "models";

export default function PredictiveAnalyticsPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("overview");
  const [overview, setOverview] = useState<PredictiveOverviewResponse | null>(null);
  const [timeToHire, setTimeToHire] = useState<TimeToHireForecastResponse | null>(null);
  const [demand, setDemand] = useState<HiringDemandForecastResponse | null>(null);
  const [bottlenecks, setBottlenecks] = useState<BottleneckAnalysisResponse | null>(null);
  const [risks, setRisks] = useState<RecruitmentRiskRead[]>([]);
  const [capacity, setCapacity] = useState<RecruiterCapacityResponse | null>(null);
  const [models, setModels] = useState<ModelVersionRead[]>([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [riskStatusFilter, setRiskStatusFilter] = useState<string>("OPEN");
  const [riskSeverityFilter, setRiskSeverityFilter] = useState<string>("ALL");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Acknowledge/Mitigate Modal
  const [selectedRisk, setSelectedRisk] = useState<RecruitmentRiskRead | null>(null);
  const [riskAction, setRiskAction] = useState<RiskStatus>("ACKNOWLEDGED");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [submittingRiskAction, setSubmittingRiskAction] = useState(false);

  useEffect(() => {
    loadAllData();
  }, []);

  useEffect(() => {
    if (activeTab === "risks") {
      loadRisks();
    }
  }, [riskStatusFilter, riskSeverityFilter]);

  async function loadAllData() {
    setLoading(true);
    setErrorBanner(null);
    try {
      const [ov, tth, dem, btn, rsk, cap, mdl] = await Promise.all([
        apiClient<PredictiveOverviewResponse>("/predictive-analytics/overview"),
        apiClient<TimeToHireForecastResponse>("/predictive-analytics/time-to-hire"),
        apiClient<HiringDemandForecastResponse>("/predictive-analytics/demand"),
        apiClient<BottleneckAnalysisResponse>("/predictive-analytics/bottlenecks"),
        apiClient<RecruitmentRiskRead[]>("/predictive-analytics/risks?status=OPEN"),
        apiClient<RecruiterCapacityResponse>("/predictive-analytics/capacity"),
        apiClient<ModelVersionRead[]>("/predictive-analytics/models"),
      ]);

      setOverview(ov);
      setTimeToHire(tth);
      setDemand(dem);
      setBottlenecks(btn);
      setRisks(rsk || []);
      setCapacity(cap);
      setModels(mdl || []);
    } catch (e: any) {
      setErrorBanner("Failed to load predictive recruitment intelligence: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadRisks() {
    try {
      let q = `/predictive-analytics/risks?`;
      if (riskStatusFilter !== "ALL") q += `status=${riskStatusFilter}&`;
      if (riskSeverityFilter !== "ALL") q += `severity=${riskSeverityFilter}`;
      const res = await apiClient<RecruitmentRiskRead[]>(q);
      setRisks(res || []);
    } catch (e: any) {
      console.error("Error loading risks:", e);
    }
  }

  async function handleRefresh() {
    setRefreshing(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<any>("/predictive-analytics/refresh", {
        method: "POST",
      });
      setSuccessBanner(
        `Predictive intelligence refreshed successfully: ${res.forecasts_generated} forecasts updated, ${res.risks_detected} risks identified.`
      );
      setTimeout(() => setSuccessBanner(null), 5000);
      await loadAllData();
    } catch (e: any) {
      setErrorBanner("Failed to recalculate forecasts: " + e.message);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleRiskStatusUpdate(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRisk) return;
    setSubmittingRiskAction(true);
    try {
      await apiClient(`/predictive-analytics/risks/${selectedRisk.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          status: riskAction,
          resolution_notes: resolutionNotes.trim() || undefined,
        }),
      });
      setSuccessBanner(`Risk status updated to ${riskAction}.`);
      setTimeout(() => setSuccessBanner(null), 4000);
      setSelectedRisk(null);
      setResolutionNotes("");
      loadRisks();
      // refresh overview stats
      apiClient<PredictiveOverviewResponse>("/predictive-analytics/overview").then(setOverview);
    } catch (e: any) {
      setErrorBanner("Failed to update risk: " + e.message);
    } finally {
      setSubmittingRiskAction(false);
    }
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider flex items-center gap-1">
              <BrainCircuit className="w-3.5 h-3.5" />
              Phase 12 Predictive Intelligence
            </span>
            <span className="text-xs text-slate-500 font-medium">Asia/Kolkata (IST)</span>
          </div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-indigo-600" />
            Predictive Recruitment Intelligence & Workforce Planning
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Deterministic statistical models and multi-variate machine learning forecasting hiring velocity, demand, and risk.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium px-4 py-2.5 rounded-xl shadow-sm transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "Re-evaluating Models..." : "Refresh Forecasts"}
          </button>
        </div>
      </div>

      {/* Alert Banners */}
      {errorBanner && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl flex items-center justify-between text-sm">
          <span>{errorBanner}</span>
          <button onClick={() => setErrorBanner(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {successBanner && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl flex items-center justify-between text-sm">
          <span>{successBanner}</span>
          <button onClick={() => setSuccessBanner(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Executive KPI Summary Cards */}
      {overview && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Avg. Time-to-Hire
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1 flex items-baseline gap-1">
              {overview.average_predicted_time_to_hire_days}
              <span className="text-xs font-normal text-slate-500">days</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
              <Clock className="w-3 h-3 text-indigo-500" />
              95% Confidence Interval
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              30-Day Demand
            </div>
            <div className="text-2xl font-bold text-indigo-600 mt-1 flex items-baseline gap-1">
              +{overview.demand_next_30d_hires}
              <span className="text-xs font-normal text-slate-500">hires</span>
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
              <TrendingUp className="w-3 h-3 text-emerald-500" />
              Projected requisition volume
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Active Jobs
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">
              {overview.active_jobs_count}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {overview.active_applications_count} active candidates
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Open Risks
            </div>
            <div className="text-2xl font-bold text-amber-600 mt-1 flex items-center gap-2">
              {overview.open_risks_count}
              {overview.critical_risks_count > 0 && (
                <span className="text-xs font-bold bg-rose-100 text-rose-700 px-2 py-0.5 rounded-full">
                  {overview.critical_risks_count} Critical
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-400 mt-1 flex items-center gap-1">
              <ShieldAlert className="w-3 h-3 text-amber-500" />
              Pipeline & delay warnings
            </div>
          </div>

          <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Capacity Status
            </div>
            <div className="text-lg font-bold text-slate-900 mt-1 flex items-center gap-2">
              {overview.capacity_summary.workload_balanced ? (
                <span className="text-emerald-600 flex items-center gap-1">
                  <CheckCircle className="w-4 h-4" /> Balanced
                </span>
              ) : (
                <span className="text-amber-600 flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4" /> Imbalance
                </span>
              )}
            </div>
            <div className="text-[11px] text-slate-400 mt-1">
              {overview.capacity_summary.overloaded_count} overloaded / {overview.capacity_summary.underutilized_count} under
            </div>
          </div>
        </div>
      )}

      {/* Grounded Strategic AI Brief */}
      {overview?.ai_strategic_brief && (
        <div className="bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/80 p-5 rounded-2xl border border-indigo-100 shadow-sm flex items-start gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5">
            <Sparkles className="w-5 h-5" />
          </div>
          <div className="space-y-1">
            <div className="text-xs font-bold uppercase tracking-wider text-indigo-900 flex items-center gap-2">
              AI Strategic Executive Briefing
              <span className="text-[10px] bg-indigo-200/60 text-indigo-800 font-semibold px-2 py-0.5 rounded-full">
                Grounded in Telemetry
              </span>
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              {overview.ai_strategic_brief}
            </p>
          </div>
        </div>
      )}

      {/* Workspace Navigation Tabs */}
      <div className="border-b border-slate-200">
        <nav className="flex space-x-6 overflow-x-auto pb-px">
          {[
            { id: "overview", label: "Executive Overview", icon: BarChart2 },
            { id: "time-to-hire", label: "Time-to-Hire Forecast", icon: Clock },
            { id: "demand", label: "Hiring Demand (30-90D)", icon: TrendingUp },
            { id: "bottlenecks", label: "Bottleneck Radar", icon: AlertTriangle },
            { id: "risks", label: "Risk Register", icon: ShieldAlert },
            { id: "capacity", label: "Recruiter Capacity", icon: Users },
            { id: "models", label: "Model Governance", icon: BrainCircuit },
          ].map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as ActiveTab)}
                className={`py-3 text-xs font-semibold border-b-2 flex items-center gap-2 whitespace-nowrap transition-all ${
                  active
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab 1: Executive Overview Content */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Top Risks Widget */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <ShieldAlert className="w-4 h-4 text-rose-500" />
                  Top Actionable Recruitment Risks
                </h3>
                <button
                  onClick={() => setActiveTab("risks")}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  View All &rarr;
                </button>
              </div>

              {overview?.top_risks.length === 0 ? (
                <div className="text-center py-8 text-slate-400 text-xs">
                  No active recruitment risks detected. Requisitions are operating within safe bounds.
                </div>
              ) : (
                <div className="space-y-3">
                  {overview?.top_risks.map((r) => (
                    <div
                      key={r.id}
                      className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/60 flex items-start justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                              r.severity === "CRITICAL"
                                ? "bg-rose-100 text-rose-700"
                                : r.severity === "HIGH"
                                ? "bg-amber-100 text-amber-700"
                                : "bg-blue-100 text-blue-700"
                            }`}
                          >
                            {r.severity}
                          </span>
                          <h4 className="text-xs font-bold text-slate-900">{r.title}</h4>
                        </div>
                        <p className="text-xs text-slate-600 line-clamp-1">{r.description}</p>
                        <p className="text-[11px] text-indigo-600 font-medium pt-0.5">
                          Action: {r.recommended_action}
                        </p>
                      </div>
                      <button
                        onClick={() => {
                          setSelectedRisk(r);
                          setRiskAction("ACKNOWLEDGED");
                        }}
                        className="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold px-2 py-1 rounded bg-white border border-slate-200 shadow-2xs"
                      >
                        Action
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Department Velocity Breakdown */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
                  <Clock className="w-4 h-4 text-indigo-500" />
                  Time-to-Hire by Department
                </h3>
                <button
                  onClick={() => setActiveTab("time-to-hire")}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                >
                  Full Matrix &rarr;
                </button>
              </div>

              <div className="space-y-3">
                {timeToHire?.by_department.map((dept) => (
                  <div
                    key={dept.department}
                    className="flex items-center justify-between p-3 rounded-xl border border-slate-100 bg-slate-50/50"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-800">{dept.department}</div>
                      <div className="text-[11px] text-slate-400">
                        CI: {dept.confidence_lower}d – {dept.confidence_upper}d
                        {dept.is_fallback && " (Empirical benchmark)"}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-extrabold text-slate-900">
                        {dept.predicted_days} <span className="text-xs font-normal text-slate-500">days</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-medium">
                        Sample: {dept.sample_size} hires
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Time-to-Hire Forecast */}
      {activeTab === "time-to-hire" && timeToHire && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-3">
            <h3 className="text-sm font-bold text-slate-900">Agency Hiring Cycle Forecast</h3>
            <p className="text-xs text-slate-600 leading-relaxed max-w-3xl">
              {timeToHire.explanation}
            </p>
            <div className="flex flex-wrap items-center gap-6 pt-2 text-xs">
              <div>
                <span className="text-slate-400">Predicted Agency Mean:</span>{" "}
                <strong className="text-slate-900 font-bold">{timeToHire.overall_agency_predicted_days} days</strong>
              </div>
              <div>
                <span className="text-slate-400">95% Confidence Interval:</span>{" "}
                <strong className="text-indigo-600 font-bold">
                  [{timeToHire.confidence_interval.lower_days}d, {timeToHire.confidence_interval.upper_days}d]
                </strong>
              </div>
              <div>
                <span className="text-slate-400">Historical Base Average:</span>{" "}
                <strong className="text-slate-700">{timeToHire.historical_average_days} days</strong>
              </div>
              <div>
                <span className="text-slate-400">Sample Size:</span>{" "}
                <strong className="text-slate-700">{timeToHire.sample_size} hires</strong>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="p-5 border-b border-slate-100 flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900">Active Requisitions Forecast</h4>
              <span className="text-xs text-slate-400">{timeToHire.by_job.length} open positions</span>
            </div>

            {timeToHire.by_job.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-xs">
                No active open requisitions found.
              </div>
            ) : (
              <div className="divide-y divide-slate-100">
                {timeToHire.by_job.map((j) => (
                  <div key={j.id} className="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                    <div>
                      <h5 className="text-xs font-bold text-slate-900">{j.job_title}</h5>
                      <p className="text-[11px] text-slate-400">{j.department || "General Requisition"}</p>
                    </div>
                    <div className="flex items-center gap-6">
                      <div className="text-right">
                        <div className="text-xs font-extrabold text-slate-900">
                          {j.predicted_value} days
                        </div>
                        <div className="text-[10px] text-slate-400">
                          [{j.confidence_lower}d – {j.confidence_upper}d]
                        </div>
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase ${
                          j.confidence_level === "HIGH"
                            ? "bg-emerald-100 text-emerald-800"
                            : j.confidence_level === "MEDIUM"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {j.confidence_level} Confidence
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Hiring Demand (30, 60, 90 Days) */}
      {activeTab === "demand" && demand && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                30-Day Projected Demand
              </div>
              <div className="text-3xl font-extrabold text-indigo-600 mt-2">
                +{demand.demand_30d} <span className="text-sm font-normal text-slate-500">hires</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Estimated candidate volume: <strong>{demand.expected_application_volume_30d} applications</strong>
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                60-Day Cumulative Demand
              </div>
              <div className="text-3xl font-extrabold text-slate-900 mt-2">
                +{demand.demand_60d} <span className="text-sm font-normal text-slate-500">hires</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Trend direction: <strong className="text-slate-800">{demand.historical_trend_direction}</strong>
              </p>
            </div>

            <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
              <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                90-Day Cumulative Demand
              </div>
              <div className="text-3xl font-extrabold text-slate-900 mt-2">
                +{demand.demand_90d} <span className="text-sm font-normal text-slate-500">hires</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Model confidence: <strong className="text-emerald-600">{demand.confidence_level}</strong>
              </p>
            </div>
          </div>

          {/* Department Breakdown */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h4 className="text-sm font-bold text-slate-900">Projected Demand by Department</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {demand.department_breakdown.map((dept) => (
                <div key={dept.department} className="p-4 rounded-xl border border-slate-100 bg-slate-50/50 space-y-2">
                  <h5 className="font-bold text-xs text-slate-900">{dept.department}</h5>
                  <div className="text-xs text-slate-600 space-y-1">
                    <div className="flex justify-between">
                      <span>30 Days:</span> <strong>+{dept.demand_30d}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>60 Days:</span> <strong>+{dept.demand_60d}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span>90 Days:</span> <strong>+{dept.demand_90d}</strong>
                    </div>
                    <div className="flex justify-between text-[11px] text-indigo-600 pt-1 border-t border-slate-200/60">
                      <span>Inflow Needed:</span> <strong>{dept.expected_applications_30d} apps</strong>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Time Series History vs Predicted Table */}
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h4 className="text-sm font-bold text-slate-900">Historical vs Projected Demand Horizon</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Period</th>
                    <th className="py-2.5 px-4">Actual Requisitions</th>
                    <th className="py-2.5 px-4">Predicted Requisitions</th>
                    <th className="py-2.5 px-4">Type</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {demand.historical_vs_predicted_data.map((pt, i) => (
                    <tr key={i} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-semibold text-slate-800">{pt.period}</td>
                      <td className="py-2.5 px-4 text-slate-700">
                        {pt.actual_jobs !== null && pt.actual_jobs !== undefined ? pt.actual_jobs : "—"}
                      </td>
                      <td className="py-2.5 px-4 font-bold text-indigo-600">
                        {pt.predicted_jobs !== null && pt.predicted_jobs !== undefined ? `+${pt.predicted_jobs}` : "—"}
                      </td>
                      <td className="py-2.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            pt.actual_jobs !== null && pt.actual_jobs !== undefined
                              ? "bg-slate-100 text-slate-600"
                              : "bg-indigo-50 text-indigo-700 border border-indigo-200"
                          }`}
                        >
                          {pt.actual_jobs !== null && pt.actual_jobs !== undefined ? "HISTORICAL" : "FORECAST"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Bottleneck Radar */}
      {activeTab === "bottlenecks" && bottlenecks && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Pipeline Stage Cycle Durations & Stagnation Radar</h3>
            <p className="text-xs text-slate-600 max-w-3xl">
              Identifies pipeline stages exceeding historical benchmark durations where candidates are prone to drop-off.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 pt-2">
              {bottlenecks.stagnant_stages.map((st) => (
                <div
                  key={st.stage}
                  className={`p-4 rounded-xl border transition-all ${
                    st.is_bottleneck
                      ? "border-rose-200 bg-rose-50/50 ring-1 ring-rose-200"
                      : "border-slate-200 bg-slate-50/40"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-900">{st.stage_label}</span>
                    {st.is_bottleneck && (
                      <span className="text-[10px] font-bold bg-rose-100 text-rose-700 px-1.5 py-0.5 rounded">
                        Bottleneck
                      </span>
                    )}
                  </div>
                  <div className="text-2xl font-black text-slate-900 mt-2">
                    {st.median_duration_days} <span className="text-xs font-normal text-slate-500">days</span>
                  </div>
                  <div className="text-[11px] text-slate-500 mt-2 space-y-0.5">
                    <div>Benchmark: {st.benchmark_days}d</div>
                    <div>P90 Duration: {st.p90_duration_days}d</div>
                    <div className="font-semibold text-slate-700">
                      Active: {st.current_active_candidates} candidate(s)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Interview Delays */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h4 className="text-sm font-bold text-slate-900">Interview Scheduling Latency</h4>
              <div className="space-y-3">
                {bottlenecks.interview_scheduling_delays.map((del) => (
                  <div
                    key={del.department}
                    className="p-3.5 rounded-xl border border-slate-100 bg-slate-50/50 flex items-center justify-between"
                  >
                    <div>
                      <div className="text-xs font-bold text-slate-900">{del.department}</div>
                      <div className="text-[11px] text-slate-500">
                        Benchmark: {del.benchmark_days}d · Pending: {del.pending_interviews_count}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-extrabold text-slate-900">
                        {del.average_days_to_schedule} days
                      </div>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                          del.status === "ELEVATED_DELAY"
                            ? "bg-rose-100 text-rose-700"
                            : "bg-emerald-100 text-emerald-700"
                        }`}
                      >
                        {del.status.replace("_", " ")}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recommendations */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
              <h4 className="text-sm font-bold text-slate-900">Operational Bottleneck Remedies</h4>
              <div className="space-y-2.5">
                {bottlenecks.recommendations.map((rec, i) => (
                  <div key={i} className="p-3 rounded-xl bg-indigo-50/40 border border-indigo-100 text-xs text-indigo-900 flex items-start gap-2.5">
                    <Info className="w-4 h-4 text-indigo-600 shrink-0 mt-0.5" />
                    <span>{rec}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab 5: Risk Register */}
      {activeTab === "risks" && (
        <div className="space-y-6">
          <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
              {["OPEN", "ACKNOWLEDGED", "MITIGATED", "DISMISSED", "ALL"].map((st) => (
                <button
                  key={st}
                  onClick={() => setRiskStatusFilter(st)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    riskStatusFilter === st
                      ? "bg-white text-slate-900 shadow-sm"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-slate-500">Severity:</span>
              <select
                value={riskSeverityFilter}
                onChange={(e) => setRiskSeverityFilter(e.target.value)}
                className="text-xs bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="ALL">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          {risks.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-16 text-center">
              <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-slate-800">No recruitment risks matching filters</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                All tracked pipeline stages and requisitions meet operational thresholds.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {risks.map((r) => (
                <div
                  key={r.id}
                  className={`bg-white rounded-2xl border p-5 shadow-sm transition-all flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                    r.status === "MITIGATED" || r.status === "DISMISSED"
                      ? "border-slate-200 opacity-60"
                      : r.severity === "CRITICAL"
                      ? "border-rose-300 ring-1 ring-rose-200"
                      : "border-slate-200 hover:border-indigo-200"
                  }`}
                >
                  <div className="space-y-1.5 max-w-3xl">
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                          r.severity === "CRITICAL"
                            ? "bg-rose-100 text-rose-700"
                            : r.severity === "HIGH"
                            ? "bg-amber-100 text-amber-700"
                            : "bg-blue-100 text-blue-700"
                        }`}
                      >
                        {r.severity}
                      </span>
                      <span className="text-[10px] font-medium bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                        {r.risk_type.replace("_", " ")}
                      </span>
                      <span className="text-[10px] font-medium border border-slate-200 px-2 py-0.5 rounded-full text-slate-500">
                        Status: {r.status}
                      </span>
                    </div>

                    <h4 className="font-bold text-sm text-slate-900">{r.title}</h4>
                    <p className="text-xs text-slate-600 leading-relaxed">{r.description}</p>

                    <div className="text-xs text-indigo-700 font-semibold pt-1">
                      Recommended Action: {r.recommended_action}
                    </div>

                    {r.resolution_notes && (
                      <div className="text-[11px] text-slate-500 italic bg-slate-50 p-2 rounded-lg">
                        Resolution Notes: {r.resolution_notes}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 self-end md:self-center">
                    {r.status === "OPEN" && (
                      <button
                        onClick={() => {
                          setSelectedRisk(r);
                          setRiskAction("ACKNOWLEDGED");
                        }}
                        className="text-xs font-semibold px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}
                    {r.status !== "MITIGATED" && (
                      <button
                        onClick={() => {
                          setSelectedRisk(r);
                          setRiskAction("MITIGATED");
                        }}
                        className="text-xs font-semibold px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white transition-colors"
                      >
                        Mitigate
                      </button>
                    )}
                    {r.status !== "DISMISSED" && (
                      <button
                        onClick={() => {
                          setSelectedRisk(r);
                          setRiskAction("DISMISSED");
                        }}
                        className="text-xs font-semibold px-2.5 py-1.5 rounded-xl text-slate-400 hover:text-slate-600 transition-colors"
                        title="Dismiss risk"
                      >
                        Dismiss
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Recruiter Capacity Planning */}
      {activeTab === "capacity" && capacity && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Recruiter Capacity & Operational Workload Index</h3>
                <p className="text-xs text-slate-500">
                  Calculated from active applications (weight 1.0), upcoming interviews (weight 2.5), and open requisitions (weight 5.0).
                </p>
              </div>
              <div className="text-xs text-slate-500">
                Agency Workload Benchmark: <strong>{capacity.agency_average_workload}</strong>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
              {capacity.recruiters.map((rec) => (
                <div key={rec.id} className="p-5 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-bold text-slate-900">{rec.recruiter_name}</h4>
                      <div className="text-[10px] text-slate-400">{rec.recruiter_email}</div>
                    </div>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                        rec.utilization_status === "OPTIMAL"
                          ? "bg-emerald-100 text-emerald-700"
                          : rec.utilization_status === "OVERLOADED"
                          ? "bg-rose-100 text-rose-700"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {rec.utilization_status}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs pt-1">
                    <div className="p-2 bg-white rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px]">Apps</div>
                      <div className="font-extrabold text-slate-800">{rec.active_applications_count}</div>
                    </div>
                    <div className="p-2 bg-white rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px]">Interviews</div>
                      <div className="font-extrabold text-slate-800">{rec.upcoming_interviews_count}</div>
                    </div>
                    <div className="p-2 bg-white rounded-xl border border-slate-100">
                      <div className="text-slate-400 text-[10px]">Jobs</div>
                      <div className="font-extrabold text-slate-800">{rec.open_requisitions_count}</div>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-xs pt-2 border-t border-slate-200/60">
                    <span className="text-slate-500 font-medium">Workload Index:</span>
                    <strong className="text-indigo-600 font-bold">{rec.workload_index}</strong>
                  </div>

                  {rec.recommendations && rec.recommendations.length > 0 && (
                    <p className="text-[11px] text-slate-600 bg-white p-2 rounded-lg border border-slate-100">
                      {rec.recommendations[0]}
                    </p>
                  )}
                </div>
              ))}
            </div>

            {/* Advisory Disclaimer */}
            <div className="bg-amber-50 border border-amber-200 p-3.5 rounded-xl text-xs text-amber-800 flex items-start gap-2.5">
              <Info className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>
                <strong>Advisory Only:</strong> HireLens AI provides workload insights strictly for human decision-makers. The system will never autonomously reassign candidates, interviews, or recruiter accounts.
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 7: Model Governance & Monitoring */}
      {activeTab === "models" && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm space-y-4">
            <h3 className="text-sm font-bold text-slate-900">Predictive Model Registry & Evaluation Governance</h3>
            <p className="text-xs text-slate-600 max-w-3xl">
              Tracks active model versions, algorithms, training sample sizes, and empirical validation metrics across your agency.
            </p>

            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-500 uppercase font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Version Tag</th>
                    <th className="py-2.5 px-4">Model Type</th>
                    <th className="py-2.5 px-4">Algorithm</th>
                    <th className="py-2.5 px-4">Training Samples</th>
                    <th className="py-2.5 px-4">Validation Metrics</th>
                    <th className="py-2.5 px-4">Trained Date (IST)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {models.map((m) => (
                    <tr key={m.id} className="hover:bg-slate-50">
                      <td className="py-2.5 px-4 font-mono font-bold text-indigo-600">{m.version_tag}</td>
                      <td className="py-2.5 px-4 text-slate-700">{m.model_type}</td>
                      <td className="py-2.5 px-4 font-semibold text-slate-800">{m.algorithm}</td>
                      <td className="py-2.5 px-4 text-slate-700">{m.training_sample_size} hires</td>
                      <td className="py-2.5 px-4 font-mono text-[11px] text-slate-600">
                        {m.evaluation_metrics
                          ? `MAE: ${m.evaluation_metrics.mae || "—"}d | RMSE: ${m.evaluation_metrics.rmse || "—"} | R²: ${m.evaluation_metrics.r2 || "—"}`
                          : "Baseline Fallback"}
                      </td>
                      <td className="py-2.5 px-4 text-slate-500">{m.trained_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Action Modal for Risks */}
      {selectedRisk && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-base font-bold text-slate-900 mb-1">Update Risk: {selectedRisk.title}</h3>
            <p className="text-xs text-slate-500 mb-4">{selectedRisk.description}</p>

            <form onSubmit={handleRiskStatusUpdate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Status Transition
                </label>
                <select
                  value={riskAction}
                  onChange={(e) => setRiskAction(e.target.value as RiskStatus)}
                  className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                >
                  <option value="ACKNOWLEDGED">Acknowledge</option>
                  <option value="MITIGATED">Mitigate (Resolved)</option>
                  <option value="DISMISSED">Dismiss</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Resolution Notes (Optional)
                </label>
                <textarea
                  rows={3}
                  placeholder="Record operational steps taken, assigned recruiters, or mitigation rationale..."
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setSelectedRisk(null)}
                  className="text-xs px-4 py-2 font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingRiskAction}
                  className="text-xs px-4 py-2 font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm transition-colors disabled:opacity-50"
                >
                  {submittingRiskAction ? "Saving..." : "Update Risk"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

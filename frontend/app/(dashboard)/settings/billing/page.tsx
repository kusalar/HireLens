"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  CreditCard,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  ShieldAlert,
  Download,
  Building2,
  RefreshCw,
  Zap,
  Check,
  ChevronRight,
  TrendingUp,
  FileText,
  Activity,
  Layers,
  Sparkles,
  Lock,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  SubscriptionPlanRead,
  AgencySubscriptionRead,
  UsageOverviewResponse,
  BillingInvoiceRead,
  AgencyBillingProfileRead,
  CheckoutSessionResponse,
  PaymentTransaction,
} from "@/types";

export default function BillingWorkspacePage() {
  const [user, setUser] = useState<any>(null);
  const [plans, setPlans] = useState<SubscriptionPlanRead[]>([]);
  const [subscription, setSubscription] = useState<AgencySubscriptionRead | null>(null);
  const [usage, setUsage] = useState<UsageOverviewResponse | null>(null);
  const [invoices, setInvoices] = useState<BillingInvoiceRead[]>([]);
  const [transactions, setTransactions] = useState<PaymentTransaction[]>([]);
  const [profile, setProfile] = useState<AgencyBillingProfileRead | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Billing interval toggle (MONTHLY vs ANNUAL)
  const [selectedInterval, setSelectedInterval] = useState<"MONTHLY" | "ANNUAL">("MONTHLY");

  // Checkout Modal State
  const [checkoutModalOpen, setCheckoutModalOpen] = useState<boolean>(false);
  const [selectedPlanForCheckout, setSelectedPlanForCheckout] = useState<SubscriptionPlanRead | null>(null);
  const [selectedGateway, setSelectedGateway] = useState<"MOCK" | "RAZORPAY" | "STRIPE">("MOCK");
  const [initiatingCheckout, setInitiatingCheckout] = useState<boolean>(false);
  const [activeCheckoutSession, setActiveCheckoutSession] = useState<CheckoutSessionResponse | null>(null);
  const [verifyingPayment, setVerifyingPayment] = useState<boolean>(false);

  // Billing Profile Form
  const [legalName, setLegalName] = useState<string>("");
  const [gstin, setGstin] = useState<string>("");
  const [billingEmail, setBillingEmail] = useState<string>("");
  const [addressLine1, setAddressLine1] = useState<string>("");
  const [city, setCity] = useState<string>("");
  const [stateProvince, setStateProvince] = useState<string>("");
  const [postalCode, setPostalCode] = useState<string>("");
  const [country, setCountry] = useState<string>("IN");
  const [savingProfile, setSavingProfile] = useState<boolean>(false);
  const [gstinError, setGstinError] = useState<string | null>(null);

  // Cancel / Reactivate controls
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Load User and Base Data
  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const [u, pList, subData, useData, invData, txData, profData] = await Promise.allSettled([
        apiClient("/auth/me"),
        apiClient("/billing/plans"),
        apiClient("/billing/subscription"),
        apiClient("/billing/usage"),
        apiClient("/billing/invoices"),
        apiClient("/billing/transactions"),
        apiClient("/billing/profile"),
      ]);

      if (u.status === "fulfilled") setUser(u.value);
      if (pList.status === "fulfilled") setPlans(pList.value as SubscriptionPlanRead[]);
      if (subData.status === "fulfilled") setSubscription(subData.value as AgencySubscriptionRead);
      if (useData.status === "fulfilled") setUsage(useData.value as UsageOverviewResponse);
      if (invData.status === "fulfilled") setInvoices(invData.value as BillingInvoiceRead[]);
      if (txData.status === "fulfilled") setTransactions(txData.value as PaymentTransaction[]);
      if (profData.status === "fulfilled" && profData.value) {
        const p = profData.value as AgencyBillingProfileRead;
        setProfile(p);
        setLegalName(p.legal_name || "");
        setGstin(p.gstin || "");
        setBillingEmail(p.billing_email || "");
        setAddressLine1(p.address_line1 || "");
        setCity(p.city || "");
        setStateProvince(p.state_province || "");
        setPostalCode(p.postal_code || "");
        setCountry(p.country || "IN");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load billing information.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // GSTIN Live Validation (Indian 15-character alphanumeric format)
  const handleGstinChange = (value: string) => {
    const uppercaseVal = value.toUpperCase();
    setGstin(uppercaseVal);
    if (!uppercaseVal) {
      setGstinError(null);
      return;
    }
    const gstinRegex = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/;
    if (!gstinRegex.test(uppercaseVal)) {
      setGstinError("Invalid GSTIN format (e.g. 27AAAAA0000A1Z5)");
    } else {
      setGstinError(null);
    }
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (gstin && gstinError) {
      return;
    }
    setSavingProfile(true);
    setError(null);
    try {
      const updated: any = await apiClient("/billing/profile", {
        method: "PUT",
        body: JSON.stringify({
          legal_name: legalName || "Agency Legal Entity",
          billing_email: billingEmail || user?.email || "billing@agency.com",
          address_line1: addressLine1 || null,
          city: city || null,
          state_province: stateProvince || null,
          postal_code: postalCode || null,
          country: country || "IN",
          gstin: gstin || null,
          currency: selectedGateway === "STRIPE" ? "USD" : "INR",
        }),
      });
      setProfile(updated);
      setActionSuccess("Billing profile updated successfully.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to save billing profile.");
    } finally {
      setSavingProfile(false);
    }
  };

  const handleOpenCheckout = (plan: SubscriptionPlanRead) => {
    setSelectedPlanForCheckout(plan);
    setActiveCheckoutSession(null);
    setCheckoutModalOpen(true);
  };

  const handleInitiateCheckout = async () => {
    if (!selectedPlanForCheckout) return;
    setInitiatingCheckout(true);
    setError(null);

    try {
      const session: CheckoutSessionResponse = await apiClient("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({
          plan_slug: selectedPlanForCheckout.slug,
          billing_interval: selectedInterval,
          gateway: selectedGateway,
          currency: selectedGateway === "STRIPE" ? "USD" : "INR",
        }),
      });
      setActiveCheckoutSession(session);
    } catch (err: any) {
      setError(err.message || "Failed to initiate checkout session.");
    } finally {
      setInitiatingCheckout(false);
    }
  };

  const handleVerifyCheckout = async () => {
    if (!activeCheckoutSession) return;
    setVerifyingPayment(true);
    setError(null);

    try {
      const payload: any = {
        gateway: activeCheckoutSession.gateway,
        session_id: activeCheckoutSession.session_id,
        order_id: activeCheckoutSession.order_id || activeCheckoutSession.session_id,
        payment_id: `pay_${Date.now()}`,
        signature: "mock_signature_valid",
      };

      await apiClient("/billing/verify", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      setActionSuccess(`Successfully activated subscription for ${selectedPlanForCheckout?.name || "new plan"}!`);
      setCheckoutModalOpen(false);
      setActiveCheckoutSession(null);
      setSelectedPlanForCheckout(null);
      await loadData(true);
      setTimeout(() => setActionSuccess(null), 5000);
    } catch (err: any) {
      setError(err.message || "Payment verification failed.");
    } finally {
      setVerifyingPayment(false);
    }
  };

  const handleCancelSubscription = async () => {
    if (!confirm("Are you sure you want to cancel your subscription? It will remain active until the end of the billing period.")) {
      return;
    }
    setActionLoading(true);
    setError(null);
    try {
      await apiClient("/billing/subscription/cancel", { method: "POST" });
      setActionSuccess("Subscription marked for cancellation at period end.");
      await loadData(true);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to cancel subscription.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReactivateSubscription = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await apiClient("/billing/subscription/reactivate", { method: "POST" });
      setActionSuccess("Subscription renewed and reactivated!");
      await loadData(true);
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err: any) {
      setError(err.message || "Failed to reactivate subscription.");
    } finally {
      setActionLoading(false);
    }
  };

  const handleDownloadReceipt = async (invoiceId: string, invoiceNumber: string) => {
    try {
      const receiptText: string = await apiClient(`/billing/invoices/${invoiceId}/receipt`);
      const blob = new Blob([receiptText], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${invoiceNumber}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`Failed to download receipt: ${err.message}`);
    }
  };

  const isOwnerOrAdmin = user?.role === "OWNER" || user?.role === "ADMIN";

  const getUsageBarColor = (pct: number) => {
    if (pct >= 95) return "bg-rose-500";
    if (pct >= 80) return "bg-amber-500";
    return "bg-blue-600";
  };

  const formatIST = (dateStr?: string | null) => {
    if (!dateStr) return "N/A";
    try {
      const d = new Date(dateStr);
      return (
        d.toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        }) + " IST"
      );
    } catch {
      return dateStr;
    }
  };

  // Helper to extract meter data safely
  const getMeter = (key: string) => {
    return usage?.meters?.[key] || {
      current_usage: 0,
      hard_limit: 0,
      utilization_pct: 0,
      is_unlimited: false,
    };
  };

  const activeJobsMeter = getMeter("ACTIVE_JOBS");
  const recruitersMeter = getMeter("RECRUITERS");
  const candidatesMeter = getMeter("CANDIDATES_MONTHLY");
  const aiTokensMeter = getMeter("AI_TOKENS_MONTHLY");
  const interviewsMeter = getMeter("INTERVIEWS_MONTHLY");
  const workflowsMeter = getMeter("WORKFLOW_RUNS_MONTHLY");
  const storageMeter = getMeter("RESUME_STORAGE_MB");

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      {/* Top Header */}
      <div className="border-b border-slate-200/80 pb-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-tr from-slate-900 to-slate-800 text-white rounded-xl shadow-xs">
              <CreditCard className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-xl font-bold text-slate-900 tracking-tight">Enterprise Subscription & Billing</h1>
                <span className="px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-[10px] font-semibold tracking-wide uppercase">
                  Phase 14 Production
                </span>
                {user?.is_platform_admin && (
                  <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-semibold tracking-wide uppercase flex items-center space-x-1">
                    <ShieldAlert className="w-3 h-3 text-indigo-600" />
                    <span>Platform Admin</span>
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Manage organization subscription tiers, usage allowances, real-time quota meters, and GST-compliant tax invoices.
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => loadData(true)}
              disabled={refreshing}
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors flex items-center space-x-1.5 shadow-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
            <Link
              href="/settings"
              className="px-3 py-1.5 text-xs font-semibold text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors shadow-xs"
            >
              &larr; Settings
            </Link>
          </div>
        </div>
      </div>

      {/* Action / Error Banners */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-3 animate-in fade-in-50">
          <XCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-rose-900">Billing Operation Notice</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {actionSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-start space-x-3 animate-in fade-in-50">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold text-emerald-900">Success</p>
            <p className="text-xs text-emerald-700 mt-0.5">{actionSuccess}</p>
          </div>
        </div>
      )}

      {/* Quota Exhaustion / Warning alerts */}
      {usage?.has_warnings && (
        <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm space-y-1">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
            <p className="font-semibold text-amber-900">Subscription Quota Notice</p>
          </div>
          <p className="text-xs text-amber-800 pl-6">
            One or more metered resource limits have reached soft thresholds (80%+). Upgrade your subscription tier to avoid interruption.
          </p>
        </div>
      )}

      {/* SECTION 1: Active Subscription Card */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-6 bg-gradient-to-r from-slate-900 via-slate-800 to-indigo-950 text-white">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
              <div className="flex items-center space-x-3">
                <span className="px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 text-xs font-mono font-bold uppercase tracking-wider">
                  {subscription?.tier || "FREE"} TIER
                </span>
                <span
                  className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                    subscription?.status === "ACTIVE"
                      ? "bg-emerald-500 text-white"
                      : subscription?.status === "TRIALING"
                      ? "bg-blue-500 text-white"
                      : "bg-amber-500 text-slate-900"
                  }`}
                >
                  {subscription?.status || "ACTIVE"}
                </span>
                {subscription?.cancel_at_period_end && (
                  <span className="px-2 py-0.5 rounded-full bg-rose-500/20 border border-rose-400/40 text-rose-300 text-[10px] font-semibold">
                    Cancels at period end
                  </span>
                )}
              </div>

              <h2 className="text-2xl font-bold tracking-tight text-white mt-3">
                {subscription?.plan_name || `${subscription?.tier || "Free"} Recruitment Plan`}
              </h2>
              <p className="text-xs text-slate-300 mt-1 max-w-xl">
                Enterprise multi-tenant recruitment operating platform with deterministic candidate matching, AI Copilot, and intelligent workflow automation.
              </p>
            </div>

            <div className="flex flex-col sm:flex-row md:flex-col items-start md:items-end justify-between gap-3 text-right">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">Current Billing Period</p>
                <p className="text-xs font-mono text-slate-200 mt-0.5">
                  {formatIST(subscription?.current_period_start)} &rarr; {formatIST(subscription?.current_period_end)}
                </p>
              </div>

              {isOwnerOrAdmin && (
                <div className="flex items-center space-x-2 mt-2">
                  {subscription?.cancel_at_period_end ? (
                    <button
                      onClick={handleReactivateSubscription}
                      disabled={actionLoading}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors shadow-xs"
                    >
                      Reactivate Subscription
                    </button>
                  ) : subscription?.tier !== "FREE" ? (
                    <button
                      onClick={handleCancelSubscription}
                      disabled={actionLoading}
                      className="px-3.5 py-1.5 text-xs font-semibold bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors border border-white/20 shadow-xs"
                    >
                      Cancel at Period End
                    </button>
                  ) : null}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Feature Entitlements Strip */}
        <div className="bg-slate-50/80 px-6 py-4 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div className="flex items-center space-x-2 text-slate-700">
            <Sparkles className="w-4 h-4 text-indigo-600" />
            <span>AI Copilot: Enabled</span>
          </div>
          <div className="flex items-center space-x-2 text-slate-700">
            <TrendingUp className="w-4 h-4 text-emerald-600" />
            <span>Predictive Intelligence: Active</span>
          </div>
          <div className="flex items-center space-x-2 text-slate-700">
            <Zap className="w-4 h-4 text-amber-600" />
            <span>Workflow Automation: Active</span>
          </div>
          <div className="flex items-center space-x-2 text-slate-700">
            <Lock className="w-4 h-4 text-purple-600" />
            <span>Security Governance: Active</span>
          </div>
        </div>
      </div>

      {/* SECTION 2: Live Usage Meters & Quotas */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <Activity className="w-5 h-5 text-indigo-600" />
              <span>Real-Time Usage & Quota Consumption</span>
            </h3>
            <p className="text-xs text-slate-500">
              Metered across monthly billing cycle with atomic concurrency locks. Security, privacy, and legal hold data operations are never blocked.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Active Jobs Meter */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Active Jobs</span>
              <span className="text-[11px] font-mono font-bold text-slate-900">
                {activeJobsMeter.current_usage} / {activeJobsMeter.is_unlimited ? "Unlimited" : activeJobsMeter.hard_limit}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full ${getUsageBarColor(activeJobsMeter.utilization_pct)}`}
                style={{ width: `${Math.min(100, activeJobsMeter.utilization_pct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Concurrent slots</span>
              <span>{Math.round(activeJobsMeter.utilization_pct)}% used</span>
            </div>
          </div>

          {/* Active Recruiters Meter */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Active Recruiters</span>
              <span className="text-[11px] font-mono font-bold text-slate-900">
                {recruitersMeter.current_usage} / {recruitersMeter.is_unlimited ? "Unlimited" : recruitersMeter.hard_limit}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full ${getUsageBarColor(recruitersMeter.utilization_pct)}`}
                style={{ width: `${Math.min(100, recruitersMeter.utilization_pct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Seat allocation</span>
              <span>{Math.round(recruitersMeter.utilization_pct)}% used</span>
            </div>
          </div>

          {/* Monthly Candidates Meter */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">Monthly Candidates</span>
              <span className="text-[11px] font-mono font-bold text-slate-900">
                {candidatesMeter.current_usage} / {candidatesMeter.is_unlimited ? "Unlimited" : candidatesMeter.hard_limit}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full ${getUsageBarColor(candidatesMeter.utilization_pct)}`}
                style={{ width: `${Math.min(100, candidatesMeter.utilization_pct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Monthly reset</span>
              <span>{Math.round(candidatesMeter.utilization_pct)}% used</span>
            </div>
          </div>

          {/* AI Token Consumption Meter */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-600">AI Tokens</span>
              <span className="text-[11px] font-mono font-bold text-slate-900">
                {aiTokensMeter.current_usage.toLocaleString()} /{" "}
                {aiTokensMeter.is_unlimited ? "Unlimited" : aiTokensMeter.hard_limit.toLocaleString()}
              </span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className={`h-2 rounded-full ${getUsageBarColor(aiTokensMeter.utilization_pct)}`}
                style={{ width: `${Math.min(100, aiTokensMeter.utilization_pct)}%` }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-slate-400">
              <span>Copilot & insights</span>
              <span>{Math.round(aiTokensMeter.utilization_pct)}% used</span>
            </div>
          </div>
        </div>

        {/* Secondary usage details */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 bg-white rounded-xl border border-slate-200 text-xs flex items-center justify-between">
            <span className="text-slate-600">Interview Scheduling:</span>
            <span className="font-mono font-semibold text-slate-900">
              {interviewsMeter.current_usage} / {interviewsMeter.is_unlimited ? "Unlimited" : interviewsMeter.hard_limit}
            </span>
          </div>
          <div className="p-4 bg-white rounded-xl border border-slate-200 text-xs flex items-center justify-between">
            <span className="text-slate-600">Workflow Automations:</span>
            <span className="font-mono font-semibold text-slate-900">
              {workflowsMeter.current_usage} / {workflowsMeter.is_unlimited ? "Unlimited" : workflowsMeter.hard_limit}
            </span>
          </div>
          <div className="p-4 bg-white rounded-xl border border-slate-200 text-xs flex items-center justify-between">
            <span className="text-slate-600">Resume Storage:</span>
            <span className="font-mono font-semibold text-slate-900">
              {storageMeter.current_usage} MB / {storageMeter.is_unlimited ? "Unlimited" : `${storageMeter.hard_limit} MB`}
            </span>
          </div>
        </div>
      </div>

      {/* SECTION 3: Plan Comparison & Upgrade Matrix */}
      <div className="space-y-6 pt-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <Layers className="w-5 h-5 text-indigo-600" />
              <span>Subscription Plans & Feature Entitlements</span>
            </h3>
            <p className="text-xs text-slate-500">
              Select the optimal plan for your recruitment team. Switch between monthly and annual billing (with 2 months free on annual plans).
            </p>
          </div>

          {/* Monthly / Annual Toggle */}
          <div className="flex items-center bg-slate-100 p-1 rounded-xl self-start sm:self-auto border border-slate-200">
            <button
              onClick={() => setSelectedInterval("MONTHLY")}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
                selectedInterval === "MONTHLY"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setSelectedInterval("ANNUAL")}
              className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all flex items-center space-x-1.5 ${
                selectedInterval === "ANNUAL"
                  ? "bg-white text-slate-900 shadow-xs"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              <span>Annual Billing</span>
              <span className="px-1.5 py-0.2 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                Save 17%
              </span>
            </button>
          </div>
        </div>

        {/* Plan Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {plans.map((p) => {
            const isCurrent = subscription?.plan_id === p.id || subscription?.tier === p.tier;
            const price =
              selectedInterval === "ANNUAL"
                ? `₹${Number(p.price_inr * 10).toLocaleString()}/yr`
                : `₹${Number(p.price_inr).toLocaleString()}/mo`;

            return (
              <div
                key={p.id}
                className={`relative flex flex-col justify-between p-5 rounded-2xl border transition-all ${
                  isCurrent
                    ? "bg-gradient-to-b from-indigo-50/50 to-white border-indigo-400 shadow-md ring-2 ring-indigo-500/20"
                    : p.tier === "PROFESSIONAL"
                    ? "bg-white border-blue-300 shadow-sm hover:border-blue-400"
                    : "bg-white border-slate-200 shadow-xs hover:border-slate-300"
                }`}
              >
                {p.tier === "PROFESSIONAL" && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full bg-blue-600 text-white text-[10px] font-bold uppercase tracking-wider shadow-xs">
                    Most Popular
                  </span>
                )}

                <div>
                  <div className="flex items-center justify-between">
                    <h4 className="text-sm font-bold text-slate-900">{p.name}</h4>
                    {isCurrent && (
                      <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                        Current
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1 min-h-[32px]">
                    {p.name} recruitment tier with dedicated agency quotas.
                  </p>

                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <p className="text-xl font-bold font-mono text-slate-900">{price}</p>
                    <p className="text-[10px] text-slate-400 mt-0.5">
                      {selectedInterval === "ANNUAL" ? "Billed annually" : "Billed monthly"}
                    </p>
                  </div>

                  <ul className="mt-4 space-y-2 text-xs text-slate-600 border-t border-slate-100 pt-3">
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{p.max_active_jobs === -1 ? "Unlimited" : `${p.max_active_jobs}`} active jobs</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{p.max_recruiters === -1 ? "Unlimited" : `${p.max_recruiters}`} recruiters</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{p.max_candidates_monthly === -1 ? "Unlimited" : `${p.max_candidates_monthly}`} candidates/mo</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>{p.max_ai_tokens_monthly === -1 ? "Unlimited" : `${p.max_ai_tokens_monthly.toLocaleString()}`} AI tokens</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Deterministic candidate matching</span>
                    </li>
                    <li className="flex items-start space-x-2">
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <span>Interview advisory locks</span>
                    </li>
                  </ul>
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100">
                  {isCurrent ? (
                    <button
                      disabled
                      className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-500 cursor-default"
                    >
                      Active Plan
                    </button>
                  ) : isOwnerOrAdmin ? (
                    <button
                      onClick={() => handleOpenCheckout(p)}
                      className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-900 hover:bg-slate-800 text-white transition-colors shadow-xs flex items-center justify-center space-x-1"
                    >
                      <span>Choose {p.name}</span>
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  ) : (
                    <button
                      disabled
                      className="w-full py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-400 cursor-not-allowed"
                    >
                      Admin Only
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SECTION 4: Corporate Billing Profile & GSTIN */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-xs p-6">
        <div className="flex items-center space-x-3 mb-5">
          <div className="p-2 bg-indigo-50 text-indigo-700 rounded-lg">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-slate-900">Corporate Billing Profile & GST Compliance</h3>
            <p className="text-xs text-slate-500">
              Provide corporate details for tax invoicing. Indian entities with a valid GSTIN receive automated 18% GST itemized tax invoices.
            </p>
          </div>
        </div>

        <form onSubmit={handleSaveProfile} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Legal Entity / Business Name</label>
              <input
                type="text"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
                disabled={!isOwnerOrAdmin}
                placeholder="e.g. Acme Talent Solutions Pvt Ltd"
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                GSTIN (India 15-digit Tax Identifier)
              </label>
              <input
                type="text"
                value={gstin}
                onChange={(e) => handleGstinChange(e.target.value)}
                disabled={!isOwnerOrAdmin}
                placeholder="e.g. 27AAAAA0000A1Z5"
                maxLength={15}
                className={`w-full text-xs px-3 py-2 bg-slate-50 border rounded-lg focus:outline-none focus:ring-1 disabled:opacity-60 font-mono uppercase ${
                  gstinError ? "border-rose-400 focus:ring-rose-500 bg-rose-50/50" : "border-slate-300 focus:ring-blue-500"
                }`}
              />
              {gstinError && <p className="text-[11px] text-rose-600 mt-1">{gstinError}</p>}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Billing Email for Invoices</label>
              <input
                type="email"
                value={billingEmail}
                onChange={(e) => setBillingEmail(e.target.value)}
                disabled={!isOwnerOrAdmin}
                placeholder="finance@acme.com"
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Billing Address Line 1</label>
              <input
                type="text"
                value={addressLine1}
                onChange={(e) => setAddressLine1(e.target.value)}
                disabled={!isOwnerOrAdmin}
                placeholder="Tower B, Tech Park, Outer Ring Road"
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
              />
            </div>

            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">City</label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  placeholder="Bengaluru"
                  className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">State / Province</label>
                <input
                  type="text"
                  value={stateProvince}
                  onChange={(e) => setStateProvince(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  placeholder="Karnataka"
                  className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">PIN / Postal Code</label>
                <input
                  type="text"
                  value={postalCode}
                  onChange={(e) => setPostalCode(e.target.value)}
                  disabled={!isOwnerOrAdmin}
                  placeholder="560103"
                  className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Country</label>
              <input
                type="text"
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={!isOwnerOrAdmin}
                className="w-full text-xs px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:opacity-60"
              />
            </div>
          </div>

          {isOwnerOrAdmin && (
            <div className="flex justify-end pt-3">
              <button
                type="submit"
                disabled={savingProfile || !!gstinError}
                className="px-4 py-2 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-xs transition-colors disabled:opacity-50 flex items-center space-x-1.5"
              >
                {savingProfile && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                <span>Save Billing Profile</span>
              </button>
            </div>
          )}
        </form>
      </div>

      {/* SECTION 5: Invoices & Financial Records */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center space-x-2">
              <FileText className="w-5 h-5 text-indigo-600" />
              <span>Invoices & Financial Receipts</span>
            </h3>
            <p className="text-xs text-slate-500">
              Immutable tax invoices with GST breakdown, issued after successful payment verification.
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Invoice #</th>
                  <th className="px-5 py-3">Date (IST)</th>
                  <th className="px-5 py-3">Subtotal</th>
                  <th className="px-5 py-3">Tax (GST)</th>
                  <th className="px-5 py-3">Total Paid</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3 text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {invoices.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-5 py-10 text-center text-slate-400">
                      No invoices issued yet.
                    </td>
                  </tr>
                ) : (
                  invoices.map((inv) => (
                    <tr key={inv.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-5 py-3.5 font-mono font-medium text-slate-900">{inv.invoice_number}</td>
                      <td className="px-5 py-3.5 font-mono text-slate-500">{formatIST(inv.created_at)}</td>
                      <td className="px-5 py-3.5 font-mono">
                        {inv.currency === "INR" ? "₹" : "$"}
                        {Number(inv.subtotal).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 font-mono text-slate-500">
                        {inv.currency === "INR" ? "₹" : "$"}
                        {Number(inv.tax_amount).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 font-mono font-bold text-slate-900">
                        {inv.currency === "INR" ? "₹" : "$"}
                        {Number(inv.total_amount).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${
                            inv.status === "PAID"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                          }`}
                        >
                          {inv.status}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-right">
                        <button
                          onClick={() => handleDownloadReceipt(inv.id, inv.invoice_number)}
                          className="px-2.5 py-1 text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 rounded border border-indigo-200 transition-colors inline-flex items-center space-x-1"
                        >
                          <Download className="w-3.5 h-3.5" />
                          <span>Download</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* SECTION 6: Payment Transaction Audit */}
      <div className="space-y-4">
        <div>
          <h3 className="text-base font-bold text-slate-900 tracking-tight flex items-center space-x-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            <span>Payment Gateway Transaction Log</span>
          </h3>
          <p className="text-xs text-slate-500">
            Audit trail of gateway attempts with idempotency verification. Card credentials are never stored.
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Gateway</th>
                  <th className="px-5 py-3">Order / Tx ID</th>
                  <th className="px-5 py-3">Amount</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3">Timestamp (IST)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {transactions.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                      No payment transactions recorded yet.
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx) => (
                    <tr key={tx.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-5 py-3 font-semibold text-slate-900">{tx.payment_gateway}</td>
                      <td className="px-5 py-3 font-mono text-[11px] text-slate-600">
                        {tx.gateway_order_id || tx.gateway_transaction_id || tx.id}
                      </td>
                      <td className="px-5 py-3 font-mono font-medium">
                        {tx.currency === "INR" ? "₹" : "$"}
                        {Number(tx.amount).toLocaleString()}
                      </td>
                      <td className="px-5 py-3">
                        <span
                          className={`px-2 py-0.5 rounded border text-[10px] font-bold uppercase tracking-wider ${
                            tx.status === "SUCCEEDED"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : tx.status === "FAILED"
                              ? "bg-rose-50 text-rose-700 border-rose-200"
                              : "bg-blue-50 text-blue-700 border-blue-200"
                          }`}
                        >
                          {tx.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 font-mono text-slate-500">{formatIST(tx.created_at)}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* CHECKOUT MODAL */}
      {checkoutModalOpen && selectedPlanForCheckout && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in-50">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-lg w-full p-6 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Upgrade to {selectedPlanForCheckout.name}
                </h3>
                <p className="text-xs text-slate-500">Secure checkout session with server-side signature validation.</p>
              </div>
              <button
                onClick={() => {
                  setCheckoutModalOpen(false);
                  setActiveCheckoutSession(null);
                }}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                &times;
              </button>
            </div>

            {/* Plan and Price Summary */}
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-2">
              <div className="flex justify-between">
                <span className="text-slate-600">Selected Tier:</span>
                <span className="font-bold text-slate-900">{selectedPlanForCheckout.tier}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-600">Billing Interval:</span>
                <span className="font-semibold text-slate-900">{selectedInterval}</span>
              </div>
              <div className="flex justify-between border-t border-slate-200 pt-2 text-sm">
                <span className="font-semibold text-slate-800">Total Due:</span>
                <span className="font-bold font-mono text-indigo-600">
                  {selectedGateway === "STRIPE"
                    ? `$${Number(selectedInterval === "ANNUAL" ? selectedPlanForCheckout.price_usd * 10 : selectedPlanForCheckout.price_usd).toLocaleString()}`
                    : `₹${Number(selectedInterval === "ANNUAL" ? selectedPlanForCheckout.price_inr * 10 : selectedPlanForCheckout.price_inr).toLocaleString()}`}
                </span>
              </div>
            </div>

            {/* Gateway Selector */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-700">Select Payment Gateway</label>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setSelectedGateway("MOCK");
                    setActiveCheckoutSession(null);
                  }}
                  className={`p-3 rounded-xl border text-center transition-all ${
                    selectedGateway === "MOCK"
                      ? "bg-indigo-50 border-indigo-400 text-indigo-900 font-semibold"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <p className="text-xs font-bold">Mock Gateway</p>
                  <p className="text-[10px] text-slate-500">Test Sandbox</p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedGateway("RAZORPAY");
                    setActiveCheckoutSession(null);
                  }}
                  className={`p-3 rounded-xl border text-center transition-all ${
                    selectedGateway === "RAZORPAY"
                      ? "bg-blue-50 border-blue-400 text-blue-900 font-semibold"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <p className="text-xs font-bold">Razorpay</p>
                  <p className="text-[10px] text-slate-500">India (INR/UPI)</p>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedGateway("STRIPE");
                    setActiveCheckoutSession(null);
                  }}
                  className={`p-3 rounded-xl border text-center transition-all ${
                    selectedGateway === "STRIPE"
                      ? "bg-purple-50 border-purple-400 text-purple-900 font-semibold"
                      : "bg-white border-slate-200 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  <p className="text-xs font-bold">Stripe</p>
                  <p className="text-[10px] text-slate-500">Global (USD)</p>
                </button>
              </div>
            </div>

            {/* Checkout Actions */}
            {!activeCheckoutSession ? (
              <div className="pt-2">
                <button
                  onClick={handleInitiateCheckout}
                  disabled={initiatingCheckout}
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
                >
                  {initiatingCheckout && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Initiate Secure Checkout Session</span>
                </button>
              </div>
            ) : (
              <div className="space-y-4 pt-2">
                <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-200 text-xs text-emerald-800">
                  <p className="font-semibold">Checkout Session Created</p>
                  <p className="text-[11px] font-mono mt-0.5 truncate">
                    Order ID: {activeCheckoutSession.order_id || activeCheckoutSession.session_id}
                  </p>
                </div>

                <button
                  onClick={handleVerifyCheckout}
                  disabled={verifyingPayment}
                  className="w-full py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs rounded-xl shadow-xs transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
                >
                  {verifyingPayment && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  <span>Confirm & Activate Subscription</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

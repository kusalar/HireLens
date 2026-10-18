"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  MessageSquare,
  FileText,
  GitCompare,
  Calendar,
  BarChart3,
  Send,
  Plus,
  Trash2,
  RefreshCw,
  Copy,
  Check,
  AlertCircle,
  ExternalLink,
  ShieldCheck,
  ChevronRight,
  Info,
  Clock,
  Briefcase,
  Users,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  CopilotConversation,
  CopilotMessage,
  CopilotContextType,
  JobDescriptionGenerateResponse,
  JobDescriptionImproveResponse,
  JobDescriptionQualityReport,
  CopilotCandidateComparisonResponse,
  InterviewPrepResponse,
  AnalyticsExplainResponse,
  Job,
  Candidate,
  Interview,
} from "@/types";

export default function CopilotPage() {
  const [activeTab, setActiveTab] = useState<"chat" | "jd" | "compare" | "prep" | "analytics">("chat");

  // Chat & Conversation States
  const [conversations, setConversations] = useState<CopilotConversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [activeConv, setActiveConv] = useState<CopilotConversation | null>(null);
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [inputMessage, setInputMessage] = useState("");
  const [sendingMessage, setSendingMessage] = useState(false);
  const [loadingConversations, setLoadingConversations] = useState(false);
  const [contextType, setContextType] = useState<CopilotContextType>("AGENCY_OVERVIEW");
  const [contextId, setContextId] = useState<string>("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Entities for Context Selection
  const [availableJobs, setAvailableJobs] = useState<Job[]>([]);
  const [availableCandidates, setAvailableCandidates] = useState<Candidate[]>([]);
  const [availableInterviews, setAvailableInterviews] = useState<Interview[]>([]);

  // JD Assistant States
  const [jdMode, setJdMode] = useState<"generate" | "improve" | "analyze">("generate");
  const [jdTitle, setJdTitle] = useState("");
  const [jdDept, setJdDept] = useState("Engineering");
  const [jdLevel, setJdLevel] = useState("Senior");
  const [jdSkills, setJdSkills] = useState("Python, React, AWS, PostgreSQL");
  const [jdExpMin, setJdExpMin] = useState(4);
  const [jdWorkMode, setJdWorkMode] = useState("HYBRID");
  const [jdGenerating, setJdGenerating] = useState(false);
  const [generatedJd, setGeneratedJd] = useState<JobDescriptionGenerateResponse | null>(null);
  const [existingJdText, setExistingJdText] = useState("");
  const [improvedJd, setImprovedJd] = useState<JobDescriptionImproveResponse | null>(null);
  const [qualityReport, setQualityReport] = useState<JobDescriptionQualityReport | null>(null);
  const [copiedJd, setCopiedJd] = useState(false);

  // Candidate Compare States
  const [compareJobId, setCompareJobId] = useState("");
  const [selectedCandidateIds, setSelectedCandidateIds] = useState<string[]>([]);
  const [comparing, setComparing] = useState(false);
  const [comparisonResult, setComparisonResult] = useState<CopilotCandidateComparisonResponse | null>(null);

  // Interview Prep States
  const [prepInterviewId, setPrepInterviewId] = useState("");
  const [prepping, setPrepping] = useState(false);
  const [prepBrief, setPrepBrief] = useState<InterviewPrepResponse | null>(null);

  // Analytics Explain States
  const [analyticsExplaining, setAnalyticsExplaining] = useState(false);
  const [analyticsResult, setAnalyticsResult] = useState<AnalyticsExplainResponse | null>(null);

  // Error and Notification Messages
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Quick suggestions
  const quickPrompts = [
    "How many active candidates and jobs do we have?",
    "Summarize our hiring funnel conversion rates.",
    "Which interviews are scheduled this week?",
    "Explain why applications take time in the interview stage.",
  ];

  // -------------------------------------------------------------------
  // Initial Data Loading
  // -------------------------------------------------------------------
  useEffect(() => {
    loadConversations();
    loadContextEntities();
  }, []);

  useEffect(() => {
    if (activeConvId) {
      loadConversationDetails(activeConvId);
    }
  }, [activeConvId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function loadContextEntities() {
    try {
      const [jobsRes, candsRes, intsRes] = await Promise.allSettled([
        apiClient<Job[]>("/jobs"),
        apiClient<Candidate[]>("/candidates"),
        apiClient<Interview[]>("/interviews"),
      ]);

      if (jobsRes.status === "fulfilled" && Array.isArray(jobsRes.value)) {
        setAvailableJobs(jobsRes.value);
        if (jobsRes.value.length > 0 && !compareJobId) {
          setCompareJobId(jobsRes.value[0].id);
        }
      }
      if (candsRes.status === "fulfilled" && Array.isArray(candsRes.value)) {
        setAvailableCandidates(candsRes.value);
      }
      if (intsRes.status === "fulfilled" && Array.isArray(intsRes.value)) {
        setAvailableInterviews(intsRes.value);
        if (intsRes.value.length > 0 && !prepInterviewId) {
          setPrepInterviewId(intsRes.value[0].id);
        }
      }
    } catch (e) {
      console.error("Failed to load context entities", e);
    }
  }

  async function loadConversations() {
    setLoadingConversations(true);
    try {
      const data = await apiClient<CopilotConversation[]>("/copilot/conversations");
      setConversations(data);
      if (data.length > 0 && !activeConvId) {
        setActiveConvId(data[0].id);
      }
    } catch (e: any) {
      console.error("Failed to load conversations", e);
    } finally {
      setLoadingConversations(false);
    }
  }

  async function loadConversationDetails(id: string) {
    try {
      const data = await apiClient<CopilotConversation>(`/copilot/conversations/${id}`);
      setActiveConv(data);
      setMessages(data.messages || []);
      setContextType(data.context_type);
      setContextId(data.context_id || "");
    } catch (e: any) {
      console.error("Failed to load conversation turns", e);
    }
  }

  async function handleCreateNewConversation() {
    try {
      const newConv = await apiClient<CopilotConversation>("/copilot/conversations", {
        method: "POST",
        body: JSON.stringify({
          title: "New Recruitment Conversation",
          context_type: contextType,
          context_id: contextId ? contextId : null,
        }),
      });
      setConversations([newConv, ...conversations]);
      setActiveConvId(newConv.id);
      setActiveConv(newConv);
      setMessages([]);
    } catch (e: any) {
      setErrorBanner("Failed to initialize new conversation: " + (e.message || "Unknown error"));
    }
  }

  async function handleDeleteConversation(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await apiClient(`/copilot/conversations/${id}`, { method: "DELETE" });
      const updated = conversations.filter((c) => c.id !== id);
      setConversations(updated);
      if (activeConvId === id) {
        if (updated.length > 0) {
          setActiveConvId(updated[0].id);
        } else {
          setActiveConvId(null);
          setActiveConv(null);
          setMessages([]);
        }
      }
    } catch (err: any) {
      setErrorBanner("Failed to delete conversation: " + (err.message || "Error"));
    }
  }

  async function handleSendMessage(promptText?: string) {
    const textToSend = promptText || inputMessage;
    if (!textToSend.trim() || sendingMessage) return;

    let convId = activeConvId;
    if (!convId) {
      try {
        const newConv = await apiClient<CopilotConversation>("/copilot/conversations", {
          method: "POST",
          body: JSON.stringify({
            title: textToSend.slice(0, 40) + "...",
            context_type: contextType,
            context_id: contextId ? contextId : null,
          }),
        });
        setConversations([newConv, ...conversations]);
        setActiveConvId(newConv.id);
        setActiveConv(newConv);
        convId = newConv.id;
      } catch (e: any) {
        setErrorBanner("Could not initialize conversation: " + e.message);
        return;
      }
    }

    setSendingMessage(true);
    setInputMessage("");

    // Optimistically add user message
    const tempUserMsg: CopilotMessage = {
      id: "temp-" + Date.now(),
      conversation_id: convId!,
      role: "USER",
      content: textToSend,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const reply = await apiClient<CopilotMessage>(`/copilot/conversations/${convId}/messages`, {
        method: "POST",
        body: JSON.stringify({
          content: textToSend,
          context_type: contextType,
          context_id: contextId ? contextId : null,
        }),
      });
      setMessages((prev) => [...prev.filter((m) => m.id !== tempUserMsg.id), tempUserMsg, reply]);
    } catch (e: any) {
      setErrorBanner("Copilot turn failed: " + (e.message || "Provider timeout"));
    } finally {
      setSendingMessage(false);
    }
  }

  // -------------------------------------------------------------------
  // Job Description Assistant Handlers
  // -------------------------------------------------------------------
  async function handleGenerateJd() {
    if (!jdTitle.trim()) {
      setErrorBanner("Please specify a job title.");
      return;
    }
    setJdGenerating(true);
    setErrorBanner(null);
    try {
      const skillsArray = jdSkills.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await apiClient<JobDescriptionGenerateResponse>("/copilot/job-descriptions/generate", {
        method: "POST",
        body: JSON.stringify({
          title: jdTitle,
          department: jdDept,
          seniority_level: jdLevel,
          required_skills: skillsArray,
          experience_min: jdExpMin,
          work_mode: jdWorkMode,
          employment_type: "FULL_TIME",
        }),
      });
      setGeneratedJd(res);
      setExistingJdText(res.full_text);
    } catch (e: any) {
      setErrorBanner("JD generation failed: " + e.message);
    } finally {
      setJdGenerating(false);
    }
  }

  async function handleImproveJd() {
    if (!existingJdText.trim() || existingJdText.length < 10) {
      setErrorBanner("Please provide job description text (minimum 10 characters).");
      return;
    }
    setJdGenerating(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<JobDescriptionImproveResponse>("/copilot/job-descriptions/improve", {
        method: "POST",
        body: JSON.stringify({
          existing_description: existingJdText,
        }),
      });
      setImprovedJd(res);
    } catch (e: any) {
      setErrorBanner("JD refinement failed: " + e.message);
    } finally {
      setJdGenerating(false);
    }
  }

  async function handleAnalyzeJd() {
    if (!existingJdText.trim()) {
      setErrorBanner("Please provide job description text to analyze.");
      return;
    }
    setJdGenerating(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<JobDescriptionQualityReport>("/copilot/job-descriptions/analyze", {
        method: "POST",
        body: JSON.stringify({
          raw_text: existingJdText,
        }),
      });
      setQualityReport(res);
    } catch (e: any) {
      setErrorBanner("Quality analysis failed: " + e.message);
    } finally {
      setJdGenerating(false);
    }
  }

  // -------------------------------------------------------------------
  // Candidate Comparison Handler
  // -------------------------------------------------------------------
  async function handleCompareCandidates() {
    if (!compareJobId) {
      setErrorBanner("Please select a target job requisition.");
      return;
    }
    if (selectedCandidateIds.length < 2) {
      setErrorBanner("Please select at least 2 candidates to compare.");
      return;
    }
    setComparing(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<CopilotCandidateComparisonResponse>("/copilot/candidates/compare", {
        method: "POST",
        body: JSON.stringify({
          job_id: compareJobId,
          candidate_ids: selectedCandidateIds,
        }),
      });
      setComparisonResult(res);
    } catch (e: any) {
      setErrorBanner("Candidate comparison failed: " + e.message);
    } finally {
      setComparing(false);
    }
  }

  // -------------------------------------------------------------------
  // Interview Preparation Handler
  // -------------------------------------------------------------------
  async function handlePrepareInterview() {
    if (!prepInterviewId) {
      setErrorBanner("Please select an upcoming interview.");
      return;
    }
    setPrepping(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<InterviewPrepResponse>(`/copilot/interviews/${prepInterviewId}/prepare`, {
        method: "POST",
      });
      setPrepBrief(res);
    } catch (e: any) {
      setErrorBanner("Interview prep brief generation failed: " + e.message);
    } finally {
      setPrepping(false);
    }
  }

  // -------------------------------------------------------------------
  // Analytics Intelligence Handler
  // -------------------------------------------------------------------
  async function handleExplainAnalytics() {
    setAnalyticsExplaining(true);
    setErrorBanner(null);
    try {
      const res = await apiClient<AnalyticsExplainResponse>("/copilot/analytics/explain", {
        method: "POST",
        body: JSON.stringify({
          preset: "LAST_30_DAYS",
          focus_area: "OVERALL",
        }),
      });
      setAnalyticsResult(res);
    } catch (e: any) {
      setErrorBanner("Analytics explanation failed: " + e.message);
    } finally {
      setAnalyticsExplaining(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Banner / Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b pb-5">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg">
              <Sparkles className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-gray-900">AI Recruitment Copilot</h1>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            Grounded hiring assistant for talent insights, JD drafting, candidate comparisons, and interview prep.
          </p>
        </div>

        {/* Global Advisory Badge */}
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-full text-xs font-medium text-amber-800">
          <ShieldCheck className="w-4 h-4 text-amber-600" />
          <span>Human-in-the-Loop • Advisory AI</span>
        </div>
      </div>

      {/* Global Error Banner */}
      {errorBanner && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{errorBanner}</span>
          </div>
          <button onClick={() => setErrorBanner(null)} className="text-red-500 hover:text-red-700 font-bold">
            ×
          </button>
        </div>
      )}

      {/* Primary Navigation Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        <button
          onClick={() => setActiveTab("chat")}
          className={`py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap flex items-center gap-2 ${
            activeTab === "chat"
              ? "border-indigo-600 text-indigo-600 font-semibold"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          Chat Assistant
        </button>
        <button
          onClick={() => setActiveTab("jd")}
          className={`py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap flex items-center gap-2 ${
            activeTab === "jd"
              ? "border-indigo-600 text-indigo-600 font-semibold"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          <FileText className="w-4 h-4" />
          JD Assistant
        </button>
        <button
          onClick={() => setActiveTab("compare")}
          className={`py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap flex items-center gap-2 ${
            activeTab === "compare"
              ? "border-indigo-600 text-indigo-600 font-semibold"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          <GitCompare className="w-4 h-4" />
          Candidate Comparison
        </button>
        <button
          onClick={() => setActiveTab("prep")}
          className={`py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap flex items-center gap-2 ${
            activeTab === "prep"
              ? "border-indigo-600 text-indigo-600 font-semibold"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          <Calendar className="w-4 h-4" />
          Interview Briefs
        </button>
        <button
          onClick={() => {
            setActiveTab("analytics");
            if (!analyticsResult) handleExplainAnalytics();
          }}
          className={`py-3 px-4 text-sm font-medium border-b-2 whitespace-nowrap flex items-center gap-2 ${
            activeTab === "analytics"
              ? "border-indigo-600 text-indigo-600 font-semibold"
              : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
          }`}
        >
          <BarChart3 className="w-4 h-4" />
          Analytics Intelligence
        </button>
      </div>

      {/* -------------------------------------------------------------------
          TAB 1: CHAT ASSISTANT
      ------------------------------------------------------------------- */}
      {activeTab === "chat" && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-[640px]">
          {/* Conversation Sidebar */}
          <div className="lg:col-span-1 bg-white border rounded-xl p-4 flex flex-col justify-between shadow-sm">
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b">
                <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Conversations</span>
                <button
                  onClick={handleCreateNewConversation}
                  className="flex items-center gap-1 text-xs bg-indigo-50 text-indigo-600 hover:bg-indigo-100 px-2 py-1 rounded font-medium transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  New
                </button>
              </div>

              {loadingConversations ? (
                <div className="text-center py-8 text-xs text-gray-400">Loading history...</div>
              ) : conversations.length === 0 ? (
                <div className="text-center py-8 text-xs text-gray-400">No active conversations. Start one!</div>
              ) : (
                <div className="space-y-1.5 max-h-[460px] overflow-y-auto pr-1">
                  {conversations.map((c) => (
                    <div
                      key={c.id}
                      onClick={() => setActiveConvId(c.id)}
                      className={`group p-2.5 rounded-lg text-xs cursor-pointer flex items-center justify-between transition-colors ${
                        activeConvId === c.id
                          ? "bg-indigo-50 text-indigo-900 font-semibold border-indigo-200 border"
                          : "hover:bg-gray-50 text-gray-700"
                      }`}
                    >
                      <div className="truncate pr-2">
                        <div className="truncate">{c.title}</div>
                        <span className="text-[10px] text-gray-400">{c.context_type.replace("_", " ")}</span>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConversation(c.id, e)}
                        className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 p-1 rounded"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Context Filter Selector */}
            <div className="pt-4 border-t space-y-2">
              <label className="text-[11px] font-semibold text-gray-600 block">Active Grounding Scope</label>
              <select
                value={contextType}
                onChange={(e) => {
                  setContextType(e.target.value as CopilotContextType);
                  setContextId("");
                }}
                className="w-full text-xs border rounded-md p-1.5 bg-gray-50 text-gray-800"
              >
                <option value="AGENCY_OVERVIEW">Agency Overview</option>
                <option value="JOB">Specific Job Requisition</option>
                <option value="CANDIDATE">Specific Candidate Profile</option>
                <option value="INTERVIEW">Specific Interview Session</option>
                <option value="ANALYTICS">Recruitment Analytics</option>
              </select>

              {contextType === "JOB" && (
                <select
                  value={contextId}
                  onChange={(e) => setContextId(e.target.value)}
                  className="w-full text-xs border rounded-md p-1.5 bg-white text-gray-800"
                >
                  <option value="">Select a Job...</option>
                  {availableJobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} ({j.department || "General"})
                    </option>
                  ))}
                </select>
              )}

              {contextType === "CANDIDATE" && (
                <select
                  value={contextId}
                  onChange={(e) => setContextId(e.target.value)}
                  className="w-full text-xs border rounded-md p-1.5 bg-white text-gray-800"
                >
                  <option value="">Select a Candidate...</option>
                  {availableCandidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.full_name} ({c.current_title || "Candidate"})
                    </option>
                  ))}
                </select>
              )}

              {contextType === "INTERVIEW" && (
                <select
                  value={contextId}
                  onChange={(e) => setContextId(e.target.value)}
                  className="w-full text-xs border rounded-md p-1.5 bg-white text-gray-800"
                >
                  <option value="">Select an Interview...</option>
                  {availableInterviews.map((i) => (
                    <option key={i.id} value={i.id}>
                      {i.title} ({i.round_name})
                    </option>
                  ))}
                </select>
              )}
            </div>
          </div>

          {/* Main Chat Panel */}
          <div className="lg:col-span-3 bg-white border rounded-xl flex flex-col justify-between shadow-sm overflow-hidden">
            {/* Thread Header */}
            <div className="p-3.5 border-b bg-gray-50 flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-gray-800">{activeConv?.title || "New Recruitment Session"}</span>
                <span className="bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded text-[10px] font-medium">
                  Scope: {contextType.replace("_", " ")}
                </span>
              </div>
              <div className="text-gray-400 text-[11px] flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                <span>Asia/Kolkata Grounded</span>
              </div>
            </div>

            {/* Messages Scroll Area */}
            <div className="p-4 flex-1 overflow-y-auto space-y-4 max-h-[500px]">
              {messages.length === 0 ? (
                <div className="text-center py-12 space-y-4">
                  <div className="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-full flex items-center justify-center mx-auto">
                    <Sparkles className="w-6 h-6" />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-gray-800">Ask HireLens Copilot</h3>
                    <p className="text-xs text-gray-500 max-w-md mx-auto mt-1">
                      Query recruitment pipelines, summarize candidate qualifications, or analyze funnel metrics with verified citations.
                    </p>
                  </div>

                  {/* Suggested Prompts */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-lg mx-auto text-left pt-2">
                    {quickPrompts.map((p, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(p)}
                        className="text-xs p-2.5 border rounded-lg bg-gray-50 hover:bg-indigo-50 hover:border-indigo-200 text-gray-700 transition-colors text-left"
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                messages.map((m) => (
                  <div
                    key={m.id}
                    className={`flex flex-col ${m.role === "USER" ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-2xl px-4 py-3 text-xs leading-relaxed ${
                        m.role === "USER"
                          ? "bg-indigo-600 text-white rounded-br-none"
                          : "bg-gray-100 text-gray-900 rounded-bl-none border"
                      }`}
                    >
                      <div className="whitespace-pre-line">{m.content}</div>

                      {/* Cited Sources */}
                      {m.role === "ASSISTANT" && m.sources && m.sources.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-gray-200 text-[10px] space-y-1 text-gray-600">
                          <span className="font-semibold text-gray-700 block">Verified Sources Cited:</span>
                          {m.sources.map((s, idx) => (
                            <div key={idx} className="flex items-center gap-1.5 bg-white px-2 py-1 rounded border text-[10px]">
                              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0" />
                              <span className="font-medium text-gray-800">{s.label}</span>
                              {s.details && <span className="text-gray-400">({s.details})</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                    <span className="text-[10px] text-gray-400 mt-1 px-1">
                      {m.role === "USER" ? "You" : m.model_used || "HireLens AI"}
                    </span>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t bg-gray-50 flex items-center gap-2">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendMessage();
                  }
                }}
                placeholder="Ask a question about candidates, jobs, or pipeline analytics..."
                className="flex-1 text-xs border rounded-lg px-3 py-2.5 bg-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
              <button
                onClick={() => handleSendMessage()}
                disabled={sendingMessage || !inputMessage.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white px-4 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                {sendingMessage ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                <span>Send</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* -------------------------------------------------------------------
          TAB 2: JOB DESCRIPTION ASSISTANT
      ------------------------------------------------------------------- */}
      {activeTab === "jd" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Controls Column */}
          <div className="lg:col-span-5 bg-white border rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex border-b pb-3 justify-between items-center">
              <span className="font-bold text-sm text-gray-900">Job Description Tools</span>
              <div className="flex gap-1 bg-gray-100 p-1 rounded-lg text-xs">
                <button
                  onClick={() => setJdMode("generate")}
                  className={`px-2.5 py-1 rounded-md font-medium ${
                    jdMode === "generate" ? "bg-white text-indigo-600 shadow-sm" : "text-gray-600"
                  }`}
                >
                  Generate
                </button>
                <button
                  onClick={() => setJdMode("improve")}
                  className={`px-2.5 py-1 rounded-md font-medium ${
                    jdMode === "improve" ? "bg-white text-indigo-600 shadow-sm" : "text-gray-600"
                  }`}
                >
                  Improve
                </button>
                <button
                  onClick={() => setJdMode("analyze")}
                  className={`px-2.5 py-1 rounded-md font-medium ${
                    jdMode === "analyze" ? "bg-white text-indigo-600 shadow-sm" : "text-gray-600"
                  }`}
                >
                  Audit Quality
                </button>
              </div>
            </div>

            {/* Mode A: Generate Inputs */}
            {jdMode === "generate" && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Target Job Title *</label>
                  <input
                    type="text"
                    value={jdTitle}
                    onChange={(e) => setJdTitle(e.target.value)}
                    placeholder="e.g. Senior Backend Engineer"
                    className="w-full border rounded-lg p-2"
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-medium text-gray-700 block mb-1">Department</label>
                    <input
                      type="text"
                      value={jdDept}
                      onChange={(e) => setJdDept(e.target.value)}
                      className="w-full border rounded-lg p-2"
                    />
                  </div>
                  <div>
                    <label className="font-medium text-gray-700 block mb-1">Seniority Level</label>
                    <select
                      value={jdLevel}
                      onChange={(e) => setJdLevel(e.target.value)}
                      className="w-full border rounded-lg p-2"
                    >
                      <option value="Junior">Junior</option>
                      <option value="Mid-Level">Mid-Level</option>
                      <option value="Senior">Senior</option>
                      <option value="Lead">Lead</option>
                      <option value="Director">Director</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="font-medium text-gray-700 block mb-1">Core Required Skills (comma-separated) *</label>
                  <input
                    type="text"
                    value={jdSkills}
                    onChange={(e) => setJdSkills(e.target.value)}
                    className="w-full border rounded-lg p-2"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="font-medium text-gray-700 block mb-1">Min. Experience (Years)</label>
                    <input
                      type="number"
                      value={jdExpMin}
                      onChange={(e) => setJdExpMin(Number(e.target.value))}
                      className="w-full border rounded-lg p-2"
                    />
                  </div>
                  <div>
                    <label className="font-medium text-gray-700 block mb-1">Work Arrangement</label>
                    <select
                      value={jdWorkMode}
                      onChange={(e) => setJdWorkMode(e.target.value)}
                      className="w-full border rounded-lg p-2"
                    >
                      <option value="ONSITE">Onsite</option>
                      <option value="HYBRID">Hybrid</option>
                      <option value="REMOTE">Remote</option>
                    </select>
                  </div>
                </div>

                <button
                  onClick={handleGenerateJd}
                  disabled={jdGenerating || !jdTitle.trim()}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2 mt-4"
                >
                  {jdGenerating && <RefreshCw className="w-4 h-4 animate-spin" />}
                  <span>Generate Structured Draft</span>
                </button>
              </div>
            )}

            {/* Mode B & C: Text Input for Improve / Audit */}
            {(jdMode === "improve" || jdMode === "analyze") && (
              <div className="space-y-3 text-xs">
                <div>
                  <label className="font-medium text-gray-700 block mb-1">Paste Job Description Text *</label>
                  <textarea
                    rows={12}
                    value={existingJdText}
                    onChange={(e) => setExistingJdText(e.target.value)}
                    placeholder="Paste job description text to detect discriminatory phrasing, clarify requirements, or audit quality..."
                    className="w-full border rounded-lg p-2.5 font-mono text-xs"
                  />
                </div>

                {jdMode === "improve" ? (
                  <button
                    onClick={handleImproveJd}
                    disabled={jdGenerating || !existingJdText.trim()}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {jdGenerating && <RefreshCw className="w-4 h-4 animate-spin" />}
                    <span>Eliminate Bias & Polish Draft</span>
                  </button>
                ) : (
                  <button
                    onClick={handleAnalyzeJd}
                    disabled={jdGenerating || !existingJdText.trim()}
                    className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white font-semibold py-2.5 rounded-lg transition-colors flex items-center justify-center gap-2"
                  >
                    {jdGenerating && <RefreshCw className="w-4 h-4 animate-spin" />}
                    <span>Run Multi-Dimension Audit</span>
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Results Column */}
          <div className="lg:col-span-7 bg-white border rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex justify-between items-center border-b pb-3">
              <span className="font-bold text-sm text-gray-900">Output & Recommendations</span>
              {generatedJd && (
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(generatedJd.full_text);
                    setCopiedJd(true);
                    setTimeout(() => setCopiedJd(false), 2000);
                  }}
                  className="flex items-center gap-1.5 text-xs text-gray-600 hover:text-indigo-600 border px-2.5 py-1 rounded"
                >
                  {copiedJd ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedJd ? "Copied" : "Copy Draft"}</span>
                </button>
              )}
            </div>

            {/* Generated Output */}
            {jdMode === "generate" && generatedJd && (
              <div className="space-y-4 text-xs">
                <div className="bg-amber-50 border border-amber-200 p-2.5 rounded text-amber-800 text-[11px]">
                  <strong>Advisory Draft:</strong> {generatedJd.disclaimer}
                </div>
                <div className="border rounded-lg p-4 bg-gray-50 whitespace-pre-line font-sans leading-relaxed text-gray-800 max-h-[500px] overflow-y-auto">
                  {generatedJd.full_text}
                </div>
              </div>
            )}

            {/* Improved Output */}
            {jdMode === "improve" && improvedJd && (
              <div className="space-y-4 text-xs">
                {improvedJd.bias_findings.length > 0 && (
                  <div className="bg-emerald-50 border border-emerald-200 p-3 rounded space-y-1">
                    <span className="font-bold text-emerald-800 block">Inclusivity Adjustments Applied:</span>
                    {improvedJd.bias_findings.map((f, i) => (
                      <div key={i} className="text-emerald-700 text-[11px] flex items-center gap-1.5">
                        <Check className="w-3 h-3 text-emerald-600" />
                        <span>{f}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="border rounded-lg p-4 bg-gray-50 whitespace-pre-line text-gray-800 max-h-[440px] overflow-y-auto">
                  {improvedJd.improved_description}
                </div>
              </div>
            )}

            {/* Quality Audit Output */}
            {jdMode === "analyze" && qualityReport && (
              <div className="space-y-4 text-xs">
                <div className="flex items-center justify-between p-3.5 bg-indigo-50 border border-indigo-200 rounded-lg">
                  <div>
                    <span className="font-bold text-indigo-900 text-sm">Overall Quality Score</span>
                    <p className="text-[11px] text-indigo-700">Objective rule-based and AI structural evaluation</p>
                  </div>
                  <div className="text-2xl font-black text-indigo-700">{qualityReport.overall_score}/100</div>
                </div>

                <div className="space-y-2">
                  {qualityReport.dimensions.map((d, i) => (
                    <div key={i} className="border rounded-lg p-3 space-y-1">
                      <div className="flex justify-between items-center">
                        <span className="font-semibold text-gray-800">{d.dimension}</span>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            d.score >= 80 ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {d.score}% • {d.status}
                        </span>
                      </div>
                      <p className="text-gray-600 text-[11px]">{d.findings[0]}</p>
                      {d.suggestions.length > 0 && (
                        <p className="text-indigo-600 text-[10px]">Tip: {d.suggestions[0]}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!generatedJd && !improvedJd && !qualityReport && (
              <div className="text-center py-16 text-gray-400 text-xs">
                Select parameters on the left to generate, improve, or audit a job description.
              </div>
            )}
          </div>
        </div>
      )}

      {/* -------------------------------------------------------------------
          TAB 3: CANDIDATE COMPARISON ASSISTANT
      ------------------------------------------------------------------- */}
      {activeTab === "compare" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white border rounded-xl p-4 shadow-sm space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">Target Job Requisition</label>
                <select
                  value={compareJobId}
                  onChange={(e) => setCompareJobId(e.target.value)}
                  className="w-full text-xs border rounded-lg p-2 bg-gray-50 text-gray-800"
                >
                  <option value="">Select a Job Requisition...</option>
                  {availableJobs.map((j) => (
                    <option key={j.id} value={j.id}>
                      {j.title} ({j.department || "General"})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold text-gray-700 block mb-1">
                  Select Candidates to Compare (2 - 6)
                </label>
                <div className="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto p-1.5 border rounded-lg bg-gray-50">
                  {availableCandidates.map((c) => {
                    const isSelected = selectedCandidateIds.includes(c.id);
                    return (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            setSelectedCandidateIds(selectedCandidateIds.filter((id) => id !== c.id));
                          } else {
                            if (selectedCandidateIds.length < 6) {
                              setSelectedCandidateIds([...selectedCandidateIds, c.id]);
                            }
                          }
                        }}
                        className={`px-2.5 py-1 rounded text-xs transition-colors ${
                          isSelected
                            ? "bg-indigo-600 text-white font-medium"
                            : "bg-white border text-gray-700 hover:bg-gray-100"
                        }`}
                      >
                        {c.full_name}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={handleCompareCandidates}
                disabled={comparing || selectedCandidateIds.length < 2 || !compareJobId}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
              >
                {comparing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <GitCompare className="w-3.5 h-3.5" />}
                <span>Run Side-by-Side Comparison</span>
              </button>
            </div>
          </div>

          {/* Comparison Matrix Output */}
          {comparisonResult && (
            <div className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b pb-3">
                <div>
                  <h3 className="font-bold text-gray-900 text-sm">
                    Comparison Matrix: {comparisonResult.job_title}
                  </h3>
                  <p className="text-xs text-gray-500">{comparisonResult.comparative_summary}</p>
                </div>
                <div className="bg-blue-50 border border-blue-200 text-blue-800 text-[10px] px-2.5 py-1 rounded">
                  Deterministic Scores Preserved
                </div>
              </div>

              {/* Side-by-side Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {comparisonResult.candidates.map((cand) => (
                  <div key={cand.candidate_id} className="border rounded-xl p-4 bg-gray-50 space-y-3 text-xs">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-gray-900 text-sm">{cand.candidate_name}</h4>
                        <span className="text-gray-500">{cand.current_title || "Candidate"}</span>
                      </div>
                      {cand.deterministic_match_score !== null && (
                        <div className="bg-indigo-100 text-indigo-800 font-extrabold px-2 py-0.5 rounded text-xs">
                          {cand.deterministic_match_score}% Match
                        </div>
                      )}
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-gray-400">Experience</span>
                      <p className="text-gray-800">
                        {Math.floor(cand.total_experience_months / 12)} yrs {cand.total_experience_months % 12} mos
                      </p>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-gray-400">Verified Strengths</span>
                      <div className="flex flex-wrap gap-1">
                        {cand.key_strengths.map((s, idx) => (
                          <span key={idx} className="bg-emerald-100 text-emerald-800 px-1.5 py-0.5 rounded text-[10px]">
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <span className="text-[10px] uppercase font-bold text-gray-400">Missing / Unverified Skills</span>
                      <div className="flex flex-wrap gap-1">
                        {cand.missing_or_partial_skills.length > 0 ? (
                          cand.missing_or_partial_skills.map((s, idx) => (
                            <span key={idx} className="bg-amber-100 text-amber-800 px-1.5 py-0.5 rounded text-[10px]">
                              {s}
                            </span>
                          ))
                        ) : (
                          <span className="text-gray-400 text-[10px]">None flagged</span>
                        )}
                      </div>
                    </div>

                    <div className="space-y-1 pt-2 border-t text-[11px]">
                      <span className="font-semibold text-gray-700">Interview Probe:</span>
                      <p className="text-gray-600">{cand.areas_for_verification[0] || "Confirm technical depth"}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* -------------------------------------------------------------------
          TAB 4: INTERVIEW PREPARATION BRIEFS
      ------------------------------------------------------------------- */}
      {activeTab === "prep" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white border rounded-xl p-4 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="w-full sm:w-2/3">
              <label className="text-xs font-semibold text-gray-700 block mb-1">Select Scheduled Interview</label>
              <select
                value={prepInterviewId}
                onChange={(e) => setPrepInterviewId(e.target.value)}
                className="w-full text-xs border rounded-lg p-2 bg-gray-50 text-gray-800"
              >
                <option value="">Select an Interview...</option>
                {availableInterviews.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.title} ({i.round_name}) - {new Date(i.scheduled_start).toLocaleDateString()}
                  </option>
                ))}
              </select>
            </div>
            <button
              onClick={handlePrepareInterview}
              disabled={prepping || !prepInterviewId}
              className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white text-xs font-semibold px-4 py-2.5 rounded-lg flex items-center justify-center gap-1.5 transition-colors self-end"
            >
              {prepping ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Calendar className="w-3.5 h-3.5" />}
              <span>Generate Interview Brief</span>
            </button>
          </div>

          {/* Prep Brief Display */}
          {prepBrief && (
            <div className="bg-white border rounded-xl p-6 shadow-sm space-y-6 text-xs">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b pb-4 gap-2">
                <div>
                  <h3 className="font-bold text-gray-900 text-base">
                    Interview Brief: {prepBrief.candidate_name}
                  </h3>
                  <p className="text-gray-500">
                    Role: {prepBrief.job_title} • Round: {prepBrief.round_name} ({prepBrief.round_type})
                  </p>
                </div>
                <div className="bg-indigo-50 text-indigo-700 px-3 py-1 rounded font-semibold text-xs">
                  {prepBrief.scheduled_time}
                </div>
              </div>

              {/* Candidate Experience Summary */}
              <div className="bg-gray-50 border rounded-lg p-4 space-y-1">
                <span className="font-bold text-gray-800">Verified Profile Summary</span>
                <p className="text-gray-700 leading-relaxed">{prepBrief.candidate_experience_summary}</p>
              </div>

              {/* Suggested Questions */}
              <div className="space-y-3">
                <h4 className="font-bold text-gray-900 text-sm">Targeted Competency Questions</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {prepBrief.questions.map((q, idx) => (
                    <div key={idx} className="border rounded-lg p-3.5 bg-white space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                          {q.category}
                        </span>
                        <span className="text-gray-500 text-[10px]">{q.target_skill_or_competency}</span>
                      </div>
                      <p className="font-semibold text-gray-900 leading-snug">{q.question}</p>
                      <div className="bg-gray-50 p-2 rounded text-[11px] text-gray-600">
                        <span className="font-semibold text-gray-700">What to look for:</span> {q.what_to_look_for}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Agenda & Evaluation Guidance */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="border rounded-lg p-4 bg-gray-50 space-y-2">
                  <span className="font-bold text-gray-800 block">Suggested Round Agenda</span>
                  <ul className="space-y-1 text-gray-600">
                    {prepBrief.suggested_structure.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <ChevronRight className="w-3.5 h-3.5 text-indigo-500 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="border rounded-lg p-4 bg-amber-50 border-amber-200 space-y-2">
                  <span className="font-bold text-amber-900 block">Objective Evaluation Guidance</span>
                  <ul className="space-y-1 text-amber-800">
                    {prepBrief.evaluation_guidance.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* -------------------------------------------------------------------
          TAB 5: RECRUITMENT ANALYTICS INTELLIGENCE
      ------------------------------------------------------------------- */}
      {activeTab === "analytics" && (
        <div className="space-y-6">
          <div className="flex justify-between items-center bg-white border rounded-xl p-4 shadow-sm">
            <div>
              <h3 className="font-bold text-sm text-gray-900">Phase 8 Recruitment Analytics Insights</h3>
              <p className="text-xs text-gray-500">
                Natural-language explanations grounded strictly in deterministic backend analytics calculations.
              </p>
            </div>
            <button
              onClick={handleExplainAnalytics}
              disabled={analyticsExplaining}
              className="bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white text-xs font-semibold px-4 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              {analyticsExplaining ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
              <span>Refresh Insights</span>
            </button>
          </div>

          {analyticsResult && (
            <div className="bg-white border rounded-xl p-6 shadow-sm space-y-6 text-xs">
              {/* Executive Summary */}
              <div className="p-4 bg-indigo-50 border border-indigo-200 rounded-lg space-y-1.5">
                <span className="font-bold text-indigo-900 text-sm">Recruitment Performance Executive Summary</span>
                <p className="text-indigo-800 text-xs leading-relaxed">{analyticsResult.summary}</p>
              </div>

              {/* Verified Metrics Snapshot */}
              <div>
                <span className="text-[11px] font-bold text-gray-400 uppercase tracking-wider block mb-2">
                  Verified Software Calculations
                </span>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="border rounded-lg p-3 bg-gray-50">
                    <span className="text-gray-500 text-[10px] block">Applications</span>
                    <span className="text-xl font-bold text-gray-900">
                      {analyticsResult.verified_metrics_snapshot.applications}
                    </span>
                  </div>
                  <div className="border rounded-lg p-3 bg-gray-50">
                    <span className="text-gray-500 text-[10px] block">Interviews</span>
                    <span className="text-xl font-bold text-gray-900">
                      {analyticsResult.verified_metrics_snapshot.interviews}
                    </span>
                  </div>
                  <div className="border rounded-lg p-3 bg-gray-50">
                    <span className="text-gray-500 text-[10px] block">Hires</span>
                    <span className="text-xl font-bold text-gray-900">
                      {analyticsResult.verified_metrics_snapshot.hires}
                    </span>
                  </div>
                  <div className="border rounded-lg p-3 bg-gray-50">
                    <span className="text-gray-500 text-[10px] block">Conversion Rate</span>
                    <span className="text-xl font-bold text-indigo-600">
                      {analyticsResult.verified_metrics_snapshot.overall_conversion_pct}%
                    </span>
                  </div>
                </div>
              </div>

              {/* Insights Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="border rounded-lg p-4 space-y-2 bg-gray-50">
                  <span className="font-bold text-gray-800 block">Funnel & Bottlenecks</span>
                  <ul className="space-y-1.5 text-gray-600 text-[11px]">
                    {analyticsResult.funnel_insights.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-1">
                        <ChevronRight className="w-3 h-3 text-indigo-500 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="border rounded-lg p-4 space-y-2 bg-gray-50">
                  <span className="font-bold text-gray-800 block">Time-to-Hire Dynamics</span>
                  <ul className="space-y-1.5 text-gray-600 text-[11px]">
                    {analyticsResult.time_to_hire_insights.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-1">
                        <ChevronRight className="w-3 h-3 text-indigo-500 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="border rounded-lg p-4 space-y-2 bg-gray-50">
                  <span className="font-bold text-gray-800 block">Operational Action Items</span>
                  <ul className="space-y-1.5 text-gray-600 text-[11px]">
                    {analyticsResult.operational_recommendations.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-1">
                        <Check className="w-3 h-3 text-emerald-600 flex-shrink-0 mt-0.5" />
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

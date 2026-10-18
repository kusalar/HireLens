"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  ArrowLeft,
  Download,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileSearch,
  UserCheck,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Shield,
  Layers,
} from "lucide-react";
import { apiClient, buildApiUrl } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { ResumeDetailResponse, ResumeProcessingStatus } from "@/types";

export default function ResumeDetailPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [data, setData] = useState<ResumeDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [showExtractedText, setShowExtractedText] = useState(false);

  useEffect(() => {
    async function loadResume() {
      try {
        const res: ResumeDetailResponse = await apiClient(`/resumes/${id}`);
        setData(res);
      } catch (err) {
        console.error("Failed to load resume details:", err);
      } finally {
        setLoading(false);
      }
    }
    loadResume();
  }, [id]);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await apiClient(`/resumes/${id}/retry`, { method: "POST" });
      const refetched: ResumeDetailResponse = await apiClient(`/resumes/${id}`);
      setData(refetched);
      alert("Processing pipeline retried successfully.");
    } catch (err: any) {
      alert(`Retry failed: ${err.message}`);
    } finally {
      setRetrying(false);
    }
  };

  const handleDownload = async () => {
    if (!data) return;
    try {
      const token = localStorage.getItem("hirelens_access_token");
      const url = buildApiUrl(`/resumes/${id}/download`);
      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = data.resume.original_filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      alert(`Could not download file: ${err.message}`);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
        <p className="mt-3 text-sm text-slate-500 font-medium">Loading resume details...</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-800">Resume Not Found</h2>
        <p className="text-sm text-slate-500 mt-1">
          This document does not exist or you do not have permission to view it.
        </p>
        <Link
          href="/resumes"
          className="mt-4 inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
        >
          Back to Resumes
        </Link>
      </div>
    );
  }

  const { resume, current_profile, parse_runs, evidences } = data;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return "N/A";
    return formatDateTime(isoString);
  };

  const getStatusBadge = (status: ResumeProcessingStatus) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
            Completed
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
            <Sparkles className="w-3.5 h-3.5 mr-1 text-amber-500" />
            Review Required
          </span>
        );
      case "EXTRACTED":
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
            <FileSearch className="w-3.5 h-3.5 mr-1 text-blue-500" />
            Text Extracted
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3.5 h-3.5 mr-1 text-rose-500" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <Clock className="w-3.5 h-3.5 mr-1 text-slate-500" />
            {status}
          </span>
        );
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href="/resumes"
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                {resume.original_filename}
              </h1>
              {getStatusBadge(resume.processing_status)}
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              SHA-256: {resume.sha256_hash}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleDownload}
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <Download className="w-4 h-4 mr-1.5" />
            Download Original
          </button>

          {(resume.processing_status === "FAILED" ||
            resume.processing_status === "EXTRACTED" ||
            resume.processing_status === "QUEUED") && (
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="inline-flex items-center px-3 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
            >
              <RefreshCw className={`w-4 h-4 mr-1.5 ${retrying ? "animate-spin" : ""}`} />
              Retry Processing
            </button>
          )}

          <Link
            href={`/resumes/${id}/review`}
            className="inline-flex items-center px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Review & Confirm Profile
          </Link>
        </div>
      </div>

      {/* Overview Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs text-slate-400 font-medium block">File Type & Size</span>
          <p className="text-base font-semibold text-slate-900 mt-0.5">
            {resume.mime_type.includes("pdf") ? "PDF Document" : "Word Document (.docx)"}
          </p>
          <span className="text-xs text-slate-500">
            {formatFileSize(resume.file_size)} • {resume.page_count || 1} Page(s)
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs text-slate-400 font-medium block">Candidate Status</span>
          <p className="text-base font-semibold text-slate-900 mt-0.5">
            {resume.candidate_name || "Unassigned"}
          </p>
          <span className="text-xs text-slate-500">
            {resume.candidate_id ? "Associated with profile" : "Awaiting recruiter confirmation"}
          </span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs text-slate-400 font-medium block">Uploaded At</span>
          <p className="text-sm font-semibold text-slate-900 mt-1">
            {formatDate(resume.created_at)}
          </p>
          <span className="text-xs text-slate-500">Tenant-isolated storage</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
          <span className="text-xs text-slate-400 font-medium block">AI Extraction Confidence</span>
          <p className="text-base font-semibold text-slate-900 mt-0.5">
            {current_profile?.overall_confidence
              ? `${Math.round(current_profile.overall_confidence * 100)}%`
              : "Pending"}
          </p>
          <span className="text-xs text-slate-500">
            {evidences.length} verifiable fact evidence point(s)
          </span>
        </div>
      </div>

      {/* Extracted Profile Highlights */}
      {current_profile && (
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs p-6 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-100 pb-3">
            <h2 className="text-base font-semibold text-slate-900 flex items-center">
              <Sparkles className="w-4 h-4 mr-2 text-blue-600" />
              Extracted Profile Summary
            </h2>
            <Link
              href={`/resumes/${id}/review`}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center"
            >
              Open Full Review Editor <ExternalLink className="w-3 h-3 ml-1" />
            </Link>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <span className="text-xs text-slate-400 font-medium block">Extracted Name</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_name || "Not found in document"}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 font-medium block">Email Address</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_email || "Not found in document"}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 font-medium block">Phone</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_phone || "Not found in document"}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 font-medium block">Current Job Title</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_current_title || "Not found"}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 font-medium block">Location</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_location || "Not found"}
              </p>
            </div>
            <div>
              <span className="text-xs text-slate-400 font-medium block">Total Experience</span>
              <p className="text-sm font-semibold text-slate-800 mt-0.5">
                {current_profile.extracted_experience_months
                  ? `${Math.floor(current_profile.extracted_experience_months / 12)} yrs ${
                      current_profile.extracted_experience_months % 12
                    } mos`
                  : "Not specified"}
              </p>
            </div>
          </div>

          {current_profile.extracted_summary && (
            <div className="pt-2">
              <span className="text-xs text-slate-400 font-medium block">Professional Summary</span>
              <p className="text-sm text-slate-700 mt-1 leading-relaxed bg-slate-50 p-3 rounded-lg border border-slate-100">
                {current_profile.extracted_summary}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Parsing Runs History */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50/70">
          <h2 className="text-sm font-semibold text-slate-900 flex items-center">
            <Layers className="w-4 h-4 mr-2 text-slate-600" />
            Parsing Runs & Model Audit History ({parse_runs.length})
          </h2>
        </div>

        {parse_runs.length === 0 ? (
          <div className="p-6 text-center text-sm text-slate-400">
            No parse runs have been recorded for this resume yet.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50 text-slate-500 uppercase font-semibold">
                  <th className="py-2.5 px-4">Provider / Model</th>
                  <th className="py-2.5 px-4">Method</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Duration</th>
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4">Error Diagnostics</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {parse_runs.map((run) => (
                  <tr key={run.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-medium">
                      <span className="text-slate-900 font-semibold">{run.provider}</span> /{" "}
                      <span className="text-slate-600">{run.model_name}</span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500">
                      {run.extraction_method}
                    </td>
                    <td className="py-3 px-4">
                      {run.status === "COMPLETED" ? (
                        <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded font-semibold border border-emerald-200">
                          COMPLETED
                        </span>
                      ) : run.status === "FAILED" ? (
                        <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded font-semibold border border-rose-200">
                          FAILED
                        </span>
                      ) : (
                        <span className="text-blue-700 bg-blue-50 px-2 py-0.5 rounded font-semibold border border-blue-200">
                          {run.status}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-500">
                      {run.processing_duration_ms ? `${run.processing_duration_ms} ms` : "-"}
                    </td>
                    <td className="py-3 px-4 text-slate-500">{formatDate(run.started_at)}</td>
                    <td className="py-3 px-4 text-rose-600 max-w-xs truncate">
                      {run.error_message || "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

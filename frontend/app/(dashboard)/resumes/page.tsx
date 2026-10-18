"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  FileText,
  Upload,
  Search,
  Filter,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileSearch,
  Download,
  Trash2,
  ExternalLink,
  RefreshCw,
  Sparkles,
  Layers,
  UserCheck,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";
import { Resume, ResumeProcessingStatus } from "@/types";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchResumes = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.append("page", page.toString());
      params.append("page_size", pageSize.toString());
      if (search.trim()) params.append("search", search.trim());
      if (statusFilter) params.append("status", statusFilter);

      const res: any = await apiClient(`/resumes?${params.toString()}`);
      setResumes(res.items || []);
      setTotal(res.total || 0);
    } catch (err) {
      console.error("Failed to fetch resumes:", err);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter]);

  useEffect(() => {
    fetchResumes();
  }, [fetchResumes]);

  const handleDelete = async (resumeId: string, filename: string) => {
    if (!confirm(`Are you sure you want to permanently delete '${filename}'? This cannot be undone.`)) {
      return;
    }
    setDeletingId(resumeId);
    try {
      await apiClient(`/resumes/${resumeId}`, { method: "DELETE" });
      setResumes((prev) => prev.filter((r) => r.id !== resumeId));
      setTotal((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      alert(`Failed to delete resume: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = async (resumeId: string, filename: string) => {
    try {
      const token = localStorage.getItem("hirelens_access_token");
      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/resumes/${resumeId}/download`;
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
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err: any) {
      alert(`Could not download file: ${err.message}`);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (isoString: string) => {
    return formatDateTime(isoString);
  };

  const getStatusBadge = (status: ResumeProcessingStatus) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 mr-1 text-emerald-600" />
            Completed
          </span>
        );
      case "REVIEW_REQUIRED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
            <Sparkles className="w-3 h-3 mr-1 text-amber-500" />
            Review Required
          </span>
        );
      case "EXTRACTED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
            <FileSearch className="w-3 h-3 mr-1 text-blue-500" />
            Extracted
          </span>
        );
      case "PARSING":
      case "EXTRACTING":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
            <RefreshCw className="w-3 h-3 mr-1 text-indigo-500 animate-spin" />
            {status === "PARSING" ? "AI Parsing..." : "Extracting Text..."}
          </span>
        );
      case "QUEUED":
      case "UPLOADED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
            <Clock className="w-3 h-3 mr-1 text-slate-500" />
            Queued
          </span>
        );
      case "FAILED":
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-3 h-3 mr-1 text-rose-500" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">
            {status}
          </span>
        );
    }
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-blue-50 rounded-lg border border-blue-100 text-blue-600">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                Resume Intelligence Hub
              </h1>
              <p className="text-sm text-slate-500">
                Upload, extract, and review candidate documents with AI-assisted parsing.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <Link
            href="/resumes/upload"
            className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload Resumes
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <div className="relative w-full md:w-80">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by filename..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-colors"
          />
        </div>

        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="text-sm rounded-lg border border-slate-200 py-2 px-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 bg-white text-slate-700 font-medium"
            >
              <option value="">All Statuses</option>
              <option value="REVIEW_REQUIRED">Review Required</option>
              <option value="EXTRACTED">Extracted</option>
              <option value="COMPLETED">Completed</option>
              <option value="QUEUED">Queued</option>
              <option value="PARSING">AI Parsing</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          <button
            onClick={() => fetchResumes()}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      {/* Table Section */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        {loading && resumes.length === 0 ? (
          <div className="py-20 text-center">
            <div className="inline-block w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
            <p className="mt-2 text-sm text-slate-500">Loading resumes...</p>
          </div>
        ) : resumes.length === 0 ? (
          <div className="py-16 text-center">
            <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center mx-auto text-slate-400 mb-3">
              <FileText className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-800">No resumes found</h3>
            <p className="text-sm text-slate-500 max-w-sm mx-auto mt-1">
              {search || statusFilter
                ? "No uploaded resumes match the selected search filters."
                : "Your agency workspace has no uploaded resumes yet. Upload resumes to get started."}
            </p>
            <div className="mt-5">
              <Link
                href="/resumes/upload"
                className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm"
              >
                <Upload className="w-4 h-4 mr-2" />
                Upload Your First Resume
              </Link>
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-slate-200/80 bg-slate-50/70 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  <th className="py-3 px-6">Document</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6">Candidate Association</th>
                  <th className="py-3 px-6">Size / Pages</th>
                  <th className="py-3 px-6">Uploaded</th>
                  <th className="py-3 px-6 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-sm text-slate-700">
                {resumes.map((resume) => {
                  const isPdf = resume.mime_type.includes("pdf");
                  return (
                    <tr key={resume.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-6">
                        <div className="flex items-center space-x-3">
                          <div
                            className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                              isPdf ? "bg-rose-50 text-rose-600" : "bg-blue-50 text-blue-600"
                            }`}
                          >
                            <FileText className="w-4 h-4" />
                          </div>
                          <div className="min-w-0 max-w-xs">
                            <Link
                              href={`/resumes/${resume.id}`}
                              className="font-medium text-slate-900 hover:text-blue-600 truncate block"
                              title={resume.original_filename}
                            >
                              {resume.original_filename}
                            </Link>
                            <span className="text-xs text-slate-400 font-mono">
                              {resume.sha256_hash.substring(0, 10)}...
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3.5 px-6">{getStatusBadge(resume.processing_status)}</td>
                      <td className="py-3.5 px-6">
                        {resume.candidate_name ? (
                          <div className="flex items-center space-x-1.5 text-slate-900 font-medium">
                            <UserCheck className="w-3.5 h-3.5 text-emerald-600" />
                            <span>{resume.candidate_name}</span>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Unassigned</span>
                        )}
                      </td>
                      <td className="py-3.5 px-6 text-xs text-slate-500">
                        <div>{formatFileSize(resume.file_size)}</div>
                        {resume.page_count ? (
                          <div className="text-slate-400">{resume.page_count} page(s)</div>
                        ) : null}
                      </td>
                      <td className="py-3.5 px-6 text-xs text-slate-500">
                        {formatDate(resume.created_at)}
                      </td>
                      <td className="py-3.5 px-6 text-right space-x-2">
                        {resume.processing_status === "REVIEW_REQUIRED" ||
                        resume.processing_status === "EXTRACTED" ? (
                          <Link
                            href={`/resumes/${resume.id}/review`}
                            className="inline-flex items-center px-2.5 py-1 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 rounded border border-amber-200 transition-colors"
                          >
                            <Sparkles className="w-3 h-3 mr-1" />
                            Review
                          </Link>
                        ) : (
                          <Link
                            href={`/resumes/${resume.id}`}
                            className="inline-flex items-center px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 rounded transition-colors"
                          >
                            Details
                          </Link>
                        )}

                        <button
                          onClick={() => handleDownload(resume.id, resume.original_filename)}
                          className="p-1 text-slate-400 hover:text-slate-700 rounded hover:bg-slate-100 transition-colors"
                          title="Download original file"
                        >
                          <Download className="w-4 h-4" />
                        </button>

                        <button
                          onClick={() => handleDelete(resume.id, resume.original_filename)}
                          disabled={deletingId === resume.id}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition-colors"
                          title="Delete resume"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > pageSize && (
          <div className="px-6 py-3 border-t border-slate-200 bg-slate-50/50 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {(page - 1) * pageSize + 1} to {Math.min(page * pageSize, total)} of {total} resumes
            </span>
            <div className="flex items-center space-x-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="p-1.5 rounded border border-slate-200 bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="font-semibold text-slate-700">
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="p-1.5 rounded border border-slate-200 bg-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 transition-colors"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

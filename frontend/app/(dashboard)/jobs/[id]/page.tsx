"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Briefcase,
  MapPin,
  Clock,
  Edit3,
  Archive,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Kanban,
  GitCompare,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Job, JobRequirement } from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchJob = async () => {
    setLoading(true);
    try {
      const data: Job = await apiClient(`/jobs/${jobId}`);
      setJob(data);
    } catch (err: any) {
      setError(err.message || "Failed to load job details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchJob();
    }
  }, [jobId]);

  const handleArchive = async () => {
    if (!confirm("Are you sure you want to archive this job opening?")) return;
    try {
      const updated: Job = await apiClient(`/jobs/${jobId}/archive`, {
        method: "POST",
      });
      setJob(updated);
      setActionMessage("Job successfully archived.");
    } catch (err: any) {
      setError(err.message || "Failed to archive job.");
    }
  };

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center text-slate-500 space-y-2">
        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm">Loading job specifications...</span>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="max-w-2xl p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <p className="font-semibold">{error || "Job not found."}</p>
        <Link href="/jobs" className="mt-3 inline-block text-xs font-bold text-red-800 underline">
          Return to jobs listing
        </Link>
      </div>
    );
  }

  const mandatoryReqs = job.requirements?.filter((r) => r.is_mandatory) || [];
  const preferredReqs = job.requirements?.filter((r) => !r.is_mandatory) || [];

  return (
    <div className="max-w-5xl space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/jobs"
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Jobs</span>
        </Link>
      </div>

      {actionMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-medium">
          {actionMessage}
        </div>
      )}

      {/* Hero Header */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center space-x-2.5">
            <span
              className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                job.status === "ACTIVE"
                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                  : job.status === "ARCHIVED"
                  ? "bg-amber-50 text-amber-700 border-amber-200"
                  : "bg-slate-100 text-slate-700 border-slate-200"
              }`}
            >
              {job.status}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              Job ID: {job.id.slice(0, 8)}...
            </span>
          </div>

          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{job.title}</h1>

          <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-500 pt-1">
            {job.department && (
              <span className="font-medium text-slate-700">{job.department}</span>
            )}
            {job.location && (
              <span className="flex items-center">
                <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {job.location} ({job.work_mode})
              </span>
            )}
            <span className="flex items-center">
              <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
              {job.minimum_experience}
              {job.maximum_experience ? ` - ${job.maximum_experience}` : "+"} yrs exp
            </span>
            <span>Type: {job.employment_type.replace("_", " ")}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Link
            href={`/jobs/${job.id}/pipeline`}
            className="inline-flex items-center space-x-1.5 px-4 py-2 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg shadow-sm transition-colors"
          >
            <Kanban className="w-3.5 h-3.5" />
            <span>Recruitment Pipeline</span>
          </Link>

          <Link
            href={`/jobs/${job.id}/matches`}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Matches</span>
          </Link>

          <Link
            href={`/jobs/${job.id}/compare`}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <GitCompare className="w-3.5 h-3.5" />
            <span>Compare</span>
          </Link>

          <Link
            href={`/jobs/${job.id}/edit`}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit</span>
          </Link>


          {job.status !== "ARCHIVED" && (
            <button
              onClick={handleArchive}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-amber-700 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-lg transition-colors"
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Archive</span>
            </button>
          )}
        </div>
      </div>

      {/* Grid: Details & Requirements */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Description & Responsibilities */}
        <div className="lg:col-span-2 space-y-6">
          {job.description && (
            <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-2">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Position Overview
              </h2>
              <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">
                {job.description}
              </p>
            </div>
          )}

          {job.responsibilities && (
            <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-2">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Responsibilities & Deliverables
              </h2>
              <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">
                {job.responsibilities}
              </p>
            </div>
          )}

          {/* Structured Requirements List */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
                  <Layers className="w-4 h-4 mr-2 text-blue-600" />
                  Screening Requirements ({job.requirements?.length || 0})
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Used by the deterministic matching engine in Phase 4.
                </p>
              </div>
            </div>

            {/* Mandatory Criteria */}
            <div>
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block mb-2.5">
                Mandatory Criteria ({mandatoryReqs.length})
              </span>
              {mandatoryReqs.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No mandatory criteria defined.</p>
              ) : (
                <div className="space-y-2">
                  {mandatoryReqs.map((req) => (
                    <div
                      key={req.id}
                      className="p-3 bg-slate-50/70 border border-slate-200/80 rounded-lg flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <p className="font-medium text-slate-900">{req.requirement_text}</p>
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 bg-blue-100/60 text-blue-800 rounded">
                            {req.requirement_type}
                          </span>
                          {req.normalized_skill && (
                            <span className="text-[10px] font-mono text-slate-600 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                              {req.normalized_skill}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="shrink-0 text-[11px] font-bold text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded">
                        Weight: {req.importance_weight}x
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Preferred Criteria */}
            <div className="pt-2">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block mb-2.5">
                Preferred Criteria ({preferredReqs.length})
              </span>
              {preferredReqs.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No preferred criteria defined.</p>
              ) : (
                <div className="space-y-2">
                  {preferredReqs.map((req) => (
                    <div
                      key={req.id}
                      className="p-3 bg-slate-50/70 border border-slate-200/80 rounded-lg flex items-start justify-between gap-3 text-xs"
                    >
                      <div className="space-y-1">
                        <p className="font-medium text-slate-900">{req.requirement_text}</p>
                        <div className="flex items-center space-x-2">
                          <span className="text-[10px] font-semibold uppercase px-1.5 py-0.5 bg-slate-200 text-slate-700 rounded">
                            {req.requirement_type}
                          </span>
                          {req.normalized_skill && (
                            <span className="text-[10px] font-mono text-slate-600 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                              {req.normalized_skill}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="shrink-0 text-[11px] font-bold text-slate-500 bg-white border border-slate-200 px-2 py-0.5 rounded">
                        Weight: {req.importance_weight}x
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Meta & AI Matching Teaser */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3.5 text-xs">
            <h3 className="font-bold text-slate-900 uppercase tracking-wider">Position Metadata</h3>
            <div className="space-y-2 text-slate-600">
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Created:</span>
                <span className="font-medium text-slate-800">{formatDateTime(job.created_at)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Work Mode:</span>
                <span className="font-medium text-slate-800">{job.work_mode}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-100">
                <span className="text-slate-400">Experience:</span>
                <span className="font-medium text-slate-800">
                  {job.minimum_experience}{job.maximum_experience ? ` - ${job.maximum_experience}` : "+"} Years
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Tenant Scoped:</span>
                <span className="font-medium text-emerald-700 flex items-center">
                  <ShieldCheck className="w-3.5 h-3.5 mr-1" />
                  Protected
                </span>
              </div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-slate-900 to-slate-800 text-white rounded-xl p-5 shadow-xs space-y-3">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-4 h-4 text-blue-400" />
              <h3 className="font-bold text-sm">Matching Engine</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Match candidate resumes against this position using open-weight embeddings and deterministic scoring.
            </p>
            <div className="pt-1">
              <Link
                href="/matching"
                className="w-full inline-flex items-center justify-center space-x-1.5 py-2 px-3 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-lg shadow transition-colors"
              >
                <span>Run AI Matcher (Phase 4)</span>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

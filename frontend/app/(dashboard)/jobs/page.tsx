"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Briefcase,
  Plus,
  Search,
  Filter,
  MapPin,
  Clock,
  Layers,
  ChevronRight,
  Sparkles,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Job, WorkMode, JobStatus } from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [workModeFilter, setWorkModeFilter] = useState<string>("");

  const fetchJobs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (statusFilter) params.append("status", statusFilter);
      if (workModeFilter) params.append("work_mode", workModeFilter);

      const queryString = params.toString() ? `?${params.toString()}` : "";
      const data: Job[] = await apiClient(`/jobs${queryString}`);
      setJobs(data);
    } catch (err: any) {
      setError(err.message || "Failed to load jobs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, [statusFilter, workModeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Active Jobs & Openings</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Manage your agency positions, requirements, and hiring criteria.
          </p>
        </div>
        <Link
          href="/jobs/new"
          className="inline-flex items-center space-x-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg shadow-xs transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Create New Job</span>
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs flex flex-col md:flex-row gap-3 items-center justify-between">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by job title, department, or location..."
            className="w-full pl-9 pr-4 py-2 text-sm bg-slate-50/50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white text-slate-900"
          />
        </form>

        <div className="flex items-center space-x-3 w-full md:w-auto">
          <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All Statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="DRAFT">Draft</option>
            <option value="PAUSED">Paused</option>
            <option value="ARCHIVED">Archived</option>
            <option value="CLOSED">Closed</option>
          </select>

          <select
            value={workModeFilter}
            onChange={(e) => setWorkModeFilter(e.target.value)}
            className="text-xs py-2 px-3 bg-white border border-slate-200 rounded-lg text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            <option value="">All Work Modes</option>
            <option value="ONSITE">Onsite</option>
            <option value="HYBRID">Hybrid</option>
            <option value="REMOTE">Remote</option>
          </select>
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center text-slate-500 space-y-3">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm font-medium">Loading agency job openings...</span>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      ) : jobs.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center flex flex-col items-center">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mb-4">
            <Briefcase className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">No job openings found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm">
            {search || statusFilter || workModeFilter
              ? "No positions match your selected filter criteria. Try resetting filters."
              : "Create your first job position to define requirements and begin AI-assisted candidate matching."}
          </p>
          <div className="mt-6">
            <Link
              href="/jobs/new"
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Create First Job</span>
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5">
          {jobs.map((job) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="group bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-400/80 hover:shadow-sm transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 min-w-0">
                <div className="flex items-center space-x-2.5">
                  <h3 className="text-base font-semibold text-slate-900 group-hover:text-blue-600 transition-colors truncate">
                    {job.title}
                  </h3>
                  <span
                    className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${
                      job.status === "ACTIVE"
                        ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                        : job.status === "DRAFT"
                        ? "bg-slate-100 text-slate-700 border-slate-200"
                        : job.status === "ARCHIVED"
                        ? "bg-amber-50 text-amber-700 border-amber-200"
                        : "bg-slate-100 text-slate-600 border-slate-200"
                    }`}
                  >
                    {job.status}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-y-1 gap-x-4 text-xs text-slate-500">
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
                  <span className="flex items-center">
                    <Layers className="w-3.5 h-3.5 mr-1 text-slate-400" />
                    {job.requirements_count ?? 0} Requirements
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-3 shrink-0">
                <span className="text-xs text-slate-400">
                  Created {formatDateTime(job.created_at)}
                </span>
                <div className="h-8 w-8 rounded-full bg-slate-50 group-hover:bg-blue-50 group-hover:text-blue-600 flex items-center justify-center text-slate-400 transition-colors">
                  <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

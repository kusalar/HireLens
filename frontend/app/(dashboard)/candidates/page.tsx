"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Users,
  Plus,
  Search,
  Filter,
  MapPin,
  Clock,
  Tag,
  ChevronRight,
  ShieldCheck,
  UserCheck,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Candidate, CandidateProfileStatus } from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function CandidatesDirectoryPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState("");
  const [skillFilter, setSkillFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  const fetchCandidates = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (skillFilter) params.append("skill", skillFilter);
      if (locationFilter) params.append("location", locationFilter);
      if (statusFilter) params.append("status", statusFilter);

      const queryString = params.toString() ? `?${params.toString()}` : "";
      const data: Candidate[] = await apiClient(`/candidates${queryString}`);
      setCandidates(data);
    } catch (err: any) {
      setError(err.message || "Failed to load candidates.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCandidates();
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchCandidates();
  };

  return (
    <div className="space-y-6 max-w-7xl">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Candidate Pool & Directory</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Search, filter, and track talent profiles across your recruitment pipeline.
          </p>
        </div>
        <Link
          href="/candidates/new"
          className="inline-flex items-center space-x-2 px-4 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg shadow-xs transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Add Candidate</span>
        </Link>
      </div>

      {/* Filter Bar */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-4 shadow-xs space-y-3">
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="relative md:col-span-2">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, job title, summary..."
              className="w-full pl-9 pr-4 py-2 text-xs bg-slate-50/50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white text-slate-900"
            />
          </div>

          <div className="relative">
            <Tag className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              placeholder="Filter by skill (e.g. React)..."
              className="w-full pl-8 pr-3 py-2 text-xs bg-slate-50/50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white text-slate-900"
            />
          </div>

          <div className="flex items-center space-x-2">
            <input
              type="text"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              placeholder="City (e.g. Pune)..."
              className="w-full px-3 py-2 text-xs bg-slate-50/50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white text-slate-900"
            />
            <button
              type="submit"
              className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors shrink-0"
            >
              Search
            </button>
          </div>
        </form>

        <div className="flex items-center space-x-3 pt-1 text-xs">
          <span className="text-slate-400 font-medium">Status:</span>
          <div className="flex flex-wrap gap-1.5">
            {["", "ACTIVE", "PLACED", "INACTIVE", "ARCHIVED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition-colors ${
                  statusFilter === st
                    ? "bg-slate-900 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st === "" ? "All Profiles" : st}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Directory Content */}
      {loading ? (
        <div className="py-16 flex flex-col items-center justify-center text-slate-500 space-y-2">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="text-sm">Loading candidates...</span>
        </div>
      ) : error ? (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      ) : candidates.length === 0 ? (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center flex flex-col items-center">
          <div className="h-12 w-12 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 mb-4">
            <Users className="w-6 h-6" />
          </div>
          <h3 className="text-base font-semibold text-slate-900">No candidates found</h3>
          <p className="text-sm text-slate-500 mt-1 max-w-sm">
            {search || skillFilter || locationFilter || statusFilter
              ? "No candidate profiles match your filter parameters."
              : "Start by registering candidate profiles manually or upload resumes via the parsing engine."}
          </p>
          <div className="mt-6">
            <Link
              href="/candidates/new"
              className="inline-flex items-center space-x-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add First Candidate</span>
            </Link>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3.5">
          {candidates.map((candidate) => {
            const expYears = Math.floor(candidate.total_experience_months / 12);
            const expMonths = candidate.total_experience_months % 12;
            const expLabel =
              expYears > 0
                ? `${expYears} yr${expYears > 1 ? "s" : ""}${expMonths > 0 ? ` ${expMonths} mo` : ""}`
                : `${expMonths} mos`;

            return (
              <Link
                key={candidate.id}
                href={`/candidates/${candidate.id}`}
                className="group bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs hover:border-blue-400/80 hover:shadow-sm transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-4"
              >
                <div className="space-y-1.5 min-w-0">
                  <div className="flex items-center space-x-3">
                    <div className="h-10 w-10 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs uppercase shrink-0">
                      {candidate.full_name.slice(0, 2)}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <h3 className="text-base font-semibold text-slate-900 group-hover:text-blue-600 transition-colors">
                          {candidate.full_name}
                        </h3>
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                            candidate.profile_status === "ACTIVE"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : candidate.profile_status === "PLACED"
                              ? "bg-purple-50 text-purple-700 border-purple-200"
                              : "bg-slate-100 text-slate-600 border-slate-200"
                          }`}
                        >
                          {candidate.profile_status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 font-medium">
                        {candidate.current_title || "Candidate Profile"}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-500 pl-13 sm:pl-0 pt-1">
                    {candidate.current_location && (
                      <span className="flex items-center">
                        <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
                        {candidate.current_location}
                      </span>
                    )}
                    <span className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      {expLabel} exp
                    </span>
                    {candidate.email && (
                      <span className="text-slate-400">{candidate.email}</span>
                    )}
                  </div>

                  {candidate.skills_preview && candidate.skills_preview.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1.5">
                      {candidate.skills_preview.map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 bg-slate-100 text-slate-700 text-[11px] rounded-md font-medium"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-3 shrink-0">
                  <span className="text-xs text-slate-400">
                    Added {formatDateTime(candidate.created_at)}
                  </span>
                  <div className="h-8 w-8 rounded-full bg-slate-50 group-hover:bg-blue-50 group-hover:text-blue-600 flex items-center justify-center text-slate-400 transition-colors">
                    <ChevronRight className="w-4 h-4" />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

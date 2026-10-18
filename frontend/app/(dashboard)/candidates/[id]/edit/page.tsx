"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  User,
  Loader2,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Candidate, CandidateProfileStatus } from "@/types";

export default function EditCandidatePage() {
  const params = useParams();
  const router = useRouter();
  const candidateId = params?.id as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [expYears, setExpYears] = useState(0);
  const [location, setLocation] = useState("");
  const [summary, setSummary] = useState("");
  const [status, setStatus] = useState<CandidateProfileStatus>("ACTIVE");

  useEffect(() => {
    async function loadCandidate() {
      try {
        const data: Candidate = await apiClient(`/candidates/${candidateId}`);
        setFullName(data.full_name);
        setEmail(data.email || "");
        setPhone(data.phone_encrypted || "");
        setCurrentTitle(data.current_title || "");
        setExpYears(Math.round(data.total_experience_months / 12));
        setLocation(data.current_location || "");
        setSummary(data.professional_summary || "");
        setStatus(data.profile_status);
      } catch (err: any) {
        setError(err.message || "Failed to load candidate.");
      } finally {
        setLoading(false);
      }
    }
    if (candidateId) {
      loadCandidate();
    }
  }, [candidateId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const payload = {
        full_name: fullName.trim(),
        email: email.trim() || undefined,
        phone_encrypted: phone.trim() || undefined,
        current_title: currentTitle.trim() || undefined,
        total_experience_months: Number(expYears) * 12,
        current_location: location.trim() || undefined,
        professional_summary: summary.trim() || undefined,
        profile_status: status,
      };

      await apiClient(`/candidates/${candidateId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      router.push(`/candidates/${candidateId}`);
    } catch (err: any) {
      setError(err.message || "Failed to update candidate.");
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-16 flex items-center justify-center text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-blue-600" />
        <span className="text-sm">Loading candidate form...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link
          href={`/candidates/${candidateId}`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Candidate Profile</span>
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Edit Candidate Profile</h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
            <User className="w-4 h-4 mr-2 text-blue-600" />
            Candidate Credentials
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Full Name *
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Profile Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as CandidateProfileStatus)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              >
                <option value="ACTIVE">Active</option>
                <option value="PLACED">Placed</option>
                <option value="INACTIVE">Inactive</option>
                <option value="ARCHIVED">Archived</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Current Title
              </label>
              <input
                type="text"
                value={currentTitle}
                onChange={(e) => setCurrentTitle(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Total Experience (Years)
              </label>
              <input
                type="number"
                min={0}
                value={expYears}
                onChange={(e) => setExpYears(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Current Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Professional Summary
            </label>
            <textarea
              rows={4}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>

          <div className="pt-2 flex justify-end space-x-3">
            <Link
              href={`/candidates/${candidateId}`}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs flex items-center space-x-2 transition-colors disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Update Profile</span>}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}

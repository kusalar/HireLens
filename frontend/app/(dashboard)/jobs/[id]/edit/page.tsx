"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Loader2,
  Briefcase,
  Layers,
  Plus,
  Trash2,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Job, WorkMode, EmploymentType, JobStatus, RequirementType } from "@/types";

export default function EditJobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.id as string;

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<WorkMode>("ONSITE");
  const [employmentType, setEmploymentType] = useState<EmploymentType>("FULL_TIME");
  const [status, setStatus] = useState<JobStatus>("ACTIVE");
  const [minExp, setMinExp] = useState(0);
  const [maxExp, setMaxExp] = useState<number | "">("");
  const [description, setDescription] = useState("");
  const [responsibilities, setResponsibilities] = useState("");

  // Existing requirements
  const [existingRequirements, setExistingRequirements] = useState<any[]>([]);

  // New requirement draft
  const [newReqText, setNewReqText] = useState("");
  const [newReqSkill, setNewReqSkill] = useState("");
  const [newReqType, setNewReqType] = useState<RequirementType>("SKILL");
  const [newReqWeight, setNewReqWeight] = useState(1.0);
  const [newReqMandatory, setNewReqMandatory] = useState(true);
  const [addingReq, setAddingReq] = useState(false);

  useEffect(() => {
    async function loadJob() {
      try {
        const data: Job = await apiClient(`/jobs/${jobId}`);
        setTitle(data.title);
        setDepartment(data.department || "");
        setLocation(data.location || "");
        setWorkMode(data.work_mode);
        setEmploymentType(data.employment_type);
        setStatus(data.status);
        setMinExp(data.minimum_experience);
        setMaxExp(data.maximum_experience ?? "");
        setDescription(data.description || "");
        setResponsibilities(data.responsibilities || "");
        setExistingRequirements(data.requirements || []);
      } catch (err: any) {
        setError(err.message || "Failed to load job.");
      } finally {
        setLoading(false);
      }
    }
    if (jobId) {
      loadJob();
    }
  }, [jobId]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (maxExp !== "" && minExp > Number(maxExp)) {
      setError("Minimum experience cannot exceed maximum experience.");
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        title,
        department: department || undefined,
        location: location || undefined,
        work_mode: workMode,
        employment_type: employmentType,
        status,
        minimum_experience: Number(minExp),
        maximum_experience: maxExp === "" ? undefined : Number(maxExp),
        description: description || undefined,
        responsibilities: responsibilities || undefined,
      };

      await apiClient(`/jobs/${jobId}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      router.push(`/jobs/${jobId}`);
    } catch (err: any) {
      setError(err.message || "Failed to update job.");
      setSubmitting(false);
    }
  };

  const handleAddRequirement = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newReqText.trim()) return;
    setAddingReq(true);
    try {
      const req: any = await apiClient(`/jobs/${jobId}/requirements`, {
        method: "POST",
        body: JSON.stringify({
          requirement_text: newReqText.trim(),
          normalized_skill: newReqSkill.trim() || undefined,
          requirement_type: newReqType,
          importance_weight: Number(newReqWeight),
          is_mandatory: newReqMandatory,
        }),
      });
      setExistingRequirements([...existingRequirements, req]);
      setNewReqText("");
      setNewReqSkill("");
    } catch (err: any) {
      setError(err.message || "Failed to add requirement.");
    } finally {
      setAddingReq(false);
    }
  };

  const handleDeleteRequirement = async (reqId: string) => {
    try {
      await apiClient(`/jobs/${jobId}/requirements/${reqId}`, {
        method: "DELETE",
      });
      setExistingRequirements(existingRequirements.filter((r) => r.id !== reqId));
    } catch (err: any) {
      setError(err.message || "Failed to delete requirement.");
    }
  };

  if (loading) {
    return (
      <div className="py-16 flex items-center justify-center text-slate-500">
        <Loader2 className="w-5 h-5 animate-spin mr-2 text-blue-600" />
        <span className="text-sm">Loading job form...</span>
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link
          href={`/jobs/${jobId}`}
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Job Details</span>
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Edit Job Position</h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
            <Briefcase className="w-4 h-4 mr-2 text-blue-600" />
            Position Details
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Job Title *
              </label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Status
              </label>
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as JobStatus)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              >
                <option value="ACTIVE">Active</option>
                <option value="DRAFT">Draft</option>
                <option value="PAUSED">Paused</option>
                <option value="ARCHIVED">Archived</option>
                <option value="CLOSED">Closed</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Department
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Work Mode
              </label>
              <select
                value={workMode}
                onChange={(e) => setWorkMode(e.target.value as WorkMode)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              >
                <option value="ONSITE">Onsite</option>
                <option value="HYBRID">Hybrid</option>
                <option value="REMOTE">Remote</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Minimum Experience (Years)
              </label>
              <input
                type="number"
                min={0}
                required
                value={minExp}
                onChange={(e) => setMinExp(Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Maximum Experience (Years)
              </label>
              <input
                type="number"
                min={0}
                value={maxExp}
                onChange={(e) => setMaxExp(e.target.value === "" ? "" : Number(e.target.value))}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Job Description
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Responsibilities
            </label>
            <textarea
              rows={3}
              value={responsibilities}
              onChange={(e) => setResponsibilities(e.target.value)}
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs flex items-center space-x-2 transition-colors disabled:opacity-50"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <span>Save Position Details</span>}
            </button>
          </div>
        </div>
      </form>

      {/* Requirements Section */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
          <Layers className="w-4 h-4 mr-2 text-blue-600" />
          Manage Requirements ({existingRequirements.length})
        </h2>

        {/* Existing List */}
        <div className="space-y-2">
          {existingRequirements.map((req) => (
            <div
              key={req.id}
              className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-center justify-between text-xs"
            >
              <div className="space-y-1">
                <span className="font-medium text-slate-900">{req.requirement_text}</span>
                <div className="flex items-center space-x-2">
                  <span className="text-[10px] uppercase font-semibold px-1.5 py-0.5 bg-blue-100/60 text-blue-800 rounded">
                    {req.requirement_type}
                  </span>
                  {req.normalized_skill && (
                    <span className="text-[10px] font-mono text-slate-600 bg-white border border-slate-200 px-1.5 py-0.5 rounded">
                      {req.normalized_skill}
                    </span>
                  )}
                  <span className="text-slate-400">Weight: {req.importance_weight}x</span>
                  {req.is_mandatory && (
                    <span className="text-[10px] font-semibold text-emerald-700">Mandatory</span>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => handleDeleteRequirement(req.id)}
                className="p-1.5 text-slate-400 hover:text-red-600 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))}
        </div>

        {/* Add new requirement */}
        <form onSubmit={handleAddRequirement} className="pt-4 border-t border-slate-100 space-y-3">
          <span className="text-xs font-bold text-slate-700 uppercase tracking-wider block">
            Add Another Requirement
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-2">
            <div className="sm:col-span-2">
              <input
                type="text"
                required
                value={newReqText}
                onChange={(e) => setNewReqText(e.target.value)}
                placeholder="Requirement text..."
                className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
              />
            </div>
            <div>
              <input
                type="text"
                value={newReqSkill}
                onChange={(e) => setNewReqSkill(e.target.value)}
                placeholder="Normalized skill (optional)"
                className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md"
              />
            </div>
            <div className="flex items-center space-x-2">
              <button
                type="submit"
                disabled={addingReq}
                className="w-full py-1.5 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-md shadow-xs transition-colors"
              >
                {addingReq ? "Adding..." : "Add"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}

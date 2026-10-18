"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Plus,
  Trash2,
  Loader2,
  Briefcase,
  Layers,
  Sparkles,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { RequirementType, WorkMode, EmploymentType } from "@/types";

interface RequirementDraft {
  requirement_text: string;
  normalized_skill: string;
  requirement_type: RequirementType;
  importance_weight: number;
  is_mandatory: boolean;
}

export default function CreateJobPage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form State
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<WorkMode>("ONSITE");
  const [employmentType, setEmploymentType] = useState<EmploymentType>("FULL_TIME");
  const [minExp, setMinExp] = useState(2);
  const [maxExp, setMaxExp] = useState<number | "">(5);
  const [description, setDescription] = useState("");
  const [responsibilities, setResponsibilities] = useState("");

  // Requirements Builder
  const [requirements, setRequirements] = useState<RequirementDraft[]>([
    {
      requirement_text: "Proven proficiency in Python and modern web frameworks",
      normalized_skill: "Python",
      requirement_type: "SKILL",
      importance_weight: 1.5,
      is_mandatory: true,
    },
  ]);

  const addRequirement = () => {
    setRequirements([
      ...requirements,
      {
        requirement_text: "",
        normalized_skill: "",
        requirement_type: "SKILL",
        importance_weight: 1.0,
        is_mandatory: true,
      },
    ]);
  };

  const removeRequirement = (index: number) => {
    setRequirements(requirements.filter((_, i) => i !== index));
  };

  const updateRequirement = (index: number, field: keyof RequirementDraft, value: any) => {
    const updated = [...requirements];
    updated[index] = { ...updated[index], [field]: value };
    setRequirements(updated);
  };

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
        minimum_experience: Number(minExp),
        maximum_experience: maxExp === "" ? undefined : Number(maxExp),
        description: description || undefined,
        responsibilities: responsibilities || undefined,
        requirements: requirements
          .filter((r) => r.requirement_text.trim().length > 0)
          .map((r) => ({
            ...r,
            importance_weight: Number(r.importance_weight),
            normalized_skill: r.normalized_skill || undefined,
          })),
      };

      const created: any = await apiClient("/jobs", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push(`/jobs/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create job.");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      {/* Navigation & Header */}
      <div>
        <Link
          href="/jobs"
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Jobs</span>
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Create Job Position</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Define job specifications and structured criteria for AI candidate alignment.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Information Card */}
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
                placeholder="e.g. Lead Full Stack Engineer"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Department / Practice Area
              </label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="e.g. Technology & Cloud"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Primary Location
              </label>
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                placeholder="e.g. Bengaluru, Karnataka"
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
                Employment Type
              </label>
              <select
                value={employmentType}
                onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              >
                <option value="FULL_TIME">Full Time</option>
                <option value="PART_TIME">Part Time</option>
                <option value="CONTRACT">Contract</option>
                <option value="INTERNSHIP">Internship</option>
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
                Maximum Experience (Years, Optional)
              </label>
              <input
                type="number"
                min={0}
                value={maxExp}
                onChange={(e) => setMaxExp(e.target.value === "" ? "" : Number(e.target.value))}
                placeholder="Leave blank for no upper bound"
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
              placeholder="Overview of the position, team structure, and impact..."
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Key Responsibilities
            </label>
            <textarea
              rows={3}
              value={responsibilities}
              onChange={(e) => setResponsibilities(e.target.value)}
              placeholder="Core day-to-day duties, deliverables, and leadership expectations..."
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>
        </div>

        {/* Requirements Builder Card */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
                <Layers className="w-4 h-4 mr-2 text-blue-600" />
                Structured Requirements & Matching Criteria
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                These criteria feed the explainable matching engine in Phase 4.
              </p>
            </div>
            <button
              type="button"
              onClick={addRequirement}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold rounded-md transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Requirement</span>
            </button>
          </div>

          <div className="space-y-3">
            {requirements.map((req, index) => (
              <div
                key={index}
                className="p-3.5 rounded-lg border border-slate-200 bg-slate-50/50 space-y-2.5"
              >
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <input
                      type="text"
                      required
                      value={req.requirement_text}
                      onChange={(e) =>
                        updateRequirement(index, "requirement_text", e.target.value)
                      }
                      placeholder="Requirement requirement text (e.g. Strong understanding of PostgreSQL indexing)"
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                  {requirements.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeRequirement(index)}
                      className="p-1.5 text-slate-400 hover:text-red-600 rounded transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-xs">
                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 mb-0.5">
                      Normalized Skill
                    </span>
                    <input
                      type="text"
                      value={req.normalized_skill}
                      onChange={(e) =>
                        updateRequirement(index, "normalized_skill", e.target.value)
                      }
                      placeholder="e.g. PostgreSQL"
                      className="w-full px-2 py-1 bg-white border border-slate-300 rounded text-xs"
                    />
                  </div>

                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 mb-0.5">
                      Type
                    </span>
                    <select
                      value={req.requirement_type}
                      onChange={(e) =>
                        updateRequirement(index, "requirement_type", e.target.value as RequirementType)
                      }
                      className="w-full px-2 py-1 bg-white border border-slate-300 rounded text-xs"
                    >
                      <option value="SKILL">Skill</option>
                      <option value="EXPERIENCE">Experience</option>
                      <option value="EDUCATION">Education</option>
                      <option value="CERTIFICATION">Certification</option>
                      <option value="LOCATION">Location</option>
                      <option value="OTHER">Other</option>
                    </select>
                  </div>

                  <div>
                    <span className="block text-[10px] uppercase font-bold text-slate-500 mb-0.5">
                      Importance Weight ({req.importance_weight}x)
                    </span>
                    <input
                      type="range"
                      min={0.5}
                      max={5.0}
                      step={0.5}
                      value={req.importance_weight}
                      onChange={(e) =>
                        updateRequirement(index, "importance_weight", Number(e.target.value))
                      }
                      className="w-full accent-blue-600"
                    />
                  </div>

                  <div className="flex items-center space-x-2 pt-3">
                    <input
                      type="checkbox"
                      id={`mandatory-${index}`}
                      checked={req.is_mandatory}
                      onChange={(e) =>
                        updateRequirement(index, "is_mandatory", e.target.checked)
                      }
                      className="rounded border-slate-300 text-blue-600 focus:ring-blue-600"
                    />
                    <label
                      htmlFor={`mandatory-${index}`}
                      className="text-xs font-semibold text-slate-700 cursor-pointer"
                    >
                      Mandatory
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <Link
            href="/jobs"
            className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={submitting}
            className="px-5 py-2 text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs flex items-center space-x-2 transition-colors disabled:opacity-50"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span>Create Job & Save Requirements</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

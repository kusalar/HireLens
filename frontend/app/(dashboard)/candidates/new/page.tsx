"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  User,
  Briefcase,
  GraduationCap,
  Tag,
  Plus,
  Trash2,
  Loader2,
} from "lucide-react";
import { apiClient } from "@/lib/api";

export default function AddCandidatePage() {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Core Info
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [expYears, setExpYears] = useState(3);
  const [location, setLocation] = useState("");
  const [summary, setSummary] = useState("");

  // Skills
  const [skillInput, setSkillInput] = useState("");
  const [skills, setSkills] = useState<string[]>(["React", "TypeScript", "Node.js"]);

  // Work Experience
  const [experiences, setExperiences] = useState<any[]>([
    { company: "", job_title: "", start_date: "", end_date: "", description: "" },
  ]);

  // Education
  const [educations, setEducations] = useState<any[]>([
    { institution: "", qualification: "", field_of_study: "", start_year: "", end_year: "" },
  ]);

  const addSkill = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      const val = skillInput.trim().replace(",", "");
      if (val && !skills.includes(val)) {
        setSkills([...skills, val]);
        setSkillInput("");
      }
    }
  };

  const removeSkill = (s: string) => {
    setSkills(skills.filter((item) => item !== s));
  };

  const addExperience = () => {
    setExperiences([
      ...experiences,
      { company: "", job_title: "", start_date: "", end_date: "", description: "" },
    ]);
  };

  const updateExperience = (index: number, field: string, value: string) => {
    const updated = [...experiences];
    updated[index][field] = value;
    setExperiences(updated);
  };

  const removeExperience = (index: number) => {
    setExperiences(experiences.filter((_, i) => i !== index));
  };

  const addEducation = () => {
    setEducations([
      ...educations,
      { institution: "", qualification: "", field_of_study: "", start_year: "", end_year: "" },
    ]);
  };

  const updateEducation = (index: number, field: string, value: any) => {
    const updated = [...educations];
    updated[index][field] = value;
    setEducations(updated);
  };

  const removeEducation = (index: number) => {
    setEducations(educations.filter((_, i) => i !== index));
  };

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
        skills: skills.map((s) => ({
          skill_name: s,
          normalized_skill: s,
          proficiency: "ADVANCED",
        })),
        experiences: experiences
          .filter((exp) => exp.company.trim() && exp.job_title.trim())
          .map((exp) => ({
            company: exp.company.trim(),
            job_title: exp.job_title.trim(),
            start_date: exp.start_date || undefined,
            end_date: exp.end_date || undefined,
            description: exp.description || undefined,
          })),
        educations: educations
          .filter((edu) => edu.institution.trim() && edu.qualification.trim())
          .map((edu) => ({
            institution: edu.institution.trim(),
            qualification: edu.qualification.trim(),
            field_of_study: edu.field_of_study || undefined,
            start_year: edu.start_year ? Number(edu.start_year) : undefined,
            end_year: edu.end_year ? Number(edu.end_year) : undefined,
          })),
      };

      const created: any = await apiClient("/candidates", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      router.push(`/candidates/${created.id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create candidate.");
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl space-y-6">
      <div>
        <Link
          href="/candidates"
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 mb-2 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Candidates</span>
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Add Candidate Profile</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Enter candidate credentials and career history into your agency database.
        </p>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Basic Info */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
            <User className="w-4 h-4 mr-2 text-blue-600" />
            Personal & Contact Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Candidate Full Name *
              </label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="e.g. Vikramaditya Rao"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="candidate@example.com"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Current Professional Title
              </label>
              <input
                type="text"
                value={currentTitle}
                onChange={(e) => setCurrentTitle(e.target.value)}
                placeholder="e.g. Senior Frontend Architect"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Phone Number
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
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
                placeholder="e.g. Pune, Maharashtra"
                className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Professional Summary
            </label>
            <textarea
              rows={3}
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Candidate background, core proficiencies, and career milestones..."
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
            />
          </div>
        </div>

        {/* Skills Card */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-3">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
            <Tag className="w-4 h-4 mr-2 text-blue-600" />
            Skills & Competencies
          </h2>
          <p className="text-xs text-slate-500">
            Type skill name and press Enter or comma to add.
          </p>

          <input
            type="text"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={addSkill}
            placeholder="e.g. Python, Docker, PostgreSQL..."
            className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 text-slate-900"
          />

          <div className="flex flex-wrap gap-2 pt-1">
            {skills.map((s, idx) => (
              <span
                key={idx}
                className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
              >
                {s}
                <button
                  type="button"
                  onClick={() => removeSkill(s)}
                  className="ml-1.5 text-blue-400 hover:text-blue-800 font-bold"
                >
                  ×
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Experience Section */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <Briefcase className="w-4 h-4 mr-2 text-blue-600" />
              Work History
            </h2>
            <button
              type="button"
              onClick={addExperience}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              <span>Add Position</span>
            </button>
          </div>

          <div className="space-y-4">
            {experiences.map((exp, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <input
                      type="text"
                      placeholder="Company Name"
                      value={exp.company}
                      onChange={(e) => updateExperience(idx, "company", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Job Title"
                      value={exp.job_title}
                      onChange={(e) => updateExperience(idx, "job_title", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Start Date (e.g. 2021-03)"
                      value={exp.start_date}
                      onChange={(e) => updateExperience(idx, "start_date", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      placeholder="End Date (e.g. Present)"
                      value={exp.end_date}
                      onChange={(e) => updateExperience(idx, "end_date", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                    {experiences.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeExperience(idx)}
                        className="text-slate-400 hover:text-red-600 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Education Section */}
        <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <GraduationCap className="w-4 h-4 mr-2 text-blue-600" />
              Education
            </h2>
            <button
              type="button"
              onClick={addEducation}
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 inline-flex items-center"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              <span>Add Education</span>
            </button>
          </div>

          <div className="space-y-4">
            {educations.map((edu, idx) => (
              <div key={idx} className="p-4 rounded-lg bg-slate-50 border border-slate-200/80 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <input
                      type="text"
                      placeholder="Institution / University"
                      value={edu.institution}
                      onChange={(e) => updateEducation(idx, "institution", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Degree / Qualification (e.g. B.Tech)"
                      value={edu.qualification}
                      onChange={(e) => updateEducation(idx, "qualification", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      placeholder="Field of Study (e.g. Computer Science)"
                      value={edu.field_of_study}
                      onChange={(e) => updateEducation(idx, "field_of_study", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                  </div>
                  <div className="flex items-center space-x-2">
                    <input
                      type="number"
                      placeholder="End Year (e.g. 2020)"
                      value={edu.end_year}
                      onChange={(e) => updateEducation(idx, "end_year", e.target.value)}
                      className="w-full px-3 py-1.5 text-xs bg-white border border-slate-300 rounded"
                    />
                    {educations.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeEducation(idx)}
                        className="text-slate-400 hover:text-red-600 p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-3 pt-2">
          <Link
            href="/candidates"
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
              <span>Save Candidate Profile</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  FileText,
  ArrowLeft,
  Sparkles,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Save,
  UserCheck,
  UserPlus,
  Building,
  GraduationCap,
  Briefcase,
  Layers,
  HelpCircle,
  Clock,
  BookOpen,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  ResumeDetailResponse,
  ResumeEvidence,
  VerificationStatus,
  CandidateMatchSuggestion,
} from "@/types";

export default function ResumeReviewPage() {
  const { id } = useParams() as { id: string };
  const router = useRouter();
  const [data, setData] = useState<ResumeDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingProfile, setSavingProfile] = useState(false);
  const [confirmingCandidate, setConfirmingCandidate] = useState(false);

  // Editable identity fields
  const [candidateName, setCandidateName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [currentTitle, setCurrentTitle] = useState("");
  const [location, setLocation] = useState("");
  const [experienceMonths, setExperienceMonths] = useState<number>(0);
  const [summary, setSummary] = useState("");

  // Evidences
  const [evidences, setEvidences] = useState<ResumeEvidence[]>([]);

  // Association choice
  const [selectedCandidateId, setSelectedCandidateId] = useState<string>("");
  const [createNewCandidate, setCreateNewCandidate] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        const res: ResumeDetailResponse = await apiClient(`/resumes/${id}`);
        setData(res);
        setEvidences(res.evidences || []);

        const prof = res.current_profile;
        if (prof) {
          setCandidateName(prof.extracted_name || res.resume.candidate_name || "");
          setEmail(prof.extracted_email || "");
          setPhone(prof.extracted_phone || "");
          setCurrentTitle(prof.extracted_current_title || "");
          setLocation(prof.extracted_location || "");
          setExperienceMonths(prof.extracted_experience_months || 0);
          setSummary(prof.extracted_summary || "");
        } else if (res.resume.candidate_name) {
          setCandidateName(res.resume.candidate_name);
        }

        // If possible matches exist, default to first match or create new
        if (res.possible_matching_candidates && res.possible_matching_candidates.length > 0) {
          setSelectedCandidateId(res.possible_matching_candidates[0].candidate_id);
          setCreateNewCandidate(false);
        }
      } catch (err) {
        console.error("Failed to load review details:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  const handleSaveProfileCorrections = async () => {
    setSavingProfile(true);
    try {
      await apiClient(`/resumes/${id}/profile`, {
        method: "PUT",
        body: JSON.stringify({
          extracted_name: candidateName,
          extracted_email: email,
          extracted_phone: phone,
          extracted_current_title: currentTitle,
          extracted_location: location,
          extracted_experience_months: experienceMonths,
          extracted_summary: summary,
          recruiter_review_status: "CORRECTED",
        }),
      });
      alert("Extracted candidate profile updated successfully.");
    } catch (err: any) {
      alert(`Save failed: ${err.message}`);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleUpdateEvidenceStatus = async (
    evidenceId: string,
    newStatus: VerificationStatus,
    correctedVal?: string
  ) => {
    try {
      const payload: any = { verification_status: newStatus };
      if (correctedVal) payload.corrected_value = correctedVal;

      const updated = await apiClient<ResumeEvidence>(
        `/resumes/${id}/evidence/${evidenceId}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        }
      );

      setEvidences((prev) =>
        prev.map((e) => (e.id === evidenceId ? { ...e, verification_status: newStatus } : e))
      );
    } catch (err: any) {
      alert(`Failed to update evidence: ${err.message}`);
    }
  };

  const handleConfirmAndAssociate = async () => {
    if (!createNewCandidate && !selectedCandidateId) {
      alert("Please select an existing candidate or choose to create a new profile.");
      return;
    }

    setConfirmingCandidate(true);
    try {
      const payload = {
        candidate_id: createNewCandidate ? undefined : selectedCandidateId,
        create_new_candidate: createNewCandidate,
        candidate_name: candidateName,
        candidate_email: email,
        candidate_phone: phone,
        candidate_title: currentTitle,
        candidate_location: location,
        candidate_summary: summary,
        total_experience_months: experienceMonths,
      };

      const result: any = await apiClient(`/resumes/${id}/associate-candidate`, {
        method: "POST",
        body: JSON.stringify(payload),
      });

      alert(`Candidate profile confirmed! Master Candidate ID: ${result.id}`);
      router.push(`/candidates/${result.id}`);
    } catch (err: any) {
      alert(`Association failed: ${err.message}`);
    } finally {
      setConfirmingCandidate(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center">
        <div className="w-8 h-8 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto"></div>
        <p className="mt-3 text-sm text-slate-500 font-medium">
          Loading recruiter review workspace...
        </p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto py-16 text-center">
        <AlertCircle className="w-12 h-12 text-rose-500 mx-auto mb-3" />
        <h2 className="text-lg font-bold text-slate-800">Resume Not Found</h2>
        <Link
          href="/resumes"
          className="mt-4 inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
        >
          Back to Resumes
        </Link>
      </div>
    );
  }

  const { resume, current_profile, possible_matching_candidates } = data;
  const structured = current_profile?.structured_data;

  const skillsEvidences = evidences.filter((e) => e.field_name.startsWith("skill:"));
  const expEvidences = evidences.filter((e) => e.field_name.startsWith("experience:"));
  const eduEvidences = evidences.filter((e) => e.field_name.startsWith("education:"));

  return (
    <div className="max-w-6xl mx-auto space-y-6 pb-20">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center space-x-3">
          <Link
            href={`/resumes/${id}`}
            className="p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">
                Review & Confirm Candidate Facts
              </h1>
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                <Sparkles className="w-3.5 h-3.5 mr-1" />
                AI-Assisted
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Source Document: <span className="font-semibold text-slate-700">{resume.original_filename}</span> • Recruiter remains in full control.
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleSaveProfileCorrections}
            disabled={savingProfile}
            className="inline-flex items-center px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <Save className="w-4 h-4 mr-1.5" />
            {savingProfile ? "Saving..." : "Save Corrections"}
          </button>

          <button
            onClick={handleConfirmAndAssociate}
            disabled={confirmingCandidate}
            className="inline-flex items-center px-4 py-2 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-colors"
          >
            <UserCheck className="w-4 h-4 mr-2" />
            {confirmingCandidate ? "Confirming..." : "Confirm & Save Candidate"}
          </button>
        </div>
      </div>

      {/* Main Grid: Left Column Editor & Evidence, Right Column Candidate Matching */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 Cols): Identity & Evidence Reviews */}
        <div className="lg:col-span-2 space-y-6">
          {/* Identity Fields Editor */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3 flex items-center">
              <UserCheck className="w-4 h-4 mr-2 text-blue-600" />
              Candidate Identity Information
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 font-medium"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Phone Number
                </label>
                <input
                  type="text"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Current Job Title
                </label>
                <input
                  type="text"
                  value={currentTitle}
                  onChange={(e) => setCurrentTitle(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Current Location
                </label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Total Experience (Months)
                </label>
                <input
                  type="number"
                  min="0"
                  value={experienceMonths}
                  onChange={(e) => setExperienceMonths(parseInt(e.target.value) || 0)}
                  className="w-full text-sm px-3 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 mb-1">
                Professional Summary
              </label>
              <textarea
                rows={3}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                className="w-full text-sm p-3 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 leading-relaxed"
              />
            </div>
          </div>

          {/* Extracted Skills & Evidence Section */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h2 className="text-base font-semibold text-slate-900 flex items-center">
                <Sparkles className="w-4 h-4 mr-2 text-blue-600" />
                Skills with Verifiable Document Evidence ({structured?.skills?.length || 0})
              </h2>
            </div>

            {(!structured?.skills || structured.skills.length === 0) && (
              <p className="text-sm text-slate-400 italic">No skills extracted from document.</p>
            )}

            <div className="space-y-3">
              {structured?.skills?.map((skill, index) => {
                const evMatch = skillsEvidences.find(
                  (e) => e.field_name === `skill:${skill.skill_name}`
                );
                const status = evMatch?.verification_status || "UNREVIEWED";

                return (
                  <div
                    key={index}
                    className="p-3.5 rounded-lg border border-slate-200/80 bg-slate-50/50 flex flex-col md:flex-row md:items-center justify-between gap-3"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm text-slate-900">
                          {skill.skill_name}
                        </span>
                        {skill.proficiency && (
                          <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-blue-100/60 text-blue-700">
                            {skill.proficiency}
                          </span>
                        )}
                        {skill.source_page && (
                          <span className="text-[11px] font-medium text-slate-500">
                            Page {skill.source_page}
                          </span>
                        )}
                      </div>

                      {skill.evidence && (
                        <p className="text-xs text-slate-600 italic mt-1 bg-white p-2 rounded border border-slate-100">
                          &ldquo;{skill.evidence}&rdquo;
                        </p>
                      )}
                    </div>

                    <div className="flex items-center space-x-1.5 shrink-0">
                      <button
                        onClick={() =>
                          evMatch && handleUpdateEvidenceStatus(evMatch.id, "VERIFIED")
                        }
                        className={`px-2.5 py-1 text-xs font-semibold rounded border transition-colors flex items-center ${
                          status === "VERIFIED"
                            ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                            : "bg-white text-emerald-700 border-emerald-300 hover:bg-emerald-50"
                        }`}
                      >
                        <CheckCircle2 className="w-3 h-3 mr-1" />
                        Verify
                      </button>

                      <button
                        onClick={() =>
                          evMatch && handleUpdateEvidenceStatus(evMatch.id, "REJECTED")
                        }
                        className={`px-2.5 py-1 text-xs font-semibold rounded border transition-colors flex items-center ${
                          status === "REJECTED"
                            ? "bg-rose-600 text-white border-rose-600 shadow-xs"
                            : "bg-white text-rose-700 border-rose-300 hover:bg-rose-50"
                        }`}
                      >
                        <XCircle className="w-3 h-3 mr-1" />
                        Reject
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Work Experience Timeline Section */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3 flex items-center">
              <Briefcase className="w-4 h-4 mr-2 text-blue-600" />
              Work Experience Timeline ({structured?.experiences?.length || 0})
            </h2>

            {(!structured?.experiences || structured.experiences.length === 0) && (
              <p className="text-sm text-slate-400 italic">No experience entries extracted.</p>
            )}

            <div className="space-y-4">
              {structured?.experiences?.map((exp, index) => (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-slate-200 bg-white space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="font-bold text-sm text-slate-900">{exp.job_title}</h4>
                      <p className="text-xs font-medium text-slate-600">{exp.company}</p>
                    </div>
                    <span className="text-xs font-mono text-slate-500">
                      {exp.start_date || "N/A"} - {exp.end_date || "Present"}
                    </span>
                  </div>

                  {exp.description && (
                    <p className="text-xs text-slate-600 leading-relaxed">{exp.description}</p>
                  )}

                  {exp.evidence && (
                    <div className="text-xs text-slate-500 bg-slate-50 p-2 rounded border border-slate-100">
                      <span className="font-semibold text-slate-700">Source Excerpt: </span>
                      &ldquo;{exp.evidence}&rdquo;
                      {exp.source_page ? ` (Page ${exp.source_page})` : ""}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Education Records */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
            <h2 className="text-base font-semibold text-slate-900 border-b border-slate-100 pb-3 flex items-center">
              <GraduationCap className="w-4 h-4 mr-2 text-blue-600" />
              Education Records ({structured?.educations?.length || 0})
            </h2>

            {(!structured?.educations || structured.educations.length === 0) && (
              <p className="text-sm text-slate-400 italic">No education entries extracted.</p>
            )}

            <div className="space-y-3">
              {structured?.educations?.map((edu, index) => (
                <div
                  key={index}
                  className="p-4 rounded-lg border border-slate-200 bg-white space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="font-bold text-sm text-slate-900">{edu.institution}</h4>
                    <span className="text-xs font-mono text-slate-500">
                      {edu.start_year || ""} - {edu.end_year || ""}
                    </span>
                  </div>
                  <p className="text-xs text-slate-600">
                    {edu.qualification} in {edu.field_of_study || "General"}
                  </p>
                  {edu.evidence && (
                    <p className="text-xs text-slate-500 italic bg-slate-50 p-2 rounded border border-slate-100 mt-1">
                      &ldquo;{edu.evidence}&rdquo;
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Recruiter Confirmation & Candidate Association */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5 space-y-4 sticky top-24">
            <h3 className="text-base font-bold text-slate-900 border-b border-slate-100 pb-3 flex items-center">
              <UserCheck className="w-4 h-4 mr-2 text-emerald-600" />
              Candidate Profile Confirmation
            </h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              Decide whether to register this verified candidate as a new profile or attach it to an existing candidate.
            </p>

            {/* Possible Candidate Matches */}
            {possible_matching_candidates && possible_matching_candidates.length > 0 && (
              <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 space-y-2">
                <span className="text-xs font-bold text-amber-800 flex items-center">
                  <AlertCircle className="w-3.5 h-3.5 mr-1 text-amber-600" />
                  Possible Candidate Matches Found
                </span>
                <p className="text-[11px] text-amber-700">
                  Existing candidates found with matching email or name. HireLens will never auto-merge profiles.
                </p>

                <div className="space-y-2 pt-1">
                  {possible_matching_candidates.map((match) => (
                    <label
                      key={match.candidate_id}
                      className={`block p-2.5 rounded border text-xs cursor-pointer transition-colors ${
                        !createNewCandidate && selectedCandidateId === match.candidate_id
                          ? "bg-amber-100/70 border-amber-400 font-semibold text-slate-900"
                          : "bg-white border-amber-200 text-slate-700 hover:bg-amber-50/50"
                      }`}
                    >
                      <input
                        type="radio"
                        name="matchChoice"
                        checked={!createNewCandidate && selectedCandidateId === match.candidate_id}
                        onChange={() => {
                          setSelectedCandidateId(match.candidate_id);
                          setCreateNewCandidate(false);
                        }}
                        className="mr-2"
                      />
                      <span>{match.full_name}</span>
                      <span className="block text-[10px] text-amber-800 mt-0.5">
                        {match.match_reason}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}

            {/* Choice: Create New or Link */}
            <div className="space-y-2 pt-2">
              <label
                className={`block p-3 rounded-lg border text-sm cursor-pointer transition-colors ${
                  createNewCandidate
                    ? "bg-blue-50 border-blue-400 font-medium text-blue-900"
                    : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="candidateAction"
                  checked={createNewCandidate}
                  onChange={() => setCreateNewCandidate(true)}
                  className="mr-2 text-blue-600"
                />
                <span className="font-semibold">Create New Candidate Profile</span>
                <span className="block text-xs text-slate-500 mt-1">
                  Create a new candidate in the directory with all verified skills, experiences, and education.
                </span>
              </label>

              <label
                className={`block p-3 rounded-lg border text-sm cursor-pointer transition-colors ${
                  !createNewCandidate
                    ? "bg-blue-50 border-blue-400 font-medium text-blue-900"
                    : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                }`}
              >
                <input
                  type="radio"
                  name="candidateAction"
                  checked={!createNewCandidate}
                  onChange={() => setCreateNewCandidate(false)}
                  className="mr-2 text-blue-600"
                />
                <span className="font-semibold">Attach to Existing Candidate</span>
                <span className="block text-xs text-slate-500 mt-1">
                  Associate this resume with an existing candidate record in your agency without overwriting their profile.
                </span>
              </label>
            </div>

            <div className="pt-3 border-t border-slate-100">
              <button
                onClick={handleConfirmAndAssociate}
                disabled={confirmingCandidate}
                className="w-full py-2.5 px-4 text-sm font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-sm transition-colors flex items-center justify-center"
              >
                <UserCheck className="w-4 h-4 mr-2" />
                {confirmingCandidate ? "Confirming Profile..." : "Confirm & Save Candidate"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

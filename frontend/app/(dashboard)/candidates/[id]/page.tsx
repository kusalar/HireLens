"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  User,
  Mail,
  Phone,
  MapPin,
  Clock,
  Briefcase,
  GraduationCap,
  Tag,
  MessageSquare,
  Plus,
  Trash2,
  Edit3,
  Archive,
  Loader2,
  ShieldCheck,
  Sparkles,
  ChevronRight,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { Candidate, RecruiterNote, JobMatchResult, Application } from "@/types";
import { formatDateTime } from "@/lib/utils";

export default function CandidateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const candidateId = params?.id as string;

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [matchingHistory, setMatchingHistory] = useState<JobMatchResult[]>([]);
  const [candidateApplications, setCandidateApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Recruiter Note state
  const [newNote, setNewNote] = useState("");
  const [submittingNote, setSubmittingNote] = useState(false);
  const [noteStatus, setNoteStatus] = useState<string | null>(null);

  const fetchCandidate = async () => {
    setLoading(true);
    try {
      const [candData, matchesData, appsData] = await Promise.all([
        apiClient<Candidate>(`/candidates/${candidateId}`),
        apiClient<JobMatchResult[]>(`/candidates/${candidateId}/matches`).catch(() => []),
        apiClient<Application[]>(`/candidates/${candidateId}/applications`).catch(() => []),
      ]);
      setCandidate(candData);
      setMatchingHistory(matchesData);
      setCandidateApplications(appsData);
    } catch (err: any) {
      setError(err.message || "Failed to load candidate.");
    } finally {
      setLoading(false);
    }
  };


  useEffect(() => {
    if (candidateId) {
      fetchCandidate();
    }
  }, [candidateId]);

  const handleArchive = async () => {
    if (!confirm("Are you sure you want to archive this candidate?")) return;
    try {
      const updated: Candidate = await apiClient(`/candidates/${candidateId}/archive`, {
        method: "POST",
      });
      setCandidate(updated);
    } catch (err: any) {
      setError(err.message || "Failed to archive candidate.");
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    setSubmittingNote(true);
    setNoteStatus(null);
    try {
      const note: RecruiterNote = await apiClient(`/candidates/${candidateId}/notes`, {
        method: "POST",
        body: JSON.stringify({ note: newNote.trim() }),
      });
      if (candidate) {
        setCandidate({
          ...candidate,
          notes: [note, ...(candidate.notes || [])],
        });
      }
      setNewNote("");
      setNoteStatus("Note recorded.");
    } catch (err: any) {
      setError(err.message || "Failed to save recruiter note.");
    } finally {
      setSubmittingNote(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await apiClient(`/candidates/${candidateId}/notes/${noteId}`, {
        method: "DELETE",
      });
      if (candidate) {
        setCandidate({
          ...candidate,
          notes: (candidate.notes || []).filter((n) => n.id !== noteId),
        });
      }
    } catch (err: any) {
      setError(err.message || "Failed to delete note.");
    }
  };

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center justify-center text-slate-500 space-y-2">
        <div className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
        <span className="text-sm">Loading candidate profile...</span>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="max-w-2xl p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <p className="font-semibold">{error || "Candidate profile not found."}</p>
        <Link href="/candidates" className="mt-3 inline-block text-xs font-bold text-red-800 underline">
          Return to directory
        </Link>
      </div>
    );
  }

  const expYears = Math.floor(candidate.total_experience_months / 12);
  const expMonths = candidate.total_experience_months % 12;
  const expLabel =
    expYears > 0
      ? `${expYears} yr${expYears > 1 ? "s" : ""}${expMonths > 0 ? ` ${expMonths} mo` : ""}`
      : `${expMonths} mos`;

  return (
    <div className="max-w-5xl space-y-6">
      <div>
        <Link
          href="/candidates"
          className="inline-flex items-center text-xs font-semibold text-slate-500 hover:text-slate-800 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />
          <span>Back to Directory</span>
        </Link>
      </div>

      {/* Hero Header */}
      <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex items-start space-x-4">
          <div className="h-14 w-14 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-lg uppercase shrink-0 shadow-sm">
            {candidate.full_name.slice(0, 2)}
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-2.5">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">{candidate.full_name}</h1>
              <span
                className={`text-xs font-semibold px-2.5 py-0.5 rounded-full border ${
                  candidate.profile_status === "ACTIVE"
                    ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                    : candidate.profile_status === "PLACED"
                    ? "bg-purple-50 text-purple-700 border-purple-200"
                    : "bg-slate-100 text-slate-700 border-slate-200"
                }`}
              >
                {candidate.profile_status}
              </span>
            </div>
            <p className="text-sm font-medium text-slate-600">{candidate.current_title || "Candidate Profile"}</p>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-500 pt-1.5">
              {candidate.current_location && (
                <span className="flex items-center">
                  <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  {candidate.current_location}
                </span>
              )}
              <span className="flex items-center">
                <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                {expLabel} experience
              </span>
              {candidate.email && (
                <span className="flex items-center">
                  <Mail className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  {candidate.email}
                </span>
              )}
              {candidate.phone_encrypted && (
                <span className="flex items-center">
                  <Phone className="w-3.5 h-3.5 mr-1 text-slate-400" />
                  {candidate.phone_encrypted}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-2 shrink-0">
          <Link
            href={`/candidates/${candidate.id}/edit`}
            className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg shadow-xs transition-colors"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>Edit Profile</span>
          </Link>

          {candidate.profile_status !== "ARCHIVED" && (
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

      {/* Grid: Profile Details & Recruiter Notes */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Background & Career History */}
        <div className="lg:col-span-2 space-y-6">
          {candidate.professional_summary && (
            <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-2">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Professional Summary
              </h2>
              <p className="text-sm text-slate-700 whitespace-pre-line leading-relaxed">
                {candidate.professional_summary}
              </p>
            </div>
          )}

          {/* Skills */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-3">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <Tag className="w-4 h-4 mr-2 text-blue-600" />
              Competencies & Skills ({candidate.skills?.length || 0})
            </h2>

            {(!candidate.skills || candidate.skills.length === 0) ? (
              <p className="text-xs text-slate-400 italic">No skills documented yet.</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {candidate.skills.map((skill) => (
                  <div
                    key={skill.id}
                    className="inline-flex items-center space-x-1.5 px-3 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                  >
                    <span className="font-semibold text-slate-800">{skill.skill_name}</span>
                    {skill.proficiency && (
                      <span className="text-[10px] text-slate-400 font-mono">
                        ({skill.proficiency})
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Work History */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <Briefcase className="w-4 h-4 mr-2 text-blue-600" />
              Employment Experience
            </h2>

            {(!candidate.experiences || candidate.experiences.length === 0) ? (
              <p className="text-xs text-slate-400 italic">No employment records attached.</p>
            ) : (
              <div className="space-y-4">
                {candidate.experiences.map((exp) => (
                  <div
                    key={exp.id}
                    className="pl-4 border-l-2 border-blue-500/80 space-y-1 py-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-slate-900">{exp.job_title}</h3>
                      <span className="text-xs text-slate-400 font-medium">
                        {exp.start_date || "N/A"} — {exp.end_date || "Present"}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-slate-700">{exp.company}</p>
                    {exp.description && (
                      <p className="text-xs text-slate-500 pt-1 leading-relaxed">{exp.description}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Education */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-6 shadow-xs space-y-4">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
              <GraduationCap className="w-4 h-4 mr-2 text-blue-600" />
              Education & Degrees
            </h2>

            {(!candidate.educations || candidate.educations.length === 0) ? (
              <p className="text-xs text-slate-400 italic">No education records provided.</p>
            ) : (
              <div className="space-y-3">
                {candidate.educations.map((edu) => (
                  <div key={edu.id} className="p-3 bg-slate-50/60 border border-slate-200 rounded-lg text-xs space-y-1">
                    <div className="flex justify-between font-semibold text-slate-900">
                      <span>{edu.qualification} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}</span>
                      {edu.end_year && <span className="text-slate-400">{edu.end_year}</span>}
                    </div>
                    <p className="text-slate-600">{edu.institution}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Applications, Matching History & Recruiter Notes */}
        <div className="space-y-6">
          {/* Job Applications */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
                <Briefcase className="w-4 h-4 mr-1.5 text-blue-600" />
                Job Applications ({candidateApplications.length})
              </h2>
            </div>
            <p className="text-xs text-slate-500">
              Active and past role participation across the agency.
            </p>

            {candidateApplications.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-3 text-center">
                Candidate has not been applied to any jobs yet.
              </p>
            ) : (
              <div className="space-y-2 pt-1">
                {candidateApplications.map((app) => (
                  <Link
                    key={app.id}
                    href={`/applications/${app.id}`}
                    className="block p-3 bg-slate-50 hover:bg-blue-50/50 border border-slate-200/80 hover:border-blue-200 rounded-lg transition-colors group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-slate-900 group-hover:text-blue-600">
                        {app.job_title || "Job Position"}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                          app.status === "SELECTED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                            : app.status === "SHORTLISTED"
                            ? "bg-purple-50 text-purple-700 border-purple-200"
                            : app.status === "REJECTED"
                            ? "bg-rose-50 text-rose-700 border-rose-200"
                            : "bg-blue-50 text-blue-700 border-blue-200"
                        }`}
                      >
                        {app.status.replace("_", " ")}
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                      <span>Applied {formatDateTime(app.applied_at)}</span>
                      <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform text-slate-400" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Job Matching History */}
          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
                <Sparkles className="w-4 h-4 mr-1.5 text-blue-600" />
                Job Matching History ({matchingHistory.length})
              </h2>
            </div>
            <p className="text-xs text-slate-500">
              Evaluated fit across active job specs in your agency.
            </p>

            {matchingHistory.length === 0 ? (
              <p className="text-xs text-slate-400 italic py-3 text-center">
                No matching evaluations run yet for this candidate.
              </p>
            ) : (
              <div className="space-y-2 pt-1">
                {matchingHistory.map((m) => (
                  <Link
                    key={m.id}
                    href={`/jobs/${m.job_id}/matches/${candidateId}`}
                    className="block p-3 bg-slate-50 hover:bg-blue-50/50 border border-slate-200/80 hover:border-blue-200 rounded-lg transition-colors group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-xs text-slate-800 group-hover:text-blue-600">
                        {m.job_title || "Job Position"}
                      </span>
                      <span className="text-xs font-bold text-slate-900 bg-white border border-slate-200 px-2 py-0.5 rounded-full">
                        {Math.round(m.overall_score)}/100
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-400 mt-1">
                      <span>{m.matched_requirements_count} matched criteria</span>
                      <ChevronRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform text-slate-400" />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl border border-slate-200/80 p-5 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center">
                <MessageSquare className="w-4 h-4 mr-1.5 text-blue-600" />
                Recruiter Notes ({candidate.notes?.length || 0})
              </h2>
            </div>

            <p className="text-xs text-slate-500">
              Private screening notes, interview impressions, and feedback for your agency team.
            </p>

            {/* Note form */}
            <form onSubmit={handleAddNote} className="space-y-2">
              <textarea
                rows={3}
                required
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                placeholder="Log interview feedback, expected compensation, or assessment notes..."
                className="w-full p-2.5 text-xs bg-slate-50/50 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:bg-white"
              />
              <button
                type="submit"
                disabled={submittingNote}
                className="w-full py-2 px-3 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors flex items-center justify-center space-x-1.5 disabled:opacity-50"
              >
                {submittingNote ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <>
                    <Plus className="w-3.5 h-3.5" />
                    <span>Save Note</span>
                  </>
                )}
              </button>
            </form>

            {/* Notes List */}
            <div className="space-y-3 pt-2">
              {(!candidate.notes || candidate.notes.length === 0) ? (
                <p className="text-xs text-slate-400 italic text-center py-4">No notes logged yet.</p>
              ) : (
                candidate.notes.map((note) => (
                  <div
                    key={note.id}
                    className="p-3 bg-slate-50/70 border border-slate-200/80 rounded-lg text-xs space-y-1.5 group"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-900">
                        {note.author_name || "Recruiter"}
                      </span>
                      <div className="flex items-center space-x-2">
                        <span className="text-[10px] text-slate-400">
                          {formatDateTime(note.created_at)}
                        </span>
                        <button
                          onClick={() => handleDeleteNote(note.id)}
                          title="Delete note"
                          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-red-600 transition-opacity"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </div>
                    <p className="text-slate-700 whitespace-pre-line leading-relaxed">{note.note}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

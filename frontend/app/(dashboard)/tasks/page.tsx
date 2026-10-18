"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  CheckSquare,
  Square,
  Clock,
  AlertTriangle,
  Plus,
  Filter,
  CheckCircle2,
  Calendar,
  Briefcase,
  User,
  Trash2,
  MoreVertical,
  ChevronDown,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  RecruiterTaskRead,
  RecruiterTaskListResponse,
  RecruiterTaskStatus,
  RecruiterTaskPriority,
} from "@/types";

export default function RecruiterTasksPage() {
  const [tasks, setTasks] = useState<RecruiterTaskRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [priorityFilter, setPriorityFilter] = useState<string>("ALL");
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Create Task Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newPriority, setNewPriority] = useState<RecruiterTaskPriority>("MEDIUM");
  const [newDueDate, setNewDueDate] = useState("");
  const [submittingTask, setSubmittingTask] = useState(false);

  useEffect(() => {
    loadTasks();
  }, [statusFilter, priorityFilter]);

  async function loadTasks() {
    setLoading(true);
    setErrorBanner(null);
    try {
      let queryParams: string[] = [];
      if (statusFilter !== "ALL") queryParams.push(`status=${statusFilter}`);
      if (priorityFilter !== "ALL") queryParams.push(`priority=${priorityFilter}`);
      const qs = queryParams.length > 0 ? `?${queryParams.join("&")}` : "";

      const res = await apiClient<RecruiterTaskListResponse>(`/workflows/tasks${qs}`);
      setTasks(res.items || []);
    } catch (e: any) {
      setErrorBanner("Failed to load recruiter tasks: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleStatus(task: RecruiterTaskRead) {
    const nextStatus: RecruiterTaskStatus =
      task.status === "COMPLETED" ? "PENDING" : "COMPLETED";

    try {
      await apiClient(`/workflows/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: nextStatus }),
      });
      setSuccessBanner(
        `Task "${task.title}" marked as ${nextStatus.toLowerCase()}.`
      );
      setTimeout(() => setSuccessBanner(null), 3500);
      loadTasks();
    } catch (e: any) {
      setErrorBanner("Failed to update task: " + e.message);
    }
  }

  async function handleUpdateStatus(task: RecruiterTaskRead, status: RecruiterTaskStatus) {
    try {
      await apiClient(`/workflows/tasks/${task.id}`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setSuccessBanner(`Task status updated to ${status}.`);
      setTimeout(() => setSuccessBanner(null), 3500);
      loadTasks();
    } catch (e: any) {
      setErrorBanner("Failed to update status: " + e.message);
    }
  }

  async function handleDeleteTask(taskId: string) {
    if (!confirm("Are you sure you want to delete this task?")) return;
    try {
      await apiClient(`/workflows/tasks/${taskId}`, { method: "DELETE" });
      setSuccessBanner("Task deleted successfully.");
      setTimeout(() => setSuccessBanner(null), 3500);
      loadTasks();
    } catch (e: any) {
      setErrorBanner("Failed to delete task: " + e.message);
    }
  }

  async function handleCreateTask(e: React.FormEvent) {
    e.preventDefault();
    if (!newTitle.trim()) {
      setErrorBanner("Task title is required.");
      return;
    }

    setSubmittingTask(true);
    setErrorBanner(null);

    try {
      let isoDueDate: string | undefined = undefined;
      if (newDueDate) {
        // Interpret as IST or ISO
        const d = new Date(newDueDate);
        isoDueDate = d.toISOString();
      }

      await apiClient("/workflows/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: newTitle.trim(),
          description: newDescription.trim() || undefined,
          priority: newPriority,
          due_date: isoDueDate,
        }),
      });

      setSuccessBanner("Operational task created successfully.");
      setTimeout(() => setSuccessBanner(null), 4000);
      setShowCreateModal(false);
      setNewTitle("");
      setNewDescription("");
      setNewPriority("MEDIUM");
      setNewDueDate("");
      loadTasks();
    } catch (e: any) {
      setErrorBanner("Failed to create task: " + e.message);
    } finally {
      setSubmittingTask(false);
    }
  }

  // Formatting helpers in IST
  function formatIST(isoStr?: string | null): string {
    if (!isoStr) return "No due date";
    try {
      const date = new Date(isoStr);
      return (
        date.toLocaleString("en-IN", {
          timeZone: "Asia/Kolkata",
          day: "2-digit",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
          hour12: true,
        }) + " IST"
      );
    } catch {
      return isoStr;
    }
  }

  function isOverdue(isoStr?: string | null): boolean {
    if (!isoStr) return false;
    try {
      return new Date(isoStr).getTime() < Date.now();
    } catch {
      return false;
    }
  }

  // Summary counts
  const pendingCount = tasks.filter((t) => t.status === "PENDING").length;
  const inProgressCount = tasks.filter((t) => t.status === "IN_PROGRESS").length;
  const completedCount = tasks.filter((t) => t.status === "COMPLETED").length;
  const urgentCount = tasks.filter(
    (t) => (t.priority === "URGENT" || t.priority === "HIGH") && t.status !== "COMPLETED"
  ).length;

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-slate-900 tracking-tight flex items-center gap-3">
            <CheckSquare className="w-8 h-8 text-indigo-600" />
            Recruiter Tasks & Action Items
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Operational action items generated by recruitment workflows or scheduled by team members.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium px-4 py-2.5 rounded-xl shadow-sm shadow-indigo-100 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Recruiter Task
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorBanner && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 px-4 py-3 rounded-xl flex items-center justify-between text-sm">
          <span>{errorBanner}</span>
          <button onClick={() => setErrorBanner(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {successBanner && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 px-4 py-3 rounded-xl flex items-center justify-between text-sm">
          <span>{successBanner}</span>
          <button onClick={() => setSuccessBanner(null)} className="font-bold ml-2">
            &times;
          </button>
        </div>
      )}

      {/* Metrics Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Pending
            </div>
            <div className="text-2xl font-bold text-slate-900 mt-1">{pendingCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Urgent / High
            </div>
            <div className="text-2xl font-bold text-rose-600 mt-1">{urgentCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              In Progress
            </div>
            <div className="text-2xl font-bold text-blue-600 mt-1">{inProgressCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <Clock className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center justify-between">
          <div>
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Completed
            </div>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{completedCount}</div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        {/* Status Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl">
          {["ALL", "PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === st
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {st.replace("_", " ")}
            </button>
          ))}
        </div>

        {/* Priority Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-medium text-slate-500">Priority:</span>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="text-xs bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
          >
            <option value="ALL">All Priorities</option>
            <option value="URGENT">Urgent</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Task List */}
      {loading ? (
        <div className="p-16 text-center text-slate-400">Loading operational tasks...</div>
      ) : tasks.length === 0 ? (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-16 text-center">
          <CheckSquare className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-800">No tasks found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            There are no operational tasks matching your current filters. Tasks are triggered
            automatically by recruitment workflows or created manually.
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="mt-4 inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium px-4 py-2 rounded-xl"
          >
            <Plus className="w-3.5 h-3.5" />
            Create First Task
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const isDone = task.status === "COMPLETED";
            const overdue = !isDone && isOverdue(task.due_date);

            return (
              <div
                key={task.id}
                className={`bg-white rounded-2xl border p-5 transition-all shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  isDone
                    ? "border-slate-200 bg-slate-50/50 opacity-75"
                    : overdue
                    ? "border-rose-300 ring-1 ring-rose-200"
                    : "border-slate-200 hover:border-indigo-200 hover:shadow"
                }`}
              >
                {/* Left check and details */}
                <div className="flex items-start gap-4">
                  <button
                    onClick={() => handleToggleStatus(task)}
                    className="mt-0.5 text-slate-400 hover:text-indigo-600 transition-colors"
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-6 h-6 text-emerald-600" />
                    ) : (
                      <Square className="w-6 h-6" />
                    )}
                  </button>

                  <div className="space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h4
                        className={`font-semibold text-slate-900 ${
                          isDone ? "line-through text-slate-400" : ""
                        }`}
                      >
                        {task.title}
                      </h4>

                      {/* Priority Badge */}
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider ${
                          task.priority === "URGENT"
                            ? "bg-rose-100 text-rose-700"
                            : task.priority === "HIGH"
                            ? "bg-amber-100 text-amber-700"
                            : task.priority === "MEDIUM"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-slate-100 text-slate-600"
                        }`}
                      >
                        {task.priority}
                      </span>

                      {/* Status Badge */}
                      <span
                        className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                          task.status === "COMPLETED"
                            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                            : task.status === "IN_PROGRESS"
                            ? "bg-blue-50 text-blue-700 border border-blue-200"
                            : task.status === "CANCELLED"
                            ? "bg-slate-100 text-slate-500 border border-slate-200"
                            : "bg-amber-50 text-amber-700 border border-amber-200"
                        }`}
                      >
                        {task.status.replace("_", " ")}
                      </span>
                    </div>

                    {task.description && (
                      <p className="text-xs text-slate-600 line-clamp-2 max-w-2xl">
                        {task.description}
                      </p>
                    )}

                    {/* Metadata tags */}
                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500 pt-1">
                      {task.due_date && (
                        <span
                          className={`flex items-center gap-1 font-medium ${
                            overdue ? "text-rose-600 font-semibold" : ""
                          }`}
                        >
                          <Calendar className="w-3.5 h-3.5" />
                          Due: {formatIST(task.due_date)}
                          {overdue && " (Overdue)"}
                        </span>
                      )}

                      {task.candidate_id && (
                        <span className="flex items-center gap-1 text-indigo-600">
                          <User className="w-3.5 h-3.5" />
                          Candidate ID: {task.candidate_id.slice(0, 8)}...
                        </span>
                      )}

                      {task.job_id && (
                        <span className="flex items-center gap-1 text-slate-600">
                          <Briefcase className="w-3.5 h-3.5" />
                          Job ID: {task.job_id.slice(0, 8)}...
                        </span>
                      )}

                      {task.assigned_to_name && (
                        <span className="text-slate-400">
                          Assigned to:{" "}
                          <strong className="text-slate-600">{task.assigned_to_name}</strong>
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right controls */}
                <div className="flex items-center gap-2 self-end md:self-center">
                  <select
                    value={task.status}
                    onChange={(e) =>
                      handleUpdateStatus(task, e.target.value as RecruiterTaskStatus)
                    }
                    className="text-xs bg-slate-50 border border-slate-200 text-slate-700 rounded-lg px-2.5 py-1.5 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="PENDING">Pending</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="COMPLETED">Completed</option>
                    <option value="CANCELLED">Cancelled</option>
                  </select>

                  <button
                    onClick={() => handleDeleteTask(task.id)}
                    className="p-1.5 text-slate-400 hover:text-rose-600 transition-colors rounded-lg hover:bg-slate-100"
                    title="Delete task"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Task Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 animate-in fade-in zoom-in-95 duration-200">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Create Recruiter Task</h3>
            <p className="text-xs text-slate-500 mb-5">
              Add a follow-up action item for yourself or your recruitment team.
            </p>

            <form onSubmit={handleCreateTask} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Task Title *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Follow up on references / verify background docs"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Description / Notes
                </label>
                <textarea
                  rows={3}
                  placeholder="Provide context, required documents, or instructions..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Priority
                  </label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value as RecruiterTaskPriority)}
                    className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="URGENT">Urgent</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Due Date & Time (IST)
                  </label>
                  <input
                    type="datetime-local"
                    value={newDueDate}
                    onChange={(e) => setNewDueDate(e.target.value)}
                    className="w-full text-xs border border-slate-300 rounded-xl px-3 py-2 text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="text-xs px-4 py-2 font-medium text-slate-600 hover:text-slate-800 hover:bg-slate-100 rounded-xl transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingTask}
                  className="text-xs px-4 py-2 font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl shadow-sm transition-colors disabled:opacity-50"
                >
                  {submittingTask ? "Creating..." : "Create Task"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

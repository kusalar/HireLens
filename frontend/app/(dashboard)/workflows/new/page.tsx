"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  GitFork,
  ArrowLeft,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Layers,
  Send,
  Bell,
  CheckSquare,
  Sparkles,
  Calendar,
  BarChart2,
  ShieldCheck,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import {
  WorkflowTriggerType,
  WorkflowActionType,
  ConditionOperator,
  RecruiterTaskPriority,
} from "@/types";

interface ConditionItem {
  id: string;
  field: string;
  operator: ConditionOperator;
  value: string;
}

interface ActionItem {
  id: string;
  action_type: WorkflowActionType;
  description: string;
  requires_approval: boolean;
  approval_role: string;
  email_subject?: string;
  email_body_template?: string;
  notification_title?: string;
  notification_message?: string;
  task_title?: string;
  task_description?: string;
  task_priority?: RecruiterTaskPriority;
  task_due_days?: number;
  calendar_operation?: string;
  event_name?: string;
}

export default function NewWorkflowPage() {
  const router = useRouter();

  // Basic Info
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState<WorkflowTriggerType>("APPLICATION_SUBMITTED");

  // Conditions
  const [logicalOperator, setLogicalOperator] = useState<"AND" | "OR">("AND");
  const [conditions, setConditions] = useState<ConditionItem[]>([
    { id: "1", field: "match_score", operator: "GREATER_THAN_OR_EQUAL", value: "70" },
  ]);

  // Actions
  const [actions, setActions] = useState<ActionItem[]>([
    {
      id: "1",
      action_type: "SEND_CANDIDATE_COMMUNICATION",
      description: "Send initial acknowledgment email to candidate",
      requires_approval: false,
      approval_role: "AGENCY_ADMIN",
      email_subject: "Application received for {{job_title}}",
      email_body_template: "Hello {{candidate_name}}, thank you for applying. We are currently evaluating your profile.",
    },
  ]);

  const [saving, setSaving] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);

  // Condition Handlers
  function addCondition() {
    setConditions((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        field: "match_score",
        operator: "GREATER_THAN_OR_EQUAL",
        value: "75",
      },
    ]);
  }

  function removeCondition(id: string) {
    setConditions((prev) => prev.filter((c) => c.id !== id));
  }

  function updateCondition(id: string, updates: Partial<ConditionItem>) {
    setConditions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updates } : c))
    );
  }

  // Action Handlers
  function addAction() {
    setActions((prev) => [
      ...prev,
      {
        id: String(Date.now()),
        action_type: "CREATE_RECRUITER_TASK",
        description: "Schedule recruiter phone screen",
        requires_approval: false,
        approval_role: "AGENCY_ADMIN",
        task_title: "Review Candidate Profile",
        task_description: "Examine portfolio and schedule initial interview",
        task_priority: "MEDIUM",
        task_due_days: 2,
      },
    ]);
  }

  function removeAction(id: string) {
    setActions((prev) => prev.filter((a) => a.id !== id));
  }

  function updateAction(id: string, updates: Partial<ActionItem>) {
    setActions((prev) =>
      prev.map((a) => (a.id === id ? { ...a, ...updates } : a))
    );
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setErrorBanner("Workflow name is required.");
      return;
    }
    if (actions.length === 0) {
      setErrorBanner("At least one action step must be configured.");
      return;
    }

    setSaving(true);
    setErrorBanner(null);

    // Format conditions tree
    const formattedConditions =
      conditions.length > 0
        ? {
            logical_operator: logicalOperator,
            conditions: conditions.map((c) => {
              let parsedValue: any = c.value;
              if (
                c.operator === "GREATER_THAN" ||
                c.operator === "GREATER_THAN_OR_EQUAL" ||
                c.operator === "LESS_THAN" ||
                c.operator === "LESS_THAN_OR_EQUAL"
              ) {
                const n = parseFloat(c.value);
                if (!isNaN(n)) parsedValue = n;
              }
              return {
                field: c.field,
                operator: c.operator,
                value: parsedValue,
              };
            }),
          }
        : null;

    // Format actions
    const formattedActions = actions.map((a, idx) => ({
      action_type: a.action_type,
      step_index: idx,
      description: a.description,
      requires_approval: a.requires_approval,
      approval_role: a.approval_role,
      email_subject: a.email_subject,
      email_body_template: a.email_body_template,
      notification_title: a.notification_title,
      notification_message: a.notification_message,
      task_title: a.task_title,
      task_description: a.task_description,
      task_priority: a.task_priority,
      task_due_days: a.task_due_days,
      calendar_operation: a.calendar_operation,
      event_name: a.event_name,
    }));

    const payload = {
      name: name.trim(),
      description: description.trim() || null,
      trigger_type: triggerType,
      is_active: true,
      definition: {
        trigger_config: {},
        conditions: formattedConditions,
        actions: formattedActions,
      },
      change_summary: "Initial workflow definition",
    };

    try {
      await apiClient("/workflows", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      router.push("/workflows");
    } catch (err: any) {
      setErrorBanner("Failed to create workflow: " + err.message);
      setSaving(false);
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center justify-between border-b pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/workflows"
            className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Create Recruitment Workflow</h1>
            <p className="text-xs text-gray-500 mt-0.5">
              Configure event triggers, deterministic criteria, and automated sequences.
            </p>
          </div>
        </div>
      </div>

      {errorBanner && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-800 text-sm">
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
          <span>{errorBanner}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Basic Information */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex items-center gap-2 border-b pb-3">
            <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
              1
            </span>
            <h2 className="text-base font-semibold text-gray-900">Workflow Details & Trigger Event</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Workflow Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Auto-Ack High Match Candidates"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div className="sm:col-span-2">
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Description (Optional)
              </label>
              <textarea
                rows={2}
                placeholder="Brief summary of workflow objective..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-700 mb-1">
                Trigger Event *
              </label>
              <select
                value={triggerType}
                onChange={(e) => setTriggerType(e.target.value as WorkflowTriggerType)}
                className="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              >
                <option value="APPLICATION_SUBMITTED">Application Submitted</option>
                <option value="APPLICATION_STAGE_CHANGED">Application Stage Changed</option>
                <option value="CANDIDATE_CREATED">Candidate Created</option>
                <option value="RESUME_PROCESSED">Resume Processed</option>
                <option value="CANDIDATE_MATCHED">Candidate Matched to Job</option>
                <option value="INTERVIEW_SCHEDULED">Interview Scheduled</option>
                <option value="INTERVIEW_RESCHEDULED">Interview Rescheduled</option>
                <option value="INTERVIEW_COMPLETED">Interview Completed</option>
                <option value="FEEDBACK_SUBMITTED">Interview Feedback Submitted</option>
                <option value="CANDIDATE_INACTIVE">Candidate Inactive</option>
              </select>
              <p className="text-[11px] text-gray-400 mt-1">
                Workflow evaluates conditions immediately when this recruitment lifecycle event occurs.
              </p>
            </div>
          </div>
        </div>

        {/* Step 2: Deterministic Conditions */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                2
              </span>
              <h2 className="text-base font-semibold text-gray-900">Deterministic Condition Rules</h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">Combine logic:</span>
              <select
                value={logicalOperator}
                onChange={(e) => setLogicalOperator(e.target.value as "AND" | "OR")}
                className="text-xs font-semibold border border-gray-300 rounded px-2 py-1 bg-white"
              >
                <option value="AND">ALL conditions must match (AND)</option>
                <option value="OR">ANY condition may match (OR)</option>
              </select>
            </div>
          </div>

          <p className="text-xs text-gray-500">
            Rules are evaluated in a deterministic sandbox. If no rules are added, the workflow runs for all events.
          </p>

          <div className="space-y-3">
            {conditions.map((cond, idx) => (
              <div
                key={cond.id}
                className="flex flex-col sm:flex-row gap-2 items-start sm:items-center bg-gray-50 p-3 rounded-lg border border-gray-200"
              >
                <span className="text-xs font-bold text-gray-400 w-6">#{idx + 1}</span>

                {/* Field */}
                <div className="w-full sm:w-1/3">
                  <input
                    type="text"
                    placeholder="Field path (e.g. match_score)"
                    value={cond.field}
                    onChange={(e) => updateCondition(cond.id, { field: e.target.value })}
                    className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white font-mono"
                  />
                </div>

                {/* Operator */}
                <div className="w-full sm:w-1/3">
                  <select
                    value={cond.operator}
                    onChange={(e) =>
                      updateCondition(cond.id, { operator: e.target.value as ConditionOperator })
                    }
                    className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                  >
                    <option value="GREATER_THAN_OR_EQUAL">&gt;= (Greater or Equal)</option>
                    <option value="GREATER_THAN">&gt; (Greater Than)</option>
                    <option value="LESS_THAN_OR_EQUAL">&lt;= (Less or Equal)</option>
                    <option value="LESS_THAN">&lt; (Less Than)</option>
                    <option value="EQUALS">== (Equals)</option>
                    <option value="NOT_EQUALS">!= (Not Equals)</option>
                    <option value="CONTAINS">Contains (in text or skills list)</option>
                    <option value="NOT_CONTAINS">Does Not Contain</option>
                    <option value="EXISTS">Field Exists & Not Empty</option>
                    <option value="NOT_EXISTS">Field Does Not Exist</option>
                  </select>
                </div>

                {/* Value */}
                {cond.operator !== "EXISTS" && cond.operator !== "NOT_EXISTS" && (
                  <div className="w-full sm:w-1/3">
                    <input
                      type="text"
                      placeholder="Expected value (e.g. 75, Python)"
                      value={cond.value}
                      onChange={(e) => updateCondition(cond.id, { value: e.target.value })}
                      className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                    />
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => removeCondition(cond.id)}
                  className="p-1.5 text-gray-400 hover:text-red-600 transition"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}

            <button
              type="button"
              onClick={addCondition}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 pt-2"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Condition Rule
            </button>
          </div>
        </div>

        {/* Step 3: Sequential Actions */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex items-center justify-between border-b pb-3">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center">
                3
              </span>
              <h2 className="text-base font-semibold text-gray-900">Action Sequences</h2>
            </div>
            <span className="text-xs text-gray-400">
              Executed in order upon matching conditions
            </span>
          </div>

          <div className="space-y-4">
            {actions.map((act, idx) => (
              <div
                key={act.id}
                className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                      Step {idx + 1}
                    </span>
                    <span className="text-xs font-medium text-gray-700">
                      {act.action_type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeAction(act.id)}
                    className="p-1 text-gray-400 hover:text-red-600 transition"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                      Action Type
                    </label>
                    <select
                      value={act.action_type}
                      onChange={(e) =>
                        updateAction(act.id, {
                          action_type: e.target.value as WorkflowActionType,
                        })
                      }
                      className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                    >
                      <option value="SEND_CANDIDATE_COMMUNICATION">Send Candidate Email (Transactional Outbox)</option>
                      <option value="NOTIFY_RECRUITERS">Notify Assigned Recruiters (In-App Alert)</option>
                      <option value="CREATE_RECRUITER_TASK">Create Recruiter Follow-up Task</option>
                      <option value="GENERATE_INTERVIEW_PREP">Generate AI Interview Preparation Brief</option>
                      <option value="TRIGGER_CALENDAR_SYNC">Trigger Calendar Sync Job</option>
                      <option value="GENERATE_ANALYTICS_EVENT">Log Operational Analytics Event</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                      Step Description
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Send offer confirmation"
                      value={act.description}
                      onChange={(e) => updateAction(act.id, { description: e.target.value })}
                      className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                    />
                  </div>

                  {/* Config fields depending on action type */}
                  {act.action_type === "SEND_CANDIDATE_COMMUNICATION" && (
                    <>
                      <div className="sm:col-span-2">
                        <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                          Email Subject Template
                        </label>
                        <input
                          type="text"
                          placeholder="Application update for {{candidate_name}}"
                          value={act.email_subject || ""}
                          onChange={(e) => updateAction(act.id, { email_subject: e.target.value })}
                          className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                        />
                      </div>
                      <div className="sm:col-span-2">
                        <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                          Email Body Template
                        </label>
                        <textarea
                          rows={2}
                          placeholder="Dear {{candidate_name}}, we are reviewing your profile..."
                          value={act.email_body_template || ""}
                          onChange={(e) => updateAction(act.id, { email_body_template: e.target.value })}
                          className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                        />
                      </div>
                    </>
                  )}

                  {act.action_type === "NOTIFY_RECRUITERS" && (
                    <div className="sm:col-span-2">
                      <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                        Notification Message
                      </label>
                      <input
                        type="text"
                        placeholder="Candidate has reached interview completed stage"
                        value={act.notification_message || ""}
                        onChange={(e) => updateAction(act.id, { notification_message: e.target.value })}
                        className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                      />
                    </div>
                  )}

                  {act.action_type === "CREATE_RECRUITER_TASK" && (
                    <>
                      <div>
                        <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                          Task Title
                        </label>
                        <input
                          type="text"
                          placeholder="Conduct preliminary technical review"
                          value={act.task_title || ""}
                          onChange={(e) => updateAction(act.id, { task_title: e.target.value })}
                          className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                        />
                      </div>
                      <div>
                        <label className="block text-[11px] font-semibold text-gray-600 mb-1">
                          Task Priority
                        </label>
                        <select
                          value={act.task_priority || "MEDIUM"}
                          onChange={(e) => updateAction(act.id, { task_priority: e.target.value as RecruiterTaskPriority })}
                          className="w-full text-xs border border-gray-300 rounded px-2.5 py-1.5 bg-white"
                        >
                          <option value="LOW">Low</option>
                          <option value="MEDIUM">Medium</option>
                          <option value="HIGH">High</option>
                          <option value="URGENT">Urgent</option>
                        </select>
                      </div>
                    </>
                  )}
                </div>

                {/* Human Approval Checkbox */}
                <div className="pt-2 border-t border-gray-200/80 flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={act.requires_approval}
                      onChange={(e) => updateAction(act.id, { requires_approval: e.target.checked })}
                      className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                    />
                    <span className="text-xs font-semibold text-gray-800">
                      Require Human Review & Approval before executing this step
                    </span>
                  </label>

                  {act.requires_approval && (
                    <div className="flex items-center gap-1.5 text-xs text-amber-700 bg-amber-50 border border-amber-200 px-2.5 py-1 rounded-md">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      Queues in /approvals
                    </div>
                  )}
                </div>
              </div>
            ))}

            <button
              type="button"
              onClick={addAction}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-800 pt-2"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Action Step
            </button>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t">
          <Link
            href="/workflows"
            className="px-4 py-2 text-xs font-semibold rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-50 transition"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition disabled:opacity-50 flex items-center gap-1.5"
          >
            {saving ? "Saving..." : "Save & Activate Workflow"}
          </button>
        </div>
      </form>
    </div>
  );
}

"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Calendar,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  RefreshCw,
  ExternalLink,
  Shield,
  Layers,
  Clock,
  ArrowRightLeft,
  ChevronRight,
  Info,
  Radio,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { CalendarConnection, CalendarItem, CalendarSyncLog } from "@/types";

export default function IntegrationsSettingsPage() {
  const [connections, setConnections] = useState<CalendarConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncLogs, setSyncLogs] = useState<CalendarSyncLog[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [selectedCalendars, setSelectedCalendars] = useState<Record<string, CalendarItem[]>>({});
  const [loadingCalsFor, setLoadingCalsFor] = useState<string | null>(null);
  const [message, setMessage] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  const fetchConnections = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiClient<CalendarConnection[]>("/integrations/calendars");
      setConnections(data);
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to load calendar integrations." });
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchLogs = useCallback(async () => {
    try {
      setLoadingLogs(true);
      const data = await apiClient<CalendarSyncLog[]>("/integrations/calendars/sync-logs?limit=30");
      setSyncLogs(data);
    } catch (err: any) {
      console.error("Failed to load sync logs:", err);
    } finally {
      setLoadingLogs(false);
    }
  }, []);

  useEffect(() => {
    fetchConnections();
    fetchLogs();
  }, [fetchConnections, fetchLogs]);

  // Handle OAuth initiate
  const handleConnect = async (provider: "GOOGLE" | "MICROSOFT") => {
    try {
      setConnectingProvider(provider);
      setMessage(null);
      const res = await apiClient<{ authorization_url: string; state: string }>(
        "/integrations/calendars/init",
        {
          method: "POST",
          body: JSON.stringify({ provider }),
        }
      );
      if (res.authorization_url) {
        // If mock or local provider url, simulate direct callback for testing
        if (res.authorization_url.includes("mock") || res.authorization_url.includes("hirelens.mock")) {
          // Direct callback exchange for test/dev
          await apiClient("/integrations/calendars/callback", {
            method: "POST",
            body: JSON.stringify({
              code: "mock_auth_code_flow",
              state: res.state,
            }),
          });
          setMessage({
            type: "success",
            text: `Successfully linked ${provider === "GOOGLE" ? "Google Calendar" : "Microsoft Outlook"}!`,
          });
          await fetchConnections();
          await fetchLogs();
        } else {
          // Redirect to real provider OAuth login
          window.location.href = res.authorization_url;
        }
      }
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || `Failed to initiate ${provider} connection.` });
    } finally {
      setConnectingProvider(null);
    }
  };

  const handleDisconnect = async (connId: string) => {
    if (!confirm("Are you sure you want to disconnect this calendar? Future interviews will not sync.")) return;
    try {
      setMessage(null);
      await apiClient(`/integrations/calendars/${connId}`, { method: "DELETE" });
      setMessage({ type: "info", text: "Calendar integration disconnected successfully." });
      await fetchConnections();
      await fetchLogs();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to disconnect calendar." });
    }
  };

  const handleManualSync = async (connId: string) => {
    try {
      setSyncingId(connId);
      setMessage(null);
      const res = await apiClient<{ status: string; enqueued_count: number }>(
        `/integrations/calendars/${connId}/sync`,
        { method: "POST" }
      );
      setMessage({
        type: "success",
        text: `Sync dispatched! Queued ${res.enqueued_count} interview event(s).`,
      });
      await fetchLogs();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Sync failed to start." });
    } finally {
      setSyncingId(null);
    }
  };

  const handleLoadCalendars = async (connId: string) => {
    try {
      setLoadingCalsFor(connId);
      const cals = await apiClient<CalendarItem[]>(`/integrations/calendars/${connId}/calendars`);
      setSelectedCalendars((prev) => ({ ...prev, [connId]: cals }));
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to load calendars list." });
    } finally {
      setLoadingCalsFor(null);
    }
  };

  const handleSelectCalendar = async (connId: string, calId: string, calName: string) => {
    try {
      await apiClient(`/integrations/calendars/${connId}/selection`, {
        method: "PATCH",
        body: JSON.stringify({ calendar_id: calId, calendar_name: calName }),
      });
      setMessage({ type: "success", text: `Target calendar updated to: ${calName}` });
      await fetchConnections();
    } catch (err: any) {
      setMessage({ type: "error", text: err.message || "Failed to update target calendar." });
    }
  };

  const googleConn = connections.find((c) => c.provider === "GOOGLE" && c.is_active);
  const msConn = connections.find((c) => c.provider === "MICROSOFT" && c.is_active);

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Calendar className="h-6 w-6 text-primary" />
            Calendar & External Integrations
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Connect Google Calendar and Microsoft Outlook for real-time interview scheduling, meeting links, and two-way sync.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => {
              fetchConnections();
              fetchLogs();
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-xs font-medium text-foreground hover:bg-muted transition"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>
        </div>
      </div>

      {/* Banner / Feedback Message */}
      {message && (
        <div
          className={`p-4 rounded-xl border flex items-start gap-3 transition ${
            message.type === "success"
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : message.type === "error"
              ? "bg-destructive/10 border-destructive/30 text-destructive-foreground"
              : "bg-blue-500/10 border-blue-500/30 text-blue-400"
          }`}
        >
          {message.type === "success" ? (
            <CheckCircle2 className="h-5 w-5 shrink-0 mt-0.5" />
          ) : message.type === "error" ? (
            <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
          ) : (
            <Info className="h-5 w-5 shrink-0 mt-0.5" />
          )}
          <span className="text-sm font-medium">{message.text}</span>
        </div>
      )}

      {/* Provider Connection Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Google Calendar Card */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm hover:shadow-md transition">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-500 font-bold text-xl">
                G
              </div>
              <div>
                <h3 className="font-semibold text-foreground text-base">Google Calendar</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Google Workspace & Personal</p>
              </div>
            </div>
            {googleConn ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" /> Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                Not Connected
              </span>
            )}
          </div>

          <div className="mt-4 pt-4 border-t border-border/60 text-xs text-muted-foreground space-y-2">
            <div className="flex justify-between">
              <span>Account:</span>
              <span className="font-medium text-foreground">{googleConn ? googleConn.provider_account_email || "Linked" : "—"}</span>
            </div>
            <div className="flex justify-between">
              <span>Selected Calendar:</span>
              <span className="font-medium text-foreground">{googleConn ? googleConn.selected_calendar_name : "—"}</span>
            </div>
            <div className="flex justify-between">
              <span>Google Meet Links:</span>
              <span className="text-emerald-400 font-medium">Supported</span>
            </div>
            {googleConn?.last_synced_at && (
              <div className="flex justify-between">
                <span>Last Synced:</span>
                <span className="font-mono text-muted-foreground">
                  {new Date(googleConn.last_synced_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST
                </span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex flex-wrap gap-2">
            {googleConn ? (
              <>
                <button
                  disabled={syncingId === googleConn.id}
                  onClick={() => handleManualSync(googleConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-xs font-medium transition"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${syncingId === googleConn.id ? "animate-spin" : ""}`} />
                  Sync Now
                </button>
                <button
                  onClick={() => handleLoadCalendars(googleConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-foreground text-xs font-medium transition"
                >
                  <Layers className="h-3.5 w-3.5" />
                  Select Calendar
                </button>
                <button
                  onClick={() => handleDisconnect(googleConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-medium transition ml-auto"
                >
                  Disconnect
                </button>
              </>
            ) : (
              <button
                disabled={connectingProvider === "GOOGLE"}
                onClick={() => handleConnect("GOOGLE")}
                className="w-full inline-flex justify-center items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition shadow"
              >
                {connectingProvider === "GOOGLE" ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="h-4 w-4" />
                )}
                Connect Google Calendar
              </button>
            )}
          </div>

          {/* Calendar Picker Dropdown if opened */}
          {googleConn && selectedCalendars[googleConn.id] && (
            <div className="mt-4 p-3 rounded-xl border border-border bg-muted/40 space-y-2">
              <p className="text-xs font-semibold text-foreground">Select Target Calendar:</p>
              {selectedCalendars[googleConn.id].map((cal) => (
                <button
                  key={cal.id}
                  onClick={() => handleSelectCalendar(googleConn.id, cal.id, cal.name)}
                  className={`w-full text-left px-3 py-1.5 rounded-lg text-xs flex items-center justify-between transition ${
                    googleConn.selected_calendar_id === cal.id
                      ? "bg-primary text-primary-foreground font-medium"
                      : "hover:bg-card text-foreground"
                  }`}
                >
                  <span>{cal.name}</span>
                  {cal.primary && <span className="text-[10px] opacity-80">(Primary)</span>}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Microsoft Outlook Card */}
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm hover:shadow-md transition">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-500 font-bold text-xl">
                M
              </div>
              <div>
                <h3 className="font-semibold text-foreground text-base">Microsoft Outlook</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Microsoft 365 & Exchange</p>
              </div>
            </div>
            {msConn ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <CheckCircle2 className="h-3 w-3" /> Connected
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-muted text-muted-foreground">
                Not Connected
              </span>
            )}
          </div>

          <div className="mt-4 pt-4 border-t border-border/60 text-xs text-muted-foreground space-y-2">
            <div className="flex justify-between">
              <span>Account:</span>
              <span className="font-medium text-foreground">{msConn ? msConn.provider_account_email || "Linked" : "—"}</span>
            </div>
            <div className="flex justify-between">
              <span>Selected Calendar:</span>
              <span className="font-medium text-foreground">{msConn ? msConn.selected_calendar_name : "—"}</span>
            </div>
            <div className="flex justify-between">
              <span>Microsoft Teams Links:</span>
              <span className="text-sky-400 font-medium">Supported</span>
            </div>
            {msConn?.last_synced_at && (
              <div className="flex justify-between">
                <span>Last Synced:</span>
                <span className="font-mono text-muted-foreground">
                  {new Date(msConn.last_synced_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} IST
                </span>
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="mt-6 flex flex-wrap gap-2">
            {msConn ? (
              <>
                <button
                  disabled={syncingId === msConn.id}
                  onClick={() => handleManualSync(msConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-xs font-medium transition"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${syncingId === msConn.id ? "animate-spin" : ""}`} />
                  Sync Now
                </button>
                <button
                  onClick={() => handleLoadCalendars(msConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card hover:bg-muted text-foreground text-xs font-medium transition"
                >
                  <Layers className="h-3.5 w-3.5" />
                  Select Calendar
                </button>
                <button
                  onClick={() => handleDisconnect(msConn.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-destructive/10 hover:bg-destructive/20 text-destructive text-xs font-medium transition ml-auto"
                >
                  Disconnect
                </button>
              </>
            ) : (
              <button
                disabled={connectingProvider === "MICROSOFT"}
                onClick={() => handleConnect("MICROSOFT")}
                className="w-full inline-flex justify-center items-center gap-2 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition shadow"
              >
                {connectingProvider === "MICROSOFT" ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <ExternalLink className="h-4 w-4" />
                )}
                Connect Microsoft Outlook
              </button>
            )}
          </div>

          {/* Calendar Picker Dropdown if opened */}
          {msConn && selectedCalendars[msConn.id] && (
            <div className="mt-4 p-3 rounded-xl border border-border bg-muted/40 space-y-2">
              <p className="text-xs font-semibold text-foreground">Select Target Calendar:</p>
              {selectedCalendars[msConn.id].map((cal) => (
                <button
                  key={cal.id}
                  onClick={() => handleSelectCalendar(msConn.id, cal.id, cal.name)}
                  className={`w-full text-left px-3 py-1.5 rounded-lg text-xs flex items-center justify-between transition ${
                    msConn.selected_calendar_id === cal.id
                      ? "bg-primary text-primary-foreground font-medium"
                      : "hover:bg-card text-foreground"
                  }`}
                >
                  <span>{cal.name}</span>
                  {cal.primary && <span className="text-[10px] opacity-80">(Primary)</span>}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Two-Way Conflict & Security Policy Card */}
      <div className="rounded-2xl border border-border bg-card/60 p-5 space-y-3">
        <h4 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          Two-Way Synchronization & Security Policy
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs text-muted-foreground leading-relaxed">
          <div className="p-3 rounded-xl bg-card border border-border">
            <p className="font-semibold text-foreground mb-1">Authoritative Source</p>
            HireLens AI remains the authoritative schedule. External calendar updates flow through conflict checking before approval.
          </div>
          <div className="p-3 rounded-xl bg-card border border-border">
            <p className="font-semibold text-foreground mb-1">Advisory Lock Protection</p>
            Concurrent recruiter rescheduling and external calendar changes acquire PostgreSQL advisory locks to guarantee zero double-bookings.
          </div>
          <div className="p-3 rounded-xl bg-card border border-border">
            <p className="font-semibold text-foreground mb-1">Encrypted at Rest</p>
            Refresh and access tokens are encrypted with AES Fernet keys and never transmitted to the browser or logged.
          </div>
        </div>
      </div>

      {/* Synchronization Audit Logs Table */}
      <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-sm">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-foreground text-sm flex items-center gap-2">
              <ArrowRightLeft className="h-4 w-4 text-primary" />
              Recent Synchronization Logs
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Live audit record of calendar event dispatches, inbound webhooks, and retry attempts.
            </p>
          </div>
          <button
            onClick={fetchLogs}
            disabled={loadingLogs}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-card text-xs font-medium text-foreground hover:bg-muted transition"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loadingLogs ? "animate-spin" : ""}`} />
            Refresh Logs
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/50 border-b border-border text-muted-foreground uppercase text-[10px] font-semibold tracking-wider">
              <tr>
                <th className="px-5 py-3">Timestamp (IST)</th>
                <th className="px-5 py-3">Direction</th>
                <th className="px-5 py-3">Operation</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Details / Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {syncLogs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-muted-foreground">
                    No synchronization activity recorded yet. Events synchronize automatically when interviews are scheduled.
                  </td>
                </tr>
              ) : (
                syncLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-muted/30 transition">
                    <td className="px-5 py-3 font-mono text-muted-foreground whitespace-nowrap">
                      {new Date(log.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 font-medium text-foreground">
                        {log.direction === "INBOUND" ? "📥 Inbound" : "📤 Outbound"}
                      </span>
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap font-mono">
                      {log.operation}
                    </td>
                    <td className="px-5 py-3 whitespace-nowrap">
                      {log.status === "SUCCESS" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          SUCCESS
                        </span>
                      )}
                      {log.status === "FAILED" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-destructive/10 text-destructive border border-destructive/20">
                          FAILED
                        </span>
                      )}
                      {log.status === "CONFLICT" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          CONFLICT
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-muted-foreground max-w-md truncate">
                      {log.details || log.error_message || "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

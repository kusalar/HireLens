"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Bell,
  CheckCheck,
  Calendar,
  FileText,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  Filter,
} from "lucide-react";
import { apiClient } from "@/lib/api";

interface NotificationItem {
  id: string;
  agency_id: string;
  recipient_user_id: string;
  notification_type: string;
  title: string;
  message: string;
  related_entity_type?: string;
  related_entity_id?: string;
  is_read: boolean;
  created_at: string;
  read_at?: string;
  created_at_ist?: string;
}

export default function NotificationsPage() {
  const router = useRouter();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadOnly, setUnreadOnly] = useState<boolean>(false);
  const [total, setTotal] = useState<number>(0);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(20);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        unread_only: unreadOnly ? "true" : "false",
      });
      const data: any = await apiClient(`/notifications?${query.toString()}`);
      setNotifications(data.items || []);
      setTotal(data.total || 0);
      setUnreadCount(data.unread_count || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load notifications.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, unreadOnly]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  const handleMarkAsRead = async (id: string) => {
    try {
      await apiClient(`/notifications/${id}/read`, { method: "PATCH" });
      setNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err: any) {
      setError(err.message || "Failed to mark as read.");
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient("/notifications/mark-all-read", { method: "POST" });
      setNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch (err: any) {
      setError(err.message || "Failed to mark all as read.");
    }
  };

  const getBadgeStyle = (type: string) => {
    switch (type) {
      case "INTERVIEW_SCHEDULED":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "INTERVIEW_CONFIRMED":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "INTERVIEW_RESCHEDULED":
        return "bg-amber-50 text-amber-700 border-amber-200";
      case "INTERVIEW_CANCELLED":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "INTERVIEW_COMPLETED":
        return "bg-purple-50 text-purple-700 border-purple-200";
      case "APPLICATION_STATUS_UPDATED":
        return "bg-indigo-50 text-indigo-700 border-indigo-200";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  const getEntityLink = (item: NotificationItem) => {
    if (item.related_entity_type === "interview" && item.related_entity_id) {
      return `/interviews/${item.related_entity_id}`;
    }
    if (item.related_entity_type === "application" && item.related_entity_id) {
      return `/applications/${item.related_entity_id}`;
    }
    return null;
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-50 text-blue-600 rounded-lg border border-blue-100 shadow-xs">
              <Bell className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-slate-900 tracking-tight">Notification Center</h1>
              <p className="text-sm text-slate-500 mt-0.5">
                Real-time alerts for interviews, candidate stage movements, and system notices.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="px-3.5 py-2 text-xs font-semibold bg-white border border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 shadow-xs transition-colors flex items-center space-x-1.5"
            >
              <CheckCheck className="w-4 h-4 text-blue-600" />
              <span>Mark All as Read ({unreadCount})</span>
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-slate-200 shadow-xs">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => {
              setUnreadOnly(false);
              setPage(1);
            }}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              !unreadOnly
                ? "bg-slate-900 text-white shadow-xs"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            All Notifications ({total})
          </button>
          <button
            onClick={() => {
              setUnreadOnly(true);
              setPage(1);
            }}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors flex items-center space-x-1.5 ${
              unreadOnly
                ? "bg-blue-600 text-white shadow-xs"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            <span>Unread</span>
            {unreadCount > 0 && (
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                unreadOnly ? "bg-white text-blue-700" : "bg-blue-100 text-blue-700"
              }`}>
                {unreadCount}
              </span>
            )}
          </button>
        </div>

        <div className="text-xs text-slate-500 flex items-center space-x-1 font-mono">
          <span>Page {page} of {totalPages}</span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-start space-x-2.5">
          <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-semibold">Error loading notifications</p>
            <p className="text-xs text-rose-700 mt-0.5">{error}</p>
          </div>
        </div>
      )}

      {/* Notification List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs divide-y divide-slate-100 overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-sm flex flex-col items-center">
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mb-3"></div>
            <span>Loading notifications...</span>
          </div>
        ) : notifications.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm flex flex-col items-center">
            <CheckCircle2 className="w-12 h-12 text-slate-300 mb-3" />
            <p className="text-base font-semibold text-slate-700">No notifications found</p>
            <p className="text-xs text-slate-400 mt-1 max-w-sm">
              {unreadOnly
                ? "You have marked all notifications as read."
                : "When candidates apply, interview rounds are scheduled, or stages advance, your notifications will appear here."}
            </p>
          </div>
        ) : (
          notifications.map((item) => {
            const linkHref = getEntityLink(item);
            return (
              <div
                key={item.id}
                className={`p-5 transition-colors hover:bg-slate-50/80 flex items-start justify-between space-x-4 ${
                  !item.is_read ? "bg-blue-50/25" : ""
                }`}
              >
                <div className="flex items-start space-x-3.5 min-w-0 flex-1">
                  <div className="mt-0.5 p-2 rounded-lg bg-slate-100 border border-slate-200/60 shrink-0 text-slate-600">
                    {item.notification_type.startsWith("INTERVIEW") ? (
                      <Calendar className="w-4 h-4 text-blue-600" />
                    ) : (
                      <FileText className="w-4 h-4 text-emerald-600" />
                    )}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                      <span className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wider ${getBadgeStyle(item.notification_type)}`}>
                        {item.notification_type.replace(/_/g, " ")}
                      </span>
                      {!item.is_read && (
                        <span className="w-2 h-2 rounded-full bg-blue-600 inline-block"></span>
                      )}
                      <span className="text-xs text-slate-400 font-mono">
                        {item.created_at_ist || ""}
                      </span>
                    </div>

                    <h3 className={`text-sm font-semibold mt-1.5 ${!item.is_read ? "text-slate-900" : "text-slate-800"}`}>
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                      {item.message}
                    </p>

                    {linkHref && (
                      <div className="mt-3">
                        <Link
                          href={linkHref}
                          className="inline-flex items-center space-x-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 transition-colors"
                        >
                          <span>
                            Open {item.related_entity_type === "interview" ? "Interview Workspace" : "Application"}
                          </span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </Link>
                      </div>
                    )}
                  </div>
                </div>

                <div className="shrink-0 flex items-center space-x-2">
                  {!item.is_read && (
                    <button
                      onClick={() => handleMarkAsRead(item.id)}
                      className="px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-md border border-slate-200 transition-colors"
                      title="Mark as read"
                    >
                      Mark read
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 rounded-xl border border-slate-200 shadow-xs">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center space-x-1"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Previous</span>
          </button>
          <span className="text-xs text-slate-500 font-mono">
            Page {page} of {totalPages} ({total} items)
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-xs font-medium border border-slate-300 rounded-lg text-slate-700 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center space-x-1"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

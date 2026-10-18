"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, CheckCheck, ExternalLink, Calendar, FileText, CheckCircle2 } from "lucide-react";
import { apiClient } from "@/lib/api";

interface NotificationItem {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  related_entity_type?: string;
  related_entity_id?: string;
  created_at_ist?: string;
}

export function NotificationBell() {
  const router = useRouter();
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const [recentNotifications, setRecentNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchUnreadCount = async () => {
    try {
      const data: any = await apiClient("/notifications/unread-count");
      setUnreadCount(data.unread_count || 0);
    } catch {
      // Ignore background error
    }
  };

  const fetchRecentNotifications = async () => {
    setLoading(true);
    try {
      const data: any = await apiClient("/notifications?page=1&page_size=5");
      setRecentNotifications(data.items || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      console.error("Failed to load notifications:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleDropdown = () => {
    if (!isOpen) {
      fetchRecentNotifications();
    }
    setIsOpen(!isOpen);
  };

  const handleMarkAsRead = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await apiClient(`/notifications/${id}/read`, { method: "PATCH" });
      setRecentNotifications((prev) =>
        prev.map((item) => (item.id === id ? { ...item, is_read: true } : item))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (err) {
      console.error("Error marking read:", err);
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await apiClient("/notifications/mark-all-read", { method: "POST" });
      setRecentNotifications((prev) => prev.map((item) => ({ ...item, is_read: true })));
      setUnreadCount(0);
    } catch (err) {
      console.error("Error marking all read:", err);
    }
  };

  const handleItemClick = (item: NotificationItem) => {
    if (!item.is_read) {
      apiClient(`/notifications/${item.id}/read`, { method: "PATCH" }).catch(() => {});
      setUnreadCount((prev) => Math.max(0, prev - 1));
    }
    setIsOpen(false);
    if (item.related_entity_type === "interview" && item.related_entity_id) {
      router.push(`/interviews/${item.related_entity_id}`);
    } else if (item.related_entity_type === "application" && item.related_entity_id) {
      router.push(`/applications/${item.related_entity_id}`);
    } else {
      router.push("/notifications");
    }
  };

  const getIconForType = (type: string) => {
    if (type.startsWith("INTERVIEW")) {
      return <Calendar className="w-3.5 h-3.5 text-blue-600" />;
    }
    return <FileText className="w-3.5 h-3.5 text-emerald-600" />;
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={toggleDropdown}
        className="relative p-2 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg transition-colors focus:outline-none"
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-rose-500 rounded-full shadow-xs animate-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-84 sm:w-96 bg-white rounded-xl shadow-xl border border-slate-200 z-50 overflow-hidden animate-in fade-in-50 duration-150">
          <div className="px-4 py-3 bg-slate-50 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-800 text-sm">Notifications</span>
              {unreadCount > 0 && (
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center space-x-1"
              >
                <CheckCheck className="w-3.5 h-3.5 mr-1" />
                <span>Mark all read</span>
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-slate-100">
            {loading ? (
              <div className="py-8 text-center text-slate-400 text-xs">Loading notifications...</div>
            ) : recentNotifications.length === 0 ? (
              <div className="py-8 text-center text-slate-400 text-xs flex flex-col items-center">
                <CheckCircle2 className="w-8 h-8 text-slate-300 mb-2" />
                <span>You are all caught up!</span>
              </div>
            ) : (
              recentNotifications.map((item) => (
                <div
                  key={item.id}
                  onClick={() => handleItemClick(item)}
                  className={`p-3.5 text-left cursor-pointer transition-colors hover:bg-slate-50 flex items-start space-x-3 ${
                    !item.is_read ? "bg-blue-50/40" : ""
                  }`}
                >
                  <div className="mt-0.5 p-1.5 rounded-lg bg-slate-100 shrink-0">
                    {getIconForType(item.notification_type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className={`text-xs font-semibold truncate ${!item.is_read ? "text-slate-900" : "text-slate-700"}`}>
                        {item.title}
                      </p>
                      {!item.is_read && (
                        <span className="w-2 h-2 rounded-full bg-blue-600 shrink-0 ml-1.5"></span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-600 line-clamp-2 mt-0.5 leading-relaxed">
                      {item.message}
                    </p>
                    <div className="flex items-center justify-between mt-1.5">
                      <span className="text-[10px] text-slate-400 font-mono">
                        {item.created_at_ist || ""}
                      </span>
                      {!item.is_read && (
                        <button
                          onClick={(e) => handleMarkAsRead(item.id, e)}
                          className="text-[10px] text-blue-600 hover:text-blue-800 font-medium"
                        >
                          Mark read
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="p-2.5 bg-slate-50 border-t border-slate-100 text-center">
            <Link
              href="/notifications"
              onClick={() => setIsOpen(false)}
              className="text-xs text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center space-x-1"
            >
              <span>View all notifications</span>
              <ExternalLink className="w-3 h-3 ml-0.5" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

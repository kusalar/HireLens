"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Briefcase,
  Users,
  GitCompare,
  Kanban,
  BarChart3,
  Settings,
  LogOut,
  Sparkles,
  Building,
  UserCheck,
  FileText,
  Calendar,
  Bell,
  Layers,
  GitFork,
  CheckSquare,
  ShieldCheck,
  TrendingUp,
  Lock,
  CreditCard,
  ShieldAlert,
} from "lucide-react";

import { apiClient } from "@/lib/api";
import { NotificationBell } from "@/components/NotificationBell";

const navigation = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Resumes", href: "/resumes", icon: FileText },
  { name: "Jobs", href: "/jobs", icon: Briefcase },
  { name: "Candidates", href: "/candidates", icon: Users },
  { name: "AI Matching", href: "/matching", icon: GitCompare },
  { name: "AI Copilot", href: "/copilot", icon: Sparkles },
  { name: "Pipeline", href: "/pipeline", icon: Kanban },
  { name: "Interviews", href: "/interviews", icon: Calendar },
  { name: "Workflows", href: "/workflows", icon: GitFork },
  { name: "Approvals", href: "/approvals", icon: ShieldCheck },
  { name: "Tasks", href: "/tasks", icon: CheckSquare },
  { name: "Notifications", href: "/notifications", icon: Bell },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Predictive AI", href: "/predictive-analytics", icon: TrendingUp },
  { name: "Integrations", href: "/settings/integrations", icon: Layers },
  { name: "Security & Governance", href: "/settings/security", icon: Lock },
  { name: "Subscription & Billing", href: "/settings/billing", icon: CreditCard },
  { name: "Agency Settings", href: "/settings", icon: Settings },
  { name: "Platform Super Admin", href: "/admin", icon: ShieldAlert, superAdminOnly: true },
];


export default function DashboardLayout({

  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<any>(null);
  const [agency, setAgency] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadUserAndAgency() {
      const token = localStorage.getItem("hirelens_access_token");
      if (!token) {
        router.push("/login");
        return;
      }

      try {
        const userData: any = await apiClient("/auth/me");
        setUser(userData);

        const agencyData: any = await apiClient("/agency/profile");
        setAgency(agencyData);
      } catch (err) {
        console.error("Auth error:", err);
        localStorage.removeItem("hirelens_access_token");
        router.push("/login");
      } finally {
        setLoading(false);
      }
    }

    loadUserAndAgency();
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("hirelens_access_token");
    localStorage.removeItem("hirelens_user");
    router.push("/login");
  };

  const isDemo = Boolean(user?.is_demo || agency?.is_demo || agency?.slug === "apex-talent-partners-demo");

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="flex items-center space-x-2 text-slate-500 text-sm font-medium">
          <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading HireLens workspace...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-800">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col fixed inset-y-0 z-30">
        {/* Brand */}
        <div className="h-16 px-6 flex items-center border-b border-slate-800/80">
          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 rounded-md bg-blue-600 flex items-center justify-center text-white shadow-sm">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <span className="font-bold text-white text-base tracking-tight">HireLens</span>
              <span className="ml-1 text-xs px-1.5 py-0.5 rounded bg-blue-900/60 text-blue-300 font-semibold uppercase">
                AI
              </span>
            </div>
          </div>
        </div>

        {/* Agency Switcher / Badge */}
        <div className="px-4 py-3 mx-3 my-3 rounded-lg bg-slate-800/60 border border-slate-700/60">
          <div className="flex items-center space-x-2.5">
            <Building className="w-4 h-4 text-slate-400 shrink-0" />
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-white truncate flex items-center">
                <span>{agency?.name || "My Agency"}</span>
              </p>
              <p className="text-[11px] text-slate-400 font-mono truncate">
                /{agency?.slug}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 space-y-1 overflow-y-auto">
          {navigation
            .filter((item: any) => !item.superAdminOnly || user?.is_platform_admin)
            .map((item: any) => {
              const isActive = pathname === item.href || (item.href !== "/dashboard" && pathname?.startsWith(item.href));
              const Icon = item.icon;
              const isSuper = item.superAdminOnly;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? isSuper ? "bg-purple-600 text-white shadow-sm" : "bg-blue-600 text-white shadow-sm"
                      : isSuper ? "text-purple-300 hover:bg-purple-900/40 hover:text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  <Icon className={`w-4 h-4 mr-3 ${isActive ? "text-white" : isSuper ? "text-purple-400" : "text-slate-400"}`} />
                  <span className="flex-1 truncate">{item.name}</span>
                  {isSuper && (
                    <span className="ml-auto text-[10px] font-bold uppercase tracking-wider bg-purple-500/30 text-purple-200 px-1.5 py-0.5 rounded border border-purple-400/40">
                      ADMIN
                    </span>
                  )}
                </Link>
              );
            })}
        </nav>


        {/* User Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/40">
          <div className="flex items-center justify-between">
            <div className="min-w-0 pr-2">
              <div className="flex items-center space-x-1.5">
                <p className="text-sm font-medium text-white truncate">{user?.full_name}</p>
                {isDemo && (
                  <span className="text-[10px] font-mono uppercase bg-amber-500/30 text-amber-200 px-1.5 py-0.5 rounded border border-amber-400/40 font-bold shrink-0">
                    DEMO
                  </span>
                )}
              </div>
              <div className="flex items-center space-x-1.5 mt-0.5">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${isDemo ? "bg-amber-400" : "bg-emerald-500"}`}></span>
                <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">
                  {isDemo ? "Demo Recruiter" : user?.role}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col pl-64 min-w-0">
        <header className="h-16 bg-white border-b border-slate-200/80 px-8 flex items-center justify-between sticky top-0 z-20 shadow-xs">
          <div className="flex items-center space-x-3">
            <h2 className="text-base font-semibold text-slate-800">
              {navigation.find((i) => pathname === i.href)?.name || "Dashboard"}
            </h2>
          </div>
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <div className="h-6 w-px bg-slate-200"></div>
            <div className="text-right">
              <span className="text-xs text-slate-500 block">Workspace Mode</span>
              <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                isDemo
                  ? "text-amber-800 bg-amber-50 border-amber-300"
                  : "text-emerald-700 bg-emerald-50 border-emerald-200"
              }`}>
                {isDemo ? "✨ Live Demo Mode" : "Tenant Isolated"}
              </span>
            </div>
          </div>
        </header>

        {/* Prominent Demo Mode Banner */}
        {isDemo && (
          <div className="bg-gradient-to-r from-amber-500/10 via-blue-500/5 to-amber-500/10 border-b border-amber-200/80 px-8 py-2.5 flex flex-wrap items-center justify-between text-xs text-slate-800">
            <div className="flex items-center space-x-2">
              <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
              <span className="font-semibold text-amber-900 uppercase tracking-wide">Live Demo Mode:</span>
              <span className="text-slate-700">
                Exploring <strong>Apex Talent Partners</strong> with synthetic candidates, jobs & deterministic AI scoring. Core sample records are write-protected.
              </span>
            </div>
            <span className="hidden md:inline-flex items-center space-x-1 font-mono bg-white/90 text-amber-900 px-2.5 py-0.5 rounded text-[11px] font-semibold border border-amber-300 shadow-2xs">
              <span>Dev Week 2 Evaluator Session</span>
            </span>
          </div>
        )}

        <main className="flex-1 p-8 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Sparkles, ArrowRight, ShieldCheck, CheckCircle2, Loader2 } from "lucide-react";
import { apiClient } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [demoLaunching, setDemoLaunching] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("hirelens_access_token");
    if (token) {
      router.push("/dashboard");
    } else {
      setChecking(false);
    }
  }, [router]);

  const handleLaunchDemo = async () => {
    setDemoLaunching(true);
    try {
      const response: any = await apiClient("/auth/demo-session", {
        method: "POST",
      });
      if (response.tokens?.access_token) {
        localStorage.setItem("hirelens_access_token", response.tokens.access_token);
        localStorage.setItem("hirelens_user", JSON.stringify(response.user));
        router.push("/dashboard");
      } else {
        router.push("/login");
      }
    } catch (e) {
      router.push("/login");
    } finally {
      setDemoLaunching(false);
    }
  };

  if (checking) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col justify-between">
      {/* Navigation bar */}
      <nav className="border-b border-slate-200/80 bg-white/80 backdrop-blur-sm sticky top-0 z-10 px-6 py-4 flex items-center justify-between max-w-7xl mx-auto w-full">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-slate-900 flex items-center justify-center text-white shadow-sm">
            <Sparkles className="w-4 h-4 text-blue-400" />
          </div>
          <span className="font-bold text-slate-900 text-lg tracking-tight">HireLens AI</span>
        </div>

        <div className="flex items-center space-x-3">
          <button
            type="button"
            onClick={handleLaunchDemo}
            disabled={demoLaunching}
            className="text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200/80 px-3 py-1.5 rounded-md flex items-center space-x-1.5 transition-colors"
          >
            {demoLaunching ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5 text-blue-600" />
                <span>Live Demo</span>
              </>
            )}
          </button>
          <Link
            href="/login"
            className="text-sm font-medium text-slate-700 hover:text-slate-900 px-3 py-2 rounded-md transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/register"
            className="text-sm font-medium bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md shadow-xs transition-colors"
          >
            Register Agency
          </Link>
        </div>
      </nav>

      {/* Main Hero */}
      <main className="max-w-4xl mx-auto px-6 py-20 text-center flex flex-col items-center">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-xs font-semibold text-blue-700 mb-6">
          <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
          <span>Multi-Tenant Recruitment Intelligence SaaS</span>
        </div>

        <h1 className="text-4xl md:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight max-w-3xl">
          Find the right candidate. <br />
          <span className="text-blue-600">Not just the right keywords.</span>
        </h1>

        <p className="mt-5 text-base md:text-lg text-slate-600 max-w-2xl leading-relaxed">
          HireLens AI assists recruitment agencies with open-weight resume intelligence, explainable skill matching, and pipeline tracking — without replacing human judgment.
        </p>

        <div className="mt-8 flex flex-col sm:flex-row items-center gap-4">
          <button
            type="button"
            onClick={handleLaunchDemo}
            disabled={demoLaunching}
            className="px-6 py-3 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm flex items-center space-x-2 shadow-sm transition-all disabled:opacity-50"
          >
            {demoLaunching ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-blue-200" />
                <span>Explore Live Demo (1-Click)</span>
              </>
            )}
          </button>
          <Link
            href="/register"
            className="px-6 py-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-white font-medium text-sm flex items-center space-x-2 shadow-sm transition-all"
          >
            <span>Launch Agency Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/login"
            className="px-6 py-3 rounded-lg bg-white border border-slate-300 hover:bg-slate-50 text-slate-800 font-medium text-sm shadow-xs transition-all"
          >
            <span>Recruiter Sign In</span>
          </Link>
        </div>

        {/* Core Principles Grid */}
        <div className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 text-left w-full">
          <div className="p-5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
            <CheckCircle2 className="w-5 h-5 text-blue-600 mb-2" />
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Explainable Matching</h3>
            <p className="text-xs text-slate-500">
              Deterministic scoring and explicit evidence tracking. No black-box automated rejections.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
            <CheckCircle2 className="w-5 h-5 text-blue-600 mb-2" />
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Tenant Isolation</h3>
            <p className="text-xs text-slate-500">
              Strict database isolation. Recruiter jobs and candidate resumes are securely protected.
            </p>
          </div>

          <div className="p-5 rounded-xl bg-white border border-slate-200/80 shadow-xs">
            <CheckCircle2 className="w-5 h-5 text-blue-600 mb-2" />
            <h3 className="text-sm font-semibold text-slate-900 mb-1">Open-Weight AI</h3>
            <p className="text-xs text-slate-500">
              Modular integration with local Ollama or hosted inference for sovereign data processing.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200/80 bg-white py-6 px-6 text-center text-xs text-slate-500">
        <p>© 2026 HireLens AI. Enterprise recruitment intelligence and applicant tracking.</p>
      </footer>
    </div>
  );
}

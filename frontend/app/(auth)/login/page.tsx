"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ShieldCheck, ArrowRight, Loader2, Sparkles } from "lucide-react";
import { apiClient } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const response: any = await apiClient("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      if (response.tokens?.access_token) {
        localStorage.setItem("hirelens_access_token", response.tokens.access_token);
        localStorage.setItem("hirelens_user", JSON.stringify(response.user));
        router.push("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100/60 p-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border border-slate-200/80 p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="h-11 w-11 rounded-lg bg-slate-900 flex items-center justify-center text-white mb-3 shadow-inner">
            <Sparkles className="w-6 h-6 text-blue-400" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Sign in to HireLens AI</h1>
          <p className="text-sm text-slate-500 mt-1">Recruitment Intelligence & Applicant Tracking</p>
        </div>

        {error && (
          <div className="mb-5 p-3 rounded-md bg-red-50 border border-red-200 text-sm text-red-700">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Work Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="recruiter@agency.com"
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 text-slate-900"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Password
              </label>
              <a href="#" className="text-xs text-blue-600 hover:underline">
                Forgot password?
              </a>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full px-3 py-2 text-sm bg-white border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-blue-600 text-slate-900"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full mt-2 py-2.5 px-4 bg-slate-900 hover:bg-slate-800 text-white font-medium text-sm rounded-md shadow flex items-center justify-center space-x-2 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <>
                <span>Sign in to Dashboard</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-slate-100 text-center">
          <p className="text-sm text-slate-600">
            New recruitment agency?{" "}
            <Link href="/register" className="font-semibold text-blue-600 hover:underline">
              Create an agency account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HireLens AI — Recruitment Intelligence SaaS",
  description: "Find the right candidate. Not just the right keywords.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 selection:bg-brand-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}

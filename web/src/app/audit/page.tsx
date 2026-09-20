"use client";

import Link from "next/link";
import { ShieldCheck, User, ArrowLeft, ArrowRight, LockKey } from "@phosphor-icons/react";
import { useAuth } from "@/lib/auth";
import AuditTab from "@/components/tabs/AuditTab";

export default function AuditPage() {
  const { user, isAdmin, loginAs, isLoaded } = useAuth();

  if (!isLoaded) {
    return (
      <section className="relative min-h-[calc(100vh-4.25rem)] overflow-hidden">
        <div className="mx-auto max-w-xl rounded-2xl border border-foreground/10 bg-background/50 p-12 mt-16 text-center animate-pulse font-mono text-xs text-muted-foreground">
          Verifying administrator permissions...
        </div>
      </section>
    );
  }

  return (
    <section className="relative min-h-[calc(100vh-4.25rem)] overflow-hidden">
      {/* Background grid */}
      <div className="hairline-grid opacity-75" />

      {/* Hero Header */}
      <div className="relative mx-auto w-full max-w-7xl px-6 pt-8 pb-4 sm:px-10 sm:pt-10">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-foreground/10 pb-5">
          <div>
            <div className="flex items-center gap-2 font-mono text-xs uppercase tracking-wider text-amber font-semibold">
              <ShieldCheck size={16} weight="bold" />
              <span>Institutional Oversight · SIH 2026 PS-26015</span>
            </div>
            <h1 className="mt-2 font-display text-3xl sm:text-5xl tracking-tight text-foreground">
              Statutory Audit & Governance Console
            </h1>
            <p className="mt-1 font-mono text-xs sm:text-sm text-muted-foreground">
              Immutable audit trail recording location searches, AI pipeline runs, satellite source switches, and security events.
            </p>
          </div>

          <div className="flex items-center gap-3 font-mono text-xs">
            <Link
              href="/try"
              className="inline-flex items-center gap-1.5 rounded-full border border-foreground/15 bg-background/80 px-4 py-2 text-foreground hover:border-foreground transition-all"
            >
              <ArrowLeft size={14} weight="bold" />
              <span>Operational Console</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="relative mx-auto w-full max-w-7xl px-4 py-6 sm:px-8 pb-20">
        {!user ? (
          /* Unauthenticated Gate */
          <div className="mx-auto max-w-xl rounded-2xl border border-amber/30 bg-background/95 p-8 text-center shadow-xl backdrop-blur-md">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-amber/15 text-amber">
              <LockKey size={24} weight="bold" />
            </div>
            <div className="mt-4 font-mono text-xs uppercase tracking-widest text-amber font-semibold">
              Restricted Area
            </div>
            <h2 className="mt-1 font-display text-2xl tracking-tight text-foreground">
              Admin Authentication Required
            </h2>
            <p className="mt-2 font-sans text-sm text-muted-foreground leading-relaxed">
              The Statutory Audit Console records sensitive geospatial queries and governance events. Please authenticate as an Administrator to review audit records.
            </p>
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => loginAs("admin")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-amber text-background px-6 py-2.5 font-sans text-sm font-semibold hover:bg-amber/90 transition-all cursor-pointer shadow-xs"
              >
                <ShieldCheck size={18} weight="bold" />
                <span>Enter as Admin</span>
              </button>
              <Link
                href="/try"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-foreground/15 bg-background px-5 py-2.5 font-sans text-sm text-foreground hover:bg-foreground/5 transition-all"
              >
                <span>Return to App</span>
              </Link>
            </div>
          </div>
        ) : !isAdmin ? (
          /* Official Role - Access Denied */
          <div className="mx-auto max-w-xl rounded-2xl border border-danger/30 bg-background/95 p-8 text-center shadow-xl backdrop-blur-md">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl bg-danger/15 text-danger">
              <LockKey size={24} weight="bold" />
            </div>
            <div className="mt-4 font-mono text-xs uppercase tracking-widest text-danger font-semibold">
              Access Restricted
            </div>
            <h2 className="mt-1 font-display text-2xl tracking-tight text-foreground">
              Administrator Privileges Required
            </h2>
            <p className="mt-2 font-sans text-sm text-muted-foreground leading-relaxed">
              You are currently authenticated as <strong className="text-foreground">{user.name}</strong> with the <strong className="text-sage">Official</strong> role. The Statutory Audit Console is reserved for Administrative Officers.
            </p>
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => loginAs("admin")}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-amber text-background px-6 py-2.5 font-sans text-sm font-semibold hover:bg-amber/90 transition-all cursor-pointer shadow-xs"
              >
                <ShieldCheck size={18} weight="bold" />
                <span>Switch to Admin Role</span>
              </button>
              <Link
                href="/try"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-foreground/15 bg-background px-5 py-2.5 font-sans text-sm text-foreground hover:bg-foreground/5 transition-all"
              >
                <span>Back to Operational Console</span>
              </Link>
            </div>
          </div>
        ) : (
          /* Admin Authenticated -> Render Audit Console */
          <div className="rounded-2xl border border-foreground/10 bg-background/60 p-4 sm:p-6 backdrop-blur-xs shadow-xs">
            <AuditTab />
          </div>
        )}
      </div>
    </section>
  );
}

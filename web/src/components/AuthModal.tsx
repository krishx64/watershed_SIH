"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ShieldCheck,
  User,
  LockKey,
  Buildings,
  IdentificationBadge,
  X,
  CheckCircle,
  ArrowRight,
  SignOut,
  SignIn,
} from "@phosphor-icons/react";
import { useAuth, type UserRole } from "@/lib/auth";
import { cn } from "@/lib/cn";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const { user, isAdmin, login, loginAs, logout } = useAuth();
  const [tab, setTab] = useState<"quick" | "login">("quick");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  async function handlePasswordSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg(null);
    setSubmitting(true);
    const res = await login(username, password);
    setSubmitting(false);
    if (res.success) {
      onClose();
    } else {
      setErrorMsg(res.error || "Authentication failed");
    }
  }

  async function handleQuickSwitch(role: UserRole) {
    setSubmitting(true);
    await loginAs(role);
    setSubmitting(false);
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/30 p-4 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-lg rounded-2xl border border-foreground/15 bg-background/95 p-6 shadow-2xl backdrop-blur-md sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-foreground/15 bg-foreground/5 text-foreground">
              <ShieldCheck size={24} weight="bold" />
            </div>
            <div>
              <div className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Security & Institutional Access
              </div>
              <h2 className="font-display text-2xl tracking-tight text-foreground">
                Officer Authentication
              </h2>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-foreground/5 hover:text-foreground transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X size={18} weight="bold" />
          </button>
        </div>

        {/* Current Active Officer Profile or Unauthenticated Alert */}
        {user ? (
          <div className="mt-5 rounded-xl border border-foreground/10 bg-foreground/[0.03] p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
                Active Officer Session
              </span>
              <span
                className={cn(
                  "rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider border",
                  isAdmin
                    ? "border-amber/40 bg-amber/15 text-amber"
                    : "border-sage/40 bg-sage/15 text-sage"
                )}
              >
                {isAdmin ? "Admin (Statutory Auditor)" : "Official (Field Operations)"}
              </span>
            </div>
            <div className="mt-2.5 flex items-center justify-between gap-3">
              <div className="flex items-center gap-3 min-w-0 flex-1">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-foreground/10 text-foreground font-mono text-sm font-semibold">
                  <User size={18} weight="bold" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate font-sans text-sm font-semibold text-foreground">
                    {user.name}
                  </div>
                  <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground truncate">
                    <Buildings size={12} />
                    <span className="truncate">{user.department || "PMKSY Operations"}</span>
                    {user.badge_id && (
                      <>
                        <span>·</span>
                        <IdentificationBadge size={12} />
                        <span>{user.badge_id}</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {/* Direct Logout Button */}
              <button
                type="button"
                onClick={() => {
                  logout();
                  onClose();
                }}
                className="shrink-0 flex items-center gap-1.5 rounded-lg border border-danger/30 bg-danger/10 px-3 py-1.5 font-mono text-xs text-danger hover:bg-danger/20 transition-colors cursor-pointer"
                title="Log out of session"
              >
                <SignOut size={14} weight="bold" />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-5 rounded-xl border border-amber/30 bg-amber/5 p-4">
            <div className="flex items-center gap-2 text-amber font-mono text-xs font-semibold uppercase tracking-wider">
              <ShieldCheck size={16} weight="bold" />
              <span>Authentication Required</span>
            </div>
            <p className="mt-1 font-sans text-xs text-muted-foreground">
              Entry is restricted. Choose an institutional role below or log in with credentials to enter Watershed Signal.
            </p>
          </div>
        )}

        {/* Mode Selector Tabs */}
        <div className="mt-6 flex border-b border-foreground/10">
          <button
            type="button"
            onClick={() => setTab("quick")}
            className={cn(
              "border-b-2 px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors cursor-pointer",
              tab === "quick"
                ? "border-foreground text-foreground font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            1-Click Role Login
          </button>
          <button
            type="button"
            onClick={() => setTab("login")}
            className={cn(
              "border-b-2 px-4 py-2 font-mono text-xs uppercase tracking-wider transition-colors cursor-pointer",
              tab === "login"
                ? "border-foreground text-foreground font-semibold"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            Sign In with Password
          </button>
        </div>

        {/* Tab 1: 1-Click Role Login */}
        {tab === "quick" && (
          <div className="mt-5 space-y-3">
            <p className="font-mono text-xs text-muted-foreground">
              {user
                ? "Switch active session role without re-entering credentials:"
                : "Select an institutional role to log in and unlock access:"}
            </p>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleQuickSwitch("official")}
              className={cn(
                "w-full flex items-center justify-between rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                user?.role === "official"
                  ? "border-sage/50 bg-sage/10 shadow-xs"
                  : "border-foreground/15 bg-background hover:bg-foreground/5 hover:border-foreground/30"
              )}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sage/20 text-sage">
                  <User size={18} weight="bold" />
                </div>
                <div>
                  <div className="flex items-center gap-2 font-sans text-sm font-semibold text-foreground">
                    <span>Official Role</span>
                    {user?.role === "official" && (
                      <span className="rounded-full bg-sage/20 px-2 py-0.2 font-mono text-[9px] font-bold text-sage uppercase">
                        Current
                      </span>
                    )}
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    Full access to 9 operational watershed tabs, satellite imagery & AI models
                  </div>
                </div>
              </div>
              {user?.role === "official" ? (
                <CheckCircle size={18} weight="bold" className="text-sage" />
              ) : (
                <div className="flex items-center gap-1 font-mono text-xs text-sage font-semibold">
                  <span>Enter</span>
                  <ArrowRight size={13} weight="bold" />
                </div>
              )}
            </button>

            <button
              type="button"
              disabled={submitting}
              onClick={() => handleQuickSwitch("admin")}
              className={cn(
                "w-full flex items-center justify-between rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                isAdmin
                  ? "border-amber/50 bg-amber/10 shadow-xs"
                  : "border-foreground/15 bg-background hover:bg-foreground/5 hover:border-foreground/30"
              )}
            >
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-amber/20 text-amber">
                  <ShieldCheck size={18} weight="bold" />
                </div>
                <div>
                  <div className="flex items-center gap-2 font-sans text-sm font-semibold text-foreground">
                    <span>Admin Role</span>
                    <span className="rounded-full bg-amber/20 px-2 py-0.2 font-mono text-[9px] font-bold text-amber uppercase">
                      Unlocks Audit Console
                    </span>
                  </div>
                  <div className="font-mono text-xs text-muted-foreground">
                    All official features + exclusive Statutory Audit Console & telemetry export
                  </div>
                </div>
              </div>
              {isAdmin ? (
                <CheckCircle size={18} weight="bold" className="text-amber" />
              ) : (
                <div className="flex items-center gap-1 font-mono text-xs text-amber font-semibold">
                  <span>Enter</span>
                  <ArrowRight size={13} weight="bold" />
                </div>
              )}
            </button>
          </div>
        )}

        {/* Tab 2: Custom Credentials */}
        {tab === "login" && (
          <form onSubmit={handlePasswordSubmit} className="mt-5 space-y-4">
            {errorMsg && (
              <div className="rounded-xl border border-danger/30 bg-danger/10 p-3 font-mono text-xs text-danger">
                {errorMsg}
              </div>
            )}
            <div>
              <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                Username
              </label>
              <div className="relative">
                <User size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin or official"
                  className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                />
              </div>
            </div>

            <div>
              <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                Password
              </label>
              <div className="relative">
                <LockKey size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="admin123 or official123"
                  className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-foreground text-background py-2.5 font-sans text-sm font-semibold hover:bg-foreground/90 transition-colors cursor-pointer"
            >
              <SignIn size={16} weight="bold" />
              <span>{submitting ? "Authenticating..." : "Sign In with Credentials"}</span>
            </button>
          </form>
        )}

        {/* Footer Actions */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-foreground/10 pt-4 font-mono text-xs">
          <Link
            href="/register"
            onClick={onClose}
            className="inline-flex items-center gap-1.5 text-foreground hover:underline font-semibold"
          >
            <span>Create New Officer Profile</span>
            <ArrowRight size={13} weight="bold" />
          </Link>

          {user && (
            <button
              type="button"
              onClick={() => {
                logout();
                onClose();
              }}
              className="inline-flex items-center gap-1 text-muted-foreground hover:text-danger cursor-pointer transition-colors"
            >
              <SignOut size={14} />
              <span>Log Out</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

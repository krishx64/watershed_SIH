"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  UserPlus,
  ShieldCheck,
  User,
  Buildings,
  IdentificationBadge,
  EnvelopeSimple,
  LockKey,
  Key,
  CheckCircle,
  ArrowRight,
  ArrowLeft,
} from "@phosphor-icons/react";
import { useAuth, type UserRole } from "@/lib/auth";
import { cn } from "@/lib/cn";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [name, setName] = useState("");
  const [department, setDepartment] = useState("WDC-PMKSY Technical Operations");
  const [badgeId, setBadgeId] = useState("");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [role, setRole] = useState<UserRole>("official");
  const [adminPasskey, setAdminPasskey] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMsg(null);

    if (password !== confirmPassword) {
      setErrorMsg("Passwords do not match");
      return;
    }

    if (role === "admin" && !adminPasskey.trim()) {
      setErrorMsg("Admin role registration requires the statutory authorization passkey");
      return;
    }

    setSubmitting(true);
    const res = await register({
      username: username.trim().toLowerCase(),
      password,
      name: name.trim(),
      email: email.trim(),
      department: department.trim(),
      badge_id: badgeId.trim(),
      role,
      admin_passkey: adminPasskey.trim(),
    });
    setSubmitting(false);

    if (!res.success) {
      setErrorMsg(res.error || "Failed to create officer profile");
    } else {
      setSuccessMsg("Officer profile registered successfully. Redirecting to console...");
      setTimeout(() => {
        router.push("/try");
      }, 1200);
    }
  }

  return (
    <div className="relative min-h-[calc(100vh-4.25rem)] overflow-hidden py-12 px-6 sm:px-10">
      {/* Background hairline grid */}
      <div className="hairline-grid opacity-75" />

      {/* Subtle radial ambient lighting */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[500px] w-[1100px] rounded-full bg-foreground/[0.025] blur-3xl" />

      <div className="relative mx-auto w-full max-w-xl">
        {/* Back Link */}
        <Link
          href="/try"
          className="inline-flex items-center gap-1.5 font-mono text-xs text-muted-foreground hover:text-foreground transition-colors mb-6"
        >
          <ArrowLeft size={13} weight="bold" />
          <span>Back to Intelligence Console</span>
        </Link>

        {/* Card */}
        <div className="rounded-2xl border border-foreground/15 bg-background/90 p-8 shadow-xl backdrop-blur-md">
          <div className="flex items-center gap-3.5 border-b border-foreground/10 pb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-foreground/15 bg-foreground/5 text-foreground shadow-xs">
              <UserPlus size={24} weight="bold" />
            </div>
            <div>
              <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                Official Credential Registry
              </div>
              <h1 className="font-display text-3xl tracking-tight text-foreground">
                Create Officer Profile
              </h1>
            </div>
          </div>

          <p className="mt-4 font-sans text-sm text-muted-foreground leading-relaxed">
            Register your institutional profile with Watershed Signal to record geocoded field inspections, manage watershed interventions, and log statutory spatial analysis.
          </p>

          {errorMsg && (
            <div className="mt-5 rounded-xl border border-danger/30 bg-danger/10 p-3.5 font-mono text-xs text-danger">
              {errorMsg}
            </div>
          )}

          {successMsg && (
            <div className="mt-5 flex items-center gap-2 rounded-xl border border-sage/40 bg-sage/10 p-3.5 font-mono text-xs text-sage">
              <CheckCircle size={16} weight="bold" />
              <span>{successMsg}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-6 space-y-5">
            {/* Full Name & Department */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Full Name *
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Dr. Sunita Rao"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Officer / Badge ID
                </label>
                <div className="relative">
                  <IdentificationBadge size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="text"
                    value={badgeId}
                    onChange={(e) => setBadgeId(e.target.value)}
                    placeholder="e.g. GOI-WDC-4912"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                Department / Institutional Agency *
              </label>
              <div className="relative">
                <Buildings size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                <input
                  type="text"
                  required
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="e.g. WDC-PMKSY / State Remote Sensing Centre"
                  className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                />
              </div>
            </div>

            {/* Email & Username */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Institutional Email
                </label>
                <div className="relative">
                  <EnvelopeSimple size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="officer@pmksy.gov.in"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Account Username *
                </label>
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="e.g. srao_gis"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>
            </div>

            {/* Password & Confirm */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Password *
                </label>
                <div className="relative">
                  <LockKey size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Minimum 6 characters"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1.5">
                  Confirm Password *
                </label>
                <div className="relative">
                  <LockKey size={16} className="absolute left-3.5 top-3 text-muted-foreground" />
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    className="w-full rounded-xl border border-foreground/15 bg-background pl-10 pr-3.5 py-2 font-sans text-sm text-foreground focus:border-foreground focus:outline-hidden"
                  />
                </div>
              </div>
            </div>

            {/* Role Radio Selection */}
            <div>
              <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-2">
                Operational Access Role *
              </label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setRole("official")}
                  className={cn(
                    "flex flex-col rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                    role === "official"
                      ? "border-sage/50 bg-sage/10 shadow-xs ring-1 ring-sage/30"
                      : "border-foreground/15 bg-background hover:bg-foreground/5"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-sans text-sm font-semibold text-foreground">
                      Official Role
                    </span>
                    {role === "official" && <CheckCircle size={16} className="text-sage" weight="bold" />}
                  </div>
                  <span className="mt-1 font-mono text-[11px] text-muted-foreground">
                    Field surveys, satellite analysis, change detection, ground-truth logging.
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setRole("admin")}
                  className={cn(
                    "flex flex-col rounded-xl border p-3.5 text-left transition-all cursor-pointer",
                    role === "admin"
                      ? "border-amber/50 bg-amber/10 shadow-xs ring-1 ring-amber/30"
                      : "border-foreground/15 bg-background hover:bg-foreground/5"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-sans text-sm font-semibold text-foreground flex items-center gap-1.5">
                      <ShieldCheck size={16} className="text-amber" weight="bold" />
                      <span>Admin Role</span>
                    </span>
                    {role === "admin" && <CheckCircle size={16} className="text-amber" weight="bold" />}
                  </div>
                  <span className="mt-1 font-mono text-[11px] text-muted-foreground">
                    All official features + exclusive Statutory Audit Console & telemetry export.
                  </span>
                </button>
              </div>
            </div>

            {/* Admin Passkey field if role === 'admin' */}
            {role === "admin" && (
              <div className="rounded-xl border border-amber/30 bg-amber/5 p-4 animate-fade-in">
                <label className="block font-mono text-xs uppercase tracking-wider text-amber font-semibold mb-1.5 flex items-center gap-1.5">
                  <Key size={14} weight="bold" />
                  <span>Statutory Admin Authorization Passkey *</span>
                </label>
                <input
                  type="password"
                  required
                  value={adminPasskey}
                  onChange={(e) => setAdminPasskey(e.target.value)}
                  placeholder="Enter ADMIN_SIH_2026"
                  className="w-full rounded-xl border border-amber/40 bg-background px-3.5 py-2 font-mono text-sm text-foreground focus:border-amber focus:outline-hidden"
                />
                <p className="mt-1.5 font-mono text-[10px] text-muted-foreground">
                  Default evaluation passkey: <code className="text-amber font-bold">ADMIN_SIH_2026</code>
                </p>
              </div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={submitting}
              className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl bg-foreground text-background py-3 font-sans text-sm font-semibold hover:bg-foreground/90 transition-all cursor-pointer shadow-md"
            >
              <span>{submitting ? "Registering Profile..." : "Create Institutional Profile"}</span>
              <ArrowRight size={16} weight="bold" />
            </button>
          </form>

          {/* Quick Switch Helper */}
          <div className="mt-6 border-t border-foreground/10 pt-4 text-center font-mono text-xs text-muted-foreground">
            <span>Already have an account or testing locally? </span>
            <Link href="/try" className="text-foreground hover:underline font-semibold">
              Use Evaluation Quick Switch →
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}

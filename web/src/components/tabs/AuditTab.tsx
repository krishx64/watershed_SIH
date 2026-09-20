"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import {
  ShieldCheck,
  MagnifyingGlass,
  Database,
  ArrowsClockwise,
  CheckCircle,
  Warning,
  User,
  Clock,
  Sliders,
  MapPin,
  FileCode,
  FileCsv,
} from "@phosphor-icons/react";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/cn";

interface AuditLogEntry {
  timestamp: string;
  category: "search" | "pipeline" | "source_switch" | "ingestion" | "intervention" | "security" | string;
  action: string;
  user: string;
  user_name?: string;
  badge_id?: string;
  department?: string;
  role: string;
  details: Record<string, any>;
  status: "success" | "started" | "failed" | "rejected" | "fallback" | string;
  ip?: string;
}

interface AuditSummary {
  total_events: number;
  searches: number;
  pipeline_runs: number;
  ingestions: number;
  security_events: number;
  interventions: number;
  status: string;
  storage_mode: string;
}

export default function AuditTab() {
  const { token, isAdmin } = useAuth();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [summary, setSummary] = useState<AuditSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

  const fetchAuditLogs = useCallback(async () => {
    try {
      setError(null);
      const url = new URL("/api/audit-logs", window.location.origin);
      if (activeCategory !== "all") {
        url.searchParams.set("category", activeCategory);
      }
      if (searchQuery.trim()) {
        url.searchParams.set("q", searchQuery.trim());
      }
      url.searchParams.set("limit", "150");

      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch(url.toString(), { headers });
      if (!res.ok) {
        if (res.status === 403) {
          setError("Access Denied: Statutory Audit Console is restricted to Admin role.");
        } else {
          setError(`Server error ${res.status}: Failed to retrieve audit trail.`);
        }
        return;
      }
      const data = await res.json();
      setLogs(data.logs || []);
      setSummary(data.summary || null);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [token, activeCategory, searchQuery]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      if (!cancelled) await fetchAuditLogs();
    })();
    return () => { cancelled = true; };
  }, [fetchAuditLogs]);

  // Polling for auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      void fetchAuditLogs();
    }, 8000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchAuditLogs]);

  // Export handlers
  function handleExportJSON() {
    const blob = new Blob([JSON.stringify(logs, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `watershed_audit_log_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleExportCSV() {
    if (!logs.length) return;
    const headers = ["timestamp", "officer_name", "badge_id", "username", "role", "category", "action", "status", "ip", "details"];
    const rows = logs.map((l) => [
      l.timestamp,
      `"${l.user_name || (l.user === "admin" ? "Dr. Sunita Deshmukh" : l.user === "official" ? "Shri A. K. Sharma" : l.details?.name || l.user)}"`,
      l.badge_id || (l.user === "admin" ? "DIR-0001" : l.user === "official" ? "OFF-8821" : l.details?.badge_id || "OFF-GEN"),
      l.user,
      l.role,
      l.category,
      l.action,
      l.status,
      l.ip || "127.0.0.1",
      `"${JSON.stringify(l.details || {}).replace(/"/g, '""')}"`,
    ]);
    const csvContent = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `watershed_audit_log_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  const categoryCounts = useMemo(() => {
    return {
      all: summary?.total_events || logs.length,
      search: summary?.searches || logs.filter((l) => l.category === "search").length,
      pipeline: summary?.pipeline_runs || logs.filter((l) => l.category === "pipeline").length,
      ingestion: summary?.ingestions || logs.filter((l) => l.category === "ingestion").length,
      source_switch: logs.filter((l) => l.category === "source_switch").length,
      intervention: summary?.interventions || logs.filter((l) => l.category === "intervention").length,
      security: summary?.security_events || logs.filter((l) => l.category === "security").length,
    };
  }, [summary, logs]);

  if (!isAdmin) {
    return (
      <div className="rounded-2xl border border-danger/30 bg-danger/5 p-12 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-danger/10 text-danger mb-4">
          <Warning size={32} weight="bold" />
        </div>
        <h3 className="font-display text-2xl text-foreground tracking-tight">
          Admin Authorization Required
        </h3>
        <p className="mt-2 font-mono text-xs text-muted-foreground max-w-md mx-auto">
          The Statutory Audit Console tracks geospatial intelligence telemetry and requires administrative clearance. Please switch to the Admin role using the header selector to review audit records.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-foreground/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex h-2 w-2 rounded-full bg-amber animate-pulse" />
            <span className="font-mono text-xs uppercase tracking-wider text-amber font-semibold">
              Statutory Geospatial Audit & Telemetry Console
            </span>
          </div>
          <h2 className="font-display text-3xl sm:text-4xl tracking-tight text-foreground mt-1">
            System Ingestion & Access Audit Trail
          </h2>
          <p className="font-sans text-sm text-muted-foreground mt-1 max-w-2xl">
            Real-time immutable audit records tracking place name lookups, satellite raster requests, Resourcesat-2A vs Sentinel-2 ingestion, and officer access.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            type="button"
            onClick={fetchAuditLogs}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-xl border border-foreground/15 bg-background px-3.5 py-2 font-mono text-xs text-foreground hover:bg-foreground/5 transition-colors cursor-pointer"
            title="Refresh logs manually"
          >
            <ArrowsClockwise size={14} className={loading ? "animate-spin" : ""} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            onClick={() => setAutoRefresh(!autoRefresh)}
            className={cn(
              "flex items-center gap-1.5 rounded-xl border px-3.5 py-2 font-mono text-xs transition-colors cursor-pointer",
              autoRefresh
                ? "border-amber/40 bg-amber/10 text-amber font-medium"
                : "border-foreground/15 bg-background text-muted-foreground"
            )}
            title="Toggle 8-second live stream polling"
          >
            <span className={cn("h-1.5 w-1.5 rounded-full", autoRefresh ? "bg-amber" : "bg-muted-foreground")} />
            <span>{autoRefresh ? "Live Stream (8s)" : "Stream Paused"}</span>
          </button>

          <div className="h-6 w-px bg-foreground/10 mx-1 hidden sm:block" />

          <button
            type="button"
            onClick={handleExportCSV}
            className="flex items-center gap-1.5 rounded-xl border border-foreground/15 bg-background px-3.5 py-2 font-mono text-xs text-foreground hover:bg-foreground/5 transition-colors cursor-pointer"
            title="Export CSV audit log for official reporting"
          >
            <FileCsv size={15} />
            <span>CSV</span>
          </button>

          <button
            type="button"
            onClick={handleExportJSON}
            className="flex items-center gap-1.5 rounded-xl border border-foreground/15 bg-background px-3.5 py-2 font-mono text-xs text-foreground hover:bg-foreground/5 transition-colors cursor-pointer"
            title="Export JSON audit log"
          >
            <FileCode size={15} />
            <span>JSON</span>
          </button>
        </div>
      </div>

      {/* KPI Telemetry Cards */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Total Events</span>
            <ShieldCheck size={14} className="text-amber" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-foreground">
            {summary?.total_events || logs.length}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground truncate">
            {summary?.storage_mode || "Audit Ledger"}
          </div>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Searches</span>
            <MagnifyingGlass size={14} className="text-teal" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-teal">
            {categoryCounts.search}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground">
            Geocode queries
          </div>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Pipeline Runs</span>
            <Sliders size={14} className="text-foreground" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-foreground">
            {categoryCounts.pipeline}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground">
            Custom AOI runs
          </div>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Ingestions</span>
            <Database size={14} className="text-sage" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-sage">
            {categoryCounts.ingestion}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground">
            T0 / T1 / T2 cache
          </div>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Interventions</span>
            <MapPin size={14} className="text-foreground" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-foreground">
            {categoryCounts.intervention}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground">
            Field structures
          </div>
        </div>

        <div className="rounded-2xl border border-foreground/10 bg-background/60 backdrop-blur-md p-4 shadow-xs">
          <div className="flex items-center justify-between font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
            <span>Security</span>
            <User size={14} className="text-amber" />
          </div>
          <div className="mt-2 font-display text-2xl sm:text-3xl font-bold text-amber">
            {categoryCounts.security}
          </div>
          <div className="mt-1 font-mono text-[10px] text-muted-foreground">
            Logins & profiles
          </div>
        </div>
      </div>

      {/* Filter & Search Bar */}
      <div className="flex flex-col gap-3 rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-4 sm:flex-row sm:items-center sm:justify-between">
        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { id: "all", label: "All Logs" },
            { id: "search", label: "Search History" },
            { id: "pipeline", label: "Pipeline Requests" },
            { id: "ingestion", label: "Satellite Ingestion" },
            { id: "source_switch", label: "Source Toggles" },
            { id: "intervention", label: "Interventions" },
            { id: "security", label: "Security & Auth" },
          ].map((cat) => (
            <button
              key={cat.id}
              type="button"
              onClick={() => setActiveCategory(cat.id)}
              className={cn(
                "rounded-xl px-3 py-1.5 font-mono text-xs uppercase tracking-wider transition-colors cursor-pointer",
                activeCategory === cat.id
                  ? "bg-foreground text-background font-semibold shadow-xs"
                  : "bg-background border border-foreground/15 text-muted-foreground hover:text-foreground"
              )}
            >
              <span>{cat.label}</span>
              <span className="ml-1.5 opacity-60 text-[10px]">
                ({categoryCounts[cat.id as keyof typeof categoryCounts] ?? 0})
              </span>
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative min-w-[240px]">
          <MagnifyingGlass size={14} className="absolute left-3 top-2.5 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter by action, user, or AOI..."
            className="w-full rounded-xl border border-foreground/15 bg-background pl-8.5 pr-3 py-1.5 font-sans text-xs text-foreground focus:border-foreground focus:outline-hidden"
          />
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-danger/30 bg-danger/10 p-4 font-mono text-xs text-danger flex items-center gap-2">
          <Warning size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Log Feed Table */}
      <div className="overflow-hidden rounded-2xl border border-foreground/10 bg-background/80 shadow-sm backdrop-blur-md">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-sans">
            <thead className="border-b border-foreground/10 bg-foreground/[0.03] font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr>
                <th className="py-3 px-4">Timestamp (UTC)</th>
                <th className="py-3 px-4">Officer Name & ID</th>
                <th className="py-3 px-4">Action & Category</th>
                <th className="py-3 px-4">Event Payload / Context</th>
                <th className="py-3 px-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-foreground/5 font-sans">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center font-mono text-xs text-muted-foreground">
                    {loading ? "Streaming statutory audit trail..." : "No audit entries match the active filter criteria."}
                  </td>
                </tr>
              ) : (
                logs.map((entry, idx) => {
                  const dateObj = new Date(entry.timestamp);
                  const timeFormatted = isNaN(dateObj.getTime())
                    ? entry.timestamp
                    : dateObj.toLocaleTimeString("en-GB", { hour12: false }) + " " + dateObj.toLocaleDateString("en-GB");

                  const officerName =
                    entry.user_name ||
                    (entry.user === "admin"
                      ? "Dr. Sunita Deshmukh"
                      : entry.user === "official"
                      ? "Shri A. K. Sharma"
                      : entry.details?.name || entry.user);

                  const officerId =
                    entry.badge_id ||
                    (entry.user === "admin"
                      ? "DIR-0001"
                      : entry.user === "official"
                      ? "OFF-8821"
                      : entry.details?.badge_id || "OFF-GEN");

                  return (
                    <tr key={`${entry.timestamp}_${idx}`} className="hover:bg-foreground/[0.02] transition-colors">
                      {/* Timestamp */}
                      <td className="py-3 px-4 whitespace-nowrap font-mono text-xs text-muted-foreground">
                        <div className="flex items-center gap-1.5 text-foreground font-medium">
                          <Clock size={12} className="text-muted-foreground" />
                          <span>{timeFormatted}</span>
                        </div>
                        <div className="text-[10px] text-muted-foreground/80 mt-0.5">
                          IP: {entry.ip || "127.0.0.1"}
                        </div>
                      </td>

                      {/* Officer Name & ID */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex flex-col gap-1">
                          <div className="flex items-center gap-2">
                            <span className="font-sans font-semibold text-foreground text-xs">
                              {officerName}
                            </span>
                            <span
                              className={cn(
                                "rounded-full px-2 py-0.2 font-mono text-[9px] font-semibold uppercase tracking-wider border",
                                entry.role === "admin"
                                  ? "border-amber/40 bg-amber/15 text-amber"
                                  : entry.role === "official"
                                  ? "border-sage/40 bg-sage/15 text-sage"
                                  : "border-teal/40 bg-teal/15 text-teal"
                              )}
                            >
                              {entry.role}
                            </span>
                          </div>
                          <div className="flex items-center gap-1.5 font-mono text-[10px] text-muted-foreground">
                            <span className="rounded bg-foreground/5 px-1.5 py-0.2 font-medium text-foreground/80 border border-foreground/10">
                              {officerId}
                            </span>
                            <span>@{entry.user}</span>
                          </div>
                        </div>
                      </td>

                      {/* Action & Category */}
                      <td className="py-3 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 font-mono font-medium text-foreground">
                          {entry.category === "search" && <MagnifyingGlass size={13} className="text-teal" />}
                          {entry.category === "pipeline" && <Sliders size={13} className="text-foreground" />}
                          {entry.category === "ingestion" && <Database size={13} className="text-sage" />}
                          {entry.category === "source_switch" && <ArrowsClockwise size={13} className="text-amber" />}
                          {entry.category === "intervention" && <MapPin size={13} className="text-foreground" />}
                          {entry.category === "security" && <ShieldCheck size={13} className="text-amber" />}
                          <span>{entry.action}</span>
                        </div>
                        <span className="font-mono text-[10px] uppercase text-muted-foreground">
                          {entry.category}
                        </span>
                      </td>

                      {/* Context / Details */}
                      <td className="py-3 px-4">
                        <div className="max-w-md font-mono text-[11px] leading-relaxed text-foreground/90">
                          {entry.category === "search" && (
                            <div>
                              <span className="text-muted-foreground">Query: </span>
                              <strong className="text-foreground">{entry.details?.query}</strong>
                              {entry.details?.lat && (
                                <span className="text-muted-foreground ml-1">
                                  ({Number(entry.details.lat).toFixed(4)}, {Number(entry.details.lon).toFixed(4)})
                                </span>
                              )}
                            </div>
                          )}

                          {entry.category === "pipeline" && (
                            <div>
                              <span className="font-semibold text-foreground">{entry.details?.aoi_name || "Custom AOI"}</span>
                              <span className="text-muted-foreground ml-1.5">
                                · Radius: {entry.details?.radius_km || 2.0} km
                              </span>
                              {entry.details?.target_date && (
                                <span className="text-muted-foreground ml-1.5">
                                  · Date: {entry.details?.target_date}
                                </span>
                              )}
                            </div>
                          )}

                          {entry.category === "ingestion" && (
                            <div>
                              <span className="font-semibold text-foreground">{entry.details?.source || "Satellite"}</span>
                              <span className="text-muted-foreground ml-1.5">
                                · Tier {entry.details?.tier} ({entry.details?.latency_s}s)
                              </span>
                              {entry.details?.product_id && (
                                <div className="text-[10px] text-muted-foreground truncate">
                                  ID: {entry.details?.product_id}
                                </div>
                              )}
                            </div>
                          )}

                          {entry.category === "source_switch" && (
                            <div>
                              <span className="text-muted-foreground">Switched source for </span>
                              <strong>{entry.details?.site_key}</strong>
                              <span className="text-muted-foreground"> to </span>
                              <strong className="text-amber uppercase">{entry.details?.target_source}</strong>
                            </div>
                          )}

                          {entry.category === "intervention" && (
                            <div>
                              <span>Added structure: </span>
                              <strong className="text-foreground">{entry.details?.name}</strong>
                              <span className="text-muted-foreground ml-1">({entry.details?.type})</span>
                            </div>
                          )}

                          {entry.category === "security" && (
                            <div>
                              <span>{entry.details?.name ? `Officer: ${entry.details.name}` : entry.action}</span>
                              {entry.details?.department && (
                                <span className="text-muted-foreground ml-1">· {entry.details.department}</span>
                              )}
                            </div>
                          )}

                          {!["search", "pipeline", "ingestion", "source_switch", "intervention", "security"].includes(entry.category) && (
                            <span className="text-muted-foreground truncate block">
                              {JSON.stringify(entry.details)}
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status */}
                      <td className="py-3 px-4 whitespace-nowrap text-right">
                        <span
                          className={cn(
                            "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wider border",
                            entry.status === "success"
                              ? "border-sage/40 bg-sage/15 text-sage"
                              : entry.status === "started"
                              ? "border-amber/40 bg-amber/15 text-amber"
                              : entry.status === "fallback"
                              ? "border-teal/40 bg-teal/15 text-teal"
                              : "border-danger/40 bg-danger/15 text-danger"
                          )}
                        >
                          {entry.status === "success" && <CheckCircle size={10} weight="bold" />}
                          {entry.status === "rejected" && <Warning size={10} weight="bold" />}
                          <span>{entry.status}</span>
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

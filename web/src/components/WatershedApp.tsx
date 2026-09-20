"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/cn";
import { type SiteMeta } from "@/lib/watershed-data";
import Badge from "@/components/ui/Badge";
import Link from "next/link";
import { Radio, Check, X, Crosshair, ShieldCheck, User, LockKey, ArrowRight } from "@phosphor-icons/react";
import { useAuth } from "@/lib/auth";
import AuthModal from "@/components/AuthModal";
import LULCTab from "@/components/tabs/LULCTab";
import ChangeTab from "@/components/tabs/ChangeTab";
import HealthTab from "@/components/tabs/HealthTab";
import FieldTab from "@/components/tabs/FieldTab";
import InterventionsTab from "@/components/tabs/InterventionsTab";
import SimulatorTab from "@/components/tabs/SimulatorTab";
import ValidationTab from "@/components/tabs/ValidationTab";
import BhuvanReportTab from "@/components/tabs/BhuvanReportTab";
import AuditTab from "@/components/tabs/AuditTab";
import LocationPicker, { type CustomLocation } from "@/components/LocationPicker";

const MapTab = dynamic(() => import("@/components/tabs/MapTab"), {
  ssr: false,
  loading: () => <div className="aspect-square w-full animate-pulse rounded-2xl bg-foreground/5" />,
});

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000"
)
  .trim()
  .replace(/\/$/, "");

const TABS = [
  { key: "land-cover", label: "Land Cover", needsChangePair: false },
  { key: "change", label: "Change", needsChangePair: true },
  { key: "health", label: "Health & Alerts", needsChangePair: true },
  { key: "map", label: "Map", needsChangePair: false },
  { key: "field", label: "Field Investigation", needsChangePair: false },
  { key: "investigation", label: "Investigation", needsChangePair: false },
  { key: "bhuvan-report", label: "ISRO Bhuvan Report", needsChangePair: false, highlight: true },
  { key: "validation", label: "Scientific Validation", needsChangePair: false },
  { key: "simulator", label: "What-If Simulator", needsChangePair: false },
  { key: "audit", label: "Statutory Audit", needsChangePair: false, adminOnly: true, highlight: true },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function WatershedApp() {
  const { user, isAdmin, token, loginAs, isLoaded } = useAuth();
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [siteKey, setSiteKey] = useState<string>("custom_live");
  const [customLocation, setCustomLocation] = useState<CustomLocation | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [completedInfo, setCompletedInfo] = useState<{
    siteName: string;
    duration: number;
    timestamp: string;
  } | null>(null);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [cancelNotice, setCancelNotice] = useState<string | null>(null);
  const [meta, setMeta] = useState<SiteMeta | null>(null);
  const [activeSource, setActiveSource] = useState<"sentinel" | "bhoonidhi">("sentinel");
  const [bhoonidhiAvailable, setBhoonidhiAvailable] = useState(false);
  const [bhoonidhiMeta, setBhoonidhiMeta] = useState<SiteMeta | null>(null);
  const [isSwitchingSource, setIsSwitchingSource] = useState(false);
  const [dismissedBhoonidhiNotice, setDismissedBhoonidhiNotice] = useState(false);
  const [sourceVersion, setSourceVersion] = useState(Date.now());
  const [tab, setTab] = useState<TabKey>("land-cover");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Available tabs filtered strictly by administrative authorization
  const availableTabs = useMemo(() => {
    return TABS.filter((t) => !("adminOnly" in t && t.adminOnly) || isAdmin);
  }, [isAdmin]);

  // Synchronize ?tab=audit URL parameter if authorized
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("tab") === "audit" && isAdmin) {
        setTab("audit");
      }
    }
  }, [isAdmin]);

  // Demote to default tab if user role changes away from admin while viewing audit
  useEffect(() => {
    if (tab === "audit" && !isAdmin) {
      setTab("land-cover");
    }
  }, [isAdmin, tab]);

  // Timer for live satellite pipeline
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isAnalyzing) {
      setElapsedSeconds(0);
      timer = setInterval(() => {
        setElapsedSeconds((s) => s + 1);
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isAnalyzing]);

  // Ponytail Strategy 1 & 2: Asynchronous Bhoonidhi Ingestion Polling & Sovereign Ready Signal
  useEffect(() => {
    if (!meta || !siteKey || bhoonidhiAvailable || meta.bhoonidhi_status === "ready" || meta.bhoonidhi_status === "unavailable" || meta.bhoonidhi_status === "failed") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/pipeline/bhoonidhi-status?site_key=${encodeURIComponent(siteKey)}`);
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === "ready") {
          setBhoonidhiAvailable(true);
          if (data.bhoonidhi_meta) {
            setBhoonidhiMeta(data.bhoonidhi_meta);
          } else {
            const metaRes = await fetch(`${API_BASE_URL}/api/sites/${encodeURIComponent(siteKey)}?source=bhoonidhi&_t=${Date.now()}`);
            if (metaRes.ok) {
              const bMeta = await metaRes.json();
              setBhoonidhiMeta(bMeta);
            }
          }
          setMeta((prev) => prev ? { ...prev, bhoonidhi_status: "ready" } : prev);
          clearInterval(interval);
        } else if (data.status === "unavailable" || data.status === "failed") {
          setMeta((prev) => prev ? { ...prev, bhoonidhi_status: data.status } : prev);
          clearInterval(interval);
        }
      } catch {
        // Silent failover
      }
    }, 3500);

    return () => clearInterval(interval);
  }, [meta?.bhoonidhi_status, siteKey, bhoonidhiAvailable]);

  async function handleSwitchSource(target: "bhoonidhi" | "sentinel") {
    setIsSwitchingSource(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/pipeline/switch-source`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ site_key: siteKey, source: target }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.meta) {
          setMeta(data.meta);
          setActiveSource(target);
          setSourceVersion(Date.now());
          return;
        }
      }
      // Client-side fallback if server response wasn't 200
      if (target === "bhoonidhi" && bhoonidhiMeta) {
        setMeta(bhoonidhiMeta);
        setActiveSource("bhoonidhi");
        setSourceVersion(Date.now());
      }
    } catch (err) {
      console.error("Failed to switch raster source:", err);
      if (target === "bhoonidhi" && bhoonidhiMeta) {
        setMeta(bhoonidhiMeta);
        setActiveSource("bhoonidhi");
        setSourceVersion(Date.now());
      }
    } finally {
      setIsSwitchingSource(false);
    }
  }

  function handleCancelPipeline() {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    if (activeRunId) {
      fetch(`${API_BASE_URL}/api/pipeline/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ run_id: activeRunId }),
      }).catch(() => {});
    }
    setIsAnalyzing(false);
    setLoading(false);
    setLoadError(null);
    setCancelNotice("Pipeline analysis was cancelled by user.");
    setTimeout(() => setCancelNotice(null), 6000);
  }

  async function handleRunCustomPipeline(loc: CustomLocation) {
    // Cancel any in-flight pipeline run before starting a new one
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    const runId = "run_" + Date.now() + "_" + Math.random().toString(36).substring(2, 7);
    setActiveRunId(runId);
    setCancelNotice(null);
    setActiveSource("sentinel");
    setBhoonidhiAvailable(false);
    setBhoonidhiMeta(null);
    setDismissedBhoonidhiNotice(false);
    setSourceVersion(Date.now());

    setCustomLocation(loc);
    setIsAnalyzing(true);
    setCompletedInfo(null);
    setLoading(true);
    setLoadError(null);
    const startTime = Date.now();

    try {
      const res = await fetch(`${API_BASE_URL}/api/pipeline/run`, {
        method: "POST",
        signal: controller.signal,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          run_id: runId,
          lat: loc.lat,
          lon: loc.lon,
          name: loc.name,
          radius_km: loc.radiusKm || 2.0,
          target_date: loc.targetDate,
          t1_date: loc.t1Date,
          t2_date: loc.t2Date,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.error || `Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.status === "cancelled") {
        setIsAnalyzing(false);
        setLoading(false);
        return;
      }
      if (data.meta) {
        const totalDuration = Math.round((Date.now() - startTime) / 1000);
        setSiteKey(data.siteKey || "custom_live");
        setMeta(data.meta);
        setActiveSource(data.meta.active_source || (data.meta.primary_source?.includes("Bhoonidhi") ? "bhoonidhi" : "sentinel"));
        if (data.meta.bhoonidhi_status === "ready") {
          setBhoonidhiAvailable(true);
          setBhoonidhiMeta(data.meta);
        }
        setIsAnalyzing(false);
        setCompletedInfo({
          siteName: loc.name,
          duration: totalDuration,
          timestamp: new Date().toLocaleTimeString(),
        });
        setLoading(false);
        return;
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setIsAnalyzing(false);
        setLoading(false);
        return;
      }
      console.error("Live server execution failed:", err);
      setIsAnalyzing(false);
      setLoadError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  }

  const activeSiteName = customLocation?.name || meta?.display_name || "Selected Watershed AOI";

  // Pipeline stage computation based on elapsed seconds (calibrated for GPU acceleration)
  const currentStage =
    elapsedSeconds < 10
      ? {
          step: 1,
          label: "Querying Sentinel-2 L2A STAC Catalog",
          detail: "Searching Copernicus/AWS Open Data catalog for cloud-free (<20%) optical scenes...",
        }
      : elapsedSeconds < 22
      ? {
          step: 2,
          label: "Streaming & Clipping 10m Bands",
          detail: "Downloading Red, Green, Blue, NIR GeoTIFF COGs and computing NDVI / NDWI stacks...",
        }
      : elapsedSeconds < 28
      ? {
          step: 3,
          label: "Running Model 1 PyTorch U-Net on NVIDIA GPU",
          detail: "Segmenting 7 land-cover classes across multi-spectral tensors with RTX 3050 Tensor Cores...",
        }
      : {
          step: 4,
          label: "Hydrological Delineation & Change Matrix",
          detail:
            elapsedSeconds > 42
              ? "Running Pysheds flow routing on Copernicus 30m elevation grid & computing changes..."
              : "Ingesting Copernicus 30m DEM elevation tile (~35MB) & computing watershed drainage...",
        };

  if (!isLoaded) {
    return (
      <div className="mx-auto max-w-4xl rounded-3xl border border-foreground/10 bg-foreground/[0.02] p-16 text-center animate-pulse font-mono text-xs text-muted-foreground">
        Verifying institutional access credentials...
      </div>
    );
  }

  if (!user) {
    return (
      <div className="relative mx-auto max-w-4xl rounded-3xl border border-foreground/15 bg-background/95 p-8 sm:p-14 shadow-2xl backdrop-blur-md overflow-hidden animate-fade-up">
        {/* Corner architectural registration marks */}
        <span className="pointer-events-none absolute top-3.5 left-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
        <span className="pointer-events-none absolute top-3.5 right-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
        <span className="pointer-events-none absolute bottom-3.5 left-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
        <span className="pointer-events-none absolute bottom-3.5 right-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>

        <div className="flex flex-col items-center text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-foreground/15 bg-foreground/5 text-foreground shadow-xs">
            <LockKey size={30} weight="bold" />
          </div>

          <div className="mt-4 font-mono text-xs uppercase tracking-widest text-amber font-semibold">
            Institutional Access Control · SIH 2026 PS-26015
          </div>

          <h2 className="mt-2 font-display text-3xl sm:text-5xl tracking-tight text-foreground">
            Entry Restricted: Select Access Role
          </h2>

          <p className="mt-3 max-w-2xl font-sans text-sm sm:text-base text-muted-foreground leading-relaxed">
            Watershed Signal requires institutional authorization to access operational satellite rasters, DEM hydrology pipelines, and AI land-cover models. Choose an access role below to log in:
          </p>

          <div className="mt-8 grid w-full gap-5 sm:grid-cols-2 text-left">
            {/* Option 1: Official */}
            <div className="flex flex-col justify-between rounded-2xl border border-sage/40 bg-sage/5 p-6 sm:p-7 hover:border-sage hover:bg-sage/10 transition-all shadow-xs">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-sage/20 text-sage">
                    <User size={24} weight="bold" />
                  </div>
                  <span className="rounded-full bg-sage/20 px-2.5 py-0.5 font-mono text-[10px] font-bold text-sage uppercase">
                    Field Operations
                  </span>
                </div>
                <h3 className="mt-4 font-sans text-xl font-semibold text-foreground">
                  Official Role
                </h3>
                <p className="mt-1.5 font-mono text-xs text-muted-foreground leading-relaxed">
                  Full operational access to 9 core watershed tabs, live Model 1 AI inference, Sentinel/Bhoonidhi ingestion, and field logs.
                </p>
              </div>

              <button
                type="button"
                onClick={() => loginAs("official")}
                className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl bg-sage text-background py-3 font-sans text-sm font-semibold hover:bg-sage/90 transition-all cursor-pointer shadow-xs"
              >
                <span>Enter as Official →</span>
              </button>
            </div>

            {/* Option 2: Admin */}
            <div className="flex flex-col justify-between rounded-2xl border border-amber/40 bg-amber/5 p-6 sm:p-7 hover:border-amber hover:bg-amber/10 transition-all shadow-xs">
              <div>
                <div className="flex items-center justify-between">
                  <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber/20 text-amber">
                    <ShieldCheck size={24} weight="bold" />
                  </div>
                  <span className="rounded-full bg-amber/20 px-2.5 py-0.5 font-mono text-[10px] font-bold text-amber uppercase">
                    Statutory Auditor
                  </span>
                </div>
                <h3 className="mt-4 font-sans text-xl font-semibold text-foreground">
                  Admin Role
                </h3>
                <p className="mt-1.5 font-mono text-xs text-muted-foreground leading-relaxed">
                  All official operational features plus exclusive access to the <strong>Statutory Audit Console</strong>, user search history & telemetry logs.
                </p>
              </div>

              <button
                type="button"
                onClick={() => loginAs("admin")}
                className="mt-6 w-full flex items-center justify-center gap-2 rounded-xl bg-amber text-background py-3 font-sans text-sm font-semibold hover:bg-amber/90 transition-all cursor-pointer shadow-xs"
              >
                <span>Enter as Admin →</span>
              </button>
            </div>
          </div>

          <div className="mt-8 font-mono text-xs text-muted-foreground flex flex-wrap items-center justify-center gap-2">
            <span>Have custom officer credentials?</span>
            <button
              type="button"
              onClick={() => setShowAuthModal(true)}
              className="text-foreground font-semibold hover:underline cursor-pointer"
            >
              Sign In with Password
            </button>
            <span>·</span>
            <Link href="/register" className="text-foreground font-semibold hover:underline">
              Create Officer Profile
            </Link>
          </div>
        </div>

        <AuthModal isOpen={showAuthModal} onClose={() => setShowAuthModal(false)} />
      </div>
    );
  }

  return (
    <div className="relative rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-2xl backdrop-blur-md overflow-hidden animate-fade-up">
      {/* Corner architectural registration marks */}
      <span className="pointer-events-none absolute top-3.5 left-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
      <span className="pointer-events-none absolute top-3.5 right-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
      <span className="pointer-events-none absolute bottom-3.5 left-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>
      <span className="pointer-events-none absolute bottom-3.5 right-3.5 font-mono text-[11px] text-foreground/30 select-none">+</span>

      {/* Header with site identity & live telemetry pill */}
      <header className="border-b border-foreground/10 pb-8">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-2.5">
            {customLocation ? (
              <Badge tone="sage">ACTIVE WATERSHED AOI</Badge>
            ) : (
              <Badge tone="amber">AWAITING LOCATION QUERY</Badge>
            )}
            <span className="rounded-full border border-foreground/15 bg-foreground/5 px-3 py-1 font-mono text-xs text-foreground/80">
              {customLocation
                ? `${customLocation.lat.toFixed(4)}°N, ${customLocation.lon.toFixed(4)}°E`
                : "No Coordinates Selected"}
            </span>
            <span className="rounded-full border border-foreground/15 bg-background px-3 py-1 font-mono text-xs text-foreground/80 font-medium">
              Radius: {meta?.radius_km ? `${meta.radius_km.toFixed(1)} km` : customLocation?.radiusKm ? `${customLocation.radiusKm.toFixed(1)} km` : "2.0 km (Default)"}
            </span>
            {meta?.primary_source && (
              <span className={cn(
                "rounded-full border px-3 py-1 font-mono text-xs font-semibold flex items-center gap-1.5",
                meta.primary_source.includes("Bhoonidhi")
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-400"
                  : "border-foreground/15 bg-background text-foreground/80"
              )}>
                <Radio size={14} weight="bold" />
                <span>{meta.primary_source}</span>
                {meta.primary_source.includes("Bhoonidhi") && (
                  <span className="rounded-full bg-emerald-500/20 px-1.5 py-0.2 font-mono text-[9px] uppercase tracking-wider text-emerald-300">
                    Sovereign
                  </span>
                )}
              </span>
            )}
            {meta?.bhoonidhi_status && (meta.bhoonidhi_status === "queued" || meta.bhoonidhi_status === "processing") && (
              <span className="rounded-full border border-amber/40 bg-amber/10 px-3 py-1 font-mono text-xs font-semibold text-amber flex items-center gap-2" title="ISRO Bhoonidhi Resourcesat-2A LISS-III is downloading & clipping in background">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-amber"></span>
                </span>
                <span>Bhoonidhi Ingestion Active (Preview)</span>
              </span>
            )}
            <button
              onClick={() => setTab("bhuvan-report")}
              className={cn(
                "rounded-full border px-3 py-1 font-mono text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer shadow-xs",
                tab === "bhuvan-report"
                  ? "border-amber bg-amber text-black"
                  : meta?.bhuvan_stats?.status === "success"
                  ? "border-amber/50 bg-amber/15 text-amber hover:bg-amber/25 hover:border-amber"
                  : "border-amber/30 bg-amber/5 text-amber/90 hover:bg-amber/10"
              )}
              title="Open official ISRO Bhuvan 50k LULC ground-truth audit"
            >
              <span className="rounded-full bg-amber/20 px-1.5 py-0.2 font-mono text-[9px] uppercase tracking-wider font-bold">ISRO</span>
              <span>ISRO Bhuvan Report</span>
              <span className="rounded-full bg-amber/20 px-1.5 py-0.2 font-mono text-[9px] uppercase tracking-wider">
                {meta?.bhuvan_stats?.status === "success" ? "Live Verified" : "50k Standard"}
              </span>
            </button>
            {(customLocation?.targetDate || meta?.t2_date) && (
              <span className="rounded-full border border-amber/40 bg-amber/10 px-3 py-1 font-mono text-xs font-semibold text-amber flex items-center gap-1.5">
                <Radio size={14} weight="bold" />
                <span>Timeline: {meta?.t2_date || customLocation?.targetDate}</span>
              </span>
            )}
            {meta?.watershed_meta?.admin && (
              <span className="rounded-full border border-foreground/15 bg-background px-3 py-1 font-mono text-xs text-muted-foreground">
                {meta.watershed_meta.admin.district || meta.watershed_meta.admin.state || "India"}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isAnalyzing ? "bg-amber animate-pulse" : customLocation ? "bg-sage" : "bg-muted-foreground/50"
              )}
            />
            <span>
              {isAnalyzing
                ? "Satellite Ingestion Active"
                : customLocation
                ? "Analysis Ready"
                : "Awaiting Place Search"}
            </span>
          </div>
        </div>

        <h2 className="mt-4 font-display text-4xl sm:text-5xl lg:text-6xl leading-[0.95] tracking-tight">
          {customLocation ? customLocation.name : "Enter Name of Place or Coordinates"}
        </h2>

        <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
          {customLocation
            ? `Evaluated using ${meta?.primary_source || "Sentinel-2 L2A optical stack"} & Copernicus 30m DEM elevation grid. ${meta?.bhuvan_stats?.status === "success" ? `Cross-validated against live ISRO Bhuvan 50k LULC database (${meta.bhuvan_stats.total_sqkm} km²). ` : ""}Local context window covers a ${((meta?.radius_km || customLocation.radiusKm) * 2).toFixed(1)} km × ${((meta?.radius_km || customLocation.radiusKm) * 2).toFixed(1)} km area${meta ? ` (${Object.values(meta.class_breakdown).reduce((s, c) => s + (c.hectares || 0), 0).toFixed(0)} ha)` : ""} with organic hydrological catchment boundary delineation.`
            : "Search any village, district, or watershed in India above, or provide custom latitude and longitude coordinates with a custom radius to launch live satellite land cover classification, change detection, and catchment health assessment."}
        </p>
      </header>

      {/* ---- Unified Location Control Deck ---- */}
      <div className="mt-8 rounded-2xl border border-foreground/10 bg-foreground/2 p-5 sm:p-6 shadow-sm">
        <LocationPicker
          customLocation={customLocation}
          isAnalyzing={isAnalyzing}
          onSelectCustom={(loc) => {
            handleRunCustomPipeline(loc);
          }}
          onCancel={handleCancelPipeline}
        />
      </div>

      {/* ---- Cancellation Notice Banner ---- */}
      {cancelNotice && !isAnalyzing && (
        <div className="mt-6 flex items-center justify-between gap-3 rounded-2xl border border-amber/40 bg-amber/10 px-5 py-3.5 shadow-sm text-sm font-mono text-foreground animate-fade-up">
          <div className="flex items-center gap-2.5">
            <Crosshair size={16} weight="bold" className="text-amber" />
            <span>{cancelNotice}</span>
          </div>
          <button
            type="button"
            onClick={() => setCancelNotice(null)}
            className="text-xs text-muted-foreground hover:text-foreground cursor-pointer rounded-md border border-foreground/10 px-2.5 py-1"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ---- Live Pipeline Progress Banner (Working Animation) ---- */}
      {isAnalyzing && (
        <div className="mt-6 overflow-hidden rounded-2xl border border-amber/40 bg-amber/5 p-6 shadow-sm animate-fade-up">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="relative flex h-3.5 w-3.5 shrink-0">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-80" />
                <span className="relative inline-flex h-3.5 w-3.5 rounded-full bg-amber" />
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-sm text-foreground">
                    Live Satellite Ingestion in Progress
                  </span>
                  <span className="rounded-full bg-amber/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber uppercase tracking-wider animate-pulse">
                    Stage {currentStage.step}/4: {currentStage.label}
                  </span>
                </div>
                <p className="font-mono text-xs text-muted-foreground mt-0.5">
                  Analyzing AOI: <strong className="text-foreground">{customLocation?.name}</strong>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3.5">
              <div className="text-right">
                <span className="block font-mono text-sm font-semibold text-amber">
                  T+{elapsedSeconds}s
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  Expected ~{(customLocation?.radiusKm || 2.0) > 3.0 ? "35-50s (larger radius)" : "20-30s"}
                </span>
              </div>

              {/* High-visibility Cancel Button */}
              <button
                type="button"
                onClick={handleCancelPipeline}
                className="flex items-center gap-1.5 rounded-xl border border-red-500/50 bg-red-500/10 hover:bg-red-500/25 text-red-500 hover:text-red-400 px-3.5 py-2 font-mono text-xs font-semibold transition-all cursor-pointer shadow-xs active:scale-95"
                title="Cancel ongoing satellite ingestion and pipeline execution"
              >
                <X size={15} weight="bold" />
                <span>Cancel Analysis</span>
              </button>
            </div>
          </div>

          <p className="mt-3 font-mono text-xs text-foreground/80 bg-background/60 p-2.5 rounded-xl border border-foreground/5 flex items-center gap-2">
            <Radio size={14} className="text-amber animate-pulse shrink-0" weight="bold" />
            <span>{currentStage.detail}</span>
          </p>

          {/* Animated Progress Bar with glowing gradient */}
          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-foreground/10">
            <div
              className="h-full bg-linear-to-r from-amber via-yellow-400 to-amber transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(217,119,6,0.5)]"
              style={{
                width: `${Math.min(96, Math.max(15, elapsedSeconds * 2.8))}%`,
              }}
            />
          </div>

          <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 font-mono text-[11px]">
            <div className={cn("p-2 rounded-lg border transition-colors", currentStage.step === 1 ? "border-amber bg-amber/10 text-amber font-medium" : currentStage.step > 1 ? "border-sage/40 bg-sage/5 text-sage" : "border-foreground/10 text-muted-foreground/60")}>
              <div className="flex items-center gap-1.5">
                <span>{currentStage.step > 1 ? <Check size={12} weight="bold" /> : "1."}</span>
                <span>STAC Search</span>
              </div>
            </div>
            <div className={cn("p-2 rounded-lg border transition-colors", currentStage.step === 2 ? "border-amber bg-amber/10 text-amber font-medium" : currentStage.step > 2 ? "border-sage/40 bg-sage/5 text-sage" : "border-foreground/10 text-muted-foreground/60")}>
              <div className="flex items-center gap-1.5">
                <span>{currentStage.step > 2 ? <Check size={12} weight="bold" /> : "2."}</span>
                <span>10m Bands Clip</span>
              </div>
            </div>
            <div className={cn("p-2 rounded-lg border transition-colors", currentStage.step === 3 ? "border-amber bg-amber/10 text-amber font-medium" : currentStage.step > 3 ? "border-sage/40 bg-sage/5 text-sage" : "border-foreground/10 text-muted-foreground/60")}>
              <div className="flex items-center gap-1.5">
                <span>{currentStage.step > 3 ? <Check size={12} weight="bold" /> : "3."}</span>
                <span>PyTorch U-Net</span>
              </div>
            </div>
            <div className={cn("p-2 rounded-lg border transition-colors", currentStage.step === 4 ? "border-amber bg-amber/10 text-amber font-medium" : "border-foreground/10 text-muted-foreground/60")}>
              <div className="flex items-center gap-1.5">
                <span>4.</span>
                <span>DEM Hydrology</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ---- Analysis Complete Done Banner ---- */}
      {completedInfo && !isAnalyzing && (
        <div className="mt-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-sage/50 bg-sage/10 p-5 shadow-sm animate-fade-up">
          <div className="flex items-center gap-3.5">
            <div className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sage text-white text-lg font-bold shadow-sm">
              <span className="absolute inline-flex h-full w-full animate-ping-slow rounded-full bg-sage opacity-40" />
              <Check size={20} weight="bold" />
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-semibold text-sm text-foreground">
                  Pipeline Execution Complete: {completedInfo.siteName}
                </span>
                <span className="rounded-full bg-sage/20 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-sage uppercase tracking-wider">
                  {meta?.primary_source?.includes("Bhoonidhi") ? "ISRO Bhoonidhi LISS-III" : "Sentinel-2 L2A"}
                </span>
                {meta?.bhuvan_stats?.status === "success" && (
                  <button
                    onClick={() => setTab("bhuvan-report")}
                    className="rounded-full bg-amber/20 hover:bg-amber/30 border border-amber/40 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-amber uppercase tracking-wider flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <span className="rounded-full bg-amber/30 px-1 py-0.2 font-mono text-[9px] font-bold text-amber">ISRO</span>
                    <span>ISRO Bhuvan 50k Ground Truth Linked →</span>
                  </button>
                )}
              </div>
              <p className="font-mono text-xs text-muted-foreground mt-1">
                Completed in <strong className="text-foreground">{completedInfo.duration}s</strong> at {completedInfo.timestamp} · {meta?.primary_source || "Sentinel-2 L2A"} classified by PyTorch Model 1 U-Net {meta?.bhuvan_stats?.status === "success" ? `· Validated against official ISRO Bhuvan ${meta.bhuvan_stats.state ? `(${meta.bhuvan_stats.state})` : ""} 50k LULC database` : ""}
              </p>
            </div>
          </div>
          <button
            onClick={() => setCompletedInfo(null)}
            className="flex items-center gap-1.5 rounded-lg border border-foreground/15 bg-background px-3 py-1.5 font-mono text-xs text-muted-foreground hover:text-foreground hover:border-foreground/30 transition-colors"
          >
            <span>Dismiss</span>
            <X size={12} weight="bold" />
          </button>
        </div>
      )}

      {/* ---- Bhoonidhi Sovereign Download Notification & Action Deck ---- */}
      {!isAnalyzing && meta && (
        <>
          {/* Notification: Bhoonidhi download in progress in background while Sentinel-2 preview is active */}
          {(meta.bhoonidhi_status === "queued" || meta.bhoonidhi_status === "processing") && !bhoonidhiAvailable && (
            <div className="mt-6 overflow-hidden rounded-2xl border border-amber/40 bg-linear-to-r from-amber/15 via-amber/10 to-transparent p-5 shadow-sm animate-fade-up">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3.5">
                  <div className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber/20 border border-amber/40 text-amber text-xl shadow-xs">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-xl bg-amber opacity-30" />
                    <Radio size={20} weight="bold" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-sm text-foreground">
                        Your map is being downloaded from ISRO Bhoonidhi. Please wait...
                      </span>
                      <span className="rounded-full bg-amber/20 border border-amber/40 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-amber uppercase tracking-wider animate-pulse flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber" />
                        Sentinel-2 Preview Active Below
                      </span>
                    </div>
                    <p className="font-mono text-xs text-muted-foreground mt-1">
                      Sentinel-2 preview is ready and displayed below. Official ISRO Resourcesat-2A LISS-III sovereign archive is being retrieved and clipped in the background.
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-2 rounded-xl border border-amber/30 bg-amber/10 px-3.5 py-2 font-mono text-xs text-amber font-medium">
                    <div className="h-3 w-3 animate-spin rounded-full border-2 border-amber border-t-transparent" />
                    <span>Downloading Bhoonidhi Scene...</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Ready Banner: Bhoonidhi output is ready! Button lets user view Bhoonidhi output */}
          {(bhoonidhiAvailable || meta.bhoonidhi_status === "ready") && (
            <div className="mt-6 overflow-hidden rounded-2xl border-2 border-emerald-500/60 bg-linear-to-r from-emerald-500/20 via-emerald-500/10 to-transparent p-5 shadow-md animate-fade-up">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex items-center gap-3.5">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-500/20 border border-emerald-500/50 text-emerald-400 text-xl shadow-xs">
                    <Check size={20} weight="bold" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-sm text-foreground">
                        ISRO Bhoonidhi Sovereign Map Output is Ready!
                      </span>
                      <span className="rounded-full bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 font-mono text-[10px] font-semibold text-emerald-300 uppercase tracking-wider">
                        Resourcesat-2A LISS-III (Tier 1)
                      </span>
                      {activeSource === "bhoonidhi" ? (
                        <span className="rounded-full bg-emerald-500/30 px-2.5 py-0.5 font-mono text-[10px] font-bold text-emerald-200 flex items-center gap-1">
                          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                          Active View
                        </span>
                      ) : (
                        <span className="rounded-full bg-foreground/10 px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
                          Preview: Sentinel-2
                        </span>
                      )}
                    </div>
                    <p className="font-mono text-xs text-muted-foreground mt-1">
                      {activeSource === "bhoonidhi"
                        ? "Currently displaying official ISRO Bhoonidhi Resourcesat-2A sovereign satellite data and U-Net classification."
                        : "Sovereign satellite data has been downloaded and processed. Click the button below to view the Bhoonidhi output."}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  {activeSource !== "bhoonidhi" ? (
                    <button
                      type="button"
                      onClick={() => handleSwitchSource("bhoonidhi")}
                      disabled={isSwitchingSource}
                      className="flex items-center gap-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 active:scale-95 px-5 py-2.5 font-sans text-sm font-bold text-black shadow-lg shadow-emerald-500/25 transition-all cursor-pointer"
                    >
                      <Radio size={14} weight="bold" />
                      <span>{isSwitchingSource ? "Switching..." : "Click to View Bhoonidhi Output"}</span>
                      <span className="rounded-md bg-black/20 px-1.5 py-0.5 font-mono text-[10px]">Tier 1</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={() => handleSwitchSource("sentinel")}
                      disabled={isSwitchingSource}
                      className="flex items-center gap-2 rounded-xl border border-foreground/20 bg-background hover:bg-foreground/5 active:scale-95 px-4 py-2 font-mono text-xs text-foreground transition-all cursor-pointer"
                    >
                      <Radio size={14} weight="bold" />
                      <span>{isSwitchingSource ? "Switching..." : "Switch to Sentinel-2 Preview"}</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Notice: Bhoonidhi unavailable */}
          {meta.bhoonidhi_status === "unavailable" && !dismissedBhoonidhiNotice && (
            <div className="mt-6 flex items-center justify-between gap-3 rounded-2xl border border-foreground/15 bg-background/80 px-5 py-3.5 shadow-sm text-sm font-mono text-muted-foreground animate-fade-up">
              <div className="flex items-center gap-2.5">
                <ShieldCheck size={16} weight="bold" className="text-amber" />
                <span>ISRO Bhoonidhi: No cloud-free Resourcesat-2A scene found in catalog for this date/coordinate. Sentinel-2 preview remains active.</span>
              </div>
              <button
                type="button"
                onClick={() => setDismissedBhoonidhiNotice(true)}
                className="text-xs text-muted-foreground hover:text-foreground cursor-pointer rounded-md border border-foreground/10 px-2.5 py-1"
              >
                Dismiss
              </button>
            </div>
          )}
        </>
      )}

      {/* ---- High-Precision Segmented Tab Bar ---- */}
      <div className="mt-8">
        <div
          className="flex gap-1.5 overflow-x-auto rounded-2xl border border-foreground/15 bg-foreground/3 p-1.5 shadow-sm"
          role="tablist"
          aria-label="Watershed views"
        >
          {availableTabs.map((t) => {
            const disabled = t.needsChangePair && meta ? !meta.has_change_pair : false;
            const isActive = tab === t.key;
            const isHighlight = "highlight" in t && t.highlight;
            return (
              <button
                key={t.key}
                role="tab"
                aria-selected={isActive}
                onClick={() => !disabled && setTab(t.key)}
                disabled={disabled}
                className={cn(
                  "whitespace-nowrap rounded-xl px-4 py-2.5 font-mono text-xs uppercase tracking-wider transition-all cursor-pointer flex items-center gap-1.5",
                  isActive
                    ? isHighlight
                      ? "bg-amber text-black shadow-sm font-bold border border-amber"
                      : "bg-background text-foreground shadow-sm border border-foreground/15 font-semibold"
                    : isHighlight
                    ? "text-amber hover:bg-amber/10 font-semibold border border-amber/30"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/40",
                  disabled && "cursor-not-allowed opacity-30 hover:bg-transparent"
                )}
              >
                {t.key === "audit" && <ShieldCheck size={14} weight="bold" />}
                <span>{t.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ---- Tab content ---- */}
      <div className="mt-8 rounded-2xl border border-foreground/10 bg-background/60 p-6 sm:p-8 shadow-sm min-h-125">
        {loadError ? (
          <div className="rounded-2xl border border-red-500/30 bg-red-500/5 p-10 text-center">
            <p className="text-sm font-mono text-red-400">Analysis pipeline encountered an error:</p>
            <p className="mt-2 text-xs font-mono text-muted-foreground max-w-lg mx-auto bg-background/60 p-3 rounded-xl border border-foreground/10">
              {loadError}
            </p>
            <div className="mt-5 flex items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => setLoadError(null)}
                className="rounded-xl border border-foreground/20 px-4 py-2 font-mono text-xs text-foreground/80 hover:text-foreground hover:border-foreground/40 transition-colors cursor-pointer"
              >
                Dismiss Notice
              </button>
              {customLocation && (
                <button
                  type="button"
                  onClick={() => handleRunCustomPipeline(customLocation)}
                  className="rounded-xl bg-amber text-black font-semibold px-4 py-2 font-mono text-xs hover:bg-amber/90 transition-colors cursor-pointer shadow-xs"
                >
                  Retry Analysis →
                </button>
              )}
            </div>
          </div>
        ) : isAnalyzing || loading ? (
          <div className="relative overflow-hidden rounded-2xl border border-foreground/10 bg-background/50 p-12 text-center">
            {/* Radar scanner visualization */}
            <div className="relative mx-auto flex h-36 w-36 items-center justify-center">
              {/* Concentric rings */}
              <div className="absolute inset-0 rounded-full border border-foreground/10" />
              <div className="absolute inset-3 rounded-full border border-foreground/10 border-dashed" />
              <div className="absolute inset-7 rounded-full border border-foreground/15" />
              <div className="absolute inset-11 rounded-full border border-foreground/20" />
              
              {/* Rotating radar sweep beam */}
              <div className="absolute inset-0 rounded-full animate-radar pointer-events-none">
                <div className="h-1/2 w-1/2 rounded-tl-full bg-linear-to-br from-foreground/25 to-transparent" />
              </div>

              {/* Center satellite telemetry dot */}
              <span className="relative flex h-4 w-4">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber opacity-75" />
                <span className="relative inline-flex h-4 w-4 rounded-full bg-amber" />
              </span>
            </div>

            <div className="mt-6 max-w-md mx-auto">
              <span className="inline-block rounded-full bg-foreground/5 px-3 py-1 font-mono text-[11px] uppercase tracking-wider text-muted-foreground animate-pulse">
                Live PyTorch & Satellite Stream Active
              </span>
              <h3 className="mt-3 font-display text-xl sm:text-2xl tracking-tight">
                Analyzing satellite imagery for {customLocation?.name || "Selected AOI"}
                {customLocation?.targetDate ? ` (${customLocation.targetDate})` : ""}...
              </h3>
              <p className="mt-2 font-mono text-xs text-muted-foreground">
                Stage {currentStage.step}/4: {currentStage.label} — {currentStage.detail}
              </p>

              <div className="mt-5">
                <button
                  type="button"
                  onClick={handleCancelPipeline}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-red-500/50 bg-red-500/10 hover:bg-red-500/25 text-red-500 hover:text-red-400 px-4 py-2 font-mono text-xs font-semibold transition-all cursor-pointer shadow-xs active:scale-95"
                  title="Cancel this analysis run immediately"
                >
                  <X size={15} weight="bold" />
                  <span>Cancel Ongoing Analysis</span>
                </button>
              </div>
            </div>
          </div>
        ) : !meta ? (
          tab === "audit" && isAdmin ? (
            <AuditTab />
          ) : tab === "validation" ? (
            <ValidationTab meta={meta} />
          ) : tab === "bhuvan-report" ? (
            <BhuvanReportTab meta={meta} onSelectTab={(t) => setTab(t as TabKey)} />
          ) : (
            <div className="relative overflow-hidden rounded-2xl border border-foreground/15 bg-foreground/2 p-10 sm:p-14 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-foreground/15 bg-background shadow-sm text-foreground/70">
                <Crosshair size={32} weight="bold" />
              </div>
              <h3 className="mt-5 font-display text-2xl sm:text-3xl tracking-tight">
                Enter a Place Name or Coordinates Above
              </h3>
              <p className="mt-2 max-w-lg mx-auto text-sm text-muted-foreground leading-relaxed">
                No area of interest is loaded by default. Type any place name in India above (or enter custom coordinates), choose your analysis radius, and click <strong>Search & Ingest AOI</strong> to run the multi-spectral satellite pipeline.
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-2 font-mono text-xs text-muted-foreground">
                <span>Quick demo queries:</span>
                <button
                  type="button"
                  onClick={() =>
                    handleRunCustomPipeline({
                      name: "Kadwanchi Watershed",
                      lat: 19.8921,
                      lon: 75.9912,
                      radiusKm: 2.0,
                      isCustom: true,
                    })
                  }
                  className="rounded-full border border-amber/50 bg-amber/10 px-3.5 py-1 text-foreground hover:bg-amber/20 font-semibold transition-colors cursor-pointer flex items-center gap-1.5 shadow-sm"
                >
                  <span className="rounded-full bg-amber/20 px-1.5 py-0.2 font-mono text-[9px] text-amber font-bold">ISRO</span>
                  <span>Kadwanchi Watershed (ISRO Bhoonidhi + Bhuvan)</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleRunCustomPipeline({
                      name: "Hiware Bazar",
                      lat: 19.0300,
                      lon: 74.5500,
                      radiusKm: 2.0,
                      isCustom: true,
                    })
                  }
                  className="rounded-full border border-foreground/20 bg-background px-3 py-1 text-foreground hover:border-foreground/50 transition-colors cursor-pointer"
                >
                  Hiware Bazar (Ahmednagar)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleRunCustomPipeline({
                      name: "Ralegan Siddhi",
                      lat: 19.0069,
                      lon: 74.4534,
                      radiusKm: 2.0,
                      isCustom: true,
                    })
                  }
                  className="rounded-full border border-foreground/20 bg-background px-3 py-1 text-foreground hover:border-foreground/50 transition-colors cursor-pointer"
                >
                  Ralegan Siddhi (Ahmednagar)
                </button>
                <button
                  type="button"
                  onClick={() =>
                    handleRunCustomPipeline({
                      name: "Tamhini Ghat",
                      lat: 18.4493,
                      lon: 73.4227,
                      radiusKm: 2.0,
                      isCustom: true,
                    })
                  }
                  className="rounded-full border border-foreground/20 bg-background px-3 py-1 text-foreground hover:border-foreground/50 transition-colors cursor-pointer"
                >
                  Tamhini Ghat (Pune)
                </button>
              </div>
            </div>
          )
        ) : (
          <>
            {tab === "audit" && isAdmin && <AuditTab />}
            {tab === "land-cover" && <LULCTab key={`${siteKey}_${activeSource}_${sourceVersion}`} site={siteKey} meta={meta} />}
            {tab === "change" && <ChangeTab key={`${siteKey}_${activeSource}_${sourceVersion}`} site={siteKey} meta={meta} />}
            {tab === "health" && <HealthTab meta={meta} onNavigateToSimulator={() => setTab("simulator")} />}
            {tab === "map" && <MapTab key={`${siteKey}_${activeSource}_${sourceVersion}`} site={siteKey} meta={meta} />}
            {tab === "field" && <FieldTab key={`${siteKey}_${activeSource}_${sourceVersion}`} site={siteKey} meta={meta} />}
            {tab === "investigation" && <InterventionsTab key={`${siteKey}_${activeSource}_${sourceVersion}`} site={siteKey} meta={meta} />}
            {tab === "bhuvan-report" && <BhuvanReportTab meta={meta} onSelectTab={(t) => setTab(t as TabKey)} />}
            {tab === "validation" && <ValidationTab meta={meta} />}
            {tab === "simulator" && <SimulatorTab meta={meta} />}
          </>
        )}
      </div>
    </div>
  );
}

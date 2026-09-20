"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/cn";
import { type SiteKey, type SiteMeta } from "@/lib/watershed-data";
import Badge from "@/components/ui/Badge";
import { Radio, Check, X, Crosshair } from "@phosphor-icons/react";
import LULCTab from "@/components/tabs/LULCTab";
import ChangeTab from "@/components/tabs/ChangeTab";
import HealthTab from "@/components/tabs/HealthTab";
import FieldTab from "@/components/tabs/FieldTab";
import InterventionsTab from "@/components/tabs/InterventionsTab";
import SimulatorTab from "@/components/tabs/SimulatorTab";
import ValidationTab from "@/components/tabs/ValidationTab";
import LocationPicker, { type CustomLocation } from "@/components/LocationPicker";

const MapTab = dynamic(() => import("@/components/tabs/MapTab"), {
  ssr: false,
  loading: () => <div className="aspect-square w-full animate-pulse rounded-2xl bg-foreground/5" />,
});

const TABS = [
  { key: "land-cover", label: "Land Cover", needsChangePair: false },
  { key: "change", label: "Change", needsChangePair: true },
  { key: "health", label: "Health & Alerts", needsChangePair: true },
  { key: "map", label: "Map", needsChangePair: false },
  { key: "field", label: "Field Investigation", needsChangePair: false },
  { key: "investigation", label: "Investigation", needsChangePair: false },
  { key: "validation", label: "Scientific Validation", needsChangePair: false },
  { key: "simulator", label: "What-If Simulator", needsChangePair: false },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function WatershedApp() {
  const [siteKey, setSiteKey] = useState<string>("custom_live");
  const [customLocation, setCustomLocation] = useState<CustomLocation | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [completedInfo, setCompletedInfo] = useState<{
    siteName: string;
    duration: number;
    timestamp: string;
  } | null>(null);
  const [meta, setMeta] = useState<SiteMeta | null>(null);
  const [tab, setTab] = useState<TabKey>("land-cover");
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

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

  async function handleRunCustomPipeline(loc: CustomLocation) {
    // Cancel any in-flight pipeline run before starting a new one
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    setCustomLocation(loc);
    setIsAnalyzing(true);
    setCompletedInfo(null);
    setLoading(true);
    setLoadError(null);
    const startTime = Date.now();

    try {
      // Relative URL: same-origin in the Docker image (Python serves both the
      // static export and /api), and proxied to the API server by next.config's
      // dev rewrite when running the two servers locally.
      const res = await fetch("/api/pipeline/run", {
        method: "POST",
        signal: controller.signal,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lat: loc.lat,
          lon: loc.lon,
          name: loc.name,
          radius_km: loc.radiusKm || 2.0,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.error || `Server returned HTTP ${res.status}`);
      }

      const data = await res.json();
      if (data.meta) {
        const totalDuration = Math.round((Date.now() - startTime) / 1000);
        setSiteKey(data.siteKey || "custom_live");
        setMeta(data.meta);
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
      if ((err as Error).name === "AbortError") return; // Silently discard cancelled requests
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
            ? `Evaluated against Sentinel-2 L2A optical stack & Copernicus 30m DEM elevation grid. Local context window covers a ${((meta?.radius_km || customLocation.radiusKm) * 2).toFixed(1)} km × ${((meta?.radius_km || customLocation.radiusKm) * 2).toFixed(1)} km area${meta ? ` (${Object.values(meta.class_breakdown).reduce((s, c) => s + (c.hectares || 0), 0).toFixed(0)} ha)` : ""} with organic hydrological catchment boundary delineation.`
            : "Search any village, district, or watershed in India above, or provide custom latitude and longitude coordinates with a custom radius to launch live satellite land cover classification, change detection, and catchment health assessment."}
        </p>
      </header>

      {/* ---- Unified Location Control Deck ---- */}
      <div className="mt-8 rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-5 sm:p-6 shadow-sm">
        <LocationPicker
          customLocation={customLocation}
          onSelectCustom={(loc) => {
            handleRunCustomPipeline(loc);
          }}
        />
      </div>

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

            <div className="flex items-center gap-4">
              <div className="text-right">
                <span className="block font-mono text-sm font-semibold text-amber">
                  T+{elapsedSeconds}s
                </span>
                <span className="font-mono text-[10px] text-muted-foreground">
                  Expected ~{(customLocation?.radiusKm || 2.0) > 3.0 ? "35-50s (larger radius)" : "20-30s"}
                </span>
              </div>
            </div>
          </div>

          <p className="mt-3 font-mono text-xs text-foreground/80 bg-background/60 p-2.5 rounded-xl border border-foreground/5 flex items-center gap-2">
            <Radio size={14} className="text-amber animate-pulse shrink-0" weight="bold" />
            <span>{currentStage.detail}</span>
          </p>

          {/* Animated Progress Bar with glowing gradient */}
          <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-foreground/10">
            <div
              className="h-full bg-gradient-to-r from-amber via-yellow-400 to-amber transition-all duration-1000 ease-out shadow-[0_0_10px_rgba(217,119,6,0.5)]"
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
                  100% Real Satellite Data
                </span>
              </div>
              <p className="font-mono text-xs text-muted-foreground mt-1">
                Completed in <strong className="text-foreground">{completedInfo.duration}s</strong> at {completedInfo.timestamp} · Sentinel-2 L2A optical stack classified by trained Model 1 U-Net checkpoint
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

      {/* ---- High-Precision Segmented Tab Bar ---- */}
      <div className="mt-8">
        <div
          className="flex gap-1.5 overflow-x-auto rounded-2xl border border-foreground/15 bg-foreground/[0.03] p-1.5 shadow-sm"
          role="tablist"
          aria-label="Watershed views"
        >
          {TABS.map((t) => {
            const disabled = t.needsChangePair && meta ? !meta.has_change_pair : false;
            const isActive = tab === t.key;
            return (
              <button
                key={t.key}
                role="tab"
                aria-selected={isActive}
                onClick={() => !disabled && setTab(t.key)}
                disabled={disabled}
                className={cn(
                  "whitespace-nowrap rounded-xl px-4 py-2.5 font-mono text-xs uppercase tracking-wider transition-all",
                  isActive
                    ? "bg-background text-foreground shadow-sm border border-foreground/15 font-semibold"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/40",
                  disabled && "cursor-not-allowed opacity-30 hover:bg-transparent"
                )}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* ---- Tab content ---- */}
      <div className="mt-8 rounded-2xl border border-foreground/10 bg-background/60 p-6 sm:p-8 shadow-sm min-h-[500px]">
        {loadError ? (
          <div className="rounded-2xl border border-foreground/10 p-10 text-center">
            <p className="text-sm text-muted-foreground">Couldn&apos;t load demo data: {loadError}</p>
            <button
              onClick={() => window.location.reload()}
              className="mt-4 rounded-full border border-foreground/15 px-5 py-2.5 text-sm hover:border-foreground/40"
            >
              Retry
            </button>
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
                <div className="h-1/2 w-1/2 rounded-tl-full bg-gradient-to-br from-foreground/25 to-transparent" />
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
                Analyzing Sentinel-2 imagery for {customLocation?.name || "Selected AOI"}...
              </h3>
              <p className="mt-2 font-mono text-xs text-muted-foreground">
                Stage {currentStage.step}/4: {currentStage.label} — {currentStage.detail}
              </p>
            </div>
          </div>
        ) : !meta ? (
          tab === "validation" ? (
            <ValidationTab />
          ) : (
            <div className="relative overflow-hidden rounded-2xl border border-foreground/15 bg-foreground/[0.02] p-10 sm:p-14 text-center">
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
            {tab === "land-cover" && <LULCTab site={siteKey} meta={meta} />}
            {tab === "change" && <ChangeTab site={siteKey} meta={meta} />}
            {tab === "health" && <HealthTab meta={meta} onNavigateToSimulator={() => setTab("simulator")} />}
            {tab === "map" && <MapTab site={siteKey} meta={meta} />}
            {tab === "field" && <FieldTab site={siteKey} meta={meta} />}
            {tab === "investigation" && <InterventionsTab site={siteKey} meta={meta} />}
            {tab === "validation" && <ValidationTab />}
            {tab === "simulator" && <SimulatorTab meta={meta} />}
          </>
        )}
      </div>
    </div>
  );
}

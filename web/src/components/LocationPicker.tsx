"use client";

import { useState, useEffect } from "react";
import { cn } from "@/lib/cn";
import Button from "@/components/ui/Button";
import { MagnifyingGlass, Crosshair, ArrowUpRight, Warning, CalendarBlank, X } from "@phosphor-icons/react";

export type CustomLocation = {
  name: string;
  lat: number;
  lon: number;
  radiusKm: number;
  isCustom: boolean;
  targetDate?: string;
  t1Date?: string;
  t2Date?: string;
};

const RADIUS_OPTIONS = [
  { value: 0.5, label: "0.5 km", desc: "Micro-Site (Immediate surroundings)" },
  { value: 1.0, label: "1.0 km", desc: "Local context" },
  { value: 2.0, label: "2.0 km (Standard)", desc: "Standard catchment focus (Default)" },
  { value: 5.0, label: "5.0 km", desc: "Broad regional catchment" },
] as const;

const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ||
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  "http://127.0.0.1:8000"
)
  .trim()
  .replace(/\/$/, "");

export default function LocationPicker({
  customLocation,
  onSelectCustom,
  onCancel,
  isAnalyzing = false,
}: {
  activeSiteKey?: string;
  customLocation: CustomLocation | null;
  onSelectPreset?: (key: any) => void;
  onSelectCustom: (loc: CustomLocation) => void;
  onCancel?: () => void;
  isAnalyzing?: boolean;
}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedRadius, setSelectedRadius] = useState<number>(customLocation?.radiusKm || 2.0);
  const [isCustomRadius, setIsCustomRadius] = useState(false);
  const [customRadiusValue, setCustomRadiusValue] = useState("2.0");

  const [showCoordInputs, setShowCoordInputs] = useState(false);
  const [customLat, setCustomLat] = useState("");
  const [customLon, setCustomLon] = useState("");
  const [coordRadius, setCoordRadius] = useState("2.0");

  // Timeline inputs state
  const [timelineMode, setTimelineMode] = useState<"latest" | "month" | "pair">(
    customLocation?.t1Date && customLocation?.t2Date
      ? "pair"
      : customLocation?.targetDate
      ? "month"
      : "latest"
  );
  const [targetDate, setTargetDate] = useState<string>(customLocation?.targetDate || "2026-03");
  const [t1Date, setT1Date] = useState<string>(customLocation?.t1Date || "2020-03");
  const [t2Date, setT2Date] = useState<string>(customLocation?.t2Date || "2026-03");

  // Keep search input, radius, and timeline in sync when customLocation updates
  useEffect(() => {
    if (customLocation) {
      if (customLocation.name) {
        setSearchQuery(customLocation.name);
      }
      setSelectedRadius(customLocation.radiusKm);
      if (![0.5, 1.0, 2.0, 5.0].includes(customLocation.radiusKm)) {
        setIsCustomRadius(true);
        setCustomRadiusValue(String(customLocation.radiusKm));
      } else {
        setIsCustomRadius(false);
      }
      setCoordRadius(String(customLocation.radiusKm));

      if (customLocation.t1Date && customLocation.t2Date) {
        setTimelineMode("pair");
        setT1Date(customLocation.t1Date);
        setT2Date(customLocation.t2Date);
      } else if (customLocation.targetDate) {
        setTimelineMode("month");
        setTargetDate(customLocation.targetDate);
      }
    }
  }, [customLocation]);

  const effectiveRadius = isCustomRadius
    ? Math.max(0.2, Math.min(25, parseFloat(customRadiusValue) || 2.0))
    : selectedRadius;

  function handleApplyTimeline(mode: "latest" | "month" | "pair", customTarget?: string, customT1?: string, customT2?: string) {
    const tgt = customTarget || targetDate;
    const t1 = customT1 || t1Date;
    const t2 = customT2 || t2Date;
    if (customLocation) {
      onSelectCustom({
        ...customLocation,
        targetDate: mode === "latest" ? undefined : tgt,
        t1Date: mode === "pair" ? t1 : undefined,
        t2Date: mode === "pair" ? t2 : mode === "month" ? tgt : undefined,
      });
    }
  }

  function handleRadiusPresetClick(val: number) {
    setIsCustomRadius(false);
    setSelectedRadius(val);
    if (customLocation && customLocation.radiusKm !== val) {
      onSelectCustom({
        ...customLocation,
        radiusKm: val,
        targetDate: timelineMode === "latest" ? undefined : targetDate,
        t1Date: timelineMode === "pair" ? t1Date : undefined,
        t2Date: timelineMode === "pair" ? t2Date : timelineMode === "month" ? targetDate : undefined,
      });
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const query = searchQuery.trim();

    // If active location exists and query is empty or matches current location,
    // re-run pipeline with current effective radius without redundant external geocoding!
    if (customLocation && (!query || query.toLowerCase() === customLocation.name.toLowerCase())) {
      onSelectCustom({
        ...customLocation,
        radiusKm: effectiveRadius,
      });
      return;
    }

    if (!query) return;

    setIsSearching(true);
    setSearchError(null);

    try {
      // 1. Try our backend geocoder first (no browser CORS or forbidden header issues)
      let englishName = query;
      let parsedLat: number | null = null;
      let parsedLon: number | null = null;

      try {
        const backendRes = await fetch(`${API_BASE_URL}/api/geocode?q=${encodeURIComponent(query)}`);
        if (backendRes.ok) {
          const bData = await backendRes.json();
          if (bData.lat != null && bData.lon != null) {
            parsedLat = parseFloat(bData.lat);
            parsedLon = parseFloat(bData.lon);
            englishName = bData.display_name || query;
          }
        }
      } catch (beErr) {
        console.warn("Backend geocoder query skipped, falling back to direct OSM:", beErr);
      }

      // 2. Fallback to direct Nominatim if backend geocoder was unavailable
      if (parsedLat === null || parsedLon === null) {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(
            query
          )}&format=json&limit=5&countrycodes=in&accept-language=en&namedetails=1`
        );

        if (!res.ok) throw new Error(`Search failed: HTTP ${res.status}`);
        const data = await res.json();

        if (!data || data.length === 0) {
          setSearchError(`No Indian location matching "${query}" found.`);
          setIsSearching(false);
          return;
        }

        const place = data[0];
        parsedLat = parseFloat(place.lat);
        parsedLon = parseFloat(place.lon);

        englishName =
          place.namedetails?.["name:en"] ||
          place.name ||
          place.display_name.split(",")[0].trim() ||
          query;
      }

      onSelectCustom({
        name: englishName,
        lat: parsedLat,
        lon: parsedLon,
        radiusKm: effectiveRadius,
        isCustom: true,
        targetDate: timelineMode === "latest" ? undefined : targetDate,
        t1Date: timelineMode === "pair" ? t1Date : undefined,
        t2Date: timelineMode === "pair" ? t2Date : timelineMode === "month" ? targetDate : undefined,
      });
      setIsSearching(false);
    } catch (err) {
      setSearchError(err instanceof Error ? err.message : "Geocoding network error");
      setIsSearching(false);
    }
  }

  function handleCoordinateSubmit(e: React.FormEvent) {
    e.preventDefault();
    const latNum = parseFloat(customLat);
    const lonNum = parseFloat(customLon);
    const radNum = parseFloat(coordRadius) || 2.0;

    if (isNaN(latNum) || isNaN(lonNum)) {
      setSearchError("Please provide valid numeric coordinates.");
      return;
    }

    onSelectCustom({
      name: `${latNum.toFixed(4)}°N, ${lonNum.toFixed(4)}°E`,
      lat: latNum,
      lon: lonNum,
      radiusKm: radNum,
      isCustom: true,
      targetDate: timelineMode === "latest" ? undefined : targetDate,
      t1Date: timelineMode === "pair" ? t1Date : undefined,
      t2Date: timelineMode === "pair" ? t2Date : timelineMode === "month" ? targetDate : undefined,
    });
  }

  const renderTimelineSection = () => (
    <div className="rounded-xl border border-foreground/10 bg-background/60 p-4 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <CalendarBlank size={16} className="text-amber" weight="bold" />
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground font-semibold">
            — Satellite Acquisition Timeline (Month &amp; Year)
          </span>
        </div>
        <span className="font-mono text-xs text-foreground/80">
          Timeline Target:{" "}
          <strong className="text-amber">
            {timelineMode === "latest"
              ? "Latest Available Pass"
              : timelineMode === "month"
              ? `${targetDate} (Target Month)`
              : `Pair: ${t1Date} (T1) → ${t2Date} (T2)`}
          </strong>
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => {
            setTimelineMode("latest");
            handleApplyTimeline("latest");
          }}
          className={cn(
            "rounded-lg border px-3 py-1.5 font-mono text-xs transition-all cursor-pointer",
            timelineMode === "latest"
              ? "border-foreground bg-foreground text-background shadow-sm font-semibold"
              : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
          )}
        >
          Latest Available Pass
        </button>
        <button
          type="button"
          onClick={() => {
            setTimelineMode("month");
            handleApplyTimeline("month");
          }}
          className={cn(
            "rounded-lg border px-3 py-1.5 font-mono text-xs transition-all cursor-pointer",
            timelineMode === "month"
              ? "border-foreground bg-foreground text-background shadow-sm font-semibold"
              : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
          )}
        >
          Specific Month &amp; Year...
        </button>
        <button
          type="button"
          onClick={() => {
            setTimelineMode("pair");
            handleApplyTimeline("pair");
          }}
          className={cn(
            "rounded-lg border px-3 py-1.5 font-mono text-xs transition-all cursor-pointer",
            timelineMode === "pair"
              ? "border-foreground bg-foreground text-background shadow-sm font-semibold"
              : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
          )}
        >
          Multi-Temporal Period (T1 &amp; T2 Months)...
        </button>
      </div>

      {timelineMode === "month" && (
        <div className="space-y-3 pt-2 border-t border-foreground/10 animate-fade-up">
          <div className="flex flex-wrap items-center gap-3">
            <label className="font-mono text-xs text-muted-foreground flex items-center gap-2">
              <span>Target Month &amp; Year:</span>
              <input
                type="month"
                min="2016-01"
                max="2026-12"
                value={targetDate.slice(0, 7)}
                onChange={(e) => {
                  setTargetDate(e.target.value);
                  handleApplyTimeline("month", e.target.value);
                }}
                className="rounded-lg border border-foreground/20 bg-background px-3 py-1 text-xs font-mono outline-none focus:border-amber"
              />
            </label>
            {customLocation && (
              <button
                type="button"
                onClick={() => handleApplyTimeline("month")}
                className="rounded-lg border border-amber/50 bg-amber/15 text-amber px-3 py-1 font-mono text-xs font-semibold hover:bg-amber/25 transition-colors cursor-pointer"
              >
                Fetch Satellite Data for {targetDate}
              </button>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[11px] text-muted-foreground mr-1">Quick Seasons:</span>
            {[
              { label: "🌸 Pre-Monsoon 2026", val: "2026-03" },
              { label: "❄️ Post-Monsoon 2025", val: "2025-12" },
              { label: "🌾 Kharif Peak 2025", val: "2025-08" },
              { label: "☀️ Summer Dry 2024", val: "2024-05" },
              { label: "🏛️ 5-Yr Baseline 2020", val: "2020-03" },
            ].map((s) => (
              <button
                key={s.val}
                type="button"
                onClick={() => {
                  setTargetDate(s.val);
                  handleApplyTimeline("month", s.val);
                }}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 font-mono text-[11px] transition-colors cursor-pointer",
                  targetDate === s.val
                    ? "border-amber bg-amber/20 text-amber font-semibold"
                    : "border-foreground/15 bg-background text-muted-foreground hover:text-foreground"
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {timelineMode === "pair" && (
        <div className="space-y-3 pt-2 border-t border-foreground/10 animate-fade-up">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1">
              <label className="block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                T1 Baseline Month &amp; Year (Historical Benchmark)
              </label>
              <input
                type="month"
                min="2016-01"
                max="2024-12"
                value={t1Date.slice(0, 7)}
                onChange={(e) => setT1Date(e.target.value)}
                className="w-full rounded-lg border border-foreground/20 bg-background px-3 py-1.5 text-xs font-mono outline-none focus:border-foreground"
              />
              <span className="font-mono text-[10px] text-muted-foreground">e.g. 2020-03 (Baseline benchmark)</span>
            </div>
            <div className="space-y-1">
              <label className="block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                T2 Assessment Month &amp; Year (Recent Observation)
              </label>
              <input
                type="month"
                min="2020-01"
                max="2026-12"
                value={t2Date.slice(0, 7)}
                onChange={(e) => setT2Date(e.target.value)}
                className="w-full rounded-lg border border-foreground/20 bg-background px-3 py-1.5 text-xs font-mono outline-none focus:border-foreground"
              />
              <span className="font-mono text-[10px] text-muted-foreground">e.g. 2026-03 (Recent observation)</span>
            </div>
          </div>
          {customLocation && (
            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => handleApplyTimeline("pair")}
                className="rounded-lg border border-amber/50 bg-amber/15 text-amber px-3 py-1 font-mono text-xs font-semibold hover:bg-amber/25 transition-colors cursor-pointer"
              >
                Run Change Analysis ({t1Date} → {t2Date})
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Search Header & Mode Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h3 className="font-display text-xl sm:text-2xl tracking-tight">
            Select Watershed Area of Interest
          </h3>
          <p className="font-mono text-xs text-muted-foreground mt-0.5">
            Query Sentinel-2 imagery & Copernicus 30m DEM elevation for any location in India
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowCoordInputs(!showCoordInputs)}
          className="font-mono text-xs text-foreground/80 hover:text-foreground underline underline-offset-4 flex items-center gap-1.5 cursor-pointer rounded-lg border border-foreground/15 px-3 py-1.5 bg-background hover:bg-foreground/5 transition-colors"
        >
          <Crosshair size={14} weight="bold" />
          <span>{showCoordInputs ? "Switch to Place Name Search" : "Enter Coordinates Directly"}</span>
          {!showCoordInputs && <ArrowUpRight size={12} weight="bold" />}
        </button>
      </div>

      {/* Place Search Form */}
      {!showCoordInputs ? (
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search any village, district, or watershed in India (e.g. Kadwanchi, Hiware Bazar, Ralegan Siddhi)..."
                className="w-full rounded-2xl border border-foreground/15 bg-background px-4 py-3.5 pl-11 text-sm outline-none transition-all placeholder:text-muted-foreground/60 focus:border-foreground/40 focus:ring-2 focus:ring-foreground/5"
              />
              <MagnifyingGlass
                size={18}
                className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
                weight="bold"
              />
            </div>
            {isAnalyzing ? (
              <button
                type="button"
                onClick={onCancel}
                className="flex items-center justify-center gap-2 rounded-2xl border border-red-500/60 bg-red-500/15 hover:bg-red-500/25 text-red-500 hover:text-red-400 px-6 py-3.5 font-mono text-sm font-semibold transition-all cursor-pointer shadow-md active:scale-95 shrink-0 animate-pulse"
                title="Cancel running satellite ingestion immediately"
              >
                <X size={18} weight="bold" />
                <span>Cancel Analysis</span>
              </button>
            ) : (
              <Button
                type="submit"
                size="lg"
                disabled={isSearching || !searchQuery.trim()}
                className="shrink-0"
              >
                {isSearching ? "Geocoding & Locating..." : "Search & Ingest AOI →"}
              </Button>
            )}
          </div>

          {/* Analysis Radius & Area Selection Controls */}
          <div className="rounded-xl border border-foreground/10 bg-background/60 p-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground font-semibold">
                — Analysis Radius & Spatial Extent
              </span>
              <span className="font-mono text-xs text-foreground/80">
                Active Radius: <strong className="text-foreground">{effectiveRadius.toFixed(1)} km</strong> (~{(Math.PI * effectiveRadius * effectiveRadius).toFixed(1)} km² area)
              </span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {RADIUS_OPTIONS.map((opt) => {
                const isSelected = !isCustomRadius && selectedRadius === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    disabled={isAnalyzing}
                    onClick={() => handleRadiusPresetClick(opt.value)}
                    className={cn(
                      "rounded-lg border px-3 py-1.5 font-mono text-xs transition-all",
                      isAnalyzing ? "opacity-50 cursor-not-allowed" : "cursor-pointer",
                      isSelected
                        ? "border-foreground bg-foreground text-background shadow-sm font-semibold"
                        : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
                    )}
                    title={opt.desc}
                  >
                    {opt.label}
                  </button>
                );
              })}

              <button
                type="button"
                onClick={() => setIsCustomRadius(true)}
                className={cn(
                  "rounded-lg border px-3 py-1.5 font-mono text-xs transition-all cursor-pointer",
                  isCustomRadius
                    ? "border-foreground bg-foreground text-background shadow-sm font-semibold"
                    : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
                )}
              >
                Custom Radius...
              </button>

              {isCustomRadius && (
                <div className="flex items-center gap-2 animate-fade-up">
                  <input
                    type="number"
                    step="0.1"
                    min="0.2"
                    max="25"
                    value={customRadiusValue}
                    onChange={(e) => setCustomRadiusValue(e.target.value)}
                    className="w-20 rounded-lg border border-foreground/20 bg-background px-2.5 py-1 text-xs font-mono outline-none focus:border-foreground"
                  />
                  <span className="font-mono text-xs text-muted-foreground">km</span>
                  {customLocation && (
                    <button
                      type="button"
                      onClick={() => {
                        const r = Math.max(0.2, Math.min(25, parseFloat(customRadiusValue) || 2.0));
                        onSelectCustom({
                          ...customLocation,
                          radiusKm: r,
                        });
                      }}
                      className="rounded-lg border border-foreground/30 bg-foreground text-background px-3 py-1 font-mono text-xs font-semibold hover:opacity-90 transition-opacity cursor-pointer shadow-sm"
                    >
                      Apply Radius
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Caution Notice about Processing Time for Larger Radii */}
            <div
              className={cn(
                "flex items-start gap-2.5 rounded-xl border p-3 text-[11px] font-mono leading-relaxed transition-colors",
                effectiveRadius > 2.0
                  ? "border-amber/40 bg-amber/10 text-foreground"
                  : "border-foreground/10 bg-foreground/[0.02] text-muted-foreground"
              )}
            >
              <Warning
                size={16}
                className={cn("shrink-0 mt-0.5", effectiveRadius > 2.0 ? "text-amber" : "text-muted-foreground")}
                weight="bold"
              />
              <div>
                <strong className={effectiveRadius > 2.0 ? "text-amber font-semibold" : "text-foreground"}>
                  Processing Time Notice:
                </strong>{" "}
                Bigger radius sizes (e.g. 5.0 km or custom &gt; 3.0 km) cover substantially larger spatial areas (~10,000+ ha) and require streaming expanded multi-spectral 10m Sentinel-2 bands and 30m DEM elevation tiles. Higher radius means higher processing time (~30–50s vs ~10–20s for smaller radii).
              </div>
            </div>
          </div>

          {/* Timeline Section for Place Search */}
          {renderTimelineSection()}
        </form>
      ) : (
        /* Manual Coordinates Drawer with Radius input */
        <form
          onSubmit={handleCoordinateSubmit}
          className="rounded-2xl border border-foreground/15 bg-background/80 p-5 space-y-4 animate-fade-up"
        >
          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground font-semibold">
            — Precise Coordinate & Radius Entry
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Latitude (°N)
              </label>
              <input
                type="number"
                step="0.0001"
                required
                value={customLat}
                onChange={(e) => setCustomLat(e.target.value)}
                placeholder="e.g. 19.8921"
                className="mt-1 w-full rounded-xl border border-foreground/15 bg-background p-2.5 text-sm font-mono outline-none focus:border-foreground"
              />
            </div>

            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Longitude (°E)
              </label>
              <input
                type="number"
                step="0.0001"
                required
                value={customLon}
                onChange={(e) => setCustomLon(e.target.value)}
                placeholder="e.g. 75.9912"
                className="mt-1 w-full rounded-xl border border-foreground/15 bg-background p-2.5 text-sm font-mono outline-none focus:border-foreground"
              />
            </div>

            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-muted-foreground">
                Radius (km)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.2"
                max="25"
                required
                value={coordRadius}
                onChange={(e) => setCoordRadius(e.target.value)}
                placeholder="2.0"
                className="mt-1 w-full rounded-xl border border-foreground/15 bg-background p-2.5 text-sm font-mono outline-none focus:border-foreground"
              />
            </div>
          </div>

          {/* Coordinate Mode Radius Processing Time Notice */}
          <div
            className={cn(
              "flex items-start gap-2.5 rounded-xl border p-3 text-[11px] font-mono leading-relaxed transition-colors",
              parseFloat(coordRadius) > 2.0
                ? "border-amber/40 bg-amber/10 text-foreground"
                : "border-foreground/10 bg-foreground/[0.02] text-muted-foreground"
            )}
          >
            <Warning
              size={15}
              className={cn("shrink-0 mt-0.5", parseFloat(coordRadius) > 2.0 ? "text-amber" : "text-muted-foreground")}
              weight="bold"
            />
            <div>
              <strong className={parseFloat(coordRadius) > 2.0 ? "text-amber font-semibold" : "text-foreground"}>
                Processing Time Notice:
              </strong>{" "}
              Larger radius values expand the satellite download footprint and PyTorch tensor size, resulting in longer pipeline processing time (~30–50s).
            </div>
          </div>

          {/* Timeline Section for Coordinate Mode */}
          {renderTimelineSection()}

          <div className="flex justify-end pt-2">
            {isAnalyzing ? (
              <button
                type="button"
                onClick={onCancel}
                className="flex items-center gap-2 rounded-xl border border-red-500/60 bg-red-500/15 hover:bg-red-500/25 text-red-500 hover:text-red-400 px-5 py-2.5 font-mono text-xs font-semibold transition-all cursor-pointer shadow-sm active:scale-95 animate-pulse"
                title="Cancel running analysis immediately"
              >
                <X size={15} weight="bold" />
                <span>Cancel Analysis</span>
              </button>
            ) : (
              <Button type="submit" size="md">
                Inspect Custom Coordinates & Radius →
              </Button>
            )}
          </div>
        </form>
      )}

      {/* Error Feedback */}
      {searchError && (
        <div className="rounded-xl border border-danger/30 bg-danger/5 px-4 py-2.5 text-xs text-danger font-mono">
          {searchError}
        </div>
      )}
    </div>
  );
}

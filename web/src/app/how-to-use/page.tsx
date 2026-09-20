"use client";

import { useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import Badge from "@/components/ui/Badge";
import Button from "@/components/ui/Button";
import {
  MagnifyingGlass,
  Crosshair,
  Drop,
  Tree,
  Plant,
  ShieldCheck,
  TrendUp,
  Sliders,
  Warning,
  Camera,
  CheckCircle,
  Clock,
  ArrowRight,
  CaretRight,
  FileText,
  MapPin,
  Stack,
  Sparkle,
  Radio,
} from "@phosphor-icons/react";

type GuideTab =
  | "quickstart"
  | "location-radius"
  | "land-cover"
  | "change"
  | "health"
  | "map"
  | "simulator"
  | "field-photo"
  | "faq";

const MODULES: { id: GuideTab; label: string; step: string; tag: string }[] = [
  { id: "quickstart", label: "Quick Start Guide", step: "00", tag: "Overview" },
  { id: "location-radius", label: "Search & Radius Selection", step: "01", tag: "Input" },
  { id: "land-cover", label: "Reading Land Cover (LULC)", step: "02", tag: "Analysis" },
  { id: "change", label: "Tracking 5-Year Changes", step: "03", tag: "Detection" },
  { id: "health", label: "Health Score & Alert Cards", step: "04", tag: "Diagnosis" },
  { id: "map", label: "Interactive GIS & Catchment Map", step: "05", tag: "Hydrology" },
  { id: "simulator", label: "What-If Policy Simulator", step: "06", tag: "Planning" },
  { id: "field-photo", label: "Field Photo Verification", step: "07", tag: "Validation" },
  { id: "faq", label: "FAQ & Practical Tips", step: "08", tag: "Support" },
];

export default function HowToUsePage() {
  const [activeTab, setActiveTab] = useState<GuideTab>("quickstart");
  const [activeRadiusPreview, setActiveRadiusPreview] = useState<number>(2.0);
  const [sliderPos, setSliderPos] = useState<number>(50);

  return (
    <div className="relative min-h-screen">
      {/* Background Architectural Hairline Grid */}
      <div className="hairline-grid opacity-70" />

      <main className="relative z-10 mx-auto max-w-7xl px-6 py-16 sm:px-10 sm:py-24">
        {/* Eyebrow & Hero Header */}
        <div className="max-w-3xl">
          <div className="flex flex-wrap items-center gap-3">
            <span className="h-px w-8 bg-foreground/40" />
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              User Guide &amp; Operational Manual
            </span>
            <Badge tone="sage">SIH 2026 PS-26015</Badge>
          </div>

          <h1 className="mt-6 font-display text-5xl leading-[0.92] tracking-tight sm:text-7xl">
            How to Use
            <br />
            <span className="text-muted-foreground">GeoDhara.</span>
          </h1>

          <p className="mt-5 text-base sm:text-lg text-muted-foreground leading-relaxed">
            A comprehensive, simple-word guide designed for watershed officers, field engineers, and researchers.
            Learn how to inspect any location in India, read multi-spectral satellite land cover maps, track 5-year
            environmental transitions, and test conservation projects before allocating public funds.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <Button href="/try" variant="filled" size="md">
              Launch Live Console (/try) →
            </Button>
            <Button href="/about" variant="outline" size="md">
              Scientific Architecture →
            </Button>
          </div>
        </div>

        {/* High-Precision Interactive Module Bar */}
        <div className="mt-14 border-b border-foreground/15 pb-4">
          <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-none" role="tablist">
            {MODULES.map((m) => {
              const isActive = activeTab === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => setActiveTab(m.id)}
                  className={cn(
                    "flex items-center gap-2 rounded-xl border px-3.5 py-2 font-mono text-xs uppercase tracking-wider transition-all cursor-pointer whitespace-nowrap",
                    isActive
                      ? "border-foreground bg-foreground text-background font-semibold shadow-sm"
                      : "border-foreground/15 bg-background text-foreground/80 hover:border-foreground/40 hover:text-foreground"
                  )}
                >
                  <span className={cn("text-[10px]", isActive ? "text-background/80" : "text-muted-foreground")}>
                    {m.step}.
                  </span>
                  <span>{m.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Content Modules */}
        <div className="mt-10">
          {/* ========================================================================= */}
          {/* 00. QUICK START OVERVIEW */}
          {/* ========================================================================= */}
          {activeTab === "quickstart" && (
            <div className="space-y-10 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm backdrop-blur-md">
                <div className="max-w-2xl">
                  <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                    Module 00 · Complete Workflow Overview
                  </span>
                  <h2 className="mt-2 font-display text-3xl sm:text-4xl">The 3-Step Decision Loop</h2>
                  <p className="mt-3 text-sm sm:text-base text-muted-foreground leading-relaxed">
                    You can evaluate any rural watershed, village, or forest in India in under 45 seconds without needing prior GIS software or satellite downloading experience.
                  </p>
                </div>

                <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-3">
                  {/* Step 1 */}
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                        <span>STEP 01</span>
                        <MagnifyingGlass size={18} className="text-foreground" weight="bold" />
                      </div>
                      <h3 className="mt-3 font-display text-xl">Search &amp; Pick Radius</h3>
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                        Type any village or district in India (e.g., <em>Ralegan Siddhi</em>, <em>Hiware Bazar</em>, <em>Paithan</em>), or type exact GPS coordinates. Select your desired analysis radius from 0.5 km to 5.0 km.
                      </p>
                    </div>
                    <div className="mt-6 pt-4 border-t border-foreground/10 font-mono text-[11px] text-muted-foreground">
                      Automatic English geocoding
                    </div>
                  </div>

                  {/* Step 2 */}
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                        <span>STEP 02</span>
                        <Radio size={18} className="text-amber animate-pulse" weight="bold" />
                      </div>
                      <h3 className="mt-3 font-display text-xl">Live Satellite Ingestion</h3>
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                        The cloud server queries the Copernicus Sentinel-2 STAC catalog, streams 10m optical GeoTIFFs, downloads 30m elevation DEM grids, and runs the PyTorch U-Net neural network in ~20–35s.
                      </p>
                    </div>
                    <div className="mt-6 pt-4 border-t border-foreground/10 font-mono text-[11px] text-amber">
                      100% real satellite data · No mocks
                    </div>
                  </div>

                  {/* Step 3 */}
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
                        <span>STEP 03</span>
                        <CheckCircle size={18} className="text-sage" weight="bold" />
                      </div>
                      <h3 className="mt-3 font-display text-xl">Inspect Findings &amp; Simulate</h3>
                      <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                        Review the 7-class Land Cover map, 5-year change detection, multi-factor Health Score, physical drainage networks on the interactive map, and test conservation projects in the Policy Simulator.
                      </p>
                    </div>
                    <div className="mt-6 pt-4 border-t border-foreground/10 font-mono text-[11px] text-sage">
                      8 high-precision analytical tabs
                    </div>
                  </div>
                </div>

                <div className="mt-10 rounded-2xl border border-foreground/15 bg-background p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
                  <div>
                    <h4 className="font-display text-lg">Ready to try it right now?</h4>
                    <p className="mt-1 text-xs text-muted-foreground">
                      No sign-in or account registration required. Open the live console and search any Indian village.
                    </p>
                  </div>
                  <Button href="/try" size="md">
                    Open Live Operational Console →
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 01. SEARCH & RADIUS SELECTION */}
          {/* ========================================================================= */}
          {activeTab === "location-radius" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 01 · Area of Interest (AOI) Definition
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Finding Places &amp; Choosing Your Radius</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  Every watershed inquiry begins by selecting a target location and defining how much surrounding area you want to analyze.
                </p>

                {/* Search modes comparison */}
                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 space-y-3">
                    <div className="flex items-center gap-2 font-mono text-xs text-foreground font-semibold">
                      <MagnifyingGlass size={16} weight="bold" />
                      <span>Mode A: Search by Place Name</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Simply type any Indian village, district, town, or river name into the search box. The system automatically connects to OpenStreetMap Nominatim with strict English language parameters, converting names into precise geographic coordinates.
                    </p>
                    <div className="rounded-xl border border-foreground/10 bg-background p-3 font-mono text-xs text-foreground/80">
                      Examples: <span className="text-foreground">Ralegan Siddhi</span>, <span className="text-foreground">Hiware Bazar</span>, <span className="text-foreground">Paithan</span>, <span className="text-foreground">Tamhini Ghat</span>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 space-y-3">
                    <div className="flex items-center gap-2 font-mono text-xs text-foreground font-semibold">
                      <Crosshair size={16} weight="bold" />
                      <span>Mode B: Direct Coordinates Entry</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      If you have handheld GPS coordinates recorded during a field visit, click <em>&ldquo;Enter Coordinates Directly&rdquo;</em>. Enter the decimal latitude (°N) and longitude (°E) along with your desired radius.
                    </p>
                    <div className="rounded-xl border border-foreground/10 bg-background p-3 font-mono text-xs text-foreground/80">
                      Format: Latitude <span className="text-foreground">19.8830°N</span>, Longitude <span className="text-foreground">75.9910°E</span>
                    </div>
                  </div>
                </div>

                {/* Understanding the 4 Spatial Radii */}
                <div className="mt-10 border-t border-foreground/10 pt-8">
                  <h3 className="font-display text-2xl">Understanding Radius Sizes (Spatial Extent)</h3>
                  <p className="mt-2 text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    Different questions require different scopes. The platform offers four pre-calibrated sizes and an arbitrary custom radius:
                  </p>

                  <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 font-mono text-xs">
                    <div className="p-4 rounded-2xl border border-foreground/10 bg-background">
                      <span className="font-bold text-sm block">0.5 km (Micro-Site)</span>
                      <span className="text-muted-foreground mt-1 block">1.0 km × 1.0 km window</span>
                      <span className="text-foreground font-bold mt-2 block">~100 Hectares (~1.0 km²)</span>
                      <p className="mt-2 text-[11px] text-muted-foreground font-sans leading-normal">
                        Best for inspecting an individual check dam, farm pond, or single field plot.
                      </p>
                    </div>

                    <div className="p-4 rounded-2xl border border-foreground/10 bg-background">
                      <span className="font-bold text-sm block">1.0 km (Local Context)</span>
                      <span className="text-muted-foreground mt-1 block">2.0 km × 2.0 km window</span>
                      <span className="text-foreground font-bold mt-2 block">~400 Hectares (~4.0 km²)</span>
                      <p className="mt-2 text-[11px] text-muted-foreground font-sans leading-normal">
                        Best for a village hamlet, immediate agricultural plain, or localized gully corridor.
                      </p>
                    </div>

                    <div className="p-4 rounded-2xl border border-foreground/20 bg-foreground/5 shadow-sm ring-1 ring-foreground">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-sm">2.0 km (Standard)</span>
                        <span className="rounded-full bg-foreground/10 px-2 py-0.5 text-[9px] font-bold uppercase">Default</span>
                      </div>
                      <span className="text-muted-foreground mt-1 block">4.0 km × 4.0 km window</span>
                      <span className="text-foreground font-bold mt-2 block">~1,600 Hectares (~16.0 km²)</span>
                      <p className="mt-2 text-[11px] text-muted-foreground font-sans leading-normal">
                        Recommended balance. Covers full micro-watershed sub-basins with swift processing.
                      </p>
                    </div>

                    <div className="p-4 rounded-2xl border border-foreground/10 bg-background">
                      <span className="font-bold text-sm block">5.0 km (Regional)</span>
                      <span className="text-muted-foreground mt-1 block">10.0 km × 10.0 km window</span>
                      <span className="text-foreground font-bold mt-2 block">~10,000 Hectares (~100 km²)</span>
                      <p className="mt-2 text-[11px] text-muted-foreground font-sans leading-normal">
                        Best for regional river basins, extensive forest ridges, and multi-panchayat watersheds.
                      </p>
                    </div>
                  </div>

                  {/* Processing Time Caution Box */}
                  <div className="mt-6 rounded-2xl border border-amber/40 bg-amber/5 p-5 text-xs text-amber leading-relaxed flex items-start gap-3">
                    <Clock size={20} className="text-amber shrink-0 mt-0.5" weight="bold" />
                    <div>
                      <strong className="font-semibold text-foreground">Processing Time Notice:</strong>
                      <span className="block mt-1 text-foreground/90 font-sans">
                        A 5.0 km radius covers nearly 10 times more land than a 2.0 km radius (~10,000 ha vs ~1,600 ha). Because the server streams 10-meter resolution multi-spectral bands for this entire area, processing takes ~30–50 seconds compared to ~15–20 seconds for standard radii.
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 02. LAND COVER (LULC) */}
          {/* ========================================================================= */}
          {activeTab === "land-cover" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 02 · Land Use &amp; Land Cover Classification
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Reading the Land Cover Map (LULC)</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  LULC answers the question: <em>&ldquo;What is covering the ground right now?&rdquo;</em> The Model 1 deep learning network analyzes 6 spectral channels (Red, Green, Blue, Near-Infrared, NDVI, and NDWI) to assign every 10-meter pixel to one of 7 distinct classes.
                </p>

                {/* Interactive Split-Slider Demo */}
                <div className="mt-8 grid grid-cols-1 lg:grid-cols-[1fr_20rem] gap-8">
                  <div className="space-y-3">
                    <span className="font-mono text-xs text-muted-foreground uppercase tracking-wider block">
                      Interactive Comparison: Drag Slider to Compare Baseline (T1) vs Recent (T2)
                    </span>
                    <div className="relative aspect-square w-full max-w-md mx-auto overflow-hidden rounded-2xl border border-foreground/15 bg-foreground/5 shadow-sm select-none">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src="/demo-data/kadwanchi_watershed/t2.png"
                        alt="T2 Recent"
                        className="absolute inset-0 h-full w-full object-cover"
                        draggable={false}
                      />
                      <div
                        className="absolute inset-0 overflow-hidden"
                        style={{ clipPath: `inset(0 ${100 - sliderPos}% 0 0)` }}
                      >
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src="/demo-data/kadwanchi_watershed/t1.png"
                          alt="T1 Baseline"
                          className="h-full w-full object-cover"
                          draggable={false}
                        />
                      </div>
                      <div
                        className="pointer-events-none absolute inset-y-0 w-0.5 bg-background shadow-md"
                        style={{ left: `${sliderPos}%` }}
                      />
                      <input
                        type="range"
                        min={0}
                        max={100}
                        value={sliderPos}
                        onChange={(e) => setSliderPos(Number(e.target.value))}
                        className="absolute inset-x-4 bottom-4 mx-auto w-3/4 accent-foreground"
                      />
                      <span className="absolute left-3 bottom-12 rounded-full bg-background/90 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider shadow-sm">
                        T1 (2020 Baseline)
                      </span>
                      <span className="absolute right-3 bottom-12 rounded-full bg-background/90 px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider shadow-sm">
                        T2 (2025 Recent)
                      </span>
                    </div>
                  </div>

                  {/* 7 Class Legend */}
                  <div className="space-y-4">
                    <span className="font-mono text-xs text-muted-foreground uppercase tracking-wider block">
                      The 7 Standard Land Cover Classes
                    </span>
                    <div className="space-y-2.5 font-mono text-xs">
                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#0000ff] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Water / Structures</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Check dams, farm ponds, percolation tanks, rivers.</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#006400] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Dense Vegetation / Forest</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Perennial tree canopy, protected forest groves.</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#ffff00] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Agriculture / Cropland</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Active irrigated crops (Kharif, Rabi, Zaid).</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#90ee90] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Sparse Vegetation / Grass</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Scrubland, grazing pasture, seasonal grasses.</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#ff0000] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Built-up / Settlement</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Houses, paved roads, farm structures.</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#8b4513] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Barren / Degraded Land</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Exposed rock, eroded hill ridges, mine waste.</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 p-2 rounded-xl border border-foreground/10 bg-background">
                        <span className="h-4 w-4 rounded-md bg-[#d2b48c] shrink-0" />
                        <div>
                          <strong className="text-foreground block">Fallow / Bare Field</strong>
                          <span className="text-[11px] text-muted-foreground font-sans">Cultivated land temporarily resting between harvests.</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 03. CHANGE DETECTION */}
          {/* ========================================================================= */}
          {activeTab === "change" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 03 · Longitudinal Environmental Change
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Tracking Real Multi-Year Changes</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  How does the system distinguish permanent watershed improvements from routine seasonal farming?
                  The Change tab filters out seasonal crop cycles and focuses strictly on permanent structural transitions.
                </p>

                <div className="mt-8 grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
                  <div className="rounded-2xl border border-foreground/10 bg-foreground/5 p-4 overflow-hidden flex flex-col items-center">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src="/demo-data/kadwanchi_watershed/change.png"
                      alt="Change Map"
                      className="rounded-xl w-full max-w-sm aspect-square object-cover shadow-sm"
                    />
                    <span className="font-mono text-xs text-muted-foreground mt-3 block text-center">
                      Change detection map showing persistent interventions and structural shifts.
                    </span>
                  </div>

                  <div className="space-y-4">
                    <h3 className="font-display text-2xl">The 4 Key Transition Types</h3>
                    
                    <div className="space-y-3 font-mono text-xs">
                      <div className="p-3.5 rounded-xl border border-sky-500/30 bg-sky-500/5">
                        <strong className="text-sky-600 block text-sm">New Water Body (Blue)</strong>
                        <p className="mt-1 text-muted-foreground font-sans text-xs leading-normal">
                          Indicates a new check dam impoundment or percolation pond holding surface runoff. Treated as positive evidence of water conservation.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/5">
                        <strong className="text-emerald-600 block text-sm">Vegetation Gain / Afforestation (Green)</strong>
                        <p className="mt-1 text-muted-foreground font-sans text-xs leading-normal">
                          Barren land or open ridge successfully converted to permanent tree cover. Confirms sapling survival and slope stabilization.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl border border-purple-500/30 bg-purple-500/5">
                        <strong className="text-purple-600 block text-sm">New Built-Up / Construction (Purple)</strong>
                        <p className="mt-1 text-muted-foreground font-sans text-xs leading-normal">
                          Impervious surface or structures built where natural soil existed. Flagged for field audit to verify watershed zoning compliance.
                        </p>
                      </div>

                      <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-500/5">
                        <strong className="text-rose-600 block text-sm">Vegetation / Soil Loss (Red)</strong>
                        <p className="mt-1 text-muted-foreground font-sans text-xs leading-normal">
                          Severe topsoil erosion, gully expansion, or dried waterbeds. Priority zone for continuous contour trenching or earthen gully plugs.
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 04. HEALTH SCORE & ALERTS */}
          {/* ========================================================================= */}
          {activeTab === "health" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 04 · Catchment Diagnosis &amp; Decision Support
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Watershed Health Index &amp; Alerts</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  The health score is not an arbitrary number. It is an auditable weighted score (0–100) based on real Central Ground Water Board (CGWB) ecological metrics.
                </p>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 font-mono text-xs">
                  <div className="p-5 rounded-2xl border border-sage/40 bg-sage/5">
                    <span className="text-2xl font-bold text-sage block">70 – 100</span>
                    <strong className="text-foreground text-sm mt-1 block">Healthy Catchment (Sage)</strong>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-normal">
                      Sufficient water retention, high vegetation cover, and stable soil. Maintenance of existing structures is sufficient.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-amber/40 bg-amber/5">
                    <span className="text-2xl font-bold text-amber block">50 – 69</span>
                    <strong className="text-foreground text-sm mt-1 block">Moderate Vulnerability (Amber)</strong>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-normal">
                      High percentage of bare fallow land or declining 5-year NDVI trends. Needs targeted contour bunding and de-silting.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-danger/40 bg-danger/5">
                    <span className="text-2xl font-bold text-danger block">0 – 49</span>
                    <strong className="text-foreground text-sm mt-1 block">Critical Degradation (Rose)</strong>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-normal">
                      Severe gully scouring, near-zero water retention, and high drought risk. Immediate civil and biological works required.
                    </p>
                  </div>
                </div>

                <div className="mt-8 rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 space-y-4">
                  <h3 className="font-display text-xl">How Alerts Provide Explainable Evidence</h3>
                  <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                    Unlike black-box AI systems, every alert generated by GeoDhara contains quantifiable evidence bullets:
                  </p>
                  <div className="rounded-xl border border-foreground/10 bg-background p-4 space-y-2 font-mono text-xs">
                    <div className="flex items-center gap-2 text-amber font-semibold">
                      <Warning size={15} weight="bold" />
                      <span>Alert: Fallow Ground Moisture Stress &amp; Soil Loss Risk</span>
                    </div>
                    <ul className="list-disc pl-5 space-y-1 text-muted-foreground font-sans">
                      <li>Evidence: 24.6% of watershed area is exposed bare fallow soil during dry months.</li>
                      <li>Evidence: NDVI 5-year velocity exhibits -0.018 decline across upper slopes.</li>
                      <li>Action: Construct continuous contour trenches (CCT) and plant vetiver grass along the 2% gradient.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 05. INTERACTIVE MAP & HYDROLOGY */}
          {/* ========================================================================= */}
          {activeTab === "map" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 05 · GIS Topography &amp; Elevation Routing
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Interactive Map &amp; Catchment Boundaries</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  How does rainfall physically move across your area? The Map tab renders digital elevation modeling directly over open street maps.
                </p>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-4 font-mono text-xs">
                    <div className="p-4 rounded-xl border border-foreground/10 bg-background space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full border-2 border-blue-500 bg-blue-500/20" />
                        <strong className="text-foreground text-sm">Blue Dashed Circle (Physical Metric Radius)</strong>
                      </div>
                      <p className="text-muted-foreground font-sans text-xs leading-normal">
                        Shows the exact ground radius buffer in meters (e.g. 2,000m for 2.0 km, 5,000m for 5.0 km). Anchors your view to real physical scale.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-foreground/10 bg-background space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full bg-[#ff8c00]" />
                        <strong className="text-foreground text-sm">Orange Perimeter (Watershed Boundary)</strong>
                      </div>
                      <p className="text-muted-foreground font-sans text-xs leading-normal">
                        Delineated from Copernicus 30m DEM elevation data. Represents the natural topographic ridge dividing rainfall into this valley.
                      </p>
                    </div>

                    <div className="p-4 rounded-xl border border-foreground/10 bg-background space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="h-3 w-3 rounded-full bg-[#00c8ff]" />
                        <strong className="text-foreground text-sm">Cyan Dendritic Network (Drainage Channels)</strong>
                      </div>
                      <p className="text-muted-foreground font-sans text-xs leading-normal">
                        Shows active stream channels where flow accumulation exceeds 500 elevation cells. Indicates optimal check dam placement sites.
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 space-y-3">
                    <div className="flex items-center gap-2 font-mono text-xs font-semibold">
                      <Stack size={16} weight="bold" />
                      <span>Layer Control Checkboxes</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      On the right side of the map, you can toggle individual layers on or off:
                    </p>
                    <ul className="list-disc pl-5 space-y-1 text-xs text-muted-foreground font-sans">
                      <li>Toggle <strong>Radius Circle</strong> to inspect boundaries outside the buffer.</li>
                      <li>Toggle <strong>Land Cover (LULC)</strong> to inspect raw street maps beneath.</li>
                      <li>Adjust the <strong>Opacity Slider</strong> to blend satellite classification with underlying road networks and village names.</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 06. POLICY SIMULATOR */}
          {/* ========================================================================= */}
          {activeTab === "simulator" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 06 · Virtual Policy Modeling &amp; ROI
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">The What-If Policy Simulator</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  Test proposed conservation projects <em>virtually</em> before committing government budgets. The simulator recalculates expected groundwater recharge, soil loss prevention, and water table rise at 60 frames per second.
                </p>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-3">
                    <h3 className="font-display text-xl">The 4 Intervention Levers</h3>
                    <div className="space-y-2.5 font-mono text-xs">
                      <div className="p-3 rounded-xl border border-foreground/10 bg-background">
                        <strong className="text-sky-500 block text-sm">Masonry Check Dams</strong>
                        <span className="text-muted-foreground font-sans text-xs">
                          Built across stream channels. Each structure captures ~22.5 Million Litres of monsoon runoff annually.
                        </span>
                      </div>

                      <div className="p-3 rounded-xl border border-foreground/10 bg-background">
                        <strong className="text-emerald-500 block text-sm">Ridge Afforestation</strong>
                        <span className="text-muted-foreground font-sans text-xs">
                          Plants mixed indigenous trees on upper barren slopes. Saves ~12 tonnes of topsoil per hectare per year.
                        </span>
                      </div>

                      <div className="p-3 rounded-xl border border-foreground/10 bg-background">
                        <strong className="text-amber-500 block text-sm">Continuous Contour Trenching (CCT)</strong>
                        <span className="text-muted-foreground font-sans text-xs">
                          Digs trenches along hillslope contours. Halts sheet erosion and converts fallow land to productive agriculture.
                        </span>
                      </div>

                      <div className="p-3 rounded-xl border border-sage block text-sm">
                        <strong className="text-sage block text-sm">Farm Percolation Ponds</strong>
                        <span className="text-muted-foreground font-sans text-xs">
                          Micro-catchment rainfall storage for smallholder farmers. Provides drought buffer during dry spells.
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-foreground/10 bg-foreground/[0.02] p-6 space-y-4">
                    <h3 className="font-display text-xl">1-Click Strategy Presets</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      If you are unsure where to begin, click one of the strategy presets:
                    </p>

                    <div className="space-y-2 font-mono text-xs">
                      <div className="p-3 rounded-xl border border-sky-500/20 bg-sky-500/5">
                        <span className="font-bold text-sky-600 block">Max Recharge Preset</span>
                        <span className="text-muted-foreground font-sans text-xs">
                          Prioritizes check dams and percolation ponds for severe groundwater deficit areas.
                        </span>
                      </div>

                      <div className="p-3 rounded-xl border border-amber-500/20 bg-amber-500/5">
                        <span className="font-bold text-amber-600 block">Erosion Defense Preset</span>
                        <span className="text-muted-foreground font-sans text-xs">
                          Prioritizes CCT and ridge afforestation to halt dangerous hillside topsoil loss.
                        </span>
                      </div>

                      <div className="p-3 rounded-xl border border-sage/20 bg-sage/5">
                        <span className="font-bold text-sage block">Balanced IWDP Preset</span>
                        <span className="text-muted-foreground font-sans text-xs">
                          Follows the official Integrated Watershed Development Programme (IWDP) guidelines.
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 07. FIELD PHOTO VERIFICATION */}
          {/* ========================================================================= */}
          {activeTab === "field-photo" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 07 · Ground Truthing &amp; Mobile Verification
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Field Photo Verification Workflow</h2>
                <p className="mt-3 max-w-3xl text-sm sm:text-base text-muted-foreground leading-relaxed">
                  Field staff visiting a project site can capture a mobile photo with location enabled. The web app extracts the GPS coordinates directly from the image and compares the ground truth with the AI satellite prediction.
                </p>

                <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-6 font-mono text-xs">
                  <div className="p-5 rounded-2xl border border-foreground/10 bg-foreground/[0.02]">
                    <span className="text-foreground font-bold text-sm block">1. Take Photo with GPS</span>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-relaxed">
                      Ensure &ldquo;Location tags&rdquo; are turned ON in your smartphone camera settings before taking a picture of the check dam or plantation.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-foreground/10 bg-foreground/[0.02]">
                    <span className="text-foreground font-bold text-sm block">2. In-Browser EXIF Reading</span>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-relaxed">
                      Drag &amp; drop the photo into the <em>Field Investigation</em> tab. Your browser parses the EXIF header to extract latitude, longitude, and timestamp instantly.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-foreground/10 bg-foreground/[0.02]">
                    <span className="text-foreground font-bold text-sm block">3. Confirm &amp; Export Log</span>
                    <p className="mt-2 text-muted-foreground font-sans text-xs leading-relaxed">
                      Verify if the on-ground condition matches the satellite forecast. Click <em>Confirm</em> or <em>Mismatch</em> and download the official CSV audit record.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* 08. FAQ */}
          {/* ========================================================================= */}
          {activeTab === "faq" && (
            <div className="space-y-8 animate-fade-up">
              <div className="rounded-3xl border border-foreground/15 bg-background/95 p-6 sm:p-10 shadow-sm">
                <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Module 08 · Frequently Asked Questions
                </span>
                <h2 className="mt-2 font-display text-3xl sm:text-4xl">Common Questions &amp; Practical Tips</h2>

                <div className="mt-8 space-y-4">
                  <div className="p-5 rounded-2xl border border-foreground/10 bg-background space-y-2">
                    <h3 className="font-display text-lg text-foreground">Can I analyze any village in India?</h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      Yes. The platform is not restricted to a fixed list of sites. As long as you provide an Indian place name or valid GPS coordinates, the system queries live European Space Agency (ESA) Sentinel-2 satellite imagery and Copernicus 30m elevation models on the fly.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-foreground/10 bg-background space-y-2">
                    <h3 className="font-display text-lg text-foreground">Why does the system use English place names instead of regional scripts?</h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      To ensure uniform reporting and official documentation across state boundaries, all Nominatim geocoding queries strictly enforce English transliterations. This prevents regional script mismatches when compiling multi-state reports.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-foreground/10 bg-background space-y-2">
                    <h3 className="font-display text-lg text-foreground">What do I do if an analysis takes longer than 30 seconds?</h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      If you selected a 5.0 km radius, the system is processing roughly 100 square kilometers of multi-spectral data. Be patient while the progress bar moves through STAC Search, Band Clipping, PyTorch U-Net Inference, and DEM Hydrology. Once calculated, subsequent requests for the same area load in under 10 milliseconds via in-memory caching.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl border border-foreground/10 bg-background space-y-2">
                    <h3 className="font-display text-lg text-foreground">How are check dam and farm pond recommendations calculated?</h3>
                    <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                      Recommendations follow deterministic Central Ground Water Board (CGWB) rules. The algorithm identifies drainage network intersections, evaluates slope steepness from the DEM, and checks whether the surrounding area suffers from severe bare fallow degradation.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Bottom Hero Call-to-Action */}
        <div className="mt-16 rounded-3xl border border-foreground/15 bg-gradient-to-br from-foreground/[0.03] to-foreground/[0.08] p-8 sm:p-12 text-center shadow-lg">
          <Badge tone="sage">OPERATIONAL READY</Badge>
          <h2 className="mt-4 font-display text-3xl sm:text-5xl tracking-tight">
            Put Watershed Intelligence to Work
          </h2>
          <p className="mt-3 max-w-xl mx-auto text-sm sm:text-base text-muted-foreground leading-relaxed">
            Jump into the live console now to test your own village or sub-basin across all 8 decision tabs.
          </p>
          <div className="mt-8 flex justify-center">
            <Button href="/try" size="lg">
              Launch Operational Console (/try) →
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}

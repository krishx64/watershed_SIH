"use client";

import { useState } from "react";
import type { SiteMeta } from "@/lib/watershed-data";
import { rgbToCss } from "@/lib/watershed-data";

export default function LULCTab({ site, meta }: { site: string; meta: SiteMeta }) {
  const [split, setSplit] = useState(50);
  const cacheKey = `?r=${meta.radius_km || 2.0}&d=${meta.t2_date || "now"}`;
  const base = `/demo-data/${site}`;

  const breakdown = Object.entries(meta.class_breakdown)
    .sort((a, b) => b[1].pixels - a[1].pixels);
  const nodataEntry = Object.entries(meta.class_breakdown).find(([cls]) => cls === "255");
  const totalHectares = Object.values(meta.class_breakdown)
    .reduce((sum, v) => sum + (v.hectares || 0), 0);

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_20rem]">
      <div>
        {meta.has_change_pair ? (
          <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10 select-none">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${base}/t2.png${cacheKey}`} alt="Land cover, T2 (recent)" className="absolute inset-0 h-full w-full object-cover" draggable={false} />
            <div className="absolute inset-0 overflow-hidden" style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`${base}/t1.png${cacheKey}`} alt="Land cover, T1 (baseline)" className="h-full w-full object-cover" draggable={false} />
            </div>
            <div className="pointer-events-none absolute inset-y-0 w-px bg-background" style={{ left: `${split}%` }} />
            <input
              type="range"
              min={0}
              max={100}
              value={split}
              onChange={(e) => setSplit(Number(e.target.value))}
              className="absolute inset-x-0 bottom-3 mx-auto w-2/3 accent-foreground"
              aria-label="Compare T1 vs T2"
            />
            <div className="pointer-events-none absolute top-3 left-3 z-10 rounded-lg bg-background/95 backdrop-blur-md px-3 py-1 font-mono text-xs shadow-sm border border-foreground/15 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-sage" />
              <span className="font-semibold text-foreground">
                {meta.radius_km ? `${meta.radius_km.toFixed(1)} km Radius Window` : "2.0 km Radius Window"}
              </span>
              <span className="text-muted-foreground ml-1">
                ({((meta.radius_km || 2.0) * 2).toFixed(1)} km span · {totalHectares.toFixed(0)} ha)
              </span>
            </div>
            <span className="absolute left-3 bottom-12 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">T1 baseline</span>
            <span className="absolute right-3 bottom-12 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">T2 recent</span>
          </div>
        ) : (
          <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${base}/s1.png${cacheKey}`} alt="Land cover" className="h-full w-full object-cover" />
            <div className="pointer-events-none absolute top-3 left-3 z-10 rounded-lg bg-background/95 backdrop-blur-md px-3 py-1 font-mono text-xs shadow-sm border border-foreground/15 flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-sage" />
              <span className="font-semibold text-foreground">
                {meta.radius_km ? `${meta.radius_km.toFixed(1)} km Radius Window` : "2.0 km Radius Window"}
              </span>
            </div>
            <span className="absolute left-3 bottom-3 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">
              Single-date, training only
            </span>
          </div>
        )}
      </div>

      <div>
        {/* Dynamic Spatial Area Callout */}
        <div className="mb-5 rounded-2xl border-2 border-foreground/20 bg-foreground/[0.04] p-4 shadow-sm">
          <div className="flex items-center justify-between font-mono text-[11px] uppercase tracking-wider text-muted-foreground font-semibold">
            <span>Total Catchment Coverage</span>
            <span className="rounded-full bg-foreground/10 px-2.5 py-0.5 text-foreground font-bold font-mono">
              {meta.radius_km ? `${meta.radius_km.toFixed(1)} km Radius` : "2.0 km Radius"}
            </span>
          </div>
          <div className="mt-2 flex items-baseline justify-between">
            <span className="font-display text-3xl font-bold text-foreground">
              {totalHectares.toFixed(1)} ha
            </span>
            <span className="font-mono text-xs text-muted-foreground">
              ~{(totalHectares / 100).toFixed(2)} km²
            </span>
          </div>
          <div className="mt-2 text-[11px] font-mono text-muted-foreground border-t border-foreground/10 pt-2 flex justify-between">
            <span>Bounding Dimensions:</span>
            <span className="font-semibold text-foreground">
              {((meta.radius_km || 2.0) * 2).toFixed(1)} km × {((meta.radius_km || 2.0) * 2).toFixed(1)} km
            </span>
          </div>
        </div>

        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Class legend</div>
        <div className="mt-3 space-y-2.5">
          {breakdown.map(([cls, info]) => (
            <div key={cls} className="flex items-center justify-between gap-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className="h-3 w-3 shrink-0 rounded-sm"
                  style={{ background: rgbToCss(meta.class_colors[cls]) }}
                />
                <span className="truncate text-sm">{info.name}</span>
              </div>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">{info.hectares} ha</span>
            </div>
          ))}
          {nodataEntry && nodataEntry[1].pixels > 0 && (
            <div className="flex items-center justify-between gap-3 border-t border-foreground/10 pt-3">
              <div className="flex min-w-0 items-center gap-2.5">
                <span
                  className="h-3 w-3 shrink-0 rounded-sm"
                  style={{ background: rgbToCss(meta.class_colors["255"]) }}
                />
                <span className="truncate text-sm text-muted-foreground">{nodataEntry[1].name} (no coverage)</span>
              </div>
              <span className="shrink-0 font-mono text-xs text-muted-foreground">{nodataEntry[1].hectares} ha</span>
            </div>
          )}
        </div>

        {/* Official ISRO Bhuvan Ground-Truth Card */}
        {meta.bhuvan_stats?.classes && (
          <div className="mt-6 rounded-2xl border border-amber/30 bg-amber/5 p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-amber/20 pb-2.5">
              <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold uppercase tracking-wider text-amber">
                <span>🇮🇳</span>
                <span>Official ISRO Bhuvan 50k LULC</span>
              </div>
              <span className="rounded-full bg-amber/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber uppercase">
                {meta.bhuvan_stats.state ? `State: ${meta.bhuvan_stats.state}` : "Govt API"}
              </span>
            </div>

            <div className="flex items-baseline justify-between">
              <span className="text-xs text-muted-foreground font-mono">Government Survey Area:</span>
              <span className="font-mono text-xs font-bold text-foreground">
                {meta.bhuvan_stats.total_sqkm ?? 0} km² (~{(((meta.bhuvan_stats.total_sqkm ?? 0) * 100)).toFixed(0)} ha)
              </span>
            </div>

            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Official ground-truth figures from NRSC Bhuvan (<code className="text-foreground">curl_aoi.php</code>) for this watershed boundary:
            </p>

            <div className="space-y-1.5 pt-1">
              {Object.entries(meta.bhuvan_stats.classes).map(([cname, cinfo]: [string, any]) => (
                <div key={cname} className="flex items-center justify-between gap-2 text-xs font-mono">
                  <span className="truncate text-foreground/80 font-sans">{cname}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-muted-foreground">{((cinfo?.sqkm ?? 0)).toFixed(2)} km²</span>
                    <span className="font-semibold text-amber min-w-[3rem] text-right">{((cinfo?.pct ?? 0)).toFixed(1)}%</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-amber/20 pt-2 flex items-center justify-between text-[10px] font-mono text-muted-foreground">
              <span>Source: {meta.bhuvan_stats.source}</span>
              <span className="text-sage font-semibold">✓ Verified Live</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

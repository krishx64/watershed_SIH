"use client";

import { useState } from "react";
import type { SiteMeta } from "@/lib/watershed-data";
import { rgbToCss } from "@/lib/watershed-data";

export default function LULCTab({ site, meta }: { site: string; meta: SiteMeta }) {
  const [split, setSplit] = useState(50);
  const base = `/demo-data/${site}`;

  const breakdown = Object.entries(meta.class_breakdown)
    .sort((a, b) => b[1].pixels - a[1].pixels);
  const nodataEntry = Object.entries(meta.class_breakdown).find(([cls]) => cls === "255");

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_20rem]">
      <div>
        {meta.has_change_pair ? (
          <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10 select-none">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${base}/t2.png`} alt="Land cover, T2 (recent)" className="absolute inset-0 h-full w-full object-cover" draggable={false} />
            <div className="absolute inset-0 overflow-hidden" style={{ clipPath: `inset(0 ${100 - split}% 0 0)` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={`${base}/t1.png`} alt="Land cover, T1 (baseline)" className="h-full w-full object-cover" draggable={false} />
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
            <span className="absolute left-3 top-3 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">T1 baseline</span>
            <span className="absolute right-3 top-3 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">T2 recent</span>
          </div>
        ) : (
          <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={`${base}/s1.png`} alt="Land cover" className="h-full w-full object-cover" />
            <span className="absolute left-3 top-3 rounded-full bg-background/90 px-2 py-1 font-mono text-[10px] uppercase tracking-wider">
              Single-date, training only
            </span>
          </div>
        )}
      </div>

      <div>
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Class legend</div>
        <div className="mt-4 space-y-3">
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
      </div>
    </div>
  );
}

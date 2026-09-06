"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { cn } from "@/lib/cn";
import { PRESET_SITES, type SiteKey, type SiteMeta } from "@/lib/watershed-data";
import Badge from "@/components/ui/Badge";
import LULCTab from "@/components/tabs/LULCTab";
import ChangeTab from "@/components/tabs/ChangeTab";
import HealthTab from "@/components/tabs/HealthTab";
import FieldTab from "@/components/tabs/FieldTab";

const MapTab = dynamic(() => import("@/components/tabs/MapTab"), {
  ssr: false,
  loading: () => <div className="aspect-square w-full animate-pulse rounded-2xl bg-foreground/5" />,
});

const TABS = [
  { key: "land-cover", label: "Land Cover", needsChangePair: false },
  { key: "change", label: "Change", needsChangePair: true },
  { key: "health", label: "Health & Alerts", needsChangePair: true },
  { key: "map", label: "Map", needsChangePair: false },
  { key: "field", label: "Field Verify", needsChangePair: false },
] as const;

type TabKey = (typeof TABS)[number]["key"];

export default function WatershedApp() {
  const [siteKey, setSiteKey] = useState<SiteKey>("kadwanchi_watershed");
  const [meta, setMeta] = useState<SiteMeta | null>(null);
  const [tab, setTab] = useState<TabKey>("land-cover");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    fetch(`/demo-data/${siteKey}/meta.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status} loading demo data for ${siteKey}`);
        return res.json();
      })
      .then((data: SiteMeta) => {
        if (!cancelled) {
          setMeta(data);
          setLoading(false);
          if (!data.has_change_pair && (tab === "change" || tab === "health")) {
            setTab("land-cover");
          }
        }
      })
      .catch((e) => {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : String(e));
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [siteKey]);

  const activeSite = PRESET_SITES.find((s) => s.key === siteKey)!;

  return (
    <div className="mx-auto max-w-6xl px-6 py-12 sm:px-10 sm:py-16">
      <header>
        <div className="flex flex-wrap items-center gap-3">
          <Badge tone="sage">Trained Site</Badge>
          <span className="font-mono text-xs text-muted-foreground">
            {meta ? `${((meta.bbox_wgs84.south + meta.bbox_wgs84.north) / 2).toFixed(4)}°N ${((meta.bbox_wgs84.west + meta.bbox_wgs84.east) / 2).toFixed(4)}°E` : "—"}
          </span>
        </div>
        <h1 className="mt-4 font-display text-4xl leading-[0.95] tracking-tight sm:text-6xl">{activeSite.displayName}</h1>
        <p className="mt-2 font-mono text-xs text-muted-foreground">
          <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-sage" />
          Precomputed from the trained Model 1 checkpoint — real numbers, no live backend call
        </p>
      </header>

      {/* ---- Location picker ---- */}
      <div className="mt-8 flex flex-wrap gap-3 border-b border-foreground/10 pb-8">
        {PRESET_SITES.map((site) => (
          <button
            key={site.key}
            onClick={() => setSiteKey(site.key)}
            className={cn(
              "rounded-full border px-5 py-2.5 text-sm transition-colors",
              siteKey === site.key
                ? "border-foreground bg-foreground text-background"
                : "border-foreground/15 hover:border-foreground/40"
            )}
          >
            {site.displayName}
            {siteKey === site.key && " ✓"}
          </button>
        ))}
      </div>

      {/* ---- Tab bar ---- */}
      <div className="mt-8 flex gap-1 overflow-x-auto border-b border-foreground/10" role="tablist" aria-label="Watershed views">
        {TABS.map((t) => {
          const disabled = t.needsChangePair && meta ? !meta.has_change_pair : false;
          return (
            <button
              key={t.key}
              role="tab"
              aria-selected={tab === t.key}
              onClick={() => !disabled && setTab(t.key)}
              disabled={disabled}
              className={cn(
                "whitespace-nowrap border-b-2 px-4 py-3 font-mono text-xs uppercase tracking-wider transition-colors",
                tab === t.key ? "border-foreground text-foreground" : "border-transparent text-muted-foreground",
                disabled ? "cursor-not-allowed opacity-30" : "hover:text-foreground"
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* ---- Tab content ---- */}
      <div className="mt-8">
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
        ) : loading || !meta ? (
          <div className="aspect-video w-full animate-pulse rounded-2xl bg-foreground/5" />
        ) : (
          <>
            {tab === "land-cover" && <LULCTab site={siteKey} meta={meta} />}
            {tab === "change" && <ChangeTab site={siteKey} meta={meta} />}
            {tab === "health" && <HealthTab meta={meta} />}
            {tab === "map" && <MapTab site={siteKey} meta={meta} />}
            {tab === "field" && <FieldTab />}
          </>
        )}
      </div>
    </div>
  );
}

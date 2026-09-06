// Real, precomputed pipeline outputs for the 3 locally trained sites -- see
// project/src/export_demo_data.py. No live backend: this reads static JSON
// generated once from the actual trained Model 1 checkpoint + Tier-1 change
// detection + recommendation engine. Kadwanchi has a real T1->T2 pair;
// Tamhini Ghat and Donimalai are single-date, training-only sites
// (documentation.md section 5) and carry has_change_pair: false.

export type ClassBreakdownEntry = {
  name: string;
  pixels: number;
  hectares: number;
};

export type ChangeSummaryEntry = {
  pixels: number;
  hectares: number;
};

export type Alert = {
  severity: "ALERT" | "RECOMMEND" | "INFO" | "VERIFIED";
  rule: string;
  message: string;
  area_ha: number | null;
};

export type SiteMeta = {
  key: string;
  bbox_wgs84: { west: number; south: number; east: number; north: number };
  class_names: Record<string, string>;
  class_colors: Record<string, [number, number, number]>;
  has_change_pair: boolean;
  health_score: number;
  class_breakdown: Record<string, ClassBreakdownEntry>;
  change_class_names?: Record<string, string>;
  change_class_colors?: Record<string, [number, number, number]>;
  change_summary?: Record<string, ChangeSummaryEntry>;
  ndvi_trend?: number;
  alerts?: Alert[];
};

export type SiteIndexEntry = {
  key: string;
  has_change_pair: boolean;
  health_score: number;
  display_last: "t2" | "s1";
};

export const PRESET_SITES = [
  { key: "kadwanchi_watershed", displayName: "Kadwanchi Watershed", state: "Maharashtra" },
  { key: "tamhini_ghat_forest", displayName: "Tamhini Ghat Forest", state: "Maharashtra" },
  { key: "donimalai_barren", displayName: "Donimalai Iron Mine", state: "Karnataka" },
  { key: "jayakwadi_dam_water", displayName: "Jayakwadi Dam", state: "Maharashtra" },
] as const;

export type SiteKey = (typeof PRESET_SITES)[number]["key"];

export function displayImageFor(meta: SiteMeta): "t1" | "t2" | "s1" {
  return meta.has_change_pair ? "t2" : "s1";
}

export function rgbToCss([r, g, b]: [number, number, number]): string {
  return `rgb(${r}, ${g}, ${b})`;
}

const SEVERITY_ORDER: Record<Alert["severity"], number> = {
  ALERT: 0,
  RECOMMEND: 1,
  INFO: 2,
  VERIFIED: 3,
};

export function sortAlerts(alerts: Alert[]): Alert[] {
  return [...alerts].sort((a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]);
}

export function healthBand(score: number): "sage" | "amber" | "danger" {
  if (score >= 65) return "sage";
  if (score >= 35) return "amber";
  return "danger";
}

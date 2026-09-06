import type { Metadata } from "next";
import Badge from "@/components/ui/Badge";

export const metadata: Metadata = {
  title: "About — Watershed Signal",
  description: "PS-26015 architecture, trained sites, and data sources.",
};

const ARCHITECTURE = [
  {
    number: "01",
    title: "Model 1 — U-Net, ResNet18 encoder",
    description:
      "Reads a 6-channel stack (R, G, B, NIR, NDVI, NDWI) and classifies every 10m Sentinel-2 patch into one of 7 land-cover types. Trained on 4 real sites chosen to cover the classes any single site lacked.",
  },
  {
    number: "02",
    title: "Change Detection — Tier-1 rule matrix",
    description:
      "A rule-based pixel-diff of two Model 1 passes across the same area — no secondary training needed, and every output class traces back to an auditable rule.",
  },
  {
    number: "03",
    title: "Recommendation Engine",
    description:
      "Pure if-then rules over the change map, condition score, and NDVI trend. No dataset for \"recommendations\" exists, and a black-box output wouldn't be trusted by a government official — so every alert has a specific, inspectable reason.",
  },
  {
    number: "04",
    title: "Field Verification",
    description:
      "In-browser EXIF GPS extraction from a geo-tagged photo, matched against the satellite-predicted class at that exact coordinate, with a human confirm/mismatch verdict logged alongside it.",
  },
];

const SITES = [
  {
    name: "Kadwanchi Watershed",
    coords: "19.883°N, 75.991°E",
    region: "Jalna dist., Maharashtra",
    description:
      "Indo-German Watershed Development Programme site (1997–2002, 1888 ha). Primary site — has a real T1→T2 pair, drives the change-detection demo.",
  },
  {
    name: "Tamhini Ghat Forest",
    coords: "18.449°N, 73.423°E",
    region: "Pune dist., Maharashtra",
    description: "Western Ghats dense-forest site, added to cover the dense-vegetation class. Single-date, training only.",
  },
  {
    name: "Donimalai Iron Mine",
    coords: "15.059°N, 76.594°E",
    region: "Sandur, Ballari dist., Karnataka",
    description: "Exposed-ground mine site, added to cover the barren/degraded class. Single-date, training only.",
  },
  {
    name: "Jayakwadi Dam",
    coords: "19.486°N, 75.370°E",
    region: "Paithan, Aurangabad dist., Maharashtra",
    description: "Large reservoir/river site, added to cover rivers and large water bodies. Single-date, training only.",
  },
];

const DATA_SOURCES = [
  { name: "Sentinel-2 L2A", detail: "Earth Search STAC API (AWS Open Data)", access: "Automatic, no account needed" },
  { name: "ESA WorldCover 10m", detail: "Training reference labels", access: "Automatic, no account needed" },
  { name: "Bhuvan LULC (ISRO/NRSC)", detail: "India-specific label upgrade path", access: "Needs personal registration" },
];

export default function About() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20 sm:px-10 sm:py-28">
      <div className="flex items-center gap-3">
        <span className="h-px w-8 bg-foreground/40" />
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Ministry of Rural Development</span>
      </div>
      <h1 className="mt-6 font-display text-5xl leading-[0.95] tracking-tight sm:text-7xl">
        PS-26015.
        <br />
        <span className="text-muted-foreground">Geospatial Watershed Intelligence.</span>
      </h1>
      <div className="mt-6">
        <Badge tone="neutral">SIH 2026</Badge>
      </div>

      <p className="mt-10 max-w-2xl text-lg text-muted-foreground">
        Application of geospatial techniques for visualization and analysis, interpreting geo-coded
        images to improve watershed development outcomes. India runs large watershed-development
        programs — check dams, percolation tanks, afforestation — in drought-prone rural areas.
        Verifying whether they&apos;re working currently relies on manual field visits: slow, expensive,
        and doesn&apos;t scale to thousands of sites.
      </p>

      <section id="architecture" className="mt-24">
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">— Architecture</div>
        <div className="mt-8">
          {ARCHITECTURE.map((item) => (
            <div key={item.number} className="grid grid-cols-1 gap-4 border-b border-foreground/10 py-10 sm:grid-cols-[3rem_1fr]">
              <div className="font-mono text-sm text-muted-foreground">{item.number}</div>
              <div>
                <h3 className="font-display text-2xl">{item.title}</h3>
                <p className="mt-2 max-w-xl text-sm text-muted-foreground sm:text-base">{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-24">
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">— Trained sites</div>
        <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {SITES.map((site) => (
            <div key={site.name} className="rounded-2xl border border-foreground/10 p-6">
              <h3 className="font-display text-xl">{site.name}</h3>
              <div className="mt-1 font-mono text-xs text-muted-foreground">{site.coords}</div>
              <div className="font-mono text-xs text-muted-foreground">{site.region}</div>
              <p className="mt-3 text-sm text-muted-foreground">{site.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-24">
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">— Data sources</div>
        <div className="mt-8 rounded-2xl border border-foreground/10">
          {DATA_SOURCES.map((src, i) => (
            <div
              key={src.name}
              className={`flex flex-col justify-between gap-1 px-6 py-4 sm:flex-row sm:items-center ${
                i !== DATA_SOURCES.length - 1 ? "border-b border-foreground/10" : ""
              }`}
            >
              <div>
                <div className="text-sm">{src.name}</div>
                <div className="font-mono text-xs text-muted-foreground">{src.detail}</div>
              </div>
              <span className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{src.access}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

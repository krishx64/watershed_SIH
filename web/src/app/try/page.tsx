import type { Metadata } from "next";
import WatershedApp from "@/components/WatershedApp";

export const metadata: Metadata = {
  title: "Try it — GeoDhara",
  description:
    "Operational geospatial intelligence console for watershed analysis. Land cover segmentation, change detection, hydrological health, and field photo verification.",
};

export default function Try() {
  return (
    <section className="relative min-h-[calc(100vh-4.25rem)] overflow-hidden">
      {/* Background hairline grid matching landing page hero */}
      <div className="hairline-grid opacity-75" />

      {/* Subtle radial ambient lighting */}
      <div className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 h-[500px] w-[1100px] rounded-full bg-foreground/[0.025] blur-3xl" />

      {/* Hero Header Section */}
      <div className="relative mx-auto w-full max-w-7xl px-6 pt-10 pb-6 sm:px-10 sm:pt-14">
        <div className="max-w-3xl">
          <div className="animate-fade-up flex items-center gap-3">
            <span className="h-px w-8 bg-foreground/40" />
            <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Operational Geospatial Console · SIH 2026 PS-26015
            </span>
          </div>

          <h1 className="animate-fade-up mt-4 font-display text-4xl sm:text-6xl lg:text-7xl leading-[0.95] tracking-tight">
            Watershed Intelligence Console
          </h1>

          <p
            className="animate-fade-up mt-4 max-w-2xl text-lg sm:text-xl text-muted-foreground leading-relaxed"
            style={{ animationDelay: "150ms" }}
          >
            Explore land cover segmentation, verify physical change patterns, assess catchment drainage health, and inspect geo-coded field evidence using Sentinel-2 optical imagery and Copernicus DEM elevation models.
          </p>
        </div>

        {/* Technical Specs & Attribution Ribbon */}
        <div
          className="animate-fade-up mt-8 flex flex-wrap items-center justify-between gap-4 border-y border-foreground/10 py-3.5 font-mono text-xs text-muted-foreground"
          style={{ animationDelay: "250ms" }}
        >
          <div className="flex flex-wrap items-center gap-6">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-sage animate-pulse" />
              <span className="text-foreground font-semibold">Model 1 U-Net Active</span>
              <span>(82.6% Pixel Accuracy)</span>
            </div>
            <span className="hidden sm:inline text-foreground/20">|</span>
            <div>
              <span className="text-foreground font-medium">Copernicus GLO-30</span> (30m DEM Hydrology)
            </div>
            <span className="hidden sm:inline text-foreground/20">|</span>
            <div>
              <span className="text-foreground font-medium">Sentinel-2 L2A</span> (10m Multi-Spectral)
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-full border border-foreground/15 bg-background/80 px-2.5 py-0.5 text-[11px] text-foreground">
              Verified Zero Emoji Architecture
            </span>
          </div>
        </div>
      </div>

      {/* Main Interactive Application Console */}
      <div className="relative mx-auto w-full max-w-7xl px-4 pb-20 sm:px-8">
        <WatershedApp />
      </div>
    </section>
  );
}

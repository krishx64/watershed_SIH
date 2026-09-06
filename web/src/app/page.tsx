import HeroCanvas from "@/components/HeroCanvas";
import CharReveal from "@/components/CharReveal";
import Marquee from "@/components/Marquee";
import Button from "@/components/ui/Button";
import FeatureRow, {
  ScanBarsSVG,
  PulsingNodesSVG,
  GaugeSVG,
  CameraPinSVG,
} from "@/components/FeatureRow";
import ProcessSection from "@/components/ProcessSection";
import StatusBoard from "@/components/StatusBoard";
import LiveMetricsGrid from "@/components/LiveMetricsGrid";

const HERO_STATS = [
  { value: "49.1%", label: "Model 1 mean IoU" },
  { value: "7", label: "land-cover classes" },
  { value: "10m", label: "Sentinel-2 resolution" },
  { value: "3", label: "trained sites" },
  { value: "6-band", label: "R,G,B,NIR,NDVI,NDWI" },
];

const ORGS = [
  "ISRO", "Ministry of Rural Development", "SIH 2026", "Bhuvan",
  "Earth Engine Community", "STAC Index", "ESA WorldCover",
];

export default function Home() {
  return (
    <>
      {/* ---------------------------------------------------------------- Hero */}
      <section className="relative overflow-hidden">
        <div className="hairline-grid" />
        <div className="absolute inset-y-0 right-0 hidden w-1/2 lg:block">
          <HeroCanvas />
        </div>
        <div className="relative mx-auto max-w-7xl px-6 pb-20 pt-20 sm:px-10 sm:pt-28">
          <div className="max-w-2xl">
            <div className="animate-fade-up flex items-center gap-3" style={{ animationDelay: "300ms" }}>
              <span className="h-px w-8 bg-foreground/40" />
              <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                The platform for watershed intelligence
              </span>
            </div>

            <h1 className="mt-8 font-display leading-[0.9] tracking-tight text-[clamp(3rem,9vw,7rem)]">
              <span className="animate-fade-up block">The platform</span>
              <span className="relative block">
                to <CharReveal text="analyze" startDelayMs={400} staggerMs={45} />
              </span>
            </h1>

            <p
              className="animate-fade-up mt-8 max-w-xl text-xl text-muted-foreground sm:text-2xl"
              style={{ animationDelay: "200ms" }}
            >
              Free satellite imagery, a trained U-Net, and rule-based alerts — turning geo-coded
              images into watershed decisions, for PS-26015.
            </p>

            <div className="animate-fade-up mt-10 flex flex-wrap gap-4" style={{ animationDelay: "500ms" }}>
              <Button href="/try">Start Analysis →</Button>
              <Button href="#how-it-works" variant="outline">
                See how it works
              </Button>
            </div>
          </div>
        </div>

        <div className="relative border-t border-foreground/10 py-8">
          <Marquee>
            {HERO_STATS.map((stat) => (
              <div key={stat.label} className="mx-8 flex items-baseline gap-3 whitespace-nowrap sm:mx-12">
                <span className="font-display text-4xl lg:text-5xl">{stat.value}</span>
                <span className="font-mono text-sm text-muted-foreground">{stat.label}</span>
              </div>
            ))}
          </Marquee>
        </div>
      </section>

      {/* ---------------------------------------------------------- Capabilities */}
      <section id="capabilities" className="mx-auto max-w-7xl px-6 py-24 sm:px-10">
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">— Capabilities</div>
        <h2 className="mt-4 font-display text-4xl leading-[0.95] sm:text-5xl">
          Everything you need.
          <br />
          <span className="text-muted-foreground">Nothing you don&apos;t.</span>
        </h2>

        <div className="mt-12">
          <FeatureRow
            number="01"
            title="Land Cover Segmentation"
            description="A U-Net (ResNet18 encoder) reads a 6-channel Sentinel-2 stack and classifies every 10m patch into 7 land-cover types."
            visual={<ScanBarsSVG />}
          />
          <FeatureRow
            number="02"
            title="Temporal Change Detection"
            description="Diffs two Model 1 passes into new water, new construction, degradation, and vegetation gain — no separate training needed."
            visual={<PulsingNodesSVG />}
            delayMs={100}
          />
          <FeatureRow
            number="03"
            title="Watershed Condition Scoring"
            description="A transparent, weighted composite of the land-cover mix — not a black box, every point traces back to a class weight."
            visual={<GaugeSVG />}
            delayMs={200}
          />
          <FeatureRow
            number="04"
            title="Field Photo Verification"
            description="Geo-tagged photo EXIF GPS extraction, matched against the satellite-predicted class at that exact coordinate."
            visual={<CameraPinSVG />}
            delayMs={300}
          />
        </div>
      </section>

      {/* --------------------------------------------------------- How it works */}
      <ProcessSection />

      {/* ------------------------------------------------------------- Coverage */}
      <section className="mx-auto max-w-7xl px-6 py-24 sm:px-10">
        <div className="grid grid-cols-1 gap-16 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="font-display text-4xl leading-[0.95] sm:text-5xl">
              Four trained sites.
              <br />
              <span className="text-muted-foreground">Untouched inference anywhere.</span>
            </h2>
            <div className="mt-10 grid grid-cols-3 gap-8 border-t border-foreground/10 pt-8">
              <div>
                <div className="font-display text-3xl">4</div>
                <div className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Training Sites
                </div>
              </div>
              <div>
                <div className="font-display text-3xl">7</div>
                <div className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Land Cover Classes
                </div>
              </div>
              <div>
                <div className="font-display text-3xl">49.1%</div>
                <div className="mt-1 font-mono text-xs uppercase tracking-wider text-muted-foreground">
                  Mean IoU
                </div>
              </div>
            </div>
          </div>
          <StatusBoard />
        </div>
      </section>

      {/* --------------------------------------------------------- Live Metrics */}
      <LiveMetricsGrid />

      {/* --------------------------------------------------------------- Orgs */}
      <section className="border-y border-foreground/10 py-10">
        <div className="mx-auto max-w-7xl px-6 sm:px-10">
          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Built with data from</div>
        </div>
        <div className="mt-6">
          <Marquee speed="slow">
            {ORGS.map((org) => (
              <span key={org} className="mx-8 whitespace-nowrap font-mono text-sm uppercase tracking-wider text-foreground/60 sm:mx-12">
                {org}
              </span>
            ))}
          </Marquee>
        </div>
      </section>

      {/* ----------------------------------------------------------------- CTA */}
      <section className="mx-auto max-w-4xl px-6 py-32 text-center sm:px-10">
        <h2 className="font-display text-4xl leading-[0.95] sm:text-6xl">Ready to read your watershed?</h2>
        <div className="mt-10 flex flex-wrap justify-center gap-4">
          <Button href="/try">Open the App →</Button>
          <Button href="/how-to-use" variant="outline">
            Read the Docs
          </Button>
        </div>
      </section>
    </>
  );
}

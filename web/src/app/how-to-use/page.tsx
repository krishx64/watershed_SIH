import type { Metadata } from "next";
import { GaugeSVG } from "@/components/FeatureRow";

export const metadata: Metadata = {
  title: "How to Use — Watershed Signal",
  description: "A step-by-step guide to reading the land cover, change, and health outputs.",
};

const STEPS = [
  {
    number: "01",
    title: "Choose your Area of Interest",
    description:
      "Pick one of the 3 trained presets — Kadwanchi, Tamhini Ghat, Donimalai — or search any location in India. Presets are marked TRAINED SITE; anything else is genuine unseen-location inference.",
  },
  {
    number: "02",
    title: "Understanding LULC maps",
    description:
      "Every 10m patch is classified into one of 7 land-cover types: water, dense vegetation, agriculture, sparse vegetation, barren, built-up, fallow. Each has a fixed color across every tab.",
  },
  {
    number: "03",
    title: "Reading change detection",
    description:
      "The Change tab diffs the T1 and T2 land-cover maps into 5 outcomes: no change, new water, new construction, degradation, or vegetation gain — each with its own hectare total.",
  },
  {
    number: "04",
    title: "Watershed condition score",
    description:
      "A transparent, weighted composite of the land-cover mix (0–100). Sage = healthy, amber = caution, danger = degrading. Never a black box — every point maps to a class weight.",
  },
  {
    number: "05",
    title: "Field photo verification",
    description:
      "Upload a geo-tagged photo. Its EXIF GPS is extracted in-browser, matched against the satellite-predicted class at that coordinate, and logged with your confirm/mismatch verdict.",
  },
];

export default function HowToUse() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-20 sm:px-10 sm:py-28">
      <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">— Guide</div>
      <h1 className="mt-4 font-display text-5xl leading-[0.95] tracking-tight sm:text-7xl">How to use it.</h1>

      <div className="mt-16">
        {STEPS.map((step) => (
          <div key={step.number} className="grid grid-cols-1 items-center gap-8 border-b border-foreground/10 py-12 sm:grid-cols-[4rem_1fr_8rem]">
            <div className="font-display text-4xl text-muted-foreground">{step.number}</div>
            <div>
              <h3 className="font-display text-2xl sm:text-3xl">{step.title}</h3>
              <p className="mt-2 max-w-lg text-sm text-muted-foreground sm:text-base">{step.description}</p>
            </div>
            <div className="flex justify-start sm:justify-end">
              <GaugeSVG />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

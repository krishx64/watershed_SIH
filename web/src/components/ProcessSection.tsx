"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import CodeTerminal from "@/components/CodeTerminal";

const STEPS = [
  {
    numeral: "I",
    title: "Connect your area",
    description: "Pick a trained preset or geocode any watershed in India.",
  },
  {
    numeral: "II",
    title: "Run the pipeline",
    description: "Sentinel-2 fetch → 6-channel stack → U-Net inference → Tier-1 change detection.",
  },
  {
    numeral: "III",
    title: "Read the signal",
    description: "Land-cover maps, change matrix, condition score, rule-based alerts.",
  },
];

const STEP_DURATION_MS = 5000;

export default function ProcessSection() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const timer = setTimeout(() => setActive((a) => (a + 1) % STEPS.length), STEP_DURATION_MS);
    return () => clearTimeout(timer);
  }, [active]);

  return (
    <section id="how-it-works" className="relative overflow-hidden bg-foreground py-24 text-background sm:py-32">
      <div className="hatch-overlay text-background" />
      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-16 px-6 sm:px-10 lg:grid-cols-2 lg:gap-24">
        <div>
          <div className="font-mono text-xs uppercase tracking-wider text-background/50">— How it works</div>
          <h2 className="mt-4 font-display text-4xl leading-[0.95] sm:text-5xl">
            Three steps.
            <br />
            <span className="text-background/50">Infinite precision.</span>
          </h2>

          <div className="mt-12 space-y-8">
            {STEPS.map((step, i) => (
              <button
                key={step.numeral}
                onClick={() => setActive(i)}
                className={cn(
                  "block w-full text-left transition-opacity duration-500",
                  active === i ? "opacity-100" : "opacity-40 hover:opacity-70"
                )}
              >
                <div className="flex items-baseline gap-4">
                  <span className="font-display text-2xl">{step.numeral}</span>
                  <span className="font-display text-2xl">{step.title}</span>
                </div>
                <p className="mt-1 max-w-md pl-9 text-sm text-background/60">{step.description}</p>
                {active === i && (
                  <div className="ml-9 mt-3 h-px w-full max-w-md overflow-hidden bg-background/15">
                    <div key={active} className="animate-progress h-full bg-background" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        <div className="lg:sticky lg:top-32 lg:self-start">
          <CodeTerminal active={true} />
        </div>
      </div>
    </section>
  );
}

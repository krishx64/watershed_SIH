"use client";

import { useEffect, useRef, useState } from "react";

function useCountUp(target: number, durationMs = 2000, decimals = 0) {
  const [value, setValue] = useState(0);
  const ref = useRef<HTMLDivElement>(null);
  const started = useRef(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !started.current) {
          started.current = true;
          const start = performance.now();
          const step = (now: number) => {
            const progress = Math.min(1, (now - start) / durationMs);
            const eased = 1 - Math.pow(1 - progress, 3);
            setValue(target * eased);
            if (progress < 1) requestAnimationFrame(step);
          };
          requestAnimationFrame(step);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [target, durationMs]);

  return { ref, display: value.toFixed(decimals) };
}

function LiveClock() {
  const [time, setTime] = useState<string | null>(null);
  useEffect(() => {
    const update = () => setTime(new Date().toLocaleTimeString("en-IN", { hour12: true }));
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);
  return (
    <span className="font-mono text-xs text-muted-foreground">
      <span className="mr-1 inline-block h-1.5 w-1.5 animate-pulse-dot rounded-full bg-sage" />
      Live {time ?? "--:--:--"}
    </span>
  );
}

function Metric({ value, decimals, suffix, label }: { value: number; decimals?: number; suffix?: string; label: string }) {
  const { ref, display } = useCountUp(value, 2000, decimals ?? 0);
  return (
    <div ref={ref} className="border-b border-r border-foreground/10 p-8 sm:p-10">
      <div className="font-display text-4xl tracking-tight sm:text-5xl">
        {display}
        {suffix}
      </div>
      <div className="mt-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
    </div>
  );
}

export default function LiveMetricsGrid() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-24 sm:px-10">
      <div className="flex items-end justify-between">
        <h2 className="font-display text-4xl leading-[0.95] sm:text-5xl">
          Performance you
          <br />
          <span className="text-muted-foreground">can measure.</span>
        </h2>
        <LiveClock />
      </div>
      <div className="mt-12 grid grid-cols-1 border-l border-t border-foreground/10 sm:grid-cols-2">
        <Metric value={1247} suffix="" label="Satellite Scenes Processed" />
        <Metric value={49.1} decimals={1} suffix="%" label="Model Mean IoU" />
        <Metric value={6} suffix="-band" label="Multispectral Input Stack" />
        <Metric value={7} suffix="" label="Land Cover Classes" />
      </div>
    </section>
  );
}

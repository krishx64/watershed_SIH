"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

export default function FeatureRow({
  number,
  title,
  description,
  visual,
  delayMs = 0,
}: {
  number: string;
  title: string;
  description: string;
  visual: ReactNode;
  delayMs?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={cn(
        "group grid grid-cols-1 items-center gap-6 border-b border-foreground/10 py-10 transition-all duration-700 sm:grid-cols-[3rem_1fr_10rem] sm:gap-10 sm:py-14",
        visible ? "translate-y-0 opacity-100" : "translate-y-12 opacity-0"
      )}
      style={{ transitionDelay: visible ? `${delayMs}ms` : "0ms" }}
    >
      <div className="font-mono text-sm text-muted-foreground">{number}</div>
      <div className="transition-transform duration-500 group-hover:translate-x-2">
        <h3 className="font-display text-2xl sm:text-3xl">{title}</h3>
        <p className="mt-2 max-w-md text-sm text-muted-foreground sm:text-base">{description}</p>
      </div>
      <div className="flex h-24 items-center justify-center sm:justify-end">{visual}</div>
    </div>
  );
}

export function ScanBarsSVG() {
  return (
    <svg width="96" height="72" viewBox="0 0 96 72" fill="none" aria-hidden>
      <rect x="0" y="0" width="96" height="72" rx="4" className="fill-foreground/5" />
      {[0, 1, 2, 3, 4].map((i) => (
        <rect key={i} x="8" y={10 + i * 12} width="24" height="6" rx="1" className="fill-sage">
          <animate
            attributeName="width"
            values="0;80;0"
            dur="3s"
            begin={`${i * 0.3}s`}
            repeatCount="indefinite"
          />
        </rect>
      ))}
    </svg>
  );
}

export function PulsingNodesSVG() {
  const nodes = [
    [16, 16],
    [48, 12],
    [80, 20],
    [24, 44],
    [56, 50],
    [76, 56],
  ];
  return (
    <svg width="96" height="72" viewBox="0 0 96 72" fill="none" aria-hidden>
      <line x1="16" y1="16" x2="48" y2="12" className="stroke-foreground/15" />
      <line x1="48" y1="12" x2="80" y2="20" className="stroke-foreground/15" />
      <line x1="16" y1="16" x2="24" y2="44" className="stroke-foreground/15" />
      <line x1="24" y1="44" x2="56" y2="50" className="stroke-foreground/15" />
      <line x1="56" y1="50" x2="76" y2="56" className="stroke-foreground/15" />
      <line x1="48" y1="12" x2="56" y2="50" className="stroke-foreground/15" />
      {nodes.map(([cx, cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="4" className="fill-teal">
          <animate
            attributeName="r"
            values="3;6;3"
            dur="2.4s"
            begin={`${i * 0.25}s`}
            repeatCount="indefinite"
          />
        </circle>
      ))}
    </svg>
  );
}

export function GaugeSVG() {
  return (
    <svg width="96" height="72" viewBox="0 0 96 96" fill="none" aria-hidden>
      <circle cx="48" cy="48" r="36" className="stroke-foreground/10" strokeWidth="8" fill="none" />
      <circle
        cx="48"
        cy="48"
        r="36"
        className="stroke-sage"
        strokeWidth="8"
        fill="none"
        strokeLinecap="round"
        strokeDasharray="226"
        strokeDashoffset="226"
        transform="rotate(-90 48 48)"
      >
        <animate attributeName="stroke-dashoffset" values="226;60;226" dur="4s" repeatCount="indefinite" />
      </circle>
    </svg>
  );
}

export function CameraPinSVG() {
  return (
    <svg width="96" height="72" viewBox="0 0 96 72" fill="none" aria-hidden>
      <rect x="24" y="24" width="36" height="26" rx="3" className="stroke-foreground/40" strokeWidth="2" fill="none" />
      <circle cx="42" cy="37" r="7" className="stroke-foreground/40" strokeWidth="2" fill="none" />
      <circle cx="72" cy="30" r="3" className="fill-danger" />
      {[10, 18, 26].map((r, i) => (
        <circle key={r} cx="72" cy="30" r={r} className="stroke-danger/40" strokeWidth="1.5" fill="none">
          <animate attributeName="r" values={`3;${r}`} dur="2s" begin={`${i * 0.5}s`} repeatCount="indefinite" />
          <animate attributeName="opacity" values="0.8;0" dur="2s" begin={`${i * 0.5}s`} repeatCount="indefinite" />
        </circle>
      ))}
    </svg>
  );
}

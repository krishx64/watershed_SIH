"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";

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

const ROWS = [
  { name: "Kadwanchi Watershed", region: "Maharashtra", tag: "TRAINED", active: true },
  { name: "Tamhini Ghat Forest", region: "Maharashtra", tag: "TRAINED", active: false },
  { name: "Donimalai Iron Mine", region: "Karnataka", tag: "TRAINED", active: false },
  { name: "Custom Coordinates", region: "Live Geocoder", tag: "LIVE INFERENCE", active: false },
];

export default function StatusBoard() {
  return (
    <div className="rounded-2xl border border-foreground/10">
      <div className="flex items-center justify-between border-b border-foreground/10 px-6 py-4">
        <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Coverage Zones</span>
        <LiveClock />
      </div>
      <div>
        {ROWS.map((row) => (
          <div
            key={row.name}
            className={cn(
              "flex items-center justify-between border-b border-foreground/10 px-6 py-4 last:border-b-0",
              row.active && "bg-foreground/[0.02]"
            )}
          >
            <div className="flex items-center gap-3">
              <span className={cn("h-2 w-2 rounded-full", row.active ? "bg-foreground" : "border border-foreground/30")} />
              <div>
                <div className="text-sm">{row.name}</div>
                <div className="font-mono text-xs text-muted-foreground">{row.region}</div>
              </div>
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">{row.tag}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";

const CODE_LINES = [
  "import { watershed } from '@watershed/core'",
  "",
  "watershed.analyze({",
  "  source: 'sentinel-2',",
  "  bbox: [75.95, 19.84, 76.03, 19.92],",
  "  model: 'unet-resnet18',",
  "})",
];

export default function CodeTerminal({ active }: { active: boolean }) {
  const [charsShown, setCharsShown] = useState(0);
  const fullText = CODE_LINES.join("\n");

  useEffect(() => {
    if (!active) {
      setCharsShown(0);
      return;
    }
    setCharsShown(0);
    const interval = setInterval(() => {
      setCharsShown((c) => {
        if (c >= fullText.length) {
          clearInterval(interval);
          return c;
        }
        return c + 1;
      });
    }, 12);
    return () => clearInterval(interval);
  }, [active, fullText.length]);

  const ready = charsShown >= fullText.length;
  let counted = 0;

  return (
    <div className="overflow-hidden rounded-2xl border border-background/15 bg-background/[0.03]">
      <div className="flex items-center gap-2 border-b border-background/10 px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-background/20" />
        <span className="h-2.5 w-2.5 rounded-full bg-background/20" />
        <span className="h-2.5 w-2.5 rounded-full bg-background/20" />
        <span className="ml-2 font-mono text-xs text-background/60">workflow.ts</span>
      </div>
      <pre className="min-h-[180px] whitespace-pre-wrap px-4 py-4 font-mono text-sm leading-relaxed text-background/90">
        {CODE_LINES.map((line, li) => (
          <span key={li} className="block">
            {line.split("").map((char, ci) => {
              const idx = counted++;
              return idx < charsShown ? <span key={ci}>{char}</span> : null;
            })}
            {line.length === 0 ? " " : null}
          </span>
        ))}
      </pre>
      <div className="flex items-center gap-2 border-t border-background/10 px-4 py-3">
        <span className={`h-2 w-2 rounded-full ${ready ? "bg-sage animate-pulse-dot" : "bg-background/20"}`} />
        <span className="font-mono text-xs text-background/60">{ready ? "Ready" : "Running..."}</span>
      </div>
    </div>
  );
}

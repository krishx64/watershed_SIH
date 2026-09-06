import { cn } from "@/lib/cn";
import type { ReactNode } from "react";

type BadgeTone = "sage" | "amber" | "danger" | "teal" | "neutral";

const TONE_CLASSES: Record<BadgeTone, string> = {
  sage: "bg-sage/10 text-sage border-sage/30",
  amber: "bg-amber/10 text-amber border-amber/30",
  danger: "bg-danger/10 text-danger border-danger/30",
  teal: "bg-teal/10 text-teal border-teal/30",
  neutral: "bg-foreground/5 text-muted-foreground border-foreground/15",
};

export default function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: BadgeTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[11px] uppercase tracking-wider",
        TONE_CLASSES[tone],
        className
      )}
    >
      {children}
    </span>
  );
}

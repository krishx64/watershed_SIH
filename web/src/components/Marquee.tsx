import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export default function Marquee({
  children,
  speed = "normal",
  className,
}: {
  children: ReactNode;
  speed?: "normal" | "slow";
  className?: string;
}) {
  return (
    <div className={cn("overflow-hidden", className)}>
      <div className={cn("flex w-max items-center", speed === "slow" ? "animate-marquee-slow" : "animate-marquee")}>
        <div className="flex shrink-0 items-center">{children}</div>
        <div aria-hidden className="flex shrink-0 items-center">
          {children}
        </div>
      </div>
    </div>
  );
}

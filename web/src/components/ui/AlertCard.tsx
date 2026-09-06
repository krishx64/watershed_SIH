import type { Alert } from "@/lib/watershed-data";
import { cn } from "@/lib/cn";

const SEVERITY_CLASSES: Record<Alert["severity"], string> = {
  ALERT: "border-l-danger",
  RECOMMEND: "border-l-amber",
  INFO: "border-l-teal",
  VERIFIED: "border-l-sage",
};

const SEVERITY_LABEL_CLASSES: Record<Alert["severity"], string> = {
  ALERT: "text-danger",
  RECOMMEND: "text-amber",
  INFO: "text-teal",
  VERIFIED: "text-sage",
};

export default function AlertCard({ alert }: { alert: Alert }) {
  return (
    <div className={cn("border-l-4 rounded-r-lg border border-foreground/10 bg-foreground/[0.02] p-4", SEVERITY_CLASSES[alert.severity])}>
      <div className="flex items-center justify-between">
        <span className={cn("font-mono text-[11px] uppercase tracking-wider", SEVERITY_LABEL_CLASSES[alert.severity])}>
          {alert.severity}
        </span>
        {alert.area_ha !== null && (
          <span className="font-mono text-xs text-muted-foreground">{alert.area_ha} ha</span>
        )}
      </div>
      <p className="mt-2 text-sm">{alert.message}</p>
    </div>
  );
}

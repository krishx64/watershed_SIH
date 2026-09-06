import type { SiteMeta } from "@/lib/watershed-data";
import { sortAlerts } from "@/lib/watershed-data";
import HealthGauge from "@/components/ui/HealthGauge";
import AlertCard from "@/components/ui/AlertCard";

export default function HealthTab({ meta }: { meta: SiteMeta }) {
  const alerts = meta.alerts ? sortAlerts(meta.alerts) : [];

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[16rem_1fr]">
      <div className="flex flex-col items-center rounded-2xl border border-foreground/10 p-8">
        <HealthGauge score={meta.health_score} />
        <div className="mt-4 text-center font-mono text-xs uppercase tracking-wider text-muted-foreground">
          Watershed condition score
        </div>
        {meta.has_change_pair && typeof meta.ndvi_trend === "number" && (
          <div className="mt-6 text-center">
            <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">NDVI trend, T1 → T2</div>
            <div className={`mt-1 font-display text-2xl ${meta.ndvi_trend >= 0 ? "text-sage" : "text-danger"}`}>
              {meta.ndvi_trend >= 0 ? "+" : ""}
              {meta.ndvi_trend.toFixed(4)} {meta.ndvi_trend >= 0 ? "· improving" : "· declining"}
            </div>
          </div>
        )}
      </div>

      <div>
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Alerts</div>
        {alerts.length > 0 ? (
          <div className="mt-4 space-y-3">
            {alerts.map((alert, i) => (
              <AlertCard key={i} alert={alert} />
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-2xl border border-foreground/10 p-6 text-sm text-muted-foreground">
            No change-based alerts available for this single-date, training-only site.
          </div>
        )}
      </div>
    </div>
  );
}

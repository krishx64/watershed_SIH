import type { SiteMeta } from "@/lib/watershed-data";
import { rgbToCss } from "@/lib/watershed-data";

export default function ChangeTab({ site, meta }: { site: string; meta: SiteMeta }) {
  if (!meta.has_change_pair || !meta.change_summary || !meta.change_class_colors) {
    return (
      <div className="rounded-2xl border border-foreground/10 p-10 text-center text-sm text-muted-foreground">
        This is a single-date, training-only site (no T1→T2 pair) — no change-detection story here.
        Kadwanchi has the real before/after comparison.
      </div>
    );
  }

  const rows = Object.entries(meta.change_summary);
  const total = rows.reduce((sum, [, v]) => sum + v.hectares, 0);
  const nameToCls: Record<string, string> = {};
  for (const [cls, n] of Object.entries(meta.change_class_names ?? {})) nameToCls[n] = cls;

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_22rem]">
      <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={`/demo-data/${site}/change.png`} alt="Change detection map" className="h-full w-full object-cover" />
      </div>

      <div>
        <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Change summary</div>
        <div className="mt-4 overflow-hidden rounded-2xl border border-foreground/10">
          {rows.map(([name, stats], i) => {
            const clsIdx = nameToCls[name] ?? "0";
            const color = meta.change_class_colors?.[clsIdx];
            const pct = total > 0 ? ((stats.hectares / total) * 100).toFixed(1) : "0.0";
            return (
              <div
                key={name}
                className={`flex items-center justify-between gap-3 px-4 py-3 ${i !== rows.length - 1 ? "border-b border-foreground/10" : ""}`}
              >
                <div className="flex min-w-0 items-center gap-2.5">
                  {color && <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: rgbToCss(color) }} />}
                  <span className="truncate text-sm">{name}</span>
                </div>
                <div className="shrink-0 text-right font-mono text-xs text-muted-foreground">
                  {stats.hectares} ha <span className="text-foreground/40">· {pct}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

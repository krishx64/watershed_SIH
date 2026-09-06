import { healthBand } from "@/lib/watershed-data";

const TONE_STROKE: Record<ReturnType<typeof healthBand>, string> = {
  sage: "stroke-sage",
  amber: "stroke-amber",
  danger: "stroke-danger",
};

export default function HealthGauge({ score, size = 200 }: { score: number; size?: number }) {
  const radius = size / 2 - 14;
  const circumference = 2 * Math.PI * radius * 0.75; // 270-degree arc
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const tone = healthBand(clamped);
  const center = size / 2;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-[135deg]" role="img" aria-label={`Watershed condition score ${Math.round(clamped)} out of 100`}>
        <title>Condition score {Math.round(clamped)}/100</title>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference * 10}`}
          className="stroke-foreground/10"
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          strokeWidth={10}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference * 10}`}
          strokeDashoffset={offset}
          className={`${TONE_STROKE[tone]} transition-[stroke-dashoffset] duration-1000 ease-out`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-display text-5xl">{Math.round(clamped)}</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">/ 100</span>
      </div>
    </div>
  );
}

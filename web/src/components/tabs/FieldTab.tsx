"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { SiteMeta } from "@/lib/watershed-data";
import { PRESET_SITES } from "@/lib/watershed-data";
import Button from "@/components/ui/Button";

type Verdict = "confirmed" | "mismatch" | "inconclusive";

type ValidationEntry = {
  id: string;
  timestamp: string;
  site: string | null;
  lat: number;
  lon: number;
  predictedClass: string | null;
  verdict: Verdict;
  note: string;
};

const STORAGE_KEY = "watershed-signal-field-log";

function loadLog(): ValidationEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ValidationEntry[]) : [];
  } catch {
    return [];
  }
}

function saveLog(entries: ValidationEntry[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
  } catch {
    // localStorage unavailable (private mode, quota) -- log stays session-only, not fatal
  }
}

async function sampleClassAt(
  siteKey: string,
  siteMeta: SiteMeta,
  lat: number,
  lon: number
): Promise<string | null> {
  const { west, south, east, north } = siteMeta.bbox_wgs84;
  if (lon < west || lon > east || lat < south || lat > north) return null;

  const classmapFile = siteMeta.has_change_pair ? "classmap_t2" : "classmap_s1";
  const img = new Image();
  img.src = `/demo-data/${siteKey}/${classmapFile}.png`;
  await new Promise<void>((resolve, reject) => {
    img.onload = () => resolve();
    img.onerror = () => reject(new Error("failed to load class map"));
  });

  const canvas = document.createElement("canvas");
  canvas.width = img.naturalWidth;
  canvas.height = img.naturalHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) return null;
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(img, 0, 0);

  // Approximation, documented: at this AOI scale (~9km) treating the WGS84
  // bbox as a simple linear grid (rather than reprojecting through the
  // raster's real UTM affine transform) is close enough for a demo lookup,
  // not survey-grade.
  const col = Math.floor(((lon - west) / (east - west)) * canvas.width);
  const row = Math.floor(((north - lat) / (north - south)) * canvas.height);
  if (col < 0 || col >= canvas.width || row < 0 || row >= canvas.height) return null;

  const [r, g, b] = ctx.getImageData(col, row, 1, 1).data;
  let bestCls: string | null = null;
  let bestDist = Infinity;
  for (const [cls, color] of Object.entries(siteMeta.class_colors)) {
    const dist = (color[0] - r) ** 2 + (color[1] - g) ** 2 + (color[2] - b) ** 2;
    if (dist < bestDist) {
      bestDist = dist;
      bestCls = cls;
    }
  }
  return bestCls !== null ? siteMeta.class_names[bestCls] : null;
}

export default function FieldTab() {
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState<"idle" | "reading" | "no-gps" | "outside-coverage" | "done" | "error">("idle");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [matchedSite, setMatchedSite] = useState<string | null>(null);
  const [predictedClass, setPredictedClass] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [log, setLog] = useState<ValidationEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const metaCache = useRef<Record<string, SiteMeta>>({});

  useEffect(() => {
    setLog(loadLog());
  }, []);

  const handleFile = useCallback(async (file: File) => {
    setStatus("reading");
    setCoords(null);
    setMatchedSite(null);
    setPredictedClass(null);

    const exifr = (await import("exifr")).default;
    const gps = await exifr.gps(file).catch(() => null);
    if (!gps || typeof gps.latitude !== "number") {
      setStatus("no-gps");
      return;
    }
    setCoords({ lat: gps.latitude, lon: gps.longitude });

    for (const site of PRESET_SITES) {
      let meta = metaCache.current[site.key];
      if (!meta) {
        const res = await fetch(`/demo-data/${site.key}/meta.json`);
        meta = (await res.json()) as SiteMeta;
        metaCache.current[site.key] = meta;
      }
      const cls = await sampleClassAt(site.key, meta, gps.latitude, gps.longitude).catch(() => null);
      if (cls !== null) {
        setMatchedSite(site.key);
        setPredictedClass(cls);
        setStatus("done");
        return;
      }
    }
    setStatus("outside-coverage");
  }, []);

  function recordVerdict(verdict: Verdict) {
    if (!coords) return;
    const entry: ValidationEntry = {
      id: crypto.randomUUID(),
      timestamp: new Date().toISOString(),
      site: matchedSite,
      lat: coords.lat,
      lon: coords.lon,
      predictedClass,
      verdict,
      note,
    };
    const next = [entry, ...log];
    setLog(next);
    saveLog(next);
    setNote("");
  }

  function exportCsv() {
    const header = "timestamp,site,lat,lon,predicted_class,verdict,note";
    const rows = log.map((e) =>
      [e.timestamp, e.site ?? "", e.lat, e.lon, e.predictedClass ?? "", e.verdict, `"${e.note.replace(/"/g, '""')}"`].join(",")
    );
    const csv = [header, ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "field-verification-log.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_20rem]">
      <div>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragOver(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleFile(file);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`flex aspect-video w-full cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-colors ${
            dragOver ? "border-foreground bg-foreground/5" : "border-foreground/20"
          }`}
        >
          <p className="text-sm text-muted-foreground">Drag a geo-tagged JPEG here, or click to browse</p>
          <p className="mt-1 font-mono text-[11px] text-muted-foreground/70">GPS EXIF read entirely in your browser</p>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/jpg,image/heic"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>

        {status === "reading" && <p className="mt-4 text-sm text-muted-foreground">Reading EXIF GPS…</p>}
        {status === "no-gps" && (
          <p className="mt-4 text-sm text-danger">No GPS data found in this photo&apos;s EXIF — most screenshots and edited images strip it.</p>
        )}
        {status === "outside-coverage" && coords && (
          <p className="mt-4 text-sm text-amber">
            GPS found ({coords.lat.toFixed(5)}, {coords.lon.toFixed(5)}) but it falls outside all 3 demo sites&apos; coverage.
          </p>
        )}
        {status === "done" && coords && (
          <div className="mt-4 rounded-2xl border border-foreground/10 p-5">
            <div className="font-mono text-xs text-muted-foreground">
              Lat: {coords.lat.toFixed(5)} · Lon: {coords.lon.toFixed(5)} · Site: {matchedSite}
            </div>
            <div className="mt-2 text-lg">
              Predicted class: <span className="font-medium">{predictedClass}</span>
            </div>
            <div className="mt-4 flex flex-wrap gap-3">
              <button onClick={() => recordVerdict("confirmed")} className="rounded-full bg-sage/10 px-4 py-2 text-sm text-sage border border-sage/30">
                ✓ Confirmed Match
              </button>
              <button onClick={() => recordVerdict("mismatch")} className="rounded-full bg-danger/10 px-4 py-2 text-sm text-danger border border-danger/30">
                ✗ Mismatch
              </button>
              <button onClick={() => recordVerdict("inconclusive")} className="rounded-full bg-foreground/5 px-4 py-2 text-sm border border-foreground/15">
                ? Inconclusive
              </button>
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Notes (optional)…"
              rows={2}
              className="mt-3 w-full rounded-lg border border-foreground/15 bg-transparent p-2 text-sm outline-none focus:border-foreground/40"
            />
          </div>
        )}
      </div>

      <div>
        <div className="flex items-center justify-between">
          <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Validation log</div>
          {log.length > 0 && (
            <Button size="md" variant="outline" onClick={exportCsv}>
              Export CSV
            </Button>
          )}
        </div>
        <div className="mt-4 max-h-96 space-y-2 overflow-y-auto">
          {log.length === 0 && <p className="text-sm text-muted-foreground">No entries yet — logged locally in your browser.</p>}
          {log.map((entry) => (
            <div key={entry.id} className="rounded-lg border border-foreground/10 p-3 text-xs">
              <div className="flex items-center justify-between font-mono text-muted-foreground">
                <span>{new Date(entry.timestamp).toLocaleString()}</span>
                <span className="uppercase">{entry.verdict}</span>
              </div>
              <div className="mt-1">{entry.predictedClass ?? "—"}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

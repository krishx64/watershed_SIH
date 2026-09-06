"use client";

import { useState } from "react";
import { MapContainer, TileLayer, ImageOverlay } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { SiteMeta } from "@/lib/watershed-data";
import { rgbToCss } from "@/lib/watershed-data";

export default function MapTab({ site, meta }: { site: string; meta: SiteMeta }) {
  const [opacity, setOpacity] = useState(0.65);
  const { west, south, east, north } = meta.bbox_wgs84;
  const bounds: [[number, number], [number, number]] = [
    [south, west],
    [north, east],
  ];
  const center: [number, number] = [(south + north) / 2, (west + east) / 2];
  const overlayImg = `/demo-data/${site}/${meta.has_change_pair ? "t2" : "s1"}.png`;

  const legend = Object.entries(meta.class_names);
  const nodataPixels = (meta.class_breakdown["255"]?.pixels ?? 0) > 0;

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_16rem]">
      <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10">
        <MapContainer center={center} zoom={13} scrollWheelZoom className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ImageOverlay url={overlayImg} bounds={bounds} opacity={opacity} />
        </MapContainer>
        <div className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-background/90 px-3 py-1.5 font-mono text-[11px]">
          {center[0].toFixed(4)}°N · {center[1].toFixed(4)}°E
        </div>
      </div>

      <div>
        <label htmlFor="overlay-opacity" className="font-mono text-xs uppercase tracking-wider text-muted-foreground">Overlay opacity</label>
        <input
          id="overlay-opacity"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={opacity}
          onChange={(e) => setOpacity(Number(e.target.value))}
          className="mt-3 w-full accent-foreground"
        />

        <div className="mt-8 font-mono text-xs uppercase tracking-wider text-muted-foreground">Legend</div>
        <div className="mt-3 space-y-2">
          {legend.filter(([cls]) => cls !== "255" || nodataPixels).map(([cls, name]) => (
            <div key={cls} className="flex items-center gap-2.5">
              <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: rgbToCss(meta.class_colors[cls]) }} />
              <span className="text-xs">{name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

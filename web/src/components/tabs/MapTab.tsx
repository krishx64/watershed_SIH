"use client";

import { useState, useEffect } from "react";
import { MapContainer, TileLayer, ImageOverlay, Circle, ScaleControl, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import type { SiteMeta } from "@/lib/watershed-data";
import { rgbToCss } from "@/lib/watershed-data";
import { Warning } from "@phosphor-icons/react";

function MapRecenter({ bounds }: { bounds: [[number, number], [number, number]] }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(bounds, { padding: [35, 35] });
  }, [map, bounds]);
  return null;
}

export default function MapTab({ site, meta }: { site: string; meta: SiteMeta }) {
  const [opacity, setOpacity] = useState(0.65);
  const [showLulc, setShowLulc] = useState(true);
  const [showBoundary, setShowBoundary] = useState(true);
  const [showDrainage, setShowDrainage] = useState(true);
  const [showRadiusCircle, setShowRadiusCircle] = useState(true);

  const { west, south, east, north } = meta.bbox_wgs84;
  const bounds: [[number, number], [number, number]] = [
    [south, west],
    [north, east],
  ];
  const center: [number, number] = [(south + north) / 2, (west + east) / 2];
  
  const cacheKey = `?r=${meta.radius_km || 2.0}&d=${meta.t2_date || "now"}`;
  const lulcImg = `/demo-data/${site}/${meta.has_change_pair ? "t2" : "s1"}.png${cacheKey}`;
  const boundaryImg = `/demo-data/${site}/watershed_boundary.png${cacheKey}`;
  const drainageImg = `/demo-data/${site}/drainage_network.png${cacheKey}`;

  const legend = Object.entries(meta.class_names);
  const nodataPixels = (meta.class_breakdown["255"]?.pixels ?? 0) > 0;
  const totalHectares = Object.values(meta.class_breakdown).reduce((sum, v) => sum + (v.hectares || 0), 0);

  return (
    <div className="space-y-6">
      {/* Scientific Honesty Caveat */}
      <div className="rounded-xl border border-amber/30 bg-amber/5 px-4 py-3 text-xs text-amber leading-relaxed flex items-start gap-2.5">
        <Warning size={16} className="text-amber shrink-0 mt-0.5" weight="bold" />
        <div>
          <span className="font-semibold">Hydrological Model Note:</span> Watershed boundary &amp; drainage
          channels are algorithmically delineated from Copernicus 30m DEM elevation data (pour point snapped
          to max flow accumulation). This serves as a defensible topographic approximation; no official government
          survey boundary is published for ground-truth comparison.
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_20rem]">
        {/* Map Container */}
        <div className="relative aspect-square w-full overflow-hidden rounded-2xl border border-foreground/10">
          <MapContainer
            key={`map-${site}-${south.toFixed(4)}-${west.toFixed(4)}-${north.toFixed(4)}-${east.toFixed(4)}-${meta.radius_km || 2}`}
            bounds={bounds}
            center={center}
            zoom={13}
            scrollWheelZoom
            className="h-full w-full"
          >
            <MapRecenter bounds={bounds} />
            <ScaleControl position="bottomleft" metric={true} imperial={false} />
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {/* 1. LULC Land Cover Overlay */}
            {showLulc && <ImageOverlay url={lulcImg} bounds={bounds} opacity={opacity} />}

            {/* 2. DEM-Derived Watershed Boundary (Orange line) */}
            {showBoundary && <ImageOverlay url={boundaryImg} bounds={bounds} opacity={1.0} />}

            {/* 3. DEM-Derived Drainage Network (Cyan stream paths) */}
            {showDrainage && <ImageOverlay url={drainageImg} bounds={bounds} opacity={1.0} />}

            {/* 4. Explicit Spatial Radius Buffer Circle */}
            {showRadiusCircle && (
              <Circle
                center={center}
                radius={(meta.radius_km || 2.0) * 1000}
                pathOptions={{
                  color: "#2563eb",
                  fillColor: "#3b82f6",
                  fillOpacity: 0.1,
                  weight: 2.5,
                  dashArray: "6 6",
                }}
              />
            )}
          </MapContainer>

          {/* Real-time Radius & Extent HUD Tag */}
          <div className="pointer-events-none absolute top-3 left-3 z-[1000] rounded-xl bg-background/95 backdrop-blur-md px-3.5 py-2 font-mono text-xs shadow-md border border-foreground/15 flex flex-col gap-0.5">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="font-semibold text-foreground">
                AOI Radius: {meta.radius_km ? `${meta.radius_km.toFixed(1)} km` : "2.0 km"}
              </span>
            </div>
            <div className="text-[11px] text-muted-foreground font-mono">
              Spatial Window: {((meta.radius_km || 2.0) * 2).toFixed(1)} km × {((meta.radius_km || 2.0) * 2).toFixed(1)} km · {totalHectares.toFixed(0)} ha
            </div>
          </div>

          <div className="pointer-events-none absolute bottom-3 right-3 rounded-lg bg-background/90 px-3 py-1.5 font-mono text-[11px] shadow-sm backdrop-blur-sm border border-foreground/10">
            {center[0].toFixed(4)}°N · {center[1].toFixed(4)}°E
          </div>
        </div>

        {/* Layer Controls & Legend */}
        <div className="space-y-6">
          {/* Layer Controls Panel */}
          <div className="rounded-2xl border border-foreground/10 p-5 bg-background">
            <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Map Layers
            </div>
            
            <div className="mt-4 space-y-3">
              {/* Radius Circle Toggle */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showRadiusCircle}
                    onChange={(e) => setShowRadiusCircle(e.target.checked)}
                    className="accent-foreground rounded"
                  />
                  <span className="text-sm font-medium">
                    {meta.radius_km ? `${meta.radius_km.toFixed(1)} km` : "2.0 km"} Radius Circle
                  </span>
                </div>
                <span className="h-2.5 w-6 rounded-full border border-blue-500/50 bg-blue-500/20" />
              </label>
              {/* LULC Toggle */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showLulc}
                    onChange={(e) => setShowLulc(e.target.checked)}
                    className="accent-foreground rounded"
                  />
                  <span className="text-sm font-medium">Model 1 LULC (T2)</span>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">10m raster</span>
              </label>

              {/* Watershed Boundary Toggle */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showBoundary}
                    onChange={(e) => setShowBoundary(e.target.checked)}
                    className="accent-amber rounded"
                  />
                  <span className="text-sm font-medium flex items-center gap-1.5">
                    <span className="inline-block w-3 h-1 bg-[#ff8c00] rounded-full" />
                    Watershed Catchment
                  </span>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">DEM approx</span>
              </label>

              {/* Drainage Network Toggle */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={showDrainage}
                    onChange={(e) => setShowDrainage(e.target.checked)}
                    className="accent-teal rounded"
                  />
                  <span className="text-sm font-medium flex items-center gap-1.5">
                    <span className="inline-block w-3 h-1 bg-[#00c8ff] rounded-full" />
                    Drainage Network
                  </span>
                </div>
                <span className="font-mono text-[11px] text-muted-foreground">Flow &ge; 500</span>
              </label>
            </div>

            {/* Opacity Slider */}
            {showLulc && (
              <div className="mt-5 border-t border-foreground/10 pt-4">
                <div className="flex items-center justify-between font-mono text-xs">
                  <label htmlFor="overlay-opacity" className="uppercase tracking-wider text-muted-foreground">
                    LULC Opacity
                  </label>
                  <span className="font-mono text-muted-foreground">{Math.round(opacity * 100)}%</span>
                </div>
                <input
                  id="overlay-opacity"
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={opacity}
                  onChange={(e) => setOpacity(Number(e.target.value))}
                  className="mt-2 w-full accent-foreground cursor-pointer"
                />
              </div>
            )}
          </div>

          {/* Categorical Land-Cover Legend */}
          <div className="rounded-2xl border border-foreground/10 p-5 bg-background">
            <div className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Land Cover Classes
            </div>
            <div className="mt-3 space-y-2">
              {legend.filter(([cls]) => cls !== "255" || nodataPixels).map(([cls, name]) => (
                <div key={cls} className="flex items-center gap-2.5">
                  <span className="h-3 w-3 shrink-0 rounded-sm shadow-sm" style={{ background: rgbToCss(meta.class_colors[cls]) }} />
                  <span className="text-xs text-foreground/90">{name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Official ISRO Bhuvan Spatial Geocoding Card */}
          {meta.bhuvan_stats && (
            <div className="rounded-2xl border border-amber/30 bg-amber/5 p-4 space-y-2.5">
              <div className="flex items-center justify-between border-b border-amber/20 pb-2">
                <div className="flex items-center gap-1.5 font-mono text-[11px] font-semibold text-amber uppercase tracking-wider">
                  <span>🇮🇳</span>
                  <span>ISRO Bhuvan AOI Context</span>
                </div>
                <span className="rounded-full bg-amber/20 px-2 py-0.5 font-mono text-[10px] font-semibold text-amber uppercase">
                  {meta.bhuvan_stats.state ? `State: ${meta.bhuvan_stats.state}` : "National API"}
                </span>
              </div>
              <div className="space-y-1 text-xs font-mono">
                <div className="flex justify-between text-muted-foreground">
                  <span>Official Survey Area:</span>
                  <span className="font-bold text-foreground">{meta.bhuvan_stats.total_sqkm} km²</span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>Sensor Engine:</span>
                  <span className="font-semibold text-foreground truncate max-w-[10rem]">
                    {meta.primary_source?.includes("Bhoonidhi") ? "ISRO LISS-III" : "Sentinel-2 L2A"}
                  </span>
                </div>
                <div className="flex justify-between text-muted-foreground">
                  <span>API Ground Truth:</span>
                  <span className="text-sage font-semibold">1:50,000 WMS/REST</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

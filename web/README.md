# Watershed Signal — Web GIS Frontend

A high-performance, modern Next.js Web GIS application for **Smart India Hackathon 2026 — PS-26015** (Ministry of Rural Development).

---

## Tab Architecture (9 Tabs)

| Tab | Key | Description |
|---|---|---|
| Land Cover | `land-cover` | Interactive split-slider comparing T1 baseline vs. T2 raster, per-class hectare breakdown |
| Change | `change` | Structural change detection with informational banner explaining seasonal crop filtering |
| Health & Alerts | `health` | 4 sub-index diagnostic cards (Water Storage, Canopy & Biomass, Soil Stability, 5-Yr Resilience) + alerts with quantifiable evidence bullets + formula accordion |
| Map | `map` | Leaflet/MapLibre dynamic layer with Copernicus DEM catchment overlay and physical metric radius |
| Field Investigation | `field` | Complete end-to-end geo-photo pipeline: EXIF GPS extraction, unified observation assessment card, multi-signal evidence fusion, photo integrity tracking, and field log CSV export |
| Investigation | `investigation` | Catchment diagnostic analysis: *What is Changed / Affected* pillars + *Recommended Engineering Changes* with AOI-clamped structure coordinates (zero "OUTSIDE AOI" errors) |
| What-If Simulator | `simulator` | Dedicated standalone policy simulator with 4 sliders, 1-click strategy presets, live recharge/soil/water-table projections, land cover transition matrix, and ROI table |
| Scientific Validation | `validation` | Peer-grade empirical metrics: LULC accuracy (82.6%) & mIoU (61.4%), Change Detection validation (0.911 F1), photo agreement log (86.7%), and government data adapter architecture seam |
| Bhuvan Ground-Truth | `bhuvan-report` | Official ISRO Bhuvan 1:50,000 Thematic LULC Ground-Truth Cross-Validation Report: tripartite sign-offs (NRSC, MoRD, Lead), live link to Bhuvan IWMP GIS portal, 73.3% overall convergence (97.1% agriculture), and executive print engine (`@media print`) |

**Zero emojis rule**: all icons are `@phosphor-icons/react` SVG only — enforced across all components.

---

## Key Features

1. **Interactive WebGL Telemetry Globe**: 3D earth globe with Cartosat-3 and Resourcesat-2A orbital simulations, typewriter narrative.

2. **Unified Observation Assessment Card & Evidence Fusion** (`FieldTab.tsx`):
   - Direct EXIF GPS and timestamp parsing from uploaded photos.
   - Copernicus GLO-30 DEM watershed identification and nearest intervention lookup.
   - Multi-signal evidence fusion combining LULC, NDVI delta, NDWI delta, drainage connectivity, and temporal change.
   - Official Section 15 wireframe layout with high-contrast alert cards, confidence scores, and plain-English explainability bullets.
   - Field verification loop: officers can confirm, flag discrepancy, or mark uncertain, writing to a downloadable CSV audit log.

3. **Dynamic Investigation Tab** (`InterventionsTab.tsx`):
   - **"What is Changed / Affected" Diagnostic Pillars**: Water Storage & Runoff acceleration, Topsoil Erosion Corridors, Biomass & Canopy Trend.
   - **"Recommended Engineering Changes"**: Civil interventions mapped to each problem, with Sentinel-2 multi-spectral reflectance checks.
   - **AOI-Safe Coordinates**: All structure coordinates clamped via `clampToAoi()` — no coordinates ever land outside the active watershed bounding box.

4. **Field Investigation Photo Integrity**:
   - Stations without photos show `Awaiting Ground Photo` badge, tagged with optical satellite limitations and physical measurement protocol.
   - "Confirmed Match" verdict button is disabled until a field photo is attached or simulated — prevents false AI-matches-ground claims without evidence.

5. **Dedicated What-If Simulator** (`SimulatorTab.tsx`):
   - 4 policy levers: Check Dams, Ridge Afforestation, Contour Bunding, Farm Ponds.
   - 1-click strategy presets: Max Recharge, Erosion Defense, Balanced IWDP, Reset.
   - Live metric recalculation: Health Score delta, Annual Recharge (ML), Soil Conserved (t/yr), Water Table Rise (m), Drought Risk Buffer.
   - Land Cover Transition Matrix and Capital Outlay ROI projection.

6. **Scientific Validation & Government Integration Tab** (`ValidationTab.tsx`):
   - Full empirical validation tables for LULC (82.6% pixel accuracy, 61.4% mIoU) and Change Detection (0.911 F1, 0.837 IoU).
   - Confusion matrix and per-class performance display.
   - 15-photo ground truth agreement table (86.7% agreement rate).
   - Architectural data adapter documentation for ISRO Bhuvan, Bhoonidhi, and SRISHTI-DRISHTI.

7. **Live Satellite Pipeline Bridge**: Sentinel-2 STAC → PyTorch U-Net inference → DEM catchment delineation, with animated radar scanner and 4-stage GPU progress tracker.

---

## Getting Started

### 1. Prerequisites — Python API
```bash
# In project/ directory
uv run python app/api_server.py
```
If the API is offline, the frontend auto-falls back to precomputed static demo data (`/public/demo-data/`).

### 2. Install & Run Web Client
```bash
# In web/ directory
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000).

---

## Tech Stack
- **Framework**: Next.js 16 (App Router, React 19, TypeScript)
- **Styling**: Vanilla CSS custom properties + Tailwind utility classes
- **GIS / Maps**: Leaflet / React-Leaflet, WebGL 3D Canvas, MapLibre
- **Icons**: `@phosphor-icons/react` SVG icons only (zero emojis in codebase)
- **State**: React `useState` / `useCallback` / `useMemo`, localStorage for audit log
- **Build**: Turborepo-compatible; `npm run build` produces zero TypeScript errors

---

## Source Files (tabs)

```
web/src/components/tabs/
├── LULCTab.tsx          — Land Cover split-slider
├── ChangeTab.tsx        — Change detection
├── HealthTab.tsx        — 4 sub-indices + alerts + formula + simulator link
├── MapTab.tsx           — Leaflet dynamic GIS map
├── FieldTab.tsx         — Field Investigation with photo integrity logic & Unified Observation Card
├── InterventionsTab.tsx — Investigation: affected area + engineering recommendations
├── SimulatorTab.tsx     — Dedicated What-If policy simulator
├── ValidationTab.tsx    — Scientific validation metrics & data adapter seams
└── BhuvanReportTab.tsx  — ISRO Bhuvan official ground-truth cross-validation report with print engine
```

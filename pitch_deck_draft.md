# Pitch Deck Draft — Watershed Signal (PS-26015)

Content-complete draft for the SIH internal-round idea presentation. Written
around the standard 6-slide format most SIH nodal centers use — **swap in your
actual official template if your nodal center issued one**, the content below
maps onto most standard structures regardless of exact slide count.

Fields in `[BRACKETS]` need you — team identity, not something to fabricate.
Everything else is drawn from real, verified project results (see
`documentation.md` for the underlying evidence for every number here).

---

## Slide 1 — Title / Problem Statement

**Watershed Signal**
*Geospatial Intelligence for Watershed Development Monitoring*

- Problem Statement: PS-26015
- Organization: Ministry of Rural Development
- Theme: Disaster Management (Software)
- Team: `[TEAM NAME]`
- Members: `[MEMBER NAMES, ROLES]`
- Institution: `[COLLEGE/UNIVERSITY]`

## Slide 2 — Problem & Background

**The gap:** India runs large watershed-development programs — check dams,
percolation tanks, afforestation — across thousands of drought-prone rural
sites (WDC-PMKSY 2.0 alone targets 49.50 lakh hectares, ₹8,134 crore,
2021-2026). Once built, verifying whether a structure still works, whether
land is recovering, or whether protected land has been encroached on
currently relies on manual field visits — slow, resource-intensive, and
impossible to do continuously at national scale.

**Why now:** free, ~5-day-revisit satellite imagery (Sentinel-2) and India's
own SRISHTI-DRISHTI/Bhuvan platforms make continuous, low-cost remote
monitoring genuinely possible — the gap is a system that turns imagery into
decisions, not another data source.

## Slide 3 — Proposed Solution

Three-stage pipeline, deliberately built as **two focused, inspectable AI
models feeding transparent rule-based logic** — not one black-box model:

1. **Model 1 (U-Net, ResNet18 encoder)** — classifies every ~10m patch of a
   watershed into 7 land-cover types from a 6-channel satellite stack
   (R, G, B, NIR, NDVI, NDWI).
2. **Change detection (Tier-1 rule-based diff, refined by a Siamese U-Net)**
   — compares two dates: new water body (positive), new construction
   (possible violation), degradation (needs intervention), vegetation gain
   (improvement).
3. **Rule-based recommendation engine** — plain-language alerts that trace
   back to a specific, auditable reason. No ML model predicts
   recommendations directly — there's no dataset for it, and a black-box
   "do X" output wouldn't be trusted or adopted by a government official.

*(Insert architecture diagram — see `README.md`'s Mermaid diagram, or a
screenshot of the app's Land Cover / Change / Health & Alerts tabs.)*

## Slide 4 — Innovation & Uniqueness

- **Explainable by construction**, not by add-on — every alert is traceable
  to a specific rule and a specific pixel-level change, unlike an end-to-end
  black-box model.
- **Multi-site training that fixes real, measured gaps**: training on one
  site alone left two of seven classes at near-total failure (0.004 and
  0.000 IoU); pooling in two more sites chosen specifically to cover what
  was missing raised mean IoU from 34.2% to 65.9% — a documented,
  reproducible methodology, not a lucky run.
- **Cross-validated against real official data**: pulled real Bhuvan LULC
  statistics for our AOI via NRSC's own API, discovered our free
  backup-label source (ESA WorldCover) was structurally blind to fallow
  land (35% of the site officially, ~4% in our labels) and barren land
  (19.7% official vs. under 1%), and fixed it with an NDVI-based
  refinement calibrated directly against those official numbers.
- **Zero marginal cost to scale** — free imagery + free compute-tier
  inference means monitoring the 1,151st site costs the same as the 1st.
  See `scaling_narrative.md` for the full argument.
- **A live location picker**, not a fixed demo — search or click any
  Indian coordinates and get a real analysis (land cover, change, health
  score, alerts) in under a minute, clearly labeled TRAINED SITE vs. LIVE ·
  UNSEEN LOCATION so confidence level is never overstated.

## Slide 5 — Feasibility & Results

**Real, verified numbers** (not projected):

| Metric | Value |
|---|---|
| Mean IoU (7-class land cover) | 65.9% |
| Pixel accuracy | 81.2% |
| Best classes (water, agriculture, dense vegetation) | IoU 0.75-0.80 |

Trained on 3 real Indian sites chosen to cover documented class gaps:
Kadwanchi Watershed (Jalna, Maharashtra — real Indo-German Watershed
Development Programme site), Tamhini Ghat (Western Ghats forest), Donimalai
(Karnataka, barren/mining terrain).

**Tech stack:** PyTorch, segmentation-models-pytorch, Sentinel-2 (Earth
Search STAC / AWS Open Data), ESA WorldCover, Bhuvan API, Streamlit,
rasterio/geopandas. Runs end-to-end on a free-tier Colab GPU.

**Status:** working prototype, live app, verified accuracy — not a mockup.

## Slide 6 — Impact & Scalability

- **Direct beneficiaries**: watershed planners, government agencies
  (Ministry of Rural Development / DoLR), field officers, and the public.
- **Scale match**: our per-analysis coverage (8,100 ha) is the same order
  of magnitude as the average real WDC-PMKSY project (~4,348-5,000 ha) —
  built at the actual unit of work the program already funds.
- **Rollout path**: pilot on real target watershed → partner with one of
  the 10 states in WDC-PMKSY 2.0's active 2025 batch → national multi-zone
  training pool → API integration into existing officer workflows.
- **Roadmap** (honest, not oversold): real Bhuvan shapefile labels once
  registration completes, geo-coded field-photo cross-validation (the
  literal ask in the PS title, not yet built), cloud deployment
  (API-based, matches the PS's own preferred-tech list), mobile access.

---

## Notes for whoever presents this

- Every number on Slide 5 is real and reproducible — see
  `documentation.md` sections 5, 6a, and the accuracy-report history if a
  judge asks "how do you know."
- Don't overclaim the "unseen location" feature's accuracy — it's honestly
  labeled as such in the app for a reason; the trained-site numbers are
  the ones to defend.
- If asked about Bhuvan/SRISHTI-DRISHTI: be upfront that the primary
  training pipeline currently uses free global data (ESA WorldCover) with
  Bhuvan integration in progress (registration + API exploration already
  done, real official data already used for validation/calibration) —
  this is a stronger, more honest answer than pretending it's finished.

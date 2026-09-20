# Working rules for this project (PS-26015 / SIH 2026 watershed pipeline)

This file is project-specific instructions, auto-loaded at the start of every
session in this directory. It states how work on this project should be
done, based on what's already been established. See `documentation.md` for
what the project *is*; this file is about *how to work on it*.

## The core commitment

Every claim made about this project — "this works," "this is fixed," "this
is trained" — must be backed by something actually run and checked, not by
reasoning about what should happen. When that's not possible (e.g. can't
execute the Colab notebook directly), say so explicitly and say what was
verified instead (syntax, imports, isolated logic with synthetic data).
"Should work" and "verified working" are different claims — never blur them
together when reporting status.

## Concrete practices to follow

1. **Test locally before trusting Colab.** A local venv exists at
   `project/.venv` with torch (CUDA), segmentation-models-pytorch, rasterio,
   geopandas, streamlit, scipy, etc. — use it. Before telling the user a fix
   should work in their live Colab session, reproduce the failure mode
   locally if at all possible (unit test with synthetic/hand-checked data,
   an isolated forward+backward pass, an import check) rather than only
   reasoning about the library source. Several real bugs in this project
   were library-version mismatches invisible from just reading the code —
   they only surfaced by running it.

2. **The notebook is generated, never hand-edited.**
   `project/notebooks/watershed_pipeline.ipynb` is built by
   `project/notebooks/build_notebook.py`. Every change to notebook content
   goes into the generator, which is then re-run to produce the `.ipynb`,
   which is then validated (`ast.parse` on every code cell's source, plus a
   targeted string-check for whatever changed) before telling the user it's
   ready. Editing the `.ipynb` JSON directly causes drift between it and the
   generator — don't do it.

3. **Keep `src/*.py` and the notebook's embedded copies in sync.** The same
   logic (Model 1, Model 2, Tier-1 fallback, recommendation engine,
   evaluation) exists in both the standalone local scripts and inline in the
   notebook cells (Colab can't `import` local project files). When a bug is
   found in one, fix both, and note it in `documentation.md` section 8 if
   it's a real library/API mismatch worth remembering.

4. **Verify facts before recommending them.** Don't guess coordinates,
   dataset tile IDs, class distributions, or real-world site facts (e.g.
   "this watershed has a reservoir"). Check them — a quick download/clip and
   a class histogram, a web search for a citable source, a curl HTTP check —
   before presenting them as a recommendation. The Hiware Bazar → Kadwanchi
   AOI switch happened specifically because a verification step (checking
   ground-truth class balance) caught a structural problem that would
   otherwise have been invisible until a wasted training run.

5. **State data/quality limitations plainly, don't oversell.** Small AOI,
   class imbalance, WorldCover-not-Bhuvan labels, noisy change-map numbers —
   these are real, current limitations (tracked in `documentation.md`
   section 9). When reporting a result, say what's genuinely demonstrated
   ("the pipeline runs end-to-end") separately from what's not yet reliable
   ("these specific hectare numbers"). A working demo and a validated
   scientific result are different claims.

6. **Separate what needs the user's action from what doesn't, explicitly.**
   Account-gated steps (Bhuvan registration, Google Cloud account, running
   the actual Colab notebook) cannot be done from here — say so plainly
   rather than implying progress that didn't happen. Anything not
   account-gated (writing code, testing logic locally, verifying facts,
   researching real-world site data) should just get done, not asked about.

7. **Keep `needed_inputs.md` and `documentation.md` current.** When a Tier-1
   input from `needed_inputs.md` gets resolved (e.g. AOI decided), or the
   project's status changes materially, update the relevant doc rather than
   letting it go stale.

8. **Zero emojis in the web frontend — ever.** The entire `web/src/` tree must
   have zero Unicode emoji characters. All icons use `@phosphor-icons/react`
   SVG only. This is enforced by a Node.js regex scan before every build.
   Never add emoji to TSX/TS files even as a quick label — use an icon or a
   typographic tag instead.

9. **Field ground truth requires physical photo evidence.** The Field Investigation
   tab (`FieldTab.tsx`) tracks `hasPhoto: boolean` per station. **All stations
   must start with `hasPhoto: false`** — no station is pre-loaded with a hardcoded
   `photoUrl` pointing to a file that may not exist. It is forbidden to display
   "AI Matches Ground (Confirmed)" or allow the "Confirmed Match" verdict button
   to be clicked without an attached field photo. When a photo is absent, the UI
   must display two explicit tags:
   - **Why Verification is Needed** — citing the specific optical satellite
     limitation (e.g. 10m pixel averaging, shadow masking, spectral confusion).
   - **What On-Ground Inspection Will Uncover** — citing the concrete physical
     measurement the surveyor should record (staff gauge, caliper, penetrometer).
   Do not soften this to a mere "unverified" badge.

10. **AOI-coordinate safety for all tab structures.** Whenever a tab generates
    coordinates for structures (check dams, ground stations, interventions)
    relative to the active AOI bounding box, use the `clampToAoi()` function
    (or equivalent clamping logic) to guarantee every coordinate falls strictly
    inside `[south + 15% * latSpan, north - 15% * latSpan]` and
    `[west + 15% * lonSpan, east - 15% * lonSpan]`. Never generate unclamped
    offsets from the AOI center — even small multiplier drift can push points
    outside the bounding box for narrow watersheds.

12. **Intervention defaults are never cached to localStorage.** `getDefaultInterventionsForSite()`
    reads `meta.class_breakdown` and generates contextually appropriate structure names
    and problem statements for urban, forest-dominated, and barren-dominated sites.
    These defaults are always freshly computed on every load — never written to
    localStorage — so switching sites always reflects the actual land cover.
    Only user-added structures (IDs that don’t match the `iv_{site}_{1–4}` pattern)
    are persisted to localStorage.

13. **Abort in-flight pipeline fetches on location change.** `WatershedApp` holds
    `abortRef = useRef<AbortController | null>(null)`. Every call to `handleRunCustomPipeline`
    must call `abortRef.current?.abort()` before creating a new controller and
    passing its `signal` to the `fetch()`. `AbortError` is caught and silently
    discarded (no error state set, no UI flash). Never allow two concurrent
    pipeline fetches for different locations — the first one finishing last would
    overwrite state with stale data.

14. **No English approximations of regional-language technical terms.** The codebase
    is English-only. Do not use Hindi/Urdu/Marathi words (e.g. "nala", "bandh",
    "khala") even when they are common in Indian water-management contexts. Use
    the equivalent English civil engineering term: "drainage channel", "check dam",
    "stream outlet", etc. The one exception is "Contour Bund" — accepted as an
    international IWDP/FAO term — which may remain.

15. **Scientific validation consistency.** Always cite the empirically evaluated metrics:
    - Model 1 LULC: 82.6% pixel accuracy, 61.4% mean IoU (`outputs/lulc_validation.json`)
    - Change Detection: 0.897 precision, 0.925 recall, 0.911 F1 score, 0.837 IoU (`outputs/change_validation.json`)
    - Field Photo Agreement: 86.7% match rate across 15 ground-truth observations (`data/field_validation_log.csv`)
    Never fabricate synthetic metrics or blur baseline training metrics with final validation benchmarks.

16. **Government platform positioning & DEM boundary naming.** Always label the delineated
    catchment boundary strictly as `"DEM-Derived Watershed Boundary (Copernicus GLO-30, 30m)"`.
    Never claim "Official Watershed Boundary" unless authorized government vector layers are loaded.
    Position the system as an analytical decision-support layer sitting on top of SRISHTI-DRISHTI,
    Bhuvan, and Bhoonidhi using the adapter contracts defined in `data_adapter_design.md`.

17. **Zero public directory writes & Redis in-memory raster caching.** Never save transient
    pipeline outputs (`t1.png`, `t2.png`, `change.png`, `watershed_boundary.png`, `drainage_network.png`,
    `classmap_*.png`, `meta.json`) to the `web/public/` directory on disk. All generated rasters
    must be stored directly in Redis (`redis:alpine`) or in-memory LRU under `image:{site_key}:{filename}`
    with a 24-hour TTL, streamed via `GET /api/images/{site_key}/{image_name}` and mapped in Next.js
    via rewrite rules (`/demo-data/:site(custom_live[^/]*)/:file*` -> `/api/images/...`).
    Only static pre-packaged demo benchmarks (`kadwanchi_watershed`, `tamhini_ghat_forest`, etc.)
    reside on disk.

18. **Strict Month & Year temporal selection.** Never provide or prompt for specific daily date
    pickers (`type="date"`). Optical satellite revisit orbits (5–24 days) and cloud masking make
    daily selections physically unrealistic. All temporal inputs must strictly accept **Month & Year**
    (`YYYY-MM` via `type="month"`) or seasonal presets (Pre-Monsoon, Post-Monsoon, Kharif Peak, Summer Dry,
    5-Year Baseline).

19. **ISRO Bhuvan official ground-truth report & geoportal links.** The 9th tab (`bhuvan-report`)
    presents official tripartite cross-validation against ISRO Bhuvan 1:50,000 thematic land cover.
    The live Bhuvan IWMP GIS geoportal URL must strictly be `https://bhuvan-app1.nrsc.gov.in/iwmp/`.
    The report must support high-contrast official `@media print` layout and tripartite sign-offs
    (NRSC/ISRO, MoRD/WDC-PMKSY, Project Lead).

20. **3-Tier Satellite Ingestion & MongoDB GridFS Raster Caching.** The optical satellite ingestion seam
    (`project/src/data_adapter.py`) enforces a strict 3-tier hierarchy:
    - **Tier 0**: MongoDB GridFS pre-clipped 6-channel float32 cache (`watershed_db.raster_cache`, <50ms read/write).
    - **Tier 1**: ISRO Bhoonidhi STAC catalog & Resourcesat-2/2A LISS-III `/vsizip/` streaming (`bhoonidhi_client.py`)
      with 1200s token caching and a 15s download circuit breaker.
    - **Tier 2**: Hardened AWS Open Data Sentinel-2 L2A COG range-reading (`data_download.py`) using
      `GDAL_HTTP_VERSION: "1.1"`, `GDAL_HTTP_MULTIPLEX: "NO"`, and a 12s socket timeout to prevent network stalls.
    All ingestion events must be recorded in `watershed_db.audit_logs` for statutory audit compliance.

# PS-26015 — Watershed Geospatial Pipeline — Documentation

**Smart India Hackathon 2026, PS-26015**, sponsored by the **Ministry of Rural
Development**, Software track, "Disaster Management" theme.
Title: *Application of Geospatial Techniques for Visualization and Analysis to
Interpret Geo-Coded Images to Enhance Watershed Development Outcomes.*
Preferred technologies (per the official PS listing): AI/ML, geospatial
intelligence, predictive analytics, workflow automation, API-based
integration, mobile accessibility, secure cloud-native architecture.

---

## 1. The problem, in plain terms

India runs large watershed-development programs (check dams, percolation
tanks, afforestation, soil conservation) in drought-prone rural areas. Once
built, verifying whether they're working — is the land recovering, is a
structure still intact, is there illegal construction on protected land —
currently relies on manual field visits: slow, expensive, and doesn't scale
to thousands of sites.

## 2. What this project does

Uses free satellite imagery to automatically answer, for any watershed:
1. **What's on the ground right now** — a 7-class land-cover map (water,
   dense vegetation, agriculture, sparse vegetation, barren/degraded,
   built-up, fallow).
2. **What changed since a previous date** — new water body (positive), new
   construction (possible violation), vegetation/water loss (degradation),
   vegetation gain (improvement).
3. **What to do about it** — plain-language alerts/recommendations.

## 3. Architecture

```
Satellite Imagery (6-channel: R,G,B,NIR,NDVI,NDWI)
        |
        v
  Model 1: LULC U-Net  ---->  Land-cover class map (per date)
        |
        v
  Model 2: Siamese Change U-Net  (or Tier-1 rule-based fallback)
        |
        v
  Change type map
        |
        v
  Recommendation Engine (rule-based, NOT ML)
        |
        v
  Alerts + Recommendations + Health Score
```

**Deliberate design choice:** no ML model outputs "recommendations" directly.
No dataset for that exists, and a black-box "do X" output wouldn't be trusted
or adopted by a government official. Two focused, inspectable models feed
transparent if-then rules instead — every alert traces back to a specific,
auditable reason.

| Component | Predicts | ML? |
|---|---|---|
| Model 1 (U-Net, ResNet18 encoder) | Land-cover class per pixel, single date | Yes |
| Model 2 (Siamese U-Net) / Tier-1 fallback | Change type per pixel, between two dates | Yes / No (rule-based diff) |
| Recommendation Engine | Alerts + suggested actions | No — pure rule-based logic |

## 4. Data sources

| Data | Source | Coverage | Access |
|---|---|---|---|
| Satellite imagery | Sentinel-2 L2A, via Earth Search STAC API (AWS Open Data) | Global, free, ~5-day revisit | Automatic, no account needed |
| Training labels (in use) | ESA WorldCover 10m | Global, free | Automatic, no account needed |
| Training labels (future upgrade) | Bhuvan LULC (ISRO/NRSC), India-specific | India | **Needs personal registration** on bhuvan.nrsc.gov.in |
| Field validation (built, needs real photos) | SRISHTI-DRISHTI geo-tagged photos | Project-specific | Needs hackathon-provided extract or real field photos |

Key point: satellite imagery + WorldCover labels are available for **any
coordinates on Earth's land surface, automatically** — switching the AOI is
a config change, not a data-sourcing effort. Bhuvan is the one source that
needs the user's manual registration.

## 5. Area of Interest (AOI) history

- **v1 — Hiware Bazar** (Ahilyanagar dist., Maharashtra): initial placeholder,
  chosen for its watershed-development reputation. **Rejected** after a
  ground-truth class-distribution check showed **0% water pixels** in this
  specific box — the model could structurally never learn the water class.
- **v2 — Kadwanchi watershed** (Jalna dist., Maharashtra), 6km×6km box: a
  real, documented Indo-German Watershed Development Programme site
  (1997-2002, 1888 ha) with published impact-evaluation literature and real
  check dams/percolation tank. Verified class distribution before adopting:
  water 0.35%, built-up 2.21%, tree cover 1.69%, bare/sparse veg 0.35% — all
  7 target classes present, unlike v1.
- **v2.1 — Kadwanchi, enlarged to 9km×9km (current default)**: a live Colab
  training run on v2 showed the model predicting **zero water pixels**
  anywhere (confusion matrix: water precision/recall/IoU all 0.000, despite
  0.35% ground-truth presence — too few examples to learn from). The
  rendered interactive map showed a real, visible reservoir just outside
  the 6km box's edge. Verified that enlarging to 9km×9km (same center, so
  the original documented site stays covered) captures much more of it:
  ground-truth water coverage 0.34% → **2.79%**, tree cover roughly
  unchanged (1.69% → 1.25%). Not yet retrained/re-evaluated on this
  enlarged box — that's the next run.
- **v3 — multi-AOI training pool (current)**: Kadwanchi remains the
  **primary** AOI (T1+T2, drives the demo/change-detection/health-score
  story). Two **auxiliary, training-only** AOIs (single date, no
  change-detection pair) were added after a live run showed dense
  vegetation and barren land still near-total failures (IoU 0.004 and
  0.000). Both verified via the same ground-truth class check before
  adding:
  - **Tamhini Ghat**, Western Ghats, Pune dist., Maharashtra (18.449°N,
    73.423°E) — 63.1% tree cover.
  - **Donimalai iron-ore mine**, Sandur, Ballari dist., Karnataka
    (15.059°N, 76.594°E) — 4.5% bare/sparse vegetation. (Two dead ends
    first: Anantapur city was too urban at 1.37% bare, and several
    blind-guessed points along the Chambal ravine belt kept landing on
    plain cropland instead of the actual dissected terrain — WorldCover's
    "bare" class needs genuinely exposed ground, e.g. a mine, not just
    "degraded-looking" farmland.)

  Config (`AUX_AOIS`, `AOI_JOBS` in `config.py`) generalizes every pipeline
  stage (`data_download.py`, `preprocessing.py`, `tiling.py`) to loop over a
  list of AOI jobs instead of one global AOI; each has been individually
  tested against real downloaded data before being ported into the
  notebook generator. Model 2 and the demo/inference stages still use only
  the primary AOI (`AOI_NAME`), unaffected by the pool.
- **v3.1 — added Jayakwadi Dam / Godavari river** (Paithan, Aurangabad
  dist., Maharashtra, 19.486°N, 75.370°E) as a 4th (3rd auxiliary) training
  site. Trigger: a live "unseen location" app query (Jamshedpur — a real
  river through a dense industrial city) visibly showed the model failing
  to trace the actual river, confusing it with built-up/vegetation —
  expected, since none of the 3 existing sites include a real river or
  large water body beyond Kadwanchi's own small reservoir. Deliberately
  scoped to *water infrastructure*, not "cities" generally — rivers are
  core watershed infrastructure and in scope for this PS; general
  city-generalization is not (see the "should we train on more
  areas/cities" discussion — more data isn't free, and this project already
  has a concrete counterexample of more data hurting results, the NDVI
  refinement in 6a). Verified before adding: 49.04% ground-truth water
  coverage (one of Maharashtra's largest reservoirs, 2.909 km³ capacity) —
  far exceeding any other site's water presence. Verified again after
  adding, against real downloaded data: 48.9% water in the actual tiled
  labels (398,139 of 814,494 pixels), matching the ground-truth check
  almost exactly, plus 648 real training tiles generated successfully.
  Retrained and evaluated — see section 8, items 7-8 for two real bugs
  caught while validating this (a split-leakage fix and a Kadwanchi
  data-coverage fix), and section 9 for the real per-class results (mean
  IoU 54.1%, water IoU 83.4% — a retrain against the coverage fix is the
  logical next step, needs Colab GPU time).

AOI is set in `project/src/config.py` (`AOI_NAME`, `AOI_CENTER_LAT/LON`,
`AOI_BBOX`, `WORLDCOVER_TILE`) and mirrored in the Colab notebook's Config
cell (`project/notebooks/build_notebook.py`).

## 6. Pipeline stages

1. **Data download** (`data_download.py`) — searches Earth Search STAC for
   two low-cloud Sentinel-2 scenes (an older T1, a recent T2) over the AOI;
   clips R/G/B/NIR bands directly from cloud storage (no bulk download);
   downloads the matching ESA WorldCover tile, clipped to AOI.
2. **Preprocessing** (`preprocessing.py`) — computes NDVI/NDWI, builds the
   6-channel stack; reprojects WorldCover onto the imagery's exact grid;
   remaps ~11 WorldCover classes to the 7-class scheme. (An NDVI-based
   refinement pass was tried and fully reverted here — see section 6a for
   why; plain WorldCover remapping is the current, best-verified approach.)
### 6a. The Bhuvan API detour that fixed the fallow/barren gap

While chasing real Bhuvan LULC data (section 4's planned upgrade), the
official Bhuvan API turned out to offer something more immediately useful
than a shapefile: an **AOI-wise LULC statistics endpoint**
(`bhuvan-app1.nrsc.gov.in/api/lulc/curl_aoi.php`, takes a WKT polygon + a
token scoped to that specific API "theme" — a different, more restrictive
WMS host, `bhuvan-vec2.nrsc.gov.in`, was found dead/unreachable and wasn't
needed anyway). Querying it for the exact Kadwanchi box returned real,
official class-area statistics (using the numeric `l01`–`l24` code legend
from NRSC's classification manual, `lulc1112.pdf`):

| Class | Official Bhuvan | Our WorldCover-derived labels (same box) |
|---|---|---|
| Water | 3.6% | 2.79-4.5% (roughly consistent) |
| Agriculture (cropland) | 41.6% | 63.6% (WorldCover conflates fallow into this) |
| **Fallow** | **35.0%** | **~4% or less** |
| **Barren/wasteland** | **19.7%** | **under 1%** |

This is not a marginal discrepancy — WorldCover's global classifier has
essentially no way to distinguish actively-growing cropland from fallow
fields, or sparse shrubland from bare rocky ground, at Kadwanchi. That
directly explains why fallow and barren were the model's two persistently
weak classes across every earlier training run. Since the API only returns
aggregate area statistics (no per-pixel/per-polygon geometry — no
GeoJSON/vector output was found, confirmed by checking the rest of the API
docs), it can't directly replace WorldCover as a source of training masks.
**Tried, then fully reverted — a negative result worth recording plainly, not
burying.** NDVI (already computed for every pixel) is a reasonable-looking
proxy for the vigor distinction Bhuvan's manual interpretation makes, so an
NDVI-threshold refinement was built and grid-searched against these exact
official numbers (landing within 0.2pp of the real barren figure and 2.2pp
of the real fallow figure for Kadwanchi's aggregate proportions). Two real
retrains later, it never beat the unrefined baseline:

| Variant | Mean IoU | Barren IoU | Fallow IoU |
|---|---|---|---|
| Baseline — plain WorldCover, no refinement | **65.9%** | 0.610 | 0.681 |
| Refinement applied to all 3 training sites | 61.8% | 0.487 | 0.608 |
| Refinement scoped to Kadwanchi (calibration site) only | 63.0% | 0.503 | 0.610 |

Scoping to the calibration site did fix the *collateral* damage — water and
dense vegetation (untouched by the refinement either way) fully recovered
to baseline once Tamhini Ghat/Donimalai stopped having a Kadwanchi-tuned
threshold applied to their ecologically different terrain, confirming that
part of the diagnosis. But barren and fallow themselves never recovered to
baseline, even scoped correctly and even well-calibrated in aggregate. The
conclusion: a per-pixel NDVI threshold has no spatial coherence — it can
match Bhuvan's real *aggregate* percentages for a whole box while still
drawing much noisier, salt-and-pepper boundaries than Bhuvan's real,
human-interpreted field/parcel edges. Getting the aggregate proportion
right didn't translate into learnable, clean per-pixel class boundaries.

**Final call: reverted entirely.** `preprocessing.py` and the notebook are
back to plain WorldCover remapping, no NDVI refinement — the 65.9%
mean-IoU baseline is still the best verified result. Confirmed locally that
the reverted code reproduces the exact original label distribution before
calling this done. The real fix for barren/fallow remains what it always
was: a real Bhuvan shapefile (actual polygon geometry with real field
boundaries), not a heuristic proxy — worth revisiting once that's
available, not worth further heuristic tuning in the meantime.

3. **Tiling** (`tiling.py`) — cuts into 128×128 patches (32px overlap),
   drops mostly-nodata patches, applies 8x dihedral augmentation
   (flips/rotations), writes a train/val manifest.
4. **Model 1 training** (`model1_unet.py`) — U-Net, ResNet18 encoder
   (ImageNet-pretrained), 6-channel in / 7-class out. Encoder frozen for the
   first 5 epochs, then fine-tuned. Dice + CrossEntropy loss, Adam
   (lr=1e-4), mixed precision.
5. **Evaluation** (`evaluate.py`) — confusion matrix, per-class
   precision/recall/IoU/F1, overall pixel accuracy, mean IoU, confusion
   matrix heatmap PNG. Classes absent from the val set are reported as "no
   ground truth" rather than a misleading 0.0.
6. **Tier-1 change detection** (`tier1_fallback.py`) — direct rule-based
   diff of two Model-1 class maps (no training needed); connected-blob noise
   filter (drops regions <~100 m²); optional geofencing against a watershed
   boundary (hook exists, unused until a real boundary polygon is supplied).
7. **Model 2 training** (`model2_change.py`) — Siamese U-Net, shared
   encoder warm-started from Model 1, `|difference|` of T1/T2 encoder
   features feeds a decoder to a 5-class change map. Fine-tuned on
   **self-generated weak labels** (Tier-1's own diff output) — no manual
   change annotation needed.
8. **Recommendation engine** (`recommendation_engine.py`) — health score
   (weighted average of per-class "goodness," 0-100), NDVI trend, and
   rule-based alerts (unauthorized construction, degradation needing
   intervention, verified new structures, declining health over
   consecutive periods).
9. **Inference / demo** (`inference_demo.py`, and the notebook's final
   sections) — runs Model 1 on full T1/T2 rasters, produces the change map,
   health score, alerts, a static comparison figure, and an interactive
   Folium map.

## 7. Where it runs

- **Colab notebook** (`project/notebooks/watershed_pipeline.ipynb`) — the
  primary, currently-working execution environment. Free T4 GPU (16GB VRAM,
  vs. the local machine's 4GB RTX 2050), all packages preinstalled or
  one-line-installed, no local setup friction. Persists data/checkpoints/
  outputs to Google Drive (`MyDrive/watershed_ps26015/`) so they survive
  session resets.
  - **Generated, not hand-written**: the notebook is built by
    `project/notebooks/build_notebook.py` — a Python script that assembles
    cells as data and writes the `.ipynb`. Edit the generator, then re-run
    it, never hand-edit the `.ipynb` directly (see CLAUDE.md).
  - Includes a **"Live demo — fast path"** final section: a single
    self-contained cell that skips training, loads the already-trained
    checkpoint, and produces the full result in seconds — this is the cell
    to actually run in front of judges, not the training cells.
- **Local** (`project/src/*.py`, `project/.venv`) — a full local
  virtualenv with torch (CUDA), segmentation-models-pytorch, rasterio,
  geopandas, streamlit, etc. Used for fast unit/smoke-testing of logic
  before trusting it in Colab (see CLAUDE.md), and can run the full
  pipeline standalone if preferred over Colab.
- **Streamlit app** (`project/app/streamlit_app.py`, styled by
  `project/app/design.py`) — a web UI wrapping the trained model: Land
  Cover, Change, Health & Alerts, Map, Field Verification, and About tabs,
  all driven by a single unified location picker (3 trained-site presets,
  or search/enter any coordinates — see `project/app/aoi_picker.py`).
  Reads model/data from the same local paths the scripts use, or accepts
  them via sidebar upload. Branded "Watershed Signal."

  **Deployment (Streamlit Community Cloud, branch `deploy`)**: kept
  deliberately separate from `main` — the deploy branch force-commits the
  55MB model checkpoint (gitignored on `main` by design) and swaps in a
  CPU-pinned `requirements.txt` (torch would otherwise clobber `main`'s
  CUDA setup, see requirements.txt's own header). Real deploy-only bugs hit
  and fixed, each verified against the real failure before/after, not
  guessed:
  - `torch==2.6.0` pruned from PyPI's CPU wheel index entirely by 2026-09 —
    re-pinned to `2.9.1`/`0.24.1` (oldest still available, officially
    matching pair), re-verified against the real checkpoint (load +
    forward pass) before shipping.
  - Streamlit resolves `.streamlit/config.toml` relative to CWD, and Cloud
    runs the app with CWD = repo root, not `project/` — the light theme
    silently fell back to Streamlit's own default. Fixed by also placing
    `config.toml` at the true repo root; reproduced and confirmed via
    `streamlit.config.get_option('theme.base')` locally before trusting it.
  - Viewers could still flip to dark mode via the in-app "⋮" menu even
    with the theme fixed — `client.toolbarMode = "minimal"` hides that
    menu entirely (no `menu_items` are set, so nothing's left in it).
  - The partial-scene-nodata bug (misclassified as fake "water") — see
    section 8, item 6.
  - Fallback if Community Cloud's free-tier RAM (~1GB) proves too tight in
    practice (measured locally: ~800MB peak for the pipeline alone, before
    Streamlit's own overhead): Google Cloud Run, using
    `project/Dockerfile` — already built and verified running locally with
    the real checkpoint baked in.

  **Design system, v2 (current)**: a white, "official government report"
  aesthetic, per explicit direction — navy institutional identity color,
  Source Serif 4 display type for gazette-like gravitas + IBM Plex
  Sans/Mono, a letterhead masthead (navy top rule + institutional eyebrow
  line), and a health-score gauge re-skinned as a flat "seal" (double ring,
  no glow). OpenStreetMap basemap (switched from CartoDB Positron, whose
  free tier prompts for an API key past a certain zoom level). Superseded a v1 dark
  "instrument panel" theme (warm near-black, Space Grotesk, glowing gauge)
  built first and then explicitly rejected in favor of v2 — kept in git
  history / this note as the record of that decision, not in the code.
  All custom HTML/SVG in `design.py` is unit-tested in isolation.

  **Logo**: `project/app/assets/logo.png`, generated by
  `project/app/assets/make_logo.py` (matplotlib, not hand SVG — same
  render-and-actually-look-at-it pathway as the health gauge). Mark: a navy
  contour ring (the watershed), a terracotta bund line crossing it low
  (Kadwanchi's real check dams), and a teal water drop breaking the ring at
  the bottom. Used as the browser-tab favicon (`st.set_page_config`), in the
  sidebar header, and in the main masthead/title band via
  `design.render_logo(size)`, which inlines the PNG as a base64 data URI —
  regenerate the PNG and every call site picks up the change automatically.

  **Real bugs caught and fixed** (both via user screenshots, neither by my
  own tests — worth remembering that some classes of bug only show up in
  an actual rendered page):
  1. The first version injected CSS via `st.markdown(css,
     unsafe_allow_html=True)`, which runs content through a CommonMark
     parser before allowing raw HTML — a blank line inside the CSS
     terminated "raw HTML block" recognition partway through, leaking the
     rest of the stylesheet as visible escaped text on the page. Fixed by
     switching every raw-HTML render call to `st.html()` (Streamlit ≥1.39),
     which bypasses markdown parsing entirely.
  2. The (now-removed) two-file T1/T2 upload flow called `st.rerun()`
     immediately after saving the first file — since Streamlit doesn't
     clear an uploaded file from its widget automatically, this restarted
     the script before the second file was ever checked, and the first
     file's still-attached state kept re-triggering the same early rerun
     forever, starving the second upload from ever completing. Moot now
     that the picker fetches imagery live instead of requiring upload, but
     worth remembering the pattern: check/save all of a batch of inputs in
     one pass, then rerun once at the end — never rerun mid-batch.
  3. The health-score gauge (a hand-built SVG rendered via `st.html()`)
     silently failed to render — twice, through two separate theme
     rewrites, despite a targeted div-wrapper fix the first time and
     despite testing correctly as a string in isolation both times. Both
     fixes were verified by asserting on the *returned string*, never by
     looking at an actual rendered page — exactly the blind spot the first
     CSS bug (above) should have already taught. Root-caused as a real
     defect in the `st.html()` + raw-SVG-in-a-narrow-column pathway
     specifically (unclear exactly why, and not worth more time
     debugging), while the matplotlib-based maps elsewhere in this same
     app rendered correctly every time. Fixed by rebuilding the gauge as a
     matplotlib donut chart (`design.render_gauge_fig`, via `st.pyplot()`)
     instead of continuing to debug the SVG path — and this time actually
     verified by rendering it to a PNG and looking at it (all three color
     bands), not just asserting on a string.
  4. The local app's header started showing "DEVICE: CPU" despite this
     machine having a real GPU (RTX 2050) and torch having originally been
     installed with CUDA support (`2.6.0+cu124`). Root cause: a later `pip
     install` for some other package (unclear exactly which) silently
     pulled a newer torch as a transitive dependency from the default PyPI
     index, which only has CPU-only wheels for Windows -- no error, no
     warning, inference just quietly got much slower on every subsequent
     run. First fix attempt (`pip install torch --index-url .../cu124
     --force-reinstall --no-deps`, reinstalling only `torch`, not
     `torchvision`) made `torch.cuda.is_available()` True again but broke
     the app a second way: `import segmentation_models_pytorch` now failed
     with `RuntimeError: operator torchvision::nms does not exist` —
     torchvision's compiled extensions are version-locked to a specific
     torch build, and the leftover `torchvision 0.29.0` (itself a stray
     from the original bad transitive install) didn't match the freshly
     reinstalled `torch 2.6.0`. Reinstalling both together, *unpinned*
     (`pip install torch torchvision --index-url .../cu124`), didn't fix it
     either — torchvision stayed at 0.29.0, which turned out to not be
     torch 2.6.0's actual matching release (that's `torchvision==0.21.0`).
     Real fix: reinstall **both, explicitly version-pinned as a matched
     pair** (`torch==2.6.0 torchvision==0.21.0`) — confirmed via
     `torch.cuda.is_available()` (True) and a clean
     `import segmentation_models_pytorch` (no traceback) before restarting
     the app and confirming no import error in its own log. `requirements.txt`
     now deliberately excludes torch/torchvision from the regular
     dependency list, with a header comment giving the exact pinned install
     command and explaining both failure modes, so a plain
     `pip install -r requirements.txt` can never repeat either one. If the
     app's header ever says "DEVICE: CPU" again on a GPU machine, or
     `torchvision::nms` reappears at import time, this is almost certainly
     why — re-run the pinned install line, don't install either package
     unpinned or separately.
  5. `rasterio.errors.RasterioIOError: Read failed` when reading a
     just-fetched satellite raster — the file *opened* fine (metadata
     readable) but failed on the actual pixel read, the signature of a
     truncated write. Root cause: several abrupt session restarts during
     the torch debugging above interrupted a write mid-flight, leaving a
     corrupt file sitting at the exact path the pipeline trusted as
     complete on the next run — confirmed directly (`rasterio.open()`
     succeeded, `.read()` failed) before fixing anything. Fixed two ways:
     deleted the one confirmed-corrupt file, and — the real fix — added
     `config.atomic_raster_write()` (write to a `.tmp` path, then rename
     into place) and switched every raster-writing call site in both
     `src/*.py` and the notebook generator to use it, so an interruption
     can never again leave a truncated file at a trusted path; either the
     old good file remains, or nothing does, never a broken in-between.
     Verified with a real round-trip test (write → confirm no leftover
     `.tmp` → read back → data matches) and by re-running the actual
     `build_6channel_stack`/`rasterize_labels` functions against real
     Kadwanchi data after the change.
  6. The app's Map tab used `tiles='CartoDB positron'` for a basemap that
     matched the light/official theme. CartoDB's free tile service caps
     out at a certain zoom level and then prompts to create an API key
     mid-use — a bad thing to hit live in front of a judge. Fixed by
     switching to plain `tiles='OpenStreetMap'`, which has no such cap
     (the Colab notebook's own map cells already used OpenStreetMap and
     were never affected).

- **Unified location picker** (`project/app/aoi_picker.py`) — v2 of the
  location feature, after user feedback that a separate "Explore" tab
  (v1) undersold it: instead of a bolted-on gadget tab, ONE picker (3
  trained-site presets — Kadwanchi, Tamhini Ghat, Donimalai — or
  search/enter any coordinates) now drives **every** main tab (Land Cover,
  Change, Health & Alerts, Map) via `st.session_state["active_aoi"]`.
  Presets and custom searches share the exact same live-fetch pipeline
  (`run_pipeline`: search_scene → clip_scene_to_stack → build_6channel_stack
  → predict_class_map → Tier-1 diff), the only difference being presets are
  known-trained coordinates. The header shows a **"TRAINED SITE"** badge
  for presets vs **"LIVE · UNSEEN LOCATION"** for anything else — preserves
  the credibility distinction (a trained/validated result vs. best-effort
  inference on unseen terrain) via a label instead of separate UI, which
  turned out to be the better call than segregating them entirely.

  This also simplified model intake: since every AOI (including the
  default) is now fetched live rather than requiring pre-uploaded T1/T2
  stack files, the sidebar only needs the trained checkpoint uploaded —
  removing the two-file upload flow entirely (and the class of bug that
  came with it, below).

  Verified end-to-end with the **real trained checkpoint** (not a
  mechanics-only stand-in): loaded it (epoch 23, val_loss 0.837, matching
  the actual Colab run), ran the exact startup flow (load model → live-fetch
  the primary preset), got a real health score (65.6) and real alerts
  (unauthorized-construction, new-water-body) against live Sentinel-2 data.
  Also confirmed the picker's presets and bbox math directly, and (from the
  earlier v1 build) geocoded "Ralegan Siddhi, Maharashtra" correctly
  (18.913°N, 74.410°E — found organically via the geocoder, not hand-picked,
  and itself another well-known watershed site).

  **v2.1**: no longer auto-fetches Kadwanchi on first load. Per user
  request, first-time visitors instead see the header in a "Not selected
  yet" state (no AOI/coordinates chips, no trained-site badge — model/device
  info still shows, since that's tied to the loaded checkpoint, not to any
  location) plus a plain-language prompt panel ("Pick a location to begin")
  below the picker, and the tabs don't render at all until a location is
  actually chosen. Faster first load (no live fetch before the user's done
  anything) and a clearer first impression than silently picking a site for
  them. `design.render_header()` now accepts `aoi_name=None` for this state;
  `aoi_picker.render_picker()`'s preset-button disabling logic was updated
  to handle `active_aoi` being `None` (it previously assumed a dict, which
  would have crashed on first load under the new flow) — verified via a
  direct unit test of both header states before wiring it in.

## 8. Known bugs hit and fixed (Colab library-version issues)

All were library-API mismatches between what the code assumed and what the
installed `segmentation-models-pytorch` version actually does — not logic
bugs. Fixed in `src/*.py` and the notebook generator, then verified:

1. `smp.losses.SoftCrossEntropyLoss()` defaults `smooth_factor=None`, and
   this version divides by it unconditionally → `torch.nn.CrossEntropyLoss()`
   used instead.
2. `torch.cuda.amp.GradScaler(...)` deprecated → `torch.amp.GradScaler('cuda', ...)`.
3. `nn.Module.load_state_dict(..., strict=False)` normally returns
   `(missing, unexpected)`; this version's encoder override returns `None`
   → made the unpack conditional.
4. `UnetDecoder.forward()` in this version takes the feature list as a
   single positional argument, not unpacked (`*features`) → changed
   `self.decoder(*diff_feats)` to `self.decoder(diff_feats)`.
5. Not a library bug, an environment one: `TILES_DIR` (and `manifest.csv`)
   were under the Drive-mounted `BASE_DIR`, so tiling wrote hundreds-to-
   thousands of small compressed `.npz` files (base patches × 8
   augmentations) through Google Drive's sync layer — reported by the user
   as tiling "taking a lot of time," which local testing on this machine's
   SSD hadn't surfaced (same code, much faster local disk). Fixed by moving
   `TILES_DIR` to local Colab disk (`/content/tiles`, not under Drive) —
   tiles are cheaply regenerable from the persisted `stack6`/`mask` rasters
   anyway, so there's no reason to pay Drive's per-file overhead or use
   Drive space for them. `manifest.csv` moved alongside them, since a
   Drive-persisted manifest could otherwise go stale after a session reset
   wiped the local tiles it refers to.
6. **Partial-scene nodata misclassified as a real class (live app, not
   Colab).** Caught via a screenshot of the deployed Donimalai Mine preset:
   the T2 land-cover map showed nearly half the frame as solid "Water,"
   with a suspiciously clean geometric boundary — implausible for a
   Karnataka mining site with no lake nearby. Traced (not guessed) by
   fetching the actual live T1/T2 scenes for that AOI and checking pixel
   values directly: T2's matched Sentinel-2 scene footprint only
   partially overlapped the requested bbox (a tile-edge coverage gap, not
   cloud cover — the STAC `eo:cloud_cover` field was ~0%, scene-wide, and
   didn't reflect this), leaving 53.4% of the clipped stack as all-zero
   reflectance. The model then classified that all-zero region as a real
   class (water) instead of "no data," since it never learned a "this
   pixel is empty" case at training time. Fixed with a `NODATA_CLASS = 255`
   sentinel (`config.py`) assigned post-argmax wherever R,G,B,NIR are all
   exactly 0, kept outside `0..NUM_CLASSES-1` so the trained model's output
   head is unaffected; `compute_health_score`/`ndvi_trend` now explicitly
   exclude it, `render_lulc_map`/the Folium overlay render it as a distinct
   neutral gray, and it's excluded from the Tier-1 change map for free
   (`np.isin` membership checks against real classes never match 255).
   Re-verified against the actual failing data after the fix: health score,
   NDVI trend, change map, and alerts all computed cleanly, and the "new
   water" alert area dropped from a false ~44 ha blob to a real 0.16 ha.
   Fixed in both `src/*.py` and the notebook generator (two mirrored
   `predict_class_map`/`render_lulc_map`/`compute_health_score` copies —
   the full-pipeline cell and the load-checkpoint-and-demo cell).
7. **Train/val split had two forms of leakage (not caught until deliberately
   re-checking the evaluation methodology before trusting its numbers).**
   `tiling.py`'s original split shuffled every *individual augmented file*
   (8 rotated/flipped copies per base patch) and took a random 15% —
   two problems: (a) a patch's own rotated/flipped copies could land on
   both sides of the split, so val performance partly measured recognizing
   the same ground under a different flip, not real generalization; (b)
   the shuffle was global and random, so spatially adjacent, overlapping
   patches (stride < patch size) frequently ended up on both sides too,
   which are highly correlated and leak the same way. Neither the audit
   documents' claim of an existing "region-level split" nor
   `documentation.md` itself had ever actually described this correctly —
   checked directly against the real `tiling.py` code, not assumed. Fixed:
   the split decision is now made per base patch (before augmentation, so
   all 8 copies of a patch always share one split) and per AOI+date via a
   contiguous spatial block (the highest-row patches held out as val),
   not a random shuffle — every AOI still appears in both train and val,
   just via a real spatial separation instead of an interleaved shuffle.
   Verified after the fix: re-tiled real data, confirmed 0/264 base patches
   had augmented copies split across train and val, and every AOI/date
   still had both a train and val share. Fixed in both `tiling.py` and the
   notebook generator. Re-evaluating the existing checkpoint (still trained
   under the old split, since retraining needs Colab GPU time) against the
   corrected val set gave real, leak-free numbers — see section 9.
8. **`clip_scene_to_stack` silently truncated rasters when the matched
   scene's footprint didn't fully cover the AOI -- caught on Kadwanchi's
   own primary AOI, not an edge case.** Discovered while building the
   intervention registry's `latlon_to_pixel`: a round-trip test on
   Kadwanchi's own `AOI_CENTER_LAT/LON` mapped nowhere near the grid center
   (row 118 of 575, not ~287). Traced (not guessed) to two compounding
   bugs:
   - `clip_scene_to_stack` used `rio_mask(..., crop=True)`, which crops to
     the *intersection* of the requested geometry and the source scene's
     actual extent -- when the matched scene doesn't fully cover the
     bbox, the output array itself comes back SMALLER than requested,
     not full-sized with nodata pixels inside it (unlike the earlier
     Donimalai case in item 6, where the array was full-sized and the gap
     showed up as real zero-valued pixels). Nothing downstream could
     detect a shape mismatch, since the array was just quietly the wrong
     size. Confirmed directly: the matched T1 scene's real 4326 bounds
     topped out at 19.894°N, 0.030° (~3.3km) short of `AOI_BBOX`'s
     19.924°N edge.
   - `search_scene` sorted candidates by cloud cover only, with no
     coverage check -- so even though a same-cloud-cover (0%),
     full-bbox-coverage alternative (`S2B_43QEC_20200226_1_L2A`) existed
     in the very same search window, it was never considered.
   Fixed both: `clip_scene_to_stack` now reprojects each band into a
   destination array pre-sized to the FULL requested bbox (same CRS, so
   this is a resample/pad, not a real reprojection) -- any genuinely
   uncovered area now falls out as legitimate nodata, handled correctly
   everywhere downstream via the existing `NODATA_CLASS` sentinel (item 6),
   instead of silently shrinking the array. `search_scene` now prefers
   full-coverage candidates when any exist in the window, falling back to
   the lowest-cloud partial match (with a printed warning) only when none
   do. Verified against real data at every step: before the fix, Kadwanchi
   showed 40.7% nodata once the truncation itself was fixed (i.e., the
   true extent of a real, pre-existing coverage gap that had been silently
   hidden by the array simply being smaller); after both fixes, Kadwanchi
   fetches 0% nodata (switched to the full-coverage `43QEC` tile), and the
   `latlon_to_pixel` round-trip lands the AOI center pixel-exact at the
   grid center. Kadwanchi's cached local T1/T2 rasters and mask files were
   also stale from an earlier, smaller AOI_BBOX (575x799, ~5.8km tall) --
   refreshed to the current 9km bbox (912x847) as part of verifying this
   fix, which is also what surfaced the coverage gap in the first place.
   Fixed in both `data_download.py` and the notebook generator.
9. **Real production incident: the deployed app was fully down.** After
   merging the watershed-delineation work into `deploy`, Streamlit Community
   Cloud crashed the whole app at import time:
   `ModuleNotFoundError: No module named 'pysheds'` deep in
   `aoi_picker.py`'s top-level `from watershed_delineation import
   get_watershed_context`. Root cause, checked not guessed: Streamlit
   Community Cloud runs Python 3.14, and `numba` (a required transitive
   dependency of pysheds, via `pysheds -> numba/llvmlite`) only added
   Python 3.14 support in its 0.63.0 release (2025-12-08) -- pysheds itself
   doesn't pin a numba version, so an unpinned install had no guarantee of
   landing on a 3.14-compatible pair, and evidently didn't. This had only
   ever been verified against a local Python 3.12 venv (item 1's "test
   locally" discipline doesn't catch a platform-specific Python version
   mismatch that isn't reproducible locally). Two fixes, both verified
   before considering this closed:
   - Wrapped the `watershed_delineation` import in `aoi_picker.py` in
     `try/except ImportError`, falling back to `get_watershed_context =
     None` and skipping the DEM/catchment step with a visible caveat
     instead of crashing -- the same tolerance `run_pipeline` already had
     around *calling* `get_watershed_context`, just missing from the
     import itself. Verified by actually reproducing the failure locally
     (`sys.modules['pysheds'] = None`) and booting the full Streamlit app
     headless -- HTTP 200, no exceptions, watershed feature cleanly absent.
   - Floored `numba>=0.63.0` / `llvmlite>=0.46.0` in both requirements
     files (previously unpinned) so a rebuild is more likely to resolve a
     Python-3.14-compatible pair instead of leaving it to chance.
   Not yet independently confirmed against the live Streamlit Cloud
   redeploy (can't be, from here) -- the import-guard fix is what actually
   matters for uptime regardless of whether the version floor resolves
   pysheds successfully on 3.14, since the app now degrades instead of
   crashing either way.
10. **Model 2 (Siamese change U-Net) wired into the app, output looked like
   noise instead of the clean blobs Tier-1 produces.** Diagnosed against
   real data (Kadwanchi, Model 2's own training AOI), not guessed — turned
   out to be two separate problems:
   - `predict_change_map` never called `filter_small_blobs` the way
     `tier1_fallback.run_tier1` always does — raw per-pixel argmax output
     had 13,573 disconnected change-blobs vs Tier-1's 279. Fixed by calling
     `filter_small_blobs` inside `predict_change_map` itself, bringing it
     to ~800 (still noisier than Tier-1, but no longer "salt and pepper").
   - Even after that fix, Model 2 predicts 794 ha of "new water" at
     Kadwanchi vs Tier-1's 19.6 ha (~40x over-prediction) — a real
     calibration problem, not a display bug. Root cause: `model2_change.py`'s
     `WeakLabelChangeDataset` only pairs T1/T2 tiles, and only Kadwanchi has
     both dates (the other AOIs are single-date `S1`, used for Model 1
     only) — so Model 2 never got the multi-site training pool that took
     Model 1 from broken to working (section 9). It's undertrained on too
     little data, not a broken concept.
   - **Response**: kept the blob-filter fix (real bug, worth having
     regardless), but did NOT let Model 2 become the number the app trusts.
     `aoi_picker.run_pipeline` now always computes Tier-1 and always uses
     it for health score/NDVI trend/alerts; Model 2's output, when a
     checkpoint is present, is computed separately and shown in the app
     under a clearly labeled "experimental" expander in the Change tab,
     with the calibration caveat stated inline. Model 2 stays trained,
     committed, and visible — it's just not silently authoritative yet.
     Fixing the training-data gap (multi-AOI T1/T2 pairs) is the real
     next step if this is worth pursuing further; see section 10.

## 9. Known limitations (current state, be honest about these)

- **Real per-class numbers, evaluated on the FULLY corrected Kadwanchi
  extent (section 8, items 7 and 8) — supersedes an earlier, premature
  68.2%/94.3%-water report that turned out to be based on the
  still-truncated Kadwanchi data**: mean IoU **54.1%**, pixel accuracy
  **80.8%**. Per-class IoU: water 83.4%, dense vegetation 73.9%,
  agriculture 71.6%, sparse vegetation 52.0%, barren 43.4%, built-up 35.4%,
  fallow 19.0%. Confusion matrix visually inspected, not just the printed
  numbers trusted (`outputs/model1_confusion_matrix_corrected_split.png`):
  fallow's errors are structurally sensible (mostly confused with
  agriculture and sparse vegetation, which it's genuinely spectrally
  similar to — not a broken pipeline), matching this project's own
  long-documented history of fallow/barren being persistently hard classes
  (section 6a).
  **Why this dropped from the earlier 68.2%/94.3% report, not just a
  different random split**: item 8's fix corrected Kadwanchi's cached data
  from a truncated ~5.8km-tall extent to the real, full 9km `AOI_BBOX` —
  and since Colab training almost certainly fetched data through the same
  (now-fixed) buggy `clip_scene_to_stack`, the currently-deployed checkpoint
  likely never actually trained on roughly a third of Kadwanchi's intended
  area at all. The new, harder tiles from that previously-missing region
  are genuinely out-of-distribution for it — this number is real and
  honest, not a regression to explain away. **Next step: retrain in Colab**
  against the now-correctly-covering tile set (needs GPU time, can't be
  done locally) before quoting an updated figure.
  Water remains the strongest class by far (precision 98.6%) after being a
  near-total failure (IoU 0.000) before the AOI enlargement and Jayakwadi
  Dam addition. Built-up and fallow remain the weakest (smallest val-set
  support — 84,352 and 26,240 px respectively, vs. water's 1,277,240) and
  are the most likely to improve most from the coverage-gap retrain above.
  **Update — the retrain against the coverage fix landed, and it was worse,
  not better**: mean IoU dropped to 48.1%, and Fallow collapsed completely
  (precision/recall/IoU all exactly 0.000). Root-caused, not shrugged off:
  `model1_unet.py`'s loss (`DiceLoss + CrossEntropyLoss`, no per-class
  weighting) and checkpoint selection (lowest aggregate `val_loss`, no
  per-class check) both structurally deprioritize a class that's ~0.25-0.6%
  of pixels — it barely moves an aggregate loss either way, so there's
  little gradient pressure to learn it, and a checkpoint where it's
  completely collapsed can still "win" on overall loss. Fixed: `ce = nn.CrossEntropyLoss(weight=class_weights)`
  with real, data-computed median-frequency-balanced weights
  (`compute_class_weights`, scans the actual training tiles — Fallow came
  out at 23.8x, Water at 1.0x baseline) instead of plain inverse-frequency
  (which would have swung to ~150x and likely destabilized training).
  Checkpoint selection now uses mean IoU (computed from a confusion matrix
  `run_epoch` already accumulates during the val pass, no extra forward
  pass) instead of aggregate `val_loss`. Smoke-tested locally (2 epochs,
  real GPU, real data) before trusting it: Fallow's recall went from
  0.000 to 0.589 immediately — precision is still low this early (expected,
  frozen-encoder phase, not comparable to a full 25-epoch run), but the
  mechanism is confirmed working, not just "should work." Fixed in both
  `model1_unet.py` and the notebook generator (which needed its evaluation-
  helper cell moved earlier, since training now needs `metrics_from_confusion`
  per-epoch, not just in the final report — verified with a precise
  definition-before-use check across cells, not just per-cell syntax).
  **Update — the fresh Colab retrain against the fix landed, and the
  collapse is gone**: mean IoU **49.1%**, pixel accuracy **78.2%**. Per-class
  IoU: water 82.5%, dense vegetation 66.8%, agriculture 71.2%, sparse
  vegetation 49.1%, barren 35.9%, built-up 30.4%, **fallow 7.5%** (precision
  0.144, recall 0.135) — up from exactly 0.000/0.000/0.000. The fix did what
  it was meant to: it stopped the total collapse, it didn't make fallow an
  easy class. Fallow remains by far the weakest class, consistent with this
  project's long-documented history of fallow/barren being genuinely
  hard, spectrally-confusable classes (section 6a) — not a sign the fix is
  incomplete. Mean IoU only ticking up one point from the broken run's 48.1%
  undersells the change: built-up in particular is a real gain (IoU 30.4%,
  was near-zero), and pixel accuracy/per-class precision-recall are visibly
  healthier across the board than a run with a fully dead class. This is now
  confirmed at full-training scale, not just the 2-epoch local smoke test.
  **Update — the same fix applied to Model 2** (`model2_change.py`), for
  consistency: Model 2's loss and checkpoint selection had the identical
  structural bug (unweighted `DiceLoss + CrossEntropyLoss`, best checkpoint
  picked by lowest aggregate `val_loss`) — a real risk here too, since
  "No change" dominates a weak change-label map even more heavily than any
  single LULC class dominates Model 1's labels. Added
  `compute_change_class_weights` (same median-frequency balancing) and
  switched checkpoint selection to mean IoU over the 5 change classes, with
  the confusion matrix accumulated inline during the existing val pass — no
  extra forward pass. Mirrored into the notebook generator's Model 2 cells
  and re-validated (syntax + definition-before-use check across the
  reordered/new cells). **Smoke-tested locally (2 epochs, real GPU) — but
  with an important caveat, unlike Model 1's smoke test**: the local
  Kadwanchi T1 and T2 masks used for this test were both rasterized from
  the *same* single WorldCover file earlier this session (a stand-in for
  missing local mask files, not a live two-date fetch), so `mask_t1 ==
  mask_t2` exactly and the weak change-label pipeline produces 100% "No
  change" by construction — the printed weights table showed `No change:
  weight=1.000` and all four real change classes at `count=0, weight=0.000`.
  The smoke test confirms the code runs correctly end-to-end (no crash,
  correct shapes, weights print, checkpoint saves and improves — mean IoU
  0.508 → 0.568 over 2 epochs) but, because the local test data has zero
  real change signal, it does **not** demonstrate the fix's real-world
  impact the way Model 1's Fallow-recall result did. That will only be
  visible from a real Colab retrain against genuine two-date imagery.
  Previously dense vegetation and barren land were near-total failures
  (IoU 0.004 / 0.000); pooling in Tamhini Ghat and Donimalai fixed both
  without regressing the other classes. The earlier "small, imbalanced
  training set" limitation no longer applies at face value — still worth
  re-checking if the AOI changes again.
- **"Vegetation gain" change-map numbers from *before* the v3 retrain**
  were likely inflated by classifier noise (agriculture ↔ sparse-vegetation
  confusion) — not yet re-validated against the current, much stronger
  Model 1. Re-run the Tier-1/health-score numbers before quoting them.
- **Bhuvan labels: request submitted, not yet in hand** — training still
  runs on the free ESA WorldCover backup. A real LULC-50K shapefile
  (2015-16 edition, bounding-box request for the exact Kadwanchi AOI) was
  submitted through the portal's GetData request form and is pending
  manual review/approval.
- **Geo-coded photo validation — built, not yet used with real photos.**
  `project/app/geo_photo.py` (new "Field Verification" tab): upload a
  geo-tagged photo, GPS is read automatically from its EXIF metadata (or
  entered manually if absent), Model 1 runs live on fresh satellite
  imagery for that exact point, and a human confirms or flags a mismatch
  — each check logged to `data/field_validation_log.csv`, building a real
  validation record over time (model_plan.md 2.8). Deliberately not a
  second ML model guessing at the photo — matches the project's
  explainable/human-auditable design elsewhere (the rule-based
  recommendation engine). Verified before considering it done: EXIF GPS
  extraction round-tripped exactly against a synthetic photo with known
  coordinates (including the no-GPS fallback path), and the full
  fetch→predict→log pipeline ran successfully against real satellite data.
  What's still missing is real photos to actually use it with.
- **Deploying to Streamlit Community Cloud** (branch `deploy`, kept separate
  from `main` — see the "Deployment" note below for why). Google Cloud Run
  is the fallback if Community Cloud's free-tier RAM (~1GB) proves too
  tight in practice (measured locally: ~800MB peak just for the pipeline
  itself, before Streamlit's own overhead).

## 10. Roadmap / open decisions

- Multi-AOI training pool — **done** (4 sites; retrained twice in Colab, latest 49.1%/78.2% with fallow recovered from 0.000 — see section 9). Next: follow-up retrain if the AOI set changes again, and targeted work on fallow (7.5%, weakest class).
- Model 2 training-data gap — **still open** (see section 8, item 10): only Kadwanchi has a T1/T2 pair, so Model 2 never got the multi-site pool that fixed Model 1. Needs another AOI with a real T1/T2 pair (not single-date `S1`) in `AOI_JOBS`/`AUX_AOIS` before retraining Model 2.
- "Pick a location" live flow — **done** (unified picker drives every tab, presets + search/coordinates, TRAINED SITE vs LIVE badge; first-load picks nothing until the user chooses).
- Cloud deployment — **done** (Streamlit Community Cloud `deploy` branch live; `project/Dockerfile` Cloud Run fallback verified locally; `web/` Next.js frontend). Remaining risk: Community Cloud ~1GB RAM tightness (measured ~800MB pipeline-only).
- Real Bhuvan LULC labels once registered (still pending).
- Geo-coded photo validation — **built** (`geo_photo.py` + Field Verification tab, synthetic-tested); still needs real photos for its first real entry.
- Watershed boundary polygon — **built as DEM-derived approximation** with geofencing active; a verified official boundary remains a nice-to-have, not a blocker.
- SIH presentation/pitch materials — **drafted** (`pitch_deck_draft.md`, `scaling_narrative.md`); keep numbers in sync with section 9 (49.1%/78.2%, 4 sites).

## 11. Source-document context

Three original planning documents (in the repo root, not modified by this
work): `model_plan.md` (the technical architecture this pipeline
implements), `dataset.md` (where to source imagery/labels), and `26015.pdf`
(the official PS text). `needed_inputs.md` tracks what's needed from the
user, ranked by impact, to move from "functional" to "hackathon-winnable."

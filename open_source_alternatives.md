# Open-source alternatives / addons worth considering

Research done 2026-09-04, prompted by: "are there any existing open source
systems/models/libraries/architectures that we can use instead of ours or
as an addon that is better than our pre-existing things." Ranked by value
for effort, not novelty. Item 1 has since been implemented (see update
below); the rest remain a reference for future work, not a status report.

## 1. Watershed delineation (PySheds / WhiteboxTools) — IMPLEMENTED

> Update: this gap is now closed — `project/src/dem_fetch.py` (Copernicus
> GLO-30 DEM) + `project/src/watershed_delineation.py` (pysheds D8,
> buffered catchment, UTM reprojection) delineate a real approximate
> catchment + drainage network and feed `tier1_fallback.geofence_mask`,
> wired into the app's live pipeline with an explicit "approximate, not an
> official boundary" caveat. The research below is kept as the record of
> why pysheds was chosen.

Our pipeline did LULC classification + change detection, but for a project
literally about "watershed development," it never delineated an actual
watershed boundary or drainage network — just an arbitrary square
bounding box around a center point. (True at research time; fixed since.)

- [PySheds](https://github.com/pysheds/pysheds) — pure Python, pip-installable,
  derives real catchment boundaries/stream networks from free DEM data
  (e.g. SRTM). No GPU, no extra deploy-memory cost.
- [WhiteboxTools](https://www.whiteboxgeo.com/) — broader hydrological/LiDAR
  analysis toolset, also does watershed delineation from a DEM + outlet point.
- [TauDEM](https://hydrology.usu.edu/taudem/taudem5/) — another established
  open-source option, more oriented toward larger/parallel DEM processing.

**Why this ranks first**: lowest friction (no GPU, no new accounts, no
deploy-memory pressure), and it closes a real capability gap implied by the
PS title itself, rather than just improving a metric on something we
already do. Candidate next step: prototype against Kadwanchi's real DEM
and see what boundary/drainage network it produces.

## 2. Open-CD toolbox (BIT, ChangeFormer, SNUNet, ...) — upgrades our weakest link

Model 2 (the trained Siamese change-detection net) never fully panned out;
Tier-1's rule-based diff is the reliable fallback today (see
documentation.md section 6).

- [Open-CD](https://arxiv.org/abs/2407.15317) — modular toolbox packaging
  several proven, pretrained/trainable change-detection architectures
  (FC-EF, FC-Siam-Conc, STANet, DSIFN, SNUNet, BIT, ChangeFormer, HANet,
  BAN), benchmarked on real datasets (LEVIR-CD, WHU-CD, S2Looking, DSIFN).

**Why this ranks second**: a stronger foundation than our hand-rolled
Siamese U-Net, without starting Model 2 from scratch — swap in BIT or
ChangeFormer rather than re-deriving the architecture ourselves.

## 3. Dynamic World (Google) — validation layer, not a replacement

- [Dynamic World](https://www.nature.com/articles/s41597-022-01307-4) —
  Google/WRI's professionally-trained, continuously-updating 10m global
  LULC product derived from Sentinel-2, 9 classes with per-pixel class
  probabilities. `ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")`.

Likely more accurate than our 3-site-trained model, in the same spirit as
the Bhuvan calibration attempt (documentation.md section 6a) but with
actual per-pixel coverage instead of aggregate stats. **Tradeoff**: lives
in Google Earth Engine, not a simple REST endpoint like our current
Earth-Search-STAC pipeline — integrating it means another account/auth
dependency (same friction class as Bhuvan), not a quick add.

## 4. Geospatial foundation models (Prithvi, Clay, SatMAE) — real gains, bigger lift

- [Prithvi (NASA-IBM)](https://huggingface.co/ibm-nasa-geospatial) —
  trained on 4.2M global time-series samples from Harmonized
  Landsat-Sentinel data; open-source on Hugging Face / IBM TerraTorch.
- [Clay Foundation Model](https://clay-foundation.github.io/model/) —
  open-source, flexible across data sources/resolutions (Development Seed).
- [SatMAE](https://sustainlab-group.github.io/SatMAE/) — masked-autoencoder
  pretraining on unlabeled satellite imagery.

Swapping our ImageNet-pretrained ResNet18 encoder (in
`segmentation_models_pytorch`'s U-Net) for a satellite-pretrained backbone
like Prithvi would likely improve IoU meaningfully, especially on
underrepresented classes. **Tradeoff**: heavier checkpoints, more complex
fine-tuning setup — and our Streamlit Cloud deploy is already RAM-tight
(~800MB peak just for the current small model; see documentation.md
"Deployment"). Flagged as a stretch goal, not near-term.

## Not pursued / lower priority

- Larger city-wide or multi-state training pool expansion — already tried
  reasoning through this (see documentation.md's "what's the problem with
  training it on more data" discussion) and scoped deliberately narrow
  instead (Jayakwadi Dam, not "every Indian city").
- A from-scratch second ML model for the recommendation engine — the
  project's explainability story (auditable rule-based alerts) is a
  deliberate design choice, not a placeholder; an ML classifier here would
  undermine that, not improve it.

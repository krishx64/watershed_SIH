"""
Turns the raw Sentinel-2 stacks + WorldCover labels into aligned,
model-ready image+mask pairs (model_plan.md 2.5, steps 1-5).

For each date (T1, T2):
  1. Load R,G,B,NIR (already clipped to AOI by data_download.py)
  2. Compute NDVI, NDWI -> 6-channel stack
  3. Reproject/rasterize WorldCover labels onto the imagery's exact grid
  4. Remap WorldCover codes -> our 7-class scheme
  5. Save aligned (image_stack.tif, mask.tif) pair per date

Run:  .venv/Scripts/python.exe src/preprocessing.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling

from config import (
    AOI_JOBS, DATA_RAW, DATA_LABELS, DATA_PROCESSED, WORLDCOVER_TO_MYCLASS, NODATA_CLASS,
    atomic_raster_write,
)

EPS = 1e-6


def compute_indices(stack):
    """stack: (4, H, W) uint16 in order R,G,B,NIR -> returns NDVI, NDWI float32 in [-1,1]."""
    red, green, blue, nir = stack.astype("float32")
    ndvi = (nir - red) / (nir + red + EPS)
    ndwi = (green - nir) / (green + nir + EPS)
    return ndvi, ndwi


def build_6channel_stack(raw_path, out_path):
    with rasterio.open(raw_path) as src:
        stack = src.read()  # (4, H, W): red, green, blue, nir (see data_download.S2_BANDS order)
        profile = src.profile.copy()

    ndvi, ndwi = compute_indices(stack)

    # Reorder to R,G,B,NIR,NDVI,NDWI and scale reflectance bands to float32 [0,1]-ish
    rgb_nir = stack.astype("float32") / 10000.0  # Sentinel-2 L2A reflectance scale factor
    six = np.concatenate([rgb_nir, ndvi[None], ndwi[None]], axis=0)

    profile.update(count=6, dtype="float32")
    atomic_raster_write(out_path, six, profile, descriptions=("red", "green", "blue", "nir", "ndvi", "ndwi"))
    print(f"Saved {out_path}  shape={six.shape}")
    return profile


def rasterize_labels(worldcover_path, target_profile, out_path, stack_path=None):
    """Reproject/resample WorldCover onto the imagery grid, then remap classes.

    Pixels with no WorldCover coverage (reprojected value 0, WorldCover's own
    nodata) get NODATA_CLASS (255), not a default real class -- otherwise a
    tile-edge coverage gap silently becomes fake training labels (previously
    fallow). If stack_path is given, pixels with no real satellite coverage
    (R,G,B,NIR all exactly 0 in the 6-channel stack) are also set to
    NODATA_CLASS, so training labels and inference-time predictions agree on
    what "no data" means. Loss functions must use ignore_index=NODATA_CLASS."""
    with rasterio.open(worldcover_path) as wc_src:
        wc_data = wc_src.read(1)
        wc_crs, wc_transform = wc_src.crs, wc_src.transform

    dst_h, dst_w = target_profile["height"], target_profile["width"]
    aligned = np.zeros((dst_h, dst_w), dtype="uint8")
    reproject(
        source=wc_data,
        destination=aligned,
        src_transform=wc_transform, src_crs=wc_crs,
        dst_transform=target_profile["transform"], dst_crs=target_profile["crs"],
        dst_resolution=(target_profile["transform"].a, -target_profile["transform"].e),
        resampling=Resampling.nearest,  # categorical data: never interpolate
        src_nodata=0, dst_nodata=0,
    )

    remapped = np.full_like(aligned, fill_value=6)  # default fallow/unmapped
    for wc_code, my_class in WORLDCOVER_TO_MYCLASS.items():
        remapped[aligned == wc_code] = my_class
    remapped[aligned == 0] = NODATA_CLASS  # no WorldCover coverage -> no reference label

    if stack_path is not None:
        with rasterio.open(stack_path) as s:
            stack = s.read()  # (6, H, W) float32
        no_coverage = np.all(stack[:4] == 0, axis=0)
        remapped[no_coverage] = NODATA_CLASS

    mask_profile = target_profile.copy()
    mask_profile.update(count=1, dtype="uint8", nodata=NODATA_CLASS)
    atomic_raster_write(out_path, remapped[None], mask_profile)
    print(f"Saved {out_path}  shape={remapped.shape}  "
          f"class counts={dict(zip(*np.unique(remapped, return_counts=True)))}")


# An NDVI-based refinement (splitting WorldCover's "cropland"/"shrub-grassland"
# into agriculture-vs-fallow and sparse-veg-vs-barren) was tried here, calibrated
# by grid search against real Bhuvan AOI-wise LULC statistics for Kadwanchi. It
# matched the real aggregate proportions closely but, even scoped only to its
# calibration site, still underperformed plain WorldCover labels once actually
# retrained (mean IoU 65.9% baseline vs 61.8% all-sites / 63.0% scoped -- barren
# and fallow IoU both stayed below the unrefined baseline in every variant). A
# per-pixel NDVI threshold has no spatial coherence, so getting the aggregate
# proportion right didn't translate into learnable, clean class boundaries.
# Reverted for that reason -- see documentation.md section 6a for the full
# experimental history. The real fix remains a real Bhuvan shapefile (actual
# polygon geometry), not a heuristic proxy.


def main():
    for job in AOI_JOBS:
        name = job["name"]
        worldcover_path = DATA_LABELS / f"{name}_worldcover.tif"

        for date_tag in job["dates"]:
            raw_path = DATA_RAW / f"{name}_{date_tag}_rgbnir.tif"
            stack_out = DATA_PROCESSED / f"{name}_{date_tag}_stack6.tif"
            mask_out = DATA_PROCESSED / f"{name}_{date_tag}_mask.tif"

            print(f"\n--- {name} {date_tag}: building 6-channel stack ---")
            profile = build_6channel_stack(raw_path, stack_out)

            print(f"--- {name} {date_tag}: rasterizing/remapping labels ---")
            rasterize_labels(worldcover_path, profile, mask_out, stack_path=stack_out)

    print("\nDone. Next: python src/tiling.py")


if __name__ == "__main__":
    main()

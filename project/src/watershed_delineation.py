"""
Real watershed catchment + drainage-network delineation from DEM data
(Copernicus GLO-30, via dem_fetch.py) using pysheds -- the actual
"geospatial techniques ... to enhance watershed development outcomes" this
project was missing: everything else classifies land cover and detects
change inside an arbitrary square bounding box, never an actual watershed
boundary. Activates tier1_fallback.py's `geofence_mask`, which has existed
unused (always called with `watershed_mask=None`) since early in the
project.

Honesty note (this matters -- see documentation.md and CLAUDE.md rule 5):
none of the AOIs in this project have a verified, officially-documented
watershed outlet/boundary coordinate. The catchment this module produces is
a real, DEM-derived, algorithmically-defensible approximation -- pour point
snapped to the highest flow-accumulation cell inside the AOI, catchment
delineated on a buffered grid so it isn't artificially clipped by the fetch
window -- but it is explicitly NOT a claim of matching Kadwanchi's actual
IWDP-documented boundary. Every result carries a `caveat` string saying so;
render it, don't bury it.

Run:  .venv/Scripts/python.exe src/watershed_delineation.py   (smoke-tests against Kadwanchi)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

# pysheds 0.5 (the latest PyPI release -- checked, no newer fix available)
# calls np.in1d internally (sgrid.py, 9 call sites, all the same
# `~np.in1d(fdir.ravel(), dirmap)` pattern), which numpy removed as of 2.x.
# np.isin is numpy's own official direct replacement (same semantics for
# this 1-D membership-test usage) -- a real, verified upstream version
# mismatch, same class of issue as the segmentation-models-pytorch bugs in
# documentation.md section 8, fixed the same way: a targeted compatibility
# shim, not downgrading a core pinned dependency (numpy is shared by the
# whole pipeline). Must run before pysheds is imported.
if not hasattr(np, "in1d"):
    np.in1d = np.isin

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import array_bounds
from pysheds.grid import Grid
from pysheds.sview import Raster, ViewFinder

from dem_fetch import fetch_dem_mosaic

BUFFER_FACTOR = 1.75  # expand the AOI bbox before DEM fetch/delineation -- see module docstring
ACCUMULATION_THRESHOLD = 500  # cells; stream network = accumulation >= this


def utm_epsg_for_lon(lon: float) -> int:
    """WGS84 UTM zone for a longitude, northern hemisphere (all current AOIs are in India)."""
    zone = int((lon + 180) / 6) + 1
    return 32600 + zone


def buffered_bbox(bbox: tuple, factor: float = BUFFER_FACTOR) -> tuple:
    """Expand bbox around its own center by `factor`. Not just a memory
    tradeoff -- delineating a catchment on a DEM clipped tightly to the AOI
    would truncate the result at the fetch window, not at real topographic
    divides, producing a boundary that looks legitimate but isn't."""
    minx, miny, maxx, maxy = bbox
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    hw, hh = (maxx - minx) / 2 * factor, (maxy - miny) / 2 * factor
    return (cx - hw, cy - hh, cx + hw, cy + hh)


def reproject_dem_to_utm(elevation: np.ndarray, profile: dict):
    """EPSG:4326 -> local UTM (bilinear -- elevation is continuous, unlike
    categorical labels), BEFORE flow routing. D8 flow direction/accumulation
    on an unprojected lat/lon grid biases flow paths because dx != dy in
    meters at this latitude."""
    src_crs = profile["crs"]
    bounds = array_bounds(profile["height"], profile["width"], profile["transform"])
    center_lon = (bounds[0] + bounds[2]) / 2
    dst_crs = f"EPSG:{utm_epsg_for_lon(center_lon)}"

    dst_transform, width, height = calculate_default_transform(
        src_crs, dst_crs, profile["width"], profile["height"], *bounds, resolution=30.0,
    )
    nodata = profile.get("nodata", -9999.0)
    dst = np.full((1, height, width), nodata, dtype="float32")
    reproject(
        source=elevation, destination=dst,
        src_transform=profile["transform"], src_crs=src_crs,
        dst_transform=dst_transform, dst_crs=dst_crs,
        resampling=Resampling.bilinear,
        src_nodata=nodata, dst_nodata=nodata,
    )
    new_profile = profile.copy()
    new_profile.update(crs=dst_crs, transform=dst_transform, width=width, height=height, nodata=nodata)
    return dst, new_profile


def _to_pysheds_raster(elevation: np.ndarray, profile: dict) -> Raster:
    """elevation: (1,H,W). Builds a pysheds Raster directly from the in-memory
    array + rasterio profile -- no temp-file round trip needed (verified via
    pysheds.sview.Raster/ViewFinder's real constructor signatures)."""
    vf = ViewFinder(affine=profile["transform"], shape=elevation.shape[1:],
                     nodata=profile["nodata"], crs=profile["crs"])
    return Raster(elevation[0], viewfinder=vf)


def delineate_catchment(elevation_utm: np.ndarray, utm_profile: dict, aoi_bbox_utm: tuple):
    """Full pysheds pipeline against a buffered, UTM-projected DEM. Pour
    point = highest-accumulation cell strictly inside the ORIGINAL
    (unbuffered) AOI bbox -- not the buffered fetch extent, and not a
    fabricated "official outlet" (none is verified for any AOI here).
    Catchment is delineated on the buffered grid so it's free to extend past
    the AOI edges to real topography.

    Returns (catchment_mask (H,W) bool, drainage_mask (H,W) bool,
             pour_point_xy (x,y) in utm_profile's CRS, grid, fdir)
    on the SAME grid/shape as elevation_utm -- caller reprojects onto
    Model 1's target grid separately (catchment_to_model1_grid)."""
    raster = _to_pysheds_raster(elevation_utm, utm_profile)
    grid = Grid.from_raster(raster)

    pit_filled = grid.fill_pits(raster)
    flooded = grid.fill_depressions(pit_filled)
    inflated = grid.resolve_flats(flooded)

    dirmap = (64, 128, 1, 2, 4, 8, 16, 32)
    fdir = grid.flowdir(inflated, dirmap=dirmap)
    acc = grid.accumulation(fdir, dirmap=dirmap)

    # Restrict the pour-point search to cells inside the ORIGINAL AOI bbox.
    transform = utm_profile["transform"]
    minx, miny, maxx, maxy = aoi_bbox_utm
    rows, cols = acc.shape
    row0, col0 = rasterio.transform.rowcol(transform, minx, maxy)
    row1, col1 = rasterio.transform.rowcol(transform, maxx, miny)
    row0, row1 = sorted((max(0, row0), min(rows, row1)))
    col0, col1 = sorted((max(0, col0), min(cols, col1)))

    acc_arr = np.asarray(acc)
    window_acc = np.full_like(acc_arr, -1.0)
    window_acc[row0:row1, col0:col1] = acc_arr[row0:row1, col0:col1]
    pour_row, pour_col = np.unravel_index(np.argmax(window_acc), window_acc.shape)
    pour_x, pour_y = rasterio.transform.xy(transform, pour_row, pour_col)

    # snap="center": rasterio.transform.xy() (used above) returns cell-CENTER
    # coordinates by default, but pysheds' catchment() defaults to
    # snap="corner" -- that mismatch was enough to occasionally select a
    # disconnected neighboring cell, producing a near-empty catchment even
    # though the pour point looked reasonable. Caught by actually looking at
    # the rendered output (a single-pixel dot), not just checking it ran.
    catchment = grid.catchment(x=pour_x, y=pour_y, fdir=fdir, dirmap=dirmap,
                                xytype="coordinate", snap="center")
    drainage_mask = np.asarray(acc) >= ACCUMULATION_THRESHOLD

    return np.asarray(catchment).astype(bool), drainage_mask, (pour_x, pour_y), grid, fdir


def catchment_to_model1_grid(mask: np.ndarray, src_profile: dict, target_profile: dict) -> np.ndarray:
    """Reproject a boolean mask (catchment or drainage) onto Model 1's exact
    raster grid. Structurally identical to preprocessing.py::rasterize_labels
    -- categorical/boolean data must never be interpolated, so this copies
    that function's Resampling.nearest reprojection call shape rather than
    inventing a new pattern."""
    dst_h, dst_w = target_profile["height"], target_profile["width"]
    aligned = np.zeros((dst_h, dst_w), dtype="uint8")
    reproject(
        source=mask.astype("uint8"),
        destination=aligned,
        src_transform=src_profile["transform"], src_crs=src_profile["crs"],
        dst_transform=target_profile["transform"], dst_crs=target_profile["crs"],
        dst_resolution=(target_profile["transform"].a, -target_profile["transform"].e),
        resampling=Resampling.nearest,
    )
    return aligned.astype(bool)


def get_watershed_context(bbox: tuple, target_profile: dict, cache_dir=None) -> dict:
    """Top-level entry point for aoi_picker.py. Returns a dict with
    watershed_mask/drainage_mask on target_profile's exact grid (ready for
    tier1_fallback.run_tier1(watershed_mask=...)), the pour point in lat/lon,
    and an explicit caveat string to render, not bury."""
    from rasterio.warp import transform as warp_transform
    from config import DATA_RAW

    cache_dir = cache_dir or (DATA_RAW / "dem")
    buffered = buffered_bbox(bbox)

    elevation, profile = fetch_dem_mosaic(buffered, cache_dir=cache_dir)
    elevation_utm, utm_profile = reproject_dem_to_utm(elevation, profile)

    minx, miny, maxx, maxy = bbox
    (bx0, bx1), (by0, by1) = warp_transform("EPSG:4326", utm_profile["crs"], [minx, maxx], [miny, maxy])
    aoi_bbox_utm = (min(bx0, bx1), min(by0, by1), max(bx0, bx1), max(by0, by1))

    catchment_mask, drainage_mask, pour_xy, grid, fdir = delineate_catchment(
        elevation_utm, utm_profile, aoi_bbox_utm
    )

    watershed_mask = catchment_to_model1_grid(catchment_mask, utm_profile, target_profile)
    drainage_on_target = catchment_to_model1_grid(drainage_mask, utm_profile, target_profile)

    (pour_lon,), (pour_lat,) = warp_transform(utm_profile["crs"], "EPSG:4326", [pour_xy[0]], [pour_xy[1]])

    return {
        "watershed_mask": watershed_mask,
        "drainage_network": drainage_on_target,
        "pour_point": (pour_lat, pour_lon),
        "caveat": (
            "Approximate catchment, DEM-derived (Copernicus GLO-30, 30m resolution). "
            "Pour point = highest flow-accumulation cell inside this AOI, not a "
            "verified official watershed outlet."
        ),
    }


if __name__ == "__main__":
    from config import AOI_BBOX, DATA_PROCESSED
    import matplotlib.pyplot as plt

    with rasterio.open(DATA_PROCESSED / "kadwanchi_watershed_T2_stack6.tif") as src:
        target_profile = src.profile.copy()

    print(f"AOI_BBOX={AOI_BBOX}, buffered={buffered_bbox(AOI_BBOX)}")
    context = get_watershed_context(AOI_BBOX, target_profile)

    print(f"watershed_mask: shape={context['watershed_mask'].shape} "
          f"true_fraction={context['watershed_mask'].mean():.3f}")
    print(f"drainage_network: shape={context['drainage_network'].shape} "
          f"true_fraction={context['drainage_network'].mean():.3f}")
    print(f"pour_point (lat, lon): {context['pour_point']}")
    print(f"caveat: {context['caveat']}")

    assert context["watershed_mask"].shape == (target_profile["height"], target_profile["width"])
    assert 0.0 < context["watershed_mask"].mean() < 1.0, "catchment mask is all-true or all-false -- broken"

    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    axes[0].imshow(context["watershed_mask"], cmap="Blues")
    axes[0].set_title("Delineated catchment (on Model 1 grid)")
    axes[1].imshow(context["drainage_network"], cmap="Blues")
    axes[1].set_title(f"Drainage network (accumulation >= {ACCUMULATION_THRESHOLD})")
    fig.tight_layout()
    out_path = Path(__file__).resolve().parents[1] / "outputs" / "watershed_delineation_smoketest.png"
    fig.savefig(out_path, dpi=150)
    print(f"Saved visual check: {out_path}")

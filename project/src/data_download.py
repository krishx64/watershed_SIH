"""
Pulls everything the pipeline needs with NO account/registration, for every
AOI job in config.AOI_JOBS (the primary AOI, which needs an older T1 + recent
T2 pair for change detection, plus any auxiliary training-only AOIs, which
just need one recent scene, "S1"):
  - Sentinel-2 L2A scene(s), via the public Earth Search STAC API + AWS-hosted
    COGs (element84 / AWS Open Data), clipped to the AOI on read (no full-tile
    download).
  - ESA WorldCover 10m labels for the AOI (bootstrap/backup training labels,
    since Bhuvan's shapefile needs a registration step your side).

Run:  .venv/Scripts/python.exe src/data_download.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
from rasterio.mask import mask as rio_mask
from rasterio.warp import transform_bounds, reproject, Resampling
from shapely.geometry import box, mapping
from pystac_client import Client

from config import (
    AOI_JOBS, DATA_RAW, DATA_LABELS,
    S2_BANDS, STAC_API_URL, STAC_COLLECTION, atomic_raster_write, worldcover_url_for_tile,
)

# Date windows to search, keyed by the date-tag requested in an AOI job.
# T1/T2 bracket a multi-year gap for change detection; S1 just wants one
# recent, low-cloud scene for extra training diversity.
DATE_WINDOWS = {
    "T2": "2024-11-01/2025-03-31",  # recent dry season
    "T1": "2019-11-01/2020-03-31",  # ~5yr-earlier dry season
    "S1": "2024-11-01/2025-03-31",  # recent dry season
}


def _fully_covers(item_bbox, bbox) -> bool:
    minx, miny, maxx, maxy = bbox
    ib0, ib1, ib2, ib3 = item_bbox
    return ib0 <= minx and ib1 <= miny and ib2 >= maxx and ib3 >= maxy


def search_scene(bbox, date_tag, max_cloud=20, limit=30):
    """Find the lowest-cloud scene over bbox in the window for this date tag,
    preferring one whose own footprint fully covers the requested bbox.

    Real bug this guards against: the original version sorted candidates by
    cloud cover ONLY, with no coverage check, and a scene's footprint only
    partially overlapping the AOI is a real, observed case -- confirmed for
    Kadwanchi's own primary AOI, where the plain lowest-cloud pick left 40.7%
    of the requested bbox uncovered even though a same-cloud-cover,
    full-coverage alternative (S2B_43QEC_20200226_1_L2A) existed in the very
    same search window and was simply never considered. Full-coverage
    candidates (if any exist in the window) are preferred over partial ones
    regardless of a small cloud-cover difference; only cloud cover breaks
    ties within each group."""
    catalog = Client.open(STAC_API_URL)
    search = catalog.search(
        collections=[STAC_COLLECTION],
        bbox=bbox,
        datetime=DATE_WINDOWS[date_tag],
        query={"eo:cloud_cover": {"lt": max_cloud}},
        limit=limit,
    )
    items = list(search.items())
    if not items:
        raise RuntimeError(
            f"No low-cloud Sentinel-2 scene found for bbox={bbox}, date_tag={date_tag} "
            "-- widen the date range or cloud threshold."
        )

    full_coverage = [it for it in items if _fully_covers(it.bbox, bbox)]
    pool = full_coverage if full_coverage else items
    if not full_coverage:
        print(f"WARNING: no scene in this window fully covers bbox={bbox} -- "
              f"picking the lowest-cloud partial-coverage match; expect some "
              f"nodata pixels (handled downstream via NODATA_CLASS).")
    pool.sort(key=lambda it: it.properties.get("eo:cloud_cover", 100))
    return pool[0]


def clip_scene_to_stack(item, bbox, out_path):
    """Read R,G,B,NIR bands (10m) for one STAC item, clip to bbox, stack, save.

    Always produces an array sized to the FULL requested bbox, regardless of
    how much of it the matched scene's own footprint actually covers. Real
    bug this guards against: search_scene picks the lowest-cloud match
    without checking full-bbox coverage, and a scene whose footprint only
    partially overlaps the AOI is a real, observed case (confirmed for
    Kadwanchi's own primary AOI: the matched T1 scene's northern edge fell
    ~3.3km short of AOI_BBOX's requested northern edge). The previous
    rio_mask(..., crop=True) approach silently returned a SMALLER array in
    that case -- not nodata pixels within a correctly-sized array, an
    actually truncated shape, which nothing downstream could detect (unlike
    the NODATA_CLASS sentinel, which only catches missing coverage that
    shows up as real zero-valued pixels inside an otherwise correctly-sized
    read). Reprojecting into a pre-sized destination array (same CRS, so
    this is a resample/pad, not a real reprojection) makes any uncovered
    area fall out as legitimate zero/nodata pixels instead, which
    NODATA_CLASS already handles correctly everywhere downstream."""
    band_arrays = []
    profile = None
    target_transform = target_h = target_w = None

    for band in S2_BANDS:
        href = item.assets[band].href
        with rasterio.open(href) as src:
            if target_transform is None:
                minx, miny, maxx, maxy = transform_bounds("EPSG:4326", src.crs, *bbox)
                res = src.res[0]
                target_w = max(1, round((maxx - minx) / res))
                target_h = max(1, round((maxy - miny) / res))
                target_transform = rasterio.transform.from_origin(minx, maxy, res, res)
                profile = src.profile.copy()
                profile.update(
                    height=target_h, width=target_w, transform=target_transform,
                    count=len(S2_BANDS), dtype="uint16",
                )

            band_data = np.zeros((target_h, target_w), dtype="uint16")
            reproject(
                source=rasterio.band(src, 1), destination=band_data,
                src_transform=src.transform, src_crs=src.crs,
                dst_transform=target_transform, dst_crs=src.crs,
                resampling=Resampling.nearest,
                src_nodata=0, dst_nodata=0,
            )
            band_arrays.append(band_data)

    stack = np.stack(band_arrays, axis=0)
    atomic_raster_write(out_path, stack, profile, descriptions=tuple(S2_BANDS))
    n_nodata = int(np.all(stack == 0, axis=0).sum())
    coverage_note = f"  ({n_nodata} nodata px, {100*n_nodata/(target_h*target_w):.1f}%)" if n_nodata else ""
    print(f"Saved {out_path}  shape={stack.shape}  date={item.datetime.date()}  "
          f"cloud={item.properties.get('eo:cloud_cover'):.1f}%{coverage_note}")


def download_worldcover(bbox, worldcover_tile, out_path):
    """Clip the ESA WorldCover COG straight to bbox via HTTP range reads.

    Always produces an array sized to the FULL requested bbox, even if the
    source tile's extent does not fully cover it. The previous
    rio_mask(..., crop=True) approach silently returned a SMALLER array in
    that case (same truncation class as the section-8.8 imagery bug) --
    preprocessing then rasterized a too-small label grid and filled the
    missing area with a default class. Reprojecting into a pre-sized
    destination makes uncovered pixels explicit zeros (WorldCover's own
    nodata value), which preprocessing maps to NODATA_CLASS."""
    vsi_url = f"/vsicurl/{worldcover_url_for_tile(worldcover_tile)}"
    with rasterio.open(vsi_url) as src:
        res_x, res_y = src.res
        minx, miny, maxx, maxy = bbox
        target_w = max(1, round((maxx - minx) / res_x))
        target_h = max(1, round((maxy - miny) / res_y))
        target_transform = rasterio.transform.from_origin(minx, maxy, res_x, res_y)
        profile = src.profile.copy()
        profile.update(height=target_h, width=target_w, transform=target_transform)
        data = np.zeros((1, target_h, target_w), dtype="uint8")
        reproject(
            source=rasterio.band(src, 1), destination=data[0],
            src_transform=src.transform, src_crs=src.crs,
            dst_transform=target_transform, dst_crs=src.crs,
            resampling=Resampling.nearest,
            src_nodata=0, dst_nodata=0,
        )
    atomic_raster_write(out_path, data, profile)
    n_nodata = int((data[0] == 0).sum())
    note = f"  ({n_nodata} nodata px, {100*n_nodata/data[0].size:.1f}%)" if n_nodata else ""
    print(f"Saved {out_path}  shape={data.shape}{note}")


def run_job(job):
    name, bbox, tile, dates = job["name"], job["bbox"], job["worldcover_tile"], job["dates"]
    print(f"\n=== AOI: {name}  bbox={bbox}  dates={dates} ===")

    for date_tag in dates:
        print(f"\n--- Searching Sentinel-2 L2A scene ({date_tag}) ---")
        item = search_scene(bbox, date_tag)
        print(f"{date_tag} candidate: {item.id}  ({item.datetime.date()}, "
              f"cloud={item.properties.get('eo:cloud_cover'):.1f}%)")
        clip_scene_to_stack(item, bbox, DATA_RAW / f"{name}_{date_tag}_rgbnir.tif")

    print(f"\n--- Downloading ESA WorldCover labels ({name}) ---")
    download_worldcover(bbox, tile, DATA_LABELS / f"{name}_worldcover.tif")


def main():
    for job in AOI_JOBS:
        run_job(job)
    print("\nAll AOI jobs done. Next: python src/preprocessing.py")


if __name__ == "__main__":
    main()

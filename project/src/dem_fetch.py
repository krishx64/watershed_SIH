"""
Fetches Copernicus DEM GLO-30 elevation data for an AOI bbox -- the terrain
input for watershed_delineation.py's real catchment/drainage-network delin-
eation (PS-26015's own "geospatial techniques ... to enhance watershed
development outcomes" ask, not just land-cover classification).

Public, no-auth AWS Open Data bucket `copernicus-dem-30m` -- verified for
real via a direct curl HEAD request against an actual tile before writing
any code around it (see documentation.md), not assumed from documentation
alone. Same /vsicurl/ + rasterio.mask pattern already proven in
data_download.py::download_worldcover, just against a different public
bucket. 30m resolution, 1x1 degree tiles.

Real, verified bug this module exists specifically to avoid: Kadwanchi's own
AOI_BBOX crosses 76.0 degrees E, so a naive single-tile fetch silently misses
a real strip of the flagship AOI. dem_tiles_for_bbox() always computes every
intersecting integer-degree tile (mosaicked via rasterio.merge if >1), never
assumes a single tile.

Run:  .venv/Scripts/python.exe src/dem_fetch.py   (smoke-tests against Kadwanchi)
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import rasterio
from affine import Affine
from rasterio.io import MemoryFile
from rasterio.mask import mask as rio_mask
from rasterio.merge import merge as rio_merge
from shapely.geometry import box, mapping

from config import DATA_RAW, atomic_raster_write

COPERNICUS_DEM_BUCKET = "https://copernicus-dem-30m.s3.amazonaws.com"
DEM_CACHE_DIR = DATA_RAW / "dem"


def dem_tiles_for_bbox(bbox: tuple) -> list[str]:
    """Every integer-degree Copernicus DEM tile ID intersecting bbox (up to 4:
    N/S x E/W neighbors, whenever the bbox straddles a whole-degree line in
    either axis -- Kadwanchi's own bbox does this in longitude)."""
    minx, miny, maxx, maxy = bbox
    lat_lo, lat_hi = math.floor(miny), math.floor(maxy)
    lon_lo, lon_hi = math.floor(minx), math.floor(maxx)

    tiles = []
    for lat in range(lat_lo, lat_hi + 1):
        ns = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
        for lon in range(lon_lo, lon_hi + 1):
            ew = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
            tiles.append(f"{ns}_00_{ew}_00")
    return tiles


def dem_tile_url(tile_id: str) -> str:
    return (f"{COPERNICUS_DEM_BUCKET}/Copernicus_DSM_COG_10_{tile_id}_DEM/"
            f"Copernicus_DSM_COG_10_{tile_id}_DEM.tif")


def _fetch_and_cache_tile(tile_id: str, cache_dir: Path) -> Path:
    """Downloads one whole 1x1 degree tile (~35-40MB) and caches it on disk,
    keyed by tile ID -- tiles never change, so every AOI that falls in the
    same tile (all 4 current AOIs do, for example) reuses this fetch."""
    cache_path = cache_dir / f"{tile_id}.tif"
    if cache_path.exists():
        return cache_path
    cache_dir.mkdir(parents=True, exist_ok=True)
    vsi_url = f"/vsicurl/{dem_tile_url(tile_id)}"
    with rasterio.open(vsi_url) as src:
        data = src.read()
        profile = src.profile.copy()
    atomic_raster_write(cache_path, data, profile)
    print(f"Cached DEM tile {tile_id} -> {cache_path}  shape={data.shape}")
    return cache_path


def fetch_dem_mosaic(bbox: tuple, cache_dir: Path = DEM_CACHE_DIR):
    """Fetch/cache every tile intersecting bbox, mosaic if >1, clip to bbox.
    Returns (elevation (1,H,W) float32, profile) in EPSG:4326 (the DEM's
    native CRS -- reprojection to local UTM happens in
    watershed_delineation.py, right before flow routing, not here)."""
    tile_ids = dem_tiles_for_bbox(bbox)
    tile_paths = [_fetch_and_cache_tile(t, cache_dir) for t in tile_ids]

    if len(tile_paths) == 1:
        with rasterio.open(tile_paths[0]) as src:
            elevation, transform, profile = src.read(), src.transform, src.profile.copy()
    else:
        srcs = [rasterio.open(p) for p in tile_paths]
        elevation, transform = rio_merge(srcs)
        profile = srcs[0].profile.copy()
        profile.update(height=elevation.shape[1], width=elevation.shape[2], transform=transform)
        for s in srcs:
            s.close()

    # nodata=-9999 explicit: the source tiles declare no nodata value at all, so
    # rio_mask's crop=True (which rounds the output window to whole pixels,
    # sometimes one row/col larger than the geometry itself covers) would
    # otherwise silently fill that sliver with 0 -- indistinguishable from a
    # real sea-level elevation reading. Caught for real: a single full-width
    # row of exact-0.0 pixels at the AOI's southern edge, confirmed via a
    # direct row/col check to be 100% border pixels, not a genuine gap in the
    # source data (the raw tiles have zero 0-valued pixels).
    NODATA = -9999.0
    geom = [mapping(box(*bbox))]
    with MemoryFile() as memfile:
        with memfile.open(**profile) as tmp:
            tmp.write(elevation)
        with memfile.open() as tmp:
            clipped, clip_transform = rio_mask(tmp, geom, crop=True, nodata=NODATA)

    profile.update(height=clipped.shape[1], width=clipped.shape[2], transform=clip_transform, nodata=NODATA)
    clipped, profile = _trim_nodata_border(clipped, profile, NODATA)
    return clipped, profile


def _trim_nodata_border(elevation, profile, nodata_value):
    """Drops any fully-nodata border rows/columns left by the crop-window
    rounding above -- they carry no real elevation data, keeping them just
    means passing a degenerate edge into the flow-routing pipeline later."""
    valid = elevation[0] != nodata_value
    rows = valid.any(axis=1)
    cols = valid.any(axis=0)
    if rows.all() and cols.all():
        return elevation, profile
    r0, r1 = rows.argmax(), len(rows) - rows[::-1].argmax()
    c0, c1 = cols.argmax(), len(cols) - cols[::-1].argmax()
    trimmed = elevation[:, r0:r1, c0:c1]
    new_transform = profile["transform"] * Affine.translation(c0, r0)
    profile = profile.copy()
    profile.update(height=trimmed.shape[1], width=trimmed.shape[2], transform=new_transform)
    return trimmed, profile


if __name__ == "__main__":
    from config import AOI_BBOX

    tiles = dem_tiles_for_bbox(AOI_BBOX)
    print(f"Kadwanchi AOI_BBOX={AOI_BBOX}")
    print(f"Intersecting DEM tiles: {tiles}")
    assert len(tiles) == 2, f"expected 2 tiles (crosses 76.0E), got {len(tiles)}: {tiles}"

    elevation, profile = fetch_dem_mosaic(AOI_BBOX)
    print(f"Mosaic+clip shape={elevation.shape}  crs={profile['crs']}  "
          f"elev min/max={elevation.min():.1f}/{elevation.max():.1f}m")
    assert elevation.min() > -100, "suspicious elevation (likely nodata leaking through as huge negative)"
    print("Smoke test passed.")

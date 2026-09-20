import sys
from pathlib import Path
sys.path.insert(0, str(Path("project/src").resolve()))

import numpy as np
import rasterio
from rasterio.warp import transform_bounds, Resampling
from rasterio.windows import from_bounds
from data_adapter import BHOONIDHI_DIR, AOI_BBOX
from config import atomic_raster_write
import time

zpath = BHOONIDHI_DIR / "RA309MAR2026048011009700058PSANSTUCSRHTDF.zip"
stem = zpath.stem
base_vsi = f"/vsizip/{zpath.resolve().as_posix()}/{stem}"

t0 = time.time()
with rasterio.open(f"{base_vsi}/BAND2.tif") as src0:
    minx, miny, maxx, maxy = transform_bounds("EPSG:4326", src0.crs, *AOI_BBOX)
    target_res = 10.0
    target_w = max(1, round((maxx - minx) / target_res))
    target_h = max(1, round((maxy - miny) / target_res))
    target_transform = rasterio.transform.from_origin(minx, maxy, target_res, target_res)
    target_profile = src0.profile.copy()
    target_profile.update(
        height=target_h, width=target_w, transform=target_transform,
        count=6, dtype="float32", crs=src0.crs
    )
    win = from_bounds(minx, miny, maxx, maxy, transform=src0.transform)
    green_raw = src0.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

with rasterio.open(f"{base_vsi}/BAND3.tif") as src_red:
    red_raw = src_red.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

with rasterio.open(f"{base_vsi}/BAND4.tif") as src_nir:
    nir_raw = src_nir.read(1, window=win, out_shape=(target_h, target_w), resampling=Resampling.bilinear)

red = red_raw.astype("float32") / 10000.0
green = green_raw.astype("float32") / 10000.0
nir = nir_raw.astype("float32") / 10000.0
blue = np.clip(green * 0.7 + red * 0.3, 0.0, 1.0)
eps = 1e-6
ndvi = np.clip((nir - red) / (nir + red + eps), -1.0, 1.0)
ndwi = np.clip((green - nir) / (green + nir + eps), -1.0, 1.0)

stack = np.stack([red, green, blue, nir, ndvi, ndwi], axis=0).astype("float32")
elapsed = time.time() - t0
print(f"Stack built in {elapsed:.2f}s! Shape: {stack.shape}, min: {stack.min():.3f}, max: {stack.max():.3f}")

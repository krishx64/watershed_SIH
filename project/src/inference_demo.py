"""
End-to-end demo: runs Model 1 on the full T1 and T2 rasters (not just tiles),
gets the change map (Tier-1 fallback, or Model 2 if trained), computes the
health score + alerts, and renders the visualization products the PS asks for:
  - side-by-side LULC maps (T1, T2) + change map (outputs/lulc_demo.png)
  - an interactive Folium map you can open in a browser (outputs/watershed_map.html)
  - printed alerts/recommendations

Run:  .venv/Scripts/python.exe src/inference_demo.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import rasterio
import torch
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize
import folium

from config import (
    AOI_NAME, CHANGE_CLASS_NAMES, CLASS_COLORS, CLASS_NAMES, DATA_PROCESSED,
    IN_CHANNELS, MODELS_DIR, NODATA_CLASS, NUM_CLASSES, OUTPUTS_DIR,
)
from model1_unet import build_model
from tier1_fallback import run_tier1, filter_small_blobs, summarize_changes
from recommendation_engine import compute_health_score, generate_alerts, ndvi_trend


def pad_to_multiple(arr, multiple=32):
    """arr: (C,H,W). Reflect-pad H,W up to the next multiple. Returns padded array + orig shape."""
    c, h, w = arr.shape
    pad_h = (-h) % multiple
    pad_w = (-w) % multiple
    padded = np.pad(arr, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
    return padded, (h, w)


def predict_class_map(model, stack_path, device):
    with rasterio.open(stack_path) as src:
        img = src.read()  # (6, H, W) float32
        profile = src.profile

    padded, (orig_h, orig_w) = pad_to_multiple(img)
    tensor = torch.from_numpy(padded).unsqueeze(0).to(device)

    model.eval()
    with torch.no_grad(), torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
        logits = model(tensor)
    class_map = torch.argmax(logits, dim=1).squeeze(0).cpu().numpy()[:orig_h, :orig_w].astype("uint8")

    # R,G,B,NIR (channels 0-3) all exactly zero = no real satellite coverage at
    # that pixel (a scene whose footprint only partially overlapped the AOI --
    # common near MGRS tile edges), not a real land-cover reading. Left alone,
    # the model still assigns those pixels a real class from pure-zero input,
    # which reads as a plausible (and wrong) result -- e.g. a solid "water"
    # blob with a suspiciously straight edge. Override with the nodata
    # sentinel so downstream health/change/legend/display all treat it as
    # "no data" rather than a real reading -- see config.NODATA_CLASS.
    nodata = np.all(img[:4] == 0, axis=0)
    class_map[nodata] = NODATA_CLASS

    return class_map, img, profile


def predict_change_map(model2, img_t1, img_t2, device):
    """Run Model 2 (Siamese Change U-Net) on two already-loaded 6-channel stacks
    (C,H,W float32 arrays, as returned by predict_class_map's `img`). Returns a
    (H,W) uint8 change-class map (0-4, see config.CHANGE_CLASS_NAMES)."""
    padded_t1, (orig_h, orig_w) = pad_to_multiple(img_t1)
    padded_t2, _ = pad_to_multiple(img_t2)
    tensor_t1 = torch.from_numpy(padded_t1).unsqueeze(0).to(device)
    tensor_t2 = torch.from_numpy(padded_t2).unsqueeze(0).to(device)

    model2.eval()
    with torch.no_grad(), torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
        logits = model2(tensor_t1, tensor_t2)
    change_map = torch.argmax(logits, dim=1).squeeze(0).cpu().numpy()[:orig_h, :orig_w].astype("uint8")

    # Same nodata reasoning as predict_class_map: a pixel with no real
    # coverage at either date can't have a real change verdict. Tier-1's diff
    # already excludes NODATA_CLASS pixels implicitly (they never match any
    # source/target class in diff_to_change_map); do the same here explicitly.
    nodata = np.all(img_t1[:4] == 0, axis=0) | np.all(img_t2[:4] == 0, axis=0)
    change_map[nodata] = 0

    # Tier-1's diff always gets this same treatment (see tier1_fallback.run_tier1) --
    # without it, a raw per-pixel argmax looks dramatically noisier than Tier-1's
    # output even when the underlying prediction quality is comparable. Real
    # difference measured on Kadwanchi: 13,573 connected change-blobs raw vs
    # 279 for Tier-1; this brings it to ~800, much closer (not identical --
    # Model 2 is still less reliable than Tier-1, see documentation.md).
    change_map = filter_small_blobs(change_map)

    return change_map


def render_lulc_map(class_map, ax, title):
    cmap = ListedColormap([np.array(CLASS_COLORS[i]) / 255 for i in range(NUM_CLASSES)])
    # Pixels holding NODATA_CLASS (255) are intentionally out of [0, NUM_CLASSES-1] --
    # set_over + clip=False routes them to a distinct color instead of being
    # clamped into whatever real class sits at the top of the range.
    cmap.set_over(np.array(CLASS_COLORS[NODATA_CLASS]) / 255)
    norm = Normalize(vmin=0, vmax=NUM_CLASSES - 1, clip=False)
    ax.imshow(class_map, cmap=cmap, norm=norm, interpolation="nearest")
    ax.set_title(title)
    ax.axis("off")


def render_change_map(change_map, ax, title):
    change_colors = {
        0: (230, 230, 230), 1: (66, 135, 245), 2: (200, 30, 30),
        3: (139, 69, 19), 4: (34, 139, 34),
    }
    cmap = ListedColormap([np.array(change_colors[i]) / 255 for i in range(5)])
    ax.imshow(change_map, cmap=cmap, vmin=0, vmax=4, interpolation="nearest")
    ax.set_title(title)
    ax.axis("off")


def build_folium_map(class_map, profile, out_path):
    """Overlay the LULC class map on an interactive OSM basemap."""
    height, width = class_map.shape
    color_img = np.zeros((height, width, 3), dtype="uint8")
    for cls, rgb in CLASS_COLORS.items():
        color_img[class_map == cls] = rgb

    bounds = rasterio.transform.array_bounds(height, width, profile["transform"])  # (left, bottom, right, top)
    # profile CRS is UTM (from Sentinel-2); reproject bounds corners to WGS84 for Folium.
    from rasterio.warp import transform_bounds
    minx, miny, maxx, maxy = transform_bounds(profile["crs"], "EPSG:4326", *bounds)

    center = [(miny + maxy) / 2, (minx + maxx) / 2]
    fmap = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")
    folium.raster_layers.ImageOverlay(
        image=color_img, bounds=[[miny, minx], [maxy, maxx]], opacity=0.65, name="LULC (Model 1)",
    ).add_to(fmap)
    folium.LayerControl().add_to(fmap)
    fmap.save(str(out_path))
    print(f"Saved interactive map: {out_path}")


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = MODELS_DIR / "model1_lulc_unet.pt"
    if not ckpt_path.exists():
        raise RuntimeError(f"No trained Model 1 checkpoint at {ckpt_path} — run model1_unet.py first.")

    model = build_model().to(device)
    ckpt = torch.load(ckpt_path, map_location=device)
    model.load_state_dict(ckpt["model_state"])
    print(f"Loaded Model 1 (epoch {ckpt['epoch']}, val_loss={ckpt['val_loss']:.4f})")

    stack_t1 = DATA_PROCESSED / f"{AOI_NAME}_T1_stack6.tif"
    stack_t2 = DATA_PROCESSED / f"{AOI_NAME}_T2_stack6.tif"

    class_t1, img_t1, profile = predict_class_map(model, stack_t1, device)
    class_t2, img_t2, _ = predict_class_map(model, stack_t2, device)

    change_map = run_tier1(class_t1, class_t2)
    health = compute_health_score(class_t2)
    trend = ndvi_trend(img_t1, img_t2)

    print(f"\nHealth score (T2): {health:.1f}/100")
    print(f"NDVI trend (T1->T2): {trend:+.4f}")
    print("\nChange summary:")
    for name, stats in summarize_changes(change_map).items():
        print(f"  {name}: {stats['hectares']} ha")

    print("\nAlerts / recommendations:")
    for alert in generate_alerts(class_t2, change_map, health, trend):
        area = f" ({alert['area_ha']} ha)" if alert["area_ha"] else ""
        print(f"  [{alert['severity']}] {alert['message']}{area}")

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    render_lulc_map(class_t1, axes[0], "LULC — T1")
    render_lulc_map(class_t2, axes[1], "LULC — T2")
    render_change_map(change_map, axes[2], "Change map (Tier-1)")
    fig.tight_layout()
    png_path = OUTPUTS_DIR / "lulc_demo.png"
    fig.savefig(png_path, dpi=150)
    print(f"\nSaved static figure: {png_path}")

    build_folium_map(class_t2, profile, OUTPUTS_DIR / "watershed_map.html")


if __name__ == "__main__":
    main()

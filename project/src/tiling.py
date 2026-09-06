"""
Tiles the aligned (6-channel image, mask) pairs into small patches, drops
mostly-empty/nodata patches, augments (flip/rotate x4 -> x8 per patch), and
writes a train/val manifest (model_plan.md 2.5 steps 6-7).

Run:  .venv/Scripts/python.exe src/tiling.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import csv
import numpy as np
import rasterio

from config import AOI_JOBS, DATA_PROCESSED, PATCH_SIZE, PATCH_OVERLAP

TILES_DIR = DATA_PROCESSED / "tiles"
TILES_DIR.mkdir(exist_ok=True)

STRIDE = PATCH_SIZE - PATCH_OVERLAP
VAL_FRACTION = 0.15
MAX_NODATA_FRACTION = 0.05  # drop patches that are >5% zero/nodata pixels


def augmentations(img, mask):
    """8 dihedral transforms: identity, 3 rotations, and their mirrors."""
    out = []
    for k in range(4):
        img_r = np.rot90(img, k, axes=(1, 2))
        mask_r = np.rot90(mask, k)
        out.append((img_r, mask_r))
        out.append((np.flip(img_r, axis=2), np.flip(mask_r, axis=1)))
    return out


def tile_pair(aoi_name, date_tag):
    """Returns a list of base-patch records: {"y", "x", "files": [8 augmented filenames]}.
    Deliberately keyed by base patch, not by individual augmented file -- the
    train/val split decision in main() is made per base patch, BEFORE looking
    at augmentations, specifically so that a patch and its own rotated/flipped
    copies always land in the same split (see main()'s docstring for why).

    Filenames embed the deterministic grid position (y{y:04d}x{x:04d}), NOT a
    sequential patch counter. A sequential counter diverges between dates
    whenever T1 and T2 drop different patches to the nodata filter (e.g. T1
    keeps y=[0,96,192] as p0000/p0001/p0002 while T2 drops y=96 and numbers
    y=192 as p0001) -- pairing T1_p0001 with T2_p0001 then silently trains on
    different ground locations. Position-embedded names make the same (y,x)
    the same filename on every date, so cross-date pairing by filename is
    pairing by location. Requires re-tiling once after this change (old
    pXXXX files are removed by main() below)."""
    stack_path = DATA_PROCESSED / f"{aoi_name}_{date_tag}_stack6.tif"
    mask_path = DATA_PROCESSED / f"{aoi_name}_{date_tag}_mask.tif"

    with rasterio.open(stack_path) as s:
        img = s.read()  # (6, H, W)
    with rasterio.open(mask_path) as m:
        msk = m.read(1)  # (H, W)

    C, H, W = img.shape
    patch_records = []

    for y in range(0, H - PATCH_SIZE + 1, STRIDE):
        for x in range(0, W - PATCH_SIZE + 1, STRIDE):
            img_p = img[:, y:y + PATCH_SIZE, x:x + PATCH_SIZE]
            msk_p = msk[y:y + PATCH_SIZE, x:x + PATCH_SIZE]

            nodata_frac = float(np.mean(np.all(img_p == 0, axis=0)))
            if nodata_frac > MAX_NODATA_FRACTION:
                continue

            files = []
            for aug_idx, (img_a, msk_a) in enumerate(augmentations(img_p, msk_p)):
                fname = f"{aoi_name}_{date_tag}_y{y:04d}x{x:04d}_a{aug_idx}.npz"
                # Atomic .npz write (tmp + rename): same truncated-file class as
                # config.atomic_raster_write guards for rasters. NOTE: must pass
                # an open file object to savez, not the tmp path -- numpy
                # appends ".npz" to string/Path names that don't end with it,
                # so saving to "...npz.tmp" by path would actually create
                # "...npz.tmp.npz" and the rename below would fail.
                tmp_path = TILES_DIR / (fname + ".tmp")
                final_path = TILES_DIR / fname
                with open(tmp_path, "wb") as f:
                    np.savez_compressed(f, image=img_a.astype("float32"), mask=msk_a.astype("uint8"))
                tmp_path.replace(final_path)
                files.append(fname)
            patch_records.append({"y": y, "x": x, "files": files})

    n_tiles = sum(len(r["files"]) for r in patch_records)
    print(f"{date_tag}: {len(patch_records)} base patches -> {n_tiles} tiles (with augmentation)")
    return patch_records


def main():
    """Train/val split, done properly:
    1. Per base patch, not per augmented file -- a patch's 8 rotated/flipped
       copies always land in the SAME split. The original version shuffled and
       split individual augmented files independently, so e.g. a 0-degree crop
       could be "train" while its 90-degree rotation of the exact same ground
       was "val" -- val performance was partly measuring memorization of
       training pixels seen under a different flip, not real generalization.
    2. Per AOI+date, via a spatial block (the highest-y rows of that scene's
       patch grid), not a random shuffle across the whole pooled patch list --
       random shuffling put spatially ADJACENT (overlapping, since
       STRIDE < PATCH_SIZE) patches on both sides of the split, which are
       highly correlated and leak information the same way. A contiguous
       spatial band holds out a real, separate piece of ground instead.
    Doing the split per AOI+date (not one global block across all AOIs) keeps
    every AOI represented in both train and val, so val still reflects the
    full class diversity the multi-AOI pool was built for (documentation.md
    section 5) -- the fix is about HOW each AOI's patches get split, not
    which AOIs are eligible for validation.
    """
    # One-time migration: filenames used to be pXXXX (sequential counter, which
    # diverged between dates -- see tile_pair docstring). Remove stale files so
    # a mixed old/new tiles dir can never silently mispair.
    for stale in TILES_DIR.glob("*_p[0-9][0-9][0-9][0-9]_a*.npz"):
        stale.unlink()
    all_files = []  # (filename, split)

    for job in AOI_JOBS:
        for date_tag in job["dates"]:
            patch_records = tile_pair(job["name"], date_tag)
            if not patch_records:
                continue
            # Spatial block holdout: sort by row then col, hold out the last
            # VAL_FRACTION of rows (by patch count) as a contiguous band.
            patch_records.sort(key=lambda r: (r["y"], r["x"]))
            n_val_patches = max(1, int(len(patch_records) * VAL_FRACTION))
            val_patches = patch_records[-n_val_patches:] if len(patch_records) > 1 else []
            val_ys = {r["y"] for r in val_patches}
            for r in patch_records:
                split = "val" if r["y"] in val_ys else "train"
                for fname in r["files"]:
                    all_files.append((fname, split))

    manifest_path = DATA_PROCESSED / "manifest.csv"
    with open(manifest_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "split"])
        for fname, split in all_files:
            writer.writerow([fname, split])

    n_val = sum(1 for _, split in all_files if split == "val")
    print(f"\nTotal tiles: {len(all_files)}  (train={len(all_files) - n_val}, val={n_val})")
    print(f"Manifest: {manifest_path}")
    if len(all_files) < 200:
        print("WARNING: small tile count for a placeholder AOI — expect this to grow a lot once "
              "you swap in the real watershed AOI (bigger area = more tiles) or add more scene dates.")


if __name__ == "__main__":
    main()

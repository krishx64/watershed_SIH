"""
Model 2 — Siamese Change-Detection U-Net (model_plan.md section 3).
Shared ResNet18 encoder (reused/initialized from Model 1's trained weights)
processes T1 and T2 independently; |difference| of encoder features feeds a
U-Net decoder to a 5-class per-pixel change map.

This is the "Day 2, if time allows" model — tier1_fallback.py is the
guaranteed path. Labels for fine-tuning are self-generated: run Model 1 on
two dates of the same AOI, derive weak change labels via tier1_fallback's
diff_to_change_map(), and train this network to reproduce (and eventually
smooth/improve on) that signal.

Run:  .venv/Scripts/python.exe src/model2_change.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset
import segmentation_models_pytorch as smp

import re

from config import (
    BATCH_SIZE, CHANGE_CLASS_NAMES, DATA_PROCESSED, IN_CHANNELS, LR, MODELS_DIR, NODATA_CLASS,
    NUM_EPOCHS,
)
from tier1_fallback import diff_to_change_map
from evaluate import confusion_matrix_from_arrays, metrics_from_confusion

NUM_CHANGE_CLASSES = 5

# New tiling filenames embed grid position: {aoi}_{date}_yYYYYxXXXX_aA.npz
# (see tiling.tile_pair). Old pXXXX sequential-counter names cannot be paired
# by location -- they require re-tiling.
_NEW_TILE_RE = re.compile(r"_y(\d+)x(\d+)_a(\d+)\.npz$")
_OLD_TILE_RE = re.compile(r"_p\d+_a\d+\.npz$")


def _parse_tile_key(path):
    """Filename -> (y, x, aug_idx), or None if unparseable."""
    m = _NEW_TILE_RE.search(path.name)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


class SiameseChangeUNet(nn.Module):
    """Shared encoder (optionally warm-started from Model 1) + |diff| -> U-Net decoder head."""

    def __init__(self, encoder_name="resnet18", in_channels=IN_CHANNELS,
                 num_classes=NUM_CHANGE_CLASSES, pretrained_encoder_ckpt: Path | None = None):
        super().__init__()
        base = smp.Unet(
            encoder_name=encoder_name,
            encoder_weights="imagenet",
            in_channels=in_channels,
            classes=num_classes,
        )
        self.encoder = base.encoder
        self.decoder = base.decoder
        self.head = base.segmentation_head

        if pretrained_encoder_ckpt is not None and pretrained_encoder_ckpt.exists():
            ckpt = torch.load(pretrained_encoder_ckpt, map_location="cpu", weights_only=True)
            state = {k.replace("encoder.", ""): v for k, v in ckpt["model_state"].items()
                     if k.startswith("encoder.")}
            result = self.encoder.load_state_dict(state, strict=False)
            if result is not None:
                missing, unexpected = result
                print(f"Warm-started encoder from {pretrained_encoder_ckpt.name} "
                      f"(missing={len(missing)}, unexpected={len(unexpected)})")
            else:
                # smp's EncoderMixin.load_state_dict doesn't return (missing, unexpected)
                # like a normal nn.Module -- the load still happens, just silently.
                print(f"Warm-started encoder from {pretrained_encoder_ckpt.name}")

    def forward(self, img_t1, img_t2):
        feats_t1 = self.encoder(img_t1)
        feats_t2 = self.encoder(img_t2)
        diff_feats = [torch.abs(a - b) for a, b in zip(feats_t1, feats_t2)]
        decoded = self.decoder(diff_feats)
        return self.head(decoded)


class WeakLabelChangeDataset(Dataset):
    """Pairs up T1/T2 tiles at matching spatial location and augmentation index,
    and derives weak change labels on the fly from their (already-known) class
    masks via the Tier-1 diff rule — no manual change-label annotation needed.

    Pairing key is (y, x, aug_idx) parsed from the position-embedded filenames
    (tiling.tile_pair), NOT a sequential patch counter: T1 and T2 drop
    different patches to the nodata filter, so counter-based pairing silently
    trains on different ground locations. All 8 augmentation copies are used,
    always paired T1_a{i} with T2_a{i} of the same base patch.
    Each item exposes .base_y/.base_x so the train/val split can be done as a
    spatial block (same discipline as tiling.main), never a random shuffle."""

    def __init__(self, tiles_dir: Path, aoi_name: str):
        self.tiles_dir = tiles_dir
        t1_files = sorted(tiles_dir.glob(f"{aoi_name}_T1_*.npz"))
        if any(_OLD_TILE_RE.search(p.name) for p in t1_files):
            raise RuntimeError(
                f"Old pXXXX tile names found in {tiles_dir} — re-run tiling.py first. "
                "Counter-based names cannot be paired by location (see tiling.tile_pair)."
            )
        t1_by_key, t2_by_key = {}, {}
        for p in t1_files:
            k = _parse_tile_key(p)
            if k is not None:
                t1_by_key[k] = p
        for p in sorted(tiles_dir.glob(f"{aoi_name}_T2_*.npz")):
            k = _parse_tile_key(p)
            if k is not None:
                t2_by_key[k] = p
        self.pairs = []
        for k in sorted(set(t1_by_key) & set(t2_by_key)):
            self.pairs.append((t1_by_key[k], t2_by_key[k], k[0], k[1]))  # (t1, t2, y, x)
        if not self.pairs:
            raise RuntimeError(
                f"No matching T1/T2 tile pairs found in {tiles_dir} — run tiling.py first. "
                "(Weak-label pairing needs same-AOI T1/T2 patches at the same grid location.)"
            )

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        t1_path, t2_path, _, _ = self.pairs[idx]
        d1, d2 = np.load(t1_path), np.load(t2_path)
        img_t1, mask_t1 = d1["image"], d1["mask"]
        img_t2, mask_t2 = d2["image"], d2["mask"]
        change_label = diff_to_change_map(mask_t1, mask_t2)
        return (
            torch.from_numpy(img_t1.astype("float32")),
            torch.from_numpy(img_t2.astype("float32")),
            torch.from_numpy(change_label.astype("int64")),
        )


def compute_change_class_weights(dataset, num_classes: int) -> torch.Tensor:
    """Median-frequency balancing over the weak change labels (same fix, same
    justification as model1_unet.py::compute_class_weights, applied here
    because Model 2 has the identical structural bug: an unweighted loss +
    aggregate-val_loss-only checkpoint selection both structurally
    deprioritize rare classes -- confirmed for real on Model 1 (Fallow
    collapsed to IoU 0.000 under exactly this setup, see documentation.md
    section 8/9). "No change" dominates a weak-label change map by a wide
    margin (most pixels genuinely don't change between two dates), so the
    real change classes (new water, new construction, degradation,
    vegetation gain) are the ones at risk here, not a hypothetical."""
    counts = np.zeros(num_classes, dtype="int64")
    for i in range(len(dataset)):
        _, _, label = dataset[i]
        l = label.numpy().ravel()
        l = l[l != NODATA_CLASS]
        if l.size:
            counts += np.bincount(l, minlength=num_classes)
    if counts.sum() == 0:
        raise RuntimeError("Empty change-label dataset — cannot compute class weights.")
    freq = counts / counts.sum()
    present = freq > 0
    median_freq = np.median(freq[present])
    weights = np.where(present, median_freq / np.maximum(freq, 1e-12), 0.0)
    print("Change-class weights (median-frequency balanced):")
    for c in range(num_classes):
        print(f"  {CHANGE_CLASS_NAMES.get(c, c):<38} count={counts[c]:>10}  "
              f"freq={freq[c]*100:6.2f}%  weight={weights[c]:6.3f}")
    return torch.tensor(weights, dtype=torch.float32)


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    tiles_dir = DATA_PROCESSED / "tiles"
    from config import AOI_NAME
    dataset = WeakLabelChangeDataset(tiles_dir, AOI_NAME)
    # Spatial-block split, per base location (all 8 aug copies of one (y,x)
    # share one split) -- same discipline as tiling.main. Randomly shuffling
    # individual pairs would put overlapping patches and same-ground flips on
    # both sides (STRIDE < PATCH_SIZE), leaking exactly the way Model 1's old
    # split did before its section-8.7 fix.
    base_locs = sorted({(y, x) for _, _, y, x in dataset.pairs})
    n_val_bases = max(1, int(len(base_locs) * 0.15))
    val_bases = set(base_locs[-n_val_bases:]) if len(base_locs) > 1 else set()
    # Hold out full y-rows (same rounding as tiling.main) so the val band is
    # a contiguous piece of ground, not an interleaved selection.
    val_ys = {y for y, _ in val_bases}
    train_idx = [i for i, (_, _, y, _) in enumerate(dataset.pairs) if y not in val_ys]
    val_idx = [i for i, (_, _, y, _) in enumerate(dataset.pairs) if y in val_ys]
    if not val_idx:  # single-location fallback (matches tiling.main's len>1 guard)
        val_idx, train_idx = [len(dataset.pairs) - 1], list(range(len(dataset.pairs) - 1))
    from torch.utils.data import Subset
    train_ds, val_ds = Subset(dataset, train_idx), Subset(dataset, val_idx)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    print(f"Weak-label pairs: {len(dataset)}  (train={len(train_ds)}, val={len(val_ds)})")

    model1_ckpt = MODELS_DIR / "model1_lulc_unet.pt"
    model = SiameseChangeUNet(pretrained_encoder_ckpt=model1_ckpt).to(device)

    class_weights = compute_change_class_weights(train_ds, NUM_CHANGE_CLASSES).to(device)
    dice = smp.losses.DiceLoss(mode="multiclass", ignore_index=NODATA_CLASS)
    ce = torch.nn.CrossEntropyLoss(weight=class_weights, ignore_index=NODATA_CLASS)
    loss_fn = lambda logits, target: dice(logits, target) + ce(logits, target)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    # Checkpoint selection by mean IoU, not aggregate val_loss -- same fix,
    # same reasoning as model1_unet.py (see compute_change_class_weights'
    # docstring and documentation.md section 8/9 for the real result that
    # motivated this on Model 1: a rare class can completely collapse while
    # still "winning" on overall val_loss).
    best_mean_iou = -1.0
    ckpt_path = MODELS_DIR / "model2_change_siamese.pt"

    for epoch in range(1, NUM_EPOCHS + 1):
        t0 = time.time()
        model.train()
        train_loss = 0.0
        for img_t1, img_t2, labels in train_loader:
            img_t1, img_t2, labels = img_t1.to(device), img_t2.to(device), labels.to(device)
            with torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(img_t1, img_t2)
                loss = loss_fn(logits, labels)
            optimizer.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_loss += loss.item()
        train_loss /= max(len(train_loader), 1)

        model.eval()
        val_loss = 0.0
        val_cm = np.zeros((NUM_CHANGE_CLASSES, NUM_CHANGE_CLASSES), dtype="int64")
        with torch.no_grad():
            for img_t1, img_t2, labels in val_loader:
                img_t1, img_t2, labels = img_t1.to(device), img_t2.to(device), labels.to(device)
                with torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                    logits = model(img_t1, img_t2)
                    loss = loss_fn(logits, labels)
                val_loss += loss.item()
                preds = torch.argmax(logits, dim=1).detach().cpu().numpy()
                val_cm += confusion_matrix_from_arrays(labels.cpu().numpy(), preds, NUM_CHANGE_CLASSES)
        val_loss /= max(len(val_loader), 1)
        mean_iou = metrics_from_confusion(val_cm, CHANGE_CLASS_NAMES)["mean_iou"]

        print(f"Epoch {epoch:02d}/{NUM_EPOCHS}  train_loss={train_loss:.4f}  "
              f"val_loss={val_loss:.4f}  val_mean_iou={mean_iou:.4f}  ({time.time() - t0:.1f}s)")

        if mean_iou > best_mean_iou:
            best_mean_iou = mean_iou
            torch.save({
                "model_state": model.state_dict(), "epoch": epoch,
                "val_loss": val_loss, "val_mean_iou": mean_iou,
            }, ckpt_path)
            print(f"  -> saved best checkpoint ({ckpt_path.name}, mean_iou={mean_iou:.4f})")

    print(f"\nDone. Best val_mean_iou={best_mean_iou:.4f}. Checkpoint: {ckpt_path}")


if __name__ == "__main__":
    main()

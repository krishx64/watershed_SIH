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

from config import (
    BATCH_SIZE, CHANGE_CLASS_NAMES, DATA_PROCESSED, IN_CHANNELS, LR, MODELS_DIR, NUM_EPOCHS,
)
from tier1_fallback import diff_to_change_map
from evaluate import confusion_matrix_from_arrays, metrics_from_confusion

NUM_CHANGE_CLASSES = 5


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
            ckpt = torch.load(pretrained_encoder_ckpt, map_location="cpu")
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
    """Pairs up T1/T2 tiles at matching spatial patch index and derives weak
    change labels on the fly from their (already-known) class masks via the
    Tier-1 diff rule — no manual change-label annotation needed."""

    def __init__(self, tiles_dir: Path, aoi_name: str):
        self.tiles_dir = tiles_dir
        t1_files = sorted(tiles_dir.glob(f"{aoi_name}_T1_p*_a0.npz"))  # a0 = unaugmented, for stable pairing
        self.pairs = []
        for t1_path in t1_files:
            t2_name = t1_path.name.replace("_T1_", "_T2_")
            t2_path = tiles_dir / t2_name
            if t2_path.exists():
                self.pairs.append((t1_path, t2_path))
        if not self.pairs:
            raise RuntimeError(
                f"No matching T1/T2 tile pairs found in {tiles_dir} — run tiling.py first. "
                "(Weak-label pairing needs same-AOI T1/T2 patches at the same grid index.)"
            )

    def __len__(self):
        return len(self.pairs)

    def __getitem__(self, idx):
        t1_path, t2_path = self.pairs[idx]
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
        counts += np.bincount(label.numpy().ravel(), minlength=num_classes)
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
    n_val = max(1, int(len(dataset) * 0.15))
    train_ds, val_ds = torch.utils.data.random_split(
        dataset, [len(dataset) - n_val, n_val], generator=torch.Generator().manual_seed(42)
    )
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    print(f"Weak-label pairs: {len(dataset)}  (train={len(train_ds)}, val={len(val_ds)})")

    model1_ckpt = MODELS_DIR / "model1_lulc_unet.pt"
    model = SiameseChangeUNet(pretrained_encoder_ckpt=model1_ckpt).to(device)

    class_weights = compute_change_class_weights(train_ds, NUM_CHANGE_CLASSES).to(device)
    dice = smp.losses.DiceLoss(mode="multiclass")
    ce = torch.nn.CrossEntropyLoss(weight=class_weights)
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

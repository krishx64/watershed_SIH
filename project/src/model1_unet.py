"""
Model 1 — LULC U-Net (model_plan.md section 2).
ResNet18 encoder (ImageNet weights), 6-channel input, 7-class output.
Tuned for 4GB VRAM: small batch, mixed precision, frozen encoder for first N epochs.

Run:  .venv/Scripts/python.exe src/model1_unet.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch
from torch.utils.data import DataLoader
import segmentation_models_pytorch as smp

from config import BATCH_SIZE, CLASS_NAMES, IN_CHANNELS, LR, MODELS_DIR, NODATA_CLASS, NUM_CLASSES, NUM_EPOCHS, OUTPUTS_DIR
from dataset import WatershedTileDataset
from evaluate import (
    confusion_matrix_from_arrays, evaluate_model, metrics_from_confusion,
    plot_confusion_matrix, print_metrics_report,
)

FREEZE_ENCODER_EPOCHS = 5


def build_model():
    model = smp.Unet(
        encoder_name="resnet18",
        encoder_weights="imagenet",
        in_channels=IN_CHANNELS,
        classes=NUM_CLASSES,
    )
    return model


def set_encoder_trainable(model, trainable: bool):
    for p in model.encoder.parameters():
        p.requires_grad = trainable


def compute_class_weights(dataset, num_classes: int) -> torch.Tensor:
    """Median-frequency balancing (Eigen & Fergus; also used in SegNet):
    weight_c = median(class frequency) / frequency_c. Real numbers, computed
    from the actual training tiles, not guessed.

    Why median-frequency and not plain inverse-frequency (1/freq_c): this
    project's classes are severely imbalanced (Fallow is ~0.25% of pixels
    vs. Agriculture's ~38%) -- plain inverse-frequency would give Fallow a
    weight on the order of 150x a common class, which tends to destabilize
    training (the rare-class gradient can dominate and hurt everything
    else). Median-frequency balancing is the standard, better-behaved fix
    for this specific failure mode in semantic segmentation.

    Concrete motivation: a plain (unweighted) CrossEntropy + Dice loss,
    picking the checkpoint by lowest aggregate val_loss, produced a
    checkpoint where Fallow's precision/recall/IoU were all exactly 0.000 --
    a real result from a real training run (documentation.md section 8/9),
    not a hypothetical. A class that's 0.25% of pixels contributes almost
    nothing to an unweighted aggregate loss, so the model had essentially no
    gradient pressure to ever learn it."""
    counts = np.zeros(num_classes, dtype="int64")
    for i in range(len(dataset)):
        _, mask = dataset[i]
        m = mask.numpy().ravel()
        m = m[m != NODATA_CLASS]  # no-reference-label pixels carry no training signal
        if m.size:
            counts += np.bincount(m, minlength=num_classes)
    if counts.sum() == 0:
        raise RuntimeError("Empty training-label set (all nodata) — cannot compute class weights.")
    freq = counts / counts.sum()
    present = freq > 0
    median_freq = np.median(freq[present])
    weights = np.where(present, median_freq / np.maximum(freq, 1e-12), 0.0)
    print("Class weights (median-frequency balanced):")
    for c in range(num_classes):
        print(f"  {CLASS_NAMES.get(c, c):<38} count={counts[c]:>10}  freq={freq[c]*100:6.2f}%  weight={weights[c]:6.3f}")
    return torch.tensor(weights, dtype=torch.float32)


def run_epoch(model, loader, loss_fn, optimizer, scaler, device, train: bool, num_classes: int | None = None):
    """num_classes given (only meaningful when train=False) -> also accumulate
    a confusion matrix over the val set in the same pass used for val_loss,
    reusing the logits already computed rather than a separate forward pass.
    Returns (avg_loss, confusion_matrix_or_None)."""
    model.train(train)
    total_loss, n_batches = 0.0, 0
    cm = np.zeros((num_classes, num_classes), dtype="int64") if num_classes else None
    for images, masks in loader:
        images, masks = images.to(device), masks.to(device)
        with torch.set_grad_enabled(train):
            with torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(images)
                loss = loss_fn(logits, masks)
            if train:
                optimizer.zero_grad(set_to_none=True)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            elif cm is not None:
                preds = torch.argmax(logits, dim=1).detach().cpu().numpy()
                cm += confusion_matrix_from_arrays(masks.cpu().numpy(), preds, num_classes)
        total_loss += loss.item()
        n_batches += 1
    return total_loss / max(n_batches, 1), cm


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}" + (f" ({torch.cuda.get_device_name(0)})" if device.type == "cuda" else ""))

    train_ds = WatershedTileDataset("train")
    val_ds = WatershedTileDataset("val")
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)
    print(f"Train tiles: {len(train_ds)}  Val tiles: {len(val_ds)}")

    model = build_model().to(device)
    set_encoder_trainable(model, False)

    class_weights = compute_class_weights(train_ds, NUM_CLASSES).to(device)
    dice = smp.losses.DiceLoss(mode="multiclass", ignore_index=NODATA_CLASS)
    ce = torch.nn.CrossEntropyLoss(weight=class_weights, ignore_index=NODATA_CLASS)
    loss_fn = lambda logits, target: dice(logits, target) + ce(logits, target)

    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=LR)
    scaler = torch.amp.GradScaler("cuda", enabled=(device.type == "cuda"))

    # Checkpoint selection is by mean IoU, not aggregate val_loss. A rare
    # class (e.g. Fallow, ~0.25% of pixels) barely moves an aggregate loss
    # either way, so val_loss-based selection can happily save a checkpoint
    # where that class has completely collapsed (IoU 0.000) -- a real result
    # this project hit, not a hypothetical (documentation.md section 8/9).
    # Mean IoU is computed over the SAME val pass already run for val_loss
    # (run_epoch accumulates a confusion matrix from the logits it already
    # has), not an extra forward pass.
    best_mean_iou = -1.0
    ckpt_path = MODELS_DIR / "model1_lulc_unet.pt"

    for epoch in range(1, NUM_EPOCHS + 1):
        if epoch == FREEZE_ENCODER_EPOCHS + 1:
            print("Unfreezing encoder.")
            set_encoder_trainable(model, True)
            # Encoder params were excluded from the optimizer while frozen (no
            # wasted updates or stale momentum) -- add them now, keeping the
            # decoder's existing momentum state intact.
            optimizer.add_param_group({"params": model.encoder.parameters()})

        t0 = time.time()
        train_loss, _ = run_epoch(model, train_loader, loss_fn, optimizer, scaler, device, train=True)
        val_loss, val_cm = run_epoch(model, val_loader, loss_fn, optimizer, scaler, device,
                                      train=False, num_classes=NUM_CLASSES)
        val_metrics = metrics_from_confusion(val_cm, CLASS_NAMES)
        mean_iou = val_metrics["mean_iou"]
        dt = time.time() - t0

        print(f"Epoch {epoch:02d}/{NUM_EPOCHS}  train_loss={train_loss:.4f}  "
              f"val_loss={val_loss:.4f}  val_mean_iou={mean_iou:.4f}  ({dt:.1f}s)")

        if mean_iou > best_mean_iou:
            best_mean_iou = mean_iou
            torch.save({
                "model_state": model.state_dict(), "epoch": epoch,
                "val_loss": val_loss, "val_mean_iou": mean_iou,
            }, ckpt_path)
            print(f"  -> saved best checkpoint ({ckpt_path.name}, mean_iou={mean_iou:.4f})")

    print(f"\nDone. Best val_mean_iou={best_mean_iou:.4f}. Checkpoint: {ckpt_path}")

    print("\n--- Accuracy report (best checkpoint, val set) ---")
    model.load_state_dict(torch.load(ckpt_path, map_location=device, weights_only=True)["model_state"])
    cm = evaluate_model(model, val_loader, device, NUM_CLASSES)
    metrics = metrics_from_confusion(cm, CLASS_NAMES)
    print_metrics_report(metrics)
    plot_confusion_matrix(cm, CLASS_NAMES, OUTPUTS_DIR / "model1_confusion_matrix.png")


if __name__ == "__main__":
    main()

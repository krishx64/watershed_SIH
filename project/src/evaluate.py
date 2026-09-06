"""
Per-class accuracy / confusion-matrix reporting for Model 1 (and reusable for
Model 2). This is what turns "trust me, the model works" into numbers you can
defend to judges: precision, recall, IoU, F1 per class, overall pixel
accuracy, and mean IoU (excluding classes absent from the val set, so a
missing class doesn't silently drag the average down to a misleading number).

Usable standalone (confusion_matrix_from_arrays + metrics_from_confusion) or
end-to-end against a trained model + DataLoader (evaluate_model).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import torch


def confusion_matrix_from_arrays(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    """y_true, y_pred: same-shape int arrays (any shape, flattened internally).
    Returns cm[i, j] = count of true class i predicted as class j.
    Pixels whose true label is outside [0, num_classes) -- e.g. NODATA_CLASS=255
    (no satellite coverage / no reference label) -- carry no signal and are
    excluded rather than crashing the bincount/reshape or polluting a real
    class row."""
    y_true = y_true.ravel()
    y_pred = y_pred.ravel()
    valid = (y_true >= 0) & (y_true < num_classes) & (y_pred >= 0) & (y_pred < num_classes)
    y_true, y_pred = y_true[valid], y_pred[valid]
    cm = np.zeros((num_classes, num_classes), dtype="int64")
    idx = y_true * num_classes + y_pred
    counts = np.bincount(idx, minlength=num_classes * num_classes)
    cm += counts.reshape(num_classes, num_classes)
    return cm


def metrics_from_confusion(cm: np.ndarray, class_names: dict) -> dict:
    """Per-class precision/recall/IoU/F1 + overall pixel accuracy + mean IoU.
    Classes with zero true-label support (absent from the reference labels)
    are reported as 'no data in val set' rather than a misleading 0.0."""
    num_classes = cm.shape[0]
    support = cm.sum(axis=1)  # true pixel count per class
    per_class = {}

    for c in range(num_classes):
        tp = cm[c, c]
        fp = cm[:, c].sum() - tp
        fn = cm[c, :].sum() - tp
        name = class_names.get(c, str(c))
        if support[c] == 0:
            per_class[name] = {"support": 0, "precision": None, "recall": None, "iou": None, "f1": None}
            continue
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_class[name] = {
            "support": int(support[c]), "precision": round(float(precision), 3),
            "recall": round(float(recall), 3), "iou": round(float(iou), 3), "f1": round(float(f1), 3),
        }

    pixel_accuracy = float(np.trace(cm)) / float(cm.sum()) if cm.sum() > 0 else 0.0
    present_ious = [v["iou"] for v in per_class.values() if v["iou"] is not None]
    mean_iou = float(np.mean(present_ious)) if present_ious else 0.0

    return {
        "per_class": per_class,
        "pixel_accuracy": round(pixel_accuracy, 4),
        "mean_iou": round(mean_iou, 4),
        "classes_absent_from_val_set": [name for name, v in per_class.items() if v["support"] == 0],
    }


def print_metrics_report(metrics: dict):
    print(f"Overall pixel accuracy: {metrics['pixel_accuracy']*100:.1f}%")
    print(f"Mean IoU (over classes present in val set): {metrics['mean_iou']*100:.1f}%")
    if metrics["classes_absent_from_val_set"]:
        print(f"NOTE: absent from val set (no reference labels to check against): "
              f"{', '.join(metrics['classes_absent_from_val_set'])}")
    print(f"\n{'Class':<38}{'Support':>9}{'Precision':>11}{'Recall':>9}{'IoU':>7}{'F1':>7}")
    for name, v in metrics["per_class"].items():
        if v["support"] == 0:
            print(f"{name:<38}{'0':>9}{'  -- no reference labels in val set --':>28}")
        else:
            print(f"{name:<38}{v['support']:>9}{v['precision']:>11.3f}{v['recall']:>9.3f}"
                  f"{v['iou']:>7.3f}{v['f1']:>7.3f}")


def plot_confusion_matrix(cm: np.ndarray, class_names: dict, out_path):
    """Saves a heatmap PNG -- good as a presentation slide asset."""
    import matplotlib.pyplot as plt

    num_classes = cm.shape[0]
    row_sums = cm.sum(axis=1, keepdims=True)
    cm_norm = np.divide(cm, row_sums, out=np.zeros_like(cm, dtype="float64"), where=row_sums != 0)

    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    labels = [class_names.get(i, str(i)) for i in range(num_classes)]
    ax.set_xticks(range(num_classes)); ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(num_classes)); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    ax.set_title("Model 1 confusion matrix (row-normalized)")
    for i in range(num_classes):
        for j in range(num_classes):
            if cm[i, j] > 0:
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        fontsize=7, color="white" if cm_norm[i, j] > 0.5 else "black")
    fig.colorbar(im, ax=ax, label="fraction of true class")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Saved confusion matrix figure: {out_path}")


def evaluate_model(model, loader, device, num_classes: int) -> np.ndarray:
    """Runs the model over a DataLoader of (image, mask) batches, accumulates
    a confusion matrix across the whole loader. Returns the raw cm; call
    metrics_from_confusion() on it for the report."""
    model.eval()
    cm = np.zeros((num_classes, num_classes), dtype="int64")
    with torch.no_grad():
        for images, masks in loader:
            images = images.to(device)
            with torch.autocast(device_type=device.type, enabled=(device.type == "cuda")):
                logits = model(images)
            preds = torch.argmax(logits, dim=1).cpu().numpy()
            cm += confusion_matrix_from_arrays(masks.numpy(), preds, num_classes)
    return cm


if __name__ == "__main__":
    # Hand-checked unit test: 3-class toy example, verify the math by hand.
    #   true=[0,0,1,1,2], pred=[0,1,1,2,2]
    #   cm should be: [[1,1,0],[0,1,1],[0,0,1]]
    y_true = np.array([0, 0, 1, 1, 2])
    y_pred = np.array([0, 1, 1, 2, 2])
    cm = confusion_matrix_from_arrays(y_true, y_pred, 3)
    expected = np.array([[1, 1, 0], [0, 1, 1], [0, 0, 1]])
    assert np.array_equal(cm, expected), f"cm mismatch:\n{cm}\nexpected:\n{expected}"

    names = {0: "A", 1: "B", 2: "C"}
    metrics = metrics_from_confusion(cm, names)
    # class A: tp=1, fp=0, fn=1 -> precision=1.0, recall=0.5, iou=0.5
    assert metrics["per_class"]["A"]["precision"] == 1.0
    assert metrics["per_class"]["A"]["recall"] == 0.5
    assert metrics["per_class"]["A"]["iou"] == 0.5
    print("Unit test passed.")
    print_metrics_report(metrics)

    # test the "absent class" path
    y_true2 = np.array([0, 0, 0, 1])
    y_pred2 = np.array([0, 0, 1, 1])
    cm2 = confusion_matrix_from_arrays(y_true2, y_pred2, 3)  # class 2 never appears
    metrics2 = metrics_from_confusion(cm2, names)
    assert metrics2["per_class"]["C"]["support"] == 0
    assert metrics2["per_class"]["C"]["iou"] is None
    assert "C" in metrics2["classes_absent_from_val_set"]
    print("\nAbsent-class handling test passed.")
    print_metrics_report(metrics2)

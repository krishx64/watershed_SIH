"""
Generates assets/logo.png -- the Watershed Signal mark.

Run manually (`.venv/Scripts/python.exe app/assets/make_logo.py`) whenever the
mark needs to change; the PNG is committed so the app doesn't regenerate it
on every boot. Rendered via matplotlib (the pathway already proven reliable
elsewhere in this app -- see design.render_gauge_fig's docstring for why raw
SVG-via-st.html() was abandoned) rather than hand-written SVG.

Motif: a navy contour ring (the watershed/topography), a terracotta bund line
crossing it low (the check dams / percolation structures this project's real
AOI, Kadwanchi, actually has), and a teal water drop breaking the ring at the
bottom -- water as the signal the whole pipeline is ultimately reading.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon
import numpy as np

import design as d

OUT_PATH = Path(__file__).resolve().parent / "logo.png"


def build_logo():
    fig, ax = plt.subplots(figsize=(4, 4), subplot_kw={"aspect": "equal"})
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    # outer contour ring (the watershed boundary)
    ax.add_patch(Circle((0, 0), 1.0, fill=False, edgecolor=d.NAVY, linewidth=10))
    # inner contour ring, lighter -- reads as a second elevation band
    ax.add_patch(Circle((0, 0), 0.78, fill=False, edgecolor=d.NAVY, linewidth=4, alpha=0.35))

    # bund / check-dam line, clipped to the ring interior
    ring = Circle((0, 0), 1.0, transform=ax.transData)
    bund = ax.plot([-0.86, 0.86], [-0.30, -0.30], color=d.TERRACOTTA, linewidth=9,
                    solid_capstyle="round", zorder=2)[0]
    bund.set_clip_path(ring)

    # water drop, apex up, breaking the bottom of the ring
    apex = (0.0, 0.62)
    left = (-0.40, -0.12)
    right = (0.40, -0.12)
    drop_tip = Polygon([apex, left, right], closed=True, color=d.TEAL, zorder=3)
    ax.add_patch(drop_tip)
    ax.add_patch(Circle((0, -0.12), 0.40, color=d.TEAL, zorder=3))

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    fig.tight_layout(pad=0.15)
    return fig


if __name__ == "__main__":
    fig = build_logo()
    fig.savefig(OUT_PATH, dpi=128, transparent=True)
    print(f"wrote {OUT_PATH}")

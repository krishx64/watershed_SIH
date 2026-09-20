"""
Design system for the GeoDhara app -- an "official government
report" aesthetic: white page, navy institutional identity, serif display
type for gazette-like gravitas, a letterhead masthead, and every number set
in mono type like a survey readout.

Kept separate from streamlit_app.py so the page logic isn't buried in HTML/CSS.
"""

from functools import lru_cache
from pathlib import Path

# ---------------------------------------------------------------- tokens

PAPER = "#FFFFFF"
PAPER_ALT = "#F6F7F9"
INK = "#14213D"
INK_MUTED = "#5B6472"
RULE = "#DDE1E6"

NAVY = "#1B3B6F"         # primary institutional accent
TERRACOTTA = "#C1622D"   # secondary accent -- soil / built-up data
SAGE = "#4E7A3D"         # vegetation / verified
AMBER = "#A66A16"        # recommend / caution
DANGER = "#A23B2E"       # alert
TEAL = "#2B6E82"         # water / info

# backward-compat aliases (older call sites / notes)
BG = PAPER
BG_PANEL = PAPER_ALT
BG_RAISED = "#EEF0F3"
BORDER = RULE
TEXT = INK
TEXT_MUTED = INK_MUTED

FONT_DISPLAY = "'Source Serif 4', serif"
FONT_BODY = "'IBM Plex Sans', sans-serif"
FONT_MONO = "'IBM Plex Mono', monospace"

MPL_LIGHT_RC = {
    "figure.facecolor": PAPER,
    "axes.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "text.color": INK,
    "axes.edgecolor": RULE,
    "axes.labelcolor": INK,
    "xtick.color": INK_MUTED,
    "ytick.color": INK_MUTED,
    "axes.titlecolor": INK,
    "font.family": "monospace",
    "font.size": 10,
}
MPL_DARK_RC = MPL_LIGHT_RC  # alias kept for any stale references

LOGO_PATH = Path(__file__).resolve().parent / "assets" / "logo.png"


def _logo_data_uri() -> str:
    """Base64-inlines assets/logo.png so it can drop into any st.html() call
    with no separate static-file route to configure. Regenerate the PNG via
    `python app/assets/make_logo.py`; this just reads whatever's on disk."""
    return _cached_logo_data_uri()


@lru_cache(maxsize=1)
def _cached_logo_data_uri() -> str:
    import base64
    return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")


def render_logo(size: int = 40) -> str:
    return f'<img src="{_logo_data_uri()}" width="{size}" height="{size}" alt="GeoDhara" style="display:block;">'


def inject_css() -> str:
    return f"""<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
--paper: {PAPER}; --paper-alt: {PAPER_ALT}; --ink: {INK}; --ink-muted: {INK_MUTED}; --rule: {RULE};
--navy: {NAVY}; --terracotta: {TERRACOTTA}; --sage: {SAGE}; --amber: {AMBER}; --danger: {DANGER}; --teal: {TEAL};
}}
.stApp {{ background: var(--paper); color: var(--ink); font-family: {FONT_BODY}; }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stSidebar"] {{ background: var(--paper-alt); border-right: 1px solid var(--rule); }}
[data-testid="stSidebar"] * {{ color: var(--ink); }}
h1, h2, h3 {{ font-family: {FONT_DISPLAY} !important; letter-spacing: -0.01em; }}
p, li, label, span {{ font-family: {FONT_BODY}; }}
code, .mono {{ font-family: {FONT_MONO} !important; }}
div[data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid var(--rule); background: transparent; }}
button[data-baseweb="tab"] {{
font-family: {FONT_MONO}; font-size: 12px; letter-spacing: 0.08em; text-transform: uppercase;
color: var(--ink-muted); background: transparent; border-radius: 4px 4px 0 0; padding: 10px 16px;
}}
button[data-baseweb="tab"][aria-selected="true"] {{ color: var(--navy); border-bottom: 2px solid var(--navy); }}
div[data-baseweb="tab-highlight"] {{ background-color: var(--navy) !important; }}
div[data-baseweb="tab-border"] {{ display: none; }}
[data-testid="stFileUploader"] section {{ background: var(--paper); border: 1px dashed var(--rule); border-radius: 6px; }}
button {{ font-family: {FONT_BODY} !important; }}
.stButton > button, [data-testid="stFileUploader"] button {{
background: var(--paper); color: var(--ink); border: 1px solid var(--rule); border-radius: 4px;
}}
.stButton > button:hover, [data-testid="stFileUploader"] button:hover {{ border-color: var(--navy); color: var(--navy); }}
.stButton > button[kind="primary"] {{ background: var(--navy); color: var(--paper); border-color: var(--navy); }}
[data-testid="stTable"] table {{ font-family: {FONT_MONO}; font-size: 13px; }}
[data-testid="stTable"] thead th {{
font-family: {FONT_MONO}; text-transform: uppercase; letter-spacing: 0.06em;
font-size: 11px; color: var(--ink-muted); border-bottom: 1px solid var(--rule) !important;
}}
[data-testid="stTable"] tbody td {{ border-bottom: 1px solid var(--rule) !important; color: var(--ink); }}
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
background: var(--paper); color: var(--ink); border: 1px solid var(--rule); font-family: {FONT_MONO};
}}
hr {{ border-color: var(--rule); }}
.wsig-eyebrow {{
font-family: {FONT_MONO}; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase;
color: var(--ink-muted); margin: 0 0 4px 0;
}}
.wsig-panel {{ background: var(--paper); border: 1px solid var(--rule); border-radius: 4px; padding: 16px 18px; }}
</style>
"""


def render_masthead() -> str:
    """The top letterhead band -- a 3px navy rule + mark + institutional eyebrow line."""
    return f"""<div style="border-top:3px solid {NAVY}; padding-top:10px; margin-bottom:2px;
display:flex; align-items:center; gap:8px;">
{render_logo(20)}
<div style="font-family:{FONT_MONO}; font-size:11px; letter-spacing:0.14em; color:{INK_MUTED}; text-transform:uppercase;">
Government of India &middot; Ministry of Rural Development &middot; Smart India Hackathon 2026
</div>
</div>"""


def render_header(aoi_name: str | None, lat: float | None, lon: float | None, epoch: int, val_loss: float,
                   device: str, trained: bool = True) -> str:
    """aoi_name=None renders the pre-selection state -- no location chosen yet, so no
    AOI/coordinates/trained-badge to show (the model/device info is still valid, since
    that's tied to the loaded checkpoint, not to any location)."""
    if aoi_name is None:
        aoi_value = f'<span style="color:{INK_MUTED};">Not selected yet</span>'
        coord_value = f'<span style="color:{INK_MUTED};">&mdash;</span>'
    else:
        if trained:
            badge = f'<span style="font-family:{FONT_MONO}; font-size:10px; letter-spacing:0.08em; ' \
                    f'color:{SAGE}; border:1px solid {SAGE}; border-radius:3px; padding:2px 6px; ' \
                    f'margin-left:8px; vertical-align:middle;">TRAINED SITE</span>'
        else:
            badge = f'<span style="font-family:{FONT_MONO}; font-size:10px; letter-spacing:0.08em; ' \
                    f'color:{AMBER}; border:1px solid {AMBER}; border-radius:3px; padding:2px 6px; ' \
                    f'margin-left:8px; vertical-align:middle;">LIVE &middot; UNSEEN LOCATION</span>'
        aoi_value = aoi_name.replace("_", " ") + badge
        coord_value = f"{lat:.3f}&deg;N&nbsp;&nbsp;{lon:.3f}&deg;E"

    return f"""{render_masthead()}
<div style="display:flex; justify-content:space-between; align-items:flex-end;
border-bottom:1px solid {RULE}; padding:10px 0 16px 0; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
<div>
<div style="font-family:{FONT_MONO}; font-size:11px; letter-spacing:0.1em; color:{TERRACOTTA};
text-transform:uppercase; margin-bottom:4px;">PS-26015 &middot; Geospatial Watershed Intelligence</div>
<div style="display:flex; align-items:center; gap:12px;">
{render_logo(38)}
<div style="font-family:{FONT_DISPLAY}; font-size:34px; font-weight:700; color:{INK}; line-height:1.1;">
Watershed&nbsp;Signal
</div>
</div>
</div>
<div style="display:flex; gap:22px; flex-wrap:wrap; border:1px solid {RULE}; border-radius:4px; padding:10px 16px;">
{_telemetry_chip("AOI", aoi_value)}
{_telemetry_chip("COORDINATES", coord_value)}
{_telemetry_chip("MODEL", f"epoch {epoch} &middot; loss {val_loss:.3f}")}
{_telemetry_chip("DEVICE", str(device).upper())}
</div>
</div>"""


def _telemetry_chip(label: str, value: str) -> str:
    return f"""<div>
<div style="font-family:{FONT_MONO}; font-size:10px; letter-spacing:0.1em; color:{INK_MUTED};
text-transform:uppercase;">{label}</div>
<div style="font-family:{FONT_MONO}; font-size:14px; color:{INK};">{value}</div>
</div>"""


def render_gauge_fig(value: float, label: str = "CONDITION SCORE"):
    """Matplotlib donut gauge, styled as a flat official seal -- rendered via st.pyplot(),
    not raw SVG through st.html(). The hand-built SVG version silently failed to render
    (twice, through two different theme rewrites) despite testing correctly as a string in
    isolation -- matplotlib+st.pyplot is the pathway already proven reliable elsewhere in
    this same app (the LULC/change maps), so this rebuilds the gauge on that instead of
    debugging the SVG path a third time."""
    import matplotlib.pyplot as plt
    import numpy as np

    value = max(0.0, min(100.0, value))
    if value >= 65:
        accent = SAGE
    elif value >= 35:
        accent = AMBER
    else:
        accent = DANGER

    fig, ax = plt.subplots(figsize=(2.8, 2.8), subplot_kw={"aspect": "equal"})
    fig.patch.set_facecolor(PAPER)

    # tick marks (20, every 18deg, major every 5th) drawn as short radial lines
    for i in range(20):
        angle = np.radians(90 - i * 18)  # start at 12 o'clock, clockwise
        major = i % 5 == 0
        r1, r2 = 1.16, 1.16 - (0.07 if major else 0.035)
        ax.plot([r1 * np.cos(angle), r2 * np.cos(angle)],
                [r1 * np.sin(angle), r2 * np.sin(angle)],
                color=INK_MUTED if major else RULE, linewidth=1.2 if major else 0.8, zorder=3)

    # outer seal ring
    ax.add_patch(plt.Circle((0, 0), 1.22, fill=False, edgecolor=RULE, linewidth=1, zorder=1))
    # background track (donut)
    ax.pie([1], radius=1.0, colors=[PAPER_ALT], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.24, edgecolor=PAPER, linewidth=0))
    # value arc (donut), remainder made invisible
    ax.pie([value, 100 - value], radius=1.0, colors=[accent, PAPER], startangle=90, counterclock=False,
           wedgeprops=dict(width=0.24, edgecolor=PAPER, linewidth=0))

    ax.text(0, 0.12, f"{value:.0f}", ha="center", va="center", fontsize=30, fontweight="bold",
            color=INK, family="monospace", zorder=4)
    ax.text(0, -0.22, label, ha="center", va="center", fontsize=8.5, color=INK_MUTED,
            family="monospace", zorder=4)

    ax.set_xlim(-1.35, 1.35)
    ax.set_ylim(-1.35, 1.35)
    ax.axis("off")
    fig.tight_layout(pad=0.2)
    return fig


SEVERITY_STYLE = {
    "ALERT": (DANGER, "▲"),
    "RECOMMEND": (AMBER, "●"),
    "VERIFIED": (SAGE, "✓"),
    "INFO": (TEAL, "ℹ"),
}


def render_alert_card(severity: str, message: str, area_ha, evidence: list[str] | None = None) -> str:
    color, glyph = SEVERITY_STYLE.get(severity, (TEAL, "INFO"))
    area = f'<span style="color:{INK_MUTED}; font-family:{FONT_MONO}; font-size:12px;"> &middot; {area_ha} ha</span>' if area_ha else ""
    
    evidence_html = ""
    if evidence:
        items = "".join(f'<li style="margin-bottom:3px; color:{INK}; font-size:13px;">{e}</li>' for e in evidence)
        evidence_html = f"""<div style="margin-top:8px; padding-top:6px; border-top:1px dashed {RULE};">
<div class="wsig-eyebrow" style="font-size:10px; margin-bottom:4px;">Supporting Evidence</div>
<ul style="margin:0 0 0 16px; padding:0; list-style-type:disc;">
{items}
</ul>
</div>"""

    return f"""<div style="display:flex; gap:12px; padding:12px 14px; margin-bottom:8px; border-radius:3px;
background:{PAPER}; border:1px solid {RULE}; border-left:3px solid {color};">
<div style="flex:1;">
<span style="font-family:{FONT_MONO}; font-size:11px; letter-spacing:0.08em; font-weight:600; color:{color};">{severity}</span>
<div style="color:{INK}; font-size:14px; margin-top:2px;">{message}{area}</div>
{evidence_html}
</div>
</div>"""


def render_legend(class_names: dict, class_colors: dict) -> str:
    swatches = []
    for cls_id, name in class_names.items():
        r, g, b = class_colors[cls_id]
        swatches.append(
            f'<div style="display:flex; align-items:center; gap:6px;">'
            f'<div style="width:11px; height:11px; border-radius:2px; background:rgb({r},{g},{b}); '
            f'border:1px solid rgba(0,0,0,0.15); flex-shrink:0;"></div>'
            f'<span style="font-size:12px; color:{INK_MUTED};">{name}</span></div>'
        )
    return f'<div style="display:flex; flex-wrap:wrap; gap:14px; margin-top:10px;">{"".join(swatches)}</div>'


def render_readout_stat(label: str, value: str, accent: str = INK) -> str:
    return f"""<div class="wsig-panel">
<div class="wsig-eyebrow">{label}</div>
<div style="font-family:{FONT_MONO}; font-size:24px; color:{accent};">{value}</div>
</div>"""


def render_pick_location_prompt() -> str:
    return f"""<div class="wsig-panel" style="max-width:640px;">
<div class="wsig-eyebrow">Start here</div>
<div style="font-family:{FONT_DISPLAY}; font-size:22px; color:{INK}; margin-top:4px;">
Pick a location to begin
</div>
<p style="color:{INK_MUTED}; margin:8px 0 0 0; font-size:14px;">
Choose one of the three trained sites above, or search/enter coordinates for anywhere else.
The model fetches live satellite imagery for that spot and runs the full analysis &mdash;
land cover, change detection, condition score, and alerts &mdash; usually in 20&ndash;60 seconds.
</p>
</div>"""


def render_observation_card(
    photo_caption: str,
    lat: float,
    lon: float,
    scene_date: str,
    watershed_meta: dict,
    nearest_intervention: dict | None,
    spatial_evidence: dict,
    assessment: dict,
) -> str:
    """Unified field observation and satellite interpretation card matching official report aesthetics."""
    verdict = assessment.get("verdict", "Not enough data")
    confidence = assessment.get("confidence", "Low")
    bullets = assessment.get("bullets", [])
    recommendation = assessment.get("recommendation", "")

    if "Positive" in verdict:
        accent_color = SAGE
    elif "Caution" in verdict:
        accent_color = AMBER
    elif "Degradation" in verdict:
        accent_color = DANGER
    else:
        accent_color = INK_MUTED

    admin = watershed_meta.get("admin", {})
    state = admin.get("state", "Maharashtra")
    district = admin.get("district", "Jalna")
    block = admin.get("block", "Jalna")
    ws_id = watershed_meta.get("watershed_id", "DEM-Derived")
    ws_name = watershed_meta.get("watershed_name", "DEM-Derived Watershed Boundary")
    area_ha = watershed_meta.get("area_ha", 0.0)

    if nearest_intervention:
        iv_text = (
            f"<strong>{nearest_intervention.get('name', 'Intervention')}</strong> "
            f"({nearest_intervention.get('type', 'Structure')}) &middot; "
            f"<em>{nearest_intervention.get('distance_m', 0):.0f} m from observation</em>"
        )
    else:
        iv_text = '<span style="color:var(--ink-muted);">None recorded within 500 m</span>'

    # Evidence rows
    cls_name = spatial_evidence.get("class_t2_name", "Satellite reading")
    t1_cls = spatial_evidence.get("class_t1_name")
    cls_display = f"{cls_name}" + (f" (previously: {t1_cls})" if t1_cls and t1_cls != cls_name else "")

    ndvi2 = spatial_evidence.get("ndvi_t2")
    ndvi1 = spatial_evidence.get("ndvi_t1")
    if ndvi2 is not None and ndvi1 is not None:
        ndvi_display = f"{ndvi2:.2f} (earlier: {ndvi1:.2f})"
    elif ndvi2 is not None:
        ndvi_display = f"{ndvi2:.2f}"
    else:
        ndvi_display = "N/A"

    ndwi2 = spatial_evidence.get("ndwi_t2")
    ndwi1 = spatial_evidence.get("ndwi_t1")
    if ndwi2 is not None and ndwi1 is not None:
        ndwi_display = f"{ndwi2:.2f} (earlier: {ndwi1:.2f})"
    elif ndwi2 is not None:
        ndwi_display = f"{ndwi2:.2f}"
    else:
        ndwi_display = "N/A"

    drainage_connected = spatial_evidence.get("drainage_connected", False)
    drainage_display = "Connected to active drainage network" if drainage_connected else "Outside primary flow channels"

    change_name = spatial_evidence.get("change_name", "No significant change detected")

    bullets_html = "".join(f'<li style="margin-bottom:4px; font-size:13px; color:{INK};">{b}</li>' for b in bullets)
    if not bullets_html:
        bullets_html = f'<li style="font-size:13px; color:{INK_MUTED};">Baseline observations collected.</li>'

    return f"""<div class="wsig-panel" style="border-left:4px solid {accent_color}; margin-top:16px;">
<!-- Header -->
<div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px; border-bottom:1px solid {RULE}; padding-bottom:10px; margin-bottom:12px;">
<div>
<div class="wsig-eyebrow">Field Observation &middot; Interpretation</div>
<div style="font-family:{FONT_MONO}; font-size:13px; color:{INK};">
GPS: {lat:.5f}&deg;N&nbsp;&nbsp;{lon:.5f}&deg;E &middot; Imagery Date: {scene_date}
</div>
</div>
<div>
<span style="font-family:{FONT_MONO}; font-size:11px; letter-spacing:0.08em; text-transform:uppercase; color:{accent_color}; border:1px solid {accent_color}; border-radius:3px; padding:3px 8px;">
Confidence: {confidence}
</span>
</div>
</div>

<!-- Watershed Context -->
<div style="border-bottom:1px solid {RULE}; padding-bottom:12px; margin-bottom:12px;">
<div class="wsig-eyebrow">Watershed Context</div>
<div style="font-family:{FONT_DISPLAY}; font-size:18px; font-weight:700; color:{INK}; margin-top:2px;">
{ws_name}
</div>
<div style="font-size:13px; color:{INK_MUTED}; margin-top:2px;">
District: {district} &middot; Block: {block} &middot; State: {state} &middot; Catchment Area: <span style="font-family:{FONT_MONO}; color:{INK};">{area_ha:,.1f} ha</span>
</div>
<div style="font-family:{FONT_MONO}; font-size:11px; color:{INK_MUTED}; margin-top:2px;">ID: {ws_id}</div>
</div>

<!-- Associated Intervention -->
<div style="border-bottom:1px solid {RULE}; padding-bottom:12px; margin-bottom:12px;">
<div class="wsig-eyebrow">Associated Intervention (Within 500 m)</div>
<div style="font-size:14px; color:{INK}; margin-top:4px;">
{iv_text}
</div>
</div>

<!-- Spatial Evidence Grid -->
<div style="border-bottom:1px solid {RULE}; padding-bottom:12px; margin-bottom:12px;">
<div class="wsig-eyebrow" style="margin-bottom:8px;">Spatial & Satellite Evidence</div>
<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:10px;">
<div style="background:{PAPER_ALT}; padding:8px 10px; border-radius:3px; border:1px solid {RULE};">
<div class="wsig-eyebrow" style="font-size:10px;">Land Cover</div>
<div style="font-size:13px; color:{INK}; font-weight:500;">{cls_display}</div>
</div>
<div style="background:{PAPER_ALT}; padding:8px 10px; border-radius:3px; border:1px solid {RULE};">
<div class="wsig-eyebrow" style="font-size:10px;">Vegetation Index (NDVI)</div>
<div style="font-family:{FONT_MONO}; font-size:13px; color:{INK};">{ndvi_display}</div>
</div>
<div style="background:{PAPER_ALT}; padding:8px 10px; border-radius:3px; border:1px solid {RULE};">
<div class="wsig-eyebrow" style="font-size:10px;">Water Index (NDWI)</div>
<div style="font-family:{FONT_MONO}; font-size:13px; color:{INK};">{ndwi_display}</div>
</div>
<div style="background:{PAPER_ALT}; padding:8px 10px; border-radius:3px; border:1px solid {RULE};">
<div class="wsig-eyebrow" style="font-size:10px;">Topographic Drainage</div>
<div style="font-size:13px; color:{INK};">{drainage_display}</div>
</div>
<div style="background:{PAPER_ALT}; padding:8px 10px; border-radius:3px; border:1px solid {RULE}; grid-column: 1 / -1;">
<div class="wsig-eyebrow" style="font-size:10px;">Temporal Change Detection</div>
<div style="font-size:13px; color:{INK};">{change_name}</div>
</div>
</div>
</div>

<!-- Assessment Verdict & Bullets -->
<div style="border-bottom:1px solid {RULE}; padding-bottom:12px; margin-bottom:12px;">
<div class="wsig-eyebrow">Integrated Assessment</div>
<div style="display:flex; align-items:baseline; gap:10px; margin-top:4px;">
<div style="font-family:{FONT_DISPLAY}; font-size:22px; font-weight:700; color:{accent_color};">
{verdict}
</div>
</div>
<div style="margin-top:8px;">
<div style="font-size:12px; font-weight:600; text-transform:uppercase; letter-spacing:0.06em; color:{INK_MUTED}; margin-bottom:4px;">
Analysis Findings:
</div>
<ul style="margin:0 0 0 16px; padding:0; list-style-type:disc;">
{bullets_html}
</ul>
</div>
</div>

<!-- Recommendation -->
<div>
<div class="wsig-eyebrow">Recommended Action</div>
<p style="font-size:14px; color:{INK}; margin:4px 0 0 0; line-height:1.5;">
{recommendation}
</p>
</div>
</div>"""


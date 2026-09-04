# Scaling Narrative — Watershed Signal, National Rollout

Drafted for the SIH pitch deck. Every figure below is sourced, not estimated —
see citations. This answers the question a judge will actually ask: *"this
works on one watershed — so what, at national scale?"*

---

## 1. The scale of the actual program this plugs into

Watershed Signal isn't proposing a new government program — it's built to
monitor the one that already exists and is actively expanding:

- **WDC-PMKSY 2.0** (Watershed Development Component, Pradhan Mantri Krishi
  Sinchayee Yojana), 2021-2026: a target of **49.50 lakh hectares** (4.95
  million ha), with a central financial outlay of **₹8,134 crore**.
- In **FY 2021-22 alone**, the government sanctioned **1,150 projects**
  covering ~50 lakh hectares, at a total cost of ₹12,303 crore.
- As recently as **January 2025**, 56 *new* projects were approved across 10
  states (Rajasthan, MP, Karnataka, Odisha, Tamil Nadu, Assam, Nagaland, HP,
  Uttarakhand, Sikkim) — ₹700 crore, averaging **~5,000 hectares per
  project**, ~280,000 ha total.

Sources: [DoLR — WDC-PMKSY](https://dolr.gov.in/wdcpmksy/), [WDC-PMKSY 2.0 new projects, Jan 2025](https://www.nextias.com/ca/current-affairs/18-01-2025/new-watershed-projects-wdc-pmksy-2-0), [56 projects, ₹700 crore](https://currentaffairs.adda247.com/govt-approves-56-watershed-projects-worth-%E2%82%B9700-crore/)

## 2. Our unit of analysis already matches their unit of work

This isn't a coincidence worth glossing over — it's worth stating directly in
the pitch: **1,150 sanctioned projects (FY21-22) ÷ ~50 lakh ha ≈ 4,348 ha per
project** — and the 2025 batch averages ~5,000 ha per project. Our per-AOI
coverage (a 9km×9km box) is **8,100 ha** — the same order of magnitude as one
real, government-sanctioned watershed project. One "Watershed Signal" run
isn't monitoring an arbitrary patch of land; it's monitoring *one project*, at
the same scale the government already plans and budgets in.

## 3. Why the marginal cost of scaling is ~zero

This is the actual pitch, not a slogan — it follows directly from the
architecture already built:

- **Data**: Sentinel-2 imagery and ESA WorldCover labels are free and
  automatic for *any* coordinates on Earth's land surface — no per-site
  licensing, no incremental data-acquisition cost. (Bhuvan, once
  registration completes, is also free.)
- **Compute**: one AOI's full analysis (fetch two dates, run inference,
  detect change, generate alerts) runs in under a minute on a free-tier GPU
  or even CPU — proven in this project's own Colab runs and the app's live
  "Explore a Location" feature.
- **Revisit**: Sentinel-2 revisits every ~5 days — so unlike a field visit,
  which is a discrete, scheduled, resourced event, a satellite re-assessment
  is available essentially continuously.

Compare this to the alternative: monitoring 1,150+ physically dispersed
project sites currently means scheduling and resourcing that many field
visits, repeated periodically, indefinitely. Watershed Signal's marginal cost
of adding the 1,151st site is the same as the 1st: a config change, not a
line-item.

## 4. A credible rollout path, not a hand-wave

1. **Pilot (now → post-hackathon)**: the 3 sites already trained on
   (Kadwanchi, Tamhini Ghat, Donimalai) plus the real target watershed once
   decided — proves the mechanism on real, diverse Indian terrain.
2. **State-level pilot**: partner with one of the 10 states already in
   WDC-PMKSY 2.0's active 2025 batch (Rajasthan, MP, Karnataka, etc.) — these
   states already have live, funded projects that need monitoring *now*,
   making this a real deployment opportunity, not a hypothetical.
3. **National pool**: extend the multi-site training approach (already
   proven — see `documentation.md` section 5/6a on how 3 diverse sites fixed
   real class-imbalance gaps) to a training set spanning multiple
   agro-climatic zones, so one national model generalizes the way the
   3-site pool already demonstrably improved generalization at small scale.
4. **Integration**: surface alerts directly to the same officers who
   already manage WDC-PMKSY projects, via the API-based architecture
   (roadmap item — see `needed_inputs.md`), rather than requiring a new
   parallel monitoring workflow.

## 5. The honest limits of this framing

- These are *program-level* figures (construction + all program costs), not
  a monitoring-specific budget line — no public figure was found for
  current *manual field-verification* cost specifically, so this narrative
  doesn't claim a precise ₹-for-₹ savings figure, only that the marginal
  cost of satellite-based re-assessment is negligible by comparison.
- Scaling the *model* (not just the *pipeline*) to national accuracy still
  needs real training diversity across India's agro-climatic zones — the
  3-site pool proves the mechanism, not national-scale accuracy yet.

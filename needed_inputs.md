# What's needed to make PS-26015 fully complete

Status: the pipeline runs end-to-end against real data (Kadwanchi +
3 auxiliary sites), the app is deployed, watershed boundary/drainage
delineation and an intervention registry are built and verified. What's
left is genuinely account/data-gated or needs GPU time — nothing here is
"code not written yet."

---

## The one thing that actually blocks the PS's core ask

- [ ] **A handful of real geo-tagged field photos (SRISHTI-DRISHTI/Drishti-style)
      — even 10-20.** The Field Verification tab (EXIF GPS extraction, live
      satellite fetch + prediction at that point, human confirm/flag, logged) and
      the Interventions tab (links nearby photos to a structure automatically) are
      both built and tested end-to-end — with synthetic/self-taken test photos
      only. The PS's own text is explicit that geo-tagged photos are currently
      "used only for documentation purposes rather than for integrated spatial
      analysis and interpretation" (26015.pdf, verified directly) — that's closed
      in code, but never actually run against the real thing it's meant for.
      Either SRISHTI-DRISHTI portal access for a specific project ID, or literally
      just taking a geo-tagged phone photo of anywhere, would produce the first
      real entry.

## Needs GPU time (Colab), not new code

- [ ] **Follow-up Model 1 retrain if the training set changes again.** The
      "retrain against the corrected data" run already landed (mean IoU
      49.1%, water 82.5%, fallow recovered from 0.000 to 7.5% via the
      class-weighted-loss + mean-IoU-checkpoint fix — see documentation.md
      sections 8/9). Fallow (7.5%) and built-up (30.4%) remain the weakest
      classes with the smallest val support; any future data change (new AOI,
      Bhuvan labels) wants a fresh GPU run, but nothing is currently stale.

## Still pending (out of your hands, already submitted/investigated)

- [ ] **Bhuvan LULC shapefile** (2015-16 edition, Kadwanchi bbox) — GetData
      request submitted through the portal, awaiting manual approval. Training
      still runs on free ESA WorldCover in the meantime.
- [ ] **SRISHTI-DRISHTI / Bhuvan direct API integration** — investigated what's
      actually accessible (see documentation.md section 6a for the Bhuvan stats
      API detour); no bulk vector/photo API was found, only aggregate stats and
      the manual GetData request above. Not claimed as "integrated" anywhere.

## Nice to have, not blocking anything

- [ ] **A verified official watershed boundary polygon** for any AOI, if you ever
      get one (e.g. from IWMP records). The app already delineates and geofences
      against a real DEM-derived approximate catchment (Copernicus GLO-30 +
      pysheds) — a verified official boundary would let it say "matches the real
      IWDP boundary," not just "here's a defensible terrain-derived estimate,"
      which is the honest label it carries today.
- [ ] **Known project/intervention locations** (real check dam / percolation tank
      coordinates), if accessible in bulk. The Interventions tab already supports
      adding these one at a time by hand — a bulk import would just save data
      entry, not unlock new capability.

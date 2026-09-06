#!/usr/bin/env bash
# Manufacturer STEP models used by station_assembly.py --vendor. Files land in this directory and
# are git-ignored (30 MB each; vendor copyright). Re-run any time.
set -eu
cd "$(dirname "$0")"
UA="Mozilla/5.0"

# --- Thorlabs: direct downloads (asset URLs from the product API, Sept 2026) ------------------------
# MAX313D/M  3-axis NanoMax 300, differential drives, metric  (drawing 22803-E0W)
curl -sSL -A "$UA" -o thorlabs_MAX313D_M.step \
  "https://thin01mstroc282prod.dxcloud.episerver.net/globalassets/items/m/ma/max/max313d_m/22803-e0w.step"
# KB1X1  1" x 1" kinematic base  (drawing 2374-E0W)
curl -sSL -A "$UA" -o thorlabs_KB1X1.step \
  "https://thin01mstroc282prod.dxcloud.episerver.net/globalassets/items/k/kb/kb1/kb1x1/2374-e0w.step"
# Imperial NanoMax (MAX313D, 22802-E0W) if that is what is on the bench:
#   https://thin01mstroc282prod.dxcloud.episerver.net/globalassets/items/m/ma/max/max313d/22802-e0w.step

# --- Velmex BiSlide: the site sits behind a browser captcha, download by hand ----------------------
#   https://www.velmex.com/Technical/technical_cad_drawings.html   (Technical library, .stp per model)
#   e.g. https://velmex.com/document/mn10-0100-xxx-11-lr-stp  (MN10 motorized, 10" travel, left/right)
#   save as: velmex_MN10_x_axis.step, velmex_MN10_z_axis.step, velmex_MN10_y_axis.step

# --- SMC MHZ2-6D-M9N: CAD needs a (free) SMC account since March 2026 -------------------------------
#   https://www.smcworld.com/cadlib/en/   or   https://www.smc.eu/en-gb/products/engineering-tools/3d-product-libraries
#   save as: smc_MHZ2-6D.step   (station_assembly.py keeps the catalogue-dimensioned envelope until then)

ls -la *.step 2>/dev/null || true

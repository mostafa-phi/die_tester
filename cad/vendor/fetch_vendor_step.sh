#!/usr/bin/env bash
# Manufacturer STEP models placed by cad/build.py wherever present. Files land in this directory and
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

# --- MISUMI LX20 actuators (transport X/Y/Z): CAD download needs a MISUMI account, download by hand ----
#   https://us.misumi-ec.com/vona2/detail/110300075020/   configure LX2005CG-B1-A2040-<L>, "CAD" -> STEP AP214
#            -> save as misumi_LX2005CG-B1-A2040-300.step / -200.step / -100.step (X / Y / Z), then strip CRLF:
#               sed -i 's/\r$//' misumi_LX2005CG-B1-A2040-*.step
#   Order LX2005CG-B1-T2042-300 / -200 / -100 (high grade, 1 long block, lead 5, cover, low-particulate grease,
#   T2042 plate for the Oriental Motor AZM46 steppers). The A2040 plate in the CAD has the same outline, so the files serve.
#   The Velmex BiSlide files of the earlier layout (velmex_MN10-*.step) are no longer placed.

# --- SMC MHZ2-6D-M9N: CAD needs a (free) SMC account since March 2026 -------------------------------
#   https://www.smcworld.com/cadlib/en/   or   https://www.smc.eu/en-gb/products/engineering-tools/3d-product-libraries
#   save as: smc_MHZ2-6D.step   (downloaded by the user, Sept 2026; SolidWorks 2022 export, fingers drawn open)

ls -la *.step 2>/dev/null || true

# Vendor CAD (git-ignored)

Manufacturer STEP files placed by `python cad/build.py --vendor` (or `python cad/station/model.py --vendor`)
and by the gripper model whenever the SMC file is present. They are licensed downloads and are **not
committed**; `fetch_vendor_step.sh` downloads what can be fetched without a login. Expected names:

| File | Part | Source |
|---|---|---|
| `thorlabs_MAX313D_M.step` | Thorlabs NanoMax 300, MAX313D/M (22803-E0W) | thorlabs.com product page, "CAD" tab (the fetch script has the direct link) |
| `thorlabs_KB1X1.step` | Thorlabs KB1X1 kinematic base (2374-E0W) | thorlabs.com |
| `velmex_MN10-0150-21.step` | Velmex BiSlide MN10-0150-xxx-21 with 2 cleats and PK266 motor (X axis) | velmex.com Technical library → BiSlide → "MN10-0150-xxx-21 2Cleats PK266.stp" (captcha; download by hand, rename) |
| `velmex_MN10-0050-21.step` | Velmex BiSlide MN10-0050-xxx-21 with PK266 (Z and Y axes) | same, "MN10-0050-xxx-21 PK266.stp" |
| `smc_MHZ2-6D.step` | SMC MHZ2-6D parallel gripper (drawn open) | smcworld.com CAD library (SMC account), export STEP AP214 from the SolidWorks file |
| `suruga_KXC04015-C.step` (wanted) | Suruga KXC04015-C X stage under the nest | surugaseiki.com CAD download (account); until then `cad/nest` uses the catalog envelope |
| `suruga_RPG38.step` (wanted) | Suruga RPG38 manual rotary under the X stage | MISUMI / Suruga CAD download; envelope until then |

Frames and the split into fixed / moving solids are handled in `cad/station/model.py` (`velmex()`,
`nanomax()`, `nest()`) and `cad/gripper/model.py` (`actuator_vendor()`); if a vendor updates a file and
the solid ordering or bounding boxes change, those functions are where to look.

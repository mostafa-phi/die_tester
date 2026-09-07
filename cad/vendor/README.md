# Vendor CAD (git-ignored)

Manufacturer STEP files placed by `python cad/build.py` wherever the file exists (the gripper, nest and
station models each fall back to their envelope for a missing file and say so in their checks header). They are licensed downloads and are **not
committed**; `fetch_vendor_step.sh` downloads what can be fetched without a login. Expected names:

| File | Part | Source |
|---|---|---|
| `thorlabs_MAX313D_M.step` | Thorlabs NanoMax 300, MAX313D/M (22803-E0W) | thorlabs.com product page, "CAD" tab (the fetch script has the direct link) |
| `thorlabs_KB1X1.step` | Thorlabs KB1X1 kinematic base (2374-E0W) | thorlabs.com |
| `misumi_LX2005CG-B1-A2040-300.step`, `-200.step`, `-100.step` | MISUMI LX20 single-axis actuators (X, Y, Z transport), cover type, lead 5, A2040 motor adapter (8 solids each: body with the bracket casting, cover strip, table plate, adapter plate, 4 screws; no motor). Placed by `cad/station` `lx_file_members()`; the file frame is described in `common.LX20`. CRLF line endings must be stripped (`sed -i 's/\r$//'`) or CadQuery refuses the file | MISUMI CAD download (CADENAS STEP AP214 export, user-supplied Sept 2026) |
| `velmex_MN10-0150-21.step`, `velmex_MN10-0050-21.step` | Velmex BiSlide (the transport axes of rev. 2.10 and earlier). **No longer placed**; keep or delete | velmex.com Technical library |
| `smc_MHZ2-6D.step` | SMC MHZ2-6D parallel gripper (drawn open) | smcworld.com CAD library (SMC account), export STEP AP214 from the SolidWorks file |
| `suruga_KXC04015-C.step` | Suruga KXC04015-C X stage under the nest (4 solids: base, table, motor, coupling+cable) | Suruga CAD download (account; user-supplied). Placed by `cad/nest` `kxc04015_vendor()` when present |
| `misumi_RMPG40W-N.step` | MISUMI RMPG40W-N motorized worm-gear rotary, horizontal table (5 solids: body with worm housing, motor and straight cable; table plate; three M3 fixing bolts). Placed by `cad/nest` `rmpg40w_vendor()` under the X stage; the cable is cut after a 40 mm lead-out | MISUMI CAD download (CADENAS export, user-supplied) |
| `misumi_RMPG60ZC-N.step` | MISUMI RMPG60ZC-N, the vertical-table ("ZC") type: rotation axis horizontal. **Not used** (superseded by the RMPG40W-N) | MISUMI CAD download |

Frames and the split into fixed / moving solids are handled in `cad/station/model.py` (`nanomax()`,
`nest()`, the `lx_*()` actuator builders), `cad/nest/model.py` (`kxc04015_vendor()`) and `cad/gripper/model.py`
(`actuator_vendor()`); if a vendor updates a file and the solid ordering or bounding boxes change, those
functions are where to look.

Why these are uploaded by hand: the Suruga and MISUMI CAD portals (CADENAS PARTcommunity) run behind a
login inside a JavaScript app and return HTTP 403 to non-browser requests through this sandbox's proxy,
so the files cannot be fetched by script. Do not put account credentials in the repository or the chat.

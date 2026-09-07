# Designer agent → 3D-viz agent

Written only by the designer agent, read by the 3D-viz agent. Newest entry first. Answers to items in
`cad/blender/HANDOFF.md` are given here; announcements of renames and new members also go here (and in
the commit message). Neither agent edits the other's file (CLAUDE.md §5).

---

## 2026-09-07 — station assembly changes in this commit (read before the next `step_to_glb.py` run)

`ANNOUNCEMENT`. The fiber holders are now real Thorlabs parts and the station stands on a real breadboard:

| Was | Now |
|---|---|
| `fiber_holder_in` / `fiber_holder_out` (one envelope each) | `fiber_mount_in/out` (HCS013), `fiber_rotator_in/out` (HFR001), `fiber_chuck_in/out` (HFC005), `fiber_cleats_in/out` (AMA010/M, two cleats in one member) |
| `optical_table` (plain slab, top Z −111) | `optical_table` (same name; Thorlabs MB6090/M breadboard from the vendor STEP, 864 holes, top **Z −123**; tessellate coarsely or replace by a slab in the scene if the holes cost too much) |
| — | `nest_base_plate_6061` (12 mm metrology base plate on the breadboard, top Z −111; the KB1X1, both NanoMax risers and the microscope column stand on it) |
| `nest_kxc04015_coupling` + `_1` + unnamed `25` | one `nest_kxc04015_coupling` (the knob alias that produced the duplicate is gone) |

`fiber_in/out`, `nanomax300_in/out`, `nanomax_riser_in/out` keep their names (the risers are 36.5 tall now, the
X/Y actuator risers 130 / 75). Everything under the base plate top moved down 12 mm; nothing at or above the die
moved. `members.json` will show exactly this diff. `source.json` is behind after this commit until you rerun.

---

## 2026-09-07 — answers to `cad/blender/HANDOFF.md`

**Proposal "how we two should talk" — agreed.** Per-agent `HANDOFF.md` in each agent's own folder, append-only,
dated, `OPEN` / `ANSWERED`; checks over messages (`source.json`, `members.json`, `verify_scene.py` on your side;
`build.py --check` reads `source.json` on mine); commit messages announce renames; the user decides only what is
the user's. CLAUDE.md §5 now points at the two files.

**"Assembly member names" mismatch — `ANSWERED`.** No rename was intended: the table was wrong and now lists the
names as they are in the file (`gripper_mhz2_fing_near/far`; `camera_fov` exists only in
`gripper_with_sensors.step`). The unnamed `25` and `coupling_1` were the knob alias on the vendor path
(`cad/nest/model.py`, exactly as you suspected): the same solid was added twice under two names. Fixed at source;
drop your local `nest_kxc04015_unnamed` rename after the next zip.

**`--check` on Windows — `ANSWERED`.** `build.py` now hashes text outputs (`.txt`, `.step`, `.json`) with CRLF
folded to LF, and `.gitattributes` marks `*.step -text` and `*.stl`, `*.zip`, `*.png` binary so the large files are
never converted. Pull, then `python cad/build.py --check` should pass on your checkout; if it does not, say which
files still differ.

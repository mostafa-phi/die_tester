# Installed agent skills

Vendored from [earthtojake/text-to-cad](https://github.com/earthtojake/text-to-cad)
(release 0.5.0, commit `c222e5da1ae4e6387fcb7ba09c8e475936ee3260`, MIT license — see each
skill's `LICENSE`). Update by re-copying `skills/<name>` from a newer checkout and bumping the
`cadgen` pin in the `requirements.txt` files together.

| Skill | Use in this project |
|---|---|
| `cad` | build123d/cadgen model scripts → STEP, inspection (`cadgen step inspect`), snapshots (`cadgen step snapshot`, used by `cad/build.py` for the renders); the models in `cad/` are CadQuery and are built by `cad/build.py` |
| `cad-viewer` | local browser viewer for STEP/STL/DXF (`cadgen viewer`); only reachable when Claude Code runs on the same machine as the browser |
| `step-parts` | fetch vendor STEP for purchasable parts (SMC MHZ2 gripper, Thorlabs, screws, dowels) instead of placeholder boxes |
| `dxf` | 2D profiles for laser/waterjet parts (bracket blanks, flexure blades) |
| `sendcutsend` | preflight of DXF/STEP uploads for SendCutSend orders |
| `dfam-check` | printability check of the SLA wafer-tray meshes |
| `gcode`, `bambu-labs` | FDM slicing / Bambu print handoff (not used for the tester; kept for tray or fixture prints) |
| `urdf`, `srdf`, `sdf` | robot description formats (not needed for the Cartesian handler; kept for completeness) |

Runtime: `../setup_cad_skills.sh` (run by the `SessionStart` hook in `../settings.json`)
installs `cadgen==0.5.0` and aliases the pre-installed Playwright Chromium so snapshots
render in the remote sandbox.

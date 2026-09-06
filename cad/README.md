# CAD package: one folder per component

Parametric CadQuery models of the die-handling redesign, built and kept in sync by one script.
Frame, die, contact rules and shared helpers are in `common/`; the rules for working here are in
[`../CLAUDE.md`](../CLAUDE.md).

| Folder | What | Depends on | Outputs |
|---|---|---|---|
| [`gripper/`](gripper/README.md) | end-face die gripper module: SMC MHZ2-6D, two arms, tip blocks, flexure blade, bracket; vertical (default) and horizontal (`_h`) layouts | `common` | per-part STEP/STL, assemblies, `checks[_h].txt`, renders |
| [`nest/`](nest/README.md) | self-registering, temperature-controlled chip stage: copper vacuum chuck, Semitron cage with stop pads and guards, T-riser with TEC | `common`, `gripper` | part STEP/STL, assemblies (seated / set-down), `checks.txt`, renders |
| [`tray/`](tray/README.md) | 8 × 14 wafer tray with nose-slot pockets | `common`, `gripper` | print STL, pocket check STEP, `checks.txt`, renders (full-tray STEP ignored) |
| [`station/`](station/README.md) | full station: nest, gripper, Velmex X/Z/Y axes, NanoMax fiber stages, microscope, tray; clearance checks; layout and movement pattern | all of the above | `checks[_vendor][_h].txt`, renders (assemblies ignored: 8–106 MB) |
| `vendor/` | manufacturer STEP (git-ignored) and the fetch script; see `vendor/README.md` | | |

## Build

```bash
python cad/build.py            # gripper -> nest -> tray -> station (envelope) + renders, writes build_manifest.json
python cad/build.py --all      # + vendor-model station and the horizontal-gripper variants (needs cad/vendor/*.step)
python cad/build.py --check    # exit 1 if any source changed since the last build or a tracked output is missing / edited
```

Every `model.py` can also be run on its own (`python cad/nest/model.py`) while iterating, but the
manifest is only written by a full build, and `--check` (run at every session start) fails until
one has been done. Commit sources, checks, renders, small STEP/STL and the manifest together.

Needs `cadquery` (full OCP build) and, for the renders, `cadgen` from the vendored skills
(`.claude/setup_cad_skills.sh` installs both).

## Reading the checks

`checks*.txt` list axis-aligned-bounding-box separations per member pair: positive = clear by that
much, OK above the stated margin, TIGHT below it, OVERLAP negative. Each README states which non-OK
lines are intended (a stop pad touching the seated die, the gripper band passing under the
objective). Anything else is a defect to fix in the model, never in the text.

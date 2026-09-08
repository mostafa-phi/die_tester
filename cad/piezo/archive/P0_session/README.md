# APA60S XYZ — P0 packaging and guided-axis concept

Status: reviewable concept, NOT a manufacturing release. Created 2026-09-07 outside the repository.

## Delivered models

- `APA60S_XYZ_P0.f3d`: Fusion assembly with native guide sketches/extrusions and the supplied actuator STEP.
- `APA60S_XYZ_P0.step`: exchange-format copy.
- `APA60S_Z_axis_P0.f3d` / `.step`: standalone guided-axis concept. The Fusion archive was reopened successfully: 10 components, 7 bodies, 27 timeline items.
- `assembly_preview.png` / `single_axis_preview.png`: actual Fusion viewport renders.
- `verification.json`: nominal body bounds, volumes and Fusion interference results.

## Arrangement and dimensions

Local coordinates: X optical approach, Y transverse/lateral, Z vertical. This is different from the station repository convention, where Y is optical.

X is the bottom/outer axis. Its central carriage carries a riser and bridge that support the Y module ONLY at its fixed perimeter. The Y carriage carries the upright Z module through its fixed lower frame. The placeholder fiber holder attaches to the Z carriage.

| Item | As modeled |
|---|---:|
| Mechanical body envelope, excluding nose/fiber | 84 X × 70 Y × 106 Z mm |
| Overall envelope including nose/fiber | 101 × 70 × 106 mm |
| Base footprint | 70 × 70 mm |
| Optical center above base underside | 81 mm |
| Fiber tip datum | X66, Y0, Z81 mm |
| X and Y guide blanks | 70 × 70 × 6 mm |
| Z guide blank | 70 × 50 × 6 mm |
| Folded guide leaf free length | 14 mm |
| Leaf thickness | 0.50 mm |
| Leaf depth | 6 mm |
| Nominal handling-stop gap | 0.25 mm per direction |
| Adapter clearance-hole pattern | 20 × 45 mm; nominal M4 clearance |

The actuator is offset behind each guide; its shell has at least 1 mm nominal clearance above its fixed support. The lower X guide has 2 mm clearance to the adapter except at its fixed perimeter supports. Do not place a support underneath a moving carriage merely because that surface is convenient to mount.

## Reference requirements and mass

300 g is a maximum payload TARGET; the normal holder is lighter and remains unspecified. No 300 g performance rating has been demonstrated. The model's 20 g normal-payload parameter is an explicit provisional analysis assumption, not a user measurement. The holder is a simple envelope, not a functioning clamp.

Assuming all non-vendor structural solids are aluminum at 2.81 g/cm³, their modeled mass is approximately 222.8 g, including the placeholder holder. Adding 3 × 8.5 g nominal APA mass gives approximately 248 g, excluding hardware and wiring. This exceeds the brief's 100–150 g mechanism preference. Pocketing, shorter bridges and integrated interfaces remain necessary; this first arrangement establishes load paths and clearance.

Using the repository's 111.5 mm fiber height above the metrology base and its 27 mm coarse carriage height, this 81 mm optical height leaves only 3.5 mm for additional mounting height. This is a height-budget check ONLY. The head has NOT been inserted into the full station and checked over retract, chip exchange or device stepping.

## Validation performed

- Read and measured the supplied vendor STEP without altering it.
- Built native Fusion sketches and extrusion features; the vendor geometry remains imported.
- Checked nominal assembly for volumetric interference with coincident faces excluded: **31 bodies, zero volumetric interferences**.
- Corrected initial support overlaps and cleared the moving X mounting land.
- Exported Fusion and STEP files and reopened the standalone native archive.
- Visually inspected assembly and single-axis views.

This does not check flexure stress, dynamic response, motion under full command, joint stiffness, fatigue, or safe stop impact. Touching interfaces were excluded from the interference calculation. It is not a proof of correct constraint or assembly preload.

## Native editability

`guide_depth` drives the native guide and keeper-stop extrusions. The guide planform is generated from `geometry.json` and has fixed sketch entities. `leaf_thickness_nominal` and `leaf_length_nominal` are reference parameters, not fully linked sketch dimensions. Changing them alone does NOT resize the leaves. A subsequent model revision should either fully constrain the guide sketch or regenerate its planform from the external generator.

The monolithic guide is one elastic body. No rigid-body slider joint is used to pretend that its leaves deform. A simulation or a separate exaggerated-motion illustration is required to show actual deflection.

## Required changes before prototype release

1. Replace the rigid APA-to-carriage mounting land with a validated coupling, or substantiate direct attachment using vendor transverse/rotational stiffness and allowable loads.
2. Obtain exact mounting torque and engagement requirements; detail APA mounting screws, access and assembly order. Mounting faces are positioned, but screw bores/fasteners at those interfaces are not yet modeled.
3. Specify the real fiber holder, roll adjustment if required, mass, COM and allowable tip rotation.
4. Add leaf-root radii and a fatigue-appropriate EDM/finishing specification. The present sharp corners are not released geometry.
5. Analyze static travel, combined commands, gravity, off-axis moments and complete loaded modes, including intermediate-link modes.
6. Validate stop gaps and allowable travel before stop contact. These are handling-keeper concepts, not a proven crash-protection system.
7. Finalize structural joints and locating features. Preliminary M2 corner clearance holes are not an approved mounting design.
8. Reduce mass and height, then run full station envelope and motion checks.
9. Add actual wiring service loops, strain relief, covers and optional transport locks.

## Reproduction

The model source and tool request records are retained here for traceability. `prepare_concept.py` creates the guide planform data using the external `pythonEnvs/cad` environment. `build_fusion.py` now includes the final clearance changes and keeper geometry. `finish_fusion.py` checks and exports the active concept. Both Fusion scripts are intended for the native Fusion MCP script executor. `refine_fusion.py`, `verify_fusion.py`, and `clearance_fix.py` are historical incremental scripts; do not rerun them against the finished design.

No project repository file was edited. No cloud project save was performed; local Fusion archives preserve the work.

"""Split a shim-mode variant into one file per manufactured part: variants/<v>/manufacturing/.

    python export_manufacturing.py --variant r04        (cad environment: CadQuery)

Reads the assembly and loaded STEP the model wrote and sorts their solids by
size and position into the parts a shop needs: the body plate (one CNC job that
ends as four loose pieces), one clamp bar, one shim leaf (STEP and a flat DXF
with its holes), and the base plate. Writes a README with quantity, material,
process and the tolerances that matter for each. The drawing sheet and the
body DXF are copied in from renders/ and STEP/.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", required=True)
    args = parser.parse_args()
    root = HERE / "variants" / args.variant
    rep = json.loads((root / "geometry_report.json").read_text(encoding="utf-8"))
    if not rep.get("shim", {}).get("enabled"):
        if rep["parameters"].get("stop") == "pin":
            return export_monolithic(args.variant, root, rep)
        raise SystemExit("export_manufacturing.py is for shim-mode (R04/R05) or monolithic pin-stop (R06) variants")
    p, sh, d, r = rep["parameters"], rep["shim"], rep["derived"], rep["r02"]
    out = root / "manufacturing"
    out.mkdir(exist_ok=True)

    assembly = cq.importers.importStep(str(root / "STEP" / "parallel_yz_r01_assembly.step")).solids().vals()
    loaded = cq.importers.importStep(str(root / "STEP" / "parallel_yz_r01_loaded.step")).solids().vals()

    def kind(s):
        v = s.Volume()
        bb = s.BoundingBox()
        if bb.xmin < -0.5:
            return "base"
        if v < 30:
            return "leaf"
        if v < 100:
            return "bar"
        if (bb.xmax - bb.xmin) > p["b"] + 0.5:
            return "apa"
        if bb.xmin > p["b"] - 0.5:
            return "holder"
        return "body"

    parts = {}
    for s in assembly:
        parts.setdefault(kind(s), []).append(s)
    for s in loaded:
        if kind(s) == "base":
            parts["base"] = [s]

    def export(name, solids):
        wp = cq.Workplane("XY").add(solids)
        cq.exporters.export(wp, str(out / f"{name}.step"))

    export("body_plate_4_pieces", parts["body"])
    # ... and the four pieces one by one: the frame (largest), the platform
    # (contains the fiber hole at the origin), the two stages (Y one on the +Y
    # side; the Z stage is the same part turned over).
    body_sorted = sorted(parts["body"], key=lambda s: -s.Volume())
    frame = body_sorted[0]
    rest = body_sorted[1:]
    platform = min(rest, key=lambda s: abs(s.Center().y) + abs(s.Center().z))
    stages = [s for s in rest if s is not platform]
    stage_y = max(stages, key=lambda s: s.Center().y)
    export("frame", [frame])
    export("platform", [platform])
    export("stage", [stage_y])
    export("clamp_bar", [parts["bar"][0]])
    export("shim_leaf", [parts["leaf"][0]])
    export("base_plate", parts["base"])
    export("assembly_reference", assembly)
    jig = root / "STEP" / "assembly_jig.step"
    if jig.exists():
        shutil.copy(jig, out / "assembly_jig.step")

    # Flat DXF of one shim: a plain rectangle when every tab is bonded, else
    # with the two clamp holes at each tab.
    bond_all = p.get("bond_all", False)
    depth, length = p["b"], p["L"] + 2 * p["tab"]
    leaf = cq.Workplane("XY").rect(depth, length, centered=False).extrude(p["t"])
    if not bond_all:
        holes = [(x, y) for y in (p["tab"] / 2, length - p["tab"] / 2) for x in (depth / 4, 3 * depth / 4)]
        for x, y in holes:
            leaf = leaf.cut(cq.Workplane("XY").center(x, y).circle(1.2).extrude(p["t"]))
    cq.exporters.exportDXF(leaf.faces("<Z"), str(out / "shim_leaf_flat.dxf"))

    shutil.copy(root / "STEP" / "parallel_yz_r02_profile.dxf", out / "body_profile.dxf")
    sheet = root / "renders" / "drawing_r02.png"
    if sheet.exists():
        shutil.copy(sheet, out / "drawing_sheet.png")

    n_screws = len(sh["screws"])
    bonded = 16 if bond_all else sum(1 for b in sh["bars"] if b["access"] == "bond")
    bolts = rep["fixture_mounted"]["points"]
    readme = f"""# {args.variant.upper()} manufacturing package

Parallel-kinematic YZ fiber-alignment flexure, two {rep['actuator']['name']} actuators.
Frame: X optical (plate thickness), Y lateral, Z up; all files mm.
Analysis and the numbers behind every choice: ../../README.md (section {args.variant.upper()}).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `frame.step`, `stage.step` (×2, second turned over), `platform.step`; `body_plate_4_pieces.step` + `body_profile.dxf` as the one-plate alternative | body pieces | 1 + 2 + 1 | {rep['material']['name']}, {p['b']:.0f} mm | CNC mill each piece as its own part (recommended: every ledge, notch and hole is then on an external face) or profile all four from one plate and separate; internal corner radius R{p['r_root']:.1f} (Ø{2 * p['r_root']:.0f} cutter) | profile ±0.05; leaf ledges/notches flat 0.01, parallel 0.02 (they set the leaf planes); pad lands coplanar ±0.02, land gap {d['pocket1'] - d['y_in1'] - 2 * p['pad_boss']:.2f} +0.05/−0; stop gaps 0.30 +0.10/−0 are assembled clearances between parts; faces ground flat 0.02. Per-part sheets: `part_frame.png`, `part_stage.png`, `part_platform.png` |
| `shim_leaf.step`, `shim_leaf_flat.dxf` | leaf | 8 (+2 spares) | {p['leaf_material']['name']}, {p['t']:.2f} mm | shear or laser cut from precision shim stock; {'plain rectangle, no holes (bonded)' if bond_all else 'drill/laser 4 × Ø2.4'}; deburr, no bends | thickness {p['t']:.2f} ±0.005 (stock tolerance); outline ±0.05; flat; edges burr-free (fatigue). Free length {p['L']:.1f} is set by the clamp bars, not the leaf |
| `clamp_bar.step` | clamp bar | 16 (+4) | {rep['material']['name']} | saw from {p['b']:.0f} × {p['bar_t']:.1f} strip, {p['tab']:.1f} long, long edges chamfered {p['bar_edge_r']:.1f}; {'no holes, bonded on top of the tab' if bond_all else f'2 × Ø2.2 thru on the {n_screws // 2} screwed bars'} | the inner edge defines the leaf root: chamfer consistently; faces flat 0.01 |
| `assembly_jig.step` | bonding jig | 1 | any aluminium, 8 mm | CNC: 3 mm pockets for platform+arms and both stages (0.02 clearance), 4 dowel seats on the bolt pattern, window under the fiber hole | pocket walls ±0.02, floors flat 0.01: **this jig is what sets leaf alignment and free length** (BONDING.md) |
| `base_plate.step` | mount / base | 1 | any aluminium ({rep['material']['name']} fine) | CNC: {rep['base']['t']:.0f} mm plate, central opening {rep['base']['opening_mm'][0]:.0f} × {rep['base']['opening_mm'][1]:.0f}, windows behind the two pockets, 4 × Ø{p['bolt']} | flat 0.02 where the body sits (it is the mount reference); it is a stiffness model - replace by the station's real mount if one exists |
| `assembly_reference.step` | everything placed | - | - | reference only: body, leaves, bars, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |
| `drawing_sheet.png` | shop sheet | - | - | - | the tolerances, notes and assembly sequence in one page |

## Bought parts

| part | qty | source | notes |
|---|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT Technologies | 13 ±0.1 pad-to-pad, M2 pads; shim 0.05–0.15 to the {d['pocket1'] - d['y_in1'] - 2 * p['pad_boss']:.2f} land gap |
| M2 × 5 SHCS (frame pad), M2 × 8 SHCS (stage pad) | 2 + 2 | any | torque per CEDRAT |
| M2 × 6 SHCS, clamp bars | {n_screws} | stainless A2 | {'none: every tab is bonded' if bond_all else '0.3 N·m + Loctite 243'} |
| M4 × 20 SHCS + washers, base | 4 | any | |
| structural epoxy (3M DP460 or Loctite EA 9460) | 1 | | for the {bonded} bonded tabs (recommended: bond all 16 and use the bars as cure fixtures) |
| 2-channel piezo amplifier | 1 | CEDRAT LA75 range or equivalent | 1.1 µF per channel, ≥0.18 A peak for full stroke at 150 Hz |

## Tool access, hole by hole (each body piece machined as a separate part)

| piece | feature | axis | reached from |
|---|---|---|---|
| frame | 4 × Ø{p['bolt']}, {len(r['wire_ties'])} × Ø3 wire ties, windows, pockets | X | the face (through) |
| frame | actuator pad screw: Ø2.2 + Ø4 c'bore ×2 | leg axis | the plate's outer edge - external face |
| frame | pad land (raised 0.2) | - | the pocket side, pocket is through |
| frame | leaf anchor notches | X | through-profile slots; no taps (bonded) |
| stage | actuator pad screw: Ø2.2 + Ø4 c'bore | leg axis | the stage's inner face - external on the loose part |
| stage | ledges, notches, tongue, land | X / - | through-profile / milled from the faces |
| platform | fiber hole Ø3 + chamfers, holder taps 2 × M2 | X | the faces |
| platform | ledges, fork posts | X | through-profile; fork slot 2.6 wide takes a Ø2 cutter |

No feature needs a drill or tap inside a void: the only in-plane holes are the
actuator pad screws (from an external face on each loose part) and there are no
clamp taps because every tab is bonded.

## Assembly sequence

1. Deburr and clean the body pieces; check each ledge/notch with a shim gauge.
2. Seat the platform and both stages in the jig pockets; drop the frame over the jig's dowels.
   The jig sets the leaf planes and the free length; nothing else does.
3. Bond the 8 leaves on their ledges with the bars on top per `BONDING.md` (epoxy film,
   masking of the free length, bar as clamp; spring clips hold the bars during cure).
4. Cure, lift off the jig, check free travel by hand (the stops limit to ±0.3 mm).
5. Fit the actuators: outer guide bars are already in; drop the APA into its pocket with shims to a
   light preload, screw the frame pad from the plate edge (M2 × 5), then the stage pad from the
   coupler void (M2 × 8, ball-end key ≤25° through the front opening or stud + nut).
6. Route the leads out through the back-face windows; tie at the Ø3 holes; connect; drive each
   axis to ±50 µm and confirm no stop contact and no rub.
7. Fit the holder (2 × M2 on the platform front face); the fiber comes in from the back through
   the base opening and the Ø3 platform hole.

Bolt pattern for the base (Y, Z): {', '.join(f'({y:.1f}, {z:.1f})' for y, z in bolts)}.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    counts = {k: len(v) for k, v in parts.items()}
    print(f"wrote {out} ({counts})")
    return 0


def export_monolithic(variant: str, root: Path, rep: dict) -> int:
    """One-piece CNC plate (R06): the plate STEP, its profile DXF, the base
    plate, the assembly reference, the sheet, and a README with the order
    settings. Pins and screws are bought."""
    p, d, r = rep["parameters"], rep["derived"], rep["r02"]
    out = root / "manufacturing"
    out.mkdir(exist_ok=True)
    assembly = cq.importers.importStep(str(root / "STEP" / "parallel_yz_r01_assembly.step")).solids().vals()
    loaded = cq.importers.importStep(str(root / "STEP" / "parallel_yz_r01_loaded.step")).solids().vals()

    def kind(s):
        bb = s.BoundingBox()
        v = s.Volume()
        if bb.xmin < -0.5:
            return "base"
        if v < 60:
            return "pin"
        if (bb.xmax - bb.xmin) > p["b"] + 0.5:
            return "apa"
        if bb.xmin > p["b"] - 0.5:
            return "holder"
        return "plate"

    parts = {}
    for s in assembly:
        parts.setdefault(kind(s), []).append(s)
    for s in loaded:
        if kind(s) == "base":
            parts["base"] = [s]
    assert len(parts.get("plate", [])) == 1, f"expected one plate solid, got {len(parts.get('plate', []))}"

    def export(name, solids):
        cq.exporters.export(cq.Workplane("XY").add(solids), str(out / f"{name}.step"))

    export("plate", parts["plate"])
    export("base_plate", parts["base"])
    export("assembly_reference", assembly)
    shutil.copy(root / "STEP" / "parallel_yz_r02_profile.dxf", out / "plate_profile.dxf")
    sheet = root / "renders" / "drawing_r02.png"
    if sheet.exists():
        shutil.copy(sheet, out / "drawing_sheet.png")

    gap = d["pocket1"] - d["y_in1"] - 2 * p["pad_boss"]
    pin = r["pins"][0]
    box = d["box"]
    bolts = rep["fixture_mounted"]["points"]
    n_leaf = rep["edm"]["leaves"]
    readme = f"""# {variant.upper()} manufacturing package - one-piece CNC plate

Parallel-kinematic YZ fiber-alignment flexure, two {rep['actuator']['name']} actuators, monolithic
{rep['material']['name']} plate {box[1] - box[0]:.1f} x {box[3] - box[2]:.1f} x {p['b']:.0f} mm with eight thin-wall milled leaves
({p['t']:.2f} x {p['L']:.1f} mm, {p['b'] / p['t']:.0f}:1) and pin hard stops. Frame: X optical (plate thickness),
Y lateral, Z up; all files mm. Analysis: ../../README.md (sections "Monolithic CNC sweep" and {variant.upper()}).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `plate.step` (+ `plate_profile.dxf`, the through profile 1:1) | the flexure | 1 | {rep['material']['name']}, {p['b']:.0f} mm | CNC milling, one setup per face plus the edge drills; internal corners R{p['r_root']:.1f} (dia {2 * p['r_root']:.0f} cutter) | the {n_leaf} leaves: {p['t']:.2f} +/-0.02 thick, faces flat/parallel 0.01 over {p['b']:.0f}, perpendicular 0.01; finished last, light passes, hand deburr only. Pad lands coplanar +/-0.02 per leg, land gap {gap:.2f} +0.05/-0. Profile +/-0.05 elsewhere; faces ground flat 0.02 |
| `drawing_sheet.png` | shop sheet | - | - | - | every note above, dimensioned; send with the STEP |
| `base_plate.step` | mount | 1 | any aluminium | CNC, {rep['base']['t']:.0f} mm plate, opening {rep['base']['opening_mm'][0]:.0f} x {rep['base']['opening_mm'][1]:.0f}, 4 x dia {p['bolt']} | flat 0.02 where the flexure sits; a stiffness model - the station's real mount replaces it |
| `assembly_reference.step` | everything placed | - | - | reference: plate, 2 stop pins, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |

## Bought parts

| part | qty | notes |
|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT; 13 +/-0.1 pad-to-pad, M2 pads; shim 0.05-0.15 to the {gap:.2f} land gap |
| dowel pin dia {pin['dia']:.0f} m6 x {pin['length']:.0f} (ISO 8734 / DIN 6325) | 2 | pressed into the dia {pin['dia']:.0f} H7 holes from the outer edge; +/-{pin['travel_to_stop']:.2f} of travel per leg |
| M2 x 5 SHCS (frame pad), M2 x 8 SHCS (stage pad) | 2 + 2 | torque per CEDRAT; the stage screw's head bears on the stage's inner face (no counterbore), driven from the coupler void with a ball-end key or fitted as stud + nut |
| M4 x 20 SHCS + washers | 4 | base |
| 2-channel piezo amplifier (CEDRAT LA75 range or equivalent) | 1 | 1.1 uF per channel, >= 0.18 A peak for full stroke at 150 Hz |

## Ordering on Xometry (or any CNC shop)

- Process: CNC machining (milling). Material: {rep['material']['name']}. Finish: as machined, no anodising
  (a coating on the leaves changes their stiffness and hides burrs). Quantity: 1 (+1 spare recommended: the
  0.5 mm walls are the one feature a shop can scrap).
- Tolerance: choose the tightest general class offered (+/-.001" / 0.025 mm) and list the critical locations
  as the eight leaf thicknesses ({p['t']:.2f} +/-0.02), the four pad lands (coplanar +/-0.02, gap {gap:.2f} +0.05/-0)
  and the two dia {pin['dia']:.0f} H7 pin holes: 14 locations. Everything else is +/-0.05 per the sheet.
- Threads: 2 x M2 x {r['holder_tap_depth']:.0f} deep (front face). Upload `plate.step` and `drawing_sheet.png`; the DXF is
  a convenience for the profile only.
- Expect a DFM note on the {p['t']:.2f} mm walls ({p['b'] / p['t']:.0f}:1; most guides list 0.8 mm minimum for metals). Answer
  it with the sheet's leaf note (rough leaving 0.3, finish last both sides, no tumbling). If the shop declines,
  order variant m8t60k12 (0.60 walls, 13:1) from the same drawing set: 375 Hz instead of 431 Hz first mode.
- Wire EDM is an acceptable alternative for the leaves only (through-profile), if the shop prefers it.

## Tool access, feature by feature (one piece, no internal-face drilling)

| feature | axis | reached from |
|---|---|---|
| profile: leaves, voids, pockets, windows, notches, stop notches | X | both faces (through) |
| 4 x dia {p['bolt']:.1f} bolt holes, {len(r['wire_ties'])} x dia {r['wire_tie']:.0f} wire ties, fiber hole dia {p['fiber_hole']:.0f} + chamfers | X | the faces |
| 2 x M2 holder taps | X | front face |
| 4 pad lands (raised {p['pad_boss']:.1f}) | - | milled from the pocket, which is through |
| pad screw hole per leg: dia {r['screw_hole']:.1f} through wall, pocket and stage; c'bore dia {r['cbore']:.1f} x {r['cbore_frame']:.1f} | leg axis | the outer edge, one straight drill ({p['wall']:.0f} wall + {gap:.1f} pocket + {d['w_in']:.0f} stage) |
| 2 x dia {pin['dia']:.0f} H7 pin holes | across the leg | the outer edge, through the free wall into the notch |

## Assembly sequence

1. Deburr by hand, ultrasonic clean; check every leaf with a micrometer ({p['t']:.2f} +/-0.02) and sight the faces.
2. Press the two stop dowels from the outer edges until flush 1 mm below the edge; check +/-{pin['travel_to_stop']:.2f} free travel
   of each stage by hand (it must move freely and stop crisply both ways).
3. Fit the actuators: drop each APA into its pocket with shims to a light preload, screw the frame pad from
   the edge (M2 x 5), then the stage pad from the coupler void (M2 x 8, ball-end key, or stud + nut).
4. Route the leads out at the back face; tie at the dia {r['wire_tie']:.0f} holes; drive each axis to +/-50 um and confirm
   no stop contact and no rub.
5. Fit the holder (2 x M2 on the platform front face); the fiber comes in from the back through the base
   opening and the platform hole.

Bolt pattern for the base (Y, Z): {', '.join(f'({y:.1f}, {z:.1f})' for y, z in bolts)}.
"""
    (out / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote {out} ({ {k: len(v) for k, v in parts.items()} })")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)

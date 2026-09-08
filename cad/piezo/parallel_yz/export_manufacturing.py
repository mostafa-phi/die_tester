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
        raise SystemExit("export_manufacturing.py is for shim-mode variants (R04)")
    p, sh, d = rep["parameters"], rep["shim"], rep["derived"]
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
    export("clamp_bar", [parts["bar"][0]])
    export("shim_leaf", [parts["leaf"][0]])
    export("base_plate", parts["base"])
    export("assembly_reference", assembly)

    # Flat DXF of one shim: rectangle with the two clamp holes at each tab.
    depth, length = p["b"], p["L"] + 2 * p["tab"]
    hole_pitch = p["b"] / 2                   # the two screws sit at 1/4 and 3/4 of the depth
    holes = [(x, y) for y in (p["tab"] / 2, length - p["tab"] / 2) for x in (depth / 4, 3 * depth / 4)]
    leaf = (cq.Workplane("XY").rect(depth, length, centered=False)
            .extrude(p["t"]))
    for x, y in holes:
        leaf = leaf.cut(cq.Workplane("XY").center(x, y).circle(1.2).extrude(p["t"]))
    cq.exporters.exportDXF(leaf.faces("<Z"), str(out / "shim_leaf_flat.dxf"))

    shutil.copy(root / "STEP" / "parallel_yz_r02_profile.dxf", out / "body_profile.dxf")
    shutil.copy(root / "renders" / "drawing_r02.png", out / "drawing_sheet.png")

    n_screws = len(sh["screws"])
    bonded = sum(1 for b in sh["bars"] if b["access"] == "bond")
    bolts = rep["fixture_mounted"]["points"]
    readme = f"""# {args.variant.upper()} manufacturing package

Parallel-kinematic YZ fiber-alignment flexure, two {rep['actuator']['name']} actuators.
Frame: X optical (plate thickness), Y lateral, Z up; all files mm.
Analysis and the numbers behind every choice: ../../README.md (section {args.variant.upper()}).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `body_plate_4_pieces.step`, `body_profile.dxf` | body: frame, 2 input stages, platform | 1 plate → 4 pieces | {rep['material']['name']} | CNC mill: through-profile from the DXF, then ledges/notches, 4 pad lands (2.5 × 5, +0.2 raised), M2 clearance + counterbores on the actuator axes, {n_screws} × M2 clamp taps side-drilled, 2 × M2 holder taps, 4 × Ø{p['bolt']} thru, 2 × Ø3 wire ties | profile ±0.05; leaf ledges and notches flat 0.01, parallel 0.02 (they set the leaf planes); pad lands coplanar ±0.02, land gap {d['pocket1'] - d['y_in1'] - 2 * p['pad_boss']:.2f} +0.05/−0; stop gaps 0.30 +0.10/−0; both faces ground flat 0.02. **The four pieces come loose after the profile cut - bag them together.** |
| `shim_leaf.step`, `shim_leaf_flat.dxf` | leaf | 8 (+2 spares) | {p['leaf_material']['name']}, {p['t']:.2f} mm | shear or laser cut from precision shim stock, drill/laser 4 × Ø2.4; deburr, no bends | thickness {p['t']:.2f} ±0.005 (stock tolerance); outline ±0.05; flat; edges burr-free (fatigue). Free length {p['L']:.1f} is set by the clamp bars, not the leaf |
| `clamp_bar.step` | clamp bar | 16 (+4) | {rep['material']['name']} | CNC or saw from strip: {p['b']:.0f} × {p['tab']:.1f} × {p['bar_t']:.1f}, 2 × Ø2.2 thru on the {n_screws // 2} screwed bars ({bonded} bars are bonded, no holes needed) | the inner edge R0.3 defines the leaf root: break that edge consistently; faces flat 0.01 |
| `base_plate.step` | mount / base | 1 | any aluminium ({rep['material']['name']} fine) | CNC: {rep['base']['t']:.0f} mm plate, central opening {rep['base']['opening_mm'][0]:.0f} × {rep['base']['opening_mm'][1]:.0f}, windows behind the two pockets, 4 × Ø{p['bolt']} | flat 0.02 where the body sits (it is the mount reference); it is a stiffness model - replace by the station's real mount if one exists |
| `assembly_reference.step` | everything placed | - | - | reference only: body, leaves, bars, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |
| `drawing_sheet.png` | shop sheet | - | - | - | the tolerances, notes and assembly sequence in one page |

## Bought parts

| part | qty | source | notes |
|---|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT Technologies | 13 ±0.1 pad-to-pad, M2 pads; shim 0.05–0.15 to the {d['pocket1'] - d['y_in1'] - 2 * p['pad_boss']:.2f} land gap |
| M2 × 5 SHCS (frame pad), M2 × 8 SHCS (stage pad) | 2 + 2 | any | torque per CEDRAT |
| M2 × 6 SHCS, clamp bars | {n_screws} | stainless A2 | 0.3 N·m + Loctite 243 |
| M4 × 20 SHCS + washers, base | 4 | any | |
| structural epoxy (3M DP460 or Loctite EA 9460) | 1 | | for the {bonded} bonded tabs (recommended: bond all 16 and use the bars as cure fixtures) |
| 2-channel piezo amplifier | 1 | CEDRAT LA75 range or equivalent | 1.1 µF per channel, ≥0.18 A peak for full stroke at 150 Hz |

## Assembly sequence

1. Deburr and clean body pieces; check each ledge/notch with a shim gauge.
2. Place the frame on the base (4 × M4, do not torque). Fit the two stages and the platform in a
   simple jig (three pins on a flat plate at the platform and stage reference faces; the jig sets
   the leaf-plane parallelism).
3. Insert the 8 leaves on their ledges, bars on top; screw the {n_screws // 2} accessible bars
   (0.3 N·m); for the {bonded} inner guide bars (and optionally all), apply a thin epoxy film under the
   tab and clamp with the bar for the cure.
4. Cure, remove the jig, check free travel by hand (the stops limit to ±0.3 mm).
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


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)

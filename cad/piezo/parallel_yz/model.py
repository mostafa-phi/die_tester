"""Parallel-kinematic YZ flexure platform for two APA60S - concept R01.

One wire-EDM plate, 7075-T6, lying in the YZ plane (perpendicular to the optical
axis X) with the fiber passing through a hole in its central platform. The
platform is held by four identical legs, two of them driven:

    frame --[4 guide leaves, bend in the leg axis]-- input stage
          --[2 coupler leaves, bend across the leg axis]-- platform

The APA sits in a pocket between the frame and the input stage's outer face,
collinear with the leg axis, so it only ever sees motion along its own axis: the
coupler leaves carry the other axis' motion past it. Both actuators are grounded,
the moving mass is the platform, the input stages and the leaves, and the
stiffness the actuator sees is set by the leaf sections alone.

Frame: X optical (plate thickness, +X toward the die), Y lateral, Z up - the
same head frame as ../README.md. Units mm.

Runs in the `cad` environment (CadQuery 2.8); the FE scripts beside it run in
`pic-env`. Writes STEP/, geometry_report.json and nothing else.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import cadquery as cq

HERE = Path(__file__).resolve().parent
VENDOR = HERE.parent / "APA60S.step"

# Amplified actuators that fit the pocket: pad-to-pad length along the leg,
# shell length across it, and the spring the FE uses. Values from the CEDRAT
# datasheets (APA60S: vendor STEP + cases.json; APA120S: datasheet rev 06/2024,
# ICD 000620-ICD-01: 28.8 x 13 x 10, M2 pads 2.5 x 5, 1.9 deep).
ACTUATORS = {
    "APA60S": dict(apa_len=15.0, apa_long=29.3, apa_mass_g=8.5, apa_k_N_per_um=1.7,
                   apa_free_um=(75.0, 68.0), apa_force_limit_N=None, apa_blocked_free_Hz=None),
    "APA120S": dict(apa_len=13.0, apa_long=28.8, apa_mass_g=7.2, apa_k_N_per_um=0.33,
                    apa_free_um=(140.0, 130.0), apa_force_limit_N=32.0, apa_blocked_free_Hz=1300.0),
}

# Named variants: overrides on P. The baseline (no variant) is R01 with the APA60S.
VARIANTS = {
    # APA120S with thinner leaves: spend the larger stroke budget on range.
    "apa120s": dict(actuator="APA120S", t=0.30),
    # APA120S on the unchanged R01 leaves, to separate the actuator's effect from the leaves'.
    "apa120s_t040": dict(actuator="APA120S", t=0.40),
}

# Every number of the concept, in one place. Change here, rebuild, re-solve.
P = dict(
    t=0.40,          # leaf thickness (EDM web)
    L=17.0,          # leaf free length, coupler and guide alike
    b=10.0,          # plate thickness = leaf depth = APA60S thickness
    a_p=10.0,        # platform half-size (20 x 20 platform)
    s_c=7.0,         # coupler leaf centrelines at z = +/- s_c on the leg axis
    w_in=8.0,        # input stage width along the leg axis
    h_in=10.0,       # input stage half-height across the leg axis
    s_g=2.5,         # guide leaf centrelines at +/- s_g about the stage mid-plane
    g=1.5,           # void margin beyond the input stage's outer face
    r_root=0.5,      # root fillet on every profile vertex
    wall=6.0,        # frame wall beyond the APA pocket
    actuator="APA60S",   # key into ACTUATORS; sets apa_len, apa_long, mass, spring, stroke
    apa_clear=1.5,   # pocket clearance beyond the shell, each side
    pad=(2.5, 5.0),  # APA pad: 2.5 along the shell, 5.0 through the thickness (vendor STEP)
    pad_boss=0.2,    # raised land the pad bolts to, so the FE patch is an exact face
    fiber_hole=3.0,  # through the platform, along X
    bolt=4.5,        # corner clearance holes (M4) in the frame
    bolt_inset=7.0,
    # Payload for the loaded cases: the fiber holder, an aluminium block
    # 25 x 10 x 7 mm (user, 2026-09-07; 25 along the fiber, 10 across, 7 up),
    # standing on the platform's front face. 4.9 g at aluminium density; it
    # replaces the 70 g surrogate of the first solve. Fiber tip 5 mm beyond it.
    payload_len=25.0,                                  # along X
    payload_wy=10.0, payload_wz=7.0,                   # across, up
    payload_rho_kg_m3=2810.0, payload_E_MPa=71700.0, payload_nu=0.33,
    tip_ahead=30.0,  # fiber tip ahead of the plate's front face (25 mm holder + 5 mm)
    E_MPa=71700.0, nu=0.33, rho_kg_m3=2810.0,        # 7075-T6, as fem_r01
)


def resolve(p: dict) -> dict:
    """P with the chosen actuator's numbers folded in."""
    return {**p, **ACTUATORS[p["actuator"]]}


def derived(p: dict) -> dict:
    """Stations along a leg axis (the +Y leg; the others are rotations of it)."""
    y_in0 = p["a_p"] + p["L"]                 # input stage inner face
    y_in1 = y_in0 + p["w_in"]                 # input stage outer face (pad boss on it)
    c0 = p["h_in"] + p["L"]                   # guide leaves anchor into the frame here
    pocket0 = y_in1                           # APA pocket, inner end
    pocket1 = y_in1 + p["apa_len"] + 2 * p["pad_boss"]   # frame face carrying the far pad
    R = pocket1 + p["wall"]                   # plate half-size
    pocket_h = p["apa_long"] / 2 + p["apa_clear"]
    void_out = y_in1 + p["g"]                 # guide void, outer y extent
    return dict(y_in0=y_in0, y_in1=y_in1, c0=c0, pocket0=pocket0, pocket1=pocket1,
                R=R, pocket_h=pocket_h, void_out=void_out,
                guide_y=(y_in0 + p["w_in"] / 2 - p["s_g"], y_in0 + p["w_in"] / 2 + p["s_g"]))


# Leg axes: +Y, +Z driven; -Y, -Z passive. (cos, sin) of the rotation that takes
# the +Y leg onto each leg, applied to (y, z).
LEGS = {"+Y": (1, 0), "+Z": (0, 1), "-Y": (-1, 0), "-Z": (0, -1)}
DRIVEN = ("+Y", "+Z")


def rot(leg: str, y: float, z: float) -> tuple[float, float]:
    c, s = LEGS[leg]
    return c * y - s * z, s * y + c * z


def rect_rot(leg: str, y0, y1, z0, z1) -> tuple[float, float, float, float]:
    """Axis-aligned box of the +Y leg, rotated onto `leg`; returns (y0, y1, z0, z1)."""
    ys, zs = zip(*(rot(leg, y, z) for y in (y0, y1) for z in (z0, z1)))
    return min(ys), max(ys), min(zs), max(zs)


def leg_rects(p: dict, d: dict) -> dict:
    """Voids, solids and leaf boxes of the +Y leg as (y0, y1, z0, z1)."""
    t2 = p["t"] / 2
    voids = [
        # everything between the platform edge and the guide void's outer end,
        # over the full anchor height: the leaves and the stage are added back
        (p["a_p"], d["void_out"], -d["c0"], d["c0"]),
        # APA pocket
        (d["pocket0"], d["pocket1"], -d["pocket_h"], d["pocket_h"]),
    ]
    stage = (d["y_in0"], d["y_in1"], -p["h_in"], p["h_in"])
    leaves = []
    for z in (-p["s_c"], p["s_c"]):                          # coupler leaves, along Y
        leaves.append((p["a_p"], d["y_in0"], z - t2, z + t2))
    for y in d["guide_y"]:                                    # guide leaves, along Z
        leaves.append((y - t2, y + t2, p["h_in"], d["c0"]))
        leaves.append((y - t2, y + t2, -d["c0"], -p["h_in"]))
    return dict(voids=voids, stage=stage, leaves=leaves)


def _rect(sk: cq.Sketch, r, mode: str) -> cq.Sketch:
    y0, y1, z0, z1 = r
    return sk.push([((y0 + y1) / 2, (z0 + z1) / 2)]).rect(y1 - y0, z1 - z0, mode=mode).reset()


def build(p: dict) -> tuple[cq.Workplane, cq.Workplane, dict]:
    d = derived(p)
    R = d["R"]
    # The plate profile in the YZ plane: local sketch x = global Y, y = global Z.
    sk = cq.Sketch().rect(2 * R, 2 * R)
    per_leg = {}
    for leg in LEGS:
        rects = leg_rects(p, d)
        per_leg[leg] = {
            "voids": [rect_rot(leg, *r) for r in rects["voids"]],
            "stage": rect_rot(leg, *rects["stage"]),
            "leaves": [rect_rot(leg, *r) for r in rects["leaves"]],
        }
    for leg in LEGS:
        for r in per_leg[leg]["voids"]:
            sk = _rect(sk, r, "s")
    for leg in LEGS:
        sk = _rect(sk, per_leg[leg]["stage"], "a")
        for r in per_leg[leg]["leaves"]:
            sk = _rect(sk, r, "a")
    sk = sk.clean()
    sk = sk.reset().vertices().fillet(p["r_root"]).reset()

    plate = cq.Workplane("YZ").placeSketch(sk).extrude(p["b"])

    # Pad lands: on the driven input stages' outer faces and the opposing frame faces.
    x0 = (p["b"] - p["pad"][1]) / 2
    pads = {}
    for leg in DRIVEN:
        for side, y_face, direction in (("stage", d["y_in1"], +1), ("frame", d["pocket1"], -1)):
            y_a, y_b = sorted((y_face, y_face + direction * p["pad_boss"]))
            box = rect_rot(leg, y_a, y_b, -p["pad"][0] / 2, p["pad"][0] / 2)
            boss = (cq.Workplane("XY")
                    .box(p["b"], box[1] - box[0], box[3] - box[2], centered=False)
                    .translate((0, box[0], box[2])))
            # only the pad footprint through the thickness
            boss = boss.intersect(cq.Workplane("XY").box(p["pad"][1], 2 * R, 2 * R, centered=False)
                                  .translate((x0, -R, -R)))
            plate = plate.union(boss)
            y_pad = y_face + direction * p["pad_boss"]
            axis = "y" if leg[1] == "Y" else "z"
            other = "z" if axis == "y" else "y"
            sign = 1 if leg[0] == "+" else -1
            pads[f"{leg[1]}_{side}"] = {
                "x": [x0, x0 + p["pad"][1]],
                axis: sign * y_pad,
                other: [-p["pad"][0] / 2, p["pad"][0] / 2],
                "normal": {axis: sign * direction},
                "leg": leg, "side": side,
            }

    # Fiber hole through the platform, corner bolt holes through the frame.
    plate = plate.cut(cq.Workplane("YZ").circle(p["fiber_hole"] / 2).extrude(p["b"]))
    inset = R - p["bolt_inset"]
    holes = (cq.Workplane("YZ")
             .pushPoints([(sy * inset, sz * inset) for sy in (-1, 1) for sz in (-1, 1)])
             .circle(p["bolt"] / 2).extrude(p["b"]))
    plate = plate.cut(holes)

    # Payload block on the front face, centred on the fiber.
    hy, hz = p["payload_wy"] / 2, p["payload_wz"] / 2
    payload = (cq.Workplane("XY")
               .box(p["payload_len"], p["payload_wy"], p["payload_wz"], centered=False)
               .translate((p["b"], -hy, -hz)))

    info = {"derived": d, "legs": per_leg, "pads": pads,
            "payload_box": {"x": [p["b"], p["b"] + p["payload_len"]],
                            "y": [-hy, hy], "z": [-hz, hz]}}
    return plate, payload, info


def place_apa(p: dict, d: dict, leg: str) -> cq.Workplane | None:
    """Vendor APA60S dropped into a driven leg's pocket, for the assembly STEP."""
    if not VENDOR.exists() or p["actuator"] != "APA60S":
        return None                         # only the APA60S STEP is on hand
    apa = cq.importers.importStep(str(VENDOR)).val()
    centre = (d["y_in1"] + d["pocket1"]) / 2
    origin, y_axis, z_axis, x_axis = cq.Vector(0, 0, 0), cq.Vector(0, 1, 0), cq.Vector(0, 0, 1), cq.Vector(1, 0, 0)
    # Vendor frame: x along the shell, y motion axis (pads at +/-7.5), z thickness.
    if leg == "+Y":
        # (x, y, z) -> (-z, y, x): shell along Z, motion along Y, thickness along X
        apa = apa.rotate(origin, y_axis, -90)
        apa = apa.translate(cq.Vector(p["b"] / 2, centre, 0))
    else:
        # (x, y, z) -> (z, x, y): shell along Y, motion along Z, thickness along X
        apa = apa.rotate(origin, x_axis, 90).rotate(origin, z_axis, 90)
        apa = apa.translate(cq.Vector(p["b"] / 2, 0, centre))
    return cq.Workplane("XY").add(apa)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", default=None, choices=sorted(VARIANTS),
                        help="build a named variant into variants/<name>/ instead of the baseline")
    args = parser.parse_args()

    P = resolve({**globals()["P"], **VARIANTS.get(args.variant, {})})
    root = HERE if args.variant is None else HERE / "variants" / args.variant
    step_dir = root / "STEP"
    step_dir.mkdir(parents=True, exist_ok=True)
    plate, payload, info = build(P)
    d = info["derived"]

    plate_solid = plate.val()
    vol = plate_solid.Volume()
    rho = P["rho_kg_m3"] * 1e-6                        # g/mm3
    plate_mass_g = vol * rho
    payload_vol = payload.val().Volume()
    payload_g = payload_vol * P["payload_rho_kg_m3"] * 1e-6

    # Moving-mass bookkeeping from the profile rectangles (leaves at half weight,
    # a beam's effective mass); the FE modal is the real answer.
    stage_mm2 = P["w_in"] * 2 * P["h_in"]
    leaf_mm2 = P["t"] * P["L"]
    platform_g = ((2 * P["a_p"]) ** 2 - 3.14159 * (P["fiber_hole"] / 2) ** 2) * P["b"] * rho
    stage_g = stage_mm2 * P["b"] * rho
    leaf_g = leaf_mm2 * P["b"] * rho
    moving_one_axis_g = platform_g + 2 * stage_g + 0.5 * (8 + 4) * leaf_g + P["apa_mass_g"] / 2

    cq.exporters.export(plate, str(step_dir /"parallel_yz_r01.step"))
    loaded = cq.Workplane("XY").add(plate.val()).add(payload.val())
    cq.exporters.export(loaded, str(step_dir /"parallel_yz_r01_loaded.step"))
    assembly = cq.Workplane("XY").add(plate.val())
    for leg in DRIVEN:
        apa = place_apa(P, d, leg)
        if apa is not None:
            assembly = assembly.add(apa.val())
    cq.exporters.export(assembly, str(step_dir /"parallel_yz_r01_assembly.step"))

    leaf_boxes = []
    for leg, parts in info["legs"].items():
        for (y0, y1, z0, z1) in parts["leaves"]:
            leaf_boxes.append({"x": [0.0, P["b"]], "y": [y0, y1], "z": [z0, z1], "leg": leg})
    stage_boxes = {leg: {"x": [0.0, P["b"]], "y": [r[0], r[1]], "z": [r[2], r[3]]}
                   for leg, r in ((leg, parts["stage"]) for leg, parts in info["legs"].items())}

    report = {
        "concept": f"parallel-kinematic YZ platform, four P-P legs, two {P['actuator']} grounded to the frame",
        "variant": args.variant or "R01 baseline",
        "frame": "X optical (plate thickness, +X toward the die), Y lateral, Z up; mm",
        "parameters": P,
        "derived": d,
        "plate_mm": [P["b"], 2 * d["R"], 2 * d["R"]],
        "plate_volume_mm3": vol,
        "plate_mass_g": plate_mass_g,
        "mass_estimates_g": {
            "platform": platform_g, "input_stage": stage_g, "leaf": leaf_g,
            "moving_per_axis_incl_half_apa": moving_one_axis_g,
            "note": "profile-rectangle estimates; the FE modal carries the real mass",
        },
        "material": {"name": "7075-T6 (Fusion 'Aluminum 7075' values, as fem_r01)",
                     "E_MPa": P["E_MPa"], "nu": P["nu"], "rho_kg_m3": P["rho_kg_m3"]},
        "payload": {"mass_g": payload_g, "box": info["payload_box"],
                    "rho_kg_m3": P["payload_rho_kg_m3"], "E_MPa": P["payload_E_MPa"],
                    "nu": P["payload_nu"],
                    "com": [P["b"] + P["payload_len"] / 2, 0.0, 0.0],
                    "source": "user 2026-09-07: aluminium block 25 x 10 x 7 mm; "
                              "orientation (25 along the fiber) and mounting on the front face assumed"},
        "tip": [P["b"] + P["tip_ahead"], 0.0, 0.0],
        "pads": info["pads"],
        "actuator": {"name": P["actuator"], "k_N_per_um": P["apa_k_N_per_um"], "mass_g": P["apa_mass_g"],
                     "free_stroke_um": {"nominal": P["apa_free_um"][0], "minimum": P["apa_free_um"][1]},
                     "force_limit_N": P["apa_force_limit_N"], "blocked_free_Hz": P["apa_blocked_free_Hz"]},
        "leaf_boxes": leaf_boxes,
        "stage_boxes": stage_boxes,
        "platform_box": {"x": [0.0, P["b"]], "y": [-P["a_p"], P["a_p"]], "z": [-P["a_p"], P["a_p"]]},
        "fixture": {"face": "x = 0 (back face)", "outside_square_half": d["void_out"],
                    "rule": "back-face facets with max(|y|,|z|) > outside_square_half are fixed"},
        "outputs": ["STEP/parallel_yz_r01.step", "STEP/parallel_yz_r01_loaded.step",
                    "STEP/parallel_yz_r01_assembly.step"],
    }
    (root / "geometry_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[{report['variant']}] {P['actuator']}, leaves {P['t']} mm -> {root}")
    print(f"plate {P['b']:.0f} x {2 * d['R']:.1f} x {2 * d['R']:.1f} mm, "
          f"{vol:.0f} mm3, {plate_mass_g:.1f} g; moving per axis ~{moving_one_axis_g:.1f} g")
    print(f"payload block {payload_vol:.0f} mm3 at {P['payload_rho_kg_m3']:.0f} kg/m3 = {payload_g:.2f} g")
    print("wrote", ", ".join(report["outputs"]), "and geometry_report.json")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # OCP's interpreter teardown segfaults on this machine (see ../README.md);
    # everything is written and flushed, so leave without running it.
    os._exit(code)

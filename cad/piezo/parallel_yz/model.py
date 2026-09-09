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
    # R02: the apa120s plate detailed for manufacture - screw access, hard stops,
    # holder holes, wire ties, lightening windows - and solved on a bolted base.
    "r02": dict(actuator="APA120S", t=0.30, r02=True, bolt_inset=6.0),
    # R03 (2026-09-08): minimum-cut version. Two legs only, one guide pair per
    # leg (8 leaves, 6 threaded contours), leaves thick enough to mill.
    # Same stroke budget: 3 leaves bend per axis, so t=1.0 x L=26 in an 8 mm
    # plate gives k ~ 0.06 N/um, and 1.0 x 8 mm walls are within CNC limits.
    # Guide pair spread to +/-7 on a 16 mm stage: a two-leg plate has no passive
    # leg to balance the coupler's bending moment, so the stage's own rotational
    # stiffness (~ spacing^2) is what keeps Y out of Z.
    "r03": dict(actuator="APA120S", t=1.0, L=29.0, b=8.0, w_in=16.0, s_g=7.0, s_c=8.0, r02=True,
                legs=("+Y", "+Z"), guide_sides="plus", windows=False,
                # walls sized so the four M4 holes clear both the pockets and the base opening
                wall=9.0, wall_free=10.0, bolt_inset=5.5, base_margin=1.0,
                wire_tie_pos=(62.0, 24.0)),
    # R03 in a 10 mm plate: the same eight cuts, leaves 1.0 x 31 (10:1 walls),
    # for out-of-plane stiffness ~ b^3 - R03's first mode is the X bounce.
    "r03b": dict(actuator="APA120S", t=1.0, L=31.0, b=10.0, w_in=16.0, s_g=7.0, s_c=8.0, r02=True,
                 legs=("+Y", "+Z"), guide_sides="plus", windows=False,
                 wall=9.0, wall_free=10.0, bolt_inset=5.5, base_margin=1.0,
                 wire_tie_pos=(64.0, 24.0)),
    # R04 (2026-09-08): R03's topology with 0.20 mm 17-7PH shim leaves clamped
    # on a CNC 6061 body. k_leaf = E b t^3 / L^3 = 21 N/mm at L = 8.5, so four
    # bending leaves per axis give ~0.085 N/um; working stress ~200 MPa, 500 MPa
    # at the 0.3 mm stop. The stage width follows from tabs, bars and the guide
    # pair spacing; wall and inset sized so the four M4 clear pockets and opening.
    "r04": dict(actuator="APA120S", shim=True, t=0.20, L=8.5, b=8.0, s_g=6.0, s_c=7.5, r02=True,
                legs=("+Y", "+Z"), guide_sides="plus", windows=False,
                wall=6.5, wall_free=8.0, bolt_inset=5.5, base_margin=1.0,
                wire_tie_pos=(46.0, 21.0),
                body_material=dict(name="6061-T6", E_MPa=68900.0, nu=0.33, rho_kg_m3=2700.0)),
    # R05 (2026-09-08 machining review): R04 detailed for CNC + bonded assembly.
    # R1.0 internal radii (dia 2 cutter, 4:1 in 8 mm), 1.0 mm stop posts, no
    # clamp screws/taps (bonded tabs), ledge reliefs, per-part exports and jig.
    "r05": dict(actuator="APA120S", shim=True, t=0.20, L=8.5, b=8.0, s_g=6.0, s_c=7.5, r02=True,
                legs=("+Y", "+Z"), guide_sides="plus", windows=False,
                wall=6.5, wall_free=8.0, bolt_inset=5.5, base_margin=1.0,
                wire_tie_pos=(46.0, 21.0), r_root=1.0, bond_all=True, post_w=(1.0, 1.0), lightening=True,
                body_material=dict(name="6061-T6", E_MPa=68900.0, nu=0.33, rho_kg_m3=2700.0)),
}

# R02 detailing, all in the frame of the +Y leg (rotated onto the others).
R02 = dict(
    screw_hole=2.2,          # M2 clearance, along the leg axis, through stage and frame wall
    cbore=4.0, cbore_stage=2.2, cbore_frame=3.0,   # socket-head counterbores (dia, depths)
    # Tongue-and-fork stop in the coupler void: the tongue hangs from the stage's
    # inner face, the two posts stand on the platform edge. Gaps are one EDM wire
    # kerf, 0.30 mm, i.e. 5x the nominal travel; they stop before the leaves yield.
    stop_gap=0.30,
    tongue=(3.5, 5.5),       # z range of the tongue; posts sit either side with stop_gap
    tongue_len=15.0,         # from the stage inner face toward the platform
    post_len=4.0,            # from the platform edge toward the stage
    post_w=(0.9, 0.7),       # inner / outer post widths (outer one is limited by the leaf)
    holder_tap=1.6, holder_tap_depth=6.0, holder_tap_y=3.5,   # 2 x M2 on the front face
    fiber_chamfer=0.5,
    wire_tie=3.0, wire_tie_pos=(42.0, 21.0),   # dia, (along, across) the driven leg
    window=(33.5, 44.5),     # corner lightening window, square, same range in y and z
    base_t=10.0, base_margin=3.5, bolt_washer_r=6.0,   # the mount model: opening = moving region + margin
)

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
    r02=False,       # manufacturing detail (dict R02) and the bolted base in the loaded STEP
    legs=("+Y", "+Z", "-Y", "-Z"),   # which legs exist; R03 keeps only the driven two
    guide_sides="both",   # "both": guide leaves above and below the stage; "plus": one pair only
    wall_free=8.0,   # frame wall on a side that has no leg
    windows=True,    # corner lightening windows (R02 only; needs the corner blocks)
    # R04 "shim" mode: the leaves are not part of the profile but separate
    # spring-steel shims standing edgewise, clamped by bars on milled ledges.
    # t is then the shim thickness, L the free length between clamp edges.
    shim=False,
    tab=3.5,         # clamped tab length at each leaf end
    bar_t=2.0,       # clamp bar thickness (2 x M2 per bar; its edge defines the root, R0.3)
    leaf_material=dict(name="17-7PH CH900 precision shim", E_MPa=204000.0, nu=0.30, rho_kg_m3=7800.0),
    body_material=None,   # None: the plate material below; R04 uses 6061-T6
    # R05 machining pass: every tab epoxy-bonded (no clamp screws, no taps, plain
    # shims), bars kept as bonded backup blocks with the root edge radiused;
    # ledges run r_root past the tab so the tab end clears the cutter radius.
    bond_all=False,
    bar_edge_r=0.3,
    post_w=None,     # stop post widths override (R02["post_w"] when None)
    # Two-leg plates: lightening windows in the +Y+Z corner block and in the
    # frame beside each pocket (the frame is fixed, so this is weight only).
    lightening=False,
    lightening_wall=1.75,
    apa_clear=1.5,   # pocket clearance beyond the shell, each side
    apa_fit=0.15,    # land-to-land gap = apa_len + apa_fit: the APA120S is 13 +/-0.1 (ICD), shim to fit
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
    # In shim mode the platform grows a short arm toward each stage so that the
    # coupler tabs of the two legs land on different arms instead of crossing
    # each other in the platform corner (they did, in the first R04 build).
    arm = p["tab"] + 0.5 if p["shim"] else 0.0
    a_leg = p["a_p"] + arm                    # platform extent along a leg axis
    y_in0 = a_leg + p["L"]                    # input stage inner face
    if p["shim"]:
        # Guide shims stand at y_g1 / y_g2 (each occupies [y_g, y_g + t]); the
        # stage runs from the coupler tab to the outer guide's bar.
        y_g1 = y_in0 + p["tab"] + p["bar_t"]
        y_g2 = y_g1 + 2 * p["s_g"]
        y_in1 = y_g2 + p["t"] + p["bar_t"]
        guide_y = (y_g1, y_g2)
    else:
        y_in1 = y_in0 + p["w_in"]             # input stage outer face (pad boss on it)
        guide_y = (y_in0 + p["w_in"] / 2 - p["s_g"], y_in0 + p["w_in"] / 2 + p["s_g"])
    c0 = p["h_in"] + p["L"]                   # guide leaves anchor into the frame here
    pocket0 = y_in1                           # APA pocket, inner end
    pocket1 = y_in1 + p["apa_len"] + p["apa_fit"] + 2 * p["pad_boss"]   # frame face carrying the far pad
    R = pocket1 + p["wall"]                   # plate half-size on a side that has a leg
    pocket_h = p["apa_long"] / 2 + p["apa_clear"]
    void_out = y_in1 + p["g"]                 # guide void, outer y extent
    # Across the leg, the void spans the guide anchors on the sides that have
    # guide leaves and just clears the stage on a side that has none.
    void_lo = -c0 if p["guide_sides"] == "both" else -(p["h_in"] + p["g"])
    # Outer box: a leg's side reaches R, a leg-less side is a bare wall beyond
    # the voids that touch it (the neighbouring leg's stage clearance).
    free = p["h_in"] + p["g"] + p["wall_free"]
    legs = set(p["legs"])
    box = (-R if "-Y" in legs else -free, R if "+Y" in legs else R,
           -R if "-Z" in legs else -free, R if "+Z" in legs else R)
    # The moving region (nothing outside it may be fixed): a leg's void reaches
    # void_out along its axis; a leg-less side is just the stage clearance.
    clear = p["h_in"] + p["g"]
    inner = (-void_out if "-Y" in legs else -clear, void_out if "+Y" in legs else clear,
             -void_out if "-Z" in legs else -clear, void_out if "+Z" in legs else clear)
    return dict(y_in0=y_in0, y_in1=y_in1, w_in=y_in1 - y_in0, c0=c0, pocket0=pocket0, pocket1=pocket1,
                arm=arm, a_leg=a_leg,
                R=R, pocket_h=pocket_h, void_out=void_out, void_lo=void_lo, box=box, inner=inner,
                guide_y=guide_y)


# Leg axes: +Y, +Z driven; -Y, -Z passive. Each entry is the 2 x 2 map that
# takes the +Y leg's (y, z) onto that leg. +Z is the MIRROR y<->z, not a
# rotation, so a single-sided guide (R03) lands on the +Y+Z corner for both
# legs; on a four-leg plate the two choices are equivalent by symmetry.
LEGS = {"+Y": ((1, 0), (0, 1)), "+Z": ((0, 1), (1, 0)),
        "-Y": ((-1, 0), (0, 1)), "-Z": ((0, 1), (-1, 0))}
DRIVEN = ("+Y", "+Z")


def rot(leg: str, y: float, z: float) -> tuple[float, float]:
    (a, b), (c, d) = LEGS[leg]
    return a * y + b * z, c * y + d * z


def rect_rot(leg: str, y0, y1, z0, z1) -> tuple[float, float, float, float]:
    """Axis-aligned box of the +Y leg, rotated onto `leg`; returns (y0, y1, z0, z1)."""
    ys, zs = zip(*(rot(leg, y, z) for y in (y0, y1) for z in (z0, z1)))
    return min(ys), max(ys), min(zs), max(zs)


def leg_rects(p: dict, d: dict) -> dict:
    """Voids, solids and leaf boxes of the +Y leg as (y0, y1, z0, z1)."""
    t2 = p["t"] / 2
    voids = [
        # everything between the platform edge and the guide void's outer end,
        # over the guide anchor height: the leaves and the stage are added back
        (p["a_p"], d["void_out"], d["void_lo"], d["c0"]),
        # APA pocket
        (d["pocket0"], d["pocket1"], -d["pocket_h"], d["pocket_h"]),
    ]
    stage = (d["y_in0"], d["y_in1"], -p["h_in"], p["h_in"])
    leaves, notches, bars, roles = [], [], [], []
    arms = []
    if p["shim"]:
        t, tab, bt = p["t"], p["tab"], p["bar_t"]
        a, y0, y1, h, c0 = d["a_leg"], d["y_in0"], d["y_in1"], p["h_in"], d["c0"]
        arms.append((p["a_p"], a, -p["a_p"], p["a_p"]))      # platform arm toward this stage
        # Coupler shims lie on ledges at z = +/-s_c (shim above the top ledge,
        # below the bottom one); the tabs reach `tab` into the arm and the stage.
        for s in (1, -1):
            z_face = s * p["s_c"]
            z_lo, z_hi = sorted((z_face, z_face + s * t))
            leaves.append((a - tab, y0 + tab, z_lo, z_hi))
            b_lo, b_hi = sorted((z_face + s * t, z_face + s * (t + bt)))
            bars += [(a - tab, a, b_lo, b_hi), (y0, y0 + tab, b_lo, b_hi)]
            roles += ["coupler_platform", "coupler_stage"]
            # ledges: everything above (below) the shim face is removed over the
            # tab, plus r_root of relief so the tab end never rides the cutter radius
            rr = p["r_root"]
            l_lo, l_hi = sorted((z_face, s * p["a_p"]))
            notches.append((a - tab - rr, a, l_lo, l_hi))
            notches.append((y0, y0 + tab + rr, z_face, h) if s > 0 else (y0, y0 + tab + rr, -h, z_face))
        # Guide shims stand at y_g (occupying [y_g, y_g + t]) from tab below the
        # stage top to tab into the frame; the inner one is clamped from the
        # inside (bar toward the platform), the outer one from the outside.
        y_g1, y_g2 = d["guide_y"]
        for y_g, side in ((y_g1, -1), (y_g2, +1)):
            leaves.append((y_g, y_g + t, h - tab, c0 + tab))
            rr = p["r_root"]
            if side < 0:
                bar_y = (y_g - bt, y_g)
                notch_y = (y_g - bt, y_g + t)
                # At the frame the inner notch runs back to where the other
                # leg's void ends (c0), or the two legs' notches leave an island
                # in the corner (they did, twice).
                frame_notch_y = (min(y0, c0), y_g + t)
            else:
                bar_y = (y_g + t, y_g + t + bt)
                notch_y = (y_g, y_g + t + bt)
                frame_notch_y = notch_y
            # Notches run r_root deeper than the tab (relief for the tab end).
            bars += [(bar_y[0], bar_y[1], h - tab, h), (bar_y[0], bar_y[1], c0, c0 + tab)]
            notches += [(notch_y[0], notch_y[1], h - tab - rr, h), (frame_notch_y[0], frame_notch_y[1], c0, c0 + tab + rr)]
            which = "inner" if side < 0 else "outer"
            roles += [f"guide_{which}_stage", f"guide_{which}_frame"]
    else:
        for z in (-p["s_c"], p["s_c"]):                          # coupler leaves, along Y
            leaves.append((p["a_p"], d["y_in0"], z - t2, z + t2))
        for y in d["guide_y"]:                                    # guide leaves, along Z
            leaves.append((y - t2, y + t2, p["h_in"], d["c0"]))
            if p["guide_sides"] == "both":
                leaves.append((y - t2, y + t2, -d["c0"], -p["h_in"]))
    return dict(voids=voids, stage=stage, leaves=leaves, notches=notches, bars=bars, roles=roles, arms=arms)


# How each clamp bar is fastened, from tracing a straight driver path to its
# screws inside the finished plate (2026-09-08 review): "screw" has a clear
# in-plane path, "angled" only a ball-end key through the front opening, and
# "bond" none at all - those tabs are epoxy-bonded (DP460 / EA 9460) in a jig,
# the bar staying as cure fixture and mechanical backup.
BAR_ACCESS = {
    "coupler_platform": "screw",       # heads face the open channel toward the frame corner
    "coupler_stage": "angled",         # an 8-12 mm window, then frame
    "guide_outer_stage": "screw",      # heads face the actuator pocket, fitted before the APA
    "guide_inner_stage": "bond",       # heads would face the stage coupler bar
    "guide_outer_frame": "angled",     # into the guide void
    "guide_inner_frame": "angled",
}


def bolt_points(p: dict, d: dict) -> list[tuple[float, float]]:
    y0, y1, z0, z1 = d["box"]
    i = p["bolt_inset"]
    if set(p["legs"]) == {"+Y", "+Z"}:
        # Two-leg plate: the +Y/-Z and -Y/+Z corners sit beside the pockets, so
        # those two bolts slide along the free walls to under/beside the stages.
        mid = d["y_in0"] + d["w_in"] / 2
        return [(y1 - i, z1 - i), (y0 + i, z0 + i), (mid, z0 + i), (y0 + i, mid)]
    return [(y0 + i, z0 + i), (y0 + i, z1 - i), (y1 - i, z0 + i), (y1 - i, z1 - i)]


def _rect(sk: cq.Sketch, r, mode: str) -> cq.Sketch:
    y0, y1, z0, z1 = r
    return sk.push([((y0 + y1) / 2, (z0 + z1) / 2)]).rect(y1 - y0, z1 - z0, mode=mode).reset()


def _box(r, x0: float, x1: float) -> cq.Workplane:
    """Through-thickness box from a (y0, y1, z0, z1) rectangle."""
    y0, y1, z0, z1 = r
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def _cyl_along(leg: str, y_from: float, y_to: float, z: float, x: float, dia: float) -> cq.Workplane:
    """Cylinder along the +Y leg's axis from y_from to y_to (rotated onto `leg`)."""
    ya, yb = sorted((y_from, y_to))
    p0 = rot(leg, ya, z)
    p1 = rot(leg, yb, z)
    direction = cq.Vector(0, p1[0] - p0[0], p1[1] - p0[1])
    solid = cq.Solid.makeCylinder(dia / 2, direction.Length, cq.Vector(x, p0[0], p0[1]),
                                  direction.normalized())
    return cq.Workplane("XY").add(solid)


def _cyl_through(y: float, z: float, dia: float, x0: float, x1: float) -> cq.Workplane:
    return cq.Workplane("XY").add(cq.Solid.makeCylinder(dia / 2, x1 - x0, cq.Vector(x0, y, z),
                                                          cq.Vector(1, 0, 0)))


def r02_stops(p: dict, d: dict) -> dict:
    """Tongue and fork rectangles of the +Y leg, (y0, y1, z0, z1)."""
    r = R02
    z0, z1 = r["tongue"]
    g = r["stop_gap"]
    # The tongue reaches 2 mm into the fork whatever the leaf length is.
    a = d.get("a_leg", p["a_p"])            # platform edge along the leg (arm end in shim mode)
    tongue = (a + r["post_len"] - 2.0, d["y_in0"] + 0.5, z0, z1)      # 0.5 into the stage
    pw = p.get("post_w") or r["post_w"]
    post_in = (a - 0.5, a + r["post_len"], z0 - g - pw[0], z0 - g)
    post_out = (a - 0.5, a + r["post_len"], z1 + g, z1 + g + pw[1])
    assert post_out[3] < p["s_c"] - p["t"] / 2 - 0.3, "outer post too close to the coupler leaf"
    return dict(tongue=tongue, posts=[post_in, post_out])


def add_r02(plate: cq.Workplane, p: dict, d: dict) -> tuple[cq.Workplane, dict]:
    """Manufacturing detail on top of the concept plate; returns the plate and what was added."""
    r = R02
    R = d["R"]
    added = {"stops": [], "screw_holes": [], "wire_ties": [], "windows": [], "holder_taps": []}

    # Hard stops on every leg (sharp boxes, unioned after the filleted profile:
    # a 0.7 mm post cannot carry R0.5 fillets).
    stops = r02_stops(p, d)
    for leg in p["legs"]:
        for rect in [stops["tongue"], *stops["posts"]]:
            box = rect_rot(leg, *rect)
            plate = plate.union(_box(box, 0.0, p["b"]))
            added["stops"].append({"x": [0.0, p["b"]], "y": [box[0], box[1]], "z": [box[2], box[3]], "leg": leg})

    # M2 screw access on the driven legs: through the input stage from the coupler
    # void (counterbore on the inner face) and through the frame wall from the
    # outer edge (counterbore on the edge). Both run on the leg axis through the
    # pad lands into the actuator's tapped pads.
    xm = p["b"] / 2
    for leg in [leg for leg in DRIVEN if leg in p["legs"]]:
        stage_hole = _cyl_along(leg, d["y_in0"] - 1.0, d["y_in1"] + p["pad_boss"] + 0.1, 0.0, xm, r["screw_hole"])
        stage_cb = _cyl_along(leg, d["y_in0"] - 1.0, d["y_in0"] + r["cbore_stage"], 0.0, xm, r["cbore"])
        frame_hole = _cyl_along(leg, d["pocket1"] - p["pad_boss"] - 0.1, R + 1.0, 0.0, xm, r["screw_hole"])
        frame_cb = _cyl_along(leg, R - r["cbore_frame"], R + 1.0, 0.0, xm, r["cbore"])
        for cyl in (stage_hole, stage_cb, frame_hole, frame_cb):
            plate = plate.cut(cyl)
        added["screw_holes"].append({"leg": leg, "stage": "M2 x 8 SHCS from the coupler void",
                                     "frame": "M2 x 5 SHCS from the outer edge"})
        # Wire-tie holes beside the pocket, one each side of the actuator where
        # there is frame to drill (a two-leg plate has frame on one side only).
        tie = p.get("wire_tie_pos", r["wire_tie_pos"])
        for s in (-1, 1):
            y, z = rot(leg, tie[0], s * tie[1])
            if not plate.val().isInside(cq.Vector(p["b"] / 2, y, z)):
                continue
            plate = plate.cut(_cyl_through(y, z, r["wire_tie"], -1.0, p["b"] + 1.0))
            added["wire_ties"].append([y, z])

    # Two-leg plates: a window in the corner block and one in the frame beside
    # each pocket, walls `lightening_wall` from every void, hole and bolt.
    if p.get("lightening") and set(p["legs"]) == {"+Y", "+Z"}:
        w = p["lightening_wall"]
        bolt_edge = R - p["bolt_inset"] - p["bolt"] / 2 - w
        lo = d["void_out"] + w
        if bolt_edge - lo > 4.0:
            box = (lo, bolt_edge, lo, bolt_edge)
            plate = plate.cut(_box(box, -1.0, p["b"] + 1.0))
            added["windows"].append({"y": [box[0], box[1]], "z": [box[2], box[3]]})
        tie_y, tie_z = p.get("wire_tie_pos", r["wire_tie_pos"])
        z_lo = tie_z + r["wire_tie"] / 2 + w                 # above the wire-tie hole
        z_hi = d["void_out"] - w
        y_hi = d["pocket1"] - w
        if y_hi - lo > 4.0 and z_hi - z_lo > 4.0:
            for leg in [leg for leg in DRIVEN if leg in p["legs"]]:
                box = rect_rot(leg, lo, y_hi, z_lo, z_hi)
                plate = plate.cut(_box(box, -1.0, p["b"] + 1.0))
                added["windows"].append({"y": [box[0], box[1]], "z": [box[2], box[3]]})

    # Corner lightening windows (only where a four-leg plate has its corner blocks).
    w0, w1 = r["window"]
    if p["windows"]:
        for sy in (-1, 1):
            for sz in (-1, 1):
                box = (min(sy * w0, sy * w1), max(sy * w0, sy * w1), min(sz * w0, sz * w1), max(sz * w0, sz * w1))
                plate = plate.cut(_box(box, -1.0, p["b"] + 1.0))
                added["windows"].append({"y": [box[0], box[1]], "z": [box[2], box[3]]})

    # Holder: two M2 tapped holes on the front face either side of the fiber.
    for s in (-1, 1):
        y = s * r["holder_tap_y"]
        plate = plate.cut(_cyl_through(y, 0.0, r["holder_tap"], p["b"] - r["holder_tap_depth"], p["b"] + 1.0))
        added["holder_taps"].append([y, 0.0])

    # Fiber hole chamfers, both faces.
    c = p["fiber_hole"] / 2 + 0.3
    plate = plate.edges(cq.selectors.BoxSelector((-0.1, -c, -c), (p["b"] + 0.1, c, c))).chamfer(r["fiber_chamfer"])
    return plate, added


def build_jig(p: dict, d: dict, per_leg: dict) -> cq.Workplane:
    """Assembly jig: a plate with 3 mm pockets that locate the platform (with its
    arms) and both input stages at nominal while the leaves are bonded, and
    dowel holes on the frame's bolt pattern to locate the frame around them.
    Pocket clearance 0.02 per side; the jig sits on the body's back face."""
    r = R02
    t = 8.0
    y0, y1, z0, z1 = d["box"]
    jig = cq.Workplane("XY").box(t, y1 - y0 + 10, z1 - z0 + 10, centered=False).translate((-t, y0 - 5, z0 - 5))
    c = 0.02
    depth = 3.0
    pockets = [(-p["a_p"] - c, p["a_p"] + c, -p["a_p"] - c, p["a_p"] + c)]
    for parts in per_leg.values():
        pockets += [(a[0] - c, a[1] + c, a[2] - c, a[3] + c) for a in parts["arms"]]
        s = parts["stage"]
        pockets.append((s[0] - c, s[1] + c, s[2] - c, s[3] + c))
    for rect in pockets:
        jig = jig.cut(_box(rect, -depth, 1.0))
    for y, z in bolt_points(p, d):
        jig = jig.cut(_cyl_through(y, z, p["bolt"] - 0.5, -t - 1.0, 1.0))   # press-fit dowel seats
    # A window under the fiber hole and the holder taps so nothing touches them.
    jig = jig.cut(_cyl_through(0.0, 0.0, 8.0, -t - 1.0, 1.0))
    return jig


def build_base(p: dict, d: dict) -> cq.Workplane:
    """Mount model: a plate of the same outline behind the flexure, with a central
    opening for the fiber loop and the four bolt holes; fixed at the bolts."""
    r = R02
    t = r["base_t"]
    y0, y1, z0, z1 = d["box"]
    base = cq.Workplane("XY").box(t, y1 - y0, z1 - z0, centered=False).translate((-t, y0, z0))
    # Opening: the moving region plus a margin, so the base touches frame only.
    iy0, iy1, iz0, iz1 = d["inner"]
    m = p.get("base_margin", r["base_margin"])
    base = base.cut(_box((iy0 - m, iy1 + m, iz0 - m, iz1 + m), -t - 1.0, 1.0))
    # Windows behind the actuator pockets: the APA leads leave through the back
    # face, and the actuator is 2 mm thicker than an 8 mm plate anyway.
    for leg in [leg for leg in DRIVEN if leg in p["legs"]]:
        y0, y1, z0, z1 = rect_rot(leg, d["pocket0"], d["pocket1"], -d["pocket_h"], d["pocket_h"])
        base = base.cut(_box((y0 - 1.5, y1 + 1.5, z0 - 1.5, z1 + 1.5), -t - 1.0, 1.0))
    for y, z in bolt_points(p, d):
        base = base.cut(_cyl_through(y, z, p["bolt"], -t - 1.0, 1.0))
    return base


def build(p: dict) -> tuple[cq.Workplane, cq.Workplane, dict]:
    d = derived(p)
    R = d["R"]
    y0, y1, z0, z1 = d["box"]
    driven = [leg for leg in DRIVEN if leg in p["legs"]]
    # The plate profile in the YZ plane: local sketch x = global Y, y = global Z.
    # Absolute polygon, not push().rect(): a pushed location leaks into every
    # later operation on the sketch and would shift all voids by the box centre.
    sk = cq.Sketch().polygon([(y0, z0), (y1, z0), (y1, z1), (y0, z1), (y0, z0)])
    per_leg = {}
    for leg in p["legs"]:
        rects = leg_rects(p, d)
        per_leg[leg] = {
            "voids": [rect_rot(leg, *r) for r in rects["voids"]],
            "stage": rect_rot(leg, *rects["stage"]),
            "leaves": [rect_rot(leg, *r) for r in rects["leaves"]],
            "notches": [rect_rot(leg, *r) for r in rects["notches"]],
            "bars": [rect_rot(leg, *r) for r in rects["bars"]],
            "roles": rects["roles"],
            "arms": [rect_rot(leg, *r) for r in rects["arms"]],
        }
    for leg in p["legs"]:
        for r in per_leg[leg]["voids"]:
            sk = _rect(sk, r, "s")
    # A side without a leg still needs the platform cut free of the wall: a
    # clearance slot from the platform edge to the wall's inner face.
    for leg in LEGS:
        if leg not in p["legs"]:
            sk = _rect(sk, rect_rot(leg, p["a_p"], p["h_in"] + p["g"], d["void_lo"], d["c0"]), "s")
    for leg in p["legs"]:
        sk = _rect(sk, per_leg[leg]["stage"], "a")
        for r in per_leg[leg]["arms"]:
            sk = _rect(sk, r, "a")
        if not p["shim"]:
            for r in per_leg[leg]["leaves"]:
                sk = _rect(sk, r, "a")
    if p["shim"]:
        # Ledges and bar notches come out of platform, stages and frame alike.
        for leg in p["legs"]:
            for r in per_leg[leg]["notches"]:
                sk = _rect(sk, r, "s")
    sk = sk.clean()
    sk = sk.reset().vertices().fillet(p["r_root"]).reset()

    plate = cq.Workplane("YZ").placeSketch(sk).extrude(p["b"])

    # Pad lands: on the driven input stages' outer faces and the opposing frame faces.
    x0 = (p["b"] - p["pad"][1]) / 2
    pads = {}
    for leg in driven:
        for side, y_face, direction in (("stage", d["y_in1"], +1), ("frame", d["pocket1"], -1)):
            y_a, y_b = sorted((y_face, y_face + direction * p["pad_boss"]))
            box = rect_rot(leg, y_a, y_b, -p["pad"][0] / 2, p["pad"][0] / 2)
            boss = (cq.Workplane("XY")
                    .box(p["pad"][1], box[1] - box[0], box[3] - box[2], centered=False)
                    .translate((x0, box[0], box[2])))
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
    holes = (cq.Workplane("YZ").pushPoints(bolt_points(p, d))
             .circle(p["bolt"] / 2).extrude(p["b"]))
    plate = plate.cut(holes)

    r02_added = None
    if p.get("r02"):
        plate, r02_added = add_r02(plate, p, d)

    # Shim leaves (steel) and their clamp bars (body material) as separate solids,
    # with the two M2 clamp screws per bar: clearance through the bar and the
    # tab, tapped 4 mm into the body. Screws run normal to the leaf plane.
    leaf_solids, bar_solids, screws = [], [], []
    if p["shim"]:
        for leg in p["legs"]:
            leaf_solids += [_box(r, 0.0, p["b"]) for r in per_leg[leg]["leaves"]]
            for r, role in zip(per_leg[leg]["bars"], per_leg[leg]["roles"]):
                bar = _box(r, 0.0, p["b"])
                # The bar's root edge (the X-parallel edge facing the free leaf)
                # is radiused so the leaf bends off a radius, not a corner; the
                # model chamfers all four long edges, which is what a shop does.
                try:
                    bar = bar.edges("|X").chamfer(p["bar_edge_r"])
                except Exception:
                    pass
                if p["bond_all"] or BAR_ACCESS[role] == "bond":
                    bar_solids.append(bar)               # bonded: no screws, no taps
                    continue
                y0, y1, z0, z1 = r
                along_z = (z1 - z0) <= (y1 - y0)          # thin in z: coupler bar, screws along Z
                # The body lies beyond the leaf: on the far side of the bar from the free leaf.
                for x in (p["b"] * 0.25, p["b"] * 0.75):
                    if along_z:
                        y, zc = (y0 + y1) / 2, (z0 + z1) / 2
                        # which side is the body? the ledge is under the leaf: pick the
                        # side whose point 1 mm beyond the bar+leaf is inside the plate
                        for s in (-1, 1):
                            probe = cq.Vector(x, y, zc + s * ((z1 - z0) / 2 + p["t"] + 1.0))
                            if plate.val().isInside(probe):
                                start = zc - s * (z1 - z0) / 2 - s * 0.01
                                depth = (z1 - z0) + p["t"] + 4.0
                                clear = cq.Solid.makeCylinder(1.1, (z1 - z0) + p["t"] + 0.02, cq.Vector(x, y, start), cq.Vector(0, 0, s))
                                tap = cq.Solid.makeCylinder(0.8, depth, cq.Vector(x, y, start), cq.Vector(0, 0, s))
                                bar = bar.cut(cq.Workplane("XY").add(clear))
                                plate = plate.cut(cq.Workplane("XY").add(tap))
                                screws.append({"x": x, "y": y, "z": zc, "axis": "z", "into": s,
                                               "role": role, "access": BAR_ACCESS[role]})
                                break
                    else:
                        z, yc = (z0 + z1) / 2, (y0 + y1) / 2
                        for s in (-1, 1):
                            probe = cq.Vector(x, yc + s * ((y1 - y0) / 2 + p["t"] + 1.0), z)
                            if plate.val().isInside(probe):
                                start = yc - s * (y1 - y0) / 2 - s * 0.01
                                depth = (y1 - y0) + p["t"] + 4.0
                                clear = cq.Solid.makeCylinder(1.1, (y1 - y0) + p["t"] + 0.02, cq.Vector(x, start, z), cq.Vector(0, s, 0))
                                tap = cq.Solid.makeCylinder(0.8, depth, cq.Vector(x, start, z), cq.Vector(0, s, 0))
                                bar = bar.cut(cq.Workplane("XY").add(clear))
                                plate = plate.cut(cq.Workplane("XY").add(tap))
                                screws.append({"x": x, "y": yc, "z": z, "axis": "y", "into": s,
                                               "role": role, "access": BAR_ACCESS[role]})
                                break
                bar_solids.append(bar)

    # Payload block on the front face, centred on the fiber.
    hy, hz = p["payload_wy"] / 2, p["payload_wz"] / 2
    payload = (cq.Workplane("XY")
               .box(p["payload_len"], p["payload_wy"], p["payload_wz"], centered=False)
               .translate((p["b"], -hy, -hz)))

    info = {"derived": d, "legs": per_leg, "pads": pads, "r02": r02_added,
            "leaf_solids": leaf_solids, "bar_solids": bar_solids, "screws": screws,
            "payload_box": {"x": [p["b"], p["b"] + p["payload_len"]],
                            "y": [-hy, hy], "z": [-hz, hz]}}
    return plate, payload, info


def apa_placeholder(p: dict, d: dict, leg: str) -> cq.Workplane:
    """Datasheet envelope of the actuator when no vendor STEP is on hand: the
    shell (apa_long across the leg, 8 mm along it, full thickness) between two
    2.5 x 5 pads that meet the lands. Placement only, not for analysis."""
    shell_len = 8.0                          # APA120S ICD: shell ~8 along the motion axis
    y_a, y_b = d["y_in1"] + p["pad_boss"], d["pocket1"] - p["pad_boss"]
    yc = (y_a + y_b) / 2
    x0 = (p["b"] - p["pad"][1]) / 2
    shell = _box(rect_rot(leg, yc - shell_len / 2, yc + shell_len / 2, -p["apa_long"] / 2, p["apa_long"] / 2),
                 (p["b"] - 10.0) / 2, (p["b"] + 10.0) / 2)
    pads = _box(rect_rot(leg, y_a, y_b, -p["pad"][0] / 2, p["pad"][0] / 2), x0, x0 + p["pad"][1])
    return shell.union(pads)


def place_apa(p: dict, d: dict, leg: str) -> cq.Workplane | None:
    """Vendor APA60S dropped into a driven leg's pocket, for the assembly STEP."""
    if not VENDOR.exists() or p["actuator"] != "APA60S":
        return apa_placeholder(p, d, leg)   # only the APA60S STEP is on hand
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

    body = P["body_material"] or {"name": "7075-T6 (Fusion 'Aluminum 7075' values, as fem_r01)",
                                  "E_MPa": P["E_MPa"], "nu": P["nu"], "rho_kg_m3": P["rho_kg_m3"]}
    # In shim mode the body is four pieces (frame, two stages, platform) held
    # together only by the leaves; treat it as a list of solids throughout.
    body_solids = plate.solids().vals()
    vol = sum(s.Volume() for s in body_solids)
    rho = body["rho_kg_m3"] * 1e-6                     # g/mm3
    plate_mass_g = vol * rho
    payload_vol = payload.val().Volume()
    payload_g = payload_vol * P["payload_rho_kg_m3"] * 1e-6
    leaf_rho = P["leaf_material"]["rho_kg_m3"] * 1e-6 if P["shim"] else rho
    leaves_g = sum(s.val().Volume() for s in info["leaf_solids"]) * leaf_rho
    bars_g = sum(s.val().Volume() for s in info["bar_solids"]) * rho

    # Moving-mass bookkeeping from the profile rectangles (leaves at half weight,
    # a beam's effective mass); the FE modal is the real answer.
    stage_mm2 = d["w_in"] * 2 * P["h_in"]
    leaf_mm2 = P["t"] * P["L"]
    platform_g = ((2 * P["a_p"]) ** 2 - 3.14159 * (P["fiber_hole"] / 2) ** 2) * P["b"] * rho
    stage_g = stage_mm2 * P["b"] * rho
    leaf_g = leaf_mm2 * P["b"] * leaf_rho
    moving_one_axis_g = platform_g + 2 * stage_g + 0.5 * (8 + 4) * leaf_g + P["apa_mass_g"] / 2

    # The "plate" STEP the FE meshes: the body plus its shim leaves as separate
    # solids (fragmented conformal by mesh.py); the assembly adds the clamp bars.
    plate_wp = cq.Workplane("XY").add(body_solids)
    for s in info["leaf_solids"]:
        plate_wp = plate_wp.add(s.val())
    cq.exporters.export(plate_wp, str(step_dir /"parallel_yz_r01.step"))
    loaded = cq.Workplane("XY").add(body_solids)
    for s in info["leaf_solids"]:
        loaded = loaded.add(s.val())
    loaded = loaded.add(payload.val())
    base_info = None
    if P.get("r02"):
        base = build_base(P, d)
        loaded = loaded.add(base.val())
        iy0, iy1, iz0, iz1 = d["inner"]
        margin = P.get("base_margin", R02["base_margin"])
        base_info = {
            "t": R02["base_t"],
            "opening_mm": [iy1 - iy0 + 2 * margin, iz1 - iz0 + 2 * margin],
            "mass_g": base.val().Volume() * rho,
            "material": "same elastic constants as the plate (aluminium)",
        }
        fixture_mounted = {
            "x": -R02["base_t"], "radius": R02["bolt_washer_r"],
            "points": [list(pt) for pt in bolt_points(P, d)],
            "rule": "base back-face facets within radius of a bolt centre are fixed (washer footprint)",
        }
        # The EDM profile for the shop: the back face carries every through-cut
        # and nothing else (the pad lands and the holder taps are milling ops).
        cq.exporters.exportDXF(plate.faces("<X"), str(step_dir / "parallel_yz_r02_profile.dxf"))
    cq.exporters.export(loaded, str(step_dir /"parallel_yz_r01_loaded.step"))

    # What the wire has to do: every inner wire of the back face is a threaded
    # contour; their lengths plus the outer wire are the cut path. The design
    # rule from 2026-09-08 is to minimise these, so they are reported every build.
    back = plate.faces("<X")
    wires = back.wires().vals()
    edm = {"closed_contours_to_thread": len(wires) - len(body_solids),
           "body_pieces": len(body_solids),
           "cut_length_mm": sum(w.Length() for w in wires),
           "leaves": len(leaf_boxes := [None] * 0) or sum(len(v["leaves"]) for v in info["legs"].values())}

    assembly = cq.Workplane("XY").add(body_solids)
    for s in info["leaf_solids"] + info["bar_solids"]:
        assembly = assembly.add(s.val())
    for leg in [leg for leg in DRIVEN if leg in P["legs"]]:
        apa = place_apa(P, d, leg)
        if apa is not None:
            assembly = assembly.add(apa.val())
    cq.exporters.export(assembly, str(step_dir /"parallel_yz_r01_assembly.step"))
    if P["shim"] and P["bond_all"]:
        jig = build_jig(P, d, info["legs"])
        cq.exporters.export(jig, str(step_dir / "assembly_jig.step"))

    leaf_boxes = []
    for leg, parts in info["legs"].items():
        for (y0, y1, z0, z1) in parts["leaves"]:
            leaf_boxes.append({"x": [0.0, P["b"]], "y": [y0, y1], "z": [z0, z1], "leg": leg})
    stage_boxes = {leg: {"x": [0.0, P["b"]], "y": [r[0], r[1]], "z": [r[2], r[3]]}
                   for leg, r in ((leg, parts["stage"]) for leg, parts in info["legs"].items())}

    report = {
        "concept": f"parallel-kinematic YZ platform, {len(P['legs'])} P-P legs, two {P['actuator']} grounded to the frame",
        "variant": args.variant or "R01 baseline",
        "frame": "X optical (plate thickness, +X toward the die), Y lateral, Z up; mm",
        "parameters": P,
        "derived": d,
        "plate_mm": [P["b"], d["box"][1] - d["box"][0], d["box"][3] - d["box"][2]],
        "edm": edm,
        "plate_volume_mm3": vol,
        "plate_mass_g": plate_mass_g,
        "mass_estimates_g": {
            "platform": platform_g, "input_stage": stage_g, "leaf": leaf_g,
            "moving_per_axis_incl_half_apa": moving_one_axis_g,
            "note": "profile-rectangle estimates; the FE modal carries the real mass",
        },
        "material": body,
        # Regions with a material other than the body's: the shim leaves. The
        # holder is handled separately (loaded meshes only).
        "material_regions": [
            {"box": {"x": [0.0, P["b"]], "y": [y0, y1], "z": [z0, z1]}, **P["leaf_material"]}
            for parts in info["legs"].values() for (y0, y1, z0, z1) in parts["leaves"]
        ] if P["shim"] else [],
        "shim": {"enabled": P["shim"], "tab": P["tab"], "bar_t": P["bar_t"], "leaf_t": P["t"],
                 "free_length": P["L"], "leaf_depth": P["b"], "leaves_g": leaves_g, "bars_g": bars_g,
                 "bars": [{"y": [r[0], r[1]], "z": [r[2], r[3]], "leg": leg, "role": role,
                           "access": BAR_ACCESS[role]}
                          for leg, parts in info["legs"].items()
                          for r, role in zip(parts["bars"], parts["roles"])],
                 "arm": d["arm"],
                 "clamp": "2 x M2 per bar, bar edge R0.3 defines the root; 32 taps side-drilled",
                 "screws": info["screws"]}
                if P["shim"] else {"enabled": False},
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
                    "outside_box": list(d["inner"]),
                    "rule": "back-face facets outside the inner box (y0, y1, z0, z1) are fixed"},
        "outputs": ["STEP/parallel_yz_r01.step", "STEP/parallel_yz_r01_loaded.step",
                    "STEP/parallel_yz_r01_assembly.step"],
    }
    if P.get("r02"):
        report["r02"] = {**R02, **info["r02"]}
        report["base"] = base_info
        report["fixture_mounted"] = fixture_mounted
        report["refine_boxes"] = info["r02"]["stops"]
        report["outputs"].append("STEP/parallel_yz_r02_profile.dxf")
    (root / "geometry_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"[{report['variant']}] {P['actuator']}, leaves {P['t']} mm -> {root}")
    print(f"plate {P['b']:.0f} x {report['plate_mm'][1]:.1f} x {report['plate_mm'][2]:.1f} mm, "
          f"{vol:.0f} mm3, {plate_mass_g:.1f} g; moving per axis ~{moving_one_axis_g:.1f} g")
    print(f"EDM: {edm['leaves']} leaves, {edm['closed_contours_to_thread']} contours to thread, "
          f"{edm['cut_length_mm'] / 1000:.2f} m of cut")
    if P["shim"]:
        print(f"shim leaves: {len(info['leaf_solids'])} x {P['leaf_material']['name']} "
              f"{P['t']:.2f} x {P['b']:.0f} x {P['L'] + 2 * P['tab']:.1f} ({leaves_g:.1f} g), "
              f"{len(info['bar_solids'])} clamp bars ({bars_g:.1f} g); stage width {d['w_in']:.1f}")
    print(f"payload block {payload_vol:.0f} mm3 at {P['payload_rho_kg_m3']:.0f} kg/m3 = {payload_g:.2f} g")
    if base_info:
        print(f"base plate {base_info['mass_g']:.0f} g, opening "
              f"{base_info['opening_mm'][0]:.0f} x {base_info['opening_mm'][1]:.0f} mm; "
              f"loaded STEP fixed at the four bolts")
    print("wrote", ", ".join(report["outputs"]), "and geometry_report.json")
    return 0


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    # OCP's interpreter teardown segfaults on this machine (see ../README.md);
    # everything is written and flushed, so leave without running it.
    os._exit(code)

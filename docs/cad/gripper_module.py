"""
Parametric CAD for the end-face die gripper module.

Generates STEP/STL for the custom parts and a STEP assembly that includes a
dimensionally faithful stand-in for the SMC MHZ2-6D actuator (from the SMC
catalog drawing), the 10 x 6 x 0.5 mm die and the nest rails, so clearances can
be checked in any CAD package.

Frame (same as the concept study and the 3-D viewer):
    X = die long axis (10 mm), gripper stroke direction, +X toward the far end face
    Y = die optical axis (6 mm), fibers approach along +/-Y
    Z = up; Z = 0 is the die's BOTTOM face when the die is gripped at the nest.

Run:  python docs/cad/gripper_module.py        -> writes docs/cad/out/
Needs: pip install cadquery
"""
from __future__ import annotations

import math
import os
import cadquery as cq
from cadquery import exporters

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# Parameters (mm, N)
# ----------------------------------------------------------------------------
P = dict(
    # die
    die_len=10.0, die_wid=6.0, die_thk=0.5, die_len_tol=0.025,
    # contact geometry (concept study Fig. 3)
    nose_h=0.35,          # contact band height on the end face
    nose_gap_top=0.10,    # nose top below die top surface
    nose_setback=0.60,    # tip block face set back above the nose
    nose_w=3.0,           # contact width along Y (die middle 3 mm)
    nose_y0=1.5,          # contact band from Y=1.5 to 4.5
    # arm bars: only these pass under the objective
    arm_h=5.0,            # bar underside above die top
    bar_h=3.0, bar_w=3.0, # bar cross-section (Z, Y)
    bar_gap=0.5,          # Y gap between the two bars where they run side by side
    # flexure (0.005" feeler gauge stock, spring steel)
    blade_t=0.127, blade_w=3.0, blade_free=5.0, blade_clamp=3.0, blade_in_block=1.0,
    grip_preload=0.13,    # blade deflection with a nominal die -> ~0.30 N
    E_steel=200e9,
    # MHZ2-6D (SMC catalog "Dimensions MHZ2-6", basic type)
    act_body_x=20.0, act_body_y=10.0, act_body_z=38.8,
    act_fing_x=4.0, act_fing_y=4.0, act_fing_len=14.2,
    act_closed_outer=16.0, act_open_outer=20.0,    # finger OUTER faces: SMC's "8 closed / 12 open" is the gap between the
                                                   # finger inner faces (fingers 4 thick at +/-4..8 closed, +/-6..10 open; from the vendor STEP)
    act_m2_from_tip=(2.5, 7.5),                      # attachment threads, on finger outer face
    act_m3_from_front=13.3, act_m3_pitch=12.0,       # body through-holes along Y
    act_port_from_rear=(5.5, 22.5), act_port_offset=1.6,
    # placement
    body_cx=-30.0,        # actuator centre X (body -40..-20; objective barrel to X -12, tube to X -15)
    finger_tip_z=None,    # computed: bars top + 2.5
    # root plates / heads
    root_t=3.0,           # plate thickness bolted to the finger outer face
    head_x=4.0,           # head length along X at the bar end
    # mounting interface
    iface_pitch=25.0, iface_screw="M4", bracket_t=3.0, top_t=6.0,
    # sensor provision
    fiber_hole_d=0.6,
)

die_top = P["die_thk"]
bar_z0 = die_top + P["arm_h"]                # bar underside
bar_z1 = bar_z0 + P["bar_h"]                 # bar top
P["finger_tip_z"] = bar_z1 + 2.5
tip_z = P["finger_tip_z"]
body_z0 = tip_z + P["act_fing_len"]          # actuator body bottom
body_z1 = body_z0 + P["act_body_z"]
cx = P["body_cx"]
die_cy = P["die_wid"] / 2.0                  # 3.0

# nominal nose faces when fingers are fully closed (hard stop): gap = die_len - preload
gap_closed = P["die_len"] - P["grip_preload"]
near_face_x = die_cy * 0 + (P["die_len"] - gap_closed) / 2.0     # +0.065
far_face_x = P["die_len"] - (P["die_len"] - gap_closed) / 2.0    # 9.935

# finger positions (closed): inner faces touch at body centre
near_fing_x0 = cx - P["act_closed_outer"] / 2                      # -38 (closed)
near_fing_x1 = near_fing_x0 + P["act_fing_x"]                       # -34
far_fing_x1 = cx + P["act_closed_outer"] / 2                        # -22
far_fing_x0 = far_fing_x1 - P["act_fing_x"]                         # -26
fing_y0, fing_y1 = die_cy - P["act_fing_y"] / 2, die_cy + P["act_fing_y"] / 2   # 1..5

# bar Y lanes: near bar low-Y, far bar high-Y, contact blocks centred on die middle
blk_y0, blk_y1 = P["nose_y0"], P["nose_y0"] + P["nose_w"]  # 1.5..4.5  (contact band, tip blocks, heads)
# bars run in lanes outside the head band so the two arms never collide when they move relative to each other
near_bar_y1 = blk_y0 - 0.3                               # 1.2
near_bar_y0 = near_bar_y1 - P["bar_w"]                   # -1.8
far_bar_y0 = blk_y1 + 0.3                                # 4.8
far_bar_y1 = far_bar_y0 + P["bar_w"]                     # 7.8
blade_plane_off = 1.8                                    # blade plane behind the near nose face


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def flexure_k():
    E, b, t, L = P["E_steel"], P["blade_w"] * 1e-3, P["blade_t"] * 1e-3, P["blade_free"] * 1e-3
    return E * b * t ** 3 / (4 * L ** 3)  # N/m, cantilever end load


# ----------------------------------------------------------------------------
# Bought part stand-in: MHZ2-6D body + fingers (closed position)
# ----------------------------------------------------------------------------
def actuator(open_mm=0.0):
    body = box(cx - P["act_body_x"] / 2, cx + P["act_body_x"] / 2,
               die_cy - P["act_body_y"] / 2, die_cy + P["act_body_y"] / 2, body_z0, body_z1)
    # M3 through-holes along Y (body mounting), 12 apart, 13.3 from the finger face
    zh = body_z0 + P["act_m3_from_front"]
    for dx in (-P["act_m3_pitch"] / 2, P["act_m3_pitch"] / 2):
        body = body.cut(cq.Workplane("XZ").center(cx + dx, zh).circle(1.3).extrude(-40).translate((0, -10, 0)))
    # ports on the +Y face (M3), and pilot hole on the top face
    for zr in P["act_port_from_rear"]:
        body = body.cut(cq.Workplane("XZ").center(cx + P["act_port_offset"], body_z1 - zr).circle(1.25).extrude(-3)
                        .translate((0, die_cy + P["act_body_y"] / 2 + 0.01, 0)))
    body = body.cut(cq.Workplane("XY").center(cx, die_cy).circle(3.5).extrude(-1.5).translate((0, 0, body_z1)))
    near = box(near_fing_x0 - open_mm, near_fing_x1 - open_mm, fing_y0, fing_y1, tip_z, body_z0)
    far = box(far_fing_x0 + open_mm, far_fing_x1 + open_mm, fing_y0, fing_y1, tip_z, body_z0)
    # M2 attachment holes on the outer faces (axis X)
    for z in P["act_m2_from_tip"]:
        near = near.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.0).extrude(6).translate((near_fing_x0 - open_mm - 1, 0, 0)))
        far = far.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.0).extrude(6).translate((far_fing_x1 + open_mm - 5, 0, 0)))
    return body, near, far


def actuator_vendor(open_mm=0.0, path=None):
    """SMC MHZ2-6D from the vendor STEP (docs/cad/vendor/smc_MHZ2-6D.step), in the gripper frame with the
    fingers pointing down and set to closed + open_mm. File frame: body 10 (x) x 20 (y) x 38.8 (z -30..8.8),
    fingers +z to 23, drawn OPEN (uprights at y 6..10 / -10..-6). Returns (body, near_finger, far_finger) or None."""
    import os
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor", "smc_MHZ2-6D.step")
    if not os.path.exists(path):
        return None
    wp = cq.importers.importStep(path)
    sol = sorted(wp.solids().vals(), key=lambda t: -t.Volume())
    body, f_a, f_b = sol[0], sol[1], sol[2]
    if f_a.BoundingBox().ymin > 0:
        f_pos, f_neg = f_a, f_b
    else:
        f_pos, f_neg = f_b, f_a
    shift = 2.0 - open_mm                                              # open -> closed is 2 mm inward per finger
    f_pos = f_pos.translate(cq.Vector(0, -shift, 0)); f_neg = f_neg.translate(cq.Vector(0, shift, 0))

    def to_frame(t):                                                   # file (x, y, z) -> gripper (y, x, -z), then place
        w = cq.Workplane().add(t).rotate((0, 0, 0), (1, 0, 0), 180).rotate((0, 0, 0), (0, 0, 1), 90)
        return w.translate((cx, die_cy, body_z0 + 8.8))                # file z = 8.8 (body top) -> Z body_z0
    return to_frame(body), to_frame(f_neg), to_frame(f_pos)            # file -y finger -> -X (near), +y -> +X (far)


# ----------------------------------------------------------------------------
# Custom part 1: FAR arm (rigid). Root plate on the far finger's outer (+X) face,
# bar along +X in the high-Y lane, head at the far end carrying the rigid tip block.
# ----------------------------------------------------------------------------
def far_arm():
    rt = P["root_t"]
    root_x0, root_x1 = far_fing_x1, far_fing_x1 + rt                 # -22..-19
    root = box(root_x0, root_x1, fing_y0, fing_y1, tip_z - 1.0, tip_z + 10.0)
    # M2 clearance holes (2.2) with counterbore for the screw heads (3.8 x 2 deep)
    for z in P["act_m2_from_tip"]:
        root = root.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.1).extrude(rt + 2).translate((root_x0 - 1, 0, 0)))
        root = root.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.9).extrude(2.0).translate((root_x1 - 2.0, 0, 0)))
    # transition block under the root plate (full width from finger Y to the far lane), then the drop in the lane
    trans = box(root_x0, root_x1, fing_y0, far_bar_y1, bar_z1 + 0.5, tip_z - 1.0)
    drop = box(root_x0, root_x1, far_bar_y0, far_bar_y1, bar_z0, bar_z1 + 0.5).union(trans)
    # bar to the head
    head_x0 = far_face_x + 2.0                                        # tip block is 2.0 thick: 9.935..11.935
    head_x1 = head_x0 + P["head_x"]                                   # 11.935..15.935
    bar = box(root_x0, head_x1, far_bar_y0, far_bar_y1, bar_z0, bar_z1)
    # head: full 3 mm wide block centred on the die middle, carries the tip block on its -X face
    head = box(head_x0, head_x1, blk_y0, blk_y1, bar_z0, bar_z1)
    # M2 tapped hole along X for the tip block screw
    head = head.cut(cq.Workplane("YZ").center(die_cy, bar_z0 + 1.5).circle(0.8).extrude(P["head_x"] + 0.2).translate((head_x0 - 0.1, 0, 0)))
    return root.union(drop).union(bar).union(head)


# ----------------------------------------------------------------------------
# Custom part 2: NEAR arm (compliant). Root plate on the near finger's outer (-X) face,
# bar along +X in the low-Y lane, raised head with a slot that clamps the flexure blade.
# ----------------------------------------------------------------------------
def near_arm():
    rt = P["root_t"]
    root_x0, root_x1 = near_fing_x0 - rt, near_fing_x0               # -33..-30
    root = box(root_x0, root_x1, fing_y0, fing_y1, tip_z - 1.0, tip_z + 10.0)
    for z in P["act_m2_from_tip"]:
        root = root.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.1).extrude(rt + 2).translate((root_x0 - 1, 0, 0)))
        root = root.cut(cq.Workplane("YZ").center(die_cy, tip_z + z).circle(1.9).extrude(2.0).translate((root_x0, 0, 0)))
    trans = box(root_x0, root_x1, near_bar_y0, fing_y1, bar_z1 + 0.5, tip_z - 1.0)
    drop = box(root_x0, root_x1, near_bar_y0, near_bar_y1, bar_z0, bar_z1 + 0.5).union(trans)
    # bar runs under the far finger tip toward the die; head straddles the blade plane
    blade_plane = near_face_x - blade_plane_off                        # -1.735
    head_x1 = blade_plane + 1.0                                        # 1 mm wall on the +X side of the slot
    head_x0 = head_x1 - P["head_x"] - 1.0                              # -6.7..-0.7
    bar = box(root_x0, head_x1, near_bar_y0, near_bar_y1, bar_z0, bar_z1)
    # raised head so the blade has its free length: head bottom = block top + free length
    blk_top = P["nose_h"] + 0.05 + (P["nose_h"] + 1.1)                # near block top (see near_tip_block): 0.05..1.5
    head_z0 = 1.5 + P["blade_free"]                                   # 6.5
    head_z1 = head_z0 + P["bar_h"]                                    # 9.5  (max height under objective)
    head = box(head_x0, head_x1, blk_y0, blk_y1, head_z0, head_z1)
    # blade slot (blade_t + 0.05) x (blade_w + 0.1) x blade_clamp deep, on the head's -X? no: blade hangs
    # from the head bottom at X = -2 - 0.6 (behind the tip block face)
    slot_x = blade_plane
    slot = box(slot_x - (P["blade_t"] + 0.05) / 2, slot_x + (P["blade_t"] + 0.05) / 2,
               die_cy - (P["blade_w"] + 0.1) / 2, die_cy + (P["blade_w"] + 0.1) / 2,
               head_z0 - 0.01, head_z0 + P["blade_clamp"])
    head = head.cut(slot)
    # M2 clamp screw along X through the head into the slot (pinches the blade)
    head = head.cut(cq.Workplane("YZ").center(die_cy, head_z0 + 1.5).circle(0.8).extrude(P["head_x"] + 0.2).translate((head_x0 - 0.1, 0, 0)))
    # join bar to raised head with a riser
    riser = box(head_x0, head_x1, near_bar_y0, near_bar_y1, bar_z0, head_z1)
    return root.union(drop).union(bar).union(riser).union(head)


# ----------------------------------------------------------------------------
# Custom part 3a: FAR tip block (Semitron ESd 480), rigid, screwed to the far head.
# Face toward the die at X = far_face_x; nose band Z 0.05..0.40 protrudes 0.6 toward the die.
# ----------------------------------------------------------------------------
def far_tip_block():
    x_face = far_face_x
    blk = box(x_face + P["nose_setback"], x_face + 2.0, blk_y0, blk_y1, 0.05, bar_z1 + 0.05)
    nose = box(x_face, x_face + P["nose_setback"] + 0.01, blk_y0, blk_y1, 0.05, 0.05 + P["nose_h"])
    blk = blk.union(nose)
    # M2 clearance + countersink from the die side (head sits 6.5 mm above the die top)
    blk = blk.cut(cq.Workplane("YZ").center(die_cy, bar_z0 + 1.5).circle(1.1).extrude(3).translate((x_face - 0.5, 0, 0)))
    blk = blk.cut(cq.Workplane("YZ").center(die_cy, bar_z0 + 1.5).circle(2.0).extrude(1.2).translate((x_face + P["nose_setback"] - 0.01, 0, 0)))
    # fiber-sensor provision: 0.6 hole along X at mid die thickness
    blk = blk.cut(cq.Workplane("YZ").center(die_cy, P["die_thk"] / 2).circle(P["fiber_hole_d"] / 2).extrude(4).translate((x_face - 1, 0, 0)))
    return blk


# ----------------------------------------------------------------------------
# Custom part 3b: NEAR tip block (Semitron ESd 480), short, bonded to the blade's lower end.
# ----------------------------------------------------------------------------
def near_tip_block():
    x_face = near_face_x
    top = 1.5
    blk = box(x_face - 2.0, x_face - P["nose_setback"], blk_y0, blk_y1, 0.05, top)
    nose = box(x_face - P["nose_setback"] - 0.01, x_face, blk_y0, blk_y1, 0.05, 0.05 + P["nose_h"])
    blk = blk.union(nose)
    # blade slot from the top, at the blade plane (1.8 behind the nose face)
    slot_x = x_face - blade_plane_off
    blk = blk.cut(box(slot_x - (P["blade_t"] + 0.03) / 2, slot_x + (P["blade_t"] + 0.03) / 2,
                      die_cy - (P["blade_w"] + 0.05) / 2, die_cy + (P["blade_w"] + 0.05) / 2,
                      top - P["blade_in_block"], top + 0.01))
    blk = blk.cut(cq.Workplane("YZ").center(die_cy, P["die_thk"] / 2).circle(P["fiber_hole_d"] / 2).extrude(4).translate((x_face - 3, 0, 0)))
    return blk


# ----------------------------------------------------------------------------
# Custom part 4: flexure blade (0.005" feeler-gauge stock)
# ----------------------------------------------------------------------------
def blade():
    x_face = near_face_x
    slot_x = x_face - blade_plane_off
    z0 = 1.5 - P["blade_in_block"]
    z1 = 1.5 + P["blade_free"] + P["blade_clamp"]
    return box(slot_x - P["blade_t"] / 2, slot_x + P["blade_t"] / 2,
               die_cy - P["blade_w"] / 2, die_cy + P["blade_w"] / 2, z0, z1)


# ----------------------------------------------------------------------------
# Custom part 5: mounting bracket (L): vertical plate on the actuator's -Y face
# (2 x M3 through the body), horizontal top plate with the 25 x 25 mm M4 interface + 2 dowels.
# ----------------------------------------------------------------------------
def bracket():
    bt, tt = P["bracket_t"], P["top_t"]
    y_face = die_cy - P["act_body_y"] / 2           # -2.0 (body -Y face)
    vp = box(cx - 14, cx + 8, y_face - bt, y_face, body_z0 + 6, body_z1 + tt)          # stays at X <= cx+8 = -22
    zh = body_z0 + P["act_m3_from_front"]
    for dx in (-P["act_m3_pitch"] / 2, P["act_m3_pitch"] / 2):
        vp = vp.cut(cq.Workplane("XZ").center(cx + dx, zh).circle(1.7).extrude(-bt - 1).translate((0, y_face - bt - 0.5, 0)))
    # top plate: X cx-24 .. cx+8 (never past X = -22, i.e. 7 mm clear of a dia-40 microscope tube); pattern centred at cx-8
    tp = box(cx - 24, cx + 8, die_cy - 17, die_cy + 17, body_z1, body_z1 + tt)
    pitch = P["iface_pitch"]; pcx = cx - 8
    for dx in (-pitch / 2, pitch / 2):
        for dy in (-pitch / 2, pitch / 2):
            tp = tp.cut(cq.Workplane("XY").center(pcx + dx, die_cy + dy).circle(2.25).extrude(tt + 1).translate((0, 0, body_z1 - 0.5)))
    for dx in (-pitch / 2, pitch / 2):     # 3 mm dowel holes on the X axis
        tp = tp.cut(cq.Workplane("XY").center(pcx + dx, die_cy).circle(1.5).extrude(tt + 1).translate((0, 0, body_z1 - 0.5)))
    return vp.union(tp)


# ----------------------------------------------------------------------------
# Context: die on nest rails, objective keep-out
# ----------------------------------------------------------------------------
def die():
    return box(0, P["die_len"], 0, P["die_wid"], 0, P["die_thk"])


def rails():
    r1 = box(0, P["die_len"], 1.0, 1.9, -1.5, 0)
    r2 = box(0, P["die_len"], 4.1, 5.0, -1.5, 0)
    deck = box(-4, 14, 0.6, 5.4, -4.5, -1.5)
    return r1.union(r2).union(deck)


def keepout(wd=20.0):
    return cq.Workplane("XY").center(5, die_cy).circle(17).extrude(wd).translate((0, 0, die_top))


# ----------------------------------------------------------------------------
# Build, check, export
# ----------------------------------------------------------------------------
def main():
    parts = {
        "far_arm_6061": far_arm(),
        "near_arm_6061": near_arm(),
        "far_tip_block_semitron": far_tip_block(),
        "near_tip_block_semitron": near_tip_block(),
        "flexure_blade_0p127_steel": blade(),
        "bracket_6061": bracket(),
    }
    body, fn, ff = actuator(0.0)
    ctx = {"mhz2_6d_body": body, "mhz2_6d_finger_near": fn, "mhz2_6d_finger_far": ff,
           "die_10x6x0p5": die(), "nest_rails": rails()}

    # ---- numeric checks ----
    k = flexure_k()
    F = k * P["grip_preload"] * 1e-3
    Ftol = k * P["die_len_tol"] * 1e-3
    # highest custom-part point inside the objective footprint (|X-5|<=17, |Y-3|<=17)
    def zmax_in_footprint(shape):
        bb = shape.val().BoundingBox()
        return bb.zmax
    near_head_top = 1.5 + P["blade_free"] + P["bar_h"]
    report = [
        f"closed nose gap            : {gap_closed:.3f} mm (die {P['die_len']:.3f} -> blade preload {P['grip_preload']:.3f} mm)",
        f"open nose gap              : {gap_closed + 2 * (P['act_open_outer'] - P['act_closed_outer']) / 2:.2f} mm (2.0 mm per side)",
        f"flexure stiffness          : {k / 1000:.2f} N/mm  (t={P['blade_t']} mm, w={P['blade_w']} mm, L={P['blade_free']} mm)",
        f"grip force                 : {F:.2f} N  +/- {Ftol:.2f} N for die length +/- {P['die_len_tol']} mm",
        f"nose top below die top     : {P['die_thk'] - (0.05 + P['nose_h']):.3f} mm",
        f"far bar top above die top  : {bar_z1 - die_top:.2f} mm  (far bar lane Y {far_bar_y0:.1f}..{far_bar_y1:.1f}, near lane Y {near_bar_y0:.1f}..{near_bar_y1:.1f})",
        f"near head X extent         : {near_face_x - blade_plane_off - P['head_x'] :.2f} .. {near_face_x - blade_plane_off + 1.0:.2f}",
        f"near head top above die top: {near_head_top - die_top:.2f} mm  <- tallest tool part inside objective footprint",
        f"actuator body X extent     : {cx - P['act_body_x']/2:.1f} .. {cx + P['act_body_x']/2:.1f} (objective barrel -12..22, tube -15..25)",
        f"bracket/interface X extent : {cx - 24:.1f} .. {cx + 8:.1f}  (pattern centre X {cx - 8:.1f}, Y {die_cy:.1f})",
        f"module height above die top: {body_z1 + P['top_t'] - die_top:.1f} mm (to interface plate top)",
        f"body Y extent              : {die_cy - P['act_body_y']/2:.1f} .. {die_cy + P['act_body_y']/2:.1f}  (fiber clamps at Y <= -12 and >= 18)",
    ]
    print("\n".join(report))
    with open(os.path.join(OUT, "gripper_checks.txt"), "w") as f:
        f.write("\n".join(report) + "\n")

    # ---- exports ----
    for name, shape in parts.items():
        exporters.export(shape, os.path.join(OUT, f"{name}.step"))
        exporters.export(shape, os.path.join(OUT, f"{name}.stl"), tolerance=0.01, angularTolerance=0.1)
    assy = cq.Assembly(name="gripper_module")
    colors = {
        "far_arm_6061": (0.55, 0.58, 0.62), "near_arm_6061": (0.45, 0.48, 0.52),
        "far_tip_block_semitron": (0.15, 0.15, 0.15), "near_tip_block_semitron": (0.15, 0.15, 0.15),
        "flexure_blade_0p127_steel": (0.85, 0.70, 0.25), "bracket_6061": (0.60, 0.65, 0.72),
        "mhz2_6d_body": (0.80, 0.80, 0.82), "mhz2_6d_finger_near": (0.7, 0.7, 0.72), "mhz2_6d_finger_far": (0.7, 0.7, 0.72),
        "die_10x6x0p5": (0.81, 0.89, 0.97), "nest_rails": (0.56, 0.56, 0.56),
    }
    for name, shape in {**parts, **ctx}.items():
        c = colors[name]
        assy.add(shape, name=name, color=cq.Color(c[0], c[1], c[2], 1.0))
    assy.add(keepout(), name="objective_keepout_wd20", color=cq.Color(0.85, 0.64, 0.25, 0.25))
    assy.save(os.path.join(OUT, "gripper_module_assembly.step"))

    # ---- 2-D views (SVG) of the assembly without the keep-out ----
    comp = cq.Compound.makeCompound([s.val() for s in {**parts, **ctx}.values()])
    # The SVG exporter's up-vector is not controllable, so rotate the model into the image plane and
    # always project along -Z: image x = model X (or Y), image up = model Z.
    def rotated(rx, ry, rz):
        c = comp
        if rz: c = c.rotate((0, 0, 0), (0, 0, 1), rz)
        if rx: c = c.rotate((0, 0, 0), (1, 0, 0), rx)
        if ry: c = c.rotate((0, 0, 0), (0, 1, 0), ry)
        return c
    views = {
        "front_alongY": rotated(-90, 0, 0),        # look along +Y: X right, Z up
        "side_alongX": rotated(-90, 0, 90),        # look along -X: Y right, Z up
        "top": comp,                               # look down -Z: X right, Y up
        "iso": rotated(-60, 0, -35),               # 30 deg elevation, 35 deg azimuth
    }
    for vname, c in views.items():
        exporters.export(cq.Workplane().add(c), os.path.join(OUT, f"view_{vname}.svg"),
                         opt={"width": 1200, "height": 800, "marginLeft": 20, "marginTop": 20,
                              "showAxes": False, "projectionDir": (0, 0, 1), "strokeWidth": 0.4,
                              "strokeColor": (30, 30, 30), "hiddenColor": (180, 180, 190), "showHidden": False})
    print("wrote", OUT)


if __name__ == "__main__":
    main()

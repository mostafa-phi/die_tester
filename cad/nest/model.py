"""
Self-registering, temperature-controlled nest ("chip stage") for the die tester.

The die is set down by the end-face gripper onto a lapped copper vacuum chuck pad and then
pushed, by the gripper's own compliant nose, against two hard-stop pads on its +X end face.
The stop pads fix X and yaw mechanically; the chuck pad fixes Z, pitch and roll; Y is left
free (the fiber stages approach along Y and measure the gap anyway) but is caged to
+/-0.6 mm by four corner blocks that never touch the die in normal operation.

Fiber access: the fiber tips protrude only ~5 mm from their holders, so the holder bodies
come to Y -5 and Y +11 (facets at Y 0 and 6). Nothing of the nest may be in that space:
the nest is a 10 mm wide neck (Y -2..8) down to below the holders' underside, and only
widens (for the TEC and the mounting) further down. Nothing ever stands in front of a
facet where a fiber can go (X 1..9); nothing touches the top surface.

Thermal: the chuck pad is the top of a copper block (Ni-plated) whose neck passes through
the riser to a 15 x 15 mm TEC in the riser's wide section; the aluminium riser is the hot-
side heat sink. Vacuum reaches the pad through 6 holes and a plenum in the copper block,
exiting as a stub tube on the -X side; a thermistor bore enters from +X.

Die stage (the nest moves): the devices span ~8 mm along X but the fiber stages only travel
4 mm, so the die is stepped from device to device by a Suruga KXC04015-C X stage under the
nest (15 mm travel, DS102-driven, 1 um half step), exactly as the current tester does with its
centre stage. A MISUMI RMPG40W-N motorized worm-gear rotary stage (40 mm class, horizontal table,
5-phase stepper on the DS102's second axis) sits UNDER the X stage so one rotation aligns both the
stop-pad datum and the stage travel to the fiber-stage axes; it is set with a gauge die and can
re-trim yaw per die if open-loop device stepping is wanted. The stack from the table up: KB1X1
kinematic base, 5 mm adapter, RMPG40W-N (35 tall), 3 mm adapter, KXC04015-C (30), riser, cage/chuck.
Both motors point -X (the only free direction: +X is the microscope column, +/-Y the fiber stages);
the rotary's body is longer on its motor side, which is turned toward -Y. The stack needs 100 mm
under the die, so the fiber stages and the Y stage sit on 25 mm risers (common.NANOMAX_RISER) and
the table plane is at Z -111. The gripper meets the nest only at the stage HOME position; the
exchange sequence homes the stage first and the fence enforces it.

Frame, die and contact rules: cad/common (X die long axis, Y optical axis, Z up, die bottom at the nest = 0).
The gripper parts used for the checks come from cad/gripper.

Outputs (this folder):
  STEP/nest_chuck_copper.step (+STL/)   C101 copper, Ni plated, pad lapped flat <= 3 um; 6 x dia 0.5 vacuum holes
  STEP/nest_cage_semitron.step (+STL/)  Semitron ESd 480 frame: 4 corner blocks (X stop pads, X guard, Y guards)
  STEP/nest_riser_6061.step             T-shaped riser / heat sink: 10 mm neck, TEC pocket, on the KXC04015 table
  STEP/nest_adapter_kb_rpg.step         adapter plate KB1X1 -> RMPG40W-N base   (6061, 5 mm, 4 x M3 tapped on 32 sq)
  STEP/nest_adapter_rpg_kxc.step        adapter plate RMPG40W-N table -> KXC04015 base (6061, 3 mm, M2 at +/-10, M3 tapped at +/-16)
  STEP/nest_module_assembly.step        chuck + cage + riser + TEC + die stage stack (vendor STEP where present) + die + gripper (closed) + envelopes
  STEP/nest_module_setdown.step         same with the jaws open at the set-down position (push step)
  checks.txt                            clearances vs gripper (closed / open / push), holders, fibers, die; stage at home and +/-travel

Run:  python cad/nest/model.py   (or python cad/build.py)
"""
from __future__ import annotations
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # cad/
import common as C                                                             # noqa: E402
from common import box, cyl_x, cyl_z, bb, gap                                  # noqa: E402
from gripper import model as G                                                 # noqa: E402

DIRS = C.out_dirs(__file__)
L, W, T = C.DIE_LEN, C.DIE_WID, C.DIE_THK               # 10, 6, 0.5

N = dict(
    # --- fiber side (single source: common.FIBER; measure on the bench) ---
    fiber_protrusion=C.FIBER["protrusion"],
    holder_w=C.FIBER["holder_w"],
    holder_zb=C.FIBER["holder_zb"], holder_zt=C.FIBER["holder_zt"],
    holder_len=C.FIBER["holder_len"],
    # --- chuck pad: lapped copper, 0.5 mm inboard of every die edge -> 9 x 5 mm = 75 % of the backside ---
    pad=(0.5, 9.5, 0.5, 5.5), pad_z=(-1.5, 0.0),
    vac_holes=((2.0, 1.5), (5.0, 1.5), (8.0, 1.5), (2.0, 4.5), (5.0, 4.5), (8.0, 4.5)), vac_d=0.5,
    plenum=(1.5, 8.5, 1.0, 5.0, -3.0, -2.0),
    # copper block: top face at -1.5 (flush with the cage plate top), neck through the riser to the TEC
    block=(-1.5, 11.5, 0.6, 5.4), block_z_top=-1.5, tec_z=-12.0,        # neck bottom = TEC cold face
    vac_stub=(3.0, -6.0, 1.5, -9.5),                                   # (Y, Z, dia, X end): stub tube out of the -X face
    therm=(3.0, -6.0, 1.0, 5.0),                                       # (Y, Z, dia, depth) thermistor bore from +X
    # --- cage (Semitron ESd 480) and its corner blocks ---
    cage=(-2.5, 12.5, -2.0, 8.0, -4.5, -1.5),
    post_z1=0.30, post_z0=-1.5,        # block tops 0.30: 0.09 below the fiber envelope (dia 0.125 at Z 0.5, +0.05) so a fiber aligned to a
                                       # waveguide near the die end passes over the corner guards; still cages the 0.5 mm die
    stop_x=10.0, pad_t=0.6, pad_y=((0.6, 1.2), (4.8, 5.4)), relief=0.2,
    guard_gap=0.4,
    yguard_gap=0.6, yguard_t=0.4, yguard_len=1.5,
    # --- riser / heat sink: neck no wider than the cage in Y down to below the holders, then wide ---
    neck=(-8.0, 18.0, -2.0, 8.0), neck_bottom=-12.0,                   # neck Y = cage Y; holders bottom out at -8
    wide=(-14.0, 24.0, -16.0, 22.0), wide_top=-12.0,                   # 38 sq: covers the KXC04015 table's 32 mm bolt grid
    tec=(15.0, 15.0, 2.5), tec_c=(5.0, 3.0),                           # 15 x 15 x 2.5 micro-TEC centred under the die
    # --- push-to-stop ---
    place_short=0.2, push_overtravel=0.10,
    # --- die stage stack under the riser (bottom up), all centred on the die centre (X 5, Y 3) ---
    adapter_t=3.0, adapter1_t=5.0,                                      # 6061 adapter plates (bolt-pattern changes); the lower one takes the
                                                                        # RMPG40W-N's M3 fixing bolts (they protrude 5 mm below its base)
    # MISUMI RMPG40W-N (from the vendor STEP): body 40 (X) x 55 (Y) x 35 tall, rotation axis 20 from the short end / 35 from the motor
    # end; 39 sq table 6.5 thick with 8 x M2 on a 10 mm grid + dia 8 bore; base 4 x M3 cbore on 32 x 32 around the axis (bolted from
    # above); worm housing + 28 sq stepper along the body's +X (motor centre 24 from the axis toward the long end), cable dia 14 to X 184
    rot=dict(w=40.0, len_short=20.0, len_long=35.0, h=35.0, table=39.0, table_t=6.5, worm=(20.0, 42.0), motor=(42.0, 59.5), motor_sq=28.0,
             motor_off=24.0, cable=(60.0, 100.0), cable_d=14.0, motor_side=-1),   # motor_side: the long end / motor go to station -Y
                                                                        # cable: only the 40 mm straight lead-out is modelled; the vendor file
                                                                        # draws it straight to 184 (station X -179), which would run into the
                                                                        # Y-stage riser at X < -150 -> route it down/along -Y after the lead-out
    kxc=dict(table=40.0, h=30.0, base_h=21.0, base_len=43.5, overhang=3.5,    # Suruga KXC04015-C (catalog p.1-132): 40 sq table, 30 tall,
             motor_len=59.0, coupling_len=12.0, coupling_h=15.0,        # 59 mm motor section: 12 mm coupling housing (15 tall, the table
             motor_w=28.0, motor_z=(4.0, 34.0), knob_len=4.0, knob_dia=12.0,   # passes over it) + 47 mm motor box 28 wide, 4..34 tall (above the table top!)
             travel=15.0, mount_pitch=32.0, table_t=9.0),               # 15 mm travel (+/-7.5), M3 on a 32 mm grid top and bottom
    stage_step_used=4.0,                                                # device stepping actually used: +/-4 mm (waveguides at die X 1..9 under a fiber at X 5)
)
DIE_CX, DIE_CY = L / 2, W / 2


# ----------------------------------------------------------------------------
# Parts
# ----------------------------------------------------------------------------
def chuck():
    """Copper chuck: pad island on the block top, vacuum holes + plenum, neck to the TEC, vacuum stub, thermistor bore."""
    bx0, bx1, by0, by1 = N["block"]
    z_top, z_tec = N["block_z_top"], N["tec_z"]
    c = box(bx0, bx1, by0, by1, z_tec, z_top)
    px0, px1, py0, py1 = N["pad"]
    c = c.union(box(px0, px1, py0, py1, N["pad_z"][0], N["pad_z"][1]))
    c = c.cut(box(*N["plenum"]))
    for (x, y) in N["vac_holes"]:
        c = c.cut(cyl_z(x, y, N["plenum"][5] - 0.1, N["pad_z"][1] + 0.1, N["vac_d"] / 2))
    vy, vz, vd, vxe = N["vac_stub"]
    c = c.cut(cyl_x(vy, vz, bx0 - 0.1, 5.0, vd / 2))                      # bore from the -X face to under the plenum
    c = c.cut(cyl_z(5.0, vy, vz, N["plenum"][4] + 0.1, vd / 2))            # up into the plenum
    c = c.union(cyl_x(vy, vz, vxe, bx0 + 0.01, vd / 2 + 0.5).cut(cyl_x(vy, vz, vxe - 0.1, bx0 + 0.1, vd / 2)))   # stub tube
    ty, tz, td, tdepth = N["therm"]
    c = c.cut(cyl_x(ty, tz, bx1 - tdepth, bx1 + 0.1, td / 2))
    return c


def corner_block(sx, sy):
    """One corner block; sx = +1 for the +X (stop) end, -1 for the -X (guard) end; sy = +1 for +Y, -1 for -Y.
    Bar along Y on the end-face side with a contact face only in the pad zone (relief elsewhere), plus a
    leg along X outside the facet plane (Y guard). Returns (bar, leg)."""
    z0, z1 = N["post_z0"], N["post_z1"]
    t = N["pad_t"]
    if sx > 0:
        face = N["stop_x"]; xb0, xb1 = face, face + t
    else:
        face = -N["guard_gap"]; xb0, xb1 = face - t, face
    (pa, pb) = N["pad_y"][1] if sy > 0 else N["pad_y"][0]
    yg = W + N["yguard_gap"] if sy > 0 else -N["yguard_gap"]
    yo = yg + N["yguard_t"] * sy
    ylo, yhi = (pa, yo) if sy > 0 else (yo, pb)
    bar = box(xb0, xb1, ylo, yhi, z0, z1)
    if sy > 0:
        rel = box(face - 1 if sx < 0 else face, face + 1 if sx > 0 else face, pb, yhi + 0.1, z0 - 0.1, z1 + 0.1)
    else:
        rel = box(face - 1 if sx < 0 else face, face + 1 if sx > 0 else face, ylo - 0.1, pa, z0 - 0.1, z1 + 0.1)
    rel = rel.intersect(box(min(face, face + sx * N["relief"]), max(face, face + sx * N["relief"]), -10, 20, z0 - 1, z1 + 1))
    bar = bar.cut(rel)
    if sx > 0:
        lx0, lx1 = L - N["yguard_len"] + 1.0, xb1
    else:
        lx0, lx1 = xb0, N["yguard_len"] - 1.0
    leg = box(lx0, lx1, min(yg, yo), max(yg, yo), z0, z1)
    return bar, leg


def cage():
    x0, x1, y0, y1, z0, z1 = N["cage"]
    c = box(x0, x1, y0, y1, z0, z1)
    bx0, bx1, by0, by1 = N["block"]
    c = c.cut(box(bx0 - 0.05, bx1 + 0.05, by0 - 0.05, by1 + 0.05, z0 - 0.1, z1 + 0.1))   # window for the copper block
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar, leg = corner_block(sx, sy)
            c = c.union(bar).union(leg)
    for (x, y) in ((-1.8, -1.2), (11.8, 7.2)):                                   # 2 x M2 to the riser
        c = c.cut(cyl_z(x, y, z0 - 0.1, z1 + 0.1, 1.1))
    for (x, y) in ((11.8, -1.2), (-1.8, 7.2)):                                   # 2 x dia 1.5 dowels
        c = c.cut(cyl_z(x, y, z0 - 0.1, z1 + 0.1, 0.75))
    return c


def cage_parts():
    x0, x1, y0, y1, z0, z1 = N["cage"]
    parts = [box(x0, x1, y0, y1, z0, z1)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts += list(corner_block(sx, sy))
    return parts


def tec():
    w, d, h = N["tec"]; cx_, cy_ = N["tec_c"]
    return box(cx_ - w / 2, cx_ + w / 2, cy_ - d / 2, cy_ + d / 2, N["tec_z"] - h, N["tec_z"])


def levels(table_z=C.TABLE_Z, kb_top=None):
    """Z of every interface in the die-stage stack (bottom up). kb_top defaults to the KB1X1 height from common."""
    kb_top = table_z + C.KB1X1_H if kb_top is None else kb_top
    t = N["adapter_t"]
    z = {"table": table_z, "kb_top": kb_top, "ad1_top": kb_top + N["adapter1_t"]}
    z["rpg_top"] = z["ad1_top"] + N["rot"]["h"]
    z["ad2_top"] = z["rpg_top"] + t
    z["kxc_bottom"] = z["ad2_top"]
    z["kxc_base_top"] = z["kxc_bottom"] + N["kxc"]["base_h"]
    z["stage_top"] = z["kxc_bottom"] + N["kxc"]["h"]
    return z


def adapter_kb_rpg(z0):
    """Plate on the KB1X1 top platform (25.4 sq) carrying the RMPG40W-N base: 4 x M3 tapped on the rotary's 32 x 32 pattern
    (its fixing bolts come down through its body, confirmed in the vendor STEP), 4 x clearance for the KB1X1 platform screws."""
    t = N["adapter1_t"]; r = N["rot"]; sgn = r["motor_side"]
    y0, y1 = sorted((DIE_CY + sgn * r["len_long"], DIE_CY - sgn * r["len_short"]))
    a = box(DIE_CX - r["w"] / 2, DIE_CX + r["w"] / 2, y0, y1, z0, z0 + t)
    for dx in (-16, 16):
        for dy in (-16, 16):
            a = a.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 - 0.1, z0 + t + 0.1, 1.25))
    for dx in (-8, 8):
        for dy in (-8, 8):
            a = a.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 - 0.1, z0 + t + 0.1, 1.7))
    return a


def adapter_rpg_kxc(z0):
    """Plate on the RMPG40W-N table (8 x M2 on a 10 mm grid, confirmed in the vendor STEP) carrying the KXC04015 base:
    4 x M3 tapped on the 32 mm grid, 4 x M2 clearance at (+/-10, +/-10), dia 8 relief over the rotary's bore."""
    t = N["adapter_t"]; k = N["kxc"]["table"]
    a = box(DIE_CX - k / 2, DIE_CX + k / 2, DIE_CY - k / 2, DIE_CY + k / 2, z0, z0 + t)
    p = N["kxc"]["mount_pitch"] / 2
    for dx in (-p, p):
        for dy in (-p, p):
            a = a.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 - 0.1, z0 + t + 0.1, 1.25))
    for dx in (-10, 10):
        for dy in (-10, 10):
            a = a.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 - 0.1, z0 + t + 0.1, 1.15))
    return a


def _rot_frame(w, z0):
    """Vendor RMPG40W-N file frame (X = worm/motor direction, Y = rotation axis (table at +Y), Z = body length with the axis at Z -24)
    -> station: axis vertical through the die centre, motor toward -X, long end toward motor_side * Y."""
    sgn = N["rot"]["motor_side"]
    w = w.rotate((0, 0, 0), (1, 0, 0), 90)                      # (x, y, z) -> (x, -z, y): axis up
    w = w.rotate((0, 0, 0), (0, 0, 1), 180)                     # -> (-x, z, y): motor toward -X, long end (+z) toward +Y
    if sgn < 0:
        w = w.mirror("XZ")                                      # long end toward -Y instead
    return w.translate((DIE_CX, DIE_CY + sgn * 24.0, z0 + 16.5))   # file axis lands at Y -/+24 after the rotations / mirror


def rmpg40w(z0):
    """MISUMI RMPG40W-N envelope in the station frame: body, table, worm housing, motor, cable. Base face at z0, table top at z0 + 35."""
    r = N["rot"]; sgn = r["motor_side"]
    yl = DIE_CY + sgn * r["len_long"]; ys = DIE_CY - sgn * r["len_short"]
    y0, y1 = min(yl, ys), max(yl, ys)
    body = box(DIE_CX - r["w"] / 2, DIE_CX + r["w"] / 2, y0, y1, z0, z0 + r["h"] - r["table_t"])
    body = body.cut(cyl_z(DIE_CX, DIE_CY, z0 - 0.1, z0 + r["h"] + 0.1, 4.0))
    t = r["table"]
    table = box(DIE_CX - t / 2, DIE_CX + t / 2, DIE_CY - t / 2, DIE_CY + t / 2, z0 + r["h"] - r["table_t"], z0 + r["h"])
    for dx in (-10, 0, 10):
        for dy in (-10, 0, 10):
            table = table.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 + r["h"] - 3.7, z0 + r["h"] + 0.1, 4.0 if (dx == 0 and dy == 0) else 0.8))
    ym = DIE_CY + sgn * r["motor_off"]; ms = r["motor_sq"] / 2; zc = z0 + 16.5
    worm = box(DIE_CX - r["worm"][1], DIE_CX - r["worm"][0], ym - 14, ym + 14, zc - 14, zc + 14)
    motor = box(DIE_CX - r["motor"][1], DIE_CX - r["motor"][0], ym - ms, ym + ms, zc - ms, zc + ms)
    cable = cyl_x(ym - sgn * 5.5, zc - 11.6, DIE_CX - r["cable"][1], DIE_CX - r["cable"][0], r["cable_d"] / 2)
    return {"body": body, "table": table, "worm": worm, "motor": motor, "cable": cable}


def rmpg40w_vendor(z0, path=None):
    """MISUMI RMPG40W-N from the vendor STEP (cad/vendor/misumi_RMPG40W-N.step, git-ignored). 5 solids: body (with worm housing,
    motor, cable), table plate, three M3 fixing bolts. Split by bounding box; bolts merged into the body. Returns the same dict
    as rmpg40w() (worm/motor/cable are the body's sub-boxes for the checks) or None."""
    path = path or C.vendor_path("misumi_RMPG40W-N.step")
    if not os.path.exists(path):
        return None
    wp = cq.importers.importStep(path)
    sol = sorted(wp.solids().vals(), key=lambda t: -t.Volume())
    body = _rot_frame(cq.Workplane().add(sol[0]), z0)
    body = body.cut(box(DIE_CX - 400, DIE_CX - N["rot"]["cable"][1], -100, 100, z0 - 50, z0 + 100))   # drop the straight cable past the lead-out
    table = _rot_frame(cq.Workplane().add(sol[1]), z0)
    bolts = _rot_frame(cq.Workplane().add(cq.Compound.makeCompound(sol[2:])), z0)
    env = rmpg40w(z0)
    return {"body": body, "table": table, "bolts": bolts, "worm": body.intersect(env["worm"]), "motor": body.intersect(env["motor"]),
            "cable": body.intersect(box(*[c for pair in zip(bb(env["cable"])[0::2], bb(env["cable"])[1::2]) for c in pair]))}


def kxc04015(z0, x_off=0.0):
    """Suruga KXC04015-C envelope with its table at X offset x_off (0 = home, +/-7.5 travel). Motor section toward -X.
    Returns dict: base, table, motor, knob. Base 40 wide x 43.5 long (3.5 overhang at the far +X end), 21 tall; table 40 sq, top at z0 + 30."""
    k = N["kxc"]; t = k["table"]
    x0, x1 = DIE_CX - t / 2, DIE_CX + t / 2
    y0, y1 = DIE_CY - t / 2, DIE_CY + t / 2
    base = box(x0, x1 + k["overhang"], y0, y1, z0, z0 + k["base_h"])
    for dx in (-k["mount_pitch"] / 2, k["mount_pitch"] / 2):                     # 4 x dia 3.5 through, cbore, on the 32 grid
        for dy in (-k["mount_pitch"] / 2, k["mount_pitch"] / 2):
            base = base.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, z0 - 0.1, z0 + k["base_h"] + 0.1, 1.75))
    table = box(x0 + x_off, x1 + x_off, y0, y1, z0 + k["h"] - k["table_t"], z0 + k["h"])
    for dx in (-16, 0, 16):                                                       # 8 x M3 on the 16 grid (centre = dia 4 H7 pin)
        for dy in (-16, 0, 16):
            table = table.cut(cyl_z(DIE_CX + x_off + dx, DIE_CY + dy, z0 + k["h"] - 4.1, z0 + k["h"] + 0.1, 1.25 if (dx or dy) else 2.0))
    mw = k["motor_w"]
    coupling = box(x0 - k["coupling_len"], x0, DIE_CY - mw / 2, DIE_CY + mw / 2, z0, z0 + k["coupling_h"])
    motor = box(x0 - k["motor_len"], x0 - k["coupling_len"], DIE_CY - mw / 2, DIE_CY + mw / 2, z0 + k["motor_z"][0], z0 + k["motor_z"][1])
    zk = z0 + (k["motor_z"][0] + k["motor_z"][1]) / 2 + 3
    knob = cyl_x(DIE_CY, zk, x0 - k["motor_len"] - k["knob_len"], x0 - k["motor_len"] + 0.01, k["knob_dia"] / 2)
    return {"base": base, "table": table, "coupling": coupling, "motor": motor, "knob": knob}


def kxc04015_vendor(z0, x_off=0.0, path=None):
    """Suruga KXC04015-C from the vendor STEP (cad/vendor/suruga_KXC04015-C.step, git-ignored). File frame: X = travel
    (motor at +X), Y = up (base bottom Y 0, table top Y 30), Z = width (+/-20), table drawn at mid travel. Confirmed from the
    file: table 8 x M3 on a 16 mm grid + dia 4 centre pin; base 4 x dia 3.5 through on 32 x 32 + dia 4 centre + one dia 5 at
    (27.5, 4); base solid runs to X 31 (sensor cover), motor box 28 sq x 38 long at X 41..79, 34 tall (4 above the table top).
    Station frame: X = -file X (motor toward -X), Y = file Z, Z = file Y. Returns the same dict as kxc04015() or None."""
    path = path or C.vendor_path("suruga_KXC04015-C.step")
    if not os.path.exists(path):
        return None
    wp = cq.importers.importStep(path)
    parts = {}
    for t in wp.solids().vals():
        b = t.BoundingBox()
        if b.ymin > 15 and b.xmax < 25:
            k = "table"
        elif b.xmin > 40:
            k = "motor"
        elif b.xmax <= 31.5 and b.ymin < 1:
            k = "base"
        else:
            k = "coupling"
        w = cq.Workplane().add(t).rotate((0, 0, 0), (1, 0, 0), 90).rotate((0, 0, 0), (0, 0, 1), 180)   # (x, y, z) -> (-x, z, y)
        w = w.translate((DIE_CX + (x_off if k == "table" else 0.0), DIE_CY, z0))
        parts[k] = w
    parts["knob"] = parts["coupling"]                                                                  # knob/cable are in the coupling solid
    return parts


def stack(table_z=C.TABLE_Z, kb_top=None, x_off=0.0, vendor=False):
    """All die-stage stack parts under the riser, name -> shape, plus the levels dict. vendor=True places the Suruga
    KXC04015-C and MISUMI RMPG40W-N STEP files when they are present."""
    z = levels(table_z, kb_top)
    ro = (rmpg40w_vendor(z["ad1_top"]) if vendor else None) or rmpg40w(z["ad1_top"])
    kx = (kxc04015_vendor(z["kxc_bottom"], x_off) if vendor else None) or kxc04015(z["kxc_bottom"], x_off)
    parts = {"nest_adapter_kb_rpg": adapter_kb_rpg(z["kb_top"])}
    parts.update({f"rmpg40w_{k}": v for k, v in ro.items()})
    parts.update({"nest_adapter_rpg_kxc": adapter_rpg_kxc(z["rpg_top"]), "kxc04015_base": kx["base"], "kxc04015_table": kx["table"],
                  "kxc04015_coupling": kx["coupling"], "kxc04015_motor": kx["motor"], "kxc04015_knob": kx["knob"]})
    return parts, z


def riser(stage_top):
    """T-shaped riser: narrow neck (cage width in Y) from the cage plate down past the holders' underside,
    wide body below with the TEC pocket, wire channel and the vacuum stub clearance; bolted to the KXC04015 table
    (4 x M3 counterbored on the 32 mm grid). stage_top = Z of the X-stage table top (levels()['stage_top'])."""
    nx0, nx1, ny0, ny1 = N["neck"]
    wx0, wx1, wy0, wy1 = N["wide"]
    r = box(wx0, wx1, wy0, wy1, stage_top, N["wide_top"]).union(box(nx0, nx1, ny0, ny1, N["neck_bottom"], N["cage"][4]))
    p = N["kxc"]["mount_pitch"] / 2
    for dx in (-p, p):                                                                                    # M3 cbore to the stage table
        for dy in (-p, p):
            r = r.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, stage_top - 0.1, N["wide_top"] + 0.1, 1.7))
            r = r.cut(cyl_z(DIE_CX + dx, DIE_CY + dy, N["wide_top"] - 3.0, N["wide_top"] + 0.1, 2.8))
    bx0, bx1, by0, by1 = N["block"]
    r = r.cut(box(bx0 - 0.3, bx1 + 0.3, by0 - 0.3, by1 + 0.3, N["tec_z"] - 0.1, N["cage"][4] + 0.1))   # slot for the copper neck (air gap)
    w, d, h = N["tec"]; cx_, cy_ = N["tec_c"]
    r = r.cut(box(cx_ - w / 2 - 0.2, cx_ + w / 2 + 0.2, cy_ - d / 2 - 0.2, cy_ + d / 2 + 0.2, N["tec_z"] - h - 0.05, N["tec_z"] + 0.1))
    r = r.cut(box(wx0 - 0.1, cx_ - w / 2, cy_ - 2.0, cy_ + 2.0, N["tec_z"] - h, N["tec_z"] + 0.1))         # TEC wire channel to -X
    vy, vz, vd, vxe = N["vac_stub"]
    r = r.cut(cyl_x(vy, vz, nx0 - 0.1, bx0, vd / 2 + 1.0))                                            # vacuum stub clearance
    ty, tz, td, _ = N["therm"]
    r = r.cut(cyl_x(ty, tz, bx1, nx1 + 0.1, td / 2 + 0.6))                                            # thermistor wire clearance
    for (x, y) in ((-1.8, -1.2), (11.8, 7.2)):                                                            # M2 tapped for the cage
        r = r.cut(cyl_z(x, y, N["cage"][4] - 4.0, N["cage"][4] + 0.1, 0.8))
    for (x, y) in ((11.8, -1.2), (-1.8, 7.2)):
        r = r.cut(cyl_z(x, y, N["cage"][4] - 3.0, N["cage"][4] + 0.1, 0.75))
    return r


# ----------------------------------------------------------------------------
# Context and checks
# ----------------------------------------------------------------------------
def fiber_envelopes():
    """Fiber (dia 0.125 at the die-top height, X 1..9 where the waveguides are) and holder body envelopes."""
    fz0, fz1 = T - 0.0625 - 0.05, T + 0.0625 + 0.05
    p, hw, hl = N["fiber_protrusion"], N["holder_w"] / 2, N["holder_len"]
    zb, zt = N["holder_zb"], N["holder_zt"]
    return {
        "fiber_in": box(1.0, 9.0, -p, 0.0, fz0, fz1),
        "fiber_out": box(1.0, 9.0, W, W + p, fz0, fz1),
        "holder_in": box(5 - hw, 5 + hw, -p - hl, -p, zb, zt),
        "holder_out": box(5 - hw, 5 + hw, W + p, W + p + hl, zb, zt),
    }



def moving_members(x_off=0.0):
    """Everything that moves with the X stage, as separate boxes for per-member checks: neck, wide body, cage plate,
    corner blocks, chuck block, stage table. Translated by x_off along X."""
    nx0, nx1, ny0, ny1 = N["neck"]; wx0, wx1, wy0, wy1 = N["wide"]
    z = levels()
    m = {"riser neck": box(nx0, nx1, ny0, ny1, N["neck_bottom"], N["cage"][4]),
         "riser wide body": box(wx0, wx1, wy0, wy1, z["stage_top"], N["wide_top"]),
         "cage plate": box(*N["cage"]), "chuck block": chuck(),
         "stage table": kxc04015(z["kxc_bottom"])["table"]}
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar, leg = corner_block(sx, sy)
            tag = f"{'+' if sx > 0 else '-'}X{'+' if sy > 0 else '-'}Y"
            m[f"{'stop pad' if sx > 0 else 'X guard'} {tag}"] = bar
            m[f"Y guard {tag}"] = leg
    return {k: v.translate((x_off, 0, 0)) for k, v in m.items()}


def main():
    z = levels()
    ch, cg, rs, te = chuck(), cage(), riser(z["stage_top"]), tec()
    stk, _ = stack(vendor=True)                       # vendor stages where their files exist, envelopes otherwise
    die_seated = C.die()
    die_placed = C.die().translate((-N["place_short"], 0, 0))
    die_yoff = C.die().translate((-N["place_short"], -0.4, 0))
    grip_closed = {"far_tip": G.far_tip_block(), "near_tip": G.near_tip_block(), "blade": G.blade(),
                   "near_arm": G.near_arm(), "far_arm": G.far_arm()}
    o = 1.5
    grip_open = {"far_tip": G.far_tip_block().translate((o, 0, 0)), "near_tip": G.near_tip_block().translate((-o, 0, 0)),
                 "blade": G.blade().translate((-o, 0, 0)), "near_arm": G.near_arm().translate((-o, 0, 0)),
                 "far_arm": G.far_arm().translate((o, 0, 0))}
    push = o - G.near_face_x + N["place_short"] + N["push_overtravel"]
    grip_push = {k: v.translate((push, 0, 0)) for k, v in grip_open.items()}
    fib = fiber_envelopes()
    blocks = {}
    for sx in (-1, 1):
        for sy in (-1, 1):
            bar, leg = corner_block(sx, sy)
            tag = f"{'+' if sx > 0 else '-'}X{'+' if sy > 0 else '-'}Y"
            blocks[f"{'stop pad' if sx > 0 else 'X guard'} {tag}"] = bar
            blocks[f"Y guard {tag}"] = leg
    plate = box(*N["cage"])
    nx0, nx1, ny0, ny1 = N["neck"]; wx0, wx1, wy0, wy1 = N["wide"]
    neck = box(nx0, nx1, ny0, ny1, N["neck_bottom"], N["cage"][4])
    wide = box(wx0, wx1, wy0, wy1, z["stage_top"], N["wide_top"])
    pad = box(N["pad"][0], N["pad"][1], N["pad"][2], N["pad"][3], N["pad_z"][0], N["pad_z"][1])
    k = N["kxc"]

    px0, px1, py0, py1 = N["pad"]
    pad_area = (px1 - px0) * (py1 - py0)
    rep = [
        "Nest: lapped copper chuck pad -> Z/pitch/roll; +X Semitron stop pads (Y 0.6-1.2, 4.8-5.4; 4.2 mm base) -> X and yaw;",
        f"Y free within +/-{N['yguard_gap']} mm (corner guards). Fiber protrusion {N['fiber_protrusion']} mm: holder bodies at Y <= -{N['fiber_protrusion']} and >= {W + N['fiber_protrusion']}.",
        f"Chuck pad {px1 - px0:.0f} x {py1 - py0:.0f} mm = {100 * pad_area / (L * W):.0f} % of the backside on metal, 0.5 mm inboard of every edge; "
        f"{len(N['vac_holes'])} x dia {N['vac_d']} vacuum holes; copper neck to a {N['tec'][0]:.0f} x {N['tec'][1]:.0f} TEC at Z {N['tec_z']}.",
        f"Push-to-stop: set down {N['place_short']} mm short, jaws open, gripper +{push:.2f} mm -> near nose seats the die with "
        f"{G.flexure_k() * N['push_overtravel'] * 1e-3:.2f} N (blade overtravel {N['push_overtravel']} mm).",
        f"Die stage stack (table Z {z['table']:.1f}): KB1X1 top {z['kb_top']:.1f}, adapter, RMPG40W-N {z['ad1_top']:.1f}..{z['rpg_top']:.1f}, adapter, "
        f"KXC04015-C {z['kxc_bottom']:.1f}..{z['stage_top']:.1f} (table top), riser wide body {z['stage_top']:.1f}..{N['wide_top']:.1f} "
        f"({N['wide_top'] - z['stage_top']:.1f} mm: TEC pocket {N['tec'][2]} + floor), neck to the cage plate at {N['cage'][4]:.1f}.",
        f"Stage travel {k['travel']:.0f} mm (+/-{k['travel'] / 2:.1f}); device stepping uses +/-{N['stage_step_used']:.0f}. Both motors point -X "
        f"(X < {DIE_CX - k['table'] / 2:.0f}); the rotary's long end and motor toward {'-' if N['rot']['motor_side'] < 0 else '+'}Y. The gripper meets the nest at stage HOME only.",
        "",
    ]

    def check(an, a, bn, b, need=0.0):
        g = gap(bb(a), bb(b))
        flag = "  OK " if g > need else ("  TOUCH" if g > -1e-6 else "  ** OVERLAP **")
        rep.append(f"  {an:34s} vs {bn:26s}: {g:7.2f}{flag}")

    rep.append("chuck pad inside the die footprint (positive = pad edge inboard of the die edge):")
    b = bb(pad); rep.append(f"  pad X {b[0]:.1f}..{b[1]:.1f} in die 0..{L:.0f} (margins {b[0]:.1f} / {L - b[1]:.1f}); pad Y {b[2]:.1f}..{b[3]:.1f} in die 0..{W:.0f} (margins {b[2]:.1f} / {W - b[3]:.1f})")
    rep.append("cage blocks vs the die (only the +X stop pads touch the seated die):")
    for bn, blk in blocks.items():
        check(bn, blk, "die seated", die_seated)
        check(bn, blk, "die set down (-0.2 X)", die_placed)
        check(bn, blk, "die Y-offset -0.4", die_yoff)
    rep.append("cage blocks vs the gripper, jaws CLOSED on the seated die:")
    for bn, blk in blocks.items():
        for gn, gp in grip_closed.items():
            check(bn, blk, f"{gn} (closed)", gp, need=0.2)
    rep.append("cage blocks vs the gripper, jaws OPEN at the set-down position:")
    for bn, blk in blocks.items():
        for gn in ("far_tip", "near_tip", "blade"):
            check(bn, blk, f"{gn} (open)", grip_open[gn].translate((-N["place_short"], 0, 0)), need=0.2)
    rep.append("cage blocks vs the gripper during the push (jaws open, +X indexed):")
    for bn, blk in blocks.items():
        for gn in ("far_tip", "near_tip", "blade"):
            check(bn, blk, f"{gn} (push)", grip_push[gn], need=0.2)
    rep.append("nest vs fiber / holder envelopes (holder front 5 mm from the facet, body 25 wide, Z -8..+4):")
    for fn_, fe in fib.items():
        for bn, blk in blocks.items():
            check(bn, blk, fn_, fe, need=0.3)
        check("cage plate", plate, fn_, fe, need=0.3)
        check("chuck block", ch, fn_, fe, need=0.3)
        check("riser neck", neck, fn_, fe, need=2.0)
        check("riser wide body", wide, fn_, fe, need=2.0)
    rep.append("holder bodies vs the gripper at the nest (jaws closed):")
    for hn in ("holder_in", "holder_out"):
        for gn, gp in grip_closed.items():
            check(gn, gp, hn, fib[hn], need=2.0)
    # the nest MOVES under fixed fibers and holders: the fibers stay at station X 5 (the device under test is brought to them),
    # the holder bodies stay where they are; every moving member is checked over the used stepping range and at the travel ends
    fz0, fz1 = T - 0.0625 - 0.05, T + 0.0625 + 0.05
    p_ = N["fiber_protrusion"]
    fixed_fib = {"fiber_in (station X 5)": box(DIE_CX - 0.1, DIE_CX + 0.1, -p_, 0.0, fz0, fz1),
                 "fiber_out (station X 5)": box(DIE_CX - 0.1, DIE_CX + 0.1, W, W + p_, fz0, fz1),
                 "holder_in": fib["holder_in"], "holder_out": fib["holder_out"]}
    used = N["stage_step_used"]; ends = k["travel"] / 2
    offs = sorted(set([-ends, ends] + [round(-used + i * 1.0, 1) for i in range(int(2 * used) + 1)]))
    rep.append(f"the nest moves under FIXED fibers (at station X 5) and holders: worst clearance of every moving member over stage offsets "
               f"{offs[0]:+.1f}..{offs[-1]:+.1f} (device stepping +/-{used:.0f}, travel ends +/-{ends:.1f}):")
    fixed_stack = {n: v for n, v in stk.items() if n != "kxc04015_table"}
    worst = {}
    for x_off in offs:
        mv = moving_members(x_off)
        for fn_, fe in fixed_fib.items():
            for mn, mm in mv.items():
                g = gap(bb(mm), bb(fe))
                key = (mn, fn_)
                if key not in worst or g < worst[key][0]:
                    worst[key] = (g, x_off)
        for mn, mm in mv.items():
            for sn, sv in fixed_stack.items():
                g = gap(bb(mm), bb(sv))
                key = (mn, sn)
                if key not in worst or g < worst[key][0]:
                    worst[key] = (g, x_off)
    for (mn, on), (g, xo) in sorted(worst.items(), key=lambda kv: kv[0]):
        if on.startswith("fiber") or on.startswith("holder"):
            need = 2.0 if ("riser" in mn or "table" in mn) else (0.05 if on.startswith("fiber") else 0.3)
        else:
            if (mn, on) == ("stage table", "kxc04015_base") or (mn == "riser wide body" and on == "kxc04015_base"):
                continue
            need = 2.0
        if g < 6.0 or on.startswith("fiber"):
            rep.append(f"  {mn:24s} vs {on:26s}: {g:7.2f} @{xo:+.1f}{'  OK ' if g > need else ('  TIGHT' if g > -1e-6 else '  ** OVERLAP **')}")
    kv = kxc04015_vendor(z["kxc_bottom"])
    if kv is not None:
        rep.append("KXC04015-C vendor STEP vs the catalog envelope (station frame; the file is the record where they differ):")
        ke = kxc04015(z["kxc_bottom"])
        for kname in ("base", "table", "motor", "coupling"):
            bv, be = bb(kv[kname]), bb(ke[kname])
            rep.append(f"  {kname:10s} vendor X {bv[0]:6.1f}..{bv[1]:6.1f} Y {bv[2]:6.1f}..{bv[3]:6.1f} Z {bv[4]:6.1f}..{bv[5]:6.1f}   "
                       f"envelope X {be[0]:6.1f}..{be[1]:6.1f} Y {be[2]:6.1f}..{be[3]:6.1f} Z {be[4]:6.1f}..{be[5]:6.1f}")
    rv = rmpg40w_vendor(z["ad1_top"])
    if rv is not None:
        rep.append("RMPG40W-N vendor STEP vs the envelope (station frame):")
        re_ = rmpg40w(z["ad1_top"])
        for kname in ("body", "table", "motor", "cable"):
            bv, be = bb(rv[kname]), bb(re_[kname])
            rep.append(f"  {kname:10s} vendor X {bv[0]:6.1f}..{bv[1]:6.1f} Y {bv[2]:6.1f}..{bv[3]:6.1f} Z {bv[4]:6.1f}..{bv[5]:6.1f}   "
                       f"envelope X {be[0]:6.1f}..{be[1]:6.1f} Y {be[2]:6.1f}..{be[3]:6.1f} Z {be[4]:6.1f}..{be[5]:6.1f}")
    rep.append("fixed stack members vs the holders and fibers (both motors point -X):")
    for sn, sv in stk.items():
        for fn_, fe in fib.items():
            g = gap(bb(sv), bb(fe))
            if g < 15:
                rep.append(f"  {sn:34s} vs {fn_:26s}: {g:7.2f}{'  OK ' if g > 2 else ('  TIGHT' if g > 0 else '  ** OVERLAP **')}")
    rep.append("near nose face at the end of the push: X %.2f = blade overtravel (die -X end face at X 0.00 on the pads)"
               % (-N["place_short"] + G.near_face_x - o + push))
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(DIRS["comp"], "checks.txt"), "w") as f:
        f.write(txt + "\n")

    parts = {"nest_chuck_copper": ch, "nest_cage_semitron": cg, "nest_riser_6061": rs,
             "nest_adapter_kb_rpg": stk["nest_adapter_kb_rpg"], "nest_adapter_rpg_kxc": stk["nest_adapter_rpg_kxc"]}
    for name, shape in parts.items():
        C.export_part(shape, DIRS, name, stl=(name in ("nest_chuck_copper", "nest_cage_semitron")), tolerance=0.005)
    col = {"nest_chuck_copper": (0.72, 0.45, 0.20), "nest_cage_semitron": (0.16, 0.16, 0.18), "nest_riser_6061": (0.60, 0.63, 0.68),
           "nest_adapter_kb_rpg": (0.60, 0.63, 0.68), "nest_adapter_rpg_kxc": (0.60, 0.63, 0.68), "tec_15x15": (0.85, 0.85, 0.88)}
    vend = {n: v for n, v in stk.items() if not n.startswith("nest_adapter")}
    vcol = (0.20, 0.20, 0.22)
    assy = cq.Assembly(name="nest_module")
    for n, s in {**parts, "tec_15x15": te}.items():
        assy.add(s, name=n, color=cq.Color(*col[n], 1.0))
    for n, s in vend.items():
        assy.add(s, name=n, color=cq.Color(*vcol, 1.0))
    assy.add(die_seated, name="die_seated", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k, v in grip_closed.items():
        assy.add(v, name=f"gripper_{k}_closed", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    for k, v in fib.items():
        assy.add(v, name=k, color=cq.Color(0.94, 0.82, 0.50, 0.35))
    assy.save(os.path.join(DIRS["STEP"], "nest_module_assembly.step"))
    a2 = cq.Assembly(name="nest_module_setdown")
    for n, s in {**parts, "tec_15x15": te}.items():
        a2.add(s, name=n, color=cq.Color(*col[n], 1.0))
    for n, s in vend.items():
        a2.add(s, name=n, color=cq.Color(*vcol, 1.0))
    a2.add(die_placed, name="die_set_down", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k in ("far_tip", "near_tip", "blade", "near_arm", "far_arm"):
        a2.add(grip_open[k].translate((-N["place_short"], 0, 0)), name=f"gripper_{k}_open", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    a2.save(os.path.join(DIRS["STEP"], "nest_module_setdown.step"))
    for old in ("nest_module_assembly_vendor.step",):
        try: os.remove(os.path.join(DIRS["STEP"], old))
        except OSError: pass
    print("wrote", DIRS["comp"])


if __name__ == "__main__":
    main()

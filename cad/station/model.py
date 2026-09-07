"""
Full test-station assembly: nest, gripper module, bench-level Cartesian transport
(X axis + Z axis + arm, Y stage under the stick), two NanoMax 300 fiber stages with
holders, microscope column/objective, optical table. Frame, die and contact rules: cad/common
(X = die long axis, Y = optical axis, Z up, Z = 0 = die bottom at the nest). The gripper, the nest and
the tray are imported from their own packages (cad/gripper, cad/nest, cad/tray); this file only
places them and adds the transport, the fiber stages and the microscope.

Bought parts: vendor STEP from cad/vendor (git-ignored, see vendor/README.md) wherever the file is present,
the envelope below otherwise (so a clone without the vendor files still builds and checks):
  - MISUMI LX20 single-axis actuators (X, Y, Z transport): envelope from common.LX20 until the STEP is supplied
  - Thorlabs NanoMax 300: 112 x 112 footprint, 62.5 deck height, 4 mm travel
  - Microscope: objective barrel dia 34, tube dia 40, column post dia 40 behind (+X)  (always an envelope)

Transport layout (see station/README.md): the X actuator runs along X beside the input NanoMax at Y -140, on a
full-length riser, its 52 mm band outside the tray's Y sweep so no bridge is needed; the Z actuator stands on an
angle bracket on the X block with its motor up; the 25 mm square arm leaves an adapter plate on the Z block along
+Y to the gripper interface. The Y actuator sits under the tray on a riser that puts the pocket ledges 12 mm below
the chuck pad, so Z uses 8 mm lift + 12 mm drop of its 36.5 mm stroke.

Run: python cad/station/model.py [--horizontal]
     -> STEP/station_assembly[_h].step (git-ignored, large) + checks[_h].txt (the header lists the vendor files placed)
"""
from __future__ import annotations
import os, sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # cad/
import common as C                                                             # noqa: E402
from common import box, bb, gap, gap_any, gap_cyl                              # noqa: E402
from gripper import model as G                                                 # noqa: E402
from nest import model as NM                                                   # noqa: E402
from tray import model as TM                                                   # noqa: E402

DIRS = C.out_dirs(__file__)
VENDOR_PLACED = []                           # names of the manufacturer files actually placed (written into the checks header)


def vendor_step(fname):
    """Manufacturer STEP from cad/vendor/ when the file exists, else None (caller falls back to its envelope)."""
    p = C.vendor_path(fname)
    if os.path.exists(p):
        print(f"[vendor] {fname}")
        VENDOR_PLACED.append(fname)
        return cq.importers.importStep(p)
    return None

# ----------------------------------------------------------------------------
# Station parameters
# ----------------------------------------------------------------------------
S = dict(
    # fiber side: bench levels from common (TABLE_Z follows from these)
    holder_axis_above_deck=C.HOLDER_AXIS_ABOVE_DECK,   # fiber axis height above the NanoMax top platform (holder-dependent; measure)
    nanomax_w=C.NANOMAX["w"], nanomax_h=C.NANOMAX["h"], nanomax_platform_h=C.NANOMAX["platform_h"], nanomax_gap_y=C.NANOMAX["gap_y"],
    # fiber holder envelope: single source common.FIBER (shared with the nest)
    fiber_protrusion=C.FIBER["protrusion"], holder_w=C.FIBER["holder_w"], holder_zb=C.FIBER["holder_zb"],
    holder_zt=C.FIBER["holder_zt"], holder_len=C.FIBER["holder_len"],
    # microscope (behind the nest, +X, as in the bench photo); WD and diameters from common
    obj_wd=C.OBJ_WD, obj_dia=C.OBJ_DIA, obj_len=40.0, tube_dia=C.TUBE_DIA, tube_len=60.0,
    column_x=80.0, column_dia=40.0, column_top=260.0,
    # transport: three MISUMI LX2005-B1-T2042 actuators (common.LX20), lead 5
    lx_L=dict(x=300, y=200, z=100),   # base lengths -> effective strokes 236.5 / 136.5 / 36.5 (common.LX20["stroke"])
    x_axis_cy=-140.0,              # X actuator centre-line: its 52 mm band (Y -166..-114) lies beside the tray's Y sweep (deck to
                                   # Y -108 at the extreme row) and beside the input NanoMax (X -51..61), so the riser is one bar
    nanomax_riser=C.NANOMAX_RISER, # plate under each NanoMax (the die-stage stack needs 100 mm under the die; the fiber axis stays at Z 0.5)
    tray_drop=12.0,                # pocket ledge top below the chuck pad top: Z uses 8 mm lift + 12 mm drop of its stroke
    push_x=1.7,                    # push-to-stop travel at the nest (docs/pick_and_place_design.md 3.3)
    end_margin=2.5,                # block-centre margin kept to both travel limits of every actuator
    tower_w=60.0, tower_t=10.0,    # 6061 angle bracket on the X block: 60 x 60 x 10 base plate (block's 4 x M4), 10 mm vertical leg
    arm_sec=25.0,                  # square arm bar (6061) from the adapter plate on the Z block to the gripper interface
    arm_plate_t=8.0,               # adapter plate on the Z block face (block's 4 x M4)
    tower_mass=1.7,                # kg: Z actuator 0.45 + brake motor 0.6 + bracket 0.3 + arm 0.25 + gripper 0.1 (moment check on the X block)
    # wafer tray: geometry and column positions live in cad/tray (TM.TR)
    tray_cols=TM.TR["cols"], tray_rows=TM.TR["rows"], tray_col_pitch=TM.TR["col_pitch"], tray_row_pitch=TM.TR["row_pitch"],
    tray_col0_x=TM.TR["col0_x"],   # die X of the first (nearest) column; last column at -95 - 7*16 = -207
)

die_top = G.die_top
table_z = C.TABLE_Z                                                                          # -86.0 (single source: common)
cy = G.die_cy                                                                                # 3.0
S["table_z"] = table_z


# ----------------------------------------------------------------------------
# Static structure
# ----------------------------------------------------------------------------
def table():
    return box(-720, 220, -280, 280, table_z - 12, table_z)


def nest():
    """Nest (cad/nest): copper chuck + Semitron cage + T-riser with the TEC on the die-stage stack
    (KB1X1 kinematic base, adapter, KXC04015-C X stage, spacer, RMPG40W-N rotary). Returns name -> shape of the
    static-frame parts at the stage home position and fills S['_nest_*'] member lists for the checks."""
    kb = vendor_step("thorlabs_KB1X1.step")
    if kb is not None:
        # Thorlabs 2374-E0W: 25.4 x 25.4 x 12.7 mm assembled, modelled with Y as the thickness ->
        # rotate Y->Z, centre on the die (X 5, Y 3), bottom on the table
        b = kb.val().BoundingBox()
        kb = kb.rotate((0, 0, 0), (1, 0, 0), 90)
        b2 = kb.val().BoundingBox()
        kb = kb.translate((5 - (b2.xmin + b2.xmax) / 2, cy - (b2.ymin + b2.ymax) / 2, table_z - b2.zmin))
        kb_top = table_z + (b2.zmax - b2.zmin)                                 # 12.7
    else:
        kb = box(5 - 12.7, 5 + 12.7, cy - 12.7, cy + 12.7, table_z, table_z + C.KB1X1_H)   # KB1X1 envelope 25.4 sq x 12.7
        kb_top = table_z + C.KB1X1_H
    z = NM.levels(table_z, kb_top)
    stk, _ = NM.stack(table_z, kb_top, vendor=True)
    riser = NM.riser(z["stage_top"])
    S["_nest_tec"] = NM.tec(); S["_nest_levels"] = z
    S["_nest_cage"] = NM.cage(); S["_nest_cage_parts"] = NM.cage_parts()
    nx0, nx1, ny0, ny1 = NM.N["neck"]; wx0, wx1, wy0, wy1 = NM.N["wide"]
    S["_nest_riser_parts"] = [box(nx0, nx1, ny0, ny1, NM.N["neck_bottom"], NM.N["cage"][4]),      # neck (cage width in Y)
                              box(wx0, wx1, wy0, wy1, z["stage_top"], NM.N["wide_top"])]          # wide body on the stage table
    S["_nest_stack_parts"] = [v for n, v in stk.items() if not n.startswith("rmpg40w") and n != "nest_spacer_kxc_rot"] + [kb]   # fixed part (rotary + spacer move)
    S["_nest_moving"] = NM.moving_members(0.0)                                                    # what the X stage carries (dict)
    for fn_ in ("suruga_KXC04015-C.step", "misumi_RMPG40W-N.step"):
        if os.path.exists(C.vendor_path(fn_)):
            VENDOR_PLACED.append(fn_)
    parts = {"nest_kb1x1": kb, "nest_riser_6061": riser, "nest_chuck_copper": NM.chuck()}
    parts.update({"nest_" + n if not n.startswith("nest_") else n: v for n, v in stk.items()})
    return parts


def nanomax(side):
    """side=-1 input (Y<0), +1 output (Y>6). Returns list of (name, shape)."""
    g = S["nanomax_gap_y"]
    if side < 0:
        y0, y1 = -(g + S["nanomax_w"]), -g
    else:
        y0, y1 = G.P["die_wid"] + g, G.P["die_wid"] + g + S["nanomax_w"]
    x0, x1 = 5 - S["nanomax_w"] / 2, 5 + S["nanomax_w"] / 2
    zr = table_z + S["nanomax_riser"]                                          # NanoMax base sits on its riser plate
    riser = nanomax_riser_part(x0, x1, y0, y1, table_z, zr)
    stage = vendor_step("thorlabs_MAX313D_M.step")
    if stage is not None:
        # Thorlabs 22803-E0W (MAX313D/M): base plate X -114.5..-2.5, Y -14..98, Z 0; body Y face at -14 is the
        # side without micrometers, so it faces the die; the three micrometers point away (+Y in the file).
        # The Z micrometer sticks 46 mm out of the +X face. Input stage: rotating 180 deg would point it at the
        # X axis (37 mm overlap), so rotate -90 deg instead: the micrometer-free -X face turns toward the die,
        # the two Y micrometers point +X (toward the column side, nothing there at Y -90..-150) and the Z
        # micrometer points -Y. (A left-handed NanoMax would allow the mirror-symmetric layout.) Output stage: as modelled.
        if side < 0:
            stage = stage.rotate((0, 0, 0), (0, 0, 1), -90)                   # (x, y) -> (y, -x): body Y 14..115.5, base X -14..98
            stage = stage.translate((5 - 42.0, y1 - 115.5, zr))               # inner (body) face -> Y -45, base centred on the die
        else:
            stage = stage.translate((5 + 58.5, y0 + 14.0, zr))                # inner face -> Y 51
        ptop = zr + 62.5                                                      # NanoMax 300 deck height (Thorlabs)
        body = plat = None
    else:
        body = box(x0, x1, y0, y1, zr, zr + S["nanomax_h"])
        plat = box(x0 + 10, x1 - 10, y0 + 6, y1 - 6, zr + S["nanomax_h"], zr + S["nanomax_h"] + S["nanomax_platform_h"])
        ptop = zr + S["nanomax_h"] + S["nanomax_platform_h"]
    # fiber holder: post on the platform near the inner edge, arm to the clamp, clamp, fiber
    if side < 0:
        post = box(-4, 14, y1 - 14, y1 - 6, ptop, die_top + 4)
        arm = box(1, 9, y1 - 8, -S["fiber_protrusion"] - S["holder_len"] + 1, die_top - 1.5, die_top + 1.5)
        clamp = box(5 - S["holder_w"] / 2, 5 + S["holder_w"] / 2, -S["fiber_protrusion"] - S["holder_len"], -S["fiber_protrusion"],
                    S["holder_zb"], S["holder_zt"])
        fib = cq.Workplane("XZ").center(5, die_top).circle(0.0625).extrude(S["fiber_protrusion"] - 0.02).translate((0, -0.02, 0))
    else:
        yf = G.P["die_wid"]
        post = box(-4, 14, y0 + 6, y0 + 14, ptop, die_top + 4)
        arm = box(1, 9, yf + S["fiber_protrusion"] + S["holder_len"] - 1, y0 + 8, die_top - 1.5, die_top + 1.5)
        clamp = box(5 - S["holder_w"] / 2, 5 + S["holder_w"] / 2, yf + S["fiber_protrusion"], yf + S["fiber_protrusion"] + S["holder_len"],
                    S["holder_zb"], S["holder_zt"])
        fib = cq.Workplane("XZ").center(5, die_top).circle(0.0625).extrude(-(S["fiber_protrusion"] - 0.02)).translate((0, yf + 0.02, 0))
    tag = "in" if side < 0 else "out"
    S[f"_holder_parts_{tag}"] = [post, arm, clamp]
    stage_shape = stage if stage is not None else body.union(plat)
    return [(f"nanomax300_{tag}", stage_shape), (f"nanomax_riser_{tag}", riser), (f"fiber_holder_{tag}", post.union(arm).union(clamp)), (f"fiber_{tag}", fib)]


def microscope():
    z_obj0 = die_top + S["obj_wd"]
    obj = cq.Workplane("XY").center(5, cy).circle(S["obj_dia"] / 2).extrude(S["obj_len"]).translate((0, 0, z_obj0))
    nose = cq.Workplane("XY").center(5, cy).circle(6).workplane(offset=4).circle(S["obj_dia"] / 2 - 5).loft().translate((0, 0, z_obj0))
    tube = cq.Workplane("XY").center(5, cy).circle(S["tube_dia"] / 2).extrude(S["tube_len"]).translate((0, 0, z_obj0 + S["obj_len"]))
    z_arm = z_obj0 + S["obj_len"] + S["tube_len"]
    harm = box(5, S["column_x"], cy - 15, cy + 15, z_arm, z_arm + 25)
    col = cq.Workplane("XY").center(S["column_x"], cy).circle(S["column_dia"] / 2).extrude(S["column_top"] - table_z).translate((0, 0, table_z))
    return [("objective", obj.union(nose)), ("microscope_tube", tube), ("microscope_arm", harm), ("microscope_column", col)]


def keepout():
    return C.keepout(S["obj_wd"], S["obj_dia"])


# ----------------------------------------------------------------------------
# MISUMI LX20 single-axis actuators (envelope from common.LX20). Three orientations:
#   X: rail along X at Y = S["x_axis_cy"], block moves in X, motor beyond the -X end
#   Y: rail along Y under the tray, block moves in Y, motor beyond the +Y end
#   Z: rail vertical, back face against the tower's vertical leg (+X face), block face toward the nest, motor up
# All members are boxes; the block envelope includes the part riding inside the rail. When the manufacturer STEP is
# supplied (cad/vendor/misumi_LX2005-B1-T2042-<L>.step) it replaces these members under the same names.
# ----------------------------------------------------------------------------
LX = C.LX20
_LX_FILES = {}


def lx_limits(L):
    """Table-centre travel limits measured from the rail start (0) to its end (L): the effective stroke."""
    m = LX["block_len"] / 2 + LX["end_margin"]                                            # 31.75
    return m, L - m


def lx_file_members(L):
    """Members of one actuator in the VENDOR FILE FRAME (axis along +x, rail x 56..56+L, motor beyond x < 0, rail bottom
    y = 0, up = +y, width along z). From cad/vendor/misumi_LX2005CG-B1-A2040-<L>.step when present (body with the
    bracket casting + cover strip -> 'rail'; adapter plate + screws -> 'plate'; table plate -> 'block'), else boxes of
    the same extents. The motor is always an envelope box on the plate. Returns (dict name -> Workplane, table centre x)."""
    if L in _LX_FILES:
        return _LX_FILES[L]
    fx0 = LX["file_rail_x0"]
    ms = LX["motor_sq"] / 2
    motor = box(-LX["plate_t"] - LX["motor_len"], -LX["plate_t"], LX["axis_h"] - ms, LX["axis_h"] + ms, -ms, ms)
    wp = vendor_step(f"misumi_LX2005CG-B1-A2040-{L}.step")
    if wp is not None:
        sol = wp.solids().vals()
        bx = lambda t: t.BoundingBox()
        table = [t for t in sol if bx(t).zmax > 25.0]                                   # the 52 wide table plate
        plate = [t for t in sol if bx(t).xmax < 10.0]                                    # adapter plate (x -13..0) + 4 screws
        body = [t for t in sol if t not in table and t not in plate]                    # body (rail + bracket casting), cover strip
        mk = lambda ts: cq.Workplane().add(cq.Compound.makeCompound(ts))
        tb = bx(table[0])
        m = dict(rail=mk(body), plate=mk(plate), block=mk(table), motor=motor)
        tc = (tb.xmin + tb.xmax) / 2
    else:
        w2, h = LX["rail_w"] / 2, LX["rail_h"]
        tc = fx0 + L / 2
        m = dict(rail=box(0.0, fx0 + L, 0.0, h, -w2, w2),
                 plate=box(-LX["plate_t"], 0.0, LX["axis_h"] - LX["plate_sq"] / 2, LX["axis_h"] + LX["plate_sq"] / 2, -LX["plate_sq"] / 2, LX["plate_sq"] / 2),
                 block=box(tc - LX["block_len"] / 2, tc + LX["block_len"] / 2, 6.0, LX["block_top"], -LX["block_w"] / 2, LX["block_w"] / 2),
                 motor=motor)
    _LX_FILES[L] = (m, tc)
    return _LX_FILES[L]


def _lx_place(L, rot, tr, c_file):
    """Members of the L actuator with the table centre moved to file x = c_file, rotated by [(axis, deg), ...] about the
    origin and translated by tr. Returns dict name -> shape (station frame)."""
    m, tc = lx_file_members(L)
    out = {}
    for n, s in m.items():
        w = s.translate((c_file - tc, 0, 0)) if n == "block" else s
        for axis, ang in rot:
            w = w.rotate((0, 0, 0), axis, ang)
        out[n] = w.translate(tr)
    return out


def lx_x(L, x1, cyx, zr, xc):
    """X actuator: rail X x1-L..x1 (nest end at x1), bottom face at Z zr, table centred at X xc, motor beyond -X.
    file (x, y, z) -> station (x + x0 - 56, cyx - z, zr + y)."""
    fx0 = LX["file_rail_x0"]
    x0 = x1 - L
    tx = x0 - fx0
    d = _lx_place(L, [((1, 0, 0), 90)], (tx, cyx, zr), xc - tx)
    lo, hi = lx_limits(L)
    d.update(c_lo=x0 + lo, c_hi=x0 + hi, x0=x0, x1=x1, motor_x=x0 - fx0 - LX["plate_t"] - LX["motor_len"])
    return d


def lx_y(L, y0, cx, zr, yc):
    """Y actuator: rail Y y0..y0+L at X cx, bottom face at Z zr, table centred at Y yc, motor beyond +Y.
    file (x, y, z) -> station (cx - z, y1 + 56 - x, zr + y)."""
    fx0 = LX["file_rail_x0"]
    y1 = y0 + L
    ty = y1 + fx0
    d = _lx_place(L, [((1, 0, 0), 90), ((0, 0, 1), -90)], (cx, ty, zr), ty - yc)
    lo, hi = lx_limits(L)
    d.update(c_lo=y0 + lo, c_hi=y0 + hi, y0=y0, y1=y1, motor_y=y1 + fx0 + LX["plate_t"] + LX["motor_len"])
    return d


def lx_z(L, z0, xl, cyx, zc):
    """Z actuator: rail Z z0..z0+L with its mounting face at X xl (table face at xl + 27 toward the nest), width along
    Y about cyx, table centred at Z zc, motor above the rail. file (x, y, z) -> station (xl + y, cyx - z, z0 + L + 56 - x)."""
    fx0 = LX["file_rail_x0"]
    tz = z0 + L + fx0
    d = _lx_place(L, [((0, 1, 0), 90), ((0, 0, 1), -90)], (xl, cyx, tz), tz - zc)
    lo, hi = lx_limits(L)
    d.update(c_lo=z0 + lo, c_hi=z0 + hi, top=tz + LX["plate_t"] + LX["motor_len"])
    return d


# ----------------------------------------------------------------------------
# Transport
# ----------------------------------------------------------------------------
# ----------------------------------------------------------------------------
# Mounting parts: the custom pieces between the actuators and everything else. Real parts with bolt patterns,
# exported as STEP + STL (printed in PPA-CF for the prototype, machined in 6061 after the trials; see
# docs/print_list.md). Hole sizes are tap-drill / press-fit for printing; ream or tap after printing.
# ----------------------------------------------------------------------------
M = dict(
    tap_m3=2.5, tap_m4=3.3,               # tap-drill holes for M3 / M4 (tap directly in PPA-CF, or open to 4.0 / 5.6 for heat-set inserts)
    m4_clr=4.5, m4_cbore=(8.0, 4.5),      # M4 clearance and counterbore (dia, depth) for SHCS
    dowel3=2.9, dowel4=3.9,               # press-fit dowel holes (ream to H7 after printing)
    flange_t=8.0, flange_w=60.0, y_flange_w=80.0,   # riser foot flanges: thickness, total width (X riser / Y riser)
    slot=(6.6, 14.0), slot_pitch=50.0,    # foot slots for M6 or 1/4-20 table bolts (25 mm or 1 in grid)
    deck_t=6.0,                           # tray deck: flat 6 mm plate (the tray bottom sits on its top face)
    tray_pin=(3.0, 10.0, 3.0),            # tray datum pins: dia 3 m6 dowel, 10 long, 3.0 proud of the deck top (below the tray's
                                          # 3.8 mm wall top); reamed dia 3 H7 through the deck; positions from tray.datum_pins()
    rib_len=40.0, rib_h=60.0, rib_t=10.0, # tower gusset rib on the -X side of the leg
    nanomax_grid=25.0, nanomax_hole=6.6,  # NanoMax riser plates: through holes on the 25 mm grid (M6 bolts through the stage slots)
)


def lx_base_along(L):
    """Base-hole positions along the rail measured from its far (non-motor) end, from the vendor STEP."""
    return [LX["base_first"][L] + k * LX["mount_pitch"] for k in range(LX["base_n"][L])]


def slot_x(xc_, yc_, z0, z1, w, ln):
    """Slot along X: width w (in Y), length ln (in X), centred at (xc_, yc_)."""
    return box(xc_ - ln / 2 + w / 2, xc_ + ln / 2 - w / 2, yc_ - w / 2, yc_ + w / 2, z0, z1) \
        .union(C.cyl_z(xc_ - ln / 2 + w / 2, yc_, z0, z1, w / 2)).union(C.cyl_z(xc_ + ln / 2 - w / 2, yc_, z0, z1, w / 2))


def slot_y(xc_, yc_, z0, z1, w, ln):
    return box(xc_ - w / 2, xc_ + w / 2, yc_ - ln / 2 + w / 2, yc_ + ln / 2 - w / 2, z0, z1) \
        .union(C.cyl_z(xc_, yc_ - ln / 2 + w / 2, z0, z1, w / 2)).union(C.cyl_z(xc_, yc_ + ln / 2 - w / 2, z0, z1, w / 2))


def x_riser_part(x0, x1, cyx, zr):
    """X riser bar: 40 wide body under the base rail from the table to zr, 60 wide x 8 foot flange with slots for the
    table bolts, M3 tap-drill holes on the LX20 base pattern and two dia 4 pin holes on the centre line."""
    L = S["lx_L"]["x"]
    w2, fw2, ft = LX["base_w"] / 2, M["flange_w"] / 2, M["flange_t"]
    r = box(x0, x1, cyx - w2, cyx + w2, table_z, zr).union(box(x0, x1, cyx - fw2, cyx + fw2, table_z, table_z + ft))
    for a in lx_base_along(L):
        for dy in (-LX["mount_row"], LX["mount_row"]):
            r = r.cut(C.cyl_z(x1 - a, cyx + dy, zr - 10.0, zr + 0.5, M["tap_m3"] / 2))
    for a in (lx_base_along(L)[0], lx_base_along(L)[-1]):
        r = r.cut(C.cyl_z(x1 - a, cyx, zr - 8.0, zr + 0.5, M["dowel4"] / 2))
    xs = x0 + 25.0
    while xs <= x1 - 25.0:
        for dy in (-(w2 + 5.0), w2 + 5.0):
            r = r.cut(slot_x(xs, cyx + dy, table_z - 0.5, table_z + ft + 0.5, *M["slot"]))
        xs += M["slot_pitch"]
    return r


def y_riser_part(y0, y1, cx, zr):
    """Y riser bar under the Y actuator: same construction along Y (foot flange 80 wide)."""
    L = S["lx_L"]["y"]
    w2, fw2, ft = LX["base_w"] / 2, M["y_flange_w"] / 2, M["flange_t"]
    r = box(cx - w2, cx + w2, y0, y1, table_z, zr).union(box(cx - fw2, cx + fw2, y0, y1, table_z, table_z + ft))
    for a in lx_base_along(L):
        for dx in (-LX["mount_row"], LX["mount_row"]):
            r = r.cut(C.cyl_z(cx + dx, y0 + a, zr - 10.0, zr + 0.5, M["tap_m3"] / 2))
    for a in (lx_base_along(L)[0], lx_base_along(L)[-1]):
        r = r.cut(C.cyl_z(cx, y0 + a, zr - 8.0, zr + 0.5, M["dowel4"] / 2))
    ys = y0 + 25.0
    while ys <= y1 - 25.0:
        for dx in (-(w2 + 10.0), w2 + 10.0):
            r = r.cut(slot_y(cx + dx, ys, table_z - 0.5, table_z + ft + 0.5, *M["slot"]))
        ys += M["slot_pitch"]
    return r


def tower_bracket_part(xc):
    """Angle bracket on the X table plate: 60 x 60 x 10 base (4 x M4 counterbored on the table's 20 x 45 pattern, 2 dowels),
    10 mm vertical leg on the +X side carrying the Z rail (M3 tap-drill holes on the LX20 base pattern, 2 pin holes),
    gusset rib behind the leg. Returns (solid, X of the leg's +X face)."""
    cyx, t, hw = S["x_axis_cy"], S["tower_t"], S["tower_w"] / 2
    xb_top = S["x_rail_z"] + LX["block_top"]
    z0, Lz = S["z_rail_z0"], S["lx_L"]["z"]
    xl = xc + hw
    base = box(xc - hw, xc + hw, cyx - hw, cyx + hw, xb_top, xb_top + t)
    leg = box(xl - t, xl, cyx - hw, cyx + hw, xb_top, z0 + Lz)
    rib = (cq.Workplane("XZ").polyline([(xl - t, xb_top + t), (xl - t - M["rib_len"], xb_top + t), (xl - t, xb_top + t + M["rib_h"])]).close()
           .extrude(M["rib_t"] / 2, both=True).translate((0, cyx, 0)))
    br = base.union(leg).union(rib)
    al, ac = LX["table_holes"]
    for dx in (-al / 2, al / 2):
        for dy in (-ac / 2, ac / 2):
            br = br.cut(C.cyl_z(xc + dx, cyx + dy, xb_top - 0.5, xb_top + t + 0.5, M["m4_clr"] / 2))
            br = br.cut(C.cyl_z(xc + dx, cyx + dy, xb_top + t - M["m4_cbore"][1], xb_top + t + 0.5, M["m4_cbore"][0] / 2))
    for dy in (-LX["table_dowel"][1] / 2, LX["table_dowel"][1] / 2):
        br = br.cut(C.cyl_z(xc, cyx + dy, xb_top - 0.5, xb_top + 6.0, M["dowel3"] / 2))
    for a in lx_base_along(Lz):
        for dy in (-LX["mount_row"], LX["mount_row"]):
            br = br.cut(C.cyl_x(cyx + dy, z0 + a, xl - 8.0, xl + 0.5, M["tap_m3"] / 2))
    for a in (lx_base_along(Lz)[0], lx_base_along(Lz)[-1]):
        br = br.cut(C.cyl_x(cyx, z0 + a, xl - 6.0, xl + 0.5, M["dowel4"] / 2))
    return br, xl


def x_axis(xc):
    """X actuator on its riser bar (table to S['x_rail_z']); nest end of the rail at S['x_rail_x1']. Returns dict."""
    cyx = S["x_axis_cy"]
    ax = lx_x(S["lx_L"]["x"], S["x_rail_x1"], cyx, S["x_rail_z"], xc)
    ax["riser"] = x_riser_part(ax["x0"], ax["x1"], cyx, S["x_rail_z"])         # under the base rail only: the motor overhangs
    return ax


def z_tower(xc, zc):
    """Tower on the X table at xc: the angle bracket and the Z actuator on its leg's +X face; Z table centred at zc.
    Returns (dict of parts, X of the Z table face)."""
    cyx = S["x_axis_cy"]
    z0, Lz = S["z_rail_z0"], S["lx_L"]["z"]
    br, xl = tower_bracket_part(xc)
    zax = lx_z(Lz, z0, xl, cyx, zc)
    parts = {"tower_bracket_6061": br, "z_axis_rail_lx20": zax["rail"], "z_axis_block": zax["block"],
             "z_axis_plate": zax["plate"], "z_axis_motor": zax["motor"]}
    S["_z_top"] = zax["top"]
    return parts, xl + LX["block_top"]


def arm(xf, zc, z_iface_top, gx):
    """One-piece arm: adapter block on the Z table face at X xf (33 deep, 4 x M4 counterbored from the outside on the
    table's 20 x 45 pattern, 2 dowels), 25 sq bar along +Y from the axis band to the die line with its bottom at
    z_iface_top + 8, 8 mm end plate over the gripper interface (gripper.IFACE: 4 x M4 tap-drill + 2 dowels) at die X gx.
    Returns (solid, members [block, bar, end plate])."""
    a, cyx, t = S["arm_sec"], S["x_axis_cy"], S["arm_plate_t"]
    ix0, ix1, iy0, iy1 = G.IFACE
    za = z_iface_top + 8
    bw = t + a                                                        # block depth = plate + bar, flush with the bar's +X face
    hl = LX["block_len"] / 2
    block = box(xf, xf + bw, cyx - LX["table_holes"][1] / 2 - 7.5, cyx + 20 + a, zc - hl, zc + hl)   # -Y wall 7.5 outside the counterbores
    bar_y = box(xf + t, xf + bw, cyx + 20, iy1, za, za + a)
    ep = box(gx + ix0, gx + ix1, iy0, iy1, z_iface_top, z_iface_top + 8)
    al, ac = LX["table_holes"]
    for dz in (-al / 2, al / 2):
        for dy in (-ac / 2, ac / 2):
            block = block.cut(C.cyl_x(cyx + dy, zc + dz, xf - 0.5, xf + bw + 0.5, M["m4_clr"] / 2))
            block = block.cut(C.cyl_x(cyx + dy, zc + dz, xf + t, xf + bw + 0.5, M["m4_cbore"][0] / 2))
    for dy in (-LX["table_dowel"][1] / 2, LX["table_dowel"][1] / 2):
        block = block.cut(C.cyl_x(cyx + dy, zc, xf - 0.5, xf + 6.0, M["dowel3"] / 2))
    if G.LAYOUT == "horizontal":
        pcx, pcy = G.cx - 2 + gx, G.H["m3_y"]
    else:
        pcx, pcy = G.cx - 8 + gx, G.die_cy
    pitch = G.P["iface_pitch"]
    for dx in (-pitch / 2, pitch / 2):
        for dy in (-pitch / 2, pitch / 2):
            ep = ep.cut(C.cyl_z(pcx + dx, pcy + dy, z_iface_top - 0.5, z_iface_top + 8.5, M["tap_m4"] / 2))
        ep = ep.cut(C.cyl_z(pcx + dx, pcy, z_iface_top - 0.5, z_iface_top + 8.5, M["dowel3"] / 2))
    return block.union(bar_y).union(ep), [block, bar_y, ep]


def deck_part(tray_x0, tray_x1, ty0, ty1, cx, yc, z0):
    """Tray deck on the Y table plate: flat 6 mm plate, tray footprint + 8 per side, 4 x M4 counterbored from the top on
    the table's 20 x 45 pattern, 2 dowels to the table, and two reamed dia 3 holes for the tray datum pins (round hole
    and slot in the tray's X rims, tray.datum_pins). The tray bottom sits on the deck top at z0 + 6; the pins stand 3 mm
    proud, inside the tray's 3.8 mm height, so nothing above the deck can meet them."""
    t = M["deck_t"]
    d = box(tray_x0 - 8, tray_x1 + 8, ty0 - 8, ty1 + 8, z0, z0 + t)
    al, ac = LX["table_holes"]
    for dy in (-al / 2, al / 2):
        for dx in (-ac / 2, ac / 2):
            d = d.cut(C.cyl_z(cx + dx, yc + dy, z0 - 0.5, z0 + t + 0.5, M["m4_clr"] / 2))
            d = d.cut(C.cyl_z(cx + dx, yc + dy, z0 + t - M["m4_cbore"][1], z0 + t + 0.5, M["m4_cbore"][0] / 2))
    for px, py in TM.datum_pins(tray_x0, tray_x1, yc):
        d = d.cut(C.cyl_z(px, py, z0 - 0.5, z0 + t + 0.5, M["tray_pin"][0] / 2))
    for dx in (-LX["table_dowel"][1] / 2, LX["table_dowel"][1] / 2):
        d = d.cut(C.cyl_z(cx + dx, yc, z0 - 0.5, z0 + 5.0, M["dowel3"] / 2))
    return d


def nanomax_riser_part(x0, x1, y0, y1, z0, z1):
    """25 mm riser plate under a NanoMax: dia 6.6 through holes on the 25 mm grid (M6 bolts pass through the stage's slots
    and the plate into the table)."""
    r = box(x0, x1, y0, y1, z0, z1)
    g = M["nanomax_grid"]; cxm, cym = (x0 + x1) / 2, (y0 + y1) / 2
    for i in (-1.5, -0.5, 0.5, 1.5):
        for j in (-1.5, -0.5, 0.5, 1.5):
            r = r.cut(C.cyl_z(cxm + i * g, cym + j * g, z0 - 0.5, z1 + 0.5, M["nanomax_hole"] / 2))
    return r


def y_stage_and_tray(active_col_x, active_row_y):
    """Y actuator under the tray deck on its riser, deck and the wafer tray (columns along X, rows along Y). The tray is
    positioned so that the pocket in column 'active_col_x' (die X) and the active row sits at Y = active_row_y.
    Returns (dict of parts, z_led, tray extents)."""
    x_first = S["tray_col0_x"]
    tray_x0, tray_x1, ty0, ty1 = TM.extents(x_first, active_row_y)
    tray_len_y = ty1 - ty0
    tray_cx = (tray_x0 + tray_x1) / 2
    Ly = S["lx_L"]["y"]
    zr = S["y_rail_z"]
    ay = lx_y(Ly, cy - Ly / 2, tray_cx, zr, active_row_y)              # rail centred on the pick line Y 3
    riser = y_riser_part(ay["y0"], ay["y1"], tray_cx, zr)
    deck_z0 = zr + LX["block_top"]
    deck = deck_part(tray_x0, tray_x1, ty0, ty1, tray_cx, active_row_y, deck_z0)
    tray, z_led, _ = TM.tray(x_first, active_row_y, deck_z0 + M["deck_t"])   # tray bottom on the deck top, on the two pins
    pd, pl, pp = M["tray_pin"]
    pins = [C.cyl_z(px, py, deck_z0 + M["deck_t"] + pp - pl, deck_z0 + M["deck_t"] + pp, pd / 2)
            for px, py in TM.datum_pins(tray_x0, tray_x1, active_row_y)]
    parts = {"y_axis_rail_lx20": ay["rail"], "y_axis_block": ay["block"], "y_axis_plate": ay["plate"], "y_axis_motor": ay["motor"],
             "y_stage_riser": riser, "tray_deck": deck, "wafer_tray": tray, "tray_pin_xm": pins[0], "tray_pin_xp": pins[1]}
    S["_y_limits"] = (ay["c_lo"], ay["c_hi"]); S["_y_motor_y"] = ay["motor_y"]
    return parts, z_led, (tray_x0, tray_x1, tray_len_y)


# ----------------------------------------------------------------------------
# Gripper module placed at (die X = gx, die bottom Z = gz)
# ----------------------------------------------------------------------------
def gripper_at(gx, gz, open_mm=0.0):
    parts = {
        "far_arm": G.far_arm(), "near_arm": G.near_arm(), "far_tip": G.far_tip_block(),
        "near_tip": G.near_tip_block(), "blade": G.blade(), "bracket": G.bracket(),
    }
    vend = G.actuator_vendor(open_mm)
    if vend is not None and "smc_MHZ2-6D.step" not in VENDOR_PLACED:
        VENDOR_PLACED.append("smc_MHZ2-6D.step")
    body, fn, ff = vend if vend is not None else G.actuator(open_mm)
    parts.update({"mhz2_body": body, "mhz2_fing_near": fn, "mhz2_fing_far": ff})
    return {k: v.translate((gx, 0, gz)) for k, v in parts.items()}


# ----------------------------------------------------------------------------
# Clearance checks (axis-aligned bounding boxes)
# ----------------------------------------------------------------------------
def main():
    # ---- derived transport numbers (all from the gripper interface, the tray drop and the actuator geometry) ----
    lo_c, _ = lx_limits(0)                                             # 31.75: block centre to rail end at the limit
    z_iface_top = G.body_z1 + G.P["top_t"]                             # bracket top plate top (Z 70 vertical / 26 horizontal)
    za = z_iface_top + 8                                               # arm bar bottom (on the 8 mm end plate)
    zc_nest = za + S["arm_sec"] / 2                                    # Z block centre at the nest: the bar is centred on the block
    S["z_rail_z0"] = zc_nest - S["tray_drop"] - S["end_margin"] - lo_c    # rail start so the tray set-down keeps the end margin
    S["x_rail_z"] = S["z_rail_z0"] - S["tower_t"] - LX["block_top"]    # X rail bottom: the Z rail starts on the tower base plate
    S["y_rail_z"] = -S["tray_drop"] - (TM.TR["floor_t"] + TM.TR["ledge_h"]) - M["deck_t"] - LX["block_top"]   # ledge top at -tray_drop
    xc_nest = G.IFACE[0] - (S["tower_w"] / 2 + LX["block_top"] + S["arm_plate_t"])   # arm bar starts at the adapter plate
    S["xc_nest"] = xc_nest
    S["x_rail_x1"] = xc_nest + S["push_x"] + lo_c + S["end_margin"]    # rail's nest end: push-to-stop stays inside the travel

    # ---- static ----
    static = {}
    static["optical_table"] = table()
    for n, s in nest().items(): static[n] = s
    static["nest_tec"] = S["_nest_tec"]; static["nest_cage_semitron"] = S["_nest_cage"]
    for name, s in nanomax(-1) + nanomax(+1): static[name] = s
    for name, s in microscope(): static[name] = s
    xax = x_axis(xc_nest)
    static["x_axis_rail_lx20"] = xax["rail"]; static["x_axis_plate"] = xax["plate"]; static["x_axis_motor"] = xax["motor"]
    static["x_axis_riser"] = xax["riser"]
    static["die_at_nest"] = G.die()
    yparts, z_led, tray_ext = y_stage_and_tray(S["tray_col0_x"], cy)
    for n, s in yparts.items(): static[n] = s
    stick, deck = yparts["wafer_tray"], yparts["tray_deck"]

    # ---- moving, at NEST ----
    tower, xf = z_tower(xc_nest, zc_nest)
    arm_u, arm_parts = arm(xf, zc_nest, z_iface_top, 0.0)
    moving_nest = {"x_axis_block": xax["block"]}
    moving_nest.update(tower)
    moving_nest["arm_6061"] = arm_u
    tower_parts = list(tower.values())
    grip_nest = gripper_at(0.0, 0.0)

    # ---- moving, at the FARTHEST tray column (second configuration; worst case for travel and the tower) ----
    far_col_x = S["tray_col0_x"] - (S["tray_cols"] - 1) * S["tray_col_pitch"]
    S["stick_x"] = far_col_x
    xc2 = xc_nest + far_col_x
    gz2 = z_led                                        # die bottom on the tray ledges (-tray_drop)
    xblock2 = lx_x(S["lx_L"]["x"], S["x_rail_x1"], S["x_axis_cy"], S["x_rail_z"], xc2)["block"]
    tower2, xf2 = z_tower(xc2, zc_nest + gz2)
    arm2_u, arm2_parts = arm(xf2, zc_nest + gz2, z_iface_top + gz2, far_col_x)
    tower2_parts = list(tower2.values())
    grip_stick = gripper_at(far_col_x, gz2, open_mm=1.5)

    # ---- custom mounting parts: STEP + STL per part (the print list is docs/print_list.md) ----
    sfx = G.SFX
    C.export_part(arm_u, DIRS, f"arm_6061{sfx}")                                  # depends on the gripper layout
    C.export_part(xax["riser"], DIRS, f"x_axis_riser_6061{sfx}")                  # its height follows the arm level
    if not sfx:
        C.export_part(tower["tower_bracket_6061"], DIRS, "tower_bracket_6061")
        C.export_part(yparts["y_stage_riser"], DIRS, "y_axis_riser_6061")
        C.export_part(yparts["tray_deck"], DIRS, "tray_deck_6061")
        C.export_part(static["nanomax_riser_in"], DIRS, "nanomax_riser_6061")

    # ---- checks ----
    Lx, Ly, Lz = S["lx_L"]["x"], S["lx_L"]["y"], S["lx_L"]["z"]
    zlim = lx_limits(Lz); zlo, zhi = S["z_rail_z0"] + zlim[0], S["z_rail_z0"] + zlim[1]
    ylo, yhi = S["_y_limits"]
    rep = []
    rep.append(f"table plane Z = {table_z:.1f} (die bottom = 0). Nest die top at {die_top}; fiber axis at {die_top} via holder {S['holder_axis_above_deck']} above NanoMax deck")
    zl = S["_nest_levels"]
    rep.append(f"NanoMax on {S['nanomax_riser']:.0f} mm risers; X actuator riser {S['x_rail_z'] - table_z:.1f} tall (rail bottom Z {S['x_rail_z']:.1f}); "
               f"Y actuator riser {S['y_rail_z'] - table_z:.1f} tall (rail bottom Z {S['y_rail_z']:.1f})")
    rep.append(f"die stage stack: KB1X1 top {zl['kb_top']:.1f} / KXC04015-C {zl['kxc_bottom']:.1f}..{zl['kxc_top']:.1f} / spacer / RMPG40W-N {zl['rot_bottom']:.1f}..{zl['rot_top']:.1f} "
               f"/ riser to the cage plate at {NM.N['cage'][4]:.1f}; X stage travel +/-{NM.N['kxc']['travel'] / 2:.1f}, stepping +/-{NM.N['stage_step_used']:.0f}; "
               f"exchange at stage HOME only (fence)")
    rep.append(f"wafer tray: {S['tray_cols']} columns x {S['tray_rows']} rows = {S['tray_cols']*S['tray_rows']} pockets, "
               f"{tray_ext[1]-tray_ext[0]:.0f} x {tray_ext[2]:.0f} mm; columns at die X {S['tray_col0_x']:.0f} .. {far_col_x:.0f} (pitch {S['tray_col_pitch']}); "
               f"ledges {abs(z_led):.1f} below the chuck pad")
    rep.append(f"transport: 3 x MISUMI LX2005CG-B1 (cover, low-particulate grease, lead 5, {LX['repeat']*1000:.0f} um repeatability, {LX['v_max']:.0f} mm/s screw-rated; ~200 mm/s with a 42 sq stepper)")
    x_used = abs(far_col_x) + S["push_x"]
    rep.append(f"  X: L {Lx} (stroke {LX['stroke'][Lx]}), rail X {xax['x0']:.0f}..{xax['x1']:.0f} at Y {S['x_axis_cy']:.0f}, motor to X {xax['motor_x']:.0f}; "
               f"block centre nest {xc_nest:.1f} (+{S['push_x']} push) -> far column {xc2:.1f}: used {x_used:.1f}; "
               f"limits {xax['c_lo']:.1f}..{xax['c_hi']:.1f} -> margins {xc2 - xax['c_lo']:.1f} / {xax['c_hi'] - xc_nest - S['push_x']:.1f}"
               f"{'  OK ' if xc2 >= xax['c_lo'] and xc_nest + S['push_x'] <= xax['c_hi'] else '  ** OUT OF TRAVEL **'}")
    y_used = (S["tray_rows"] - 1) * S["tray_row_pitch"]
    rep.append(f"  Y: L {Ly} (stroke {LX['stroke'][Ly]}), rail Y {cy - Ly / 2:.0f}..{cy + Ly / 2:.0f} at X {(tray_ext[0] + tray_ext[1]) / 2:.0f}, motor toward +Y to Y {S['_y_motor_y']:.0f}; "
               f"rows +/-{y_used / 2:.2f} about Y {cy:.0f}: used {y_used:.1f}; limits {ylo:.1f}..{yhi:.1f} -> margin {yhi - cy - y_used / 2:.1f}"
               f"{'  OK ' if cy - y_used / 2 >= ylo and cy + y_used / 2 <= yhi else '  ** OUT OF TRAVEL **'}")
    z_used = S["tray_drop"] + 8.0
    rep.append(f"  Z: L {Lz} (stroke {LX['stroke'][Lz]}), rail Z {S['z_rail_z0']:.1f}..{S['z_rail_z0'] + Lz:.1f}, motor up to Z {S['_z_top']:.0f}; "
               f"block centre nest {zc_nest:.1f}, +8 lift, tray {zc_nest + gz2:.1f}: used {z_used:.1f}; limits {zlo:.1f}..{zhi:.1f} -> margins {zc_nest + gz2 - zlo:.1f} / {zhi - zc_nest - 8:.1f}"
               f"{'  OK ' if zc_nest + gz2 >= zlo and zc_nest + 8 <= zhi else '  ** OUT OF TRAVEL **'}")
    lever = (zc_nest - (S["x_rail_z"] + LX["block_top"])) / 1000.0
    ma = S["tower_mass"] * 9.81 * lever
    mc = 0.45 * 9.81 * (cy - S["x_axis_cy"]) / 1000.0
    rep.append(f"  X block moment: tower {S['tower_mass']} kg at {lever * 1000:.0f} mm above the block -> Ma {ma:.2f} N.m of {LX['m_a']:.0f} allowable; "
               f"arm + gripper 0.45 kg at {cy - S['x_axis_cy']:.0f} mm -> Mc {mc:.2f} N.m of {LX['m_c']:.0f}{'  OK ' if ma < LX['m_a'] / 5 and mc < LX['m_c'] / 5 else '  ** CHECK **'}")
    rep.append(f"  exchange time: X {abs(far_col_x):.0f} mm at 200 mm/s with 25 mm ramps ~{abs(far_col_x) / 200 + 0.3:.1f} s each way; Z moves 8 / 20 mm at 50 mm/s")
    pairs = [
        ("gripper far_arm @nest", grip_nest["far_arm"], "objective", static["objective"]),
        ("gripper near_arm @nest", grip_nest["near_arm"], "objective", static["objective"]),
        ("gripper bracket @nest", grip_nest["bracket"], "microscope_tube", static["microscope_tube"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "microscope_tube", static["microscope_tube"]),
        ("gripper far_arm @nest", grip_nest["far_arm"], "microscope_column", static["microscope_column"]),
        ("gripper near_arm @nest", grip_nest["near_arm"], "fiber_holder_in", static["fiber_holder_in"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_holder_in", static["fiber_holder_in"]),
        ("nest_riser (neck/wide)", S["_nest_riser_parts"], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("nest_riser (neck/wide)", S["_nest_riser_parts"], "fiber_holder_out (per member)", S["_holder_parts_out"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "fiber_holder_out (per member)", S["_holder_parts_out"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "nanomax300_in", static["nanomax300_in"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "nanomax300_out", static["nanomax300_out"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "x_axis_riser", xax["riser"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "x_axis_rail_lx20", xax["rail"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "y_axis_rail_lx20", yparts["y_axis_rail_lx20"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "y_axis_motor", yparts["y_axis_motor"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "y_stage_riser", yparts["y_stage_riser"]),
        ("die stage stack (per member)", S["_nest_stack_parts"], "gripper @nest (per member)", list(grip_nest.values())),
        ("nest moving @-7.5 (per member)", [v.translate((-7.5, 0, 0)) for v in S["_nest_moving"].values()], "nanomax300_in", static["nanomax300_in"]),
        ("nest moving @+7.5 (per member)", [v.translate((7.5, 0, 0)) for v in S["_nest_moving"].values()], "nanomax300_out", static["nanomax300_out"]),
        ("nest moving @-7.5 (per member)", [v.translate((-7.5, 0, 0)) for v in S["_nest_moving"].values()], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("nest moving @+7.5 (per member)", [v.translate((7.5, 0, 0)) for v in S["_nest_moving"].values()], "fiber_holder_out (per member)", S["_holder_parts_out"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("nest_chuck", static["nest_chuck_copper"], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("nest_chuck", static["nest_chuck_copper"], "fiber_holder_in", static["fiber_holder_in"]),
        ("gripper near_arm @nest", grip_nest["near_arm"], "fiber_holder_out", static["fiber_holder_out"]),
        ("gripper far_arm @nest", grip_nest["far_arm"], "fiber_holder_in", static["fiber_holder_in"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_holder_out", static["fiber_holder_out"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_in", static["fiber_in"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_out", static["fiber_out"]),
        ("gripper far_arm @nest", grip_nest["far_arm"], "fiber_holder_out", static["fiber_holder_out"]),
        ("gripper bracket @nest", grip_nest["bracket"], "fiber_holder_in", static["fiber_holder_in"]),
        ("gripper bracket @nest", grip_nest["bracket"], "fiber_holder_out", static["fiber_holder_out"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "fiber_holder_in", static["fiber_holder_in"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "fiber_holder_out", static["fiber_holder_out"]),
        ("arm @nest (per member)", arm_parts, "microscope_tube", static["microscope_tube"]),
        ("arm @nest (per member)", arm_parts, "nanomax300_in", static["nanomax300_in"]),
        ("arm @nest (per member)", arm_parts, "fiber_holder_in", static["fiber_holder_in"]),
        ("arm @nest (per member)", arm_parts, "fiber_holder_out", static["fiber_holder_out"]),
        ("arm @nest (per member)", arm_parts, "x_axis_rail_lx20", xax["rail"]),
        ("arm @nest (per member)", arm_parts, "z_axis_motor @nest", tower["z_axis_motor"]),
        ("arm @nest (per member)", arm_parts, "z_axis_plate @nest", tower["z_axis_plate"]),
        ("arm @nest (per member)", arm_parts, "tray_deck", deck),
        ("tower @nest (per member)", tower_parts, "nanomax300_in", static["nanomax300_in"]),
        ("tower @nest (per member)", tower_parts, "fiber_holder_in", static["fiber_holder_in"]),
        ("tower @nest (per member)", tower_parts, "x_axis_rail_lx20", xax["rail"]),
        ("tower @nest (per member)", tower_parts, "tray_deck", deck),
        ("tower @nest (per member)", tower_parts, "wafer_tray", stick),
        ("tower @nest (per member)", tower_parts, "microscope_arm", static["microscope_arm"]),
        ("x_axis_block @nest", xax["block"], "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_rail_lx20", xax["rail"], "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_rail_lx20", xax["rail"], "nanomax_riser_in", static["nanomax_riser_in"]),
        ("x_axis_rail_lx20", xax["rail"], "y_axis_rail_lx20", yparts["y_axis_rail_lx20"]),
        ("x_axis_rail_lx20", xax["rail"], "y_stage_riser", yparts["y_stage_riser"]),
        ("x_axis_rail_lx20", xax["rail"], "deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0))),
        ("x_axis_rail_lx20", xax["rail"], "tray @row 0 (Y-48.75)", stick.translate((0, -48.75, 0))),
        ("x_axis_riser", xax["riser"], "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_riser", xax["riser"], "nanomax_riser_in", static["nanomax_riser_in"]),
        ("x_axis_riser", xax["riser"], "y_stage_riser", yparts["y_stage_riser"]),
        ("x_axis_riser", xax["riser"], "y_axis_rail_lx20", yparts["y_axis_rail_lx20"]),
        ("x_axis_riser", xax["riser"], "deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0))),
        ("x_axis_motor", xax["motor"], "y_stage_riser", yparts["y_stage_riser"]),
        ("x_axis_plate", xax["plate"], "optical_table", static["optical_table"]),
        ("y_axis_motor", yparts["y_axis_motor"], "nanomax300_out", static["nanomax300_out"]),
        ("y_axis_motor", yparts["y_axis_motor"], "nanomax_riser_out", static["nanomax_riser_out"]),
        ("y_axis_plate", yparts["y_axis_plate"], "nanomax_riser_out", static["nanomax_riser_out"]),
        ("y_axis_rail_lx20", yparts["y_axis_rail_lx20"], "nanomax_riser_in", static["nanomax_riser_in"]),
        ("y_stage_riser", yparts["y_stage_riser"], "nanomax_riser_in", static["nanomax_riser_in"]),
        ("y_stage_riser", yparts["y_stage_riser"], "nanomax_riser_out", static["nanomax_riser_out"]),
        ("tray_deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0)), "nanomax300_in", static["nanomax300_in"]),
        ("tray_deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0)), "nanomax_riser_in", static["nanomax_riser_in"]),
        ("tray_deck @row 13 (Y+48.75)", deck.translate((0, 48.75, 0)), "nanomax300_out", static["nanomax300_out"]),
        ("tray_deck @row 13 (Y+48.75)", deck.translate((0, 48.75, 0)), "nanomax_riser_out", static["nanomax_riser_out"]),
        ("wafer_tray @row 13 (Y+48.75)", stick.translate((0, 48.75, 0)), "nanomax300_out", static["nanomax300_out"]),
        ("tower @far column (per member)", tower2_parts, "y_axis_rail_lx20", yparts["y_axis_rail_lx20"]),
        ("tower @far column (per member)", tower2_parts, "y_stage_riser", yparts["y_stage_riser"]),
        ("tower @far column (per member)", tower2_parts, "tray_deck", deck),
        ("tower @far column (per member)", tower2_parts, "wafer_tray", stick),
        ("tower @far column (per member)", tower2_parts, "x_axis_plate", xax["plate"]),
        ("tower @far column (per member)", tower2_parts, "x_axis_motor", xax["motor"]),
        ("x_axis_block @far column", xblock2, "x_axis_plate", xax["plate"]),
        ("arm @far column (per member)", arm2_parts, "wafer_tray", stick),
        ("arm @far column (per member)", arm2_parts, "tray_deck", deck),
        ("arm @far column (per member)", arm2_parts, "x_axis_rail_lx20", xax["rail"]),
        ("arm @far column (per member)", arm2_parts, "x_axis_plate", xax["plate"]),
        ("arm @far column (per member)", arm2_parts, "x_axis_motor", xax["motor"]),
        ("arm @far column (per member)", arm2_parts, "y_axis_motor", yparts["y_axis_motor"]),
        ("gripper mhz2_body @far col", grip_stick["mhz2_body"], "wafer_tray", stick),
        ("tray pins (per member)", [yparts["tray_pin_xm"], yparts["tray_pin_xp"]], "gripper near_arm @far col", grip_stick["near_arm"]),
        ("tray pins (per member)", [yparts["tray_pin_xm"], yparts["tray_pin_xp"]], "gripper near_tip @far col", grip_stick["near_tip"]),
        ("tray pins (per member)", [yparts["tray_pin_xm"], yparts["tray_pin_xp"]], "gripper blade @far col", grip_stick["blade"]),
        ("tray pins (per member)", [yparts["tray_pin_xm"], yparts["tray_pin_xp"]], "gripper mhz2_body @far col", grip_stick["mhz2_body"]),
        ("tray pins (per member)", [yparts["tray_pin_xm"], yparts["tray_pin_xp"]], "arm @far column (per member)", arm2_parts),
        ("gripper bracket @far col", grip_stick["bracket"], "wafer_tray", stick),
        ("gripper far_arm @far col", grip_stick["far_arm"], "wafer_tray", stick),
        ("gripper near_arm @far col", grip_stick["near_arm"], "wafer_tray", stick),
        ("gripper mhz2_body @far col", grip_stick["mhz2_body"], "x_axis_rail_lx20", xax["rail"]),
        ("gripper mhz2_body @far col", grip_stick["mhz2_body"], "y_axis_motor", yparts["y_axis_motor"]),
        ("gripper bracket @far col", grip_stick["bracket"], "y_axis_motor", yparts["y_axis_motor"]),
    ]
    rep.append("")
    rep.append("clearances vs boxes (AABB separation, mm; negative = overlap):")
    for an, a, bn, b in pairs:
        if bn in ("objective", "microscope_tube", "microscope_column"):
            continue
        gp = gap_any(a, b)
        flag = "  OK " if gp > 2 else ("  TIGHT" if gp > 0 else "  ** OVERLAP **")
        rep.append(f"  {an:32s} vs {bn:26s}: {gp:7.1f}{flag}")
    rep.append("")
    rep.append("clearances vs microscope cylinders (radial or vertical, mm):")
    z_obj0 = die_top + S["obj_wd"]
    cyls = {
        "objective (dia 34)": ((5, cy), S["obj_dia"] / 2, z_obj0, z_obj0 + S["obj_len"]),
        "microscope_tube (dia 40)": ((5, cy), S["tube_dia"] / 2, z_obj0 + S["obj_len"], z_obj0 + S["obj_len"] + S["tube_len"]),
        "microscope_column (dia 40)": ((S["column_x"], cy), S["column_dia"] / 2, table_z, S["column_top"]),
    }
    lowcut = box(-200, 200, -100, 100, -50, G.bar_z1 + 0.01)          # bars only (under the objective)
    incut = box(-10, 200, -100, 100, G.bar_z1 + 0.01, 300)             # heads near the die, above bar height
    outcut = box(-200, -10, -100, 100, G.bar_z1 + 0.01, 300)           # root plates / transitions, outboard
    for sn_, sv_ in (("die stage: RMPG40W motor", static["nest_rmpg40w_motor"]), ("die stage: RMPG40W cable", static["nest_rmpg40w_cable"]),
                     ("die stage: KXC motor", static["nest_kxc04015_motor"]), ("die stage: KXC knob", static["nest_kxc04015_knob"])):
        g_ = gap_cyl(bb(sv_), (S["column_x"], cy), S["column_dia"] / 2, table_z, S["column_top"])
        rep.append(f"  {sn_:24s} vs {'microscope_column (dia 40)':26s}: {g_:7.1f}{'  OK ' if g_ > 2 else ('  TIGHT' if g_ > 0 else '  ** OVERLAP **')}")
    for pn, part in [("far_arm bars @nest", grip_nest["far_arm"].intersect(lowcut)), ("far_arm root @nest", grip_nest["far_arm"].intersect(outcut)),
                     ("near_arm bars @nest", grip_nest["near_arm"].intersect(lowcut)), ("near_arm head @nest", grip_nest["near_arm"].intersect(incut)),
                     ("near_arm root @nest", grip_nest["near_arm"].intersect(outcut)),
                     ("far_tip @nest", grip_nest["far_tip"]),
                     ("bracket @nest", grip_nest["bracket"]), ("mhz2_body @nest", grip_nest["mhz2_body"]), ("arm bar @nest", arm_parts[1]),
                     ("arm end plate @nest", arm_parts[2]), ("z_axis_motor @nest", tower["z_axis_motor"])]:
        for cn, (axy, r, z0, z1) in cyls.items():
            gp = gap_cyl(bb(part), axy, r, z0, z1)
            flag = "  OK " if gp > 2 else ("  TIGHT" if gp > 0 else "  ** OVERLAP **")
            rep.append(f"  {pn:24s} vs {cn:26s}: {gp:7.1f}{flag}")
    # swept volumes between nest and stick, after the 8 mm approach lift: (a) gripper module band, (b) arm band
    lift = 8.0
    def sweep(b):                                                     # AABB swept from the nest to the farthest column, lifted
        return (S["stick_x"] + b[0], b[1], b[2], b[3], b[4] + lift, b[5] + lift)
    g_sweeps = [sweep(bb(v)) for v in grip_nest.values()]              # per part (no union-box conservatism)
    a_sweeps = [sweep(bb(pp)) for pp in arm_parts]
    rep.append("")
    rep.append("swept volumes nest <-> tray (after the 8 mm lift; per member) vs static objects:")
    statics = ["nanomax300_in", "fiber_holder_in", "fiber_in", "nanomax300_out", "fiber_holder_out", "nest_riser_6061", "nest_kxc04015_motor", "nest_rmpg40w_motor",
               "x_axis_rail_lx20", "x_axis_riser", "x_axis_motor", "y_axis_motor", "y_axis_plate", "microscope_arm"]
    for n in statics:
        g1 = min(gap(g, bb(static[n])) for g in g_sweeps); g2 = min(gap(g, bb(static[n])) for g in a_sweeps)
        rep.append(f"  gripper band vs {n:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    for cn, (axy, r, z0, z1) in cyls.items():
        g1 = min(gap_cyl(g, axy, r, z0, z1) for g in g_sweeps); g2 = min(gap_cyl(g, axy, r, z0, z1) for g in a_sweeps)
        rep.append(f"  gripper band vs {cn:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    rep.append("")
    rep.append("the gripper band sweep necessarily passes under the objective (that is the exchange); its clearance there is the")
    rep.append("bar height check in cad/gripper/checks.txt (tallest part 9.0 mm above die top vs WD).")
    suffix = G.SFX
    placed = sorted(set(VENDOR_PLACED))
    rep.insert(0, ("VENDOR MODELS placed: " + ", ".join(placed) + "; envelopes for everything else (the microscope and the three LX20 "
                   "actuators until their STEP is supplied). AABBs include micrometers, motors, cables and switches.") if placed else
               "VENDOR MODELS: none present in cad/vendor (envelope build; see cad/vendor/README.md)")
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(DIRS["comp"], f"checks{suffix}.txt"), "w") as f: f.write(txt + "\n")

    # ---- assembly export (nest configuration + ghost of stick configuration) ----
    assy = cq.Assembly(name="test_station")
    al, dark, blue, moving, amber = (0.60, 0.63, 0.68), (0.20, 0.20, 0.22), (0.56, 0.69, 0.82), (0.18, 0.31, 0.44), (0.85, 0.81, 0.68)
    col = {
        "optical_table": (0.86, 0.88, 0.90), "nest_kb1x1": (0.45, 0.48, 0.52), "nest_riser_6061": al, "nest_chuck_copper": (0.72, 0.45, 0.20), "nest_tec": (0.85, 0.85, 0.88), "nest_cage_semitron": (0.16, 0.16, 0.18),
        "nest_adapter_kb_kxc": al, "nest_spacer_kxc_rot": al, "nest_rmpg40w_body": dark, "nest_rmpg40w_table": (0.25, 0.25, 0.27),
        "nest_rmpg40w_worm": dark, "nest_rmpg40w_motor": (0.30, 0.30, 0.32), "nest_rmpg40w_cable": (0.30, 0.30, 0.32), "nest_rmpg40w_bolts": (0.45, 0.48, 0.52),
        "nanomax_riser_in": al, "nanomax_riser_out": al, "y_stage_riser": al, "x_axis_riser": al, "tray_deck": al, "tray_pin_xm": (0.45, 0.48, 0.52), "tray_pin_xp": (0.45, 0.48, 0.52),
        "nest_kxc04015_base": dark, "nest_kxc04015_table": (0.25, 0.25, 0.27), "nest_kxc04015_coupling": dark, "nest_kxc04015_motor": (0.30, 0.30, 0.32), "nest_kxc04015_knob": dark,
        "nanomax300_in": blue, "nanomax300_out": blue, "fiber_holder_in": (0.36, 0.40, 0.44),
        "fiber_holder_out": (0.36, 0.40, 0.44), "fiber_in": (0.94, 0.82, 0.50), "fiber_out": (0.94, 0.82, 0.50),
        "objective": (0.20, 0.23, 0.27), "microscope_tube": (0.25, 0.28, 0.32), "microscope_arm": (0.77, 0.79, 0.82), "microscope_column": (0.77, 0.79, 0.82),
        "x_axis_rail_lx20": dark, "x_axis_plate": dark, "x_axis_motor": (0.30, 0.30, 0.32), "x_axis_block": moving, "die_at_nest": (0.81, 0.89, 0.97),
        "y_axis_rail_lx20": dark, "y_axis_block": moving, "y_axis_plate": dark, "y_axis_motor": (0.30, 0.30, 0.32), "wafer_tray": amber,
        "tower_bracket_6061": moving, "z_axis_rail_lx20": dark, "z_axis_block": moving, "z_axis_plate": dark, "z_axis_motor": (0.30, 0.30, 0.32),
        "arm_6061": moving,
    }
    for n, s in static.items(): assy.add(s, name=n, color=cq.Color(*col.get(n, al), 1.0))
    for n, s in moving_nest.items(): assy.add(s, name=n, color=cq.Color(*col.get(n, moving), 1.0))
    for n, s in grip_nest.items(): assy.add(s, name=f"gripper_{n}", color=cq.Color(0.25, 0.25, 0.27, 1.0))
    ghost = {"x_axis_block_at_far_col": xblock2, "arm_at_far_col": arm2_u}
    ghost.update({f"{n}_at_far_col": s for n, s in tower2.items()})
    for n, s in ghost.items():
        assy.add(s, name=n, color=cq.Color(0.18, 0.31, 0.44, 0.25))
    for n, s in grip_stick.items(): assy.add(s, name=f"gripper_at_far_col_{n}", color=cq.Color(0.25, 0.25, 0.27, 0.25))
    assy.add(keepout(), name="objective_keepout", color=cq.Color(0.85, 0.64, 0.25, 0.25))
    assy.save(os.path.join(DIRS["STEP"], f"station_assembly{suffix}.step"))
    print("wrote station files to", DIRS["comp"])


if __name__ == "__main__":
    main()

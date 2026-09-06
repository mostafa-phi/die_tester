"""
Full test-station assembly: nest, gripper module, bench-level Cartesian transport
(X axis + Z axis + arm, Y stage under the stick), two NanoMax 300 fiber stages with
holders, microscope column/objective, optical table. Frame, die and contact rules: cad/common
(X = die long axis, Y = optical axis, Z up, Z = 0 = die bottom at the nest). The gripper, the nest and
the tray are imported from their own packages (cad/gripper, cad/nest, cad/tray); this file only
places them and adds the transport, the fiber stages and the microscope.

Bought parts: vendor STEP from cad/vendor (git-ignored, see vendor/fetch_vendor_step.sh) with --vendor,
otherwise envelopes:
  - Velmex BiSlide MN10 class: 102 wide x 64 tall body; 102 x 102 x 10 carriage plate
  - Thorlabs NanoMax 300: 112 x 112 footprint, 62.5 deck height, 4 mm travel
  - Microscope: objective barrel dia 34, tube dia 40, column post dia 40 behind (+X)  (always an envelope)

Run: python cad/station/model.py [--vendor] [--horizontal]
     -> STEP/station_assembly[_vendor][_h].step (git-ignored, large) + checks[_vendor][_h].txt
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
USE_VENDOR = "--vendor" in sys.argv          # place manufacturer STEP models where they exist


def vendor_step(fname):
    """Manufacturer STEP from cad/vendor/, or None (caller falls back to its envelope)."""
    p = C.vendor_path(fname)
    if USE_VENDOR and os.path.exists(p):
        print(f"[vendor] {fname}")
        return cq.importers.importStep(p)
    return None

# ----------------------------------------------------------------------------
# Station parameters
# ----------------------------------------------------------------------------
S = dict(
    # fiber side
    holder_axis_above_deck=20.0,   # fiber axis height above the NanoMax top platform (holder-dependent; measure)
    nanomax_w=112.0, nanomax_h=62.5, nanomax_platform_h=4.0, nanomax_gap_y=45.0,   # inner face to facet
    # fiber holder envelope: single source common.FIBER (shared with the nest)
    fiber_protrusion=C.FIBER["protrusion"], holder_w=C.FIBER["holder_w"], holder_zb=C.FIBER["holder_zb"],
    holder_zt=C.FIBER["holder_zt"], holder_len=C.FIBER["holder_len"],
    # microscope (behind the nest, +X, as in the bench photo); WD and diameters from common
    obj_wd=C.OBJ_WD, obj_dia=C.OBJ_DIA, obj_len=40.0, tube_dia=C.TUBE_DIA, tube_len=60.0,
    column_x=80.0, column_dia=40.0, column_top=260.0,
    # transport (Velmex BiSlide envelope)
    axis_w=102.0, axis_h=64.0, car_t=10.0, car_len=102.0,
    x_travel=300.0, x_body_len=380.0, z_body_len=150.0, y_travel=105.0, y_body_len=205.0,
    x_axis_cy=-100.0,              # X axis centre-line in Y (beside the input NanoMax, outside the fiber corridor)
    x_axis_riser=86.0,             # X axis on a riser ABOVE the NanoMax envelope and above the tray deck that passes under it (body bottom Z 0)
    xc_nest=-140.0,                # X-carriage centre when the gripper is at the nest (arm reach 140; keeps the real Velmex slider inside its travel)
    arm_sec=25.0,                  # square arm bar
    arm_cross_z=82.0,              # underside of the arm bars where they cross the X-axis band: X slider top 65.1
                                   # + 11.9 far-column drop + 5 mm margin. A lower bracket gets a vertical drop bar.
    cleat_shift=120.0,             # Velmex cleats are clamps, free along the body: moved 120 mm toward the motor end
                                   # (file z 247..317 -> 367..437) so the horizontal gripper body clears them at the far columns
    # wafer tray: geometry and column positions live in cad/tray (TM.TR)
    tray_cols=TM.TR["cols"], tray_rows=TM.TR["rows"], tray_col_pitch=TM.TR["col_pitch"], tray_row_pitch=TM.TR["row_pitch"],
    tray_col0_x=TM.TR["col0_x"],   # die X of the first (nearest) column; last column at -150 - 7*16 = -262
)

die_top = G.die_top
table_z = die_top - S["holder_axis_above_deck"] - S["nanomax_h"] - S["nanomax_platform_h"]   # -86.5
cy = G.die_cy                                                                                # 3.0
S["table_z"] = table_z


# ----------------------------------------------------------------------------
# Static structure
# ----------------------------------------------------------------------------
def table():
    return box(-720, 220, -280, 280, table_z - 12, table_z)


def nest():
    """Nest (cad/nest): copper chuck + Semitron cage + T-riser with the TEC, on a KB1X1 kinematic base."""
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
        kb = box(-14, 24, -16, 22, table_z, table_z + 20)                     # kinematic base envelope
        kb_top = table_z + 20
    riser = NM.riser(table_z, kb_top)
    ins = NM.chuck()
    S["_nest_tec"] = NM.tec()
    S["_nest_cage"] = NM.cage(); S["_nest_cage_parts"] = NM.cage_parts()
    nx0, nx1, ny0, ny1 = NM.N["neck"]; wx0, wx1, wy0, wy1 = NM.N["wide"]
    S["_nest_riser_parts"] = [box(nx0, nx1, ny0, ny1, NM.N["neck_bottom"], NM.N["cage"][4]),      # neck (cage width in Y)
                              box(wx0, wx1, wy0, wy1, kb_top, NM.N["wide_top"]), kb]              # wide body below the holders, base
    return kb.union(riser), ins


def nanomax(side):
    """side=-1 input (Y<0), +1 output (Y>6). Returns list of (name, shape)."""
    g = S["nanomax_gap_y"]
    if side < 0:
        y0, y1 = -(g + S["nanomax_w"]), -g
    else:
        y0, y1 = G.P["die_wid"] + g, G.P["die_wid"] + g + S["nanomax_w"]
    x0, x1 = 5 - S["nanomax_w"] / 2, 5 + S["nanomax_w"] / 2
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
            stage = stage.translate((5 - 42.0, y1 - 115.5, table_z))          # inner (body) face -> Y -45, base centred on the die
        else:
            stage = stage.translate((5 + 58.5, y0 + 14.0, table_z))           # inner face -> Y 51
        ptop = table_z + 62.5                                                 # NanoMax 300 deck height (Thorlabs)
        body = plat = None
    else:
        body = box(x0, x1, y0, y1, table_z, table_z + S["nanomax_h"])
        plat = box(x0 + 10, x1 - 10, y0 + 6, y1 - 6, table_z + S["nanomax_h"], table_z + S["nanomax_h"] + S["nanomax_platform_h"])
        ptop = table_z + S["nanomax_h"] + S["nanomax_platform_h"]
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
    return [(f"nanomax300_{tag}", stage_shape), (f"fiber_holder_{tag}", post.union(arm).union(clamp)), (f"fiber_{tag}", fib)]


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
# Velmex BiSlide MN10 vendor models (file frame: body along +Z from z=0, motor beyond the +Z end plate,
# slider on the +Y face, width along X; measured from the two STEP files in vendor/)
# ----------------------------------------------------------------------------
V = dict(body_x=43.2, body_y0=-27.3, body_y1=27.3, slider_top=37.8, slider_len=116.9, slider_hw=39.3, end_plate=9.5)
VELMEX_TRAVEL = {"velmex_MN10-0150-21.step": 381.0, "velmex_MN10-0050-21.step": 127.0}
VX_X0 = -40.0                     # station X of the X-axis body's nest-end face (file z = 0); the body runs toward -X from here
VY_Y0 = -142.25                   # station Y of the Y-axis body's -Y end face (file z = 0); motor toward +Y


def velmex(fname):
    """Split a BiSlide STEP into fixed solids and the moving slider (+ its switch striker); slider drawn at mid travel."""
    wp = vendor_step(fname)
    if wp is None:
        return None
    sol = wp.solids().vals()
    bx = lambda t: t.BoundingBox()
    slider = [t for t in sol if bx(t).xmin < -35 and bx(t).ymin > 5 and bx(t).ymax < 39]
    striker = [t for t in sol if bx(t).xmin > 29 and bx(t).ymin > 28 and bx(t).ymax < 33]
    mov = slider + striker
    fixed = [t for t in sol if all(t is not m for m in mov)]
    b = bx(slider[0]); body = max(sol, key=lambda t: t.Volume())
    return dict(fixed=fixed, mov=mov, slider_c=(b.zmin + b.zmax) / 2, body_len=bx(body).zmax,
                travel=VELMEX_TRAVEL[fname], zmax=max(bx(t).zmax for t in sol))


def place(solids, dz, rot, tr):
    """Translate solids along the file z by dz, apply rotations [(axis, deg), ...] about the origin, then translate."""
    c = cq.Workplane().add(cq.Compound.makeCompound([t.translate(cq.Vector(0, 0, dz)) for t in solids]))
    for axis, ang in rot:
        c = c.rotate((0, 0, 0), axis, ang)
    return c.translate(tr)


def slider_target(v, zc_file, what):
    lo, hi = v["body_len"] / 2 - v["travel"] / 2, v["body_len"] / 2 + v["travel"] / 2
    if not (lo <= zc_file <= hi):
        print(f"[vendor] WARNING: {what} slider centre {zc_file:.1f} outside travel {lo:.1f}..{hi:.1f} (file frame)")
    return zc_file - v["slider_c"]


ROT_X_AXIS = [((1, 0, 0), 90), ((0, 0, 1), -90)]     # file (x, y, z) -> station (-z, -x, y): body along -X, slider up, switches -Y
ROT_Z_AXIS = [((0, 0, 1), -90)]                      # file (x, y, z) -> station (y, -x, z): body up, slider face +X (toward the nest)
ROT_Y_AXIS = [((1, 0, 0), 90), ((0, 0, 1), 180)]     # file (x, y, z) -> station (-x, z, y): body along +Y, slider up
_VX = {}


def _vx():
    if "x" not in _VX:
        _VX["x"] = velmex("velmex_MN10-0150-21.step")
        _VX["z"] = velmex("velmex_MN10-0050-21.step")
        _VX["y"] = velmex("velmex_MN10-0050-21.step")
    return _VX


# ----------------------------------------------------------------------------
# Transport
# ----------------------------------------------------------------------------
def x_axis():
    """Returns (body, motor_end, riser). The riser is two pedestals: the Y stage body crosses under the X axis
    between them (X -260..-140); the 0150's cleats (file z 247..317 -> X -357..-287) sit on the long pedestal."""
    v = _vx()["x"]
    cyx = S["x_axis_cy"]
    zb = table_z + S["x_axis_riser"]
    if v is not None:
        tr = (VX_X0, cyx, zb - V["body_y0"])                                  # file y = -27.3 (body bottom) -> Z zb
        bl = v["body_len"]
        def _fix(t):                                                            # relocate the two cleats along the body
            b = t.BoundingBox()
            if max(abs(b.xmin), abs(b.xmax)) > 50 and b.ymax < -15:
                return t.translate(cq.Vector(0, 0, S["cleat_shift"]))
            return t
        v = dict(v, fixed=[_fix(t) for t in v["fixed"]])
        is_cleat = lambda t: max(abs(t.BoundingBox().xmin), abs(t.BoundingBox().xmax)) > 50 and t.BoundingBox().ymax < -15
        # motor end = everything living in the last 60 mm of the body and beyond: coupling housing (z 508..564, 68 mm tall),
        # motor-end plate and the PK266 (z 552..628). The arm never reaches that X range, so it is checked separately.
        body_sol = [t for t in v["fixed"] if t.BoundingBox().zmin < bl - 60.0 and not is_cleat(t)]   # body, nest-end plate, screw, switches
        motor_sol = [t for t in v["fixed"] if t.BoundingBox().zmin >= bl - 60.0]
        cleat_sol = [t for t in v["fixed"] if is_cleat(t)]
        body = place(body_sol, 0.0, ROT_X_AXIS, tr)
        motor = place(motor_sol, 0.0, ROT_X_AXIS, tr)
        S["_x_cleats"] = place(cleat_sol, 0.0, ROT_X_AXIS, tr)
        ped1 = box(VX_X0 - bl + 10, -285, cyx - 40, cyx + 40, table_z, zb)   # long pedestal, carries the two cleats (X -357..-287)
        ped2 = box(-120, VX_X0 - 25, cyx - 40, cyx + 40, table_z, zb)          # short pedestal, ends 14 mm short of the NanoMax base (X -51)
        return body, motor, (ped1, ped2)                                       # gap X -285..-120: Y stage body and tray deck pass through
    y0, y1 = cyx - S["axis_w"] / 2, cyx + S["axis_w"] / 2
    x1 = S["xc_nest"] + 60                              # body ends 60 beyond the nest carriage centre (carriage half-length 51)
    x0 = x1 - S["x_body_len"]                           # ... and runs back toward the tray
    body = box(x0, x1, y0, y1, zb, zb + S["axis_h"])
    motor = box(x0 - 60, x0, cyx - 28, cyx + 28, zb + 4, zb + 60)              # NEMA 23 stepper envelope
    ped1 = box(x0 + 10, -285, y0 + 6, y1 - 6, table_z, zb)
    ped2 = box(-120, x1 - 10, y0 + 6, y1 - 6, table_z, zb)
    return body, motor, (ped1, ped2)


def z_tower(xc):
    """X carriage + Z axis body for X-carriage centre xc."""
    vx, vz = _vx()["x"], _vx()["z"]
    if vx is not None:
        zb = table_z + S["x_axis_riser"]
        trx = (VX_X0, S["x_axis_cy"], zb - V["body_y0"])
        xcar = place(vx["mov"], slider_target(vx, VX_X0 - xc, "X"), ROT_X_AXIS, trx)          # station X = VX_X0 - file z
        zc_top = zb + (V["slider_top"] - V["body_y0"])                                          # X slider top: zb + 65.1
        trz = (xc, S["x_axis_cy"], zc_top + V["end_plate"])                                     # Z body end plate sits on the X slider
        zbody = place(vz["fixed"], 0.0, ROT_Z_AXIS, trz)
        S["_z_tr"] = trz; S["_zc_top"] = zc_top
        return xcar, zbody
    y0, y1 = S["x_axis_cy"] - S["axis_w"] / 2, S["x_axis_cy"] + S["axis_w"] / 2
    zc0 = table_z + S["x_axis_riser"] + S["axis_h"]
    xcar = box(xc - S["car_len"] / 2, xc + S["car_len"] / 2, y0, y1, zc0, zc0 + S["car_t"])
    zb0 = zc0 + S["car_t"]
    zbody = box(xc - S["axis_h"] / 2, xc + S["axis_h"] / 2, y0, y1, zb0, zb0 + S["z_body_len"])
    return xcar, zbody


def z_carriage_and_arm(xc, z_iface_top, gx):
    """Z carriage plate on the +X face of the Z body and the L-arm whose end plate bottom sits at z_iface_top,
    covering the gripper bracket interface at gripper X position gx (die origin X)."""
    a = S["arm_sec"]
    cyx = S["x_axis_cy"]
    # end plate over the bracket interface (footprint from gripper_module.IFACE, in the gripper frame)
    ix0, ix1, iy0, iy1 = G.IFACE                     # bracket top-plate footprint (gripper frame), per layout
    ep = box(gx + ix0, gx + ix1, iy0, iy1, z_iface_top, z_iface_top + 8)
    # the bars cross the X-axis band no lower than arm_cross_z (+ the gripper's Z offset); a vertical drop bar
    # joins them to the end plate when the interface is lower (horizontal gripper layout)
    gz = z_iface_top - (G.body_z1 + G.P["top_t"])                                    # 0 at the nest, tray drop elsewhere
    za = max(z_iface_top + 8, S["arm_cross_z"] + gz)
    if za > z_iface_top + 8:
        ep = ep.union(box(gx + ix0, gx + ix0 + a, iy1 - a, iy1, z_iface_top + 8 - 0.01, za + a))
    # bar along Y from the X-axis band to the end plate, then bar along X back to the Z carriage face
    bar_y = box(gx + ix0, gx + ix0 + a, cyx + 20, iy1, za, za + a)
    vz = _vx()["z"]
    if vz is not None:
        zc_file = (vz["body_len"] / 2 - vz["travel"] / 2) + 20.0                       # slider parked 20 mm above its low limit
        trz = S["_z_tr"]
        zc = place(vz["mov"], slider_target(vz, zc_file + gz, "Z"), ROT_Z_AXIS, trz)
        zs0 = trz[2] + zc_file + gz - V["slider_len"] / 2                             # slider Z range (absolute)
        zs1 = zs0 + V["slider_len"]
        xf = xc + V["slider_top"]                                                      # Z slider face (+X)
        plate = box(xf, xf + 10, cyx - V["slider_hw"], cyx + V["slider_hw"], zs0 + 5, zs1 - 5)   # adapter plate on the slider
        drop = box(xf + 10, xf + 10 + a, cyx + 20, cyx + 20 + a, za, zs0 + 40)                 # 25 sq bar down to the arm level
        bar_x = box(xf + 10, gx + ix0 + a, cyx + 20, cyx + 20 + a, za, za + a)
        return zc, ep.union(bar_y).union(bar_x).union(drop).union(plate), [ep, bar_y, bar_x, drop, plate]
    y0, y1 = cyx - S["axis_w"] / 2, cyx + S["axis_w"] / 2
    xf = xc + S["axis_h"] / 2                        # Z body +X face
    zc = box(xf, xf + 10, y0, y1, za - 28, za - 28 + S["car_len"])
    bar_x = box(xf + 10, gx + ix0 + a, cyx + 20, cyx + 20 + a, za, za + a)
    return zc, ep.union(bar_y).union(bar_x), [ep, bar_y, bar_x]


def y_stage_and_tray(active_col_x, active_row_y):
    """Y axis body under the tray deck, its carriage, deck and the wafer tray (cols along X, rows along Y).
    The tray is positioned so that the pocket in column 'active_col_x' (die X) and the active row sits at Y = active_row_y."""
    x_first = S["tray_col0_x"]                                       # die X of column 0 (nearest the nest)
    tray_x0, tray_x1, ty0, ty1 = TM.extents(x_first, active_row_y)
    tray_len_y = ty1 - ty0
    tray_cx = (tray_x0 + tray_x1) / 2
    xw0, xw1 = tray_cx - S["axis_w"] / 2, tray_cx + S["axis_w"] / 2
    ycar_c = active_row_y                                            # carriage / tray placed so the active row is at active_row_y
    vy = _vx()["y"]
    if vy is not None:
        tr = (tray_cx, VY_Y0, table_z - V["body_y0"])
        ybody = place(vy["fixed"], 0.0, ROT_Y_AXIS, tr)
        ycar = place(vy["mov"], slider_target(vy, ycar_c - VY_Y0, "Y"), ROT_Y_AXIS, tr)       # station Y = VY_Y0 + file z
        deck_z0 = table_z + (V["slider_top"] - V["body_y0"])                                    # slider top: table + 65.1
    else:
        yb0 = -38.0
        ybody = box(xw0, xw1, yb0, yb0 + S["y_body_len"], table_z, table_z + S["axis_h"])
        zc0 = table_z + S["axis_h"]
        ycar = box(xw0, xw1, ycar_c - S["car_len"] / 2, ycar_c + S["car_len"] / 2, zc0, zc0 + S["car_t"])
        deck_z0 = zc0 + S["car_t"]
    deck = box(tray_x0 - 8, tray_x1 + 8, ycar_c - tray_len_y / 2 - 8, ycar_c + tray_len_y / 2 + 8, deck_z0, deck_z0 + 6)
    z_top_deck = deck_z0 + 6
    tray, z_led, _ = TM.tray(x_first, ycar_c, z_top_deck)            # pockets and ledges: cad/tray
    return ybody, ycar, deck, tray, z_led, (tray_x0, tray_x1, tray_len_y)


# ----------------------------------------------------------------------------
# Gripper module placed at (die X = gx, die bottom Z = gz)
# ----------------------------------------------------------------------------
def gripper_at(gx, gz, open_mm=0.0):
    parts = {
        "far_arm": G.far_arm(), "near_arm": G.near_arm(), "far_tip": G.far_tip_block(),
        "near_tip": G.near_tip_block(), "blade": G.blade(), "bracket": G.bracket(),
    }
    vend = G.actuator_vendor(open_mm) if USE_VENDOR else None
    body, fn, ff = vend if vend is not None else G.actuator(open_mm)
    parts.update({"mhz2_body": body, "mhz2_fing_near": fn, "mhz2_fing_far": ff})
    return {k: v.translate((gx, 0, gz)) for k, v in parts.items()}


# ----------------------------------------------------------------------------
# Clearance checks (axis-aligned bounding boxes)
# ----------------------------------------------------------------------------
def main():
    # ---- static ----
    static = {}
    static["optical_table"] = table()
    kb, ins = nest(); static["nest_riser_kinematic"] = kb; static["nest_chuck_copper"] = ins; static["nest_tec"] = S["_nest_tec"]
    static["nest_cage_semitron"] = S["_nest_cage"]
    for name, s in nanomax(-1) + nanomax(+1): static[name] = s
    for name, s in microscope(): static[name] = s
    xax, xmot, (xr1, xr2) = x_axis(); static["x_axis_body_velmex"] = xax; static["x_axis_motor_end"] = xmot
    static["x_axis_riser_long"] = xr1; static["x_axis_riser_short"] = xr2
    if "_x_cleats" in S: static["x_axis_cleats"] = S["_x_cleats"]
    static["die_at_nest"] = G.die()

    # ---- moving, at NEST ----
    xc = S["xc_nest"]
    xcar, zbody = z_tower(xc)
    z_iface_top = G.body_z1 + G.P["top_t"]            # bracket top plate top (Z 70)
    zc, arm, arm_parts = z_carriage_and_arm(xc, z_iface_top, 0.0)
    ybody, ycar, deck, stick, z_led, tray_ext = y_stage_and_tray(S["tray_col0_x"], cy)
    moving_nest = {"x_carriage": xcar, "z_axis_body_velmex": zbody, "z_carriage": zc, "arm_L_25sq": arm}
    grip_nest = gripper_at(0.0, 0.0)

    # ---- moving, at the FARTHEST tray column (second configuration; worst case for travel and the Z tower) ----
    far_col_x = S["tray_col0_x"] - (S["tray_cols"] - 1) * S["tray_col_pitch"]
    S["stick_x"] = far_col_x
    xc2 = xc + far_col_x
    gz2 = z_led                                        # die bottom on the tray ledges
    xcar2, zbody2 = z_tower(xc2)
    zc2, arm2, arm2_parts = z_carriage_and_arm(xc2, z_iface_top + gz2, far_col_x)
    grip_stick = gripper_at(far_col_x, gz2, open_mm=1.5)

    # ---- checks ----
    rep = []
    rep.append(f"table plane Z = {table_z:.1f} (die bottom = 0). Nest die top at {die_top}; fiber axis at {die_top} via holder {S['holder_axis_above_deck']} above NanoMax deck")
    rep.append(f"wafer tray: {S['tray_cols']} columns x {S['tray_rows']} rows = {S['tray_cols']*S['tray_rows']} pockets, "
               f"{tray_ext[1]-tray_ext[0]:.0f} x {tray_ext[2]:.0f} mm; columns at die X {S['tray_col0_x']:.0f} .. {far_col_x:.0f} (pitch {S['tray_col_pitch']})")
    rep.append(f"X carriage: nest {xc:.0f} -> farthest column {xc2:.0f}  (travel used {abs(far_col_x):.0f} of {S['x_travel']:.0f} mm)")
    rep.append(f"Z carriage: nest arm at Z {z_iface_top:.1f} -> tray at Z {z_iface_top + gz2:.1f} (drop {abs(gz2):.1f} mm) + 8 mm approach lift")
    rep.append(f"Y stage: row pitch {S['tray_row_pitch']} x {S['tray_rows']} rows -> travel {(S['tray_rows']-1)*S['tray_row_pitch']:.1f} mm (axis {S['y_travel']:.0f})")
    pairs = [
        ("gripper far_arm @nest", grip_nest["far_arm"], "objective", static["objective"]),
        ("gripper near_arm @nest", grip_nest["near_arm"], "objective", static["objective"]),
        ("gripper bracket @nest", grip_nest["bracket"], "microscope_tube", static["microscope_tube"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "microscope_tube", static["microscope_tube"]),
        ("gripper far_arm @nest", grip_nest["far_arm"], "microscope_column", static["microscope_column"]),
        ("gripper near_arm @nest", grip_nest["near_arm"], "fiber_holder_in", static["fiber_holder_in"]),
        ("nest_cage (per member)", S["_nest_cage_parts"], "fiber_holder_in", static["fiber_holder_in"]),
        ("nest_riser (neck/wide/base)", S["_nest_riser_parts"], "fiber_holder_in (per member)", S["_holder_parts_in"]),
        ("nest_riser (neck/wide/base)", S["_nest_riser_parts"], "fiber_holder_out (per member)", S["_holder_parts_out"]),
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
        ("arm_L @nest", arm_parts, "microscope_tube", static["microscope_tube"]),
        ("arm_L @nest", arm_parts, "nanomax300_in", static["nanomax300_in"]),
        ("arm_L @nest", arm_parts, "fiber_holder_in", static["fiber_holder_in"]),
        ("z_axis_body @nest", zbody, "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_body", xax, "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_body", xax, "y_stage_body", ybody),
        ("x_axis_riser_long", xr1, "y_stage_body", ybody),
        ("x_axis_riser_short", xr2, "y_stage_body", ybody),
        ("x_axis_riser_short", xr2, "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_riser_long", xr1, "deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0))),
        ("x_axis_riser_short", xr2, "deck @row 0 (Y-48.75)", deck.translate((0, -48.75, 0))),
        ("x_axis_body", xax, "tray @row 0 (Y-48.75)", stick.translate((0, -48.75, 0))),
        ("x_axis_body", xax, "wafer_tray", stick),
        ("x_axis_motor_end", xmot, "y_stage_body", ybody),
        ("z_axis_body @stick", zbody2, "y_stage_body", ybody),
        ("arm_L @far column", arm2_parts, "wafer_tray", stick),
        ("arm_L @far column", arm2_parts, "x_carriage @far col", xcar2),
        ("arm_L @far column", arm2_parts, "x_axis_body", xax),
        ("arm_L @far column", arm2_parts, "x_axis_motor_end", xmot),
        ("gripper mhz2_body @far col", grip_stick["mhz2_body"], "x_axis_body", xax),
        ("gripper bracket @far col", grip_stick["bracket"], "x_axis_body", xax),
        ("arm_L @nest", arm_parts, "x_carriage @nest", xcar),
        ("arm_L @nest", arm_parts, "x_axis_body", xax),
        ("gripper mhz2_body @far col", grip_stick["mhz2_body"], "wafer_tray", stick),
        ("gripper far_arm @far col", grip_stick["far_arm"], "wafer_tray", stick),
        ("gripper near_arm @far col", grip_stick["near_arm"], "wafer_tray", stick),
    ]
    pairs += [
        ("x_carriage @nest", xcar, "nanomax300_in", static["nanomax300_in"]),
        ("x_carriage @nest", xcar, "fiber_holder_in", static["fiber_holder_in"]),
        ("z_axis_body @nest", zbody, "fiber_holder_in", static["fiber_holder_in"]),
        ("x_axis_body", xax, "fiber_holder_in", static["fiber_holder_in"]),
        ("gripper bracket @nest", grip_nest["bracket"], "fiber_holder_out", static["fiber_holder_out"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "fiber_holder_in", static["fiber_holder_in"]),
        ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "fiber_holder_out", static["fiber_holder_out"]),
    ]
    rep.append("")
    rep.append("clearances vs boxes (AABB separation, mm; negative = overlap):")
    if "x_axis_cleats" in static:
        pairs += [("gripper mhz2_body @far col", grip_stick["mhz2_body"], "x_axis_cleats", static["x_axis_cleats"]),
                  ("gripper mhz2_body @nest", grip_nest["mhz2_body"], "x_axis_cleats", static["x_axis_cleats"]),
                  ("arm_L @far column", arm2_parts, "x_axis_cleats", static["x_axis_cleats"])]
    for an, a, bn, b in pairs:
        if bn in ("objective", "microscope_tube", "microscope_column"):
            continue
        gp = gap_any(a, b)
        flag = "  OK " if gp > 2 else ("  TIGHT" if gp > 0 else "  ** OVERLAP **")
        rep.append(f"  {an:26s} vs {bn:20s}: {gp:7.1f}{flag}")
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
    for pn, part in [("far_arm bars @nest", grip_nest["far_arm"].intersect(lowcut)), ("far_arm root @nest", grip_nest["far_arm"].intersect(outcut)),
                     ("near_arm bars @nest", grip_nest["near_arm"].intersect(lowcut)), ("near_arm head @nest", grip_nest["near_arm"].intersect(incut)),
                     ("near_arm root @nest", grip_nest["near_arm"].intersect(outcut)),
                     ("far_tip @nest", grip_nest["far_tip"]),
                     ("bracket @nest", grip_nest["bracket"]), ("mhz2_body @nest", grip_nest["mhz2_body"]), ("arm_L @nest", arm), ("z_carriage @nest", zc)]:
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
    statics = ["nanomax300_in", "fiber_holder_in", "fiber_in", "nanomax300_out", "fiber_holder_out", "nest_riser_kinematic",
               "x_axis_body_velmex", "x_axis_riser_short", "microscope_arm"] + (["x_axis_cleats"] if "x_axis_cleats" in static else [])
    for n in statics:
        g1 = min(gap(g, bb(static[n])) for g in g_sweeps); g2 = min(gap(g, bb(static[n])) for g in a_sweeps)
        rep.append(f"  gripper band vs {n:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    for cn, (axy, r, z0, z1) in cyls.items():
        g1 = min(gap_cyl(g, axy, r, z0, z1) for g in g_sweeps); g2 = min(gap_cyl(g, axy, r, z0, z1) for g in a_sweeps)
        rep.append(f"  gripper band vs {cn:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    rep.append("")
    rep.append("the gripper band sweep necessarily passes under the objective (that is the exchange); its clearance there is the")
    rep.append("bar height check in cad/gripper/checks.txt (tallest part 9.0 mm above die top vs WD).")
    suffix = ("_vendor" if USE_VENDOR else "") + G.SFX
    if USE_VENDOR:
        rep.insert(0, "VENDOR MODELS: Thorlabs MAX313D/M (22803-E0W) x2, KB1X1 (2374-E0W); Velmex MN10-0150-xxx-21 (X) and MN10-0050-xxx-21 (Z, Y) "
                      "with PK266 motors; envelopes for the SMC gripper and the microscope. AABBs include micrometers, motors and switches.")
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(DIRS["comp"], f"checks{suffix}.txt"), "w") as f: f.write(txt + "\n")

    # ---- assembly export (nest configuration + ghost of stick configuration) ----
    assy = cq.Assembly(name="test_station")
    col = {
        "optical_table": (0.86, 0.88, 0.90), "nest_riser_kinematic": (0.60, 0.63, 0.68), "nest_chuck_copper": (0.72, 0.45, 0.20), "nest_tec": (0.85, 0.85, 0.88), "nest_cage_semitron": (0.16, 0.16, 0.18),
        "nanomax300_in": (0.56, 0.69, 0.82), "nanomax300_out": (0.56, 0.69, 0.82), "fiber_holder_in": (0.36, 0.40, 0.44),
        "fiber_holder_out": (0.36, 0.40, 0.44), "fiber_in": (0.94, 0.82, 0.50), "fiber_out": (0.94, 0.82, 0.50),
        "objective": (0.20, 0.23, 0.27), "microscope_tube": (0.25, 0.28, 0.32), "microscope_arm": (0.77, 0.79, 0.82), "microscope_column": (0.77, 0.79, 0.82),
        "x_axis_body_velmex": (0.56, 0.69, 0.82), "x_axis_motor_end": (0.45, 0.48, 0.52), "x_axis_riser_long": (0.60, 0.63, 0.68), "x_axis_riser_short": (0.60, 0.63, 0.68), "x_axis_cleats": (0.45, 0.48, 0.52), "die_at_nest": (0.81, 0.89, 0.97),
        "x_carriage": (0.18, 0.31, 0.44), "z_axis_body_velmex": (0.56, 0.69, 0.82), "z_carriage": (0.18, 0.31, 0.44), "arm_L_25sq": (0.18, 0.31, 0.44),
        "y_stage_body": (0.56, 0.69, 0.82), "y_carriage": (0.18, 0.31, 0.44), "tray_deck": (0.60, 0.63, 0.68), "wafer_tray": (0.85, 0.81, 0.68),
    }
    for n, s in static.items(): assy.add(s, name=n, color=cq.Color(*col[n], 1.0))
    for n, s in moving_nest.items(): assy.add(s, name=n, color=cq.Color(*col[n], 1.0))
    for n, s in {"y_stage_body": ybody, "y_carriage": ycar, "tray_deck": deck, "wafer_tray": stick}.items(): assy.add(s, name=n, color=cq.Color(*col[n], 1.0))
    for n, s in grip_nest.items(): assy.add(s, name=f"gripper_{n}", color=cq.Color(0.25, 0.25, 0.27, 1.0))
    for n, s in {"x_carriage_at_far_col": xcar2, "z_axis_at_far_col": zbody2, "z_carriage_at_far_col": zc2, "arm_at_far_col": arm2}.items():
        assy.add(s, name=n, color=cq.Color(0.18, 0.31, 0.44, 0.25))
    for n, s in grip_stick.items(): assy.add(s, name=f"gripper_at_far_col_{n}", color=cq.Color(0.25, 0.25, 0.27, 0.25))
    assy.add(keepout(), name="objective_keepout", color=cq.Color(0.85, 0.64, 0.25, 0.25))
    assy.save(os.path.join(DIRS["STEP"], f"station_assembly{suffix}.step"))
    print("wrote station files to", DIRS["comp"])


if __name__ == "__main__":
    main()

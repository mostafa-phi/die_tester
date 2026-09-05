"""
Full test-station assembly: nest, gripper module, bench-level Cartesian transport
(X axis + Z axis + arm, Y stage under the stick), two NanoMax 300 fiber stages with
holders, microscope column/objective, optical table. Same frame as gripper_module.py
(X = die long axis, Y = optical axis, Z up, Z = 0 = die bottom at the nest).

Bought-part envelopes (to be replaced by vendor STEP in Fusion):
  - Velmex BiSlide MN10 class: 102 wide x 64 tall body; 102 x 102 x 10 carriage plate
  - Thorlabs NanoMax 300: 112 x 112 footprint, 62.5 deck height, 4 mm travel
  - Microscope: objective barrel dia 34, tube dia 40, column post dia 40 behind (+X)

Run: python docs/cad/station_assembly.py  -> docs/cad/out/station_*.step/svg + station_checks.txt
"""
from __future__ import annotations
import os, sys
import cadquery as cq
from cadquery import exporters

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gripper_module as G   # noqa: E402  (parts + P in the shared frame)

OUT = G.OUT
box = G.box
mat_note = []

# ----------------------------------------------------------------------------
# Station parameters
# ----------------------------------------------------------------------------
S = dict(
    # fiber side
    holder_axis_above_deck=20.0,   # fiber axis height above the NanoMax top platform (holder-dependent; measure)
    nanomax_w=112.0, nanomax_h=62.5, nanomax_platform_h=4.0, nanomax_gap_y=45.0,   # inner face to facet
    fiber_protrusion=12.0,         # fiber tip to V-groove clamp
    # microscope (behind the nest, +X, as in the bench photo)
    obj_wd=20.0, obj_dia=34.0, obj_len=40.0, tube_dia=40.0, tube_len=60.0,
    column_x=80.0, column_dia=40.0, column_top=260.0,
    # transport (Velmex BiSlide envelope)
    axis_w=102.0, axis_h=64.0, car_t=10.0, car_len=102.0,
    x_travel=300.0, x_body_len=380.0, z_body_len=150.0, y_travel=105.0, y_body_len=205.0,
    x_axis_cy=-100.0,              # X axis centre-line in Y (beside the input NanoMax, outside the fiber corridor)
    x_axis_riser=76.0,             # X axis sits on a riser ABOVE the NanoMax envelope (body top Z -10 .. +54)
    xc_nest=-120.0,                # X-carriage centre when the gripper is at the nest (carriage end X -69, NanoMax face X -51)
    arm_sec=25.0,                  # square arm bar
    # wafer tray: one 100 mm wafer = 8 columns x 14 rows = 112 pockets, die returns to its own pocket after test
    tray_cols=8, tray_rows=14, tray_col_pitch=16.0, tray_row_pitch=7.5,
    tray_col0_x=-150.0,            # die X of the first (nearest) column; last column at -150 - 7*16 = -262
)

die_top = G.die_top
table_z = die_top - S["holder_axis_above_deck"] - S["nanomax_h"] - S["nanomax_platform_h"]   # -86.5
cy = G.die_cy                                                                                # 3.0
S["table_z"] = table_z


# ----------------------------------------------------------------------------
# Static structure
# ----------------------------------------------------------------------------
def table():
    return box(-540, 220, -280, 280, table_z - 12, table_z)


def nest():
    """Two-piece nest: riser + lapped rail insert, on a KB1X1-class kinematic base."""
    kb = box(-14, 24, -16, 22, table_z, table_z + 20)                        # kinematic base envelope
    riser = box(-8, 18, -10, 16, table_z + 20, -4.5)                          # riser column
    insert = box(-1, 11, 0.6, 5.4, -4.5, -1.5)                                # rail insert body (narrow in Y)
    r1 = box(0, 10, 1.0, 1.9, -1.5, 0.0)
    r2 = box(0, 10, 4.1, 5.0, -1.5, 0.0)
    ins = insert.union(r1).union(r2)
    for x in (1.5, 4.0, 6.5, 9.0):                                            # vacuum ports into each rail
        for y in (1.45, 4.55):
            ins = ins.cut(cq.Workplane("XY").center(x, y).circle(0.3).extrude(6).translate((0, 0, -4.6)))
    riser = riser.cut(cq.Workplane("XZ").center(5, -30).circle(2.0).extrude(-30).translate((0, -12, 0)))  # M5 vacuum port
    return kb.union(riser), ins


def nanomax(side):
    """side=-1 input (Y<0), +1 output (Y>6). Returns list of (name, shape)."""
    g = S["nanomax_gap_y"]
    if side < 0:
        y0, y1 = -(g + S["nanomax_w"]), -g
    else:
        y0, y1 = G.P["die_wid"] + g, G.P["die_wid"] + g + S["nanomax_w"]
    x0, x1 = 5 - S["nanomax_w"] / 2, 5 + S["nanomax_w"] / 2
    body = box(x0, x1, y0, y1, table_z, table_z + S["nanomax_h"])
    plat = box(x0 + 10, x1 - 10, y0 + 6, y1 - 6, table_z + S["nanomax_h"], table_z + S["nanomax_h"] + S["nanomax_platform_h"])
    ptop = table_z + S["nanomax_h"] + S["nanomax_platform_h"]
    # fiber holder: post on the platform near the inner edge, arm to the clamp, clamp, fiber
    if side < 0:
        post = box(-4, 14, y1 - 14, y1 - 6, ptop, die_top + 4)
        arm = box(1, 9, y1 - 8, -S["fiber_protrusion"], die_top - 1.5, die_top + 1.5)
        clamp = box(1, 9, -S["fiber_protrusion"] - 8, -S["fiber_protrusion"], die_top - 2, die_top + 2)
        fib = cq.Workplane("XZ").center(5, die_top).circle(0.0625).extrude(S["fiber_protrusion"] - 0.02).translate((0, -0.02, 0))
    else:
        yf = G.P["die_wid"]
        post = box(-4, 14, y0 + 6, y0 + 14, ptop, die_top + 4)
        arm = box(1, 9, yf + S["fiber_protrusion"], y0 + 8, die_top - 1.5, die_top + 1.5)
        clamp = box(1, 9, yf + S["fiber_protrusion"], yf + S["fiber_protrusion"] + 8, die_top - 2, die_top + 2)
        fib = cq.Workplane("XZ").center(5, die_top).circle(0.0625).extrude(-(S["fiber_protrusion"] - 0.02)).translate((0, yf + 0.02, 0))
    tag = "in" if side < 0 else "out"
    return [(f"nanomax300_{tag}", body.union(plat)), (f"fiber_holder_{tag}", post.union(arm).union(clamp)), (f"fiber_{tag}", fib)]


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
    return cq.Workplane("XY").center(5, cy).circle(S["obj_dia"] / 2).extrude(S["obj_wd"]).translate((0, 0, die_top))


# ----------------------------------------------------------------------------
# Transport
# ----------------------------------------------------------------------------
def x_axis():
    y0, y1 = S["x_axis_cy"] - S["axis_w"] / 2, S["x_axis_cy"] + S["axis_w"] / 2
    x1 = S["xc_nest"] + 60                              # body ends 60 beyond the nest carriage centre (carriage half-length 51)
    x0 = x1 - S["x_body_len"]                           # ... and runs back toward the sticks
    zb = table_z + S["x_axis_riser"]
    body = box(x0, x1, y0, y1, zb, zb + S["axis_h"])
    riser = box(x0 + 10, x1 - 10, y0 + 6, y1 - 6, table_z, zb)
    return body.union(riser), (x0, x1, y0, y1)


def z_tower(xc):
    """X carriage + Z axis body + Z carriage + arm, for X-carriage centre xc. Returns dict of shapes and arm end plate."""
    y0, y1 = S["x_axis_cy"] - S["axis_w"] / 2, S["x_axis_cy"] + S["axis_w"] / 2
    zc0 = table_z + S["x_axis_riser"] + S["axis_h"]
    xcar = box(xc - S["car_len"] / 2, xc + S["car_len"] / 2, y0, y1, zc0, zc0 + S["car_t"])
    zb0 = zc0 + S["car_t"]
    zbody = box(xc - S["axis_h"] / 2, xc + S["axis_h"] / 2, y0, y1, zb0, zb0 + S["z_body_len"])
    return xcar, zbody


def z_carriage_and_arm(xc, z_iface_top, gx):
    """Z carriage plate on the +X face of the Z body and the L-arm whose end plate bottom sits at z_iface_top,
    covering the gripper bracket interface at gripper X position gx (die origin X)."""
    y0, y1 = S["x_axis_cy"] - S["axis_w"] / 2, S["x_axis_cy"] + S["axis_w"] / 2
    a = S["arm_sec"]
    xf = xc + S["axis_h"] / 2                        # Z body +X face
    zc = box(xf, xf + 10, y0, y1, z_iface_top - 20, z_iface_top - 20 + S["car_len"])
    # end plate over the bracket interface (bracket top plate X gx-48..gx-16, Y -14..20 in gripper frame)
    ep = box(gx + G.cx - 26, gx + G.cx + 8, cy - 18, cy + 22, z_iface_top, z_iface_top + 8)
    # bar along Y from the X-axis band to the end plate, then bar along X back to the Z carriage face
    bar_y = box(gx + G.cx - 26, gx + G.cx - 26 + a, S["x_axis_cy"] + 20, cy + 22, z_iface_top + 8, z_iface_top + 8 + a)
    bar_x = box(xf + 10, gx + G.cx - 26 + a, S["x_axis_cy"] + 20, S["x_axis_cy"] + 20 + a, z_iface_top + 8, z_iface_top + 8 + a)
    return zc, ep.union(bar_y).union(bar_x)


def y_stage_and_tray(active_col_x, active_row_y):
    """Y axis body under the tray deck, its carriage, deck and the wafer tray (cols along X, rows along Y).
    The tray is positioned so that the pocket in column 'active_col_x' (die X) and the active row sits at Y = active_row_y."""
    nc, nr, pc, pr = S["tray_cols"], S["tray_rows"], S["tray_col_pitch"], S["tray_row_pitch"]
    x_first = S["tray_col0_x"]                                       # die X of column 0 (nearest the nest)
    tray_x0 = x_first - (nc - 1) * pc - 3.0                          # tray spans all columns (+3 mm rim)
    tray_x1 = x_first + 13.0
    tray_len_y = nr * pr + 1.5
    tray_cx = (tray_x0 + tray_x1) / 2
    xw0, xw1 = tray_cx - S["axis_w"] / 2, tray_cx + S["axis_w"] / 2
    yb0 = -38.0
    ybody = box(xw0, xw1, yb0, yb0 + S["y_body_len"], table_z, table_z + S["axis_h"])
    zc0 = table_z + S["axis_h"]
    # carriage / tray placed so the active row is at active_row_y: active row = middle row here
    ycar_c = active_row_y
    ycar = box(xw0, xw1, ycar_c - S["car_len"] / 2, ycar_c + S["car_len"] / 2, zc0, zc0 + S["car_t"])
    deck = box(tray_x0 - 8, tray_x1 + 8, ycar_c - tray_len_y / 2 - 8, ycar_c + tray_len_y / 2 + 8, zc0 + S["car_t"], zc0 + S["car_t"] + 6)
    z_top_deck = zc0 + S["car_t"] + 6
    z_led = z_top_deck + 2.2 + 0.8                                   # ledge top = die bottom in the pocket
    # slab to full wall height, cut all pocket cavities in ONE boolean, add all ledges in ONE boolean
    tray = box(tray_x0, tray_x1, ycar_c - tray_len_y / 2, ycar_c + tray_len_y / 2, z_top_deck, z_led + 0.8)
    cavities, ledges = [], []
    for c in range(nc):
        xd = x_first - c * pc                                        # die X for this column
        for k in range(nr):
            yc = ycar_c + (k - (nr - 1) / 2) * pr
            y0 = yc - 3.0
            cavities.append(box(xd - 2, xd + 12, y0 - 0.4, y0 + 6.4, z_top_deck + 2.2, z_led + 1.0).val())   # 14 x 6.8 cavity (2 mm jaw space each end)
            ledges.append(box(xd, xd + 10, y0 + 0.4, y0 + 1.4, z_top_deck + 2.2, z_led).val())
            ledges.append(box(xd, xd + 10, y0 + 4.6, y0 + 5.6, z_top_deck + 2.2, z_led).val())
    tray = tray.cut(cq.Workplane().add(cq.Compound.makeCompound(cavities)))
    tray = tray.union(cq.Workplane().add(cq.Compound.makeCompound(ledges)))
    return ybody, ycar, deck, tray, z_led, (tray_x0, tray_x1, tray_len_y)


# ----------------------------------------------------------------------------
# Gripper module placed at (die X = gx, die bottom Z = gz)
# ----------------------------------------------------------------------------
def gripper_at(gx, gz, open_mm=0.0):
    parts = {
        "far_arm": G.far_arm(), "near_arm": G.near_arm(), "far_tip": G.far_tip_block(),
        "near_tip": G.near_tip_block(), "blade": G.blade(), "bracket": G.bracket(),
    }
    body, fn, ff = G.actuator(open_mm)
    parts.update({"mhz2_body": body, "mhz2_fing_near": fn, "mhz2_fing_far": ff})
    return {k: v.translate((gx, 0, gz)) for k, v in parts.items()}


# ----------------------------------------------------------------------------
# Clearance checks (axis-aligned bounding boxes)
# ----------------------------------------------------------------------------
def bb(shape):
    b = shape.val().BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def gap(a, b):
    """Separation between two AABBs: >0 = clear by that much (max over axes), <=0 = overlap in all axes."""
    dx = max(a[0] - b[1], b[0] - a[1])
    dy = max(a[2] - b[3], b[2] - a[3])
    dz = max(a[4] - b[5], b[4] - a[5])
    return max(dx, dy, dz)


def gap_cyl(a, axis_xy, r, z0, z1):
    """Clearance of AABB a to a vertical cylinder: max(radial gap, vertical gap). >0 clear."""
    ax, ay = axis_xy
    dx = max(a[0] - ax, ax - a[1], 0.0); dy = max(a[2] - ay, ay - a[3], 0.0)
    radial = (dx ** 2 + dy ** 2) ** 0.5 - r
    vertical = max(z0 - a[5], a[4] - z1)
    return max(radial, vertical)


def main():
    # ---- static ----
    static = {}
    static["optical_table"] = table()
    kb, ins = nest(); static["nest_riser_kinematic"] = kb; static["nest_rail_insert_17-4"] = ins
    for name, s in nanomax(-1) + nanomax(+1): static[name] = s
    for name, s in microscope(): static[name] = s
    xax, xbb = x_axis(); static["x_axis_body_velmex"] = xax
    static["die_at_nest"] = G.die()

    # ---- moving, at NEST ----
    xc = S["xc_nest"]
    xcar, zbody = z_tower(xc)
    z_iface_top = G.body_z1 + G.P["top_t"]            # bracket top plate top (Z 70)
    zc, arm = z_carriage_and_arm(xc, z_iface_top, 0.0)
    ybody, ycar, deck, stick, z_led, tray_ext = y_stage_and_tray(S["tray_col0_x"], cy)
    moving_nest = {"x_carriage": xcar, "z_axis_body_velmex": zbody, "z_carriage": zc, "arm_L_25sq": arm}
    grip_nest = gripper_at(0.0, 0.0)

    # ---- moving, at the FARTHEST tray column (second configuration; worst case for travel and the Z tower) ----
    far_col_x = S["tray_col0_x"] - (S["tray_cols"] - 1) * S["tray_col_pitch"]
    S["stick_x"] = far_col_x
    xc2 = xc + far_col_x
    gz2 = z_led                                        # die bottom on the tray ledges
    xcar2, zbody2 = z_tower(xc2)
    zc2, arm2 = z_carriage_and_arm(xc2, z_iface_top + gz2, far_col_x)
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
        ("gripper far_arm @nest", grip_nest["far_arm"], "fiber_holder_out", static["fiber_holder_out"]),
        ("gripper bracket @nest", grip_nest["bracket"], "fiber_holder_in", static["fiber_holder_in"]),
        ("arm_L @nest", arm, "microscope_tube", static["microscope_tube"]),
        ("arm_L @nest", arm, "nanomax300_in", static["nanomax300_in"]),
        ("arm_L @nest", arm, "fiber_holder_in", static["fiber_holder_in"]),
        ("z_axis_body @nest", zbody, "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_body", xax, "nanomax300_in", static["nanomax300_in"]),
        ("x_axis_body", xax, "y_stage_body", ybody),
        ("z_axis_body @stick", zbody2, "y_stage_body", ybody),
        ("arm_L @far column", arm2, "wafer_tray", stick),
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
    for an, a, bn, b in pairs:
        if bn in ("objective", "microscope_tube", "microscope_column"):
            continue
        gp = gap(bb(a), bb(b))
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
    gm = [bb(v) for v in grip_nest.values()]
    g_sweep = (S["stick_x"] + min(b[0] for b in gm), max(b[1] for b in gm), min(b[2] for b in gm), max(b[3] for b in gm),
               min(b[4] for b in gm) + lift, max(b[5] for b in gm) + lift)
    ab = bb(arm)
    a_sweep = (S["stick_x"] + ab[0], ab[1], ab[2], ab[3], ab[4] + lift, ab[5] + lift)
    rep.append("")
    rep.append("swept volumes nest <-> stick (after the 8 mm lift) vs static objects:")
    for n in ("nanomax300_in", "fiber_holder_in", "fiber_in", "nanomax300_out", "fiber_holder_out", "nest_riser_kinematic", "x_axis_body_velmex", "microscope_arm"):
        g1 = gap(g_sweep, bb(static[n])); g2 = gap(a_sweep, bb(static[n]))
        rep.append(f"  gripper band vs {n:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    for cn, (axy, r, z0, z1) in cyls.items():
        g1 = gap_cyl(g_sweep, axy, r, z0, z1); g2 = gap_cyl(a_sweep, axy, r, z0, z1)
        rep.append(f"  gripper band vs {cn:22s}: {g1:7.1f}{'  OK ' if g1 > 2 else '  ** CHECK **'}    arm band: {g2:7.1f}{'  OK ' if g2 > 2 else '  ** CHECK **'}")
    rep.append("")
    rep.append("the gripper band sweep necessarily passes under the objective (that is the exchange); its clearance there is the")
    rep.append("bar height check in gripper_checks.txt (tallest part 9.0 mm above die top vs WD).")
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(OUT, "station_checks.txt"), "w") as f: f.write(txt + "\n")

    # ---- assembly export (nest configuration + ghost of stick configuration) ----
    assy = cq.Assembly(name="test_station")
    col = {
        "optical_table": (0.86, 0.88, 0.90), "nest_riser_kinematic": (0.60, 0.63, 0.68), "nest_rail_insert_17-4": (0.56, 0.56, 0.56),
        "nanomax300_in": (0.56, 0.69, 0.82), "nanomax300_out": (0.56, 0.69, 0.82), "fiber_holder_in": (0.36, 0.40, 0.44),
        "fiber_holder_out": (0.36, 0.40, 0.44), "fiber_in": (0.94, 0.82, 0.50), "fiber_out": (0.94, 0.82, 0.50),
        "objective": (0.20, 0.23, 0.27), "microscope_tube": (0.25, 0.28, 0.32), "microscope_arm": (0.77, 0.79, 0.82), "microscope_column": (0.77, 0.79, 0.82),
        "x_axis_body_velmex": (0.56, 0.69, 0.82), "die_at_nest": (0.81, 0.89, 0.97),
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
    assy.save(os.path.join(OUT, "station_assembly.step"))

    # ---- views ----
    solids = [s.val() for s in list(static.values()) + list(moving_nest.values()) + [ybody, ycar, deck, stick] + list(grip_nest.values())]
    comp = cq.Compound.makeCompound(solids)
    ghost = cq.Compound.makeCompound([s.val() for s in [xcar2, zbody2, zc2, arm2] + list(grip_stick.values())])
    both = cq.Compound.makeCompound(solids + [ghost])

    def rot(c, rx, rz):
        if rz: c = c.rotate((0, 0, 0), (0, 0, 1), rz)
        if rx: c = c.rotate((0, 0, 0), (1, 0, 0), rx)
        return c
    views = {"station_plan": both, "station_front_alongY": rot(both, -90, 0), "station_side_alongX": rot(both, -90, 90), "station_iso": rot(both, -60, -35)}
    for vname, c in views.items():
        exporters.export(cq.Workplane().add(c), os.path.join(OUT, f"view_{vname}.svg"),
                         opt={"width": 1400, "height": 900, "marginLeft": 20, "marginTop": 20, "showAxes": False,
                              "projectionDir": (0, 0, 1), "strokeWidth": 0.5, "strokeColor": (30, 30, 30), "showHidden": False})
    # nest close-up: everything within +/-70 mm of the die
    near = [s for s in solids if gap(bb(cq.Workplane().add(s)), (-70, 80, -70, 80, -20, 90)) <= 0]
    nc = cq.Compound.makeCompound(near)
    for vname, c in {"nest_closeup_front": rot(nc, -90, 0), "nest_closeup_iso": rot(nc, -60, -35), "nest_closeup_plan": nc}.items():
        exporters.export(cq.Workplane().add(c), os.path.join(OUT, f"view_{vname}.svg"),
                         opt={"width": 1400, "height": 900, "marginLeft": 20, "marginTop": 20, "showAxes": False,
                              "projectionDir": (0, 0, 1), "strokeWidth": 0.5, "strokeColor": (30, 30, 30), "showHidden": False})
    print("wrote station files to", OUT)


if __name__ == "__main__":
    main()

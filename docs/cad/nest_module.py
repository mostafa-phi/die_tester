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

Frame = gripper frame: X die long axis, Y optical axis, Z up, die bottom at the nest = 0.

Parts (docs/cad/out/):
  nest_chuck_copper{.step,.stl}      C101 copper, Ni plated, pad lapped flat <= 3 um; 6 x dia 0.5 vacuum holes
  nest_cage_semitron{.step,.stl}     Semitron ESd 480 frame: 4 corner blocks (X stop pads, X guard, Y guards)
  nest_riser_6061.step               T-shaped riser / heat sink: 10 mm neck, TEC pocket, on the KB1X1 base
  nest_module_assembly.step          chuck + cage + riser + TEC + die + gripper (closed) + fiber/holder envelopes
  nest_module_setdown.step           same with the jaws open at the set-down position (push step)
  nest_checks.txt                    clearances vs gripper (closed / open / push), holders, fibers, die

Run:  python docs/cad/nest_module.py
"""
from __future__ import annotations
import os
import sys
import cadquery as cq
from cadquery import exporters

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gripper_module as G   # noqa: E402

OUT = G.OUT
box = G.box
P = G.P
L, W, T = P["die_len"], P["die_wid"], P["die_thk"]      # 10, 6, 0.5

N = dict(
    # --- fiber side (measure on the bench) ---
    fiber_protrusion=5.0,          # fiber tip beyond the holder front face
    holder_w=25.0,                 # holder body width along X (centred on the die)
    holder_zb=-8.0, holder_zt=4.0, # holder body bottom / top relative to the die bottom (fiber axis at Z 0.5)
    holder_len=20.0,               # holder body length along Y (envelope only)
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
    post_z1=0.40, post_z0=-1.5,
    stop_x=10.0, pad_t=0.6, pad_y=((0.6, 1.2), (4.8, 5.4)), relief=0.2,
    guard_gap=0.4,
    yguard_gap=0.6, yguard_t=0.4, yguard_len=1.5,
    # --- riser / heat sink: neck no wider than the cage in Y down to below the holders, then wide ---
    neck=(-8.0, 18.0, -2.0, 8.0), neck_bottom=-12.0,                   # neck Y = cage Y; holders bottom out at -8
    wide=(-8.0, 18.0, -10.0, 16.0), wide_top=-12.0,
    tec=(15.0, 15.0, 2.5), tec_c=(5.0, 3.0),                           # 15 x 15 x 2.5 micro-TEC centred under the die
    # --- push-to-stop ---
    place_short=0.2, push_overtravel=0.10,
)


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
        c = c.cut(G.cyl_z(x, y, N["plenum"][5] - 0.1, N["pad_z"][1] + 0.1, N["vac_d"] / 2))
    vy, vz, vd, vxe = N["vac_stub"]
    c = c.cut(G.cyl_x(vy, vz, bx0 - 0.1, 5.0, vd / 2))                      # bore from the -X face to under the plenum
    c = c.cut(G.cyl_z(5.0, vy, vz, N["plenum"][4] + 0.1, vd / 2))            # up into the plenum
    c = c.union(G.cyl_x(vy, vz, vxe, bx0 + 0.01, vd / 2 + 0.5).cut(G.cyl_x(vy, vz, vxe - 0.1, bx0 + 0.1, vd / 2)))   # stub tube
    ty, tz, td, tdepth = N["therm"]
    c = c.cut(G.cyl_x(ty, tz, bx1 - tdepth, bx1 + 0.1, td / 2))
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
        c = c.cut(G.cyl_z(x, y, z0 - 0.1, z1 + 0.1, 1.1))
    for (x, y) in ((11.8, -1.2), (-1.8, 7.2)):                                   # 2 x dia 1.5 dowels
        c = c.cut(G.cyl_z(x, y, z0 - 0.1, z1 + 0.1, 0.75))
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


def riser(table_z=-86.0, kb_top=None):
    """T-shaped riser: narrow neck (cage width in Y) from the cage plate down past the holders' underside,
    wide body below with the TEC pocket, wire channel and the vacuum stub clearance; sits on the KB1X1."""
    kb_top = table_z + 20 if kb_top is None else kb_top
    nx0, nx1, ny0, ny1 = N["neck"]
    wx0, wx1, wy0, wy1 = N["wide"]
    r = box(wx0, wx1, wy0, wy1, kb_top, N["wide_top"]).union(box(nx0, nx1, ny0, ny1, N["neck_bottom"], N["cage"][4]))
    bx0, bx1, by0, by1 = N["block"]
    r = r.cut(box(bx0 - 0.3, bx1 + 0.3, by0 - 0.3, by1 + 0.3, N["tec_z"] - 0.1, N["cage"][4] + 0.1))   # slot for the copper neck (air gap)
    w, d, h = N["tec"]; cx_, cy_ = N["tec_c"]
    r = r.cut(box(cx_ - w / 2 - 0.2, cx_ + w / 2 + 0.2, cy_ - d / 2 - 0.2, cy_ + d / 2 + 0.2, N["tec_z"] - h - 0.05, N["tec_z"] + 0.1))
    r = r.cut(box(wx0 - 0.1, cx_ - w / 2, cy_ - 2.0, cy_ + 2.0, N["tec_z"] - h, N["tec_z"] + 0.1))         # TEC wire channel to -X
    vy, vz, vd, vxe = N["vac_stub"]
    r = r.cut(G.cyl_x(vy, vz, nx0 - 0.1, bx0, vd / 2 + 1.0))                                            # vacuum stub clearance
    ty, tz, td, _ = N["therm"]
    r = r.cut(G.cyl_x(ty, tz, bx1, nx1 + 0.1, td / 2 + 0.6))                                            # thermistor wire clearance
    for (x, y) in ((-1.8, -1.2), (11.8, 7.2)):                                                            # M2 tapped for the cage
        r = r.cut(G.cyl_z(x, y, N["cage"][4] - 4.0, N["cage"][4] + 0.1, 0.8))
    for (x, y) in ((11.8, -1.2), (-1.8, 7.2)):
        r = r.cut(G.cyl_z(x, y, N["cage"][4] - 3.0, N["cage"][4] + 0.1, 0.75))
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


def bb(w):
    b = w.val().BoundingBox(); return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def gap(a, b):
    return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3], a[4] - b[5], b[4] - a[5])


def main():
    ch, cg, rs, te = chuck(), cage(), riser(), tec()
    die_seated = G.die()
    die_placed = G.die().translate((-N["place_short"], 0, 0))
    die_yoff = G.die().translate((-N["place_short"], -0.4, 0))
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
    wide = box(wx0, wx1, wy0, wy1, -86 + 20, N["wide_top"])
    pad = box(N["pad"][0], N["pad"][1], N["pad"][2], N["pad"][3], N["pad_z"][0], N["pad_z"][1])

    px0, px1, py0, py1 = N["pad"]
    pad_area = (px1 - px0) * (py1 - py0)
    rep = [
        "Nest: lapped copper chuck pad -> Z/pitch/roll; +X Semitron stop pads (Y 0.6-1.2, 4.8-5.4; 4.2 mm base) -> X and yaw;",
        f"Y free within +/-{N['yguard_gap']} mm (corner guards). Fiber protrusion {N['fiber_protrusion']} mm: holder bodies at Y <= -{N['fiber_protrusion']} and >= {W + N['fiber_protrusion']}.",
        f"Chuck pad {px1 - px0:.0f} x {py1 - py0:.0f} mm = {100 * pad_area / (L * W):.0f} % of the backside on metal, 0.5 mm inboard of every edge; "
        f"{len(N['vac_holes'])} x dia {N['vac_d']} vacuum holes; copper neck to a {N['tec'][0]:.0f} x {N['tec'][1]:.0f} TEC at Z {N['tec_z']}.",
        f"Push-to-stop: set down {N['place_short']} mm short, jaws open, gripper +{push:.2f} mm -> near nose seats the die with "
        f"{G.flexure_k() * N['push_overtravel'] * 1e-3:.2f} N (blade overtravel {N['push_overtravel']} mm).",
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
    rep.append("near nose face at the end of the push: X %.2f = blade overtravel (die -X end face at X 0.00 on the pads)"
               % (-N["place_short"] + G.near_face_x - o + push))
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(OUT, "nest_checks.txt"), "w") as f:
        f.write(txt + "\n")

    parts = {"nest_chuck_copper": ch, "nest_cage_semitron": cg, "nest_riser_6061": rs}
    for name, shape in parts.items():
        exporters.export(shape, os.path.join(OUT, f"{name}.step"))
        if name != "nest_riser_6061":
            exporters.export(shape, os.path.join(OUT, f"{name}.stl"), tolerance=0.005, angularTolerance=0.1)
    for old in ("nest_rail_insert_17-4.step", "nest_rail_insert_17-4.stl"):
        try: os.remove(os.path.join(OUT, old))
        except OSError: pass
    col = {"nest_chuck_copper": (0.72, 0.45, 0.20), "nest_cage_semitron": (0.16, 0.16, 0.18), "nest_riser_6061": (0.60, 0.63, 0.68),
           "tec_15x15": (0.85, 0.85, 0.88)}
    assy = cq.Assembly(name="nest_module")
    for n, s in {**parts, "tec_15x15": te}.items():
        assy.add(s, name=n, color=cq.Color(*col[n], 1.0))
    assy.add(die_seated, name="die_seated", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k, v in grip_closed.items():
        assy.add(v, name=f"gripper_{k}_closed", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    for k, v in fib.items():
        assy.add(v, name=k, color=cq.Color(0.94, 0.82, 0.50, 0.35))
    assy.save(os.path.join(OUT, "nest_module_assembly.step"))
    a2 = cq.Assembly(name="nest_module_setdown")
    for n, s in {**parts, "tec_15x15": te}.items():
        a2.add(s, name=n, color=cq.Color(*col[n], 1.0))
    a2.add(die_placed, name="die_set_down", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k in ("far_tip", "near_tip", "blade", "near_arm", "far_arm"):
        a2.add(grip_open[k].translate((-N["place_short"], 0, 0)), name=f"gripper_{k}_open", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    a2.save(os.path.join(OUT, "nest_module_setdown.step"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

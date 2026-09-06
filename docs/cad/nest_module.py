"""
Self-registering nest ("chip stage") for the die tester.

The die is set down by the end-face gripper onto two lapped backside vacuum rails and then
pushed, by the gripper's own compliant nose, against two hard-stop pads on its +X end face.
The pads fix X and yaw mechanically; the rails fix Z, pitch and roll; Y is left free (the
fiber stages approach along Y and measure the gap anyway) but is caged to +/-0.6 mm by four
corner blocks that never touch the die in normal operation. Nothing ever stands in front
of a facet where a fiber can go (X 1..9), nothing touches the top surface.

Frame = gripper frame: X die long axis, Y optical axis, Z up, die bottom at the nest = 0.

Parts (all in docs/cad/out/):
  nest_rail_insert_17-4{.step,.stl}   17-4 PH (or hard-anodized 6061), rails lapped coplanar, 8 vacuum ports
  nest_cage_semitron{.step,.stl}      Semitron ESd 480 frame with the 4 corner blocks (X stop pads + guards)
  nest_riser_6061.step                riser column on the KB1X1 kinematic base, M5 vacuum port
  nest_module_assembly.step           insert + cage + riser + die + gripper (closed and open) + fiber stubs
  nest_checks.txt                     clearances of the cage vs the gripper (both jaw states), fibers, die

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
    # backside rails (existing): 1 mm inboard of the facets, lapped tops define Z / pitch / roll
    rail_y=((1.0, 1.9), (4.1, 5.0)), rail_z=(-1.5, 0.0),
    port_x=(1.5, 4.0, 6.5, 9.0), port_d=0.6,
    # rail insert body and the cage frame that surrounds it
    insert=(-1.5, 11.5, 0.6, 5.4, -4.5, -1.5),
    cage=(-2.5, 12.5, -2.0, 8.0, -4.5, -1.5),
    # contact band on the end faces: same band the gripper noses use (top 0.10 below the die top)
    post_z1=0.40, post_z0=-1.5,
    # +X hard-stop pads: two pads 0.6 wide on the end face, 0.6 mm in from each facet -> yaw from a 4.2 mm base
    stop_x=10.0, pad_t=0.6, pad_y=((0.6, 1.2), (4.8, 5.4)), relief=0.2,
    # -X guard bar (0.4 mm gap): stops the die sliding off the rails toward -X; same Y pads, recessed elsewhere
    guard_gap=0.4,
    # Y guard legs: 0.6 mm outside each facet plane, only at the die corners (X <= 0.5 and >= 9.5) where no fiber goes
    yguard_gap=0.6, yguard_t=0.4, yguard_len=1.5,
    # push-to-stop: the die is set down this far short of the pads, then the near nose pushes it home
    place_short=0.2, push_overtravel=0.10,
    # riser (existing)
    riser=(-8, 18, -10, 16),
)


# ----------------------------------------------------------------------------
# Parts
# ----------------------------------------------------------------------------
def rail_insert():
    x0, x1, y0, y1, z0, z1 = N["insert"]
    ins = box(x0, x1, y0, y1, z0, z1)
    for (ya, yb) in N["rail_y"]:
        ins = ins.union(box(0, L, ya, yb, N["rail_z"][0], N["rail_z"][1]))
    for x in N["port_x"]:
        for (ya, yb) in N["rail_y"]:
            ins = ins.cut(G.cyl_z(x, (ya + yb) / 2, z0 - 0.1, N["rail_z"][1] + 0.1, N["port_d"] / 2))
    # vacuum plenum under the rails, fed from the riser's M5 port
    ins = ins.cut(box(0.5, L - 0.5, y0 + 0.5, y1 - 0.5, z0 - 0.1, z0 + 1.5))
    return ins


def corner_block(sx, sy):
    """One corner block; sx = +1 for the +X (stop) end, -1 for the -X (guard) end; sy = +1 for +Y, -1 for -Y.
    Bar along Y on the end-face side with a contact face only in the pad zone (relief elsewhere), plus a
    leg along X outside the facet plane (Y guard)."""
    z0, z1 = N["post_z0"], N["post_z1"]
    t = N["pad_t"]
    if sx > 0:
        face = N["stop_x"]; xb0, xb1 = face, face + t
    else:
        face = -N["guard_gap"]; xb0, xb1 = face - t, face
    # pad zone in Y (nearest this corner)
    (pa, pb) = N["pad_y"][1] if sy > 0 else N["pad_y"][0]
    yg = W + N["yguard_gap"] if sy > 0 else -N["yguard_gap"]                 # Y-guard face
    yo = yg + N["yguard_t"] * sy                                              # its outer face
    ylo, yhi = (pa, yo) if sy > 0 else (yo, pb)
    bar = box(xb0, xb1, ylo, yhi, z0, z1)
    # relieve the bar face by 0.2 outside the pad zone so only the pad touches the end face
    if sy > 0:
        rel = box(face - 1 if sx < 0 else face, face + 1 if sx > 0 else face, pb, yhi + 0.1, z0 - 0.1, z1 + 0.1)
    else:
        rel = box(face - 1 if sx < 0 else face, face + 1 if sx > 0 else face, ylo - 0.1, pa, z0 - 0.1, z1 + 0.1)
    rel = rel.intersect(box(min(face, face + sx * N["relief"]), max(face, face + sx * N["relief"]), -10, 20, z0 - 1, z1 + 1))
    bar = bar.cut(rel)
    # Y-guard leg along X, outside the facet plane, at the die corner only
    if sx > 0:
        lx0, lx1 = L - N["yguard_len"] + 1.0, xb1              # X 9.5..10.6
    else:
        lx0, lx1 = xb0, N["yguard_len"] - 1.0                  # X -1.0..0.5
    leg = box(lx0, lx1, min(yg, yo), max(yg, yo), z0, z1)
    return bar, leg


def corner_union(sx, sy):
    bar, leg = corner_block(sx, sy)
    return bar.union(leg)


def cage():
    x0, x1, y0, y1, z0, z1 = N["cage"]
    c = box(x0, x1, y0, y1, z0, z1)
    ix0, ix1, iy0, iy1, _, _ = N["insert"]
    c = c.cut(box(ix0 - 0.05, ix1 + 0.05, iy0 - 0.05, iy1 + 0.05, z0 - 0.1, z1 + 0.1))   # window for the insert
    for sx in (-1, 1):
        for sy in (-1, 1):
            c = c.union(corner_union(sx, sy))
    # 2 x M2 to the riser, 2 x dia 1.5 dowels
    for (x, y) in ((-1.8, -1.2), (11.8, 7.2)):
        c = c.cut(G.cyl_z(x, y, z0 - 0.1, z1 + 0.1, 1.1))
    for (x, y) in ((11.8, -1.2), (-1.8, 7.2)):
        c = c.cut(G.cyl_z(x, y, z0 - 0.1, z1 + 0.1, 0.75))
    return c


def cage_parts():
    """The cage as separate members (plate, 4 bars, 4 legs) for per-member clearance checks."""
    x0, x1, y0, y1, z0, z1 = N["cage"]
    parts = [box(x0, x1, y0, y1, z0, z1)]
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts += list(corner_block(sx, sy))
    return parts


def riser(table_z=-86.0, kb_top=None):
    x0, x1, y0, y1 = N["riser"]
    kb_top = table_z + 20 if kb_top is None else kb_top
    r = box(x0, x1, y0, y1, kb_top, N["cage"][4])
    r = r.cut(G.cyl_y(5, -30, -12.5, 3.0, 2.0))                                  # M5 vacuum port from the -Y face
    r = r.cut(G.cyl_z(5, G.die_cy, -30, N["cage"][4] + 0.1, 1.0))                 # riser to plenum
    return r


# ----------------------------------------------------------------------------
# Context and checks
# ----------------------------------------------------------------------------
def fiber_envelopes():
    """Volumes a fiber or its holder can occupy near the die: fiber dia 0.125 at the die-top height over X 1..9
    (waveguides are >= 1.5 from the die ends), clamp bodies further out."""
    fz0, fz1 = T - 0.0625 - 0.05, T + 0.0625 + 0.05
    return {
        "fiber_in": box(1.0, 9.0, -12.0, 0.0, fz0, fz1),
        "fiber_out": box(1.0, 9.0, W, W + 12.0, fz0, fz1),
        "clamp_in": box(1.0, 9.0, -20.0, -12.0, -1.5, 2.5),
        "clamp_out": box(1.0, 9.0, W + 12.0, W + 20.0, -1.5, 2.5),
    }


def bb(w):
    b = w.val().BoundingBox(); return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def gap(a, b):
    return max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3], a[4] - b[5], b[4] - a[5])


def main():
    ins, cg, rs = rail_insert(), cage(), riser()
    die_seated = G.die()                                                 # end face on the stop pads: X 0..10
    die_placed = G.die().translate((-N["place_short"], 0, 0))            # as set down, before the push
    die_yoff = G.die().translate((-N["place_short"], -0.4, 0))           # worst-case Y offset from the tray pocket
    grip_closed = {"far_tip": G.far_tip_block(), "near_tip": G.near_tip_block(), "blade": G.blade(),
                   "near_arm": G.near_arm(), "far_arm": G.far_arm()}
    body, fn, ff = G.actuator(1.5)
    open_shift = 1.5
    grip_open = {"far_tip": G.far_tip_block().translate((open_shift, 0, 0)),
                 "near_tip": G.near_tip_block().translate((-open_shift, 0, 0)),
                 "blade": G.blade().translate((-open_shift, 0, 0)),
                 "near_arm": G.near_arm().translate((-open_shift, 0, 0)),
                 "far_arm": G.far_arm().translate((open_shift, 0, 0))}
    # jaws open and the gripper indexed +X to push the die home (near nose pushes the -X end face)
    push = open_shift - G.near_face_x + N["place_short"] + N["push_overtravel"]     # 1.735: near nose meets the end face, pushes 0.2, overtravels 0.1
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
    rep = ["Nest registration: rails -> Z/pitch/roll; +X pads (Y 0.6-1.2, 4.8-5.4, 4.2 mm base) -> X and yaw;",
           f"Y free within +/-{N['yguard_gap']} mm (corner guards). Push-to-stop: set down {N['place_short']} mm short, jaws open,",
           f"gripper +{push:.1f} mm -> near nose seats the die with {G.flexure_k() * N['push_overtravel'] * 1e-3:.2f} N (blade overtravel {N['push_overtravel']} mm).",
           f"Contact band on the end faces Z 0.05..{N['post_z1']} (top {T - N['post_z1']:.2f} below the die top), pads 0.6 mm from the facets.",
           ""]
    def check(an, a, bn, b, need=0.0):
        g = gap(bb(a), bb(b))
        flag = "  OK " if g > need else ("  TOUCH" if g > -1e-6 else "  ** OVERLAP **")
        rep.append(f"  {an:34s} vs {bn:26s}: {g:7.2f}{flag}")
    rep.append("cage blocks vs the die (must never be under it; +X pads touch the seated die's end face):")
    for bn, blk in blocks.items():
        check(bn, blk, "die seated", die_seated)
        check(bn, blk, "die set down (-0.2 X)", die_placed)
        check(bn, blk, "die Y-offset -0.4", die_yoff)
    rep.append("cage blocks vs the gripper, jaws CLOSED on the seated die:")
    for bn, blk in blocks.items():
        for gn, gp in grip_closed.items():
            check(bn, blk, f"{gn} (closed)", gp, need=0.2)
    rep.append("cage blocks vs the gripper, jaws OPEN (+/-1.5) at the set-down position:")
    for bn, blk in blocks.items():
        for gn in ("far_tip", "near_tip", "blade"):
            check(bn, blk, f"{gn} (open)", grip_open[gn].translate((-N["place_short"], 0, 0)), need=0.2)
    rep.append("cage blocks vs the gripper during the push (jaws open, +X indexed):")
    for bn, blk in blocks.items():
        for gn in ("far_tip", "near_tip", "blade"):
            check(bn, blk, f"{gn} (push)", grip_push[gn], need=0.2)
    rep.append("cage blocks, cage plate and insert vs fiber / holder envelopes:")
    for fn_, fe in fib.items():
        for bn, blk in blocks.items():
            check(bn, blk, fn_, fe, need=0.3)
        check("cage plate", plate, fn_, fe, need=0.3)
        check("rail insert", ins, fn_, fe, need=0.3)
    rep.append("near nose face at the end of the push: X %.2f = blade overtravel (die -X end face at X 0.00 on the pads)"
               % (-N["place_short"] + G.near_face_x - open_shift + push))
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(OUT, "nest_checks.txt"), "w") as f:
        f.write(txt + "\n")

    # ---- exports ----
    parts = {"nest_rail_insert_17-4": ins, "nest_cage_semitron": cg, "nest_riser_6061": rs}
    for name, shape in parts.items():
        exporters.export(shape, os.path.join(OUT, f"{name}.step"))
        if name != "nest_riser_6061":
            exporters.export(shape, os.path.join(OUT, f"{name}.stl"), tolerance=0.005, angularTolerance=0.1)
    assy = cq.Assembly(name="nest_module")
    assy.add(ins, name="nest_rail_insert_17-4", color=cq.Color(0.56, 0.56, 0.58, 1.0))
    assy.add(cg, name="nest_cage_semitron", color=cq.Color(0.16, 0.16, 0.18, 1.0))
    assy.add(rs, name="nest_riser_6061", color=cq.Color(0.60, 0.63, 0.68, 1.0))
    assy.add(die_seated, name="die_seated", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k, v in grip_closed.items():
        assy.add(v, name=f"gripper_{k}_closed", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    for k, v in fib.items():
        assy.add(v, name=k, color=cq.Color(0.94, 0.82, 0.50, 0.35))
    assy.save(os.path.join(OUT, "nest_module_assembly.step"))
    # a second assembly: jaws open at the set-down position, for the push step
    a2 = cq.Assembly(name="nest_module_setdown")
    a2.add(ins, name="nest_rail_insert_17-4", color=cq.Color(0.56, 0.56, 0.58, 1.0))
    a2.add(cg, name="nest_cage_semitron", color=cq.Color(0.16, 0.16, 0.18, 1.0))
    a2.add(die_placed, name="die_set_down", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for k in ("far_tip", "near_tip", "blade", "near_arm", "far_arm"):
        a2.add(grip_open[k].translate((-N["place_short"], 0, 0)), name=f"gripper_{k}_open", color=cq.Color(0.55, 0.58, 0.62, 1.0))
    a2.save(os.path.join(OUT, "nest_module_setdown.step"))
    print("wrote", OUT)


if __name__ == "__main__":
    main()

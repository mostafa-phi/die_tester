"""
Wafer tray: one 100 mm wafer of 10 x 6 mm dies = 8 columns x 14 rows = 112 pockets, all dies in one
orientation. Each die returns to its own pocket after test, so (row, column) is the die's identity and
mirrors the wafer map. SLA printed (Formlabs Rigid 10K / Protolabs Accura), lidded, DataMatrix on the rim.

Pocket: cavity 12.0 x 6.8 mm holds the die by its four corners to +/-1.0 mm in X and +/-0.4 mm in Y
(inside the open jaws' +/-1.9 mm capture). Both end walls carry a 3.6 mm wide nose slot (Y 1.2..4.8)
for the open jaw tip blocks; with the 16 mm column pitch the slots of neighbouring pockets meet, so
the slot is a through channel along each column, closed only by the tray rims (slot_depth sets how far
the channel runs into the rim: the open tip blocks reach 3.44 mm beyond the die origin). Two 1.0 mm
ledges under the facet-edge strips carry the die 0.8 mm above the cavity floor; the pocket walls stop
0.8 mm above the die bottom (0.3 above the die top). Nothing touches the facets or the top surface.

Frame, die and contact rules: cad/common. In the station (cad/station) the tray rides on the Y-stage deck;
columns run along X (the transfer direction), rows along Y.

Outputs (this folder):
  STEP/wafer_tray_8x14.step, STL/wafer_tray_8x14.stl   the tray in its own frame (deck top Z 0, pocket (0,0) die origin at X 0, Y 0)
  STEP/tray_pocket_check.step                          one pocket with the open gripper at the set-down height
  checks.txt                                           pocket vs die retention and vs the open jaws

Run:  python cad/tray/model.py   (or python cad/build.py)
"""
from __future__ import annotations
import os
import sys
import cadquery as cq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # cad/
import common as C                                                             # noqa: E402
from common import box, bb, gap                                                # noqa: E402
from gripper import model as G                                                 # noqa: E402

DIRS = C.out_dirs(__file__)
L, W, T = C.DIE_LEN, C.DIE_WID, C.DIE_THK

TR = dict(
    cols=8, rows=14, col_pitch=16.0, row_pitch=7.5,
    col0_x=-150.0,                 # station: die X of the first (nearest) column; last column at -150 - 7*16 = -262
    floor_t=2.2,                   # cavity floor above the deck
    ledge_w=1.0, ledge_h=0.8,      # ledges under the facet-edge strips; ledge top = die bottom
    wall_above_die=0.8,            # wall top above the die bottom
    cav_x=(-1.0, 11.0),            # cavity X relative to the die origin: +/-1.0 retention by the corners
    cav_y=(-0.4, 6.4),             # cavity Y: +/-0.4 retention
    slot_depth=2.8, slot_y=(1.2, 4.8),   # nose slot channel (3.6 wide) runs this far beyond the cavity into the rims
    rim_x=(5.0, 15.0),             # tray rim beyond the last pocket's die origin (-X side) and the first pocket's (+X side)
    rim_y=0.75,                    # half of the extra length in Y
    jaw_open=1.5,                  # per-side jaw opening at the tray (of the 2.0 available)
)


def extents(x_first, yc):
    """Tray footprint for the die-origin X of column 0 and the Y of the active row centre (rows centred on yc)."""
    nc, nr, pc, pr = TR["cols"], TR["rows"], TR["col_pitch"], TR["row_pitch"]
    x0 = x_first - (nc - 1) * pc - TR["rim_x"][0]
    x1 = x_first + TR["rim_x"][1]
    len_y = nr * pr + 2 * TR["rim_y"]
    return x0, x1, yc - len_y / 2, yc + len_y / 2


def pocket_origins(x_first, yc):
    """(column, row, die X, die Y) of every pocket's die origin (die corner X 0 / Y 0)."""
    nc, nr, pc, pr = TR["cols"], TR["rows"], TR["col_pitch"], TR["row_pitch"]
    out = []
    for c in range(nc):
        xd = x_first - c * pc
        for k in range(nr):
            yd = yc + (k - (nr - 1) / 2) * pr - W / 2
            out.append((c, k, xd, yd))
    return out


def pocket_features(xd, yd, z_deck):
    """(cavities, ledges) solids for one pocket whose die origin is (xd, yd) on a deck top at z_deck."""
    z_floor = z_deck + TR["floor_t"]
    z_led = z_floor + TR["ledge_h"]                       # die bottom
    z_top = z_led + TR["wall_above_die"] + 0.2            # cut through the wall top
    cx0, cx1 = TR["cav_x"]; cy0, cy1 = TR["cav_y"]; sy0, sy1 = TR["slot_y"]; sd = TR["slot_depth"]
    cavities = [box(xd + cx0, xd + cx1, yd + cy0, yd + cy1, z_floor, z_top).val(),
                box(xd + cx0 - sd, xd + cx0, yd + sy0, yd + sy1, z_floor, z_top).val(),
                box(xd + cx1, xd + cx1 + sd, yd + sy0, yd + sy1, z_floor, z_top).val()]
    lw = TR["ledge_w"]
    ledges = [box(xd, xd + L, yd + cy0 + 0.8, yd + cy0 + 0.8 + lw, z_floor, z_led).val(),
              box(xd, xd + L, yd + cy1 - 0.8 - lw, yd + cy1 - 0.8, z_floor, z_led).val()]
    return cavities, ledges


def tray(x_first, yc, z_deck):
    """The tray solid on a deck top at z_deck. Returns (tray, z_die_bottom, (x0, x1, y0, y1))."""
    x0, x1, y0, y1 = extents(x_first, yc)
    z_led = z_deck + TR["floor_t"] + TR["ledge_h"]
    slab = box(x0, x1, y0, y1, z_deck, z_led + TR["wall_above_die"])
    cavities, ledges = [], []
    for _, _, xd, yd in pocket_origins(x_first, yc):
        cv, ld = pocket_features(xd, yd, z_deck)
        cavities += cv; ledges += ld
    slab = slab.cut(cq.Workplane().add(cq.Compound.makeCompound(cavities)))
    slab = slab.union(cq.Workplane().add(cq.Compound.makeCompound(ledges)))
    return slab, z_led, (x0, x1, y0, y1)


def pocket_walls(xd, yd, z_deck):
    """The wall, rim and ledge members around ONE pocket as separate boxes (for per-member clearance checks).
    The pocket is treated as an end pocket on both sides (rim at -X and at +X): the worst case."""
    z_floor = z_deck + TR["floor_t"]; z_led = z_floor + TR["ledge_h"]; z_top = z_led + TR["wall_above_die"]
    cx0, cx1 = TR["cav_x"]; cy0, cy1 = TR["cav_y"]; sy0, sy1 = TR["slot_y"]; sd = TR["slot_depth"]
    pc, pr = TR["col_pitch"], TR["row_pitch"]
    m = {}
    # end walls beside the slots (four pieces) and the wall material beyond the slot depth
    m["-X wall (-Y of slot)"] = box(xd + cx0 - sd, xd + cx0, yd + cy0, yd + sy0, z_floor, z_top)
    m["-X wall (+Y of slot)"] = box(xd + cx0 - sd, xd + cx0, yd + sy1, yd + cy1, z_floor, z_top)
    m["+X wall (-Y of slot)"] = box(xd + cx1, xd + cx1 + sd, yd + cy0, yd + sy0, z_floor, z_top)
    m["+X wall (+Y of slot)"] = box(xd + cx1, xd + cx1 + sd, yd + sy1, yd + cy1, z_floor, z_top)
    m["-X rim (slot end)"] = box(xd - TR["rim_x"][0], xd + cx0 - sd, yd + sy0, yd + sy1, z_floor, z_top)
    m["+X rim (slot end)"] = box(xd + cx1 + sd, xd + TR["rim_x"][1], yd + sy0, yd + sy1, z_floor, z_top)
    m["-Y side wall"] = box(xd + cx0, xd + cx1, yd + cy1 - pr, yd + cy0, z_floor, z_top)
    m["+Y side wall"] = box(xd + cx0, xd + cx1, yd + cy1, yd + cy0 + pr, z_floor, z_top)
    m["floor"] = box(xd + cx0 - sd, xd + cx1 + sd, yd + cy0, yd + cy1, z_deck, z_floor)
    lw = TR["ledge_w"]
    m["-Y ledge"] = box(xd, xd + L, yd + cy0 + 0.8, yd + cy0 + 0.8 + lw, z_floor, z_led)
    m["+Y ledge"] = box(xd, xd + L, yd + cy1 - 0.8 - lw, yd + cy1 - 0.8, z_floor, z_led)
    return m


def main():
    # shop file in the tray's own frame: deck top Z 0, pocket (col 0, row centre) die origin at X 0
    nr, pr = TR["rows"], TR["row_pitch"]
    yc = W / 2
    tr, z_led, ext = tray(0.0, yc, 0.0)
    C.export_part(tr, DIRS, "wafer_tray_8x14", tolerance=0.02, angular=0.2)

    # ---- checks on one pocket: die retention, open jaws, bars, gripper at the set-down height ----
    xd, yd = 0.0, 0.0
    walls = pocket_walls(xd, yd, 0.0)
    die_c = C.die().translate((xd, yd, z_led))
    o = TR["jaw_open"]
    gz = z_led
    jaws = {"near_tip (open)": G.near_tip_block().translate((xd - o, yd, gz)),
            "far_tip (open)": G.far_tip_block().translate((xd + o, yd, gz)),
            "blade (open)": G.blade().translate((xd - o, yd, gz)),
            "near_arm (open)": G.near_arm().translate((xd - o, yd, gz)),
            "far_arm (open)": G.far_arm().translate((xd + o, yd, gz))}
    cx0, cx1 = TR["cav_x"]; cy0, cy1 = TR["cav_y"]; sy0, sy1 = TR["slot_y"]
    rep = [
        f"Wafer tray {TR['cols']} x {TR['rows']} = {TR['cols'] * TR['rows']} pockets, {ext[1] - ext[0]:.0f} x {ext[3] - ext[2]:.0f} mm, "
        f"column pitch {TR['col_pitch']} (X), row pitch {TR['row_pitch']} (Y); walls {TR['floor_t'] + TR['ledge_h'] + TR['wall_above_die']:.1f} tall.",
        f"Pocket cavity {cx1 - cx0:.1f} x {cy1 - cy0:.1f}: die retained to +/-{-cx0:.1f} mm in X (jaw capture +/-{o + 0.4:.1f}) "
        f"and +/-{-cy0:.1f} mm in Y; nose slots {sy1 - sy0:.1f} wide (contact band {C.CONTACT_Y0}..{C.CONTACT_Y1}), "
f"through between pockets and {TR['slot_depth']} into the rims; ledges {TR['ledge_w']} wide x {TR['ledge_h']} tall under the facet-edge strips.",
        f"Die on the ledges at Z {z_led:.1f} above the deck; wall top {TR['wall_above_die'] - T:.1f} mm above the die top.",
        "",
        "pocket members vs the die on its ledges (only the ledges touch; positive = clear):",
    ]

    def check(an, a, bn, b, need):
        g = gap(bb(a), bb(b))
        rep.append(f"  {an:22s} vs {bn:18s}: {g:7.2f}{C.flag(g, need, -1e-6)}")

    for wn, w in walls.items():
        check(wn, w, "die", die_c, 0.0 if "ledge" in wn else 0.3)
    rep.append("pocket members vs the open gripper at the set-down height (jaws +/-%.1f):" % o)
    for jn, j in jaws.items():
        for wn, w in walls.items():
            if wn == "floor" and "arm" in jn:
                continue
            check(wn, w, jn, j, 0.3)
    rep.append("bars vs the wall tops: the arm bars run 5 mm above the die bottom, walls end 0.8 above it.")
    txt = "\n".join(rep); print(txt)
    with open(os.path.join(DIRS["comp"], "checks.txt"), "w") as f:
        f.write(txt + "\n")

    # one-pocket check assembly
    one = box(xd - TR["rim_x"][0], xd + TR["rim_x"][1], yd + cy1 - pr, yd + cy0 + pr, 0, z_led + TR["wall_above_die"])
    cv, ld = pocket_features(xd, yd, 0.0)
    one = one.cut(cq.Workplane().add(cq.Compound.makeCompound(cv))).union(cq.Workplane().add(cq.Compound.makeCompound(ld)))
    a = cq.Assembly(name="tray_pocket_check")
    a.add(one, name="pocket", color=cq.Color(0.85, 0.81, 0.68, 1.0))
    a.add(die_c, name="die", color=cq.Color(0.81, 0.89, 0.97, 1.0))
    for jn, j in jaws.items():
        a.add(j, name=jn.split(" ")[0], color=cq.Color(0.55, 0.58, 0.62, 1.0))
    a.save(os.path.join(DIRS["STEP"], "tray_pocket_check.step"))
    print("wrote", DIRS["comp"])


if __name__ == "__main__":
    main()

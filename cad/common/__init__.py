"""
Shared definitions for every CAD component in cad/.

Everything two or more components need lives here, so a number can only be changed in
one place:  the die, the contact rules, the fiber-holder envelope, the CadQuery box /
cylinder helpers, the AABB clearance functions and the per-component output layout.

Frame (all components, the docs and the three.js viewer):
    X = die long axis (10 mm), gripper stroke / transfer direction, +X toward the far end face
    Y = die optical axis (6 mm); the fibers approach along -Y (input) and +Y (output)
    Z = up; Z = 0 is the die's BOTTOM face when the die sits on the nest

Contact rules (never violated by any part, in any state):
    - the facets (Y = 0 and Y = 6 faces) and the top surface are never touched;
    - the die is held or pushed only on its END faces (X = 0 / X = 10), inside the band
      CONTACT_Y0..CONTACT_Y1 and CONTACT_Z0..CONTACT_Z1 (top of the band NOSE_GAP_TOP below the die top);
    - the backside may rest on the chuck pad / tray ledges, nothing else touches it.
"""
from __future__ import annotations

import os
import cadquery as cq

# ----------------------------------------------------------------------------
# Die (TFLN, air clad, singulated)
# ----------------------------------------------------------------------------
DIE_LEN, DIE_WID, DIE_THK = 10.0, 6.0, 0.5
DIE_LEN_TOL = 0.025                 # +/- on the dicing length
DIE_TOP = DIE_THK
DIE_CY = DIE_WID / 2.0              # 3.0, optical-axis centre

# end-face contact band (concept study Fig. 3): middle 3 mm of the end face, 0.35 tall, 0.10 below the top
NOSE_H = 0.35
NOSE_GAP_TOP = 0.10
CONTACT_Y0, CONTACT_Y1 = 1.5, 4.5
CONTACT_Z0 = DIE_THK - NOSE_GAP_TOP - NOSE_H      # 0.05
CONTACT_Z1 = DIE_THK - NOSE_GAP_TOP               # 0.40

# ----------------------------------------------------------------------------
# Fiber side envelope (measure on the bench; used by the nest and the station)
# ----------------------------------------------------------------------------
FIBER = dict(
    protrusion=5.0,                 # fiber tip beyond the holder front face
    holder_w=25.0,                  # holder body width along X (centred on the die)
    holder_zb=-8.0, holder_zt=4.0,  # holder body bottom / top relative to the die bottom (fiber axis at Z 0.5)
    holder_len=20.0,                # holder body length along Y (envelope only)
    retract=1.0,                    # fiber retract along +/-Y before the gripper moves
)

# ----------------------------------------------------------------------------
# Microscope envelope (measure: WD and what sits above the objective)
# ----------------------------------------------------------------------------
OBJ_WD, OBJ_DIA, TUBE_DIA = 20.0, 34.0, 40.0

# ----------------------------------------------------------------------------
# Bench levels: the optical-table plane follows from the fiber stages (NanoMax 300 deck + platform + holder)
# putting the fiber axis at the die-top height. Everything under the die (nest stack) is built up from TABLE_Z.
# ----------------------------------------------------------------------------
NANOMAX = dict(w=112.0, h=62.5, platform_h=4.0, gap_y=45.0)   # footprint, deck height, top platform, inner face to facet
HOLDER_AXIS_ABOVE_DECK = 20.0                                  # fiber axis above the NanoMax platform (holder-dependent; measure)
NANOMAX_RISER = 25.0                                           # riser plate under each NanoMax (and under the Y stage): the motorized
                                                               # die-stage stack (KB1X1 + RMPG40W-N 35 + KXC04015 30 + riser) needs
                                                               # 100 mm under the die; the fiber stages set the table plane, so they rise
TABLE_Z = DIE_TOP - HOLDER_AXIS_ABOVE_DECK - NANOMAX["h"] - NANOMAX["platform_h"] - NANOMAX_RISER   # -111.0
KB1X1_H = 12.7                                                 # Thorlabs KB1X1 kinematic base, assembled height (vendor STEP 2374-E0W)

# ----------------------------------------------------------------------------
# MISUMI LX20 single-axis actuator: the station's transport axes X, Y and Z (chosen over the Velmex BiSlide for cost
# and speed; the die is placed by hard references, the axes only need +/-0.15 mm at the nest and +/-0.05 mm in Z).
# Catalog (MISUMI FA 2014 p.417, LXM p.401, LX guide pp.43-47): ground ball screw dia 6, lead 1 or 5 (lead 5 used:
# 690 mm/s screw-rated, ~200 mm/s with a 42 sq stepper), repeatability +/-0.005 mm, backlash 0.01, running
# parallelism 0.025, allowable static moment Ma/Mb 27 N.m and Mc 93 N.m with one long block, base lengths
# 100/150/200/250/300 with effective stroke L - 63.5, motor adapters T2028 / T2042 / T2056.4 for 28 / 42 / 56.4 sq
# steppers. Dimensions confirmed against the manufacturer STEP (cad/vendor/misumi_LX2005CG-B1-A2040-<L>.step,
# CADENAS export, Sept 2026; 8 solids: body with the motor-bracket casting, cover strip, table plate, adapter plate
# and its 4 screws): in the file the axis runs along +x with the motor beyond x < 0, the rail bottom is y = 0
# (mounting face, up = +y) and the width runs along z. The motor itself is not in the file (envelope below).
# ----------------------------------------------------------------------------
LX20 = dict(
    # cover type (LX2005CG: cover included, low-particulate grease): 40 wide x 26.5 tall body (rail + cover strip),
    # 52 wide table plate 57 long with its top 27 above the rail bottom; the motor-bracket casting continues the
    # body section 56 mm beyond the rail, then the 40 x 40 x 13 adapter plate centred on the screw axis.
    base_w=40.0, base_h=18.0,                        # base rail (mounting footprint; the risers are this wide)
    rail_w=40.0, rail_h=26.5,                        # body envelope: width across the axis, height above the rail bottom (cover top 26.2)
    block_w=52.0, block_len=57.0, block_top=27.0,    # table plate: width, length along the axis, top face above the rail bottom
    end_margin=3.25,                                 # rail end to table end at the travel limit: L = stroke + 57 + 2 x 3.25 (= stroke + 63.5)
    axis_h=13.0,                                     # screw axis above the rail bottom (a 40/42 sq motor then hangs 7-8 mm below the rail)
    bracket_len=56.0,                                # motor-bracket casting beyond the rail end (same 40 x 26.5 section as the body)
    plate_t=13.0, plate_sq=40.0,                     # motor adapter plate (A2040 as uploaded; T2042 for a 42 sq stepper has the same outline)
    motor_sq=42.0, motor_len=90.0,                   # motor envelope on the plate: 40 sq servo or 42 sq brake stepper, length assumed
    stroke={100: 36.5, 150: 86.5, 200: 136.5, 250: 186.5, 300: 236.5},   # effective stroke per base length L
    v_max=690.0, repeat=0.005, m_a=27.0, m_c=93.0,   # mm/s (screw-rated), mm, N.m, N.m
    mount_pitch=60.0, mount_hole=3.4,                # N x dia 3.4 through / dia 6.5 counterbore along the rail, pitch 60
    table_holes=(33.2, 20.0),                        # 4 x M4 through the table plate
    mass_per_100=0.22,                               # kg per 100 mm of rail (table included ~0.45 kg at L 100)
    file_rail_x0=56.0,                               # vendor file: rail starts at x 56 (x 0..56 is the bracket casting), motor plate x -13..0
)


# ----------------------------------------------------------------------------
# CadQuery helpers
# ----------------------------------------------------------------------------
def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from its extents."""
    return (cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False)
            .translate((x0, y0, z0)))


def cyl_z(x, y, z0, z1, r):
    return cq.Workplane("XY").center(x, y).circle(r).extrude(z1 - z0).translate((0, 0, z0))


def cyl_x(y, z, x0, x1, r):
    return cq.Workplane("XY").circle(r).extrude(x1 - x0).rotate((0, 0, 0), (0, 1, 0), 90).translate((x0, y, z))


def cyl_y(x, z, y0, y1, r):
    return cq.Workplane("XY").circle(r).extrude(y1 - y0).rotate((0, 0, 0), (1, 0, 0), -90).translate((x, y0, z))


def die():
    """The die at the nest: X 0..10, Y 0..6, Z 0..0.5."""
    return box(0, DIE_LEN, 0, DIE_WID, 0, DIE_THK)


def keepout(wd=OBJ_WD, dia=OBJ_DIA):
    """Objective keep-out cylinder above the die (front lens at WD above the die top)."""
    return cq.Workplane("XY").center(DIE_LEN / 2, DIE_CY).circle(dia / 2).extrude(wd).translate((0, 0, DIE_TOP))


# ----------------------------------------------------------------------------
# Clearance checks (axis-aligned bounding boxes)
# ----------------------------------------------------------------------------
def bb(shape):
    """(xmin, xmax, ymin, ymax, zmin, zmax) of a Workplane / Shape."""
    s = shape.val() if hasattr(shape, "val") else shape
    b = s.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def gap(a, b):
    """Separation between two AABBs: >0 = clear by that much (max over axes), <=0 = overlap in all axes."""
    dx = max(a[0] - b[1], b[0] - a[1])
    dy = max(a[2] - b[3], b[2] - a[3])
    dz = max(a[4] - b[5], b[4] - a[5])
    return max(dx, dy, dz)


def gap_parts(parts, b):
    """Separation of a union of shapes (list) from AABB b = min over the members' AABB gaps (no union-box conservatism)."""
    return min(gap(bb(pp), b) for pp in parts)


def gap_any(a, b):
    """gap() where either side may be a shape or a list of member shapes (min over all member pairs)."""
    al = a if isinstance(a, list) else [a]
    bl = b if isinstance(b, list) else [b]
    return min(gap(bb(x), bb(y)) for x in al for y in bl)


def gap_cyl(a, axis_xy, r, z0, z1):
    """Clearance of AABB a to a vertical cylinder: max(radial gap, vertical gap). >0 clear."""
    ax, ay = axis_xy
    dx = max(a[0] - ax, ax - a[1], 0.0); dy = max(a[2] - ay, ay - a[3], 0.0)
    radial = (dx ** 2 + dy ** 2) ** 0.5 - r
    vertical = max(z0 - a[5], a[4] - z1)
    return max(radial, vertical)


def flag(g, need=2.0, tight=0.0):
    return "  OK " if g > need else ("  TIGHT" if g > tight else "  ** OVERLAP **")


# ----------------------------------------------------------------------------
# Output layout: every component writes only into its own folder
#   <component>/STEP/*.step   <component>/STL/*.stl   <component>/renders/*.png   <component>/checks*.txt
# ----------------------------------------------------------------------------
CAD_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR_DIR = os.path.join(CAD_ROOT, "vendor")


def out_dirs(model_file):
    """Create and return the (STEP, STL, renders, component) folders for a component's model.py."""
    comp = os.path.dirname(os.path.abspath(model_file))
    d = {"STEP": os.path.join(comp, "STEP"), "STL": os.path.join(comp, "STL"),
         "renders": os.path.join(comp, "renders"), "comp": comp}
    for k in ("STEP", "STL", "renders"):
        os.makedirs(d[k], exist_ok=True)
    return d


def vendor_path(fname):
    return os.path.join(VENDOR_DIR, fname)


def export_part(shape, dirs, name, stl=True, tolerance=0.01, angular=0.1):
    """STEP (+ STL) for one custom part."""
    from cadquery import exporters
    exporters.export(shape, os.path.join(dirs["STEP"], f"{name}.step"))
    if stl:
        exporters.export(shape, os.path.join(dirs["STL"], f"{name}.stl"), tolerance=tolerance, angularTolerance=angular)

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

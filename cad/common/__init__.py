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
    protrusion=5.0,                 # bare fiber beyond the chuck tip, to the facet
    retract=1.0,                    # fiber retract along +/-Y before the gripper moves
    # Thorlabs holder stack on each NanoMax top platform (vendor STEP in cad/vendor; drawings 16022 / 10916 / 10907-E0W):
    # HCS013 RMS-threaded flexure-stage mount (25 wide x 20 deep x 25 tall, key in the platform's centre groove, locked by
    # two AMA010/M cleats, optical axis 12.5 above the platform) -> HFR001 fiber chuck rotator screwed into its front face
    # (dia 25 knurled body 24.1 long + 5 mm RMS thread, 360 deg rotation, three M3 nylon setscrews clamp the chuck)
    # -> HFC005 dia 1/4" fiber chuck (dia 6.35 x 70 brass, dia 200 um stripped fiber). The mount sits at the platform's inner
    # edge, so the chuck reaches the facet with 41.9 mm of its length beyond the rotator. No adapter plate is needed.
    mount_w=25.0, mount_d=20.0, mount_h=25.0, mount_axis=12.5, mount_flange=3.0,
    rotator_d=25.0, rotator_len=24.1, rotator_thread=5.0,
    chuck_d=6.35, chuck_len=70.0,
    mount_front=None,               # facet -> HCS013 front face (set below from the NanoMax geometry)
)

# ----------------------------------------------------------------------------
# Microscope envelope (measure: WD and what sits above the objective)
# ----------------------------------------------------------------------------
OBJ_WD, OBJ_DIA, TUBE_DIA = 20.0, 34.0, 40.0

# ----------------------------------------------------------------------------
# Tray sensors carried on the arm end plate (cad/station places them; docs/pick_and_place_design.md 3.5 says what they do).
# Envelopes from the manufacturers' published outlines; hole patterns and window positions are ASSUMED where the drawing
# was not available and must be confirmed against the vendor STEP (cad/vendor) before the bracket is made.
# ----------------------------------------------------------------------------
SENSORS = dict(
    # Panasonic HG-C1030 CMOS laser displacement sensor: 30 mm reference, +/-5 mm range, 10 um repeatability, spot dia 50 um,
    # 0-5 V analog + NPN, 12-24 V, 35 g, die-cast body 20 x 44 x 25, two M3 through holes, 5-core cable (2 m).
    hgc1030=dict(w=20.0, l=44.0, h=25.0,          # width (X here), length along the emitting face (Y here), height along the beam (Z)
                 beam_from_end=12.0,               # ASSUMED: beam exits the 20 x 44 face 12 mm from one end (laser window); confirm
                 holes=(3.2, 18.0, 12.5),          # ASSUMED: 2 x dia 3.2 through the 20 mm width, 18 apart along the length, 12.5 above the
                                                   # emitting face (the manual gives the M3 screws and the 18 mm); confirm
                 ref=30.0, span=5.0, repeat=0.010, mass=35.0),
    # Basler dart daA1440-220um S-mount: 1/2.9" IMX273 global shutter 1440 x 1080, 3.45 um pixels, USB3 micro-B, 15 g.
    # Geometry MEASURED on the manufacturer STEP (cad/vendor/basler_dart_daA1440_smount.step, drawing IB102744 rev 02): housing
    # 29 x 29 (29.3 with the USB shell peeking out one side), lens ring dia 16.3 protruding 5.9 in front of the housing front face
    # (M12 x 0.5 thread 7.4 deep), housing 9.5 deep behind the front face, USB micro-B socket on the back near one edge (plug inserts
    # sideways), 4 x dia 2.2 through holes on a 22.4 square (M2 screws). Mounted as Basler intends: front face against the bracket
    # (here the TOP of the arm end plate, ring down through a dia 17 hole). Lens: 16 mm M12 for 1/2.5" sensors on a 4 mm M12 spacer
    # ring: a board lens is sold focused near infinity (100-200 mm minimum object distance) and the extension that focuses it at
    # distance d is f^2 / (d - f) = 4.3 mm at 75 mm. Magnification 0.27, field 19 x 14 mm, 13 um/px, depth of field ~1.5 mm at f/4.
    dart=dict(file="basler_dart_daA1440_smount.step",
              w=29.3, l=29.0, body_h=9.5,          # housing behind its front face (X, Y, Z here)
              ring_d=16.3, ring_len=5.9,           # lens ring in front of the front face (goes through the plate)
              stub=(4.1, 3.2, 4.4, 6.3, 10.1),     # USB socket shell on the back: X size, Y size, height above the back, offsets of its
                                                   # centre from the housing centre (+x, +y in the file frame; the plug inserts along +x)
              holes=(2.2, 22.4),                   # 4 x dia 2.2 through on 22.4 x 22.4 (drawing) -> M2 tap-drill 1.6 in the plate
              file_front_z=-8.0, file_usb_side="+x",   # file frame: front face plane, ring toward -z, USB toward +x
              lens_d=14.0, lens_out=16.0,          # 16 mm M12 lens + 4 mm spacer: dia 14 envelope, front 16 beyond the ring front
              px=0.00345, sensor=(4.97, 3.73), f=16.0, spacer=4.0, mass=15.0 + 20.0),
)


def sensor_fov(wd, f=None, sensor=None, px=None):
    """(field width, field height, um per pixel) of the dart + lens at working distance wd (thin lens; lens front ~ f from the pupil)."""
    d = SENSORS["dart"]
    f = f or d["f"]; sensor = sensor or d["sensor"]; px = px or d["px"]
    m = f / max(wd - f, 0.1)                        # magnification for an object wd from the front principal plane (thin lens)
    return sensor[0] / m, sensor[1] / m, px / m * 1000.0

# ----------------------------------------------------------------------------
# Bench levels: the optical-table plane follows from the fiber stages (NanoMax 300 deck + platform + holder)
# putting the fiber axis at the die-top height. Everything under the die (nest stack) is built up from TABLE_Z.
# ----------------------------------------------------------------------------
NANOMAX = dict(w=112.0, h=62.5, platform_h=4.0, gap_y=45.0)   # footprint, deck height, top platform, inner face to facet
NANOMAX["platform_w"] = 60.0                                   # top platform 60 x 60 with a 3 mm cross groove (vendor STEP)
FIBER["mount_front"] = NANOMAX["gap_y"] + (NANOMAX["w"] - NANOMAX["platform_w"]) / 2   # 71: HCS013 front face at the platform's inner edge
HOLDER_AXIS_ABOVE_DECK = FIBER["mount_axis"]                   # 12.5: HCS013 axis above the NanoMax top platform (Thorlabs 16022-E0W)
NEST_BASE_T = 12.0                                             # metrology base plate (6061) on the breadboard: carries both NanoMax risers,
                                                               # the nest's KB1X1 (one M4 tap) and the microscope column, so the fiber-to-die
                                                               # loop closes through one plate and its bolt pattern is free of the 25 mm grid
NANOMAX_RISER = 36.5                                           # riser plate under each NanoMax on the base plate: the die-stage stack needs
                                                               # 111 mm from the plate top to the die bottom (KB1X1 + KXC04015 + RMPG40W-N +
                                                               # riser), the fiber axis is 75 above the NanoMax base (62.5 deck + 12.5 mount)
TABLE_Z = DIE_TOP - HOLDER_AXIS_ABOVE_DECK - NANOMAX["h"] - NANOMAX_RISER - NEST_BASE_T   # -123.0: breadboard top
BASE_TOP = TABLE_Z + NEST_BASE_T                               # -111.0: base plate top (KB1X1 seat, NanoMax riser seat, column base)
# Thorlabs MB6090/M aluminium breadboard, 600 x 900 x 12.7, 864 x M6 on 25 mm, first hole 25 from the edge (drawing 13808-E0W).
# Placed so that the riser bolt rows land on holes: X holes at 4 (mod 25), Y holes at 10 (mod 25); see station README "Bolt grid".
BREADBOARD = dict(file="thorlabs_MB6090_M.step", L=900.0, W=600.0, t=12.7, pitch=25.0, edge=25.0, x0=-671.0, y0=-290.0)
BREADBOARD["hole0"] = (BREADBOARD["x0"] + BREADBOARD["edge"], BREADBOARD["y0"] + BREADBOARD["edge"])   # (-646, -265)


def grid_offset(x, y):
    """Distance of (x, y) from the nearest breadboard hole, per axis (0 = on a hole line)."""
    p = BREADBOARD["pitch"]; hx, hy = BREADBOARD["hole0"]
    dx = (x - hx) % p; dy = (y - hy) % p
    return min(dx, p - dx), min(dy, p - dy)


def holder_boxes(side):
    """AABB envelopes of the fiber holder stack on one side (-1 input at Y < 0, +1 output at Y > 6), station frame (die
    bottom Z 0, fiber axis at DIE_TOP): chuck (from the fiber protrusion to the rotator front), rotator, mount (with its
    flanges). The nest checks use these; the station uses the vendor STEP and falls back to these."""
    f = FIBER; ax = DIE_TOP; cx = DIE_LEN / 2
    yf = 0.0 if side < 0 else DIE_WID
    span = (lambda a, b: (yf - b, yf - a)) if side < 0 else (lambda a, b: (yf + a, yf + b))
    rf = f["mount_front"]; r0 = rf - f["rotator_len"]
    out = {}
    y0, y1 = span(f["protrusion"], r0)
    out["chuck"] = box(cx - f["chuck_d"] / 2, cx + f["chuck_d"] / 2, y0, y1, ax - f["chuck_d"] / 2, ax + f["chuck_d"] / 2)
    y0, y1 = span(r0, rf)
    out["rotator"] = box(cx - f["rotator_d"] / 2, cx + f["rotator_d"] / 2, y0, y1, ax - f["rotator_d"] / 2, ax + f["rotator_d"] / 2)
    y0, y1 = span(rf, rf + f["mount_d"])
    w2 = f["mount_w"] / 2 + f["mount_flange"]
    out["mount"] = box(cx - w2, cx + w2, y0, y1, ax - f["mount_axis"], ax - f["mount_axis"] + f["mount_h"])
    return out
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
    # bolt patterns measured in the vendor STEP files (file frame, see above):
    mount_pitch=60.0, mount_hole=3.4, mount_row=9.0, # base: N x dia 3.4 through / dia 6.5 counterbore from inside the rail channel,
                                                     # two rows at z = +/-9, pitch 60 along the rail; the mounting surface gets M3
    base_first={300: 40.0, 200: 50.0, 100: 30.0},    # first base hole measured from the rail's far (non-motor) end, per L ...
    base_n={300: 5, 200: 3, 100: 2},                 # ... and the number of holes per row (the last one carries the dia 4 dowel,
    base_dowel=4.0,                                  # the first one a 4 x 8 slot, both on the rail centre line)
    table_holes=(20.0, 45.0),                        # 4 x M4 tapped in the table plate: 20 along the axis x 45 across, about its centre
    table_dowel=(3.0, 45.0),                         # 2 x dia 3 dowel holes in the table plate at its centre, 45 apart across (one slotted)
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

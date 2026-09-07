"""Build the Blender scene for the die-tester station from the converted CAD geometry.

Reads `station_assembly.glb` (written by `step_to_glb.py` from the station assembly STEP), sorts the
84 named parts into collections, gives each one a material chosen from its name, and adds lighting
and the four cameras that match the `cadgen` renders in `cad/station/renders/`.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background \
        --python cad/blender/build_scene.py -- --render iso

The GLB is in metres (OpenCASCADE converts the CAD's millimetres on export), so one Blender unit is
one metre and the station is ~0.94 m across.  Scene length units are set to millimetres for display,
which is how every number in `cad/` and `docs/` is written.

Outputs `die_tester_station.blend` next to this file; both it and the GLB are git-ignored.
"""

import argparse
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))

# --------------------------------------------------------------------------------------------
# Parts -> collections.  The names come from the `cq.Assembly` members added in
# cad/station/model.py; the first matching rule wins, so put specific prefixes before general ones.
# --------------------------------------------------------------------------------------------
COLLECTIONS = [
    ("Table",       ("optical_table",)),
    ("Nest",        ("nest_", "die_at_nest")),
    ("Fibers",      ("nanomax", "fiber_")),
    ("Microscope",  ("microscope_", "objective")),
    ("Tray",        ("wafer_tray", "tray_deck", "tray_pin_")),
    ("X axis",      ("x_axis_",)),
    ("Y axis",      ("y_axis_", "y_stage_riser")),
    ("Z tower",     ("z_axis_", "tower_bracket")),
    ("Arm",         ("arm_6061",)),
    ("Gripper",     ("gripper_",)),
    ("Tray camera", ("camera_",)),
]

# The station STEP carries the moving group twice: opaque at the nest, and a second translucent copy
# of the X carriage, tower, arm, gripper and camera at the farthest tray column, as the worst case for
# travel and for the tower.  STEP has no reliable transparency, so both arrive solid.  Only the copy
# at the nest is wanted here - the animation moves it through the travel the ghost stands for.
# The marker sits mid-name on the gripper and camera members (gripper_at_far_col_near_arm), so match
# it anywhere, not just as a suffix.
DROP_MARKER = "_at_far_col"
DROP_NAMES = {"objective_keepout"}

# One solid of the Suruga KXC04015-C die stage arrives from the STEP without a product name (the
# vendor path aliases the knob onto the coupling solid, cad/nest/model.py:337, so a member is left
# carrying only its entity number).  It sits in the die-stage stack below the nest; give it a name so
# it lands in the right collection instead of a stray "Other".
NAME_FIXES = {"25": "nest_kxc04015_unnamed"}

# --------------------------------------------------------------------------------------------
# Materials: (base colour RGB, metallic, roughness).
# The material of each custom part is already in its filename suffix (_6061, _copper, _semitron,
# _steel) per the repo convention; the vendor parts get the finish they actually have.
# --------------------------------------------------------------------------------------------
MATERIALS = {
    "aluminium": ((0.62, 0.64, 0.67), 1.0, 0.38),   # machined + bead-blasted 6061
    "anodized":  ((0.16, 0.17, 0.19), 0.7, 0.45),   # black-anodized vendor bodies
    "motor":     ((0.10, 0.10, 0.11), 0.4, 0.55),   # stepper cans / painted housings
    "steel":     ((0.72, 0.73, 0.75), 1.0, 0.20),   # spring-steel flexure blade, fasteners
    "copper":    ((0.85, 0.48, 0.30), 1.0, 0.25),   # nest chuck pad
    "semitron":  ((0.20, 0.21, 0.23), 0.0, 0.65),   # ESd 225 tip blocks and cage
    "resin":     ((0.86, 0.84, 0.79), 0.0, 0.55),   # SLA wafer tray
    "ceramic":   ((0.92, 0.92, 0.90), 0.0, 0.40),   # TEC top plate
    "die":       ((0.55, 0.68, 0.78), 0.0, 0.08),   # air-clad TFLN die
    "glass":     ((0.80, 0.86, 0.90), 0.0, 0.05),   # fiber tips
    "table":     ((0.13, 0.14, 0.15), 0.2, 0.70),   # optical table top
    "cable":     ((0.08, 0.08, 0.09), 0.0, 0.80),
    "pcb":       ((0.15, 0.35, 0.22), 0.0, 0.60),   # Basler dart board camera
}

# (substring, material) — first match wins.
MATERIAL_RULES = [
    ("optical_table", "table"),
    ("die_at_nest", "die"),
    ("nest_chuck_copper", "copper"),
    ("nest_cage_semitron", "semitron"),
    ("nest_tec", "ceramic"),
    ("nest_rmpg40w_cable", "cable"),
    ("nest_rmpg40w_bolts", "steel"),
    ("_tip", "semitron"),
    ("gripper_blade", "steel"),
    ("gripper_mhz2", "anodized"),
    ("camera_dart", "pcb"),
    ("camera_lens", "anodized"),
    ("camera_usb", "anodized"),
    ("fiber_holder", "aluminium"),
    ("fiber_", "glass"),
    ("nanomax300", "anodized"),
    ("objective", "anodized"),
    ("microscope_", "anodized"),
    ("wafer_tray", "resin"),
    ("tray_pin", "steel"),
    ("_motor", "motor"),
    ("_rail_lx20", "anodized"),
    ("kxc04015", "aluminium"),
    ("rmpg40w", "aluminium"),
    ("kb1x1", "aluminium"),
]
DEFAULT_MATERIAL = "aluminium"     # every remaining part is machined 6061


def material_for(name):
    for key, mat in MATERIAL_RULES:
        if key in name:
            return mat
    return DEFAULT_MATERIAL


def collection_for(name):
    for coll, prefixes in COLLECTIONS:
        if any(name.startswith(p) for p in prefixes):
            return coll
    return "Other"


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "MILLIMETERS"
    scene.unit_settings.scale_length = 1.0
    return scene


def import_glb(path):
    if not os.path.exists(path):
        sys.exit("missing %s - run step_to_glb.py first" % path)
    before = set(bpy.data.objects)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except AttributeError:
        bpy.ops.wm.gltf_import(filepath=path)
    imported = [o for o in bpy.data.objects if o not in before]

    # glTF is nominally Y-up and Blender's importer rotates for that, but OpenCASCADE writes this
    # file in the CAD's own Z-up frame, so the import lands on its side.  Rotate it back: the
    # station frame is X = die long axis, Y = optical axis, Z up (cad/common/__init__.py).
    fix = Matrix.Rotation(math.radians(-90.0), 4, "X")
    for obj in imported:
        if obj.parent is None:
            obj.matrix_world = fix @ obj.matrix_world
    return [o for o in imported if o.type == "MESH"]


def make_material(key):
    name = "st_" + key
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    rgb, metallic, roughness = MATERIALS[key]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (rgb[0], rgb[1], rgb[2], 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if key in ("die", "glass"):
        # The die is air-clad TFLN and the fiber tips are silica: let a little light through so the
        # facets read as glass rather than as painted blocks.
        if "Transmission Weight" in bsdf.inputs:
            bsdf.inputs["Transmission Weight"].default_value = 0.55 if key == "glass" else 0.25
        bsdf.inputs["IOR"].default_value = 2.2 if key == "die" else 1.45
    return mat


def sort_into_collections(objects):
    scene = bpy.context.scene
    made = {}
    dropped = 0
    for obj in objects:
        if obj.name in NAME_FIXES:
            obj.name = NAME_FIXES[obj.name]
        name = obj.name
        if DROP_MARKER in name or name in DROP_NAMES:
            bpy.data.objects.remove(obj, do_unlink=True)
            dropped += 1
            continue
        coll_name = collection_for(name)
        if coll_name not in made:
            coll = bpy.data.collections.new(coll_name)
            scene.collection.children.link(coll)
            made[coll_name] = coll
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        made[coll_name].objects.link(obj)

        obj.data.materials.clear()
        obj.data.materials.append(make_material(material_for(name)))
        for poly in obj.data.polygons:
            poly.use_smooth = True
    return made, dropped


def world_corners(objects):
    """Every object's bounding-box corners in world space.

    Framing on these rather than on one global box matters here: the station is an L around the
    tray, so its overall box is mostly empty air and would push the cameras much too far back.
    """
    bpy.context.view_layer.update()
    return [obj.matrix_world @ Vector(corner)
            for obj in objects for corner in obj.bound_box]


def scene_bounds(objects):
    bpy.context.view_layer.update()
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for obj in objects:
        for corner in obj.bound_box:
            p = obj.matrix_world @ Vector(corner)
            lo = Vector(map(min, lo, p))
            hi = Vector(map(max, hi, p))
    return lo, hi


def add_lighting(lo, hi):
    """Studio key/fill/rim sized to the machine, over a mid-grey world.

    Most of the station is black-anodized vendor hardware on a black optical table, so the world
    contributes real ambient fill here rather than only a backdrop; without it the machine renders
    as black on black.
    """
    world = bpy.data.worlds.new("station_world")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs[0].default_value = (0.22, 0.24, 0.28, 1.0)
    background.inputs[1].default_value = 1.0
    bpy.context.scene.world = world

    centre = (lo + hi) / 2
    span = max(hi - lo)
    lights = [
        ("key", Vector((-0.8, -1.0, 1.2)), 4000.0, span * 1.0),
        ("fill", Vector((1.3, -0.8, 0.5)), 1200.0, span * 1.4),
        ("rim", Vector((0.1, 1.2, 0.9)), 2200.0, span * 0.9),
    ]
    for name, direction, power, size in lights:
        data = bpy.data.lights.new("light_" + name, type="AREA")
        data.energy = power
        data.size = size
        obj = bpy.data.objects.new("light_" + name, data)
        obj.location = centre + direction * span * 0.9
        obj.rotation_euler = (direction * -1).to_track_quat("Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(obj)


def frame_distance(camera_data, target, corners, direction, aspect, margin=1.03):
    """Distance along `direction` at which every corner still fits in the camera frame."""
    forward = -direction.normalized()
    right = forward.cross(Vector((0.0, 0.0, 1.0)))
    if right.length < 1e-6:                       # straight-down plan view
        right = Vector((1.0, 0.0, 0.0))
    right.normalize()
    up = right.cross(forward).normalized()

    angle_x = camera_data.angle
    tan_x = math.tan(angle_x / 2.0)
    tan_y = tan_x / aspect
    distance = 0.0
    for corner in corners:
        rel = corner - target
        along = rel.dot(forward)
        distance = max(distance,
                       abs(rel.dot(right)) / tan_x - along,
                       abs(rel.dot(up)) / tan_y - along)
    return distance * margin


def add_cameras(lo, hi, focus_lo, focus_hi, focus_corners, nest_corners, aspect):
    """Cameras framed on the machine itself.

    `lo`/`hi` cover everything including the 940 x 560 mm optical table; `focus_lo`/`focus_hi`
    exclude it, so the machine fills the frame and the table is simply cropped at the edges - the
    same choice the cadgen renders in cad/station/renders/ make.
    """
    # Aim at the centroid of the parts rather than the centre of their bounding box: the box is
    # stretched upward by the Z-axis brake motor and the microscope column, which would leave the
    # machine sitting in the bottom third of every frame.
    target = sum(focus_corners, Vector((0.0, 0.0, 0.0))) / len(focus_corners)

    # Directions point from the target towards the camera.  Matched to the existing renders:
    # side looks along +Y (the optical axis), front along +X (the die long axis).
    views = {
        "iso": (Vector((1.0, -1.15, 0.75)), 50.0, None),
        "plan": (Vector((0.0, 0.0, 1.0)), 60.0, None),
        "side": (Vector((0.0, -1.0, 0.12)), 60.0, None),
        "front": (Vector((-1.0, 0.0, 0.12)), 60.0, None),
        # The exchange itself: the nest, the die, the jaws and both fiber holders.
        "nest": (Vector((0.9, -1.0, 0.55)), 50.0, "nest"),
    }
    cameras = {}
    for name, (direction, lens, override) in views.items():
        data = bpy.data.cameras.new("cam_" + name)
        data.lens = lens
        data.clip_start = 0.005
        data.clip_end = 100.0
        obj = bpy.data.objects.new("cam_" + name, data)
        bpy.context.scene.collection.objects.link(obj)

        box = nest_corners if override == "nest" else focus_corners
        aim = (sum(box, Vector((0.0, 0.0, 0.0))) / len(box)) if override else target
        distance = frame_distance(data, aim, box, direction, aspect)
        obj.location = aim + direction.normalized() * distance
        obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
        cameras[name] = obj
    bpy.context.scene.camera = cameras["iso"]
    return cameras


def eevee_engine():
    """EEVEE Next is 'BLENDER_EEVEE_NEXT' in Blender 4.2-4.5 and plain 'BLENDER_EEVEE' in 5.x."""
    items = bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items
    return "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in items else "BLENDER_EEVEE"


def enable_gpu():
    """Point Cycles at OptiX or CUDA when the machine has it.

    The device lives in user preferences rather than in the .blend, so this has to run in every
    background session, not just the one that built the scene.  Returns the backend that was
    selected, or None if it fell back to CPU.

    Cycles renders with one backend at a time (plus the CPU), so a machine with both an NVIDIA and
    an Intel GPU uses one of them, not both: OptiX here, because the RTX 2000 Ada is much the
    faster of the two.
    """
    addon = bpy.context.preferences.addons.get("cycles")
    if not addon:
        return None
    prefs = addon.preferences
    for device_type in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = device_type
        except TypeError:
            continue
        prefs.get_devices()
        gpus = [d for d in prefs.devices if d.type == device_type]
        if gpus:
            for device in prefs.devices:
                device.use = device.type in (device_type, "CPU")
            bpy.context.scene.cycles.device = "GPU"
            print("[render] Cycles on %s: %s" % (device_type, ", ".join(d.name for d in gpus)))
            return device_type
    print("[render] no OptiX/CUDA device found, Cycles on CPU")
    return None


def configure_render(engine, samples, resolution):
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = resolution
    scene.view_settings.exposure = 0.6
    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    scene.render.film_transparent = False
    if engine != "cycles":
        scene.render.engine = eevee_engine()
        scene.eevee.taa_render_samples = samples
        return
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True
    enable_gpu()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", default=os.path.join(HERE, "station_assembly.glb"))
    ap.add_argument("--output", default=os.path.join(HERE, "die_tester_station.blend"))
    ap.add_argument("--engine", choices=("cycles", "eevee"), default="cycles")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--render", nargs="*", default=[],
                    help="camera names to render after building (iso plan side front)")
    ap.add_argument("--resolution", type=int, nargs=2, default=(1920, 1280))
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    reset_scene()
    objects = import_glb(args.glb)
    print("[scene] imported %d parts" % len(objects))

    made, dropped = sort_into_collections(objects)
    kept = [o for o in bpy.data.objects if o.type == "MESH"]
    print("[scene] %d parts kept, %d clearance-study ghosts dropped" % (len(kept), dropped))
    for name in sorted(made):
        print("[scene]   %-12s %3d" % (name, len(made[name].objects)))
    if "Other" in made:
        print("[scene]   unclassified: %s"
              % ", ".join(sorted(o.name for o in made["Other"].objects)))

    lo, hi = scene_bounds(kept)
    print("[scene] bounds mm  X %8.1f..%8.1f   Y %8.1f..%8.1f   Z %8.1f..%8.1f"
          % (lo.x * 1000, hi.x * 1000, lo.y * 1000, hi.y * 1000, lo.z * 1000, hi.z * 1000))

    machine = [o for o in kept if o.name != "optical_table"]
    focus_lo, focus_hi = scene_bounds(machine)

    # The close-up frames the exchange itself: the nest stack, the die, the jaws and both fiber
    # holders, which is where every contact rule in CLAUDE.md applies.
    close_up = [o for o in kept
                if o.name.startswith(("nest_", "die_at_nest", "gripper_", "fiber_holder"))]

    add_lighting(lo, hi)
    configure_render(args.engine, args.samples, tuple(args.resolution))
    cameras = add_cameras(lo, hi, focus_lo, focus_hi,
                          world_corners(machine), world_corners(close_up),
                          args.resolution[0] / args.resolution[1])

    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print("[scene] saved %s" % args.output)

    renders = os.path.join(HERE, "renders")
    os.makedirs(renders, exist_ok=True)
    for name in args.render:
        bpy.context.scene.camera = cameras[name]
        bpy.context.scene.render.filepath = os.path.join(renders, "station_" + name + ".png")
        bpy.ops.render.render(write_still=True)
        print("[render] %s" % bpy.context.scene.render.filepath)


if __name__ == "__main__":
    main()

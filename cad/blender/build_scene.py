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

# The worst-case pose - the X carriage, tower, arm, gripper and camera at the farthest tray column -
# now lives in its own file, station_far_column.step, so the main assembly carries no ghosts and
# this marker normally matches nothing.  It is kept because the marker is how those members are
# named (cad/station/README.md, "Assembly member names"), so pointing --glb at a conversion of the
# far-column file still yields one machine rather than two overlaid.  The marker sits mid-name on
# the gripper and camera members (gripper_at_far_col_near_arm), so match it anywhere.
DROP_MARKER = "_at_far_col"

# Render aids: volumes the station model draws to show clearance, not parts of the machine.
DROP_NAMES = {"objective_keepout", "camera_fov"}

# --------------------------------------------------------------------------------------------
# Materials: (base colour RGB, metallic, roughness).
# The material of each custom part is already in its filename suffix (_6061, _copper, _semitron,
# _steel) per the repo convention; the vendor parts get the finish they actually have.
# --------------------------------------------------------------------------------------------
MATERIALS = {
    # Metallic is a physical property, not a dial: a surface either is an exposed conductor or it
    # is not, and intermediate values are what make everything look like the same grey alloy.  Only
    # bare metal gets 1.0 - machined 6061, the copper pad, steel.  Anodizing is a dielectric oxide
    # layer and painted motor housings are dielectric too, so both get 0.0 and read by their
    # roughness instead.
    #
    # Base colours are lifted from the true blacks of the real hardware: this is lab equipment
    # being documented, so every part has to stay legible in shadow.  Anodized aluminium and
    # stepper cans really are near-black, but rendered at their measured value they read as one
    # silhouette.
    "aluminium": ((0.66, 0.67, 0.68), 1.0, 0.44),   # machined + bead-blasted 6061, neutral silver
    "anodized":  ((0.13, 0.14, 0.16), 0.0, 0.38),   # black-anodized bodies: satin dielectric
    "motor":     ((0.09, 0.09, 0.10), 0.0, 0.50),   # painted stepper housings, dielectric
    "steel":     ((0.76, 0.77, 0.79), 1.0, 0.18),   # spring-steel flexure blade, fasteners
    "copper":    ((0.92, 0.48, 0.24), 1.0, 0.22),   # nest chuck pad
    "brass":     ((0.78, 0.60, 0.28), 1.0, 0.30),   # HFC005 fiber chuck body
    "semitron":  ((0.22, 0.21, 0.19), 0.0, 0.68),   # ESd 225 tip blocks and cage, warm charcoal
    "resin":     ((0.91, 0.87, 0.78), 0.0, 0.55),   # SLA wafer tray, warm cream
    "ceramic":   ((0.94, 0.94, 0.92), 0.0, 0.40),   # TEC top plate
    "die":       ((0.42, 0.68, 0.88), 0.0, 0.08),   # air-clad TFLN die
    "glass":     ((0.78, 0.88, 0.96), 0.0, 0.05),   # fiber tips
    "table":     ((0.11, 0.12, 0.14), 0.0, 0.52),   # MB6090/M breadboard, black anodized
    "cable":     ((0.12, 0.12, 0.13), 0.0, 0.80),
    "pcb":       ((0.14, 0.45, 0.24), 0.0, 0.60),   # Basler dart board camera
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
    ("fiber_in", "glass"),
    ("fiber_out", "glass"),
    ("fiber_rotator", "anodized"),
    ("fiber_chuck", "brass"),        # the assembly authors this bronze; HFC005 bodies are brass
    ("fiber_cleats", "steel"),
    ("fiber_mount", "aluminium"),
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


# CAD edges are mathematically sharp, so nothing catches a highlight along them and the parts read
# as untouched solid modelling.  Real machined and cast parts have a break on every edge.  A Cycles
# bevel shader fakes that at shading time - no geometry, no modifier on 70 meshes - and the thin
# highlight it puts on every edge is most of what separates a render from a CAD screenshot.
BEVEL_RADIUS = 0.00018      # 0.18 mm, about the break a deburred machined edge carries
BEVEL_SAMPLES = 4


def imported_base_color(obj):
    """The colour the station assembly authored for this member, as imported from the GLB.

    `cad/station/model.py` gives every `cq.Assembly` member a `cq.Color`, cascadio carries it into
    the GLB and Blender imports it as a Principled base colour.  That is the designer's material
    intent - black anodizing on the rails, 6061 grey on the machined parts, copper on the chuck,
    bronze on the fiber chucks - so it is the base colour to render, not one invented here.
    """
    for slot in obj.data.materials:
        if slot is None or not slot.use_nodes:
            continue
        for node in slot.node_tree.nodes:
            if node.type == "BSDF_PRINCIPLED":
                return tuple(node.inputs["Base Color"].default_value)[:3]
    return None


def make_material(key, rgb=None):
    """A material of class `key`; `rgb` overrides its base colour but not how it responds to light.

    The class still decides metallic and roughness, because a colour cannot say whether a surface
    is an exposed conductor or an anodized dielectric, and that distinction is what stopped the
    whole machine looking like one grey alloy.
    """
    name = "st_" + key
    if rgb is not None:
        name += "_%02x%02x%02x" % tuple(min(255, max(0, int(c * 255 + 0.5))) for c in rgb)
    if name in bpy.data.materials:
        return bpy.data.materials[name]
    default_rgb, metallic, roughness = MATERIALS[key]
    rgb = default_rgb if rgb is None else rgb
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bevel = mat.node_tree.nodes.new("ShaderNodeBevel")
    bevel.inputs["Radius"].default_value = BEVEL_RADIUS
    bevel.samples = BEVEL_SAMPLES
    mat.node_tree.links.new(bsdf.inputs["Normal"], bevel.outputs["Normal"])
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


def sort_into_collections(objects, use_assembly_colors=False):
    scene = bpy.context.scene
    made = {}
    dropped = 0
    for obj in objects:
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

        authored = imported_base_color(obj) if use_assembly_colors else None
        obj.data.materials.clear()
        obj.data.materials.append(make_material(material_for(name), authored))
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
    tree = world.node_tree
    background = tree.nodes["Background"]
    # The world is the main fill here, not a backdrop: a bright even surround is what keeps the
    # anodized hardware readable and stops the breadboard going to black.  It is a vertical
    # gradient rather than a flat colour because a metal can only reflect what is around it, and a
    # flat world turns every polished surface into a flat grey card.
    coord = tree.nodes.new("ShaderNodeTexCoord")
    separate = tree.nodes.new("ShaderNodeSeparateXYZ")
    ramp = tree.nodes.new("ShaderNodeValToRGB")
    tree.links.new(separate.inputs[0], coord.outputs["Generated"])
    tree.links.new(ramp.inputs["Fac"], separate.outputs["Z"])
    ramp.color_ramp.elements[0].position = 0.30
    ramp.color_ramp.elements[0].color = (0.20, 0.21, 0.24, 1.0)   # floor, below the horizon
    ramp.color_ramp.elements[1].position = 0.78
    ramp.color_ramp.elements[1].color = (0.62, 0.66, 0.72, 1.0)   # sky
    tree.links.new(background.inputs[0], ramp.outputs["Color"])
    background.inputs[1].default_value = 1.0
    bpy.context.scene.world = world

    centre = (lo + hi) / 2
    span = max(hi - lo)
    lights = [
        # Bright enough to read the black hardware, directional enough to keep the form: the key
        # does the shaping, the world does the filling.
        ("key", Vector((-0.8, -1.0, 1.2)), 5400.0, span * 0.9),
        ("fill", Vector((1.3, -0.8, 0.5)), 1900.0, span * 1.6),
        ("rim", Vector((0.1, 1.2, 0.9)), 2600.0, span * 1.0),
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
    scene.view_settings.exposure = 0.75
    # AgX is filmic and desaturating; "Punchy" puts the colour back, which matters for the copper
    # chuck, the green camera board and the blue die.  Fall back in order if a look is missing.
    for look in ("AgX - Punchy", "AgX - Base Contrast", "AgX - Medium High Contrast"):
        try:
            scene.view_settings.look = look
        except TypeError:
            continue
        print("[render] look %s" % look)
        break
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
    ap.add_argument("--assembly-colors", action="store_true",
                    help="use the colours the station assembly authors (navy moving group, blue "
                         "NanoMax, light-grey breadboard) instead of the real hardware finishes; "
                         "useful for design review, where seeing what travels matters more than "
                         "seeing what it will look like")
    ap.add_argument("--samples", type=int, default=128)
    ap.add_argument("--render", nargs="*", default=[],
                    help="camera names to render after building (iso plan side front)")
    ap.add_argument("--resolution", type=int, nargs=2, default=(1920, 1280))
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    reset_scene()
    objects = import_glb(args.glb)
    print("[scene] imported %d parts" % len(objects))

    made, dropped = sort_into_collections(objects, args.assembly_colors)
    kept = [o for o in bpy.data.objects if o.type == "MESH"]
    print("[scene] %d parts kept, %d render aids and far-column copies dropped"
          % (len(kept), dropped))
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
                if o.name.startswith(("nest_", "die_at_nest", "gripper_", "fiber_"))]

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

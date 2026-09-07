"""Animate one full die exchange on the Blender station scene.

Opens `die_tester_station.blend` (from `build_scene.py`), rigs the moving groups onto empties and
keyframes the 14-step movement pattern documented in `cad/station/README.md`, then saves
`die_tester_station_animated.blend`.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background \
        --python cad/blender/animate_exchange.py -- --preview

Every position comes from the CAD or the design documents, in millimetres in the station frame
(X = die long axis, Y = optical axis, Z up, die bottom on the nest at Z 0):

  * the X-table centre sits at X -121 at the nest and the tray columns are at die X -(95 + 16c)
    (README "Movement pattern" step 6, and the tray's 16 mm column pitch);
  * the rows are on a 7.5 mm pitch and the Y stage brings the wanted row to Y 3 (step 7);
  * the Z traverse is +8 mm above the die-at-nest plane and the tray ledges are 12 mm below it
    (steps 2, 5 and 8);
  * the jaws open 1.5 mm per side (steps 9 and 11) from the closed pose the STEP is drawn in;
  * the fibers retract 1.0 mm along +/-Y before any gripper move (step 1);
  * the push-to-stop is a 1.7 mm carriage move that slides the die 0.2 mm onto the pads (step 12).

Two dice are animated: the one the STEP carries on the nest, which goes out to a tray pocket, and a
copy of it already sitting in another pocket, which comes back to the nest.  That is the exchange -
the STEP is a single static pose and has only the one die.

The cycle is a loop, and the README's numbered steps start in the middle of it.  Step 13 leaves the
gripper parked 60 mm out at the traverse height with the fibers back at the facets and a device
under test, so that is the state step 0 begins from: stage home, fibers retract, and only then does
the gripper come in over the die and descend.  The last frame returns to the first frame's pose.
"""

import argparse
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from build_scene import (                                # noqa: E402  (needs HERE on sys.path)
    enable_gpu, eevee_engine, frame_distance, world_corners)

MM = 0.001

FPS = 30

# --------------------------------------------------------------------------------------------
# Which parts ride which axis.  Read off the assembly: x_axis_block is the LX20 table plate whose
# centre is at X -121 (the documented X-table centre at the nest) and z_axis_block is the Z table
# plate centred at Z 90.5, so those two are the carriages; the rails, adapter plates and motors of
# each actuator are static, as are the KB1X1, the KXC base and its motor.
# --------------------------------------------------------------------------------------------
X_CARRIAGE = ["x_axis_block", "tower_bracket_6061",
              "z_axis_rail_lx20", "z_axis_plate", "z_axis_motor"]
Z_CARRIAGE = ["z_axis_block", "arm_6061", "gripper_bracket", "gripper_mhz2_body",
              "camera_dart", "camera_lens", "camera_usb_plug"]
JAW_NEAR = ["gripper_mhz2_fing_near", "gripper_near_arm", "gripper_near_tip", "gripper_blade"]
JAW_FAR = ["gripper_mhz2_fing_far", "gripper_far_arm", "gripper_far_tip"]
Y_CARRIAGE = ["y_axis_block", "tray_deck", "tray_pin_xm", "tray_pin_xp", "wafer_tray"]
# The Suruga table and everything above it steps in X; the RMPG table and above also rotate.
STAGE_X = ["nest_kxc04015_table", "nest_spacer_kxc_rot",
           "nest_rmpg40w_body", "nest_rmpg40w_motor", "nest_rmpg40w_worm",
           "nest_rmpg40w_cable", "nest_rmpg40w_bolts"]
STAGE_THETA = ["nest_rmpg40w_table", "nest_riser_6061", "nest_tec",
               "nest_chuck_copper", "nest_cage_semitron"]
FIBER_IN = ["fiber_in", "fiber_holder_in"]
FIBER_OUT = ["fiber_out", "fiber_holder_out"]

# The RMPG40W-N yaw axis runs through the die (cad/station/README.md); the die centre is X 5, Y 3.
THETA_AXIS = Vector((5.0, 3.0, 0.0))

TRAVERSE = 8.0        # Z above the die-at-nest plane, step 2
LEDGE_DROP = -12.0    # tray pocket ledges below the nest plane, step 8
JAW_OPEN = 1.5        # per side, steps 9 and 11
FIBER_RETRACT = 1.0   # step 1
PUSH = 1.7            # carriage move of the push-to-stop, step 12
PUSH_SLIDE = 0.2      # how far the die itself slides onto the pads, step 12
# Step 13 parks the gripper "out" so the fibers can come in and the die stage can step devices.
# Out is towards the tray (-X): +X would drive the arm at the microscope column, which stands at
# X 80. -60 mm takes the jaws clear of the nest cage (X -2.5..12.5) and of the fiber corridor,
# while staying well short of tray column 0 at -95.
PARK = -60.0
START_STAGE_X = 4.0   # the die stage starts one device off home, so step 0 has something to do


def column_dx(col):
    """X the carriage travels from the nest to tray column `col` (README step 6)."""
    return -(95.0 + 16.0 * col)


ROW_PITCH = 7.5       # tray row pitch (README step 7)


def row_offset(row):
    """Where row `row` sits along Y when the tray stage is at its origin."""
    return ROW_PITCH * row


def stage_y(row):
    """Y the tray stage travels to bring row `row` to the die line at Y 3 (README step 7)."""
    return -ROW_PITCH * row


# --------------------------------------------------------------------------------------------
# Rigging
# --------------------------------------------------------------------------------------------


def empty(name, parent=None):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.02
    bpy.context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    return obj


def attach(names, target):
    """Parent objects to an empty without moving them.

    A missing name is fatal, not a warning: the member names are the interface with the station
    model (CLAUDE.md section 5), and a part that quietly fails to join its axis would simply stand
    still in the render while everything around it moved.
    """
    missing = []
    for name in names:
        obj = bpy.data.objects.get(name)
        if obj is None:
            missing.append(name)
            continue
        world = obj.matrix_world.copy()
        obj.parent = target
        obj.matrix_parent_inverse = target.matrix_world.inverted()
        obj.matrix_world = world
    if missing:
        sys.exit("[rig] not in the assembly: %s\n"
                 "      the station's member names changed; check cad/station/README.md, "
                 "\"Assembly member names\", and update the axis lists here."
                 % ", ".join(missing))


def build_rig():
    rig = {}
    rig["x"] = empty("rig_x_carriage")
    rig["z"] = empty("rig_z_carriage", rig["x"])
    rig["jaw_near"] = empty("rig_jaw_near", rig["z"])
    rig["jaw_far"] = empty("rig_jaw_far", rig["z"])
    rig["y"] = empty("rig_y_stage")
    rig["stage"] = empty("rig_die_stage_x")
    rig["theta"] = empty("rig_die_stage_theta", rig["stage"])
    rig["fiber_in"] = empty("rig_fiber_in")
    rig["fiber_out"] = empty("rig_fiber_out")

    # The yaw empty sits on the rotary axis so a Z rotation on it is the fiducial trim.
    rig["theta"].location = THETA_AXIS * MM
    # attach() reads target.matrix_world, and assigning .location does not refresh it: without this
    # update the yaw empty still reads as sitting at the origin, every part attached to it keeps a
    # parent inverse computed against that stale matrix, and the whole nest top - chuck, cage, TEC,
    # riser, rotary table - ends up displaced by the axis offset (5, 3, 0) mm once the depsgraph
    # catches up, leaving the die hanging off the edge of its chuck.
    bpy.context.view_layer.update()

    attach(X_CARRIAGE, rig["x"])
    attach(Z_CARRIAGE, rig["z"])
    attach(JAW_NEAR, rig["jaw_near"])
    attach(JAW_FAR, rig["jaw_far"])
    attach(Y_CARRIAGE, rig["y"])
    attach(STAGE_X, rig["stage"])
    attach(STAGE_THETA, rig["theta"])
    attach(FIBER_IN, rig["fiber_in"])
    attach(FIBER_OUT, rig["fiber_out"])
    return rig


def free_from_parent(obj):
    """Detach from the imported assembly's root empty, keeping the world transform.

    The dice are the only parts driven by absolute keyframed positions rather than by a rig empty,
    and that root empty carries the Z-up correction rotation, so a Z move written into `location`
    would come out along Y.
    """
    world = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = world
    return obj


def make_second_die(source, col, row):
    """A copy of the die, sitting on the ledges of the pocket it will be picked from."""
    die = source.copy()
    die.data = source.data
    die.name = "die_from_tray"
    for coll in source.users_collection:
        coll.objects.link(die)
    die.parent = None
    die.matrix_world = source.matrix_world.copy()
    die.location = die.location + Vector((column_dx(col), row_offset(row), LEDGE_DROP)) * MM
    return die


# --------------------------------------------------------------------------------------------
# The cycle: a list of (label, seconds, targets).  Targets name the axis variables that change over
# that segment; anything not named holds its value.
# --------------------------------------------------------------------------------------------

def cycle(out_col, out_row, in_col, in_row, theta_trim):
    traverse, ledge = TRAVERSE, LEDGE_DROP
    return [
        # label                       s     targets
        ("hold (parked, under test)", 0.5, {}),
        ("0  die stage to home",     0.8, {"sx": 0.0, "th": 0.0}),
        ("1  fibers retract 1 mm",   0.5, {"fib": FIBER_RETRACT}),
        ("2  gripper in over the die", 1.4, {"x": 0.0, "jaw": JAW_OPEN}),
        ("3  Z down beside the die", 0.7, {"z": 0.0}),
        ("4  jaws close",            0.5, {"jaw": 0.0}),
        ("5  vacuum off, lift 8 mm", 0.7, {"z": traverse}),
        ("6  X to tray column %d" % out_col,
                                     1.6, {"x": column_dx(out_col)}),
        ("7  Y stage to row %+d" % out_row,
                                     1.0, {"y": stage_y(out_row)}),
        ("8  Z down onto ledges",    0.9, {"z": ledge}),
        ("9  jaws open",             0.5, {"jaw": JAW_OPEN}),
        ("10 Z up, to the next die", 0.9, {"z": traverse}),
        ("10 X to column %d" % in_col,
                                     1.0, {"x": column_dx(in_col)}),
        ("10 Y stage to row %+d" % in_row,
                                     0.9, {"y": stage_y(in_row)}),
        ("10 Z down onto the die",   0.9, {"z": ledge}),
        ("10 jaws close",            0.5, {"jaw": 0.0}),
        ("10 lift",                  0.9, {"z": traverse}),
        # Arrives 0.2 mm short of the stop pads, so the carriage stops at PUSH_SLIDE short of X 0.
        ("10 X back to the nest",    1.8, {"x": -PUSH_SLIDE, "y": 0.0}),
        ("11 Z down onto the chuck", 0.9, {"z": 0.0}),
        ("11 jaws open",             0.5, {"jaw": JAW_OPEN}),
        ("12 push to stop +1.7 mm",  0.8, {"x": -PUSH_SLIDE + PUSH, "push": PUSH_SLIDE}),
        ("13 vacuum on, back off",   0.6, {"x": -PUSH_SLIDE}),
        ("13 Z up",                  0.6, {"z": traverse}),
        ("13 X to park",             1.2, {"x": PARK}),
        ("13 fibers approach",       0.6, {"fib": 0.0}),
        ("14 yaw trim",              0.8, {"th": theta_trim}),
        ("14 step to next device",   0.8, {"sx": 4.0}),
        ("hold",                     0.6, {}),
    ]


def add_orbit_camera(degrees, first, last, aspect):
    """A camera that circles the station over the whole cycle and ends behind it.

    The camera hangs off a pivot empty standing on the machine's centroid, so rotating the pivot
    about Z swings the camera round while it keeps looking at the same point.  Its elevation and
    lens come from cam_iso, and its radius is the largest of the distances needed at 24 azimuths
    around the circle, so nothing leaves the frame part-way through the turn.
    """
    source = bpy.data.objects["cam_iso"]
    machine = [o for o in bpy.data.objects
               if o.type == "MESH" and o.name != "optical_table"]
    corners = world_corners(machine)
    # Mean of the corners, which is also the mean of the parts' own centres; it lands at
    # (-60, -20, 1.5) mm, essentially on the die plane between the nest and the tray.
    target = sum(corners, Vector((0.0, 0.0, 0.0))) / len(corners)

    # cam_iso's own offset from the target sets the elevation; frame_distance wants a direction
    # pointing from the target out towards the camera, which is exactly that offset.
    base = source.matrix_world.translation - target
    radius = max(frame_distance(source.data, target, corners, swung, aspect)
                 for swung in _azimuths(base, 24))

    pivot = empty("rig_orbit")
    pivot.location = target
    camera = source.copy()
    camera.data = source.data.copy()
    camera.name = "cam_orbit"
    camera.data.name = "cam_orbit"
    bpy.context.scene.collection.objects.link(camera)
    camera.location = target + base.normalized() * radius
    camera.rotation_euler = base.to_track_quat("Z", "Y").to_euler()
    camera.parent = pivot
    camera.matrix_parent_inverse = pivot.matrix_world.inverted()

    keyframe(pivot, first, target, (0.0, 0.0, 0.0))
    keyframe(pivot, last, target, (0.0, 0.0, math.radians(degrees)))
    print("[anim] orbit camera: %+.0f deg over %d frames, radius %.0f mm"
          % (degrees, last - first, radius * 1000))
    return camera


def _azimuths(direction, count):
    """`direction` swung around Z in `count` even steps, keeping its elevation."""
    return [Matrix.Rotation(2.0 * math.pi * i / count, 4, "Z") @ direction
            for i in range(count)]


def keyframe(obj, frame, location=None, rotation=None):
    if location is not None:
        obj.location = location
        obj.keyframe_insert("location", frame=frame)
    if rotation is not None:
        obj.rotation_euler = rotation
        obj.keyframe_insert("rotation_euler", frame=frame)


def animate(rig, dice, segments, start_theta):
    """Write the keyframes.  Axis values are millimetres in the station frame."""
    # The cycle is a loop, and the documented step list starts in the middle of it: step 13 leaves
    # the gripper parked at the traverse height with the fibers back in and a device under test, so
    # that is where step 0 must find it.  Starting from the STEP's static pose instead would have
    # the jaws already standing on the die before the fibers have even retracted.
    # Yaw starts at the trim the previous device needed, and step 0 homes it: the jaws grip end
    # faces and push to the stop pads, so the die has to be square to them before they come in.
    # It also closes the loop - the clip ends on the new device's trim, where it began.
    state = {"x": PARK, "z": TRAVERSE, "y": 0.0, "jaw": JAW_OPEN,
             "sx": START_STAGE_X, "th": start_theta, "fib": 0.0, "push": 0.0}
    die_out, die_in = dice
    # Which rig each die rides, and its world position, tracked as the carriers move.
    carrier = {die_out: "nest", die_in: "tray"}
    position = {die_out: die_out.location + Vector((state["sx"], 0.0, 0.0)) * MM,
                die_in: die_in.location.copy()}

    def write(frame, previous):
        keyframe(rig["x"], frame, Vector((state["x"], 0.0, 0.0)) * MM)
        keyframe(rig["z"], frame, Vector((0.0, 0.0, state["z"])) * MM)
        keyframe(rig["y"], frame, Vector((0.0, state["y"], 0.0)) * MM)
        keyframe(rig["jaw_near"], frame, Vector((-state["jaw"], 0.0, 0.0)) * MM)
        keyframe(rig["jaw_far"], frame, Vector((state["jaw"], 0.0, 0.0)) * MM)
        keyframe(rig["stage"], frame, Vector((state["sx"], 0.0, 0.0)) * MM)
        keyframe(rig["theta"], frame, THETA_AXIS * MM,
                 (0.0, 0.0, math.radians(state["th"])))
        keyframe(rig["fiber_in"], frame, Vector((0.0, -state["fib"], 0.0)) * MM)
        keyframe(rig["fiber_out"], frame, Vector((0.0, state["fib"], 0.0)) * MM)

        for die in (die_out, die_in):
            ride = carrier[die]
            if ride == "jaws":
                delta = Vector((state["x"] - previous["x"], 0.0, state["z"] - previous["z"]))
            elif ride == "tray":
                delta = Vector((0.0, state["y"] - previous["y"], 0.0))
            elif ride == "nest":
                delta = Vector((state["sx"] - previous["sx"] + state["push"] - previous["push"],
                                0.0, 0.0))
            else:
                delta = Vector((0.0, 0.0, 0.0))
            position[die] = position[die] + delta * MM
            keyframe(die, frame, position[die])

    frame = 1.0
    marks = []
    write(frame, state)
    for label, seconds, targets in segments:
        previous = dict(state)
        state.update(targets)
        frame += max(1.0, round(seconds * FPS))
        write(frame, previous)
        marks.append((int(frame), label))
        print("[anim] f%4d  %s" % (int(frame), label))

        # Hand the die over at the frames where the jaws actually take or release it.
        if label == "4  jaws close":
            carrier[die_out] = "jaws"
        elif label == "9  jaws open":
            carrier[die_out] = "tray"
        elif label == "10 jaws close":
            carrier[die_in] = "jaws"
        elif label == "11 jaws open":
            carrier[die_in] = "nest"

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = int(frame)
    # verify_scene.py looks steps up by name, so editing the cycle cannot leave it checking the
    # wrong frames.
    scene["exchange_steps"] = json.dumps(marks)
    return int(frame)


def all_fcurves(action):
    """Blender 5 stores curves in slotted layers/strips; older files keep action.fcurves."""
    curves = getattr(action, "fcurves", None)
    if curves is not None:
        for fcurve in curves:
            yield fcurve
        return
    for layer in action.layers:
        for strip in layer.strips:
            for channelbag in getattr(strip, "channelbags", []):
                for fcurve in channelbag.fcurves:
                    yield fcurve


def smooth_all():
    """Ease every keyframe so the axes accelerate and settle instead of stepping linearly."""
    eased = 0
    for action in bpy.data.actions:
        for fcurve in all_fcurves(action):
            for point in fcurve.keyframe_points:
                point.interpolation = "BEZIER"
                point.handle_left_type = "AUTO_CLAMPED"
                point.handle_right_type = "AUTO_CLAMPED"
                eased += 1
            fcurve.update()
    print("[anim] eased %d keyframes" % eased)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blend", default=os.path.join(HERE, "die_tester_station.blend"))
    ap.add_argument("--output", default=os.path.join(HERE, "die_tester_station_animated.blend"))
    ap.add_argument("--out-column", type=int, default=3, help="tray column the nest die goes to")
    ap.add_argument("--out-row", type=int, default=2)
    ap.add_argument("--in-column", type=int, default=4, help="tray column the next die comes from")
    ap.add_argument("--in-row", type=int, default=-1)
    ap.add_argument("--theta-trim", type=float, default=0.4,
                    help="illustrative yaw trim in degrees; the real value is read per die from "
                         "the fiducials, so this only shows that the axis moves")
    ap.add_argument("--preview", action="store_true", help="render an mp4 of the cycle")
    ap.add_argument("--engine", choices=("cycles", "eevee"), default="cycles",
                    help="cycles resolves the shallow surface detail; eevee is the fast draft")
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--camera", default="nest",
                    help="iso, plan, side, front, nest, or orbit")
    ap.add_argument("--orbit", type=float, default=180.0,
                    help="degrees the orbit camera turns over the cycle; 180 ends behind the "
                         "station, negative goes the other way round")
    ap.add_argument("--resolution", type=int, nargs=2, default=(1280, 854))
    args = ap.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])

    bpy.ops.wm.open_mainfile(filepath=args.blend)
    rig = build_rig()
    die_out = free_from_parent(bpy.data.objects["die_at_nest"])
    die_in = make_second_die(die_out, args.in_column, args.in_row)

    end = animate(rig, (die_out, die_in),
                  cycle(args.out_column, args.out_row,
                        args.in_column, args.in_row, args.theta_trim),
                  args.theta_trim)
    add_orbit_camera(args.orbit, bpy.context.scene.frame_start, end,
                     args.resolution[0] / args.resolution[1])
    smooth_all()
    bpy.ops.wm.save_as_mainfile(filepath=args.output)
    print("[anim] %d frames (%.1f s at %d fps) -> %s"
          % (end, end / float(FPS), FPS, args.output))

    if args.preview:
        scene = bpy.context.scene
        scene.camera = bpy.data.objects["cam_" + args.camera]
        if args.engine == "cycles":
            scene.render.engine = "CYCLES"
            scene.cycles.samples = args.samples
            scene.cycles.use_denoising = True
            backend = enable_gpu()
            if backend == "OPTIX":
                # Denoise on the GPU; the default OpenImageDenoise runs on the CPU and, at this
                # sample count, costs more per frame than the sampling itself.
                scene.cycles.denoiser = "OPTIX"
            # 64 parts move every frame, so without this Cycles re-syncs the scene and rebuilds the
            # BVH for each one and the GPU spends most of the frame idle: measured 5.3 s a frame
            # without, 2.2 s with.
            scene.render.use_persistent_data = True
        else:
            scene.render.engine = eevee_engine()
            scene.eevee.taa_render_samples = args.samples
            # Without ray tracing EEVEE Next gives no contact shadow, and features as shallow as
            # the tray's 0.4 mm pocket ledges render as flat surface.
            for flag in ("use_raytracing", "use_shadows", "use_shadow_jitter_viewport"):
                if hasattr(scene.eevee, flag):
                    setattr(scene.eevee, flag, True)
        scene.render.resolution_x, scene.render.resolution_y = args.resolution
        # Blender 5 gates the video formats behind media_type; 4.x exposes FFMPEG directly.
        if hasattr(scene.render.image_settings, "media_type"):
            scene.render.image_settings.media_type = "VIDEO"
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "HIGH"
        scene.render.filepath = os.path.join(HERE, "renders", "exchange_" + args.camera + ".mp4")
        os.makedirs(os.path.dirname(scene.render.filepath), exist_ok=True)
        bpy.ops.render.render(animation=True)
        print("[anim] preview %s" % scene.render.filepath)


if __name__ == "__main__":
    main()

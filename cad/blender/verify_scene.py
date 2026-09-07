"""Check the animated scene against the static one before spending an hour rendering it.

    "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" --background \
        --python cad/blender/verify_scene.py

Exits non-zero if any check fails, so it can gate a render.  Every check exists because something
actually went wrong once; see BLUEPRINT.md.

  inventory   the expected part counts, and no far-column ghosts
  rig         just after the homing step, every part is exactly where the static scene has it plus
              the offset its own axis should have, and nothing else.  This is the one that
              matters: a stale parent
              matrix silently displaced the whole nest top by the yaw axis offset (5, 3, 0) mm and
              the die ended up hanging off its chuck
  seating     the die's underside sits on the chuck at the nest and on the ledge plane in the tray,
              and its footprint stays inside the chuck pad
  contact     the jaw tips stay inside the contact band's Y window while closed on the die.  Only
              that: the full per-member contact rules belong to the CAD and are already checked in
              cad/gripper/checks.txt, which sees the real geometry rather than bounding boxes
  loop        the last frame returns to the first frame's pose
"""

import json
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
from animate_exchange import (                            # noqa: E402
    FIBER_IN, FIBER_OUT, JAW_FAR, JAW_NEAR, JAW_OPEN, LEDGE_DROP, PARK,
    STAGE_THETA, STAGE_X, TRAVERSE, X_CARRIAGE, Y_CARRIAGE, Z_CARRIAGE)

TOL = 0.02            # mm; the tessellation itself is 0.05 mm, so this only catches real moves
STATIC_PARTS = 70     # 71 assembly members less objective_keepout, the one render aid
ANIMATED_PARTS = 71   # the same 70, plus the copy of the die that starts in a tray pocket

# CLAUDE.md: the die is held only on its end faces, inside the band Y 1.5..4.5.
CONTACT_Y = (1.5, 4.5)


def step_frame(scene, prefix):
    """The frame a named cycle step ends on, from the marks animate_exchange stored."""
    marks = json.loads(scene.get("exchange_steps", "[]"))
    for frame, label in marks:
        if label.startswith(prefix):
            return frame
    sys.exit("no cycle step starting %r - re-run animate_exchange.py" % prefix)


def boxes():
    """Every mesh part's world bounding box, in millimetres."""
    bpy.context.view_layer.update()
    out = {}
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        pts = [obj.matrix_world @ Vector(c) for c in obj.bound_box]
        out[obj.name] = [min(p[i] for p in pts) * 1000 for i in range(3)] + \
                        [max(p[i] for p in pts) * 1000 for i in range(3)]
    return out


def offset(before, after):
    """How far a part moved, assuming it only translated."""
    return Vector((after[i] - before[i] for i in range(3)))


def expected_offsets():
    """Where each part should be at frame 1 relative to the static scene.

    Checked just after step 0: the carriage is still parked at PARK and up at TRAVERSE with the
    jaws open, and the die stage has just homed, so everything below the gripper is back where the
    static scene has it.
    """
    want = {}
    for name in X_CARRIAGE:
        want[name] = Vector((PARK, 0.0, 0.0))
    for name in Z_CARRIAGE:
        want[name] = Vector((PARK, 0.0, TRAVERSE))
    for name in JAW_NEAR:
        want[name] = Vector((PARK - JAW_OPEN, 0.0, TRAVERSE))
    for name in JAW_FAR:
        want[name] = Vector((PARK + JAW_OPEN, 0.0, TRAVERSE))
    for name in STAGE_X + STAGE_THETA + ["die_at_nest"]:
        want[name] = Vector((0.0, 0.0, 0.0))
    for name in Y_CARRIAGE + FIBER_IN + FIBER_OUT:
        want[name] = Vector((0.0, 0.0, 0.0))
    return want


def check(label, ok, detail=""):
    print("[%s] %-10s %s" % ("ok " if ok else "FAIL", label, detail))
    return ok


def check_inventory(static, now):
    good = check("inventory", len(static) == STATIC_PARTS and len(now) == ANIMATED_PARTS,
                 "%d static, %d animated (want %d and %d)"
                 % (len(static), len(now), STATIC_PARTS, ANIMATED_PARTS))
    ghosts = [n for n in now if "_at_far_col" in n or n == "objective_keepout"]
    good &= check("ghosts", not ghosts, "far-column copies present: %s" % ghosts if ghosts else
                  "none, as intended")
    return good


def check_rig(static, now):
    want = expected_offsets()
    bad = []
    for name, before in static.items():
        after = now.get(name)
        if after is None:
            bad.append("%s missing" % name)
            continue
        moved = offset(before, after)
        target = want.get(name, Vector((0.0, 0.0, 0.0)))
        error = (moved - target).length
        if error > TOL:
            bad.append("%s off by %.2f mm (moved %.1f,%.1f,%.1f want %.1f,%.1f,%.1f)"
                       % (name, error, moved.x, moved.y, moved.z, target.x, target.y, target.z))
    for line in bad[:10]:
        print("       %s" % line)
    return check("rig", not bad, "all %d parts at their axis offset" % len(static) if not bad
                 else "%d parts misplaced at frame 1" % len(bad))


def check_seating(scene, frames):
    """The die's underside must rest on the chuck at the nest and on the ledge plane in the tray."""
    good = True
    for frame, where in frames:
        scene.frame_set(frame)
        box = boxes()
        die = box["die_at_nest"]
        if where == "nest":
            chuck = box["nest_chuck_copper"]
            gap = die[2] - chuck[5]
            inside = die[0] >= chuck[0] - TOL and die[3] <= chuck[3] + TOL
            good &= check("seat f%d" % frame, abs(gap) <= TOL and inside,
                          "die bottom %.2f mm from the chuck top, footprint %s"
                          % (gap, "on the pad" if inside else "OVERHANGING in X"))
        else:
            good &= check("seat f%d" % frame, abs(die[2] - LEDGE_DROP) <= TOL,
                          "die bottom at %.2f mm, ledges at %.1f" % (die[2], LEDGE_DROP))
    return good


def check_contact(scene, frame):
    """While closed, the jaw tips must lie inside the contact band's Y window."""
    scene.frame_set(frame)
    box = boxes()
    good = True
    for tip in ("gripper_near_tip", "gripper_far_tip"):
        t = box[tip]
        good &= check("contact", t[1] >= CONTACT_Y[0] - TOL and t[4] <= CONTACT_Y[1] + TOL,
                      "%s Y %.2f..%.2f, band %.1f..%.1f"
                      % (tip, t[1], t[4], CONTACT_Y[0], CONTACT_Y[1]))
    return good


def check_loop(scene, static):
    """The clip has to end where it began, or it cannot be played on repeat."""
    scene.frame_set(scene.frame_start)
    first = boxes()
    scene.frame_set(scene.frame_end)
    last = boxes()
    # The two dice have swapped places by design; everything else must come back.
    dice = {"die_at_nest", "die_from_tray"}
    bad = [n for n in first if n not in dice
           and offset(first[n], last[n]).length > TOL]
    return check("loop", not bad, "start and end poses match" if not bad
                 else "%d parts not back: %s" % (len(bad), bad[:6]))


def main():
    static_path = os.path.join(HERE, "die_tester_station.blend")
    animated_path = os.path.join(HERE, "die_tester_station_animated.blend")
    for path in (static_path, animated_path):
        if not os.path.exists(path):
            sys.exit("missing %s - run build_scene.py and animate_exchange.py first" % path)

    bpy.ops.wm.open_mainfile(filepath=static_path)
    static = boxes()

    bpy.ops.wm.open_mainfile(filepath=animated_path)
    scene = bpy.context.scene

    # Compare after the homing step: the axes are then at pure translations, with the yaw trim of
    # the previous device already wound out, so a rotation cannot masquerade as a displacement.
    homed = step_frame(scene, "0 ")
    scene.frame_set(homed)
    now = boxes()

    gripped = step_frame(scene, "4 ")
    placed = step_frame(scene, "9 ")

    good = check_inventory(static, now)
    good &= check_rig(static, now)
    good &= check_seating(scene, [(gripped, "nest"), (placed, "tray")])
    good &= check_contact(scene, gripped)
    good &= check_loop(scene, static)

    print("[%s] verify_scene" % ("PASS" if good else "FAIL"))
    sys.exit(0 if good else 1)


if __name__ == "__main__":
    main()

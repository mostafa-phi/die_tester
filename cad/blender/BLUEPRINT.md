# Blueprint: how to change the Blender scene without breaking it

Rules distilled from bugs that actually shipped here. Read before editing `build_scene.py` or
`animate_exchange.py`. Longer explanations of what the folder does are in [README.md](README.md).

## The loop

```
CAD change -> python cad/build.py            # regenerates station_assembly.step.zip
           -> step_to_glb.py                 # 35 s
           -> build_scene.py                 # 20 s
           -> animate_exchange.py            # 15 s
           -> verify_scene.py                # 30 s   <- MUST pass before rendering
           -> --preview                      # 12 min per camera
```

**Never render before `verify_scene.py` exits 0.** A preview costs 12 minutes a camera; the checks
cost 30 seconds and have caught every geometry bug so far. Renders are also the *last* step — if a
script changes mid-render, the cameras disagree with each other.

## Non-negotiables

1. **`view_layer.update()` after moving anything you then parent to.** Assigning `.location`
   does not refresh `matrix_world`. `attach()` reads `matrix_world` to build the parent inverse, so
   without the update it silently uses a stale one. This displaced the entire nest top by the yaw
   axis offset (5, 3, 0) mm and left the die hanging off its chuck — invisible in the numbers I was
   checking at the time, obvious on screen.
2. **Keyframe absolute positions only on unparented objects.** The imported parts hang off the
   assembly's root empty, which carries the Z-up correction rotation, so writing a Z move into
   `location` comes out along Y. The two dice are detached with `free_from_parent()` for exactly
   this reason. Everything else moves via a rig empty and never touches `location` directly.
3. **Derive positions from the documents, never from the render.** Every number in the cycle traces
   to `cad/station/README.md`. If a pose looks wrong, fix the number and its source, don't nudge it
   until it looks right.
4. **The cycle is a loop and the README's steps start in the middle of it.** Step 13 leaves the
   gripper parked, fibers in, a device under test; step 0 begins there. Starting from the STEP's
   static pose put the jaws on the die before the fibers had retracted.
5. **Sign conventions bite.** "Park" is −X, towards the tray; +X drives the arm into the microscope
   column. Bringing tray row *r* to the die line is a −7.5·r stage move, not +7.5·r. Both were
   wrong once, and both look plausible until you check the endpoint.
6. **Check what you changed against something independent.** The die-versus-jaws checks passed
   throughout the chuck bug, because both were on rigs and both were wrong together. Comparing
   against the *static* scene is what caught it.

## Adding a moving part

Add its name to the right list in `animate_exchange.py` (`X_CARRIAGE`, `Z_CARRIAGE`, `JAW_*`,
`Y_CARRIAGE`, `STAGE_X`, `STAGE_THETA`, `FIBER_*`), then add the expected offset in
`verify_scene.py`'s `expected_offsets()`. A part in neither is assumed static and the rig check will
fail the moment it moves — which is the point. Bump `STATIC_PARTS` / `ANIMATED_PARTS` if the count
really changed.

## Adding a cycle step

Add a `(label, seconds, targets)` row to `cycle()`. Labels are the addressing scheme: they are
written into the .blend as `scene["exchange_steps"]`, and `verify_scene.py` looks frames up by label
prefix, so **keep the leading step number** (`"4  jaws close"`). No magic frame numbers anywhere.

## Rendering

- **Cycles for anything anyone else sees**, EEVEE only for checking motion. Shallow features — the
  tray's 0.4 mm pocket ledges above all — read as flat surface in EEVEE.
- `use_persistent_data` + the OptiX denoiser: the cycle went from 92 min to 12. Without them the GPU
  sits at 0% between frames rebuilding the BVH for 64 moving parts.
- `enable_gpu()` must run in **every** background session — Cycles' device lives in user
  preferences, not in the .blend, so a run that skips it renders on CPU and says nothing.
- Blender's API names move between versions: `BLENDER_EEVEE_NEXT` became `BLENDER_EEVEE`, video
  output now needs `image_settings.media_type = "VIDEO"`, and actions are slotted so
  `action.fcurves` is gone. Probe with `hasattr`/enum lookups rather than pinning to 5.2.
- OneDrive occasionally locks a PNG mid-write ("cannot save"). Re-run; it is not a scene fault.

## Known simplifications

Keep these listed here rather than letting them look like bugs:

- The fibers move as holder-plus-tip; the NanoMax bodies are single vendor compounds, so the moving
  platform cannot be separated from the bolted-down base without cutting the mesh.
- The yaw trim angle (`--theta-trim`, 0.4°) is illustrative — the real value is read per die from
  the fiducials.
- `nest_kxc04015_unnamed` is a Suruga solid that arrives from the STEP with only an entity number.
- The orbit camera holds one radius, the largest needed across 24 azimuths, so the machine looks
  small at the tighter angles. A per-frame radius would fill the frame but adds a zoom.

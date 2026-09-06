# Nest (chip stage): self-registering, temperature-controlled

`model.py` (CadQuery) → `STEP/`, `STL/`, `renders/`, `checks.txt`. Rebuild with `python cad/build.py`.
Imports `cad/gripper` (the jaws for the clearance checks) and `cad/common` (die, contact rules,
fiber-holder envelope `FIBER`, bench levels `TABLE_Z` / `KB1X1_H`). Used by `cad/station` (`levels()`,
`stack()`, `riser()`, `chuck()`, `cage()`, `cage_parts()`, `moving_members()`, `tec()`, `N`).

![nest](renders/nest_iso.png)
![set-down, jaws open](renders/nest_setdown_iso.png)

## What it does

The gripper sets the die down on a lapped copper vacuum-chuck pad 0.2 mm short of two hard-stop pads,
opens, and pushes the die onto the pads with its own compliant nose (**push-to-stop**). The pads fix X and
yaw, the pad fixes Z, pitch and roll; Y is left free for the fiber stages (which measure the gap anyway)
and caged to ±0.6 mm. Nothing touches the facets or the top surface; only the two stop pads and the chuck
ever touch the die.

| Axis | Mechanism |
|---|---|
| Z, pitch, roll | lapped copper chuck pad (flat ≤ 3 µm), 9 × 5 mm = 75 % of the backside, 0.5 mm inboard of every edge |
| X, yaw | two Semitron ESd 480 **stop pads** on the +X end face (Y 0.6–1.2 and 4.8–5.4, 0.6 mm in from the facets, contact band Z 0.05–0.30): yaw from a 4.2 mm base ≈ 0.03° |
| Y | free; **corner guards** 0.6 mm outside each facet plane only at X ≤ 0.5 and X ≥ 9.5 where no fiber goes, plus an X guard 0.4 mm behind the −X end face |

Milling cannot make a sharp inside corner, and the die's corners are not trusted either: the stop pads
are 0.6 mm from the facets and the 0.2 mm relief between pad and guard keeps the die corner in free
space. The die registers on two pads and a plane, never in a corner.

**Push-to-stop numbers** (`checks.txt`): set down 0.2 mm short, jaws open (+1.5 mm per side), gripper
indexes +1.735 mm in X; the open near nose meets the −X end face, slides the die 0.2 mm onto the pads and
overtravels 0.10 mm, so the flexure blade limits the push to 0.25 N. Vacuum on, jaws retract. The camera
then reads Y and confirms X (a die that stuck to the chuck stops short and is caught there).

## Die stage: the nest moves

The devices span about 8 mm along the die, the NanoMax fiber stages travel only 4 mm, so the die is
stepped from device to device by moving the nest, as the current tester does with its centre stage.
One X move keeps both fibers registered to each other. The gripper meets the nest only at the stage
**home** position; the exchange sequence homes the stage first and the software fence enforces it.

The stack needs 100 mm under the die, so the two NanoMax stages and the Y stage sit on **25 mm riser
plates** (`common.NANOMAX_RISER`) and the table plane is at Z −111; the fiber axis stays at Z 0.5.

| Level (bottom up) | Part | Z (table = −111.0) |
|---|---|---|
| kinematic base | Thorlabs KB1X1 (2374-E0W), 25.4 sq × 12.7 | −111.0 … −98.3 |
| adapter | `STEP/nest_adapter_kb_rpg.step`, 6061, 5 mm: KB1X1 platform pattern → 4 × M3 tapped on the rotary's 32 × 32 (its bolts come down through its body) | −98.3 … −93.3 |
| rotary | **MISUMI RMPG40W-N** motorized worm-gear rotary, horizontal table: body 40 × 55 × 35 tall with the axis 20 mm from the short end, 39 sq table with 8 × M2 on a 10 mm grid and a Ø8 bore; 28 mm 5-phase stepper on the DS102's second axis; motor toward −X, long end toward −Y. **Vendor STEP placed** (`cad/vendor/misumi_RMPG40W-N.step`) | −93.3 … −58.3 |
| adapter | `STEP/nest_adapter_rpg_kxc.step`, 6061, 3 mm: rotary table (M2 at ±10) → KXC04015 base (4 × M3 tapped on 32 mm) | −58.3 … −55.3 |
| X stage | **Suruga KXC04015-C** (crossed-roller, 40 × 40 table, 30 tall, 15 mm travel, ball screw Ø6 × 1 mm lead, 2 µm full / 1 µm half step, ±0.2 µm repeatability, 0.31 kg, 5-phase stepper on the DS102): motor section 59 mm toward −X, its 28 mm motor box 4 mm above the table top. **Vendor STEP placed** (`cad/vendor/suruga_KXC04015-C.step`): it confirms the table's 8 × M3 on a 16 mm grid with a Ø4 centre pin and the base's 4 × Ø3.5 on 32 × 32; the cable loop reaches Y +31 behind the motor, the base solid runs 11 mm further toward the motor than the catalog outline | −55.3 … −25.3 |
| riser | `STEP/nest_riser_6061.step`: 38 × 38 wide body (M3 counterbored on the stage's 32 mm grid, TEC pocket, wire channel) to Z −12, then the 10 mm neck to the cage plate | −25.3 … −4.5 |

**Why the rotary sits under the X stage.** The yaw the fibers see is the sum of the stop-pad
registration (per die, ~0.03°) and two static errors: the nest datum vs the fiber-stage axes and the
X-stage travel vs those axes. With the rotary under the whole stack one rotation aligns both. Being
motorized (worm gear, stepper on the DS102 axis the current centre stage's θ uses today), it is set
with a gauge die and can also trim yaw per die from the camera or a two-device fit, which is what
open-loop device stepping across 8 mm needs (0.02°). Per-device realignment alone tolerates 0.1°.
Dicing squareness between the end face and the facet is the floor no stage can remove. The rotary's
straight cable in the vendor file reaches 179 mm out along −X, which would run into the Y-stage riser;
it is routed down after a 40 mm lead-out (only that lead-out is modelled).

**Travel used.** ±4 mm of the ±7.5 available brings any waveguide at die X 1 … 9 under a fiber fixed
at station X 5. `checks.txt` sweeps the stage from −7.5 to +7.5 and reports the worst clearance of every
moving member (neck, wide body, cage plate, corner blocks, chuck, stage table) against the fixed fibers
and holder bodies: the corner blocks come within 0.4 mm of a fiber at ±4 (their tops are 0.30, 0.09 below
the fiber envelope), the neck and cage plate keep 3.0 mm to the holders at any offset, the riser keeps
5.5 mm to the motor box at −7.5. Both motors point −X because +X is the microscope column and ±Y are the
fiber stages (the station checks confirm 87 mm and more to the column, 10 mm to the input NanoMax base).

**Thermal note.** The riser's wide body is 13.3 mm thick on the stage table, so the KXC04015 table
becomes part of the TEC's hot-side path. Fine below ~2 W; above that put a copper spreader with a
thermal break under the riser or take the heat off with a water block rather than into the stage.

## Fiber access

The fiber tips protrude ~5 mm from their holders (`common.FIBER`), so the holder bodies come to Y −5 and
Y +11 (facets at Y 0 / 6), 25 mm wide, from 8 mm below to 4 mm above the fiber axis (envelope; measure
the real holder). Nothing of the nest may be in that space: the riser is a **10 mm wide neck** (Y −2…8)
from the cage plate down to Z −12, below the holders' underside, and only then widens to 26 × 26 mm for
the TEC and the KB1X1 base. Checked: cage and neck 3.0 mm from the holder faces, chuck block 5.5 mm, wide
body 4 mm under the holders; gripper arms 3.2 mm from the holders at the nest.

## Thermal and vacuum

The chuck is a C101 copper block (Ni-plated, pad lapped after plating): a 9 × 5 mm pad island on a
13 × 4.8 mm block whose neck passes through the cage plate and the riser (0.3 mm air gap all round) to a
**15 × 15 × 2.5 mm TEC** in the riser's wide section at Z −12; the aluminium riser is the hot-side heat
sink (add fins or a water block on the wide section above ~2 W). Thermistor bore Ø1.0 × 5 deep from the
+X face at Z −6. **Vacuum**: 6 × Ø0.5 holes in the pad into a 7 × 4 × 1 mm plenum, bore to a Ø1.5 stub
tube leaving the −X face at Z −6 through a clearance hole in the riser neck (no seal between copper and
riser); silicone hose to the M5 fitting.

## Parts

| File | Material | Make | Notes |
|---|---|---|---|
| `STEP/nest_chuck_copper.step` (+STL) | C101 copper, Ni plate | CNC + lap | pad island, vacuum holes, plenum, neck, stub tube, thermistor bore |
| `STEP/nest_cage_semitron.step` (+STL) | Semitron ESd 480 | CNC | one piece: plate with the copper window, 4 corner blocks (stop pads, X guard, Y guards); 2 × M2 + 2 × Ø1.5 dowels to the riser |
| `STEP/nest_riser_6061.step` | 6061 | CNC | T-riser: neck, 38 × 38 wide body with the TEC pocket, wire channel, vacuum-stub and thermistor clearances, 4 × M3 counterbored to the KXC04015 table |
| `STEP/nest_adapter_kb_rpg.step`, `STEP/nest_adapter_rpg_kxc.step` | 6061 | CNC / waterjet | 5 mm and 3 mm adapter plates between the KB1X1, the RMPG40W-N and the KXC04015 (both stage bolt patterns confirmed in the vendor STEP; the KB1X1 platform pattern still to confirm) |
| — | Suruga KXC04015-C X stage, MISUMI RMPG40W-N rotary, TEC 15 × 15 × 2.5, thermistor, KB1X1 (Thorlabs 2374-E0W) | buy | both stages run on the existing DS102 controller #3 (today's centre-stage X and θ axes) |

Assemblies: `STEP/nest_module_assembly.step` (die seated, jaws closed, fiber/holder envelopes, full
stack) and `STEP/nest_module_setdown.step` (jaws open at the set-down position). `checks.txt` lists every
clearance: corner blocks vs die (seated / set down / Y-offset), vs the jaws closed / open / during the
push, nest vs fiber and holder envelopes, holders vs the gripper, and the moving-nest sweep. Expected
non-OK lines: the two stop pads TOUCH the seated die (by design).

## Open items (measure on the bench)

- Real fiber-holder envelope (width, height below/above the fiber axis, front-face-to-tip): `common.FIBER`.
- RMPG40W-N resolution and repeatability from the MISUMI datasheet (not in the STEP); the KB1X1 platform bolt pattern for the lower adapter.
- TEC part number, heat load and whether the riser needs a water block.
- Die backside finish (vacuum seal on a lapped pad needs it flat and clean).

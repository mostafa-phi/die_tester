# R04 manufacturing package

Parallel-kinematic YZ fiber-alignment flexure, two APA120S actuators.
Frame: X optical (plate thickness), Y lateral, Z up; all files mm.
Analysis and the numbers behind every choice: ../../README.md (section R04).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `body_plate_4_pieces.step`, `body_profile.dxf` | body: frame, 2 input stages, platform | 1 plate → 4 pieces | 6061-T6 | CNC mill: through-profile from the DXF, then ledges/notches, 4 pad lands (2.5 × 5, +0.2 raised), M2 clearance + counterbores on the actuator axes, 28 × M2 clamp taps side-drilled, 2 × M2 holder taps, 4 × Ø4.5 thru, 2 × Ø3 wire ties | profile ±0.05; leaf ledges and notches flat 0.01, parallel 0.02 (they set the leaf planes); pad lands coplanar ±0.02, land gap 13.15 +0.05/−0; stop gaps 0.30 +0.10/−0; both faces ground flat 0.02. **The four pieces come loose after the profile cut - bag them together.** |
| `shim_leaf.step`, `shim_leaf_flat.dxf` | leaf | 8 (+2 spares) | 17-7PH CH900 precision shim, 0.20 mm | shear or laser cut from precision shim stock, drill/laser 4 × Ø2.4; deburr, no bends | thickness 0.20 ±0.005 (stock tolerance); outline ±0.05; flat; edges burr-free (fatigue). Free length 8.5 is set by the clamp bars, not the leaf |
| `clamp_bar.step` | clamp bar | 16 (+4) | 6061-T6 | CNC or saw from strip: 8 × 3.5 × 2.0, 2 × Ø2.2 thru on the 14 screwed bars (2 bars are bonded, no holes needed) | the inner edge R0.3 defines the leaf root: break that edge consistently; faces flat 0.01 |
| `base_plate.step` | mount / base | 1 | any aluminium (6061-T6 fine) | CNC: 10 mm plate, central opening 57 × 57, windows behind the two pockets, 4 × Ø4.5 | flat 0.02 where the body sits (it is the mount reference); it is a stiffness model - replace by the station's real mount if one exists |
| `assembly_reference.step` | everything placed | - | - | reference only: body, leaves, bars, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |
| `drawing_sheet.png` | shop sheet | - | - | - | the tolerances, notes and assembly sequence in one page |
| `BONDING.md` | bench traveller for bonding the leaves | - | - | - | materials, masking, fixture, cure, acceptance checks |

## Bought parts

| part | qty | source | notes |
|---|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT Technologies | 13 ±0.1 pad-to-pad, M2 pads; shim 0.05–0.15 to the 13.15 land gap |
| M2 × 5 SHCS (frame pad), M2 × 8 SHCS (stage pad) | 2 + 2 | any | torque per CEDRAT |
| M2 × 6 SHCS, clamp bars | 28 | stainless A2 | 0.3 N·m + Loctite 243 |
| M4 × 20 SHCS + washers, base | 4 | any | |
| structural epoxy (3M DP460 or Loctite EA 9460) | 1 | | for the 2 bonded tabs (recommended: bond all 16 and use the bars as cure fixtures) |
| 2-channel piezo amplifier | 1 | CEDRAT LA75 range or equivalent | 1.1 µF per channel, ≥0.18 A peak for full stroke at 150 Hz |

## Assembly sequence

1. Deburr and clean body pieces; check each ledge/notch with a shim gauge.
2. Place the frame on the base (4 × M4, do not torque). Fit the two stages and the platform in a
   simple jig (three pins on a flat plate at the platform and stage reference faces; the jig sets
   the leaf-plane parallelism).
3. Insert the 8 leaves on their ledges, bars on top; screw the 14 accessible bars
   (0.3 N·m); for the 2 inner guide bars (and optionally all), apply a thin epoxy film under the
   tab and clamp with the bar for the cure.
4. Cure, remove the jig, check free travel by hand (the stops limit to ±0.3 mm).
5. Fit the actuators: outer guide bars are already in; drop the APA into its pocket with shims to a
   light preload, screw the frame pad from the plate edge (M2 × 5), then the stage pad from the
   coupler void (M2 × 8, ball-end key ≤25° through the front opening or stud + nut).
6. Route the leads out through the back-face windows; tie at the Ø3 holes; connect; drive each
   axis to ±50 µm and confirm no stop contact and no rub.
7. Fit the holder (2 × M2 on the platform front face); the fiber comes in from the back through
   the base opening and the Ø3 platform hole.

Bolt pattern for the base (Y, Z): (56.8, 56.8), (-14.0, -14.0), (32.4, -14.0), (-14.0, 32.4).

# R05 manufacturing package

Parallel-kinematic YZ fiber-alignment flexure, two APA120S actuators.
Frame: X optical (plate thickness), Y lateral, Z up; all files mm.
Analysis and the numbers behind every choice: ../../README.md (section R05).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `frame.step`, `stage.step` (×2, second turned over), `platform.step`; `body_plate_4_pieces.step` + `body_profile.dxf` as the one-plate alternative | body pieces | 1 + 2 + 1 | 6061-T6, 8 mm | CNC mill each piece as its own part (recommended: every ledge, notch and hole is then on an external face) or profile all four from one plate and separate; internal corner radius R1.0 (Ø2 cutter) | profile ±0.05; leaf ledges/notches flat 0.01, parallel 0.02 (they set the leaf planes); pad lands coplanar ±0.02, land gap 13.15 +0.05/−0; stop gaps 0.30 +0.10/−0 are assembled clearances between parts; faces ground flat 0.02. Per-part sheets: `part_frame.png`, `part_stage.png`, `part_platform.png` |
| `shim_leaf.step`, `shim_leaf_flat.dxf` | leaf | 8 (+2 spares) | 17-7PH CH900 precision shim, 0.20 mm | shear or laser cut from precision shim stock; plain rectangle, no holes (bonded); deburr, no bends | thickness 0.20 ±0.005 (stock tolerance); outline ±0.05; flat; edges burr-free (fatigue). Free length 8.5 is set by the clamp bars, not the leaf |
| `clamp_bar.step` | clamp bar | 16 (+4) | 6061-T6 | saw from 8 × 2.0 strip, 3.5 long, long edges chamfered 0.3; no holes, bonded on top of the tab | the inner edge defines the leaf root: chamfer consistently; faces flat 0.01 |
| `assembly_jig.step` | bonding jig | 1 | any aluminium, 8 mm | CNC: 3 mm pockets for platform+arms and both stages (0.02 clearance), 4 dowel seats on the bolt pattern, window under the fiber hole | pocket walls ±0.02, floors flat 0.01: **this jig is what sets leaf alignment and free length** (BONDING.md) |
| `base_plate.step` | mount / base | 1 | any aluminium (6061-T6 fine) | CNC: 10 mm plate, central opening 57 × 57, windows behind the two pockets, 4 × Ø4.5 | flat 0.02 where the body sits (it is the mount reference); it is a stiffness model - replace by the station's real mount if one exists |
| `assembly_reference.step` | everything placed | - | - | reference only: body, leaves, bars, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |
| `drawing_sheet.png` | shop sheet | - | - | - | the tolerances, notes and assembly sequence in one page |

## Bought parts

| part | qty | source | notes |
|---|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT Technologies | 13 ±0.1 pad-to-pad, M2 pads; shim 0.05–0.15 to the 13.15 land gap |
| M2 × 5 SHCS (frame pad), M2 × 8 SHCS (stage pad) | 2 + 2 | any | torque per CEDRAT |
| M2 × 6 SHCS, clamp bars | 0 | stainless A2 | none: every tab is bonded |
| M4 × 20 SHCS + washers, base | 4 | any | |
| structural epoxy (3M DP460 or Loctite EA 9460) | 1 | | for the 16 bonded tabs (recommended: bond all 16 and use the bars as cure fixtures) |
| 2-channel piezo amplifier | 1 | CEDRAT LA75 range or equivalent | 1.1 µF per channel, ≥0.18 A peak for full stroke at 150 Hz |

## Tool access, hole by hole (each body piece machined as a separate part)

| piece | feature | axis | reached from |
|---|---|---|---|
| frame | 4 × Ø4.5, 2 × Ø3 wire ties, windows, pockets | X | the face (through) |
| frame | actuator pad screw: Ø2.2 + Ø4 c'bore ×2 | leg axis | the plate's outer edge - external face |
| frame | pad land (raised 0.2) | - | the pocket side, pocket is through |
| frame | leaf anchor notches | X | through-profile slots; no taps (bonded) |
| stage | actuator pad screw: Ø2.2 + Ø4 c'bore | leg axis | the stage's inner face - external on the loose part |
| stage | ledges, notches, tongue, land | X / - | through-profile / milled from the faces |
| platform | fiber hole Ø3 + chamfers, holder taps 2 × M2 | X | the faces |
| platform | ledges, fork posts | X | through-profile; fork slot 2.6 wide takes a Ø2 cutter |

No feature needs a drill or tap inside a void: the only in-plane holes are the
actuator pad screws (from an external face on each loose part) and there are no
clamp taps because every tab is bonded.

## Assembly sequence

1. Deburr and clean the body pieces; check each ledge/notch with a shim gauge.
2. Seat the platform and both stages in the jig pockets; drop the frame over the jig's dowels.
   The jig sets the leaf planes and the free length; nothing else does.
3. Bond the 8 leaves on their ledges with the bars on top per `BONDING.md` (epoxy film,
   masking of the free length, bar as clamp; spring clips hold the bars during cure).
4. Cure, lift off the jig, check free travel by hand (the stops limit to ±0.3 mm).
5. Fit the actuators: outer guide bars are already in; drop the APA into its pocket with shims to a
   light preload, screw the frame pad from the plate edge (M2 × 5), then the stage pad from the
   coupler void (M2 × 8, ball-end key ≤25° through the front opening or stud + nut).
6. Route the leads out through the back-face windows; tie at the Ø3 holes; connect; drive each
   axis to ±50 µm and confirm no stop contact and no rub.
7. Fit the holder (2 × M2 on the platform front face); the fiber comes in from the back through
   the base opening and the Ø3 platform hole.

Bolt pattern for the base (Y, Z): (56.8, 56.8), (-14.0, -14.0), (32.4, -14.0), (-14.0, 32.4).

# R06 manufacturing package - one-piece CNC plate

Parallel-kinematic YZ fiber-alignment flexure, two APA120S actuators, monolithic
7075-T6 (Fusion 'Aluminum 7075' values, as fem_r01) plate 83.7 x 83.7 x 8 mm with eight thin-wall milled leaves
(0.50 x 18.1 mm, 16:1) and pin hard stops. Frame: X optical (plate thickness),
Y lateral, Z up; all files mm. Analysis: ../../README.md (sections "Monolithic CNC sweep" and R06).

| file | part | qty | material | process | what matters |
|---|---|---|---|---|---|
| `plate.step` (+ `plate_profile.dxf`, the through profile 1:1) | the flexure | 1 | 7075-T6 (Fusion 'Aluminum 7075' values, as fem_r01), 8 mm | CNC milling, one setup per face plus the edge drills; internal corners R1.0 (dia 2 cutter) | the 8 leaves: 0.50 +/-0.02 thick, faces flat/parallel 0.01 over 8, perpendicular 0.01; finished last, light passes, hand deburr only. Pad lands coplanar +/-0.02 per leg, land gap 13.15 +0.05/-0. Profile +/-0.05 elsewhere; faces ground flat 0.02 |
| `drawing_sheet.png` | shop sheet | - | - | - | every note above, dimensioned; send with the STEP |
| `base_plate.step` | mount | 1 | any aluminium | CNC, 10 mm plate, opening 59 x 59, 4 x dia 4.5 | flat 0.02 where the flexure sits; a stiffness model - the station's real mount replaces it |
| `assembly_reference.step` | everything placed | - | - | reference: plate, 2 stop pins, actuator envelopes | the actuators are datasheet envelopes; CEDRAT's STEP replaces them |

## Bought parts

| part | qty | notes |
|---|---|---|
| APA120S amplified piezo actuator | 2 | CEDRAT; 13 +/-0.1 pad-to-pad, M2 pads; shim 0.05-0.15 to the 13.15 land gap |
| dowel pin dia 2 m6 x 12 (ISO 8734 / DIN 6325) | 2 | pressed into the dia 2 H7 holes from the outer edge; +/-0.30 of travel per leg |
| M2 x 5 SHCS (frame pad), M2 x 8 SHCS (stage pad) | 2 + 2 | torque per CEDRAT; the stage screw's head bears on the stage's inner face (no counterbore), driven from the coupler void with a ball-end key or fitted as stud + nut |
| M4 x 20 SHCS + washers | 4 | base |
| 2-channel piezo amplifier (CEDRAT LA75 range or equivalent) | 1 | 1.1 uF per channel, >= 0.18 A peak for full stroke at 150 Hz |

## Ordering on Xometry (or any CNC shop)

- Process: CNC machining (milling). Material: 7075-T6 (Fusion 'Aluminum 7075' values, as fem_r01). Finish: as machined, no anodising
  (a coating on the leaves changes their stiffness and hides burrs). Quantity: 1 (+1 spare recommended: the
  0.5 mm walls are the one feature a shop can scrap).
- Tolerance: choose the tightest general class offered (+/-.001" / 0.025 mm) and list the critical locations
  as the eight leaf thicknesses (0.50 +/-0.02), the four pad lands (coplanar +/-0.02, gap 13.15 +0.05/-0)
  and the two dia 2 H7 pin holes: 14 locations. Everything else is +/-0.05 per the sheet.
- Threads: 2 x M2 x 6 deep (front face). Upload `plate.step` and `drawing_sheet.png`; the DXF is
  a convenience for the profile only.
- Expect a DFM note on the 0.50 mm walls (16:1; most guides list 0.8 mm minimum for metals). Answer
  it with the sheet's leaf note (rough leaving 0.3, finish last both sides, no tumbling). If the shop declines,
  order variant m8t60k12 (0.60 walls, 13:1) from the same drawing set: 375 Hz instead of 431 Hz first mode.
- Wire EDM is an acceptable alternative for the leaves only (through-profile), if the shop prefers it.

## Tool access, feature by feature (one piece, no internal-face drilling)

| feature | axis | reached from |
|---|---|---|
| profile: leaves, voids, pockets, windows, notches, stop notches | X | both faces (through) |
| 4 x dia 4.5 bolt holes, 2 x dia 3 wire ties, fiber hole dia 3 + chamfers | X | the faces |
| 2 x M2 holder taps | X | front face |
| 4 pad lands (raised 0.2) | - | milled from the pocket, which is through |
| pad screw hole per leg: dia 2.2 through wall, pocket and stage; c'bore dia 4.0 x 3.0 | leg axis | the outer edge, one straight drill (6 wall + 13.1 pocket + 16 stage) |
| 2 x dia 2 H7 pin holes | across the leg | the outer edge, through the free wall into the notch |

## Assembly sequence

1. Deburr by hand, ultrasonic clean; check every leaf with a micrometer (0.50 +/-0.02) and sight the faces.
2. Press the two stop dowels from the outer edges until flush 1 mm below the edge; check +/-0.30 free travel
   of each stage by hand (it must move freely and stop crisply both ways).
3. Fit the actuators: drop each APA into its pocket with shims to a light preload, screw the frame pad from
   the edge (M2 x 5), then the stage pad from the coupler void (M2 x 8, ball-end key, or stud + nut).
4. Route the leads out at the back face; tie at the dia 3 holes; drive each axis to +/-50 um and confirm
   no stop contact and no rub.
5. Fit the holder (2 x M2 on the platform front face); the fiber comes in from the back through the base
   opening and the platform hole.

Bolt pattern for the base (Y, Z): (58.7, 58.7), (-14.0, -14.0), (36.1, -14.0), (-14.0, 36.1).

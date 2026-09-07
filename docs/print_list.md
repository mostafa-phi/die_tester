# Print list: every custom part, what it is made of, and how to make it

**Status:** rev. 1 (2026-09-07). Companion to the CAD package (`cad/`), which exports one STEP and one STL per
custom part. This list says which parts are printed in **Bambu PPA-CF on the H2C** for the prototype, which
are machined from the start, and what to do to each print before it goes on the machine. The station parts
were sized for the MISUMI LX20 actuators (`cad/station/README.md`); the bolt patterns come from the
manufacturer STEP files.

## 1. Printer settings that apply to every PPA-CF part

- 0.4 mm hardened-steel nozzle, 0.16 mm layers (0.2 for the risers), 5 walls, 4 top/bottom layers, 40 %
  gyroid infill; filament dried; chamber heated; textured PEI plate with glue for the 300 mm bar.
- Holes are modelled at their **finished** size and print about 0.2 mm undersize. Drill or ream every hole
  that takes a bolt or a pin: tap-drill holes (Ø2.5 for M3, Ø3.3 for M4) are tapped directly in PPA-CF, or
  opened to Ø4.0 / Ø5.6 for heat-set inserts where a joint is undone often; dowel holes (Ø2.9 / Ø3.9) are
  reamed to H7 for Ø3 / Ø4 pins; clearance holes (Ø4.5, Ø6.6) are drilled through.
- Mounting faces that meet a stage or a table (the riser tops and feet, the bracket base, the block face on
  the Z table, the deck's pocket floor) get one pass on a surface plate with 400-grit paper so the print's
  top-layer texture does not set the flatness.
- Carbon-filled surfaces must not touch a die anywhere but its backside. None of the parts below touches a
  die; the tray touches the backside only.
- A printed part in the fibre-to-die metrology loop is a fit-check part, not a final part: the NanoMax
  risers and the nest stack adapters swell with humidity by tens of µm and creep under bolt preload.

## 2. Station mounting parts (`cad/station/STL/`)

All new in this revision; they replace the envelope boxes the station model used to carry. Dimensions
are the default (vertical-gripper) layout; the `_h` files are the horizontal-gripper variant of the two
parts that depend on it.

| # | File | Part | Size (mm) | Print orientation | After printing | Bolts | Final |
|---|---|---|---|---|---|---|---|
| S1 | `x_axis_riser_6061.stl` | X riser bar under the X actuator: 40 wide body with a 60 × 8 foot flange | 300 × 60 × 118 | on its side (118 × 300 face down); 0.2 layers; ~0.7 kg | tap 10 × M3 on the top (LX20 base pattern, rows 18 apart, pitch 60); ream 2 × Ø4 pin holes on the centre line; the foot slots take M6 or ¼-20 on a 25 mm / 1″ grid | rail: M3 × 8 SHCS from inside the rail channel; table: 10 × M6 × 16 | 6061 bar 40 × 120 × 300 or an 80/20 40 × 120 profile with a tapped top plate |
| S2 | `y_axis_riser_6061.stl` | Y riser bar under the Y actuator: 40 wide body, 80 × 8 foot flange | 200 × 80 × 63 | flat on the flange | tap 6 × M3 (top), ream 2 × Ø4 | as S1 (6 × M3, 6 × M6) | 6061 bar |
| S3 | `tower_bracket_6061.stl` | Angle bracket on the X table plate carrying the Z actuator: 60 × 60 × 10 base, 10 mm leg, gusset rib | 60 × 60 × 110 | base plate down, leg up (rib is self-supporting at 56°) | drill 4 × Ø4.5 + Ø8 counterbore (table pattern 20 × 45), ream 2 × Ø3 dowels in the base; tap 4 × M3 in the leg's +X face (Z rail base pattern), ream 2 × Ø4 pins | X table: 4 × M4 × 10 SHCS + 2 × Ø3 × 8 dowels; Z rail: M3 × 8 from inside its channel | 6061, machined from a 60 × 60 × 110 block or welded angle |
| S4 | `arm_6061.stl` (`arm_6061_h.stl`) | One-piece arm: 33-deep adapter block on the Z table, 25 sq bar along +Y, 8 mm end plate over the gripper bracket, extended 38 mm in −X to carry the tray camera (4 × M2 tap-drill) | 109 × 191 × 57 (block 33 × 71 × 57, bar 25 × 25 × 171, plate 72 × 40 × 8) | station −X face down: block and bar both rest on the bed, the end plate stands as a wall; no supports | drill 4 × Ø4.5 through the block (counterbored Ø8 from the outside, 25 deep), ream 2 × Ø3 dowels in the block face; tap 4 × M4 in the end plate, ream its 2 × Ø3 dowels | Z table: 4 × M4 × 40 SHCS + 2 × Ø3 × 8 dowels; gripper bracket: 4 × M4 × 16 from below + 2 × Ø3 × 10 dowels | 6061; the bar can be a stock 25 sq bar bolted into a machined block |
| S5 | `tray_deck_6061.stl` | Flat tray deck on the Y table plate; the tray drops onto two Ø3 datum pins (round hole and slot in its X rims) | 160 × 124 × 6 | flat | drill 4 × Ø4.5 + Ø8 counterbore from the top (Y table pattern 20 × 45), ream 2 × Ø3 dowels to the table and the 2 × Ø3 H7 pin holes (press the Ø3 m6 × 10 pins 3.0 mm proud); check the top flat within 0.05 mm, since it sets the ledge plane | Y table: 4 × M4 × 10 SHCS + 2 × Ø3 × 8 dowels; tray: 2 × Ø3 m6 × 10 dowel pins | 6061 plate, or keep the print if the top measures flat |
| S6 | `nanomax_riser_6061.stl` (×2) | 25 mm riser plate under each NanoMax, Ø6.6 through holes on the 25 mm grid | 112 × 112 × 25 | flat | drill the 16 holes through | M6 × 50 SHCS through the NanoMax slots and the plate into the table | **6061 plate, final** (metrology loop); print only for the fit check |

Bolt lengths assume 1 mm of washer; check each against the tapped depth before ordering.

## 3. Gripper (`cad/gripper/STL/`)

| # | File | Part | Prototype | After printing | Final |
|---|---|---|---|---|---|
| G1 | `bracket_6061.stl` (`_h`) | L-bracket between the SMC body and the arm end plate | print, bracket plate down | drill 2 × Ø3.4 (M3 through the SMC body), 4 × Ø4.5 (interface), ream 2 × Ø3 dowels | 6061 |
| G2 | `far_arm_6061.stl` (`_h`) | rigid arm, 3 × 3 bar, head with the tip-block thread | print, bar flat on the bed | drill the 2 × Ø2.2 root holes, tap M2 in the head | 6061, hard anodised |
| G3 | `near_arm_6061.stl` (`_h`) | compliant arm with the blade slot | print, bar flat | the 0.18 mm slot does not print: print it 0.5 wide and pot the blade with the M2 clamp screw | 6061 |
| G4 | `far_tip_block_semitron.stl`, `near_tip_block_semitron.stl` | crowned noses | **machine now** (Semitron ESd 480): sub-0.1 mm features, and carbon-filled surfaces would abrade the die end faces | — | same |
| G5 | `flexure_blade_0p127_steel.stl` | blade | cut from 0.005″ feeler stock | — | same |

## 4. Nest (`cad/nest/STL/`)

| # | File | Part | Prototype | Final |
|---|---|---|---|---|
| N1 | `nest_riser_6061.stl` | T-riser with the TEC pocket | print for fit and cold trials (rotary table pattern 8 × M2: drill Ø2.2 counterbored) | 6061: it carries the TEC heat |
| N2 | `nest_adapter_kb_kxc.stl` | 3 mm plate KB1X1 → X stage | print for fit (tap 4 × M3) | 6061 or waterjet; metrology loop |
| N3 | `nest_spacer_kxc_rot.stl` | 8 mm spacer X stage → rotary, Ø4 centre dowel | print for fit (drill 4 × Ø3.4, ream Ø4) | 6061; metrology loop |
| N4 | `nest_cage_semitron.stl` | cage with stop pads and guards | print a **coarse** version for sequence rehearsal on silicon blanks only (guards 0.6 mm from the facets and 0.4 mm pads do not print to tolerance) | Semitron ESd 480, machined |
| N5 | `nest_chuck_copper.stl` | lapped vacuum chuck | **machine now**: vacuum-tight, flat to 3 µm, thermal path | C101, Ni plated, lapped |

## 5. Tray (`cad/tray/STL/`)

| # | File | Part | Prototype | After printing | Final |
|---|---|---|---|---|---|
| T1 | `wafer_tray_8x14.stl` | 112-pocket wafer tray (corner-post pockets) | print flat, 0.16 layers, 0.4 nozzle (ledges 1.0 × 0.8 mm; the 0.7 mm corner posts are under two nozzle widths, so print them as single-wall features and check a few with a pin gauge; 0.4 mm facet clearance at the posts) | measure the ledge plane with an indicator: flat within 0.1 mm over 132 mm, else skim or reprint; check surface resistance of a coupon | print (PPA-CF), or Semitron if flatness or ESD fail |

## 6. Order of printing

1. Tray, gripper bracket and arms, tower bracket, arm, deck: the hand-cycling rig and the sequence
   rehearsal need these first. Machine the two tip blocks and the chuck in parallel.
2. X and Y risers once the LX20 actuators are in hand, so the base-hole positions can be checked against
   the real rails before tapping.
3. NanoMax risers and nest adapters as fit checks only; order the aluminium versions with the chuck.

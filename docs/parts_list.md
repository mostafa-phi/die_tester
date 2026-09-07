# Parts list: buy, machine, print

**Status:** rev. 1 (2026-09-07). One page that sorts every part of the prototype by how it is obtained.
Prices, vendors and lead times are in [`bom_month1.md`](bom_month1.md); print settings, orientations and
finishing steps are in [`print_list.md`](print_list.md); the CAD files are under `cad/*/STEP` and `cad/*/STL`.
"Prototype" is the first build on the bench rig and the tester; "final" is what replaces a printed part after
the hand-cycling and sequence trials.

## 1. Purchase

| Group | Part | Qty | Note |
|---|---|---|---|
| Transport axes | MISUMI LX2005CG-B1-T2042-300 / -200 / -100 (X / Y / Z) | 1 each | high grade, 1 long block, lead 5, cover, low-particulate grease, T2042 plate |
| | Oriental Motor AZM46AK (X, Y), AZM46MK with brake (Z) | 2 + 1 | αSTEP AZ, 42 mm, absolute encoder |
| | Oriental Motor AZD-KD drivers (or one AZD-KR2D-class multi-axis) + cable sets | 3 | 24/48 V DC, RS-485 Modbus |
| | 48 V supply, Mean Well LRS-150-48 class | 1 | |
| | slit clamp couplings Ø4 (screw) × Ø6 (motor), MISUMI MCSLC20 class | 3 | not included with the actuator |
| | LX20 sensor sets: DG20X flag kit + 3 × GXL-8F per axis | 3 | home / limit backstop |
| Die stage | Suruga KXC04015-C X stage | 1 | runs on the existing DS102 #3 |
| | MISUMI RMPG40W-N motorized rotary | 1 | DS102 θ axis |
| | Thorlabs KB1X1 kinematic base | 1 | |
| | micro-TEC 15 × 15 × 2.5 (Laird OptoTEC OT08 class or TE Technology TE-63-1.0-1.3) | 1 (+1) | |
| | 10 kΩ glass-bead thermistor | 2 | |
| Gripper and pneumatics | SMC MHZ2-6D-M9N with 2 × D-M9N switches | 2 | one spare |
| | SMC SY3120-5LZ-M5 (gripper valve) | 2 | one spare |
| | SMC VQ110-5L-M5 (chuck vacuum, blow-off) | 2 | |
| | SMC AS1201F-M3-04 class meter-out speed controllers | 2 | ≤ 10 mm/s finger speed |
| | SMC IR1000-01 precision regulator (+ IR1000 class for the few-kPa blow-off) | 1 + 1 | |
| | SMC ZSE30A-01-N-L vacuum switch | 1 | seat sensing |
| | KQ2H04-M5 ×10, KQ2H04-01S ×4, KQ2T04-00A ×4, TU0425 Ø4 tubing 20 m | — | |
| | Mean Well LRS-50-24, 2 × 24 V relay/isolator modules, 24→5 V optocoupler inputs | 1 set | valves and switches to the NI USB-6363 |
| | die-present sensor (blade-deflection photo-microsensor or inductive) | 1 | chosen after the rig trials |
| Consumables and hardware | 0.005″ C1095 feeler-gauge stock (flexure blades) | 1 pack | 6 blades |
| | Loctite EA 9460 (blade-to-block bond) | 1 | |
| | gauge die 10.000 × 6 × 0.500, steel or ceramic | 1 | ground; sets the switches and the 0.10 mm top gap |
| | stainless SHCS: M2 × 5/6, M3 × 8/16, M4 × 10/16/40, M6 × 16/50; Ø3 × 8/10 and Ø4 × 8 dowel pins; 0.05 mm shim stock | — | per `print_list.md` |
| | heat-set inserts M3 / M4 (optional, for joints undone often) | — | |
| Stock for machining | C101 copper (chuck), Semitron ESd 480 rod/sheet (cage, tip blocks), 6061 plate and bar (risers, brackets, adapters) | — | Boedeker / Professional Plastics; McMaster |
| Printing | Bambu PPA-CF filament, hardened 0.4 nozzle | 2 spools | ~2 kg of parts incl. the risers |
| Bench rig | Thorlabs PT3 (if not in stock), MB1218 breadboard, AP90 / RS2P / TR75 | 1 set | hand-cycling rig |
| | AWS GEMINI-20 0.001 g scale | 1 | jaw force check |
| | Ideal-tek 2ACFR.SA.1 tweezers with A2ACF carbon-fiber tips | 3 | the only approved hand tool |
| | Simco-Ion Aerostat PC2 ionizer | 1 | before real dies are cycled |
| | Dino-Lite AM7915MZT (optional) | 0–1 | if the microscope cannot serve the rig |
| | compressor + SMC AW20 filter-regulator (if no house air); KNF N86 KN.18 pump (if no house vacuum) | 0–1 each | |
| Test dies | Si 100 mm wafers, 500 µm, diced 10 × 6 (APD) | 2 wafers | ~200 blanks |
| | LN wafer, 0.5 mm, diced 10 × 6 | 1 wafer | Gate 1 |

## 2. Machine

| Part | File | Material | Process | When |
|---|---|---|---|---|
| Vacuum chuck | `cad/nest/STEP/nest_chuck_copper.step` | C101 copper, Ni plated | CNC, pad lapped in-house ≤ 3 µm | now (+1 spare) |
| Cage with stop pads and guards | `cad/nest/STEP/nest_cage_semitron.step` | Semitron ESd 480 | CNC | now |
| Far and near tip blocks | `cad/gripper/STEP/far_tip_block_semitron.step`, `near_tip_block_semitron.step` | Semitron ESd 480 | micro CNC, crown R 30 | now, 3 of each |
| Gauge die | — | steel or ceramic | grind | now |
| NanoMax riser plates ×2 | `cad/station/STEP/nanomax_riser_6061.step` | 6061 plate 112 × 112 × 25 | mill, drill | with the chuck (metrology loop) |
| Nest T-riser | `cad/nest/STEP/nest_riser_6061.step` | 6061 | CNC | final (TEC heat path) |
| KB1X1 → KXC adapter, KXC → rotary spacer | `cad/nest/STEP/nest_adapter_kb_kxc.step`, `nest_spacer_kxc_rot.step` | 6061 | waterjet + tap / mill | final (metrology loop) |
| Gripper bracket, far arm, near arm | `cad/gripper/STEP/bracket_6061.step`, `far_arm_6061.step`, `near_arm_6061.step` | 6061-T6, arms hard anodised | CNC | final, after the rig trials |
| Tower bracket | `cad/station/STEP/tower_bracket_6061.step` | 6061 | mill from a 60 × 60 × 110 block | final |
| Arm | `cad/station/STEP/arm_6061.step` | 6061 (stock 25 sq bar + machined block acceptable) | mill | final |
| X and Y riser bars | `cad/station/STEP/x_axis_riser_6061.step`, `y_axis_riser_6061.step` | 6061 bar (or 80/20 40 × 120 profile with a tapped top plate) | saw, face, drill, tap | final |
| Tray deck | `cad/station/STEP/tray_deck_6061.step` | 6061 plate, 2 × Ø3 m6 × 10 dowel pins pressed in | mill, ream | final, or keep the print if the top measures flat |

## 3. Print (Bambu H2C, PPA-CF)

| Part | File | Purpose | Notes |
|---|---|---|---|
| Wafer tray | `cad/tray/STL/wafer_tray_8x14.stl` | prototype **and** likely final | ×4; ledge plane flat within 0.1 mm; check surface resistance |
| Gripper bracket, far arm, near arm | `cad/gripper/STL/bracket_6061.stl`, `far_arm_6061.stl`, `near_arm_6061.stl` | prototype (rig and tester) | blade slot printed 0.5 wide and potted |
| Tower bracket | `cad/station/STL/tower_bracket_6061.stl` | prototype | |
| Arm | `cad/station/STL/arm_6061.stl` | prototype | one piece, no supports on its side |
| Tray deck | `cad/station/STL/tray_deck_6061.stl` | prototype, possibly final | |
| X riser bar | `cad/station/STL/x_axis_riser_6061.stl` | prototype | 300 mm, on its side, ~0.7 kg |
| Y riser bar | `cad/station/STL/y_axis_riser_6061.stl` | prototype | |
| Nest T-riser, KB adapter, spacer | `cad/nest/STL/nest_riser_6061.stl`, `nest_adapter_kb_kxc.stl`, `nest_spacer_kxc_rot.stl` | fit check and cold trials only | metrology loop: aluminium for anything measured |
| Cage, coarse version | `cad/nest/STL/nest_cage_semitron.stl` | sequence rehearsal on silicon blanks only | never meets a TFLN die |
| NanoMax riser plates | `cad/station/STL/nanomax_riser_6061.stl` | fit check only | |

Not printed: the tip blocks (feature size and abrasion), the chuck (vacuum, flatness, heat), the blade (feeler
stock), the gauge die.

## 4. Existing on the bench, reused

Two Thorlabs NanoMax 300 (MAX313D/M) with fiber holders, the microscope with its column, the Suruga DS102
controller #3 (die-stage X and θ), the NI USB-6363, the optical table.

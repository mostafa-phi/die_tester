# Month‑1 Bill of Materials — Robotic Die Exchange Prototype

Companion to `prototype_plan_month1.md`. Every line is an orderable part or a quote
request to a named vendor. Prices are US list/street prices checked in September 2026
unless marked **quote**; lead times are for in‑stock items. Total for everything to
order now: **≈ $10–12 k with Velmex axes** (≈ $7–9 k if the lab already has a manual XYZ
stage, house vacuum and compressed air; ≈ $13–16 k with Zaber/Thorlabs axes); the transfer
axes are the largest item and are also the production kinematics.

**Check before ordering (day 0):**
1. Is there compressed air (or nitrogen at ≥ 0.3 MPa) at the bench? If yes, skip A6.
2. Is there house vacuum at the bench? If yes, skip A7.
3. Is a Thorlabs PT3 (or any 25 mm manual XYZ) in lab stock? If yes, skip B1.
4. Ask the dicing vendor today: tape type on the current lot, post‑dicing street width,
   frame size, die thickness distribution.

---

## A. Order on day 1 (lead time or critical path)

| # | Item | Exact part | Vendor | Unit price | Qty | Lead | Why this one |
|---|---|---|---|---|---|---|---|
| A1 | Transfer axes (prototype **and** production kinematics) | **Bench‑level 3‑axis Cartesian**, right‑sized to the need (±0.3 mm X/Y placement; ±0.05 mm Z for the stepped jaw). **Default: Velmex BiSlide** lead‑screw stages — X 300 mm (MN10‑0300‑M02‑21 class) + Y 150 mm under the stick deck + Z 50–100 mm, with a **VXM‑3** stepper controller (ASCII serial, trivial from Python), repeatability ~5 µm. **Budget option:** three stepper ball‑screw/lead‑screw modules (FUYU FSL40 class or igus drylin SLW) on a GRBL/Duet G‑code controller, ~$1–2 k total, repeatability 10–50 µm — adequate but no vendor support and more build/tune time. **Premium option:** Zaber X‑LSM150A‑E03 ×2 + X‑LSM050A‑E03 (built‑in controllers, Zaber Motion Library) or Thorlabs LTS150 ×2 + MTS50‑Z8 (Kinesis). | Velmex (US, direct); FUYU/igus; Zaber; Thorlabs | Velmex **quote** (~$4–5 k for 3 axes + controller); budget ~$1–2 k; premium ~$7–10 k | 1 set | Velmex 2–3 wk; modules 1–2 wk; Thorlabs in stock; Zaber 2–4 wk | The tool must enter a ~13 mm corridor under the objective horizontally along die X and never cross the fiber line. A low X axis carrying a short Z and a ~120 mm horizontal gripper arm does exactly that; the stages never enter the microscope or fiber volumes. Precision stages are **not** needed for accuracy; they are chosen for stiffness under the cantilevered arm, predictable swept volume, and a driver that works on day 1. No θ axis. Same kinematics scale to the production cell. |
| A1b | Bench‑only fallback robot (only if A1 lead time > 3 weeks) | **Dobot MG400** (articulated desktop arm: J2/J3 pitch in a vertical plane, parallelogram wrist, ±0.05 mm, 24 V DIO, TCP/IP) | RobotLAB $2,890; RobotShop; Dobot US | $2,890 | 0–1 | 1–2 wk | Fine for the stick → nest → stick cycling rig where there is no microscope. **Not for the tester**: its forearm approaches from above and behind, into the microscope column's volume, and it is not a horizontal‑plane SCARA. |
| A2 | Gripper actuator | **SMC MHZ2‑6D‑M9N** (ø6 parallel gripper, 4 mm total stroke, 0.15–0.7 MPa, with two D‑M9N solid‑state position switches) | SMC USA / Motion / Southern Controls / RS | ~$60–120 gripper; ~$40 per switch | 2 (one spare) | in stock | Its 3.3 N external force is irrelevant: the die load is set by the flexure jaw (see fingers). Two switches give "closed on die" vs "closed empty" = die‑present detection. Sensors and valves wire to the stage controllers' digital I/O (Zaber X‑MCC / Thorlabs KDC101 trigger lines) or to the NI USB‑6363 via a 24 V ↔ 5 V isolator module; confirm N/P polarity accordingly. |
| A3 | Jaw fingers + flexure | **Custom**: 2 aluminum 6061 fingers per Fig. 3 (stepped nose 0.35 mm, 0.6 mm set‑back, ≥ 13 mm long), one rigid, one carrying a spring‑steel flexure blade (k ≈ 3 N/mm) with a hard stop; jaw inserts machined from **Semitron ESd 480** (static‑dissipative PEEK) | Protolabs / Xometry CNC; Semitron from Boedeker or Professional Plastics (cut‑to‑size rod/sheet, in stock) | quote (~$300–600 incl. material) | 2 sets | 5–7 working days | Force = k × (δ + die tolerance) ⇒ 0.3 ± 0.08 N for ±25 µm dies, independent of air pressure. Semitron ESd 480 is the standard dissipative jaw material for bare‑die handling. |
| A4 | Test nest | **Custom**: 17‑4 PH H900 (or 6061 hard‑anodized) block per Fig. 4 — two rails 0.9 × 1.5 × 10 mm at 1.0 mm inboard of the facet planes, rail tops lapped flat ≤ 5 µm, 4 × Ø0.6 mm vacuum ports per rail into a common M5 port, deck ≥ 0.4 mm below jaw bottoms, ≥ 1.6 mm free beyond each end face; bolt pattern for B3 kinematic base | Protolabs / Xometry CNC (lapping in‑house on a granite plate with 3 µm diamond film, or a local lapping shop) | quote (~$400–800) | 1 (+1 spare rail insert if two‑piece) | 1 wk | The one precision part. Two‑piece (base + rail insert) is recommended so rails can be re‑lapped or re‑made without the base. |
| A5 | Wafer trays | **Custom SLA print**: one tray per wafer, **8 columns × 14 rows = 112 pockets**, 128 × 106 × 6 mm (`docs/cad/station_assembly.py`): ledges 1.0 mm wide under the facet‑edge strips, 0.8 mm tall; 2 mm jaw space beyond each end face; Y walls at 0.4 mm clearance; lid; DataMatrix on the rim. Pocket (row, col) mirrors the wafer map. Material: Formlabs **Rigid 10K** if a Form 3/4 is in house, else Protolabs Accura Xtreme / Somos WaterShed | In‑house printer or Protolabs SLA | ~$120–250 each | 4 | 2–4 days | One wafer = one tray; dies return to their own pocket after test. Cheap enough to iterate weekly. |
| A6 | Compressed air (if no house air) | **California Air Tools 1P1060S** (0.6 hp, 1 gal, 56 dBA, oil‑free) + **SMC AW20‑N02‑Z‑A** filter‑regulator | Home Depot / Walmart / Ace; SMC distributors | $149–159 compressor; ~$60 FR | 1 | in stock | Quiet enough for an optics lab; avoids the electric‑gripper alternative (Schunk EGP 25: 20–40 N min force, ~$1.5–2 k, 2–4 wk; Zimmer GEP2010: 50–200 N, $2,100 — both far too strong without the flexure). |
| A7 | Vacuum source (if no house vacuum) | **KNF N86 KN.18** diaphragm pump (6 L/min, 100 mbar ultimate) | KNF / lab suppliers (~$300 new EU list; US new quote; used ~$240) | ~$300–450 | 1 | in stock | Rail hold and seat sensing only need ~−60 kPa. |
| A8 | Test dies — silicon blanks | **UniversityWafer** 100 mm Si, 500 µm, DSP (e.g., FZ undoped <100>, $43.90 ea, MOQ 25 for that SKU; single‑wafer SKUs exist) → dice to 10 × 6 mm at **American Precision Dicing, San Jose** on UV tape, cure + expand before shipping | UniversityWafer; APD | wafer ~$44–80; dicing **quote** (~$150–300/wafer) | 2 wafers (~200 dies) | 1 wk | Cycling blanks. Also the first real "diced wafer on expanded UV tape" to practice on. |
| A9 | Test dies — LN blanks | 3″ or 4″ **X‑cut LiNbO₃, 0.5 mm, DSP** (Precision Micro‑Optics, MTI Corp, Crystro, UniversityWafer) → dice as A8 | PMO / MTI / Crystro; APD | **quote** (~$150–400/wafer) | 1 wafer | 1–2 wk | Realistic contact stress and pyroelectric behaviour for Gate 1. |
| A10 | Bench ionizer | **Simco‑Ion Aerostat PC2** benchtop ionizing blower (91‑PC2‑US‑01), 120 V | TEquipment / TestEquity / ISC Sales | $1,096 | 1 | in stock | LN charges with every temperature change; required before real dies are cycled. |

## B. Order in week 1 (short lead, needed for the manual rig and pneumatics)

| # | Item | Exact part | Vendor | Unit price | Qty | Notes |
|---|---|---|---|---|---|---|
| B1 | Manual XYZ for the hand‑cycling rig | **Thorlabs PT3** (1″ XYZ, ¼‑20) or **PT3/M** | Thorlabs / Fisher | $1,350 | 1 (skip if in stock) | Carries the gripper over nest and stick for Gate 1. |
| B2 | Rig plate | **Thorlabs MB1218** 12 × 18″ breadboard | Thorlabs / Fisher | $281 | 1 | Common plate for nest, stick, manual stage; later the robot bench. |
| B3 | Nest kinematic base | **Thorlabs KB1X1** (or KB1X1/M) kinematic base | Thorlabs | ~$150 | 1 | Lets the nest move between rig and tester and return repeatably. |
| B4 | Right‑angle bracket + posts for the gripper | Thorlabs **AP90**, **RS2P**, **TR75** as needed | Thorlabs | ~$150 total | — | |
| B5 | Gripper valve | **SMC SY3120‑5LZ‑M5** (5/2, 24 VDC, M5 ports) | Zoro / RS / Automation Distribution | $48–67 | 2 | One for the gripper, one spare (or as 3/2 for vacuum). |
| B6 | Vacuum valve | **SMC VQ110‑5L‑M5** (3/2, 24 VDC) or a second SY3120 plumbed 3‑port | SMC distributors | ~$50–70 | 1 | Nest rail vacuum on/off. |
| B7 | Precision regulator (gripper supply) | **SMC IR1000‑01** (0.005–0.2 MPa) — or **IR1010‑01** (0.01–0.4 MPa) for headroom | SMC distributors / Automation Distribution | ~$120–180 | 1 | Gripper runs at 0.15–0.2 MPa; force still comes from the flexure. |
| B8 | Vacuum switch (seat sensing) | **SMC ZSE30A‑01‑N‑L** (or ‑N01‑P for PNP, NPT) digital vacuum switch, 0 to −101 kPa | Next Day Automation / Automation Distribution | $60–85 | 1 | Threshold output → controller / DAQ digital input (via isolator). |
| B9 | Fittings & tubing | SMC **KQ2H04‑M5** (M5 → Ø4 one‑touch) ×10, **KQ2H04‑01S** ×4, **TU0425BU‑20** Ø4 PU tubing 20 m, **KQ2T04‑00A** tees ×4 | SMC distributors / McMaster | ~$80 | — | |
| B10 | 24 V supply + I/O | **Mean Well LRS‑50‑24**; if using the NI USB‑6363 for valves/sensors add a 4‑ch 24 V relay/isolator module (e.g., Phoenix Contact PLC‑RSC‑24DC/21 ×2 for valves, and 24 V→5 V optocoupler inputs for the M9 switches) | Digi‑Key / Mouser | ~$80 | 1 | Zaber and Thorlabs controllers also expose digital I/O usable for the valves. |
| B11 | Jaw force check | **American Weigh Scales GEMINI‑20** (0.001 g pocket scale) | Amazon | ~$25 | 1 | 0.3 N = 30 g on the pan; sets the flexure preload. |
| B12 | End‑face tweezers (manual stick loading) | **Ideal‑tek 2ACFR.SA.1** with **A2ACF** carbon‑fiber flat tips | TestEquity / TEquipment | ~$50 | 3 | The only approved hand tool near dies: flat ESD tips on the end faces. |
| B13 | Bench inspection camera | **Dino‑Lite AM7915MZT** (5 MP, 20–220×, EDOF) | Mega Depot / Microscope.com | **quote** (~$900–1,100) | 1 (optional) | Only if the existing microscope cannot be used at the bench rig. |
| B14 | Axis mounting | Thorlabs / Zaber adapter plates and a 90° bracket for the Z stage; 20 mm aluminum riser plate under the X axis so the gripper arm meets nest and stick heights | Thorlabs / McMaster + in‑house tapping | ~$250 | 1 | X axis runs along the exchange direction beside the nest, at bench level, outside both fiber corridors. |

## C. Not this month — price‑checked for Month 2 planning

| Item | Part | Price / lead | Use |
|---|---|---|---|
| Production transfer axes | Longer versions of A1 (X 300 mm, Y 300 mm, Z 60 mm) — same vendor and software as the prototype | quote (~$10–14 k) | Scale‑up of the Month‑1 Cartesian; a SCARA (Epson T3‑B, $7,495) is only an option with an offset gripper bar, since its vertical quill lands at the die end where the objective barrel is. |
| Film‑frame expander (if the vendor does not pre‑expand) | **Dynatex DXE 5** (≤ 150 mm) or **DXE 9** (≤ 200 mm); **Ultron UH130** semi‑automatic | quote (used manual units ~$2–5 k) | Sorting station. |
| UV cure box (if the vendor does not pre‑cure) | **Ultron UH102‑8** | quote (used units on eBay) | Sorting station. |
| Electric gripper (only if air proves impossible) | **Schunk EGP 25‑N‑N‑B** (3 mm/jaw, 20–40 N) | ~$1.5–2 k, 2–4 wk | Same flexure fingers; force still spring‑limited. |
| Machined PEEK sticks | Semitron ESd 480 or natural PEEK, CNC | quote | Replace SLA sticks after the design settles. |

---

## D. Should die sorting (tape → sticks) be outsourced to the dicing company?

**Recommendation: keep the pick itself in‑house; outsource only the tape preparation.**

What the local vendors actually offer (checked): American Precision Dicing (San Jose)
extracts from standard and UV tape into waffle packs, Gel‑Pak, vacuum‑release Gel‑Pak,
trays, film frames **and customer‑supplied custom containers**, with manual,
semi‑automatic and automated workflows, wafer‑map handling and inspection for chips and
sidewall fractures. American Dicing (NY) offers "manual pick and place for
pressure‑sensitive parts" and multiple needle/collet configurations. Neither publishes
what touches the die: the industry default is a **vacuum collet on the top surface**,
which is exactly what air‑clad waveguides forbid.

| | Outsource the pick | In‑house |
|---|---|---|
| Control of the one fragile step | Their operator, their tool, no way to see it | Your procedure, your jaws, inspect every 50 |
| Top‑surface risk | Default tooling is a top collet; edge‑only must be specified, tooled and audited | Zero by design (end‑face jaws / end‑face tweezers) |
| Iteration speed | Weeks per lot | Same day |
| Throughput needed | ~300 dies/batch | ~1 min/die manual ⇒ ~5 h per batch — not the bottleneck against hours‑per‑die test time |
| Cost | Manual sort typically a few $/die + NRE for custom carriers (quote) | Tech time; hardware already bought for the tester |
| Traceability | Wafer map → carrier map supplied | Wafer map → stick map, same |

So:

1. **Now (Month 1–2):** have the vendor dice on **UV‑release tape, UV‑cure, and expand
   the frame before shipping** (all standard services, cheap). Sort in‑house by hand:
   end‑face tweezers or the gripper on the manual XYZ, needle‑eject from below where
   needed, into the sticks. Five hours per 300‑die batch is acceptable and it is the
   same handling you do today, only safer.
2. **Month 2–3:** semi‑automate in‑house with the **same Cartesian axes and gripper** you already
   own, plus a manual ejector under the frame — the incremental cost is a used expander
   (or none if the vendor keeps expanding for you).
3. **In parallel, qualify APD as a backup:** give them two sticks, two pairs of end‑face
   tweezers and a one‑page procedure (end faces only, middle 3 mm, no top contact, no
   facet contact), and inspect the first 50 dies they return. If they pass, they become
   the overflow path; if not, you have lost nothing.
4. **Do not buy an automated sorting station** (expander + UV + custom head) until
   Month 3 volumes justify it. It is the least‑used machine in the whole system.

The reason to keep it in‑house is not cost. It is that the facet‑ and top‑surface rules
cannot be verified from outside, and the sticks and jaw geometry are still changing
weekly.

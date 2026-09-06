# Month‑1 Prototype Plan — Robotic Die Exchange on the Existing Tester

**Goal of the month:** prove, with real hardware and real dies, that a 10 × 6 × 0.5 mm
air‑clad TFLN die can be picked by its end faces, carried, set on the vision‑registered
nest, coupled by the existing auto‑alignment, and returned to its wafer-tray pocket — **hundreds of
times, without damage, with nobody touching the die**. End the month with an
unattended N‑die loop running on the current tester.

**What the month deliberately does not include:** the enclosure, a second tray position, the
production‑length axes, the X‑Y‑θ correction stage, automated tape pick, error‑recovery
software beyond "stop and alarm". Those are Month 2–3 and they all depend on Month 1's
answer.

---

## 1. What to prototype first, and why

The whole architecture (concept study §3, §6a) rests on one unproven claim: *a bare
photonic die can be gripped repeatedly by the middle of its non‑optical end faces and
set down on a backside chuck and pushed onto two end‑face stop pads, within ±0.3 mm / ±1°, with zero top‑surface or facet damage.*
If that is true, the rest is procurement and integration. If it is false, the design
redirects to the backside tongue and everything downstream changes. So:

1. **First:** the **gripper + nest + tray pocket** contact system, cycled by hand on a manual
   stage before any robot exists. This answers the damage question in week 2 regardless
   of robot lead time.
2. **Second:** the same gripper on the 3‑axis Cartesian doing **A → B → A**
   (tray → nest → tray) for hundreds of cycles with placement statistics from the
   camera.
3. **Third:** the nest at the real optical station, fibers interlocked, the existing
   `run_all_waveguides` measuring dies the robot exchanged. This is the demo.
4. **Not yet:** picking from dicing tape. It needs the expander, UV cure and ejector;
   in Month 1 we only gather the facts (tape type, street width) and do one manual
   needle‑eject experiment on a scrap wafer segment.

"Pick from point A to point B" is exactly the right first robot task — but A and B
must be **tray pocket and nest**, not the tape.

---

## 2. Parts that work, with lead times

The orderable list with exact part numbers, vendors, checked prices and the outsourcing decision is in **`bom_month1.md`**; this table is the summary.

Prices are indicative US list prices; lead times are typical for in‑stock items.
**Order the robot, gripper, and machined parts on day 1.**

| Item | Choice | Alternative | Approx. cost | Lead time |
|---|---|---|---|---|
| **Transfer axes** | Bench‑level 3‑axis Cartesian from motorized linear stages (Zaber X‑LSM, Thorlabs LTS150, or Suruga KXL06 on a DS102) — gripper arm enters under the objective along die X; no θ | Dobot MG400 for the bench‑only rig if lead time slips (not at the tester: articulated arm approaches from above/behind into the microscope volume) | ~$7–10 k | 2–4 weeks |
| **Production transfer axes (Month 2)** | Longer versions of the same Cartesian (X 300, Y 300, Z 60 mm), same software | SCARA only with an offset gripper bar (vertical quill lands where the objective barrel is) | ~$10–14 k | 3–6 weeks |
| **Gripper actuator** | SMC MHZ2‑6D pneumatic parallel gripper (4 mm total stroke) + precision regulator (SMC IR1000) + 5/2 valve (SY3120) + D‑M9 position sensors | Electric: Schunk EGP 25 or Zimmer GEP2010 (no air needed) | ~$300 pneumatic / ~$1.5–2 k electric | in stock / 2–4 weeks |
| **Jaw fingers** | Custom aluminum fingers with PEEK or Vespel SP‑1 inserts; stepped nose per Fig. 3; **one finger on a flexure or pivot with a 0.3 N spring stop** so grip force is set by the spring, not by air pressure | Bare PEEK fingers (no compliance) for the very first trial | ~$300–600 | 5–7 days (Protolabs/Xometry) or in‑house |
| **Nest** (chip stage) | Three parts (`cad/nest`): Ni‑plated **copper vacuum chuck** with a lapped 9 × 5 mm pad, 6 vacuum holes and a neck to a 15 × 15 mm TEC; **Semitron ESd 480 cage** with two +X stop pads (X and yaw by push‑to‑stop), an X guard and four corner Y guards; **6061 T‑riser** / heat sink with a 10 mm neck between the fiber holders, on the **die stage** (Suruga KXC04015‑C X stage over a Suruga RPG38 rotary, on a KB1X1 base) that steps the die from device to device | Cage without the TEC (blank copper block) for the first contact trials; the existing Suruga centre stage as the X stage if the KXC04015‑C is late | ~$600–1,000 + TEC | 1 week |
| **Vacuum** | Lab house vacuum or KNF N86 micro pump; SMC ZSE30A digital vacuum switch (seat sensing); 3/2 valve | — | ~$400 | in stock |
| **Wafer trays** (replace the sticks) | SLA print (Formlabs Rigid 10K or Protolabs Accura): 8 × 14 = 112 pockets (one 4″ wafer), cavity 12.0 × 6.8 mm with corner retention, 3.6 mm nose slots, ledges, lid; see `cad/tray/README.md` | Machined PEEK later | ~$120–250 per tray | 2–4 days |
| **I/O** | Stage‑controller digital I/O (Zaber X‑MCC / Thorlabs KDC101 triggers) or the existing NI USB‑6363 lines with a 24 V isolator module | Arduino | ~$80 | — |
| **Vision** | Existing overhead microscope camera + `ChipAlignmentController` template/edge methods for pose at the nest; a USB microscope for the bench rig | — | ~$100 | in stock |
| **Test dies** | (a) 50 diced silicon blanks 10 × 6 × 0.5 mm for cycling; (b) 20 diced LN blanks for contact realism; (c) 10–20 **scrap real TFLN dies** for damage tests | — | ~$300–800 (dicing service) | 1 week |
| **ESD** | Bench ionizer (Simco‑Ion Aerostat PC or similar), grounded fixtures, dissipative jaw inserts | — | ~$600–900 | in stock |
| **Manual rig** | Thorlabs manual XYZ stage (from lab stock) + adapter plate to carry the gripper over nest and tray | — | ~$0–300 | in stock |

**Not needed in Month 1:** X‑Y‑θ correction stage (the nest registers X and yaw mechanically; the die stage under it only steps devices and carries the once‑set RPG38 yaw trim),
film‑frame expander, UV box, enclosure, safety light curtain (bench run attended).

---

## 3. Week‑by‑week

Two people: one mechanical/integration (M), one software/test (S). Dates are working
days.

### Week 1 — decide, order, draw, and start the contact question

- **Day 1 (M+S):** order the linear stages, gripper, regulator/valves, vacuum switch, dicing of
  blank dies, ionizer. Ask the dicing vendor: tape type (UV‑release?), post‑dicing
  street width, film‑frame size, die thickness distribution.
- **Day 1–3 (M):** review and release the CAD package (`cad/`: one folder per component —
  gripper, nest, tray, station — parametric CadQuery models, STEP/STL per part, clearance
  checks; `python cad/build.py` regenerates everything). Send arms, tip blocks, bracket,
  chuck, cage and riser to machining; print the trays in‑house or send out.
- **Day 2–5 (M):** measure on the tester: objective working distance and barrel
  diameter, fiber‑holder envelope, safe retract distance, chuck mounting interface.
  Enter them into the 3‑D model's sliders; confirm the gripper bridge clears the
  objective or plan the retracting column now.
- **Day 2–5 (S):** transfer‑axes driver skeleton (`HandlingRobot` interface + a `CartesianXYZ`
  implementation over Zaber Motion Library / Kinesis / the existing `SurugaSeikiDS102`),
  digital I/O for valves/sensors, a `Interlock` class
  that refuses robot motion unless both fiber Z axes report the retracted position
  (reuse `DieTesterStage` queries).
- **Day 4–5 (M):** build the manual rig: gripper on the manual XYZ, nest and one tray
  on a common plate; dummy fingers (plain PEEK) if the real ones are not back yet.

### Week 2 — hand cycling: the damage and repeatability answer

- **Days 6–8 (M):** 100 hand cycles tray → nest → tray with silicon blanks; then 100
  with LN blanks. Tune the flexure preload to 0.2–0.5 N (measure with a gram gauge).
  Record: seat failures, drops, jaw marks under the microscope.
- **Days 8–10 (M+S):** camera repeatability at the nest: 30 placements, measure X/Y/θ
  with the existing template matching. Target: σ ≤ 0.1 mm, ≤ 0.3° before any
  correction.
- **Days 9–10 (S):** vision routine `measure_die_pose()` at the nest (facet edge + a
  fiducial or corner); pass/fail thresholds; logging to CSV.
- **Gate 1 (end of week 2):** zero top‑surface or facet damage on 20 LN blank cycles;
  seat success ≥ 95 %. *Fail → switch to the tongue fallback design immediately; add a
  centre channel to the tray pockets (one SLA reprint).*

### Week 3 — robot A → B → A

- **Days 11–12 (M):** stages arrive; assemble X–Z–arm beside the bench plate, Y under the
  wafer tray (or as third axis); mount gripper; teach nest and tray pocket coordinates using
  the camera (touch‑off with a dummy die).
- **Days 12–14 (S):** `exchange_die(from_pocket, to_nest)` primitive: approach height,
  descend, close, lift, carry, descend, open, rise; jaw sensors confirm die‑present;
  vacuum switch confirms seat; abort‑and‑alarm on any mismatch.
- **Days 13–15 (M+S):** 500 robot cycles on silicon blanks, 200 on LN blanks. Log
  drops, mis‑seats, pose scatter, cycle time. Inspect jaw inserts for wear at 0, 250,
  700 cycles (gauge the 0.10 mm top gap).
- **Gate 2:** ≥ 99 % successful cycles over the last 300; pose scatter inside Gate‑1
  targets; no jaw wear that changes the top gap by > 0.03 mm.

### Week 4 — at the optical station, with fibers, with real dies

- **Days 16–17 (M):** mount the nest at the tester's optical position (adapter to the
  current sample‑stage top, or directly to the table if the stage is removed for the
  trial). X axis at −X of the nest at bench level, outside the fiber corridors; the
  gripper arm's height under the objective verified against the measured working
  distance in the 3‑D model.
- **Days 17–18 (S):** integrate the interlock with the real fiber Z axes; `run_all_dies`
  loop = retract → exchange → pose measure → fiber offset from pose → existing first
  light → existing `run_all_waveguides` (a short device subset) → retract → return die.
- **Days 18–20 (M+S):** 5–10 **scrap real TFLN dies**, each cycled 5–10 times through
  the loop. Microscope inspection of facets, top surface and end faces before and after.
  Measure first‑light success after robot placement without human intervention.
- **Demo (day 20):** unattended loop over ≥ 5 dies, ≥ 2 passes each, no hands.
- **Parallel, low effort (M):** one manual tape experiment on a scrap wafer segment —
  needle from below through the tape, gripper from above — to size Month 2's ejector.

---

## 4. Pass criteria for the month

| Metric | Target |
|---|---|
| Pick/place success (robot, last 300 cycles) | ≥ 99 % |
| Placement scatter at nest, before correction | σ ≤ 0.1 mm X/Y, ≤ 0.3° θ |
| Visible damage on real dies after ≥ 5 cycles each | none (facets, top, end faces) |
| First light after robot placement | found by the existing routine with ≤ 1 retry |
| Exchange time (retract → next die seated and verified) | ≤ 60 s (Month‑1 robot) |
| Unattended demo | ≥ 5 dies × 2 passes, zero interventions |

---

## 5. Software work in this repository (Month 1)

| Module | Purpose |
|---|---|
| `src/handling/robot.py` | `HandlingRobot` abstract interface (move_to, grip, release, home, status); `CartesianXYZ` over Zaber Motion Library / Kinesis / `SurugaSeikiDS102`. |
| `src/handling/io.py` | Valves, vacuum switch, jaw sensors on NI‑DAQ digital lines. |
| `src/handling/interlock.py` | Fiber‑retracted and objective‑clear checks from `DieTesterStage`; a single `permit_robot_motion()` gate used by every robot call. |
| `src/handling/nest.py` | Nest vacuum on/off, seat detection, `measure_die_pose()` via existing camera + template matching. |
| `src/handling/campaign.py` | `run_all_dies`: tray map → per‑die state machine (stored → gripped → seated → measured → binned), CSV log, stop‑and‑alarm on any fault. Wraps the existing `WaveguideAlignmentController`. |
| `notebooks/handling_trials.ipynb` | Cycle tests and statistics for Gates 1–2. |

---

## 6. Risks and what we do about them this month

| Risk | Mitigation in Month 1 |
|---|---|
| Stage lead time slips | Hand cycling answers the damage question without any axes; Thorlabs LTS150 is the in‑stock fallback; a Dobot MG400 can run the bench‑only rig but never goes to the tester. |
| End‑face gripping marks or chips the dies | Flexure‑limited force, dissipative PEEK inserts, inspection every 50 cycles; **tongue fallback** already designed (tray pockets would get a centre channel). |
| Objective collides with gripper bridge | Measure WD in week 1; if < bridge + 3 mm, either shorten fingers (low bridge) or add a manual Z‑retract of the microscope column for the trial. |
| Vision pose is not repeatable enough | Fall back to two end‑face pins + retracting finger on the nest (concept study §3 option); fiber stages absorb Y. |
| Pneumatic force unstable at low pressure | Force comes from the spring, not the air; the actuator only opens/closes to stops. |
| Dies arrive on tape only, no loaded trays yet | Load a tray by hand with end‑face tweezers for Month 1 (that is today's workflow anyway); tape automation is Month 2. |

---

## 7. What Month 2 looks like if Month 1 passes

Order the longer production axes; add the second tray position and the enclosure; film‑frame expander +
UV box + ejector for the sorting station using the same gripper; X‑Y‑θ correction stage
under the nest; error‑recovery states in `campaign.py`; first lights‑out overnight run.

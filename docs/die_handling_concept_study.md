# System Redesign Study — Batch Edge-Coupled Testing of Hundreds of 10 × 6 mm Photonic Dies

**Status:** concept study for review (pre-CAD), rev. 2.2
**Scope:** ground-up redesign of the die-tester stage and handling system. The current
machine is architected around a single manually loaded die; this study treats the whole
stage system as open for redesign and asks what a machine looks like when the unit of
work is a **batch of hundreds of dies** and the target operating mode is **unattended
(lights-out) runs**, with operator involvement reduced to loading/unloading bulk
carriers and reviewing results.

Rev. 2 changes versus rev. 1: the study is reframed from "retrofit the existing
single-die stages" to a full system redesign; the carousel concept is removed; the
scaled concepts are re-derived for hundreds-of-dies batches; a recommended system
architecture is described at subsystem level. Rev. 2.1 adds the as-built observations
from the current bench (Appendix A, photo in `docs/images/current_setup.jpg`) and folds
their consequences — overhead microscope clearance, die-exchange approach direction,
fiber-arm envelope, enclosure and fiber management — into §3 and §6. Rev. 2.2 records
that the dies have **no top cladding** (exposed ridge waveguides): the nest becomes
backside-only with vision registration (§3), and §6a selects the pick-and-place system
(SCARA + backside vacuum tongue) and the slotted storage stick that goes with it.

Coordinate convention follows the brief: **X** = 10 mm die dimension, **Y** = 6 mm die
dimension (optical propagation; fibers approach along ±Y), **Z** = vertical, **θ** =
in-plane rotation.

---

## 1. Design intent: what "scaling to hundreds" actually changes

The single-die machine optimizes one coupling event. A batch machine optimizes a
*campaign*. That flips three assumptions baked into the current stage architecture:

1. **The bottleneck metric changes.** Per-die test time is
   `T_die = T_exchange + T_acquire + T_measure`. On this tester, `T_measure` for a full
   die (e.g. devices 2–66 in the current `run_all_waveguides` campaigns) is tens of
   minutes to hours; `T_exchange` is minutes. So shaving exchange seconds is not the
   prize. The prize is **removing the human from the loop between dies**, so the
   machine runs nights and weekends: a queue of 100+ dies with automatic exchange
   raises utilization from ~30 % (attended hours) toward ~90 %. For short screening
   tests (a few devices per die, `T_measure` ≈ 2–5 min), exchange and first-light time
   *do* dominate, so the design must also make exchange fast and acquisition
   deterministic. The architecture below serves both regimes.
2. **Precision should exist at exactly one point.** A carrier that replicates precision
   nests N times pays for precision N times and verifies it N times, and N is capped by
   stage travel. At hundreds scale, the winning pattern is the one used by every
   production die/wafer prober: **bulk storage is dumb and dense, transfer is coarse,
   and precision exists only at the single test site**, where one precision nest
   is made once, characterized once, and reused for every die forever.
3. **Unloading is as important as loading.** At hundreds of dies, "take the carrier off
   and sort the dies by hand" reintroduces the labor the system was meant to remove.
   The redesign must include **automatic binning** (pass/fail/grade back into output
   carriers) and per-die traceability (die ID ↔ results database).

Requirements R1–R8 from the brief (facet access, coarse-in/precise-out loading, common
optical line, independent registration, permitted contact zones, chip safety,
deterministic carrier interfaces, system-level throughput) all carry over unchanged and
are not repeated here. The presentation budget also carries over: the fixture chain
must deliver each die within roughly **±10–25 µm in Y/Z and ±0.05° in θ** of nominal at
the test site, so first light is a verification, not a search.

---

## 2. Functional architecture of the redesigned machine

Four decoupled subsystems, following the brief's storage / transfer / presentation
split, plus the optical engines:

```
   BULK STORAGE            TRANSFER              PRECISION            OPTICAL
   (hundreds)              (coarse)              PRESENTATION         ENGINES
┌────────────────┐    ┌────────────────┐    ┌────────────────────┐   ┌──────────────┐
│ input carriers │ →  │ robot / feeder │ →  │  ONE test nest at  │ ← │ 2× fiber     │
│ output bins    │ ←  │  ±0.3 mm class │ ←  │  the optical site  │   │ aligners +   │
│ (hotel/elev.)  │    │                │    │  (vision-regis-    │   │ vision       │
└────────────────┘    └────────────────┘    │  tered, §3)        │   └──────────────┘
                                            └────────────────────┘
```

- **Bulk storage** holds dies in dense carriers (slotted sticks / pallet cassettes, per
  concept) in an input **hotel** (stacked shelves with an
  elevator or a flat deck), plus output positions for binning. Capacity target:
  ≥ 200 dies resident.
- **Transfer** places the selected die into the test nest and returns it after test.
  It needs only ~±0.3 mm, ±1° placement accuracy — vision registration at the nest closes
  the rest. This is deliberately a cheap, robust motion system, not a precision stage.
- **Precision presentation** is one fixed nest (§3) on a small fine-correction stage.
  No long-travel precision axis exists anywhere in the machine: the die never travels
  far while registered, and nothing precise ever moves far.
- **Optical engines**: the two fiber aligners (each XYZ + fine alignment) and machine
  vision. Because the die always appears at the *same* nest within tens of µm, the
  fiber stages work around one fixed nominal point for the entire life of the machine —
  which is also what makes fast piezo-assisted alignment and pre-computed approach
  trajectories practical.

The reference hierarchy collapses to its shortest possible form:
`machine base → nest datums → die → waveguide` — no removable precision carrier in the
chain at all in the primary concept.

---

## 3. The precision test nest (single copy, heart of the machine)

**Governing constraint (rev. 2.2):** the dies carry **air-clad ridge waveguides — no
top oxide**. The top surface is untouchable everywhere, and the facet edges, where the
exposed waveguides terminate, are the most fragile lines on the part. The nest and
every handling step therefore contact the die **on its backside only**. In-plane
registration is done by **vision**, not by side datums: with a single fixed nest and a
calibrated overhead camera, a measured X/Y/θ is as good as a mechanical one and carries
zero facet risk. This supersedes the brief's facet-face datum sketch (§9 of the brief).

One nest, machined and lapped once, characterized exhaustively:

```
 Top view (die transparent)                        Side view (looking along X)

        ┌──────────────────────────────┐            fiber →              ← fiber
   Y=6  │ ═══════ vacuum rail ═══════  │ ← rail       ┃  die 0.3–0.7 mm    ┃
        │                              │   ~1 mm     ┌┸────────────────────┸┐
        │   ····· tongue channel ····· │ ← open      │         DIE          │
        │   (tongue enters along ±X)   │   gap       └─┬──┐  channel   ┌──┬─┘
        │                              │   ~2.5 mm     │▓▓│◄─tongue──►│▓▓│ rails
   Y=0  │ ═══════ vacuum rail ═══════  │ ← rail        │▓▓│           │▓▓│
        └──────────────────────────────┘             ──┴──┴───────────┴──┴── deck
        X=0                          X=10           recess ~1 mm inboard of each facet
```

- **Support and hold-down (Z, pitch, roll — mechanical):** two lapped **vacuum rails**
  along X on the backside, each ~10 mm long × ~0.75–1 mm wide, set **~1 mm inboard of
  each facet plane** (final recess from the measured fiber envelope, §8), standing
  ~1.5 mm proud of the nest deck. The rails define the die plane to microns, which is
  exactly the set of degrees of freedom vision measures poorly. The rail top is 0.5 mm
  below the waveguide plane and never in the fiber's horizontal path; the deck beyond
  the rails drops away so the ±Y corridors stay open for the fiber clamps. Vacuum level
  per rail doubles as **presence/seat sensing**.
- **Tongue channel:** the ~2.5 mm gap between the rails is an open channel along X in
  which the transfer tool's tongue (§6a) slides under the die center from either die
  end. Nothing about the nest blocks the ±X ends.
- **In-plane registration (X, Y, θ — by vision):** no side datums, no preload finger.
  After placement, the overhead camera measures facet-edge position and a fiducial (the
  existing OpenCV template/edge methods, which already resolve the die at the µm level
  in `ChipAlignmentController`), and the **X-Y-θ correction stage under the nest** moves
  the die to nominal before the fibers approach. Required range is only the tool's
  placement scatter — ±0.3 mm, ±1° — with sub-µm / sub-millidegree resolution (compact
  stepper or piezo-motor flexure stage). It also absorbs slow thermal drift. Nothing
  sample-side moves during a measurement.
- **Optional mechanical X/θ (not baseline):** if a hard in-plane reference is later
  wanted, two pins plus a retracting flexure finger acting on the **diced X-end faces**
  (non-optical, no waveguides) can be added without changing the rails or the tongue.
  The facet faces are never a datum surface in any variant.
- **Exchange sequence per die:** fibers retract (interlocked) → tongue slides in along X
  under the outgoing die, vacuum on, lifts 0.3–0.5 mm, withdraws → returns with the
  incoming die, lowers it onto the rails, vacuum handshake (tongue off, rails on),
  withdraws → camera measures pose → correction stage zeroes X/Y/θ → fibers approach.
- **No structure above the die top surface** in the central 8 mm of X, no structure at
  waveguide height anywhere in the ±Y fiber approach cones, and a software/hardware
  interlocked fiber-retract corridor before any nest actuation (carries over R1/R5/R6
  and brief §15/§22 unchanged).
- **Envelope as it exists today (Appendix A):** the fibers arrive on long, thin
  cantilevered holder arms that pass through slots in the ±Y walls of the present
  enclosure, and the die sits under a high-magnification objective a short working
  distance above it. Three consequences for the nest: (i) the ±Y corridors must be
  sized for the *arm*, not the fiber — the current arms are tens of mm long with a
  V-groove clamp near the tip, so the pedestal recess and any nest wall on the ±Y sides
  are set by clamp height/width, not by the 125 µm fiber; (ii) the only free approach
  directions to the die are **±X** (horizontally, under the objective) and **from
  above** (only if the objective retracts), which fixes the die-exchange geometry in §6;
  (iii) the nest must be low and stiff — the present chuck rides a tall stage tower,
  and a low pedestal directly on the base both shortens the structural loop to the
  fiber stages and frees vertical room for the exchange mechanism.

Everything else in the machine can be ordinary industrial automation because this one
component absorbs the precision problem.

---

## 4. System concepts at hundreds-of-dies scale

Three full-system concepts plus one deliberate inversion. All share the §3 nest; they
differ in storage format and transfer mechanism — which is exactly where the brief says
the freedom is.

### S1 — Stick hotel + SCARA pick-and-place into the fixed nest  *(recommended)*

**Storage:** dies sit in **slotted carrier sticks** (§6a) whose pockets support the die
on its backside only and leave a channel under the center open at both ends. A hotel
deck holds 6–10 sticks (input, pass, fail, regrade) — ≥ 100–200 dies resident. Sticks
are loaded at a bench, ideally by the dicing vendor.

**Transfer:** a 4-axis **SCARA** (~400–600 mm reach, ±0.02 mm class, integrated
controller) carrying a thin **backside vacuum tongue** that slides under the die along
X, lifts it 0.3–0.5 mm off the pocket or nest rails, and carries it. No top-surface or
facet contact at any point (§6a). Placement scatter of a few tenths of a mm is closed by
vision registration at the nest, not by a mechanical funnel.

**Sequence per die:** fibers retract → tongue removes die *i* from the nest → returns
it to its bin stick → picks die *i+1* → places it on the nest rails → vacuum handshake →
overhead camera measures X/Y/θ → correction stage zeroes the pose → fibers approach
along the pre-computed trajectory → first light as verification → measure. In the
screening regime a second tongue pre-stages die *i+1* so the swap itself is ~5 s.

**Why it wins at this scale:**
- Operator interaction = swap packs and press start: **one interaction per ~100–200
  dies**, and runs continue unattended overnight.
- Automatic binning and per-die traceability (pack + pocket ID ↔ results) fall out of
  the architecture for free.
- Exactly one precision component; adding capacity = adding shelf positions, which are
  free.
- Failure containment: a mis-seated die is detected by vacuum/vision *before* fibers
  approach; the die is returned to a reject position and the run continues — no human
  needed for the common faults.

**Main risks:** it is a real machine build (robot, hotel, tongue tooling, guarding,
ESD/ionization, error-recovery software); every die is robot-handled twice — mitigated
by backside-only contact, low approach velocities, and the fact that robot handling
replaces *tweezers*, historically the worst offender; custom sticks must be adopted
upstream; total cost dominated by the robot cell (order €30–60 k in COTS hardware
before integration labor).

### S2 — Pallet cassette line (SMT-feeder pattern)

**Storage:** each die is mounted **once**, at an offline bench station with its own
self-registering fixture, onto a reusable ~16 × 16 mm hardened **pallet** carrying
ground datum features and a clip/latching hold. Pallets stack ~25–50 high in gravity
**cassettes**; several cassettes = hundreds of dies queued.

**Transfer:** a simple elevator + pusher (walking-beam class mechanics, no robot)
advances one pallet at a time into a **kinematic dock** at the optical site: 3-groove
mount + clamp, ~1–2 µm repeatable. Tested pallets are pushed on into output cassettes
(binning by gate = two output cassettes minimum).

**Strengths:** bare-die handling happens exactly once per die, at a bench with ideal
ergonomics and lighting — the lowest facet-risk concept; the tester-side automation
handles only robust identical steel objects, so it is *simpler and more reliable* than
a bare-die robot; pallet serial numbers give bulletproof traceability; scaling is
linear (more cassettes).

**Weaknesses:** the per-die pallet-mounting labor is real (~30–60 s/die at the bench) —
it relocates rather than removes the per-die human touch, unless a second loading
automat is built later; a pallet fleet of 300+ units is a recurring cost (tens of € per
pallet at quantity) and a management task (cleaning, inspection); one extra tolerance
interface (die→pallet→dock) versus S1's die→nest.

**Best fit:** if §8 measurements or early trials show that *any* robot handling of bare
dies is unacceptable for facet yield, S2 is the scaled architecture of choice.

### S3 — Batch comb plates on a long-travel transport  *(semi-automated fallback)*

The linear self-registering magazine of the brief, scaled as far as it goes: a
**300–400 mm travel transport axis** carrying 2–4 removable monolithic comb plates of
12–15 nests each (~25–60 dies per load), each comb kinematically mounted, loaded
offline at a bench station, both ±Y corridors open along the full row.

This is the least machine-building of the three: no robot, no feeder, ~1/5 the
integration effort of S1. But it fundamentally cannot reach the campaign goal alone:
precision is replicated ~50× instead of 1×; capacity is capped by transport travel;
there is no automatic binning; and an operator event is still needed every ~50 dies, so
overnight runs end when the combs do. **Role in the redesign:** the engineering-lot /
bring-up mode and the risk-reduction stepping stone — the nest design, vision verify,
fiber choreography, and orchestration software developed for S3 transfer 1:1 to S1
(same nest, same software, the robot simply replaces the transport axis). Not the end
state.

### S4 — Stationary die field + translating optical head  *(evaluated, not selected)*

The inversion the brief asks about, evaluated clean-sheet rather than against legacy
software: dies rest in large fixed comb fields; both fiber aligners + cameras ride a
long gantry. Even with a from-scratch design this loses on physics, not on software
legacy: the moving payload is two opposed fiber stacks whose *mutual* alignment must
survive translation (the hardest stiffness/metrology problem available), optical fibers
and cabling live in drag chains (polarization and loss instability injected directly
into the measurand), and the precision problem is replicated across every nest in the
field *and* the gantry. It becomes attractive only if dies must sit on infrastructure
that cannot move (temperature-controlled chuck, RF probe cards on every die). Recorded
with that trigger condition; otherwise rejected.

---

## 5. Comparison at hundreds-of-dies scale

Ratings: ● strong / ◐ adequate / ○ weak.

| Criterion | S1 hotel + SCARA + 1 nest | S2 pallet cassette line | S3 batch combs | S4 moving head |
|---|---|---|---|---|
| Dies resident per operator interaction | 100–200 ● | 100–400 (cassettes) ● | 25–60 ◐ | 25–60 ◐ |
| Operator minutes per 100 dies | ~5 (stick swaps) ● | ~60–100 (pallet mounting) ○ | ~30 (comb loading) ◐ | ~30 ◐ |
| Unattended (lights-out) capability | full ● | full ● | until combs exhausted ◐ | until field exhausted ◐ |
| Number of precision feature sets | 1 ● | 1 dock + pallet fleet ◐ | ~50 nests ○ | ~200 nests + gantry ○ |
| Die-to-die Y/θ consistency | best possible (one nest) ● | dock-limited ● | comb machining ◐ | comb + gantry metrology ○ |
| Automatic binning / traceability | native ● | native (2+ cassettes, serials) ● | none ○ | none ○ |
| Bare-die handling events per die | 2 robot touches ◐ | 1 bench mount ● | 1 bench load ● | 1 bench load ● |
| Facet-risk profile | robot near facets, gated ◐ | lowest ● | low ● | fibers translating over dies ○ |
| Exchange time (short-test regime) | ~15–25 s, pipelined ● | ~10–20 s ● | ~10–20 s ● | ~20–40 s ◐ |
| Error containment / recovery | auto-reject, run continues ● | auto-gate ● | skip nest, human sorts later ◐ | ○ |
| Mechanism reliability class | robot cell ◐ | pusher/elevator, simplest ● | single axis, simplest ● | long gantry + drag chains ○ |
| Integration effort / relative cost | ~5× (baseline = S3) ○ | ~3× ◐ | 1× ● | ~8× ○ |
| Incremental path from S3 | direct (same nest, same s/w) ● | dock ≠ nest, partial ◐ | — | none ○ |
| Scalability beyond hundreds | add shelves ● | add cassettes ● | capped by travel ○ | capped by field ○ |

---

## 6. Recommended system: S1, reached through S3's nest

**End state (the machine to design toward):**

- **Base:** granite or polymer-granite machine base; thermal enclosure; ionized-air ESD
  environment; light curtain / interlocked doors around the robot volume.
- **Optical site:** the §3 nest on its small X-Y-θ correction stage, fixed near the
  center of the base. Overhead verify camera (die pose, existing OpenCV template/edge
  methods carry over); optional side cameras on the fiber aligners for gap/facet view.
- **Fiber aligners (redesigned, both sides):** stacked coarse XYZ (the DS102-class
  stepper stacks are adequate here and can be retained *as components*) + **piezo
  flexure XYZ fine stages** (~100 µm range, nm resolution) for fast raster/gradient
  alignment. With the die always at the same nominal point, approach trajectories are
  pre-computed and first light typically completes in seconds. Fibers park in a
  retracted, interlocked position during every nest/robot action.
- **Vision column (redesigned around the exchange):** the overhead objective stays —
  it is the verify camera — but it must **clear the exchange volume**. Two options,
  chosen by the objective's working distance and the end-effector height: (a) put the
  microscope column on a motorized Z lift (or a pneumatic two-position retract) that
  raises it 50–100 mm during every exchange; (b) keep it fixed and use a *long*
  working-distance objective (≥ 30 mm) with a low-profile end-effector that enters
  horizontally along ±X beneath it. Option (b) removes a moving element from the
  optical path and is preferred if the magnification budget allows; (a) is the
  fallback. With the backside tongue (§6a) the tool itself is *below* the die top
  surface during the exchange, so only the tool holder — outboard of the die's X end —
  must clear the objective barrel; a fixed column is very likely sufficient. In both
  cases the objective-to-die gap is a hard interlock input for the robot, exactly like
  fiber retract.
- **Transfer:** a small 4-axis **SCARA** on its own pedestal beside the optical table,
  carrying a **backside vacuum tongue** that slides under the die along ±X — the only
  direction not occupied by fiber arms (±Y) or the objective (+Z) — and lifts it off
  its rails. Selection rationale, tool geometry and alternatives are in §6a. The fiber
  arms park retracted and the objective gap is confirmed before the tongue may enter;
  all states are interlocked.
- **Storage:** custom **slotted carrier sticks/trays** (§6a) whose pockets present the
  same backside rail-pair-and-channel geometry as the nest, so the tongue picks from
  storage and places into the nest with one motion primitive. 6–10 sticks on a hotel
  deck with stick-ID reading (DataMatrix); designated output sticks for binning.
  Located to one side of the optical site along **X**, so the robot's transit path
  never crosses the fiber corridors. Standard waffle packs are not used on the machine
  (closed pocket floors force a top pick).
- **Enclosure and dressing (replaces the present small box):** the current 3D-printed
  enclosure with glass top and acrylic front shows the need for still air and dust
  control already exists; in the redesign it grows into the full cell — one enclosure
  around nest, fiber aligners, robot and hotel, with a laminar top-down flow or at
  least a still-air lid, interlocked doors, ionized air, and windows placed for the
  overhead camera and operator view. Fiber pigtails and stage cables, which today lie
  loose on the breadboard, are routed in captive guides with strain relief on the
  aligner frames: a robot may never share a volume with an unmanaged fiber. Fiber
  aligners mount to the same rigid base plate as the nest rather than to the optical
  table individually, closing the metrology loop through one stiff part.
- **Software (this repo evolves into the orchestrator):** a campaign layer above the
  existing per-die stack — die queue + results database keyed by pack/pocket ID; state
  machine per die (stored → picked → verified → nested → measured → binned) with
  explicit recovery transitions; the existing `FirstLightController` /
  `WaveguideAlignmentController` become the "measure" state's engine; `SoftwareFence`
  logic generalizes into the fiber/robot interlock. The current codebase's
  per-waveguide automation is the one part of the present system that transfers to the
  redesign essentially intact.

### 6a. Pick-and-place system and die pickup

**How a die is picked up.** Because the top surface carries exposed waveguides and the
facet edges are fragile, the die is lifted **from below, at its backside center**, by a
thin vacuum **tongue**:

- Tongue ≈ 2.5 mm wide × ≤ 0.8 mm thick × ~15 mm long, vacuum ports on its upper face,
  dissipative material (conductive PEEK or hard-anodized Al with a conductive coating —
  LN is pyroelectric and charges with every temperature swing; the cell is ionized).
- It slides horizontally **along X** into the channel between the two backside rails
  (nest or storage pocket), ~0.3 mm below the die; vacuum on; lifts 0.3–0.5 mm so the
  die leaves the rails; withdraws along X; travels; reverses the sequence at the
  destination. A vacuum switch on the tongue line confirms pick and detects loss.
- Holding force: ~12 mm² of ports at −60 kPa ≈ 0.7 N against a die weight of ~1.4 mN
  (10 × 6 × 0.5 mm LN). Backside friction holds it laterally at any sane acceleration.
  The die overhangs the tongue by ~1.75 mm per side in Y and ~0 in X — negligible bow.
- Nothing ever contacts the top surface, the facet faces, or the facet edges. The only
  contact patches in the die's entire life on the machine are the backside center
  (tongue) and the two backside rail strips (nest, storage).

**Storage carrier: slotted sticks.** Standard waffle packs have closed pocket floors and
force a top pick, so they are replaced by a machined (PEEK/Delrin) or SLA-printed
carrier whose pockets have the **same geometry as the nest**: two ledges under the die's
facet-edge strips (backside only), a floor-level **channel along X** under the center,
a **tunnel through both X-end pocket walls** so the tongue enters from the side, low
retention walls on all four sides, generous lead-in chamfers, and a lid for transport.
Pockets are arranged in a row along **Y** so every channel opens to the stick's long
edges (a 12-pocket stick ≈ 16 × 105 mm); sticks sit on the hotel deck with ~20 mm gaps
for the tool holder. A 2-D tray variant with an access well at each pocket's X end is
possible if deck area becomes the constraint. Operators load sticks at a bench from
dicing tape or Gel-Pak, gripping the **non-optical X-end faces** with tweezers as they
do today — the one remaining manual touch per die, performed far from the tester.
Preferably the dicing vendor delivers directly into these sticks.

**Robot type: 4-axis SCARA.** The task is a horizontal slide-in along one axis at a
fixed height, a few-tenths-of-a-mm vertical lift, and a carry of 300–450 mm — exactly a
SCARA's native motion — at ±0.3 mm / ±1° placement accuracy, with a payload in grams.

| Option | Verdict |
|---|---|
| **4-axis SCARA** (Epson T3/T6, Yamaha, Denso class; ~400–600 mm reach, ±0.02 mm, integrated controller, Ethernet API) | **Selected.** Horizontal approach is native; compact pedestal footprint beside the table; integrated safety/controller; J4 (θ) corrects 180°-rotated dies detected by the verify camera. A Dobot MG400-class unit (~±0.05 mm, 440 mm reach, Python SDK) is an acceptable prototyping stand-in with identical geometry. |
| Overhead Cartesian gantry | Rejected: the bridge must live above the cell, exactly where the microscope column and the two ~200 mm fiber stacks are; forces a tall enclosure and constant clearance conflicts; custom controls and safety. Reconsider only if the hotel grows far beyond 10 sticks. |
| 6-axis articulated arm (Meca500, UR3e) | Rejected: unused DOF, slower, costlier, harder safety case; no angled approaches are needed. |
| Dedicated X-Z shuttle + indexing deck | Cheapest and stiffest, but fully custom and it freezes the hotel geometry. Only if the hotel stays at 1–2 sticks. |

**Pickup alternatives considered and ranked below the tongue:**

| Method | Assessment |
|---|---|
| **Edge gripper on the X-end faces** (robotic tweezers, PEEK/Vespel jaws, 0.2–0.5 N) | Viable second choice — no top contact. But needs ~1 mm jaw clearance to pocket walls, must close symmetrically without riding onto the top edge of a 0.5 mm face, and conflicts with any nest features on the same faces. |
| **Bernoulli non-contact top gripper** | Works with standard waffle packs and never touches the die, but blows air across exposed waveguides and facet edges (particle transport), has weak lateral constraint (needs end-face stops), and the body overhangs the facets. Fallback only if custom carriers are impossible. |
| Top vacuum pads in the 1-mm end zones | **Rejected.** A 0.6 mm pad in a 1 mm strip needs ±0.2 mm die-relative placement while pocket slop alone is ±0.25 mm; one miss puts a pad on a waveguide. |
| Top-and-bottom sandwich clamp at the end zones | **Rejected.** Still touches the top surface and adds nothing over backside vacuum. |
| Electrostatic top chuck | Rejected: unpredictable on pyroelectric LN. |

**Layout and operation.** Robot pedestal at −X of the nest, off the optical table (or on
a bridge decoupled from the base plate), so its motion never enters the metrology loop;
sticks arrayed on the −X side within the arm's arc, flanking the base, outside both
fiber corridors. The robot moves **only while fibers are retracted** and is parked
during every measurement, so pipelining is not needed in the long-test regime; in the
screening regime the incoming die is pre-staged on a second tongue before the fibers
retract, making the swap itself ~5 s and the full exchange 15–25 s including vision
registration and correction. Operator role: remove stick lids, load the hotel, press
start.

**Why via S3:** the single highest-risk item is now: does backside-only handling with
vision registration deliver ±10–25 µm / ±0.05° at the fibers over hundreds of cycles
with **zero** top-surface or facet damage? That is answered fastest and cheapest by
building **one rail-pair nest, one tongue on a hand-positioned or cheap stage, and one
stick** (S3 hardware minimum), cycling dies through a few hundred times, and inspecting.
Everything built for that test (nest, tongue, stick geometry, vision registration,
fiber choreography, orchestration software) is carried unchanged into S1; the SCARA and
hotel are then a procurement-and-integration project around a proven core, not a
gamble. If the trials instead show any bare-die robot handling is untenable, the same
data redirects the build to S2 with minimal loss.

**Throughput picture (full-characterization regime, `T_measure` ≈ 60 min/die):**
utilization is the whole game — S1 at ~90 % utilization tests ~21 dies/day vs ~7/day
for any attended single-die flow; 300 dies ≈ 2 weeks unattended vs ~6+ weeks attended.
**(Screening regime, `T_measure` ≈ 3 min/die):** with pipelined exchange (~20 s) and
verification-grade first light (~10–20 s), S1 sustains ~12–15 dies/hour, ~300 dies in
one lights-out day.

---

## 7. What is retained from the current machine, and what is not

| Current element | Disposition in redesign |
|---|---|
| Per-waveguide automation software (first light, raster/Z-scan, full-chip stepping, transfer-function capture) | **Retained** — becomes the measurement engine inside the campaign state machine. |
| Fiber coarse XYZ stepper stacks (DS102) | **Retained as components** of the new fiber aligners, augmented with piezo fine stages. |
| Camera + OpenCV pose/verify methods | **Retained**, re-pointed at the fixed nest. |
| Center sample stage (X + θ, single-die chuck) | **Not retained** as the sample platform. Its X axis has no role once transfer is robotic; a compact X-Y-θ correction stage under the nest replaces the θ function with shorter range and higher stiffness. |
| Manual die placement / tweezer workflow | **Removed from the tester.** The one remaining manual touch per die is loading storage sticks at a bench, gripping the non-optical end faces. |
| Open-frame bench layout | **Replaced** by an enclosed, interlocked, ESD-managed cell (required once a robot moves near fibers). |

---

## 8. Measurements and decisions required before detailed design

1. **Fiber/chuck 3-D envelope** (tip-to-first-bulky-feature, holder W×H, safe retract,
   full swept volume during alignment) → rail recess, robot keep-out, parking
   positions.
2. **Die contact constraints — partly settled:** no top-side contact anywhere (air-clad
   waveguides, rev. 2.2) and no facet contact. Still to confirm: backside condition
   (bare substrate vs metallization/handle wafer, allowed vacuum stress, contamination
   class) → rail/tongue materials and vacuum level.
3. **Die dimensional data** (thickness ± tol — this sets the tongue's 0.3 mm working
   clearance under the die and the rail height; dicing size and squareness tol; facet
   edge condition as-received) → pocket and channel dimensions, vision-registration
   range, θ budget check.
4. **Nest seating trials** (the S3-minimum prototype): repeatability over ≥ 300
   seatings, facet-edge inspection every 50, vacuum-seat detection ROC → the go/no-go
   data for S1 vs S2.
5. **First-light capture range in practice** (from existing logs: raster window sizes
   that converge reliably) → confirms the ±10–25 µm / ±0.05° presentation budget.
6. **Carrier decision:** confirm the slotted-stick format with the dicing vendor
   (direct delivery into sticks) or size the bench transfer step from the incoming
   format (waffle pack / Gel-Pak tack level) → hotel deck design and operator time.
9. **Vision registration accuracy at the nest:** camera µm/pixel (already measured by
   the `SoftwareFence` calibration), facet-edge and fiducial detection repeatability →
   confirms X/Y/θ can be zeroed to inside the presentation budget without side datums.
10. **Objective working distance and barrel diameter** → whether the fixed vision column
   clears the tongue holder or must retract.
7. **Test-plan regimes:** expected mix of full characterization vs screening per
   campaign → pipelining priority and hotel sizing.
8. **Throughput accounting on the current tester** (operator minutes and interventions
   per die today) → the baseline the business case is measured against.

## 9. Risks and open questions

- Vision-only in-plane registration: facet-edge detection must be robust to facet
  quality variation and illumination; mechanical X/θ on the end faces is the documented
  add-on if it is not (§3).
- Tongue working clearance (~0.3 mm under the die) versus die-thickness tolerance and
  pocket/rail height tolerances across sticks from different batches.
- Rail recess (~1 mm inboard of the facet) versus the true fiber/clamp envelope — a
  fiber crash now meets a rail instead of empty space; the software fence and rail
  material (no harder than the fiber ferrule) must reflect that.
- Custom stick adoption: if dies keep arriving in waffle packs or Gel-Pak, the bench
  transfer step remains and its facet risk must be managed with tooling (end-face
  tweezers, chamfered pockets).
- Correction-stage motion per die adds ~5–10 s and a moving element under the nest;
  its stiffness and settling must be characterized so nothing sample-side drifts
  during a measurement.
- Error-recovery completeness: the value of S1 is unattended running; every credible
  fault (mis-pick, double die, cocked seat, no first light, power loss mid-run) needs a
  scripted, tested recovery path — this is software scope, and it is large.
- If any future measurement requires temperature control at the die, revisit S4's
  trigger condition before committing the nest design.

---

## Appendix A — The current bench as built, and what it implies

Reference photo: `docs/images/current_setup.jpg`.

![Current manual die-tester setup](images/current_setup.jpg)

| Observation | Design consequence |
|---|---|
| Chip stage (X + θ stack) stands on a tall tower inside a small 3D-printed enclosure with a glass top window and a clear acrylic front panel; a ring illuminator sits inside. | Still-air/dust control is an existing requirement, currently met at die scale. The redesign scales the enclosure to the whole cell (§6) rather than boxing the nest. The tall tower goes: the nest sits low on the common base plate for stiffness and to free vertical room for the exchange tool. |
| High-magnification objective on a vertical microscope column, pointing down through the top window, a short working distance above the die. | The overhead camera is the natural verify camera and is retained, but it occupies the +Z approach. Die exchange must enter along ±X beneath it, or the column must retract; objective-to-die gap becomes an interlock (§6). Working distance of the current objective is a required measurement (§8). |
| Two Suruga Seiki motorized XYZ stacks (Oriental Motor steppers, manual micrometer verniers) mounted outside the enclosure; fibers on long, thin cantilevered holder arms with V-groove clamps near the tip, passing through slots in the ±Y enclosure walls. | The arm, not the fiber, is the keep-out body: nest pedestal recess and any ±Y structure are sized from arm/clamp dimensions and the alignment sweep. The slotted walls also show today's approach corridor is already tightly constrained — in the redesign the ±Y corridors stay fully open inside one enclosure. The stacks are retained as coarse stages under added piezo fine stages; the arms should be shortened and stiffened once the enclosure no longer forces a long reach. |
| Fiber pigtails (FC/APC) and stage cables lying loose on the breadboard; blue/orange patch cables overhead; 80/20 framing close around the table. | Fiber and cable management becomes a design deliverable (captive routing, strain relief, no fiber in any robot volume). The redesigned cell should be a self-contained module on its own base plate (~600 × 500 mm footprint class) so it can be placed and, if needed, relocated as one unit within the existing frame. |
| Everything is bolted individually to the optical table (stages, tower, microscope). | Replace with a single stiff base plate carrying nest, both fiber aligners and the vision column, so thermal and structural drift is common-mode across the metrology loop; the table then only isolates vibration. |

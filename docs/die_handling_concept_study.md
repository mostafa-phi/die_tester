# System Redesign Study — Batch Edge-Coupled Testing of Hundreds of 10 × 6 mm Photonic Dies

**Status:** concept study for review (pre-CAD), rev. 2.1
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
fiber-arm envelope, enclosure and fiber management — into §3 and §6.

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
   and precision exists only at the single test site**, where one self-registering nest
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
│ (hotel/elev.)  │    │                │    │  (self-register-   │   │ vision       │
└────────────────┘    └────────────────┘    │  ing, §3)          │   └──────────────┘
                                            └────────────────────┘
```

- **Bulk storage** holds dies in standard dense carriers (waffle packs / Gel-Pak /
  pallet cassettes, per concept) in an input **hotel** (stacked shelves with an
  elevator or a flat deck), plus output positions for binning. Capacity target:
  ≥ 200 dies resident.
- **Transfer** places the selected die into the test nest and returns it after test.
  It needs only ~±0.3 mm, ±1° placement accuracy — the nest's self-registration closes
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

One nest, machined and lapped once, characterized exhaustively:

```
 Top view                                        Side view (through Y)

   preload finger (flexure, 0.1–0.3 N)             fiber →          ← fiber
        ↓ pushes −Y and −X (angled)                   │ die 0.3–0.7 mm │
   ┌────────────────────────────┐                  ┌──┴────────────────┴──┐
   │ ▷ chamfered capture funnel │                  │         DIE          │
   ●─┬──────────────────────┬──●  ← 1-mm zones     └───┬──────────────┬───┘
   │ │      DIE  10 × 6     │  │                       │ vacuum       │
   ● │                      │  ▷ ← X datum             │ pedestal     │
   ↑ └──────────────────────┘  │                       │ 10 × ~3 mm,  │
   two Y/θ datums on the       │                       │ ≥1.5–2 mm    │
   facet-side face, inside     │                       │ recessed     │
   the 1-mm X-end zones only   │                       │ from facets  │
```

- **Y/θ datums:** two polished sapphire/ruby contacts on the facet-side face at Y = 0,
  strictly inside the two 1-mm X-end zones (per brief §9). This makes the facet plane
  itself the Y reference: constant fiber working distance regardless of die-width
  tolerance, and θ tied to the lithographically defined facet. **Fallback** if
  prototype testing shows facet-edge wear: datums on the diced X = 0 end face (zero
  facet contact; θ then depends on dicing squareness — verify against the ±0.05°
  budget).
- **X datum:** one contact on the X = 10 mm end face; a single angled flexure finger
  preloads the die onto all three contacts at once.
- **Z / hold-down:** backside vacuum pedestal 10 × ~3 mm, lapped, recessed ≥ 1.5–2 mm
  in Y from each facet (final value from the measured fiber-chuck envelope, §8).
  Vacuum level doubles as **seat/presence sensing**; a differential threshold detects a
  cocked die before fibers approach.
- **Capture funnel:** ≥ ±0.5–1 mm, ±2–3° acceptance so the coarse transfer subsystem
  needs no precision. Sequence per die: *place loosely → preload finger sweeps die onto
  datums → vacuum confirms → fibers approach.* Release is the reverse, with fibers
  retracted and interlocked.
- **Fine correction under the nest:** the nest sits on a compact motorized X-Y-θ
  correction stage (±1 mm, ±1°, sub-µm/sub-millidegree resolution — e.g. stepper or
  piezo-motor flexure stage). Its only job is to zero out the small, *slowly drifting*
  residual between nest datums and the optical line (thermal drift, re-referencing
  after service). Per-die residuals within the budget are absorbed by the fiber
  aligners; nothing sample-side moves during a measurement.
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

### S1 — Carrier hotel + gantry pick-and-place into the fixed nest  *(recommended)*

**Storage:** dies remain in their **shipping waffle packs** (or Gel-Pak trays with an
eject-assist pick head). A hotel deck holds 4–10 open carriers (input, pass, fail,
regrade) — ≥ 200 dies resident with zero per-die pre-processing. Optionally an elevator
hotel for compactness.

**Transfer:** a Cartesian **gantry robot** (2-axis overhead + Z, ~300–500 mm reach,
±0.05–0.1 mm repeatability — ordinary COTS linear-motor or ball-screw axes) with a
compliant vacuum end-effector. Pickup contacts the top surface **only in the two 1-mm
X-end zones** (twin-pad tip) or the full backside via a pocket-underside eject pin,
depending on the permitted-contact answer (§8). An up-looking camera under the gantry
path measures die pose on the tip in flight (±0.02 mm class), so placement into the
nest funnel is always well inside the capture range regardless of pocket slop.

**Sequence per die:** gantry picks die *i+1* from the input pack while die *i* is being
measured (pipelining hides all robot time in the long-test regime) → fibers retract →
nest releases die *i* → gantry swaps dies (dual-tip end-effector makes this one visit)
→ nest self-registers → vision verify (overhead camera at the nest: X/Y/θ residual
against die fiducials/facet edge) → fibers approach along pre-computed trajectory →
first light as verification → measure → binned return.

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

**Main risks:** it is a real machine build (gantry, hotel, end-effector, guarding,
ESD/ionization, error-recovery software); every die is robot-handled twice near its
facets — mitigated by the end-zone-only tip, low approach velocities, and the fact that
robot handling replaces *tweezers*, historically the worst offender; total cost
dominated by the gantry cell (order €40–80 k in COTS hardware before integration
labor).

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

| Criterion | S1 hotel + gantry + 1 nest | S2 pallet cassette line | S3 batch combs | S4 moving head |
|---|---|---|---|---|
| Dies resident per operator interaction | 100–400 ● | 100–400 (cassettes) ● | 25–60 ◐ | 25–60 ◐ |
| Operator minutes per 100 dies | ~5 (pack swaps) ● | ~60–100 (pallet mounting) ○ | ~30 (comb loading) ◐ | ~30 ◐ |
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
  environment; light curtain / interlocked doors around the gantry volume.
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
  fallback. In both cases the objective-to-die gap is a hard interlock input for the
  robot, exactly like fiber retract.
- **Transfer:** overhead Cartesian gantry (X ~400–500 mm, Y ~300 mm, Z ~100 mm,
  ±0.05–0.1 mm) with a **side-entering end-effector**: the tool arrives at the nest
  horizontally **along ±X** — the only direction not occupied by fiber arms (±Y) or the
  objective (+Z) — as a low fork whose twin vacuum pads contact the two 1-mm X-end
  zones from above with a final short vertical stroke. Dual tool (swap in one visit),
  up-looking pose camera on the transit path, force-limited placement. The fiber arms
  park retracted and the objective clears before the fork may enter; all three states
  are interlocked.
- **Storage:** flat hotel deck for 6–10 open waffle packs / Gel-Paks with pack-ID
  reading (barcode/DataMatrix); designated output packs for binning. Located to one
  side of the optical site along **X**, so the gantry's transit path never crosses the
  fiber corridors.
- **Enclosure and dressing (replaces the present small box):** the current 3D-printed
  enclosure with glass top and acrylic front shows the need for still air and dust
  control already exists; in the redesign it grows into the full cell — one enclosure
  around nest, fiber aligners, gantry and hotel, with a laminar top-down flow or at
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

**Why via S3:** the single highest-risk item in every concept is the same — does the
self-registering nest really deliver ±10–25 µm / ±0.05° over hundreds of seatings
without facet damage? That question is answered fastest and cheapest by building **one
nest + a short comb** (S3 hardware minimum), cycling dies through it a few hundred
times, and measuring. Everything built for that test (nest, vision verify, fiber
choreography, orchestration software) is carried unchanged into S1; the gantry and
hotel are then a procurement-and-integration project around a proven core, not a
gamble. If the nest trials instead show bare-die robot handling is untenable, the same
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
| Manual die placement / tweezer workflow | **Eliminated** from routine operation entirely. |
| Open-frame bench layout | **Replaced** by an enclosed, interlocked, ESD-managed cell (required once a robot moves near fibers). |

---

## 8. Measurements and decisions required before detailed design

1. **Fiber/chuck 3-D envelope** (tip-to-first-bulky-feature, holder W×H, safe retract,
   full swept volume during alignment) → nest pedestal recess, gantry keep-out, parking
   positions.
2. **Permitted die contact** (top-side end zones? full backside? allowed force,
   contamination class) → end-effector design (twin-pad top pick vs backside pick),
   pallet clip design if S2.
3. **Die dimensional data** (thickness ± tol, dicing size and squareness tol, facet
   edge condition as-received) → datum option (facet-face vs end-face), funnel
   acceptance, θ budget check.
4. **Nest seating trials** (the S3-minimum prototype): repeatability over ≥ 300
   seatings, facet-edge inspection every 50, vacuum-seat detection ROC → the go/no-go
   data for S1 vs S2.
5. **First-light capture range in practice** (from existing logs: raster window sizes
   that converge reliably) → confirms the ±10–25 µm / ±0.05° presentation budget.
6. **Carrier reality check:** which shipping carriers dies actually arrive in (waffle
   pack geometry, Gel-Pak tack level X0–X8) → pick head force/eject requirements.
7. **Test-plan regimes:** expected mix of full characterization vs screening per
   campaign → pipelining priority and hotel sizing.
8. **Throughput accounting on the current tester** (operator minutes and interventions
   per die today) → the baseline the business case is measured against.

## 9. Risks and open questions

- Facet-face datum contact durability (fallback documented in §3).
- Robot pickup on TFLN top surface: coating/metallization sensitivity in the 1-mm end
  zones; Bernoulli or backside pick as alternates.
- Vacuum-pedestal stress and die bow for thin dies at the pedestal recess required by
  the chuck envelope.
- Gel-Pak extraction reliability (tack variability) if packs, not waffle trays, are the
  incoming format.
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

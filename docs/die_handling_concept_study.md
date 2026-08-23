# Concept Study — High-Throughput Handling and Edge-Coupled Testing of 10 × 6 mm Photonic Dies

**Status:** concept study for review (pre-CAD)
**Scope:** storage, transfer/indexing, and precision presentation of singulated 10 × 6 mm
edge-coupled photonic dies on the existing die tester, targeting hundreds of dies with
minimal operator intervention.

This document responds to the mechanical design brief ("High-Throughput Handling and
Edge-Coupled Testing of 10 × 6 mm Photonic Dies"). It presents **five substantially
different architecture concepts**, compares them against the brief's criteria, and
recommends a phased path. Concept A (linear self-registering magazine) is treated as the
reference point required by the brief, not as a foregone conclusion; two of the concepts
(D and E) are not variants of a planar multi-die tray at all.

Coordinate convention follows the brief: **X** = 10 mm die dimension (indexing
direction), **Y** = 6 mm die dimension (optical propagation, fibers approach along ±Y),
**Z** = vertical, **θ** = in-plane rotation.

---

## 1. What the existing tester already gives us

The concepts below are grounded in the hardware and software actually present in this
repository, because several of the brief's open questions are already partly answered by
it:

| Existing capability | Source | Consequence for the handling design |
|---|---|---|
| Left + right lensed-fiber XYZ stages, Suruga Seiki DS102 steppers, 50 nm/pulse | `src/DieTesterInstrument.py` (`default_step = 7`) | Fine coupling resolution is not the problem; die *presentation* repeatability only needs to land inside the existing first-light capture range. |
| Center sample stage with **one X translation axis + one θ rotation axis** (0.006°/full-step, limit switch disabled → usable as an indexer) | `DieTesterCenterStage` | An X-indexed carrier and per-die θ correction map directly onto axes that already exist. The center stage has **no motorized Y** — die-to-die Y consistency must come from the fixture, exactly as the brief argues. |
| Both fiber Z axes on one shared controller (`dev4`), with a homing convention chosen so Z homes *away* from the die | `DieTesterStage.__init__` comments | Safe fiber retract between dies is already a first-class operation; the handling concept only has to define the retract distance, not the mechanism. |
| Camera + OpenCV template matching for chip-angle calibration using a ~10 mm X sweep across the die | `src/ChipAlignmentController.py` | Vision-based θ and X/Y residual measurement per die already exists. A fixture only needs to be repeatable enough that this runs as a quick check, not a search. |
| Automated first light (raster + Z-scan, Gaussian fit) and full-chip stepping over all waveguides (`run_all_waveguides`, e.g. devices 2–66) | `src/FirstLightController.py`, `src/AutoAlignController.py` | Within one die, testing is already hands-off. **Die exchange is the only remaining manual step**, confirming the brief's bottleneck analysis. |
| Software fence / collision protection using camera-calibrated fiber-tip position | `src/SoftwareFence.py` | Any concept that moves the carrier with fibers nearby can reuse this for collision-safe indexing. |

Two unknowns dominate the architecture choice and must be measured first (see §8):

1. **Usable X travel of the center stage.** The angle-calibration routine sweeps ~10 mm,
   so travel is at least ~15 mm, but a multi-die linear magazine at ~11 mm pitch needs
   roughly `10 + (N−1)·pitch` mm of travel (≈ 100 mm for 9 dies). If the current stage is
   a short-travel unit, Concept A needs either a longer X stage or a carrier that feeds
   through a fixed test window; Concept B (carousel) sidesteps the limit entirely by
   using the existing θ axis as the indexer.
2. **The true 3-D fiber/chuck keep-out envelope** (tip-to-first-bulky-feature distance,
   holder width/height, swept volume during raster alignment). This sets how much
   structure may exist beside the die in ±Y and therefore the nest and carrier geometry
   for every concept.

---

## 2. Requirements distilled

From the brief, the invariants any architecture must satisfy:

- **R1 — Optical access:** both 10-mm facets (Y = 0 and Y = 6 mm) free, including the
  full 3-D fiber/ferrule/chuck approach and alignment-sweep volume on both sides.
- **R2 — Coarse-in, precise-out loading:** operator places die approximately; the
  fixture self-registers it to deterministic datums and retains it automatically.
- **R3 — Common optical line:** successive dies at essentially the same Y and θ; die
  exchange ≈ known X index + small local correction, not a re-search.
- **R4 — Independent registration:** each die references carrier datums, never its
  neighbor; die-size tolerance must not accumulate.
- **R5 — Contact only in permitted zones:** top-side contact only in the two 1-mm X-end
  strips; backside contact allowed but recessed well behind the facets.
- **R6 — Chip safety:** no tweezers at facets in routine operation; minimal clamping
  stress, particles, and drop/collision risk.
- **R7 — Deterministic carrier return:** if a removable carrier is used, the
  carrier-to-tester interface must itself be kinematic/repeatable
  (tester → carrier datum → die datum → waveguide hierarchy).
- **R8 — System throughput:** optimize operator-minutes and interventions per 100 dies,
  acquisition time per die, and recovery behavior — not carrier capacity.

A useful quantitative target: the existing raster first-light search converges quickly
when the waveguide is within roughly a few tens of µm and a few hundredths of a degree
of the expected position. So the fixture + carrier + indexing chain should deliver
die-to-die repeatability of order **±10–25 µm in Y/Z, ±0.05° in θ** at the test point.
That is precision-machining territory, not air-bearing territory — which is what makes
self-registering fixtures attractive and sub-micron mechanics unnecessary (brief §10).

---

## 3. Shared building blocks (used by several concepts)

These elements recur across concepts and can be developed once.

### 3.1 The precision die nest

A single nest design, replicated (Concepts A, B) or built once (Concepts C, D, E):

```
 Top view (one nest)                          Side view (through Y)

   preload finger (spring/flexure)               fiber →        ← fiber
        ↓ pushes -Y                                 │  die (0.3–0.7 mm thick) │
   ┌────────────────────────────┐                ┌──┴──────────────────────┴──┐
   │ ▷                        ◁ │  ← 1-mm zones  │            DIE             │
   ●─┬──────────────────────┬──●                 └───┬────────────────────┬───┘
   │ │      DIE  10 × 6     │  │                     │  vacuum pedestal   │
   ● │                      │  ▷← X datum +          │  10 × ~3 mm, top   │
   ↑ └──────────────────────┘  │   X preload         │  ≥1.5 mm recessed  │
   Y/θ datums (2 contacts,     │                     │  from each facet   │
   facet-side face, inside     │
   the two 1-mm end zones)
```

- **Y/θ datums:** two hard contacts (polished sapphire/ruby half-round pins or lapped
  carbide lands, ~0.5 mm contact width) touching the **facet-side face at Y = 0, inside
  the two 1-mm X-end zones only**. This is the arrangement sketched in brief §9. It
  fixes the *coupling plane itself* — the facet face becomes the Y reference — so the
  fiber working distance is constant die-to-die regardless of die-width (Y) tolerance.
- **Alternative Y/θ datum (zero facet contact):** reference the two contacts off the
  **diced X-end face** (X = 0, a 6-mm non-optical face) instead. This never touches a
  facet, but θ then depends on dicing squareness of that face relative to the waveguide
  axis, and Y position inherits the die-width tolerance. Recommended fallback if facet
  edge chipping at the datum contacts is observed during prototyping; otherwise the
  facet-face datum at the end zones is preferred because waveguide-to-facet geometry is
  lithographic.
- **X datum:** one contact on the X = 10 mm end face; **preload** via a light compliant
  finger (flat-spring flexure, ~0.1–0.3 N) pushing the die −Y and −X into the three
  contacts simultaneously (a single angled finger at the free corner does both).
  Flexures, not coil springs: no particles, no lubricant, deterministic force.
- **Z / hold-down:** vacuum through a **backside pedestal 10 × ~3 mm**, centered in Y,
  its edges recessed ≥ 1.5–2 mm behind each facet (final recess set by the measured
  chuck envelope, §8). Pedestal top lapped flat; die thickness places the waveguide
  plane well above the pedestal, so the near-facet volume at waveguide height is empty.
  Vacuum also serves as **presence/seating detection** (per-nest line + gauge).
- **Loading funnel:** the nest opening is surrounded by generous chamfers/ramps
  (≥ 1 mm lead-in) so a die dropped within ~±0.5–1 mm and ±2–3° slides down and, on
  preload engagement (cam lever or vacuum-actuated finger), seats against the datums.
  Sequence: *place loosely → preload finger sweeps die onto datums → vacuum confirms
  seating*. No tweezers near facets after the initial coarse placement.

### 3.2 Carrier-to-tester kinematic interface

For any removable carrier (Concepts A, B, D): a classic **Maxwell three-groove kinematic
mount** (three balls on the carrier, three radial V-grooves on the tester receiver, one
toggle clamp or magnetic preload). Repeatability of a modest machined version is ~1–2 µm
and < 0.01° — negligible against the ±10–25 µm budget. This preserves the reference
hierarchy *tester → carrier datum → die datum → die → waveguide* (brief §23) across
carrier swaps.

### 3.3 Vision hand-off (already in the repo)

After any index motion: one camera frame + template match (existing
`ChipAlignmentController`) verifies residual X/Y/θ; residual θ corrected with the
existing rotation axis, residual X with the index axis, residual Y and Z absorbed by
the *fiber* stages (they have full XYZ). Then the existing raster first-light runs as a
confirmation, not a search. Target: die-to-die transition < 30 s including retract,
index, verify, and first coupling.

---

## 4. The five concepts

### Concept A — Linear self-registering magazine (reference concept, refined)

**Architecture.** One monolithic bar ("precision comb") carrying 8–12 nests of §3.1 at a
fixed 11–12 mm pitch, all datum features machined in a single setup on one piece of
hardened stainless or invar (brief §18: monolithic ⇒ no assembly stack between nests).
The bar mounts to the X index axis via the §3.2 kinematic interface. Both ±Y sides of
the whole row are open along the full magazine length.

```
            index X →
  ║ NEST1 ║ NEST2 ║ NEST3 ║ … ║ NEST10 ║      ← one monolithic comb
     ▲ open fiber corridor above (+Y) and below (−Y) the entire row ▲
```

**Workflow.** Operator preloads the magazine **offline at a bench loading station**
(a duplicate kinematic receiver with good lighting and a lever that actuates all preload
fingers): drop 10 dies coarsely, flip the preload lever, watch 10 vacuum indicators (or
mechanical seat flags) confirm. Carry the magazine to the tester, click into the
kinematic mount, connect one vacuum coupling, start the run. The tester indexes die →
die by the known pitch; §3.3 hand-off per die; unload the whole magazine at the end.
With two magazines, loading is fully masked behind test time.

**Key dependency:** X index travel ≈ `(N−1)·pitch + margin` (9 dies @ 11 mm ⇒ ~90–100 mm).
If the current center stage is short-travel, add a long-travel X axis (e.g. a 100–150 mm
Suruga/THK crossed-roller stage with the same DS102 controller family — driver and
software already support it) under the existing rotation axis, or mount the comb on the
new axis and keep the existing stage for fine correction.

**Assessment highlights:** simplest credible path to ~10× fewer operator interactions;
θ/Y consistency limited only by one machined part + dicing tolerance; failure modes are
benign (one unseated die = one skipped nest, detected by vacuum). Capacity per load is
modest (8–12), so "hundreds of dies" means ~10–25 magazine swaps — acceptable if each
swap is ~2 minutes and loading is offline.

---

### Concept B — Carousel on the existing rotation axis

**Architecture.** A rigid disk (Ø ~90–130 mm) with 12–24 nests of §3.1 arranged around
the rim, dies oriented with their optical Y axis **radial**: outer facet overhangs the
disk edge; the inner facet faces a **cut-through window** in the disk so the inboard
fiber reaches it from inside the disk's open sector. Equivalently: the disk is a ring of
cantilevered nest "paddles" with open slots between rim and hub at every nest. The disk
mounts kinematically (§3.2) **directly on the existing center-stage θ axis**, which the
code shows has its limit switch disabled (continuous rotation) and 50 nm/pulse-class
resolution — at a 50 mm nest radius that is sub-µm tangential indexing resolution.

```
        test station (12 o'clock): both fibers engage here
                     ↓
              ┌──── die ────┐  ← outer facet overhangs rim
        ○   ○ │   window    │ ○   ○      rotation = indexing
      ○       └─────────────┘       ○
     ○         (open slot to          ○
      ○         hub for inner fiber) ○
          ○    ○    ○    ○    ○
```

**Workflow.** Same offline loading as Concept A (rotate the disk under a fixed loading
funnel at the bench station). On the tester, indexing is a fixed rotation increment; at
the single 12-o'clock test station both fibers engage exactly as today. Small per-die θ
residual is corrected by the *same* rotation axis (it is both indexer and fine-θ axis);
X residual by the existing X axis.

**Why it's interesting.** It needs **no new long-travel stage**: capacity scales with
circumference (Ø 120 mm rim ⇒ ~2× the dies of a 100 mm linear travel) while the stage
footprint stays constant. Indexing motion is short and fast.

**Watch-outs.** (a) Dies sit on an arc, so nominal per-die frames involve a rotation —
trivial in software but the vision/coupling frames must rotate with the die (camera sees
each die in the same pose at the station, so in practice this is invisible). (b) Disk
flatness/wobble and bearing runout enter the Z and θ budget; the θ axis was chosen for
fine correction, so its wobble under a ~1 N·m moment load must be measured (§8).
(c) The inboard fiber chuck must fit through/over the disk window — this is the concept's
critical 3-D clearance check and depends directly on the measured chuck envelope.
(d) Cantilevered nests demand a stiff disk (thick aluminum tooling plate or steel).

---

### Concept C — Waffle-pack storage + automated pick-and-place into one fixed precision nest

**Architecture.** Dies stay in their **shipping waffle packs** (zero re-handling into a
carrier). A small 3-axis gantry (or desktop SCARA) with a compliant vacuum tip picks the
selected die from the open pack, carries it ~100–200 mm, and sets it into **one single
precision nest** (§3.1) fixed at the optical station. The nest self-registers the die
(coarse placement tolerance of the robot: ±0.3 mm, ±1° — easily met by a cheap gantry);
test; robot returns the die to its pack pocket (or a "tested/failed" pack for binning).

**Workflow.** Operator interaction = swap waffle packs (24–100 dies each, depending on
pack) and press start. Everything else is automatic, including **binning by test
result**, which no carrier concept provides.

**Assessment highlights.** This is the only concept in this study that reaches
"hundreds of dies per operator interaction" in one step, and the precision problem is
solved exactly once (one nest, no nest-to-nest variation at all — the best possible
die-to-die Y/θ consistency). It also fully separates the brief's three functions:
storage = waffle pack, transfer = robot, presentation = one nest.

**Costs and risks.** A pick-and-place mechanism, its controller, tooling, and safety
interlocks are a genuine machine-build (≈ 5–10× the engineering of Concept A); every die
is individually handled by vacuum near its facets once per side of the move (top-surface
pickup must respect the 1-mm end zones or use a full-back Bernoulli/vacuum tip approved
for the top surface — needs the permitted-contact answer from §8); a robot fault near
the fibers is the worst collision case, so the software fence must gate robot motion.
Die-in-nest exchange time (~10–20 s) is masked by nothing, but is small next to test
time. Recommended as the **Phase-3 evolution**, reusing the identical nest developed for
Concept A.

---

### Concept D — Standardized mini-pallets + single kinematic test dock

**Architecture.** Each die is mounted **once**, at a bench station, onto a reusable
~16 × 16 mm hardened pallet carrying its own §3.1-style datums and a mechanical clip or
latching vacuum. From then on, all handling touches only pallets. Pallets stack in cheap
gravity magazines; a simple pusher/elevator feeds them one at a time into a **single
kinematic dock** at the optical station (3-groove mount + clamp, §3.2). The dock, not
the pallet, is the precision element; pallets only need repeatable datum features
(centerless-ground pins, jig-ground grooves — a per-pallet cost of tens of dollars at
quantity).

```
  bench: die → pallet (self-registering, once)
  magazines of pallets → feeder → [DOCK at optical station] → out-stack
                                     ↑ fibers engage here
```

**Assessment highlights.** Bare-die handling drops to exactly one event per die,
performed at a bench with ideal ergonomics — the lowest facet-risk concept. The tester
sees an endless stream of identical robust objects; feeding robust pallets is a solved,
low-precision problem (gravity + pusher), so tester-side automation is much simpler than
Concept C's bare-die robot. Scales smoothly: more magazines = more capacity, no
precision surface grows with capacity.

**Costs and risks.** One extra tolerance interface (die→pallet, pallet→dock) versus
die→carrier; total stack still comfortably inside budget if pallet datums are ground.
Pallet fleet cost and management (cleaning, ID marking — engrave a serial / Data Matrix,
which also gives free die traceability). Loading effort per die at the bench is similar
to Concept A's per-die effort, so operator minutes per 100 dies are not better than A —
the win is safety, traceability, and a clean path to full automation (a robot that
handles pallets is far simpler and safer than one that handles bare dies).

---

### Concept E — Stationary die bar + translating optical head

**Architecture.** Invert the motion: dies rest in a long fixed comb (same monolithic
nest bar as Concept A, but bolted to the table), and the **optical head moves** — both
fiber stages, their Z axes, and the camera ride a common long-travel X gantry that steps
from die to die.

**Assessment.** Included because the brief explicitly asks "does the die need to move?"
The honest answer for *this* tester: it is the weakest fit. The moving mass becomes two
fiber XYZ stacks + camera + cabling (fibers and USB in a drag chain — a reliability and
polarization-stability liability for the measurement itself), the gantry must hold the
two opposing fiber stages in mutual alignment while translating (a much harder stiffness
problem than translating a passive 200 g comb), and essentially all existing stage
software assumes a moving sample. It becomes attractive only if dies ever must remain on
a temperature-controlled or probe-card-contacted chuck that cannot move. Otherwise
moving the lightest thing — the die carrier — wins. Kept as a documented rejection with
its trigger condition, per the brief's request to genuinely consider it.

---

## 5. Comparison matrix

Ratings: ● strong / ◐ adequate / ○ weak, judged against the brief's criteria (§26).
"Nest count" = number of precision-registration feature sets that must be made and kept
consistent.

| Criterion | A. Linear magazine | B. Carousel | C. Pick-&-place + 1 nest | D. Mini-pallets + dock | E. Moving head |
|---|---|---|---|---|---|
| Dies per operator loading event | 8–12 ◐ | 12–24 ◐ | 24–100 (per pack) ● | per magazine of pallets ● | 8–12 ◐ |
| Operator loading effort | low (offline bench) ● | low (offline bench) ● | pack swap only ● | per-die pallet mount ◐ | low ● |
| Self-registration mechanism | §3.1 nest ×N ● | §3.1 nest ×N ● | §3.1 nest ×1 ● | pallet datums + dock ● | §3.1 nest ×N ● |
| Die-to-die Y consistency | one machined comb ● | disk + runout ◐ | single nest, best ● | dock-limited ● | comb + gantry ◐ |
| Die-to-die θ consistency | ● | ◐ (wobble budget) | ● | ● | ◐ |
| X indexing accuracy | stage-limited ● | θ-axis, sub-µm ● | robot coarse + nest ● | n/a (one dock) ● | gantry ◐ |
| Expected repeatability after carrier swap | kinematic mount ● | kinematic mount ● | n/a ● | dock clamp ● | ● |
| Optical fiber clearance | whole row open ● | inner-fiber window is the crux ◐ | one open nest, best ● | open dock ● | open ● |
| Stage-travel requirement | ~100 mm X (likely new stage) ○ | none new ● | robot only ● | none new ● | long gantry ○ |
| Die-to-die transition time | ~15–30 s ● | ~10–20 s ● | ~30–60 s ◐ | ~20–40 s ◐ | ~20–40 s ◐ |
| Vision/alignment requirement | verify-only ● | verify-only ● | verify-only ● | verify-only ● | verify + gantry cal ◐ |
| Chip/facet damage risk | low ● | low ● | robot handles bare dies ◐ | lowest ● | fibers moving near dies ○ |
| Ease of unloading / binning | whole carrier ◐ | whole disk ◐ | automatic binning ● | per-pallet, traceable ● | whole comb ◐ |
| Manufacturability | 1 monolithic part ● | disk + windows ◐ | nest easy, robot is COTS ◐ | pallet fleet + feeder ◐ | major rebuild ○ |
| Footprint | +100 mm travel ◐ | compact ● | + robot cell ○ | + feeder ◐ | large ○ |
| Compatibility with existing tester/software | high (X+θ axes, `run_all_waveguides`) ● | high (θ axis reused) ● | medium ◐ | medium ◐ | low ○ |
| Automation potential (→ hundreds unattended) | swaps remain manual ◐ | swaps remain manual ◐ | full ● | full (simple robot) ● | ◐ |
| Expected reliability | very high ● | high ◐ | medium (robot) ◐ | high ● | medium ○ |
| Complexity / approx. relative cost | 1× (baseline) | ~1.2× | ~5–10× | ~2–3× | ~8× |
| Scalability toward hundreds of dies | via magazine swaps ◐ | via disk swaps ◐ | best ● | best-safe ● | ◐ |

---

## 6. Recommendation — a phased path that shares one nest design

The concepts are not mutually exclusive; three of them share the §3.1 nest verbatim.
That suggests a low-regret sequence:

**Phase 1 — build the nest once, prove it (2–4 weeks of shop time).**
Machine a *single* §3.1 nest on a kinematic base. Measure: seating repeatability
(reload the same die 30×, measure facet Y/θ by camera), facet-edge condition after 100
seats (decides facet-face vs end-face datums), vacuum hold vs fiber-touch events, and
the real chuck keep-out volume. Every downstream concept inherits these numbers.

**Phase 2 — linear magazine (Concept A) as the workhorse**, sized by the measured X
travel: if the existing center stage travel ≥ ~60 mm, start with a 5-die comb on it and
defer the stage purchase; otherwise add a 100–150 mm DS102-compatible X axis. Build two
magazines + one bench loading station so loading is masked. Software: extend
`run_all_waveguides` one level up (`run_all_dies`: per-nest X offsets from one stored
calibration of the comb, per-die vision verify, per-die θ touch-up) — the repo's
structure already anticipates exactly this loop.
*If Phase-1 measurement shows the existing θ axis is stiff and true under moment load
and the chuck fits the inner window, Concept B (carousel) is the drop-in alternative
with double the capacity and zero new stages — decide on measured data, not preference.*

**Phase 3 — only if sustained volume demands unattended operation:** evolve to Concept C
(robot feeds the *same* nest from waffle packs, adds binning) or Concept D (pallet
stream, if facet-risk/traceability dominates). The Phase-2 magazine remains useful as
the manual-override and engineering-lot path.

Rationale versus the brief's own metric (§25): Phase 2 cuts operator interactions from
~1 per die to ~1 per 10–20 dies, with per-die transitions dominated by a known X index +
verify (~15–30 s), at baseline cost and near-zero software risk. Phases 1→2→3 never
discard precision hardware.

---

## 7. Keep-out and support geometry (applies to all concepts)

- Nothing above the die top surface within the central 8 mm of X — ever (hold-down is
  backside vacuum; the preload finger touches only end-zone side faces).
- Backside pedestal recessed ≥ 1.5–2 mm in Y from each facet **pending** the measured
  chuck envelope; evaluate in 3-D including the raster-scan swept volume and the
  angular-adjustment sweep, not a single section (brief §22).
- A protected **retract corridor**: before any index/rotation, both fibers retract along
  the optical axis by a fixed, software-fenced distance (reusing `SoftwareFence`), and
  the index axis is interlocked on "fibers retracted" — in software now, by a limit
  signal later.
- No structure taller than the die's waveguide plane within the fiber approach cone on
  either ±Y side for the full magazine/disk length (this is what kills the four-wall
  pocket and the dense 2-D array, brief §15–16).

## 8. Measurements to take on the existing tester before CAD

Priority-ordered subset of brief §24, with what each one decides:

1. **Center-stage usable X travel and repeatability** → Concept A capacity vs new-stage
   purchase; comb length.
2. **Fiber/chuck 3-D envelope**: tip-to-first-bulky-feature distance, holder W×H, safe
   retract distance, full swept volume during raster + angle alignment → pedestal
   recess, nest wall heights, Concept B inner-window feasibility.
3. **θ-axis wobble/runout under ~1 N·m moment** → go/no-go for Concept B.
4. **Die thickness and tolerance; dicing X/Y size and squareness tolerances; facet edge
   condition** → datum option (facet-face vs end-face), funnel clearances, whether θ
   from end-face dicing is inside the ±0.05° budget.
5. **Permitted top-side and backside contact, allowed clamping force, contamination
   class** → pickup method for Concept C, pallet clip design for D.
6. **Camera field of view, µm/pixel (already measured by `SoftwareFence` calibration),
   and template-match repeatability** → how much fixture error vision can absorb, i.e.
   how cheap the fixture tolerances may be.
7. **First-light capture range in practice** (from `FirstLightController` logs: raster
   window sizes that reliably converge) → the hard number behind the ±10–25 µm /
   ±0.05° presentation budget in §2.

## 9. Open questions / risks

- Facet-face datum contact: acceptable or not? (Phase-1 test decides; end-face fallback
  documented in §3.1.)
- Vacuum level and pedestal area vs die bow and permitted backside stress.
- Anti-static / contamination requirements for nest materials (hardened stainless vs
  ceramic contacts).
- Whether tested-die *binning* is required now (only Concepts C/D provide it natively;
  A/B provide it via per-nest map + operator sort at unload).
- Thermal: if any measurement needs temperature control, the chuck constraint may flip
  the choice toward Concept E's stationary-die logic — flag early.

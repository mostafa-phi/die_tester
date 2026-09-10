# Pick-and-place design: how the gripper handles the die

**Status:** design note, rev. 1 (2026-09-06). Governs `cad/gripper`, the tray pockets in `cad/tray`, the
chuck in `cad/nest` and the exchange software. The CAD quotes this note; when a number here changes,
change the model and the checks, then this note.

Frame and contact rules as in `CLAUDE.md`: X = die long axis, Y = optical axis, Z up, die bottom on
the nest at home = 0. The die is touched only on its two diced **end faces** (X = 0 and X = 10) inside
the band Y 1.5–4.5, Z 0.05–0.40, and rests only on its **backside**. Facets and top surface are never
touched.

## 1. Decision: friction grip on the end faces, nothing under the die

The jaws squeeze the end faces between a rigid nose (far, +X) and a compliant nose on a 0.127 mm
spring-steel blade (near, −X). The die is held by friction only. The gripper never reaches under the
die, so neither the chuck nor the tray has to expose the backside.

| Quantity | Value | Source |
|---|---|---|
| Die mass, 10 × 6 × 0.5 mm LiNbO₃ (4.65 g/cm³) | 0.14 g, weight 1.4 mN | geometry |
| Grip preload (blade 2.46 N/mm × 0.13 mm) | 0.32 N ± 0.06 N over the ±25 µm die-length tolerance | `cad/gripper/checks.txt` |
| Friction capacity, two contacts, µ = 0.3 (PEEK on diced LN) | 0.19 N | estimate; measure in the hand-cycling rig |
| Friction capacity at a pessimistic µ = 0.1 | 0.064 N | |
| Margin over weight | 45× (µ 0.1) to 140× (µ 0.3) | |
| Inertia at 5 m/s² transfer acceleration | 0.7 mN | |
| Contact pressure, 0.32 N on 3 × 0.35 mm | 0.3 MPa | orders below any material limit; chipping at an edge is the only risk |

**Rejected alternative: a toe under the die.** A 0.15 mm toe on each nose reaching 0.3 mm under the
die's bottom edge would make retention positive. It fits geometrically (the chuck pad is 0.5 mm inboard
of the end faces, the tray floor is open between the ledges) but every set-down becomes a 0.15 mm drop
off the toes, the push-to-stop keeps only 0.2 mm of pad margin for the toe, and Z accuracy matters
more. With the friction margin above and a verified release (section 5) the toe is not needed. It stays
on record as the fallback if the hand-cycling trials show slip.

## 2. Nose geometry

- **Band**: Y 1.5–4.5 (3 mm, the die middle), Z 0.05–0.40. The nose top is 0.10 mm below the die top so
  the top edge of a diced face, the most chip-prone line, is never loaded; the bottom is 0.05 mm above
  the die bottom so the backside lands on its support before a nose could.
- **Crown across the band width**: the contact face is a cylinder of radius 30 mm with its axis
  vertical and its apex at the nominal nose plane (sag 38 µm at the band edges). A die whose end face is
  not square to the jaws then meets the nose on a line inside the band instead of on the nose's edge.
  Two crowned noses square the die as flat ones do: the contact points move to ±R·θ and the normals
  through the crown axes give a restoring couple 2·F·(L/2 + R)·θ, so the jaws still define X and yaw
  (0.39 mN·m per degree at 0.32 N). The crown is on the noses, not the die.
- **Material**: Semitron ESd 480 (static-dissipative PEEK) noses, both replaceable; 0.6 mm setback
  above the band so the tip blocks never touch the die.

## 3. Sequences with heights, forces and interlocks

Z values are the die-bottom height in the gripper frame; the support height (chuck pad top Z 0, tray
ledge top) must be known to ±0.05 mm. The pad is lapped and fixed; each **new tray** is touched off
once (camera on a die, or a die-in-jaws contact) and its ledge height stored.

### 3.1 Pick from the tray pocket

| Step | Motion | Why it is safe |
|---|---|---|
| 1 | Jaws open (+1.5 mm per side); Z to ledge top + 0.05 mm with the noses in the 3.6 mm slots | slots keep the noses off the walls (0.3 mm), nose bottom 0.05 above the ledge top |
| 2 | Close at ≤ 10 mm/s (meter-out speed controllers on the MHZ2 ports) | the first nose to touch slides the die along the ledges (< 1 mN of ledge friction) until the other arrives; the die ends centred between the noses, so X and yaw come from the jaws, not from the ±1.0 mm pocket play |
| 3 | Hard stop reached: blade deflected 0.13 mm, 0.32 N on the die | force appears only when both noses touch; the push during sliding is microscopic |
| 4 | Z +8 mm, then transfer | 45× to 140× friction margin |

Tipping during closing is not a concern: the push acts within 0.03 mm of the centre-of-mass height and
the die slides rather than pivots.

### 3.2 Place on the tray pocket

| Step | Motion | Why it is safe |
|---|---|---|
| 1 | Z down to ledge top + 0.05 mm (die bottom 0.05 above the ledges), Y row and X column already set | end walls ±1.0 from the die ends, corner posts ±0.4 from the facets only within 0.5 mm of the corners (the walls are relieved to ≥ 1.0 mm elsewhere, so a facet cannot touch the tray along X 1–9), noses in the slot channel |
| 2 | Jaws open at ≤ 10 mm/s; die drops 0.05 mm onto the ledges | landing energy 0.07 µJ; the noses never scrape a diced face, which an overdrive would risk |
| 3 | Z +8 mm | |

An overdrive of up to 0.1 mm is tolerable (the noses then slide on the end faces with 0.19 N of
friction, and the backside takes 0.19 N), but the 0.05 mm drop is the nominal.

### 3.3 Place on the chuck (push-to-stop)

| Step | Motion | Why it is safe |
|---|---|---|
| 0 | Die stage at home (origin sensor), fibers retracted 1 mm | gripper enters only at home |
| 1 | Z down to pad top + 0.05 mm with the die's +X end face 0.2 mm short of the stop pads | corner guards 0.6 mm outside the facets, X guard 0.4 mm behind the near end |
| 2 | Jaws open; die drops 0.05 mm onto the lapped pad | |
| 3 | Gripper X +1.7 mm: the open near nose meets the −X end face, slides the die 0.2 mm onto the two +X pads and overtravels 0.10 mm; the blade limits the push to 0.25 N | the two pads (Y 0.6–1.2 and 4.8–5.4) square a yawed die: one pad touches first and the push rotates the die onto both, with ledge-level friction on the pad |
| 4 | Chuck vacuum on; vacuum switch must read "sealed" | flatness and presence only: a die 0.2 mm short of the pads seals just as well (the pad is 0.5 inboard of the ends), so this is not the registration check |
| 5 | Gripper X −1.7 mm, Z +8 mm, X out to park | |
| 6 | Registration check: the nest microscope images the +X die edge against a pad face (die stage +5 mm in X brings it under the objective) and reads the gap, nominal 0; with the blade-deflection sensor of §4 the check is also made during step 3, where the deflection must start at the pad position ±0.02 mm of X-axis travel (a die that resists anywhere else is stuck, not seated) | the "seated" signal is the microscope, or the deflection-at-position signal; the vacuum switch alone never is |

### 3.4 Pick from the chuck: the release must be positive and verified

A lapped pad and a flat backside stick: residual vacuum, moisture, van der Waals. Adhesion above the
0.19 N friction capacity is only 4 kPa over the 45 mm² pad, and if it happens the noses slip up the
end faces and scrape them. The release is therefore done **with the die already held in the jaws**, and
any positive pressure is small enough that the grip dominates it (rev. 2 of this section; the earlier
"blow-off pulse of a few kPa before gripping" would have put 0.1–0.2 N under a 1.4 mN die that was
free inside the cage, i.e. it would have launched it):

| Step | Motion | Interlock |
|---|---|---|
| 1 | Die stage home; fibers retracted 1 mm; chuck vacuum still on | flags |
| 2 | Jaws open, Z down to pad top + 0.05 mm, close at ≤ 10 mm/s on the vacuum-held die | the die cannot move: the noses meet it where the push-to-stop left it (within the ±0.03 mm the blade absorbs) |
| 3 | Vent the chuck line to atmosphere; then, optionally, a positive pressure of ≤ 0.5 kPa through the same holes (≤ 22 mN on the pad, a tenth of the friction capacity) to break the seal | vacuum switch reads atmosphere before any Z motion |
| 4 | Z +8 mm at ≤ 5 mm/s | if adhesion still exceeds the grip the noses slip and the die stays: caught by step 5, no scraping beyond one slow slip |
| 5 | Die-present check (section 4) before the X move | a die left on the pad is seen by the microscope; a die missing from the jaws stops the sequence |

### 3.5 Z across the tray: a taught map, not a planarity requirement

What the sequences above tolerate in Z: at the **pick** the nose top must stay 0.10 mm below the die top and the crown
must stay on the end face, so +0.05 / −0.30 mm; at the **place** (tray or chuck) ±0.10 mm. The chuck is one taught
point. Across the tray the ledge plane wanders by the LX20 running parallelism (0.025 mm per axis over the X and Y
travel), the deck flatness (0.05 called out), the printed tray's ledge plane (0.1 called out; a PPA-CF print can bow
more), the ledge height and the die thickness: 0.1–0.2 mm stacked, more than the +0.05 pick window. So Z is commanded
**per pocket** from a plane (or 3 × 3 grid) fitted to measured ledge heights, and the Z actuator's ±5 µm repeatability
does the rest. How the map is obtained, in order of preference:

1. **Make the stack small.** Machined 6061 deck (top flat within 0.02 after a fly cut), tray on the two pins, SLA tray
   whose ledge plane was measured flat within 0.1 mm on a surface plate (print list T1), or a machined tray (0.02). With
   the LX20 running parallelism of 0.025 per axis and ±0.025 on the die thickness the stack is 0.10–0.17 mm worst case.
2. **Widen the window.** The pick at the tray is 0.10 mm lower than nominal (contact band Z −0.05…0.30 on the end face,
   nose top 0.20 below the die top; the noses sit in the slot channel beside the ledges, 0.75 above the pocket floor), so
   the pick tolerates +0.15 / −0.20 and the place ±0.10.
3. **Teach per tray type with the jaws themselves.** A gauge die in the four corner pockets and the centre; the jaws
   are lowered in 0.02 mm steps until the die on the ledges lifts the closed jaws' contact (the MHZ2 switch reads
   "closed empty" as the noses ride up), or simply until the picked die's height at the nest microscope stops changing.
   Five points, once per tray type (not per tray), fitted to a plane and stored. Because the jaws measure their own
   height, the rail-pitch error between a sensor position and the jaws does not enter.
4. **Check every die with the camera.** The dart on the arm (§3.6) sees each die's apparent length: at 75.6 mm and
   13 µm per pixel a 10.000 mm die spans 770 px and a 0.1 mm height change scales it by 1.0 px, so with sub-pixel edge
   fitting and a one-time lens calibration each die's height is known to about ±0.03 mm before the pick, and a die
   sitting on a wall (0.8 mm proud, tilted 4.6°) is unmistakable.

**Why not a laser displacement sensor.** A Panasonic HG-C1030 (30 ± 5 mm, 10 µm) on the arm was modelled
(`cad/station/README.md`): it is 20 × 44 × 25 mm on a 60 mm drop bracket, as big as the gripper actuator, and no
10 µm-class sensor is much smaller because the triangulation baseline sets the size. It would map the wall tops at nine
points in about 10 s; the stage repeatability (±5 µm) is far better than needed for that, but the sensor rides the same
rails 61 mm from the jaws, so the rail-pitch component of the jaw height (up to the 0.025 mm parallelism) is not seen
by it, while the jaw touch-off above sees everything. It stays as an option in the model (`SN["laser"]`).
X, Y and yaw of the tray come from the two deck pins (`cad/tray/README.md`), so the map is only Z.

### 3.6 Seeing the pocket before the pick: the camera on the arm

The gripper itself is blind; the pocket play is removed mechanically (X and yaw by the closing noses, X and yaw again by
the push-to-stop at the nest) except for **Y**, which the jaws do not define, and the discrete errors of hand loading
(die rotated 180°, upside down, missing, doubled, chipped). The **Basler dart daA1440-220um** camera on the arm end
plate looks down 76 mm behind the jaws (X −76, Y 3 in the gripper frame): at the traverse height a tray die is 75.6 mm
from the lens, field 18.5 × 13.9 mm at 13 µm per pixel, so one pocket fills the frame. The lens is a 16 mm M12 board
lens on a 4 mm spacer ring: board lenses are sold focused near infinity with a 100–200 mm minimum object distance, and
the extension that focuses one at distance d is f²/(d − f), 4.3 mm here (depth of field about 1.5 mm at f/4). The camera
stands on top of the end plate with its lens ring down through the plate, so nothing hangs below it. Before
each pick the software checks occupancy, reads the orientation fiducial (ask the layout for an asymmetric mark in the
metal layer), flags chipped corners, and measures the die's Y offset in the pocket to ±0.05 mm; the pick then lands the
die centred in the nest cage instead of up to 0.4 mm off. A 180° die is either mapped mirrored or skipped and logged; an
upside-down or missing die is skipped. The nest microscope re-checks every die after the place (fiducials, seat against
the pads). Lighting: a small white LED ring around the lens (to be added to the bracket) or the bench light; the die's
metal fiducials read well in dark field.

### 3.7 Watching the pick and the place: the live-view camera

The tray camera looks 76 mm behind the jaws and the nest microscope looks straight down, so neither shows the moment
that matters when something goes wrong: the noses entering the slots, the die lifting off the ledges or settling on
the pads, the release. A second **dart daA1440** on a boom off the arm end plate's −Y edge (`cad/station`,
`live_cam_boom_6061`) rides with the gripper and looks at the jaws from the side: optical axis in the die's X = 5
plane, 35° above the horizontal, aimed at the die centre from 63 mm; an 8 mm M12 lens on a 1.5 mm spacer gives
24 × 18 mm at 16 µm per pixel with about 6 mm of depth of field at f/5.6, enough for the tilted die and the jaws'
approach. Because the camera moves with the gripper the picture is the same at every pocket and at the nest, so one
set of image regions (nose gap, die outline, ledge line) serves the whole run, and a frame per step can be logged
with the pick record. Why the −Y side and not −X or above: from ±X the arms and tip blocks hide the end faces, from
above the height is invisible, and −Y is the arm's own side, so the boom stays short and inside the exchange
envelope's Y band; at the nest the sight line to the die's near bottom edge clears the input fiber chuck's tip by
0.2 mm (the chuck hides only what lies below the die in the middle of the frame, and the fibers are retracted 1 mm
during the exchange anyway). It is a monitoring camera: the metrology stays with the microscope (nest) and the tray
camera (pocket). Lighting: two 3 mm white LEDs on the pad, or the microscope ring light at the nest.

## 4. Sensing the die in the jaws

The MHZ2's two D-M9N switches cannot tell a gripped die from an empty closed jaw (the hard stop is
the same). Options, in order of preference:

1. **Blade deflection**: with a die the blade is deflected 0.13 mm, without it 0. A reflective
   photo-microsensor or a small inductive sensor looking at the near tip block from the near head
   reads this directly. It senses the actual grip, not just presence, and works at every location.
   To be prototyped on the hand-cycling rig.
2. **Camera**: the overhead microscope sees the pad and the die at the nest; it cannot see the tray.
3. **Thru-beam through the Ø0.6 bores** in both tip blocks at Z 0.25 (already in the CAD). LiNbO₃ is
   transparent, so the beam is only attenuated by scatter at the diced faces; keep the bores, test the
   contrast before relying on it.

## 5. Parts and settings this note adds to the BOM

- 2 × meter-out speed controllers on the MHZ2-6D ports (M3), set for ≤ 10 mm/s finger speed.
- Chuck line: 3/2 vacuum valve (already listed) plus a 2/2 blow-off valve to a regulated few-kPa air
  supply, both under the sequencer; vacuum switch on the chuck line.
- Die-present sensor per section 4 after the rig trials.

## 6. What the hand-cycling rig has to measure (before the axes arrive)

1. Friction coefficient nose-on-diced-LN: hang known masses from a gripped blank die; expect > 10 g
   before slip.
2. 200 pick/place cycles tray → chuck → tray on silicon blanks, then on LN blanks, then on scrap TFLN
   dies; inspect end faces and facet edges under the microscope after every 50.
3. Release from the lapped pad with and without the blow-off pulse; record any slip.
4. Set-down scatter on the pad: X against the pads (should be mechanical), Y and yaw by camera.

## 7. Design rationale: review questions and where the design gives

Answers to the questions a reviewer asked about the sequences above (rev. 2.12). Each says what the
number is, why it is what it is, and what would change it.

**Why is the pick height window so narrow (+0.05 / −0.30 mm)?** The window is only narrow at the top.
The nose band is Z 0.05–0.40 on the 0.5 mm end face because the top edge of a diced face is the
chip-prone line and sits at the waveguide layer, so the nose top is kept 0.10 below it; the bottom
margin is 0.05 so the backside lands before a nose could. Downward the window is generous: a nose that
sits lower still contacts the end face (the noses stand in the slot channel beside the ledges, 0.85 mm
above the pocket floor, and 0.5 mm inboard of the chuck pad). Two design changes open it without any
sensor, and both are now the plan (§3.5): pick 0.10 mm lower than nominal at the tray (band Z −0.05…
0.30 on the face, window +0.15 / −0.20), and, if the hand-cycling rig shows that a shorter band holds
the die just as well, shorten the band to 0.25 mm (Z 0.10–0.35), which makes it ±0.20. The band was
0.35 for friction area and squaring, not because 0.25 fails: the contact pressure is 0.3 MPa and the
crown line contact 2 MPa, orders below any limit. A compliant Z approach was considered and rejected:
the flexure is in X, and adding Z compliance to the tips means the noses find the die by touch, which
is what the top edge must never feel. Tolerance analysis first, sensor second, was the order followed:
the laser was dropped once the stack (0.10–0.17 mm) fitted the widened window.

**Why push the die against stops after release?** For a deterministic X and yaw without vision. The
jaws centre the die to ±0.03 mm in X and square it, but the transfer adds the X axis (±5 µm repeat,
absolute worse), the arm's thermal drift and the seating of the die in the jaws, so a placed die is at
±0.05–0.1 mm and ±0.1°. The fixed fibers then step device to device along X on the die stage: at ±0.1
mm the first-light search per device is a ±100 µm raster (minutes), at ±5 µm it is ±10 µm (seconds).
The pads give ±5 µm in X and ±0.03° yaw for the cost of a 0.2 mm slide of the backside on the lapped
pad under 0.25 N. The alternative is measure-and-correct: the nest microscope already images the
fiducials for the rotary's yaw null, the die stage (15 mm travel) can absorb an X offset and the fibers
absorb Y, so the push is not needed for accuracy if the fiducial measurement is reliable. It is kept as
the default because it is cheap, needs no image processing to work, and gives a hard "seated" signal;
it becomes a configurable step, and the hand-cycling rig decides (backside inspection after 1000
pushes on a lapped pad).

**Why 0.32 N of grip?** It is not a specification, it is what the flexure produces: 2.46 N/mm × 0.13 mm
preload, ±0.06 N over the ±25 µm die length tolerance. It was chosen from the friction margin: at
µ 0.1–0.3 the two contacts carry 64–190 mN against a 1.4 mN die weight, 0.7 mN of transfer inertia and
up to 0.19 N of pad adhesion at release. The upper side of the window is far away: 0.3 MPa on the band,
2 MPa Hertz at the R30 crown (PEEK on LN), no measurable bending of the die. So the acceptable window
is roughly 0.1–1 N, the blade is a starting point inside it, and the knobs are blade thickness and the
preload shim. The rig measures what matters: pull-off force with a gauge die, the slip force on the
chuck with residual adhesion, and end-face inspection after 1000 cycles for marks.

**How is contact with both pads detected?** Not by the vacuum: a die that stops 0.2 mm short of the pads
is still fully on the pad island and seals. The vacuum switch reports flatness and presence only. Two
signals give registration (§3.3 step 6). The definitive one is the nest microscope, which images the +X
die edge against a pad face after the die stage moves the die 5 mm under the objective and reads the gap
(nominal 0, resolution well under 1 µm at the objective's magnification). The fast one, once the
blade-deflection sensor of §4 exists, is the push itself: the X axis reports where the blade started to
deflect, which must be the pad position ±0.02 mm; a die that resists earlier is stuck on the pad, one
that never resists was never in the jaws. Both are logged per exchange; the first is the acceptance
criterion, the second the interlock that stops the sequence before the vacuum is applied.

**Temperature requirements.** Not yet specified by the test plan, and they set the chuck, the sensing,
the nearby materials and the exchange sequence, so they are listed here as the proposed default until the
user confirms or changes them: set point 25 °C (lab ambient) for functional tests, range 15–60 °C for
thermal characterisation; stability ±0.05 K at the thermistor over a test (TFLN resonances move by a few
pm per K; ±0.01 K only if ring-resonator spectra are the product); settling criterion, thermistor within
±0.05 K of the set point for 10 s before the fiber alignment starts (a 10 K step settles in about 20 s
with a 15 × 15 mm TEC and the 0.14 g die). Handling temperature: the die's thermal mass is negligible,
the jaws and the tray are PEEK and PPA-CF, so unloading at any set point in the range is allowed, with
two rules: never below the dew point plus 2 K without a dry-nitrogen purge, and ramp at ≤ 2 K/s because
LiNbO₃ is pyroelectric and charges with every temperature swing (the reason the cage and the noses are
static-dissipative). The cage's PEEK pads expand 50 ppm/K, so a 35 K excursion moves the pad faces about
5 µm over their 3 mm height, within the ±5 µm budget; the copper chuck and its thermistor bore, the TEC
pocket and the wire channel in the riser are already modelled (`cad/nest`). The thermistor should be
within 3 mm of the pad island (it is, in the neck below it) and the die-to-thermistor offset calibrated
once with a thermocouple on a dummy die.

**What establishes a successful release before a damaging slip?** The numbers as stated do not close at
the pessimistic corner: at µ 0.1 the grip carries 64 mN and the worst adhesion case cited is 190 mN, so
the grip alone cannot be relied on. The design closes it in three steps. First, the seal-break: venting
plus ≤ 0.5 kPa of positive pressure through the pad holes removes the residual-vacuum term, which is the
only adhesion mechanism of that size on a lapped, Ni-plated pad under a ground backside (capillary and
van der Waals forces on a surface with 0.1–0.5 µm roughness are of order millinewtons); the 22 mN also
acts upward on the die, i.e. it helps. Second, an incremental lift with verification: the Z axis lifts
0.05 mm and the nest microscope, whose depth of field at the alignment objective is a few micrometres,
must see the die leave focus (or its edge move); if it does not, motion stops with at most 0.05 mm of
nose travel on the end faces, the seal-break repeats once, and the exchange aborts with the die still on
the pad and the vacuum re-applied. That makes "one limited slip" a bounded event of 0.05 mm at 5 mm/s,
not an accepted failure: for the prototype rig on silicon blanks it is tolerated and counted; for
production dies the abort path is the requirement. Third, the grip window allows raising the preload:
a 0.6 N blade doubles the capacity to 130 mN at µ 0.1, and the rig measures µ for PEEK on diced LiNbO₃
first; if it measures below 0.2 the blade is changed before any real die is handled. The thru-beam sensor
through the tip blocks (§4 option 3) is the on-gripper backstop: a die that slips more than 0.25 mm
relative to the noses clears the beam and stops Z within a few milliseconds.

**Why blow off before capture?** The earlier sequence was wrong and is corrected above (§3.4): a
"few kPa" through the pad holes under a free die is 0.1–0.2 N against 1.4 mN of weight. The die is
now gripped while the vacuum still holds it, then the line is vented, then an optional ≤ 0.5 kPa
(≤ 22 mN, a tenth of the grip's friction capacity) breaks the seal, and the lift is slow. If adhesion
still wins, the noses slip once and the die-present check stops the sequence; nothing can lift or
rotate the die while the jaws and the pads bound it.

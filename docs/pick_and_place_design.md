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
  vertical and its apex at the nominal nose plane (sag 37 µm at the band edges). A die whose end face is
  not square to the jaws then meets the nose on a line inside the band instead of on the nose's edge.
  Two crowned noses square the die as flat ones do: the contact points move to ±R·θ and the normals
  through the crown axes give a restoring couple 2·F·(L/2 + R)·θ, so the jaws still define X and yaw
  (0.35 mN·m per degree at 0.32 N). The crown is on the noses, not the die.
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
| 1 | Z down to ledge top + 0.05 mm (die bottom 0.05 above the ledges), Y row and X column already set | pocket walls ±1.0 / ±0.4 from the die, noses in the slots |
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
| 4 | Chuck vacuum on; vacuum switch must read "seated" | seat detection; a die that stuck on the pad short of the pads is caught here |
| 5 | Gripper X −1.7 mm, Z +8 mm, X out to park; camera confirms X against the pads, reads Y | |

### 3.4 Pick from the chuck: the release must be positive and verified

A lapped pad and a flat backside stick: residual vacuum, moisture, van der Waals. Adhesion above the
0.19 N friction capacity is only 4 kPa over the 45 mm² pad, and if it happens the noses slip up the
end faces and scrape them. Therefore:

| Step | Motion | Interlock |
|---|---|---|
| 1 | Die stage home; fibers retracted 1 mm | flags |
| 2 | Chuck line vented to atmosphere, then a blow-off pulse of a few kPa through the same holes (3/2 valve on the vacuum line, second valve to the air side) | vacuum switch reads atmosphere before any Z motion |
| 3 | Jaws open, Z down to pad top + 0.05 mm, close at ≤ 10 mm/s | |
| 4 | Z +8 mm | |
| 5 | Die-present check (section 4) before the X move | a die left on the pad is seen by the camera; a die missing from the jaws stops the sequence |

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

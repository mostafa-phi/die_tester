# R05 leaf bonding traveller

Bench procedure for bonding the eight 0.20 mm 17-7PH shim leaves to the CNC 6061
body. Written 2026-09-08 for hand assembly of the first units; it goes on the
bench with the parts. Design record: `../../../README.md` (section R05).

Why this holds: each tab is 8 × 3.5 = 28 mm² and carries ~5 N of shear at full
stroke against ~700 N of adhesive capacity. Strength is never the question. What
sets the stage's performance are three things you control here: **where the
leaf root is** (masking), **where the pieces sit while the epoxy sets**
(fixture), and **surface preparation**.

## Materials

| item | spec | notes |
|---|---|---|
| adhesive | 3M Scotch-Weld DP460 (or Loctite EA 9460) | two-part toughened epoxy, duo-pak + static mixer; NOT cyanoacrylate, NOT retaining compound, NOT solder |
| masking | PTFE tape 0.05–0.10 mm | on the leaf's free length, up to the bar edge |
| spacing (optional) | 0.05 mm glass beads in the mix | otherwise the bar torque sets the bond line |
| abrasive | Scotch-Brite or 240-grit (aluminium), 600-grit (steel tabs) | |
| solvent | IPA (and acetone for the first degrease) | lint-free wipes, nitrile gloves |
| primer (optional, recommended) | 3M AC-130 or phosphoric-acid etch on the 6061 ledges | roughly doubles humidity durability |
| fixture | `assembly_jig.step` (pockets for platform and stages, dowels for the frame) | this is what sets alignment and free length; gauge shims are the fallback only |
| clips | 16 small spring clips (or binder clips with card pads) | every bar is bonded, there are no clamp screws; the clip sets the bond line during cure |
| oven | 65 °C for 1 h (kitchen oven at its lowest setting is fine) | 24 h at room temperature is the fallback |

## Fixture: where the pieces sit while it cures

The four body pieces (frame, two input stages, platform) are positioned only
by the leaves. During cure something else must hold them at nominal, with
every leaf straight:

1. Seat the platform (with its arms) and both stages face down in the jig's
   3 mm pockets; they locate to ±0.02 on the pocket walls.
2. Drop the frame over the jig's four dowels (its bolt pattern). All four
   pieces now sit at nominal with every void gap at **8.5 mm** (both coupler
   and guide free lengths) and every front face on the jig floor, coplanar.
3. Fallback without the jig: bolt the frame to the base plate, fill the voids
   with 8.5 mm gauge shims and lay a flat plate across the front.

A 0.1 mm error in a stage's position becomes a 0.1 mm offset of that axis'
zero - out of 110 µm of travel the optical loop never notices it. What matters is
that no leaf is bent at rest.

## Sequence

1. **Prep, within one hour of bonding.**
   - Ledges (6061): acetone degrease, abrade to a uniform matte, IPA wipe until
     the wipe is clean; primer if used. No bare fingers after this.
   - Tabs (17-7PH): degrease, light 600-grit on the tab area only, IPA wipe.
     **Do not touch or abrade the free length** - a scratch there is a fatigue
     crack.
2. **Mask** each leaf's free length with PTFE tape right up to where the bar's
   inner edge will sit. Any fillet that extends past the bar edge onto the
   flexing length moves the root, stiffens that leaf against the others, and
   puts a hard notched edge at the peak-stress point.
3. **Bond**, one tab at a time: a toothpick's worth of mixed epoxy on the ledge,
   leaf on, bar on, spring clip over the bar. Wipe squeeze-out at the bar edge with an IPA-damp swab. Target bond
   line 0.05–0.10 mm; the clip gives that by itself.
   Order: the four platform-side coupler bars first (they fix the platform),
   then the stage-side coupler bars, then the guide leaves outer bars, then
   inner bars.
4. **Gel, then de-mask**: at ~2 h room temperature the epoxy has gelled; pull
   the PTFE tape now (it will not come off cleanly after full cure).
5. **Cure**: 1 h at 65 °C with the fixture in place and the actuators NOT
   fitted; let it cool clamped. (Fallback: 24 h at room temperature.)
6. Lift the assembly off the jig. Push the platform gently by
   hand to each stop (±0.3 mm); it must move freely with no rub.
7. Fit the actuators last (see the README: frame pad first from the plate
   edge, then the stage pad from the coupler void), then the holder.

## Acceptance on the bench (ten minutes, before it goes on the station)

| check | how | pass |
|---|---|---|
| stiffness, each axis | known force on the platform (10 g mass on a lever, or the actuator at a known voltage) vs. displacement | within ~15 % of 0.060 N/µm, Y and Z equal within 10 % |
| slip / creep | cycle each axis ±50 µm a few hundred times, watch the zero | no drift |
| root position | compare Y and Z stiffness | a leaf with a fillet past the bar edge shows as one axis stiffer |
| free travel | drive to the stops | no contact inside ±100 µm, clean contact at ±0.3 mm |

## If a tab is wrong

DP460 softens at ~150 °C: local heat (hot-air pencil) on the bar lifts the tab;
clean the ledge back to bare metal and re-do that tab alone. Keep two spare
leaves with the kit.

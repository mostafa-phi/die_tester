# Simulation and prototype plan

Status: **section 2 partly solved; sections 3-5 open.** The single-axis static
compliance case is meshed, solved and mesh-converged in
[`fem_r01/`](fem_r01/README.md): \(k_\text{guide}\) = **0.0395 N/um**, 1.3% above
the 0.039 N/um estimate `screening.py` produces by beam/spring analysis. That
covers the guide's own stiffness only; the payload, actuator, gravity and
off-axis cases in section 2 are not run, section 2's stress-convergence criterion
is **not** met, and sections 3-5 are untouched. `screening.py` remains a
one-dimensional estimate, not a solver.

**Do not attempt this in Fusion.** Its Simulation extension can solve these
studies from the GUI but cannot be driven through the API in build 2704.1.53 -
the `adsk.sim` classes exist while the product handle they hang off is
unreachable, so nothing is scriptable or repeatable. Evidence and the exact
failure modes are in `fem_r01/README.md`. The solver stack used instead is gmsh
+ scikit-fem + MKL PARDISO in the `pic-env` environment.

## Inputs and configuration control

Use the standalone Z STEP for the first study and the XYZ STEP for the assembly study. Record the input STEP SHA256, parameter JSON, software/version, mesh settings, material data source, contacts and constraints alongside every result. Keep scratch meshes in ignored `work/`; promote completed, reviewable results with their inputs into a named revision folder.

`cases.json` defines the initial case inventory. Null entries are missing requirements, not zero values. The elastic material values are engineering seeds; fatigue allowables must account for the actual alloy condition, EDM surface, root finish and desired life.

### Payload and range, as of 2026-09-07 (user)

Two statements from the user later the same day supersede the paragraph below
and everything in the brief:

- **The holder is an aluminium block 25 × 10 × 7 mm - 4.9 g.** Not 300 g, not
  70 g. The parallel plate's loaded cases use exactly this block (25 mm along the
  fiber, standing on the platform's front face; that orientation is assumed).
- **A large range of motion is required; ±8 µm is not remotely enough.** That
  rules out the direct-drive (unamplified stack) variant for good and keeps the
  amplified APA60S with its ≥ 60 µm loaded stroke as the actuator. The exact
  range the nest's placement error demands is still to be measured.

### Payload: 300 g is superseded (user, 2026-09-07, earlier that day)

**The maximum probe weight is < 70 g** (now further reduced to the 4.9 g block
above). This replaces the "up to 300 g" figure
that runs through the design brief and `cases.json`. The brief is a preserved
research note and is not edited; `cases.json` still carries the old
`payload_kg` list and `300 g` cases because it is a tracked input to the P0
build manifest and cannot be changed without a `build.py --fusion` rebuild.
Update it at the next rebuild. Until then **this section is the authority**.

Assumed scope, to confirm: < 70 g is everything carried on the Z carriage - the
probe plus its holder and clamp hardware - not the probe alone. COM, inertia and
the normal (as opposed to maximum) working mass remain unspecified, so the
holder is still a release blocker.

What it does and does not change, using k_guide = 0.0395 N/um from `fem_r01/`:

- **Not gravity sag.** The APA sits in parallel with the guide leaves, so the
  driven axis sees k_APA + k_guide = 1.74 N/um. Sag is 0.39 um at 70 g and would
  have been 1.69 um at 300 g - negligible either way. (Guide alone it would be
  17.4 um and 74.5 um, but the actuator is never absent.) Gravity was never the
  binding constraint on the vertical axis.
- **Not travel.** Stroke is set by the stiffness ratio, which the payload does
  not enter.
- **Yes, the payload moment.** At the 40 mm sensitivity offset the moment drops
  from 117.7 to 27.5 N.mm, a factor of 4.3. This matters most because the APA's
  allowable moments and off-axis stiffness are still unknown; a 4.3x smaller
  disturbance makes that unknown far less likely to be the thing that kills the
  design.
- **Yes, the loaded modal target.** Less payload raises the loaded first mode
  toward the 300 Hz preference. By how much cannot be stated without the modal
  mass and the holder inertia.

Retire the 0.2 kg and 0.3 kg qualification cases. Keep 0.1 kg as a margin case
only. The 40 mm offset stays a sensitivity case, not an approved specification.

### Architecture: the stack is no longer the only candidate (2026-09-07)

The design brief takes X/Y/Z nesting as given and never weighs it against a
parallel-kinematic platform. That question is now answered numerically in
[`../parallel_yz/`](../parallel_yz/README.md): one wire-EDM plate in the YZ
plane, two APA60S grounded to its frame, fiber through the centre, coarse X and
optionally the fem_r01 single-axis module as fine X underneath. Same pipeline,
same convergence gates:

| | stacked P0 | parallel R01 |
|---|---|---|
| guide stiffness, driven axis | 0.0395 N/µm | 0.1375 N/µm |
| loaded stroke, worst-case APA | 66.5 µm | 62.6 µm |
| first mode with the 4.9 g holder, actuators as springs | not solved (lumped ≈ 420 Hz) | **1200 Hz**, converged (630 Hz with the earlier 70 g surrogate) |
| cross-axis coupling / tip angle at full stroke | not solved | 0.002 % / ≤ 0.2 µrad, zero by symmetry |
| moving mass on the search axes | ~250 g | 25 g + payload |

Sections 3 and 4 below are written for the stack; for the parallel plate the
"assembly" is the plate itself, section 3's loaded modal is done (minus mount
compliance and the real holder), and section 5's single-axis prototype becomes
one leg of the plate. The decision between the two, and between the plate and
its smaller / direct-drive variants, waits on two inputs that are the user's:
the nest's placement error (sets the range actually needed) and the holder
mass (the largest remaining lever on bandwidth).

## 1. Complete the geometry needed for meaningful FEA

- Replace the rigid output land with a defined coupling, or justify direct mounting using vendor data.
- Add root radii and remove unintentional sharp stress singularities.
- Define actual attachment surfaces and fasteners. Do not bond convenient adjacent surfaces that should move independently.
- Establish the normal holder mass, COM, inertia and fiber-tip location; specify an offset envelope for the 300 g maximum.
- Obtain APA transverse/rotational stiffness and external force/moment limits. An axial-only spring cannot predict safe off-axis actuator loading.

## 2. Single-axis static study

The guide's local motion axis is **Y**; when placed as the final Z module it maps to assembly Z.

- Constrain only the intended fixed-frame mounting interfaces.
- Represent the APA with a suitable axial actuation/stiffness model. Do not reconstruct its internal ceramic prestress without vendor information.
- Apply gravity, the actual payload inertial/moment representation, actuator travel across its specified voltage range and measured assembly offsets.
- Check displacement at the payload tip, guide-root stress/strain, actuator forces and moments, and stop clearance.
- Evaluate the 40 mm / 300 g moment case as a sensitivity case, not an approved payload specification.

Begin with quadratic solid elements where available; resolve each thin leaf through its thickness, refine roots and demonstrate convergence. Choose the actual element count from convergence, not a cosmetic mesh image. Compare at least three mesh densities; initial acceptance is <5% change in tip displacement and relevant frequency, with a separately justified stress-convergence criterion.

**Done for the bare 1 N compliance case** (`fem_r01/static_r01.json`): quadratic
tets, four densities to 1.2M dof, displacement changes 2.10% / 2.86% / 1.29%.
**Not done:** the stress criterion. Peak von Mises runs 6.3 -> 6.2 -> 6.4 -> 6.7 MPa,
non-monotonic and still rising 4.11% at the finest mesh, and is sampled at
quadrature points so it under-reads the fillet peak. No stress number from this
revision may be quoted as a root stress, and fatigue assessment stays blocked on
it as well as on the missing allowable.

## 3. Loaded modal study

Include actuator/interface stiffness, guide intermediate rails, actual holder inertia and mounting structure. Run centered payloads from `cases.json`, the actual COM case, and sensitivity to coarse-stage/pedestal stiffness. Extract at least the first ten modes; identify rocking, torsion and intermediate-link modes as well as intended translations.

Use a prestressed modal solution where gravity, preload or geometry changes materially affect stiffness. Do not quote the bare APA's resonance as the stage resonance. Small dither amplitude does not remove resonance/phase constraints.

**Started, not satisfied.** `fem_r01/modal_r01.json` has the guide's own first ten
modes, converged to 1.11% (first mode 330.7 Hz). That is the guide alone: no
holder inertia, no actuator stiffness or mass, no mount compliance, no prestress,
and only translations of a single axis. It is an upper bound, not the loaded
first mode this section asks for, and it must not be compared with the 300 Hz
target. The cases listed above stay open pending the real holder and the APA
off-axis data.

## 4. Assembly and frequency-response study

Model the X carriage carrying the Y fixed frame and the Y carriage carrying the Z fixed frame. Include each upstream axis's carried mass and inertia. Check all eight commanded corners, nominal and maximum payloads, cross-axis tip displacement, and the mounting compliance.

After plausible modal behavior is established, evaluate harmonic response over candidate scan/dither bands using measured or justified damping. Absolute bandwidth claims must wait for bench frequency-response measurements.

## 5. Station integration and experimental acceptance

- Place the head with an explicit optical-X to station-Y transform using `cad/common` datums.
- Check coarse approach/retract, full fine travel, nest device stepping, gripper exchange, microscope envelope, and fiber/wire service loops.
- Test a single-axis prototype first: travel vs voltage, angle vs travel, loaded frequency response, ring-down and sensitivity to assembly torque.
- Then test XYZ acquisition time and coupling repeatability with the actual chips and fibers.

## Release gates

The following are separate outcomes: nominal geometry clearance; manufacturable geometry; mesh-converged stress/modal analysis; validated actuator interface loads; measured travel/dynamics; maximum-payload qualification; optical acquisition performance. None implies the others.

The preferred 300 Hz loaded-mode target and 60 µm loaded-stroke target are design objectives. Tip-error tolerance, fatigue life and the normal holder definition are still open. Keep every failed or unresolved case visible in the results summary.

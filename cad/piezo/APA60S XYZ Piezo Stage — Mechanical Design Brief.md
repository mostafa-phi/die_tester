# APA60S XYZ Piezo Stage — Mechanical Design Brief

## Objective

Design a compact 3-axis piezo fine-positioning stage for automated fiber-to-waveguide alignment.

Coordinate convention:

- **X:** optical axis
- **Y:** lateral/transverse
- **Z:** vertical/transverse

Requirements:

- Payload: **up to 300 g**
- Fine travel target: **≥60 µm per axis**, ideally ~65–70 µm
- Full alignment target: **<1 s**
- Y/Z perform the fast first-light search
- X performs primarily axial optimization
- Open-loop piezo operation is acceptable because optical power closes the alignment loop
- No bearings, ball screws, crossed rollers, or sliding guides in the fine stage

---

## 1. Actuators

Use:

**3 × CEDRAT APA60S**

The APA60S already includes:

- multilayer piezo stack
- preload
- mechanical displacement amplification
- ceramic protection

Therefore:

**Do not design another piezo amplifier or preload mechanism.**

The only additional mechanism needed is flexure guidance.

Before starting FEA, obtain from CEDRAT for the exact ordered revision:

- contractual datasheet
- STEP model
- force/displacement curve
- allowable off-axis loads/moments
- recommended M2 mounting torque
- large-signal capacitance
- recommended continuous dynamic operating limits

---

## 2. Recommended XYZ Nesting

Use three modular 1-axis flexure stages.

Recommended order:

```text
COARSE STAGE / FIXED FRAME
          |
          v
    X FINE STAGE
    APA60S
    [outer axis]
          |
          v
    Y FINE STAGE
    APA60S
    [middle axis]
          |
          v
    Z FINE STAGE
    APA60S
    [inner axis]
          |
          v
       PAYLOAD
       ≤300 g
```

Reasoning:

- X does not need the fastest full-range scan.
- Y and Z are the important search axes.
- Z is innermost so it lifts only the payload rather than also lifting the other fine stages.
- This minimizes vertical moving mass.

Y/Z may be swapped if actual CAD packaging clearly favors it, but X should preferably remain outermost.

---

## 3. Design of Each Axis

Each axis should consist of:

1. rigid fixed frame
2. moving carriage
3. compound-parallelogram flexure guide
4. one APA60S connecting fixed frame to moving carriage

Conceptually:

```text
             MOVING CARRIAGE
        +---------------------+
        |                     |
        +---------------------+
           ||             ||
           ||             ||
           ||             ||   FLEXURES
           ||             ||
===========||=============||=========== FIXED FRAME

        FIXED [ APA60S ] MOVING
                         ---->
```

One APA mounting interface attaches to the fixed frame.

The other attaches to the moving carriage.

The APA force axis must be collinear with the desired translation.

### Critical requirement

The **flexure guide must carry all off-axis load and moment**.

The APA should not be used to react:

- payload bending moment
- pitch/yaw load
- lateral load
- torsional load

---

## 4. Flexure Type

Preferred:

**monolithic compound/double-parallelogram flexure**

Material:

**7075-T6 aluminum**

Manufacturing:

**wire EDM**

The flexure should be:

- compliant in the desired translation direction
- very stiff laterally
- very stiff vertically/out-of-plane
- very stiff in pitch/yaw/roll
- backlash-free
- symmetric around the actuator axis

Do not use bearings or rolling guides.

---

## 5. Initial Flexure Geometry for FEA Sweep

These are only starting dimensions:

- leaf free length: **12–18 mm**
- leaf thickness: **0.35–0.60 mm**
- out-of-plane depth: **5–8 mm**

Good initial center point:

- length: ~15 mm
- thickness: ~0.45–0.55 mm
- depth: ~5–6 mm

FEA determines the final values.

---

## 6. Desired-Axis Guide Stiffness

The flexure guide consumes actuator stroke.

Approximate loaded stroke:

\[
x_{loaded}
=
x_{free}
\frac{k_{APA}}
{k_{APA}+k_{guide}}
\]

Target desired-direction guide stiffness:

\[
\boxed{k_{guide}\lesssim0.10-0.15\;N/\mu m}
\]

while maximizing stiffness in every undesired DOF.

With \(k_{APA}\approx1.7\,N/\mu m\) and \(k_{guide}=0.1\,N/\mu m\), approximately 94% of the actuator's free stroke remains.

### Mechanical acceptance target

- **≥60 µm loaded travel per axis**
- desired: ~65–70 µm

Do not sacrifice excessive travel by making the guide unnecessarily stiff in the commanded direction.

---

## 7. 300 g Payload

Maximum payload:

\[
m=0.30\,kg
\]

Static weight:

\[
F_g \approx2.94\,N
\]

The static force itself is small.

The more important problem is **payload moment**.

Keep the payload center of mass:

- centered on the stage
- close to the final Z carriage
- close to the flexure plane

Example:

300 g at a 40 mm offset produces:

\[
M\approx0.118\,N\,m
\]

The flexure guidance must carry this moment.

If the real CAD has a 40 mm COM offset, analyze at least:

- 0.12 N·m static moment
- dynamic moment from scanning
- appropriate mechanical safety factor

Use the actual final COM location rather than designing around this example.

---

## 8. Dynamic Requirements

Do not use the APA60S actuator's own resonance as the stage resonance.

The important resonance is the **complete loaded XYZ assembly**.

Targets:

- minimum complete loaded first mode: **>200 Hz**
- preferred: **>300 Hz**
- stretch target: **>500 Hz**

Expected operating region:

- full-range Y/Z search: approximately **20–50 Hz**
- small-amplitude post-capture dithering: substantially faster

For a <1 s alignment requirement, there is no reason to sacrifice robustness to chase multi-kHz loaded-stage resonance.

---

## 9. Required FEA

Model the complete system including:

- 3 × APA60S
- all flexure frames
- moving carriages
- 300 g payload
- actual payload COM
- fiber/probe holder
- wiring
- mounting adapter
- coarse-stage boundary stiffness where possible

Run:

### Static cases

- X full positive/negative travel
- Y full positive/negative travel
- Z full positive/negative travel
- combined XYZ corner
- gravity
- gravity + full Z command
- worst-case payload moment

### Modal cases

- no payload
- 100 g
- 200 g
- 300 g
- 300 g at actual COM offset

Extract:

- first 10 modes
- X/Y/Z translation modes
- pitch/yaw modes
- flexure-root stresses
- APA axial loads
- APA off-axis loads

---

## 10. Parasitic Motion

Do not accept only a specification such as "cross-axis coupling <1%."

Evaluate error at the actual fiber/probe tip.

Calculate:

- X command → parasitic Y/Z tip displacement
- Y command → parasitic X/Z tip displacement
- Z command → parasitic X/Y tip displacement
- pitch
- yaw
- roll

Angular error should be converted to tip motion:

\[
\Delta x_{tip}\approx L\theta
\]

Initial target:

**parasitic tip displacement well below 1 µm over full travel.**

The final allowable value should come from the optical coupling tolerance.

---

## 11. APA Mounting

Use the exact APA60S STEP geometry.

Current standard interface is approximately:

- two flat mounting surfaces
- ~2.5 × 5 mm
- M2 threaded interface

Design rigid local mounting lands.

Requirements:

- mounting faces parallel
- actuator axis aligned with stage translation
- no twisting during tightening
- no clamping of the elliptical actuator shell

Do not modify or drill the APA.

Obtain the allowable M2 screw torque from CEDRAT.

---

## 12. Hard Stops

Every axis should have mechanical handling/overtravel stops.

Stops should:

- protect during assembly/shipping
- protect against accidental excessive travel

They should **not** contact during normal electrically commanded motion.

Do not routinely drive an energized APA into a hard stop.

Operational travel limits should primarily be imposed electrically/software-side.

---

## 13. Cable and Fiber Management

Do not let wiring dominate the mechanics.

Requirements:

- strain-relieve APA wires on stationary structure
- provide short compliant service loops
- avoid wires crossing flexures under tension
- keep heavy probe/fiber cables off the final moving carriage

The optical fiber should also have a stationary strain-relief point close to the head.

---

## 14. Payload Plate

Final Z carriage should provide a compact rigid payload interface.

Prefer:

- precision locating features/dowels
- symmetric mounting
- minimal adapter thickness
- payload centered around stage axis

Do not build a generic optical-table platform if the actual probe-holder geometry is already known.

Design directly around the real holder.

---

## 15. Mass / Packaging Targets

Initial targets:

- individual module footprint: roughly **35–50 mm**
- individual module thickness: roughly **10–18 mm**
- complete fine-stage mechanism mass: preferably **<100–150 g**, excluding the 300 g payload

Minimize the mass of the moving parts rather than simply minimizing total fixed-frame mass.

---

## 16. Prototype Sequence

Do **not** machine the full XYZ assembly first.

### Step 1 — single-axis prototype

Build one:

**APA60S + compound-parallelogram guided carriage**

Test it with representative payload.

Measure:

- stroke vs voltage
- loaded stroke
- parasitic angle
- parasitic translation
- resonance
- response with 100/200/300 g
- behavior at 10/20/30/50/100 Hz

Proceed only if:

- loaded stroke ≥60 µm
- no stiction/backlash
- acceptable parasitic motion
- loaded resonance comfortably above intended search frequency

### Step 2 — full XYZ

Reuse the validated guide architecture for all three axes.

---

## 17. What Not to Design

Do not add:

- another displacement amplifier
- piezo preload mechanism
- ball bearings
- crossed-roller guides
- micrometers
- lead screws
- manual fine adjusters

The custom engineering effort should be:

\[
\boxed{\text{flexure guidance + nesting + payload interface + packaging}}
\]

not reinventing the actuator.

---

## Mechanical Deliverables

Please produce:

1. single-axis APA60S guided-stage CAD
2. flexure dimensions
3. actuator mounting detail
4. predicted guide stiffness
5. loaded stroke prediction
6. static stress FEA
7. 300 g loaded modal FEA
8. parasitic tip-motion analysis
9. proposed X/Y/Z nested CAD
10. actual payload COM/moment calculation
11. hard-stop concept
12. cable/fiber strain-relief concept
13. coarse-stage mounting interface
14. wire-EDM-ready preliminary drawing
15. prototype machining quote

### Starting design to pursue

**3 × APA60S + three modular compound-parallelogram flexure stages, X outer / Y middle / Z inner, 7075-T6, wire EDM, ≥60 µm loaded travel, 300 g payload, and >300 Hz preferred loaded first resonance.**
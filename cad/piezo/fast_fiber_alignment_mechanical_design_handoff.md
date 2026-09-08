# Fast Fiber-to-Waveguide Alignment Head
## Mechanical Design Handoff — Rev 1 / Rev 2

**Application:** Automated edge-coupled photonic chip testing  
**Optical axis convention:** X = optical axis, Z = vertical, Y = lateral  
**Primary objective:** Fast automatic fiber alignment to on-chip waveguides using a coarse long-travel X stage plus a fast piezo fine-alignment head  
**Design emphasis:** Minimum practical cost without sacrificing sub-second-class alignment capability

---

# 1. System Architecture

The alignment head is split into two motion layers:

1. **Coarse X approach stage**
   - Centimeter-scale travel
   - Used for safe retract, chip loading/unloading, and rapid facet approach
   - Recommended family: MISUMI LX/LXM
   - Fine optical alignment is not performed with this stage

2. **Fast piezo fine stage**
   - X/Y/Z fine optimization around first light
   - Optical power provides the true feedback signal
   - Fine-stage trajectory is generated continuously using analog commands
   - Two mechanical variants are proposed:
     - **Version A: Direct-drive XYZ**
     - **Version B: Direct X + amplified Y/Z**

Recommended production-default architecture:

```text
                     Fiber
                       |
               +-------v-------+
               |  Fine X stage |
               |   direct      |
               +-------+-------+
                       |
          +------------+------------+
          |                         |
   ~4x Y flexure              ~4x Z flexure
          ^                         ^
      Y piezo                   Z piezo
          |                         |
          +-----------+-------------+
                      |
               MISUMI coarse X
                      |
                    Frame
```

---

# 2. Design Decision

## Recommended production prototype

Use:

- **Direct-drive piezo X**
- **Approximately 3.5–4x amplified piezo Y**
- **Approximately 3.5–4x amplified piezo Z**
- MISUMI coarse X actuator below the piezo head

Reasoning:

- X does not require a large capture range because the coarse X stage already performs the long approach.
- Y and Z determine the first-light acquisition region and need substantially larger transverse capture range.
- Direct-drive XYZ is faster and stiffer, but its practical capture range is only roughly ±8–10 µm per axis.
- Amplified Y/Z gives approximately ±35–45 µm practical transverse capture range while preserving fast analog piezo scanning.

## Direct-drive version

Use this only if the machine's die nest, vision system, and coarse registration can reliably place the waveguide within approximately:

- **±6–8 µm in Y**
- **±6–8 µm in Z**

on every cycle.

---

# 3. Piezo Actuator — Frozen Component

## PiezoDrive SA030318

Use three identical stacks.

**Quantity:** 3

| Parameter | Value |
|---|---:|
| Dimensions | 3 × 3 × 18 mm |
| Travel, 0 to 150 V | ~18 µm |
| Travel, -30 to +150 V | ~25 µm |
| Capacitance | ~0.5 µF |
| Blocking force | ~330 N |
| Stiffness | ~18 N/µm |
| Approx. unit price | ~$113 |

Why this actuator:

- Low capacitance is critical for fast scanning.
- The alternative 5 × 5 × 20 mm class gives only slightly more displacement but approximately 3–4× higher capacitance.
- Lower capacitance reduces amplifier current demand and improves usable scan bandwidth.
- Force is more than sufficient for a lightweight fiber head.

---

# 4. Piezo Drive Electronics

## PiezoDrive PDu150

**Quantity:** 1

Use as the three-channel high-voltage amplifier.

| Parameter | Value |
|---|---:|
| Channels | 3 |
| Output range | approximately -30 to +150 V |
| Gain | 20 V/V |
| Peak current | ~100 mA/channel |
| RMS current | ~78 mA/channel |
| Small-signal bandwidth | ~180 kHz |
| Approx. price | ~$413 |

The mechanical stage, not the amplifier, should be the dominant bandwidth limit.

### Command relationship

```text
0 V command      -> ~0 V piezo
2.5 V command    -> ~50 V piezo
5.0 V command    -> ~100 V piezo
7.5 V command    -> ~150 V piezo
-1.5 V command   -> ~-30 V piezo
```

Recommended normal operation:

- Design around **0 to +150 V**
- Do not rely on negative voltage for nominal travel
- Treat negative drive as optional extra travel margin

---

# 5. Piezo Mechanical Interface and Preload

Bare piezo stacks must not see significant:

- tension
- bending
- shear
- off-axis loading

Each stack should be captured with a compliant preload system.

Recommended stack interface:

```text
Fine preload screw
        |
Belleville / compliant spring
        |
Ceramic or hardened ball interface
        |
Piezo stack
        |
Flat hard seat
```

Recommended preload:

- **80–120 N per stack**
- Keep preload safely below approximately 50% of blocking force
- Use a compliant preload element rather than rigidly clamping the stack

Recommended ball interfaces:

- PiezoDrive 3 mm ball ends
- Quantity: 3

Mechanical hard stops are mandatory so accidental over-command cannot fracture the piezo or flexure.

---

# 6. Version A — Direct-Drive XYZ

## Architecture

Three orthogonal direct flexure axes.

Recommended mechanism:

- monolithic flexure body
- no sliding guides
- no dovetails
- no crossed-roller stage in the fine head
- no ball bearings in the fine motion path
- double-parallelogram / parallel-guided flexure architecture

## Performance targets

| Parameter | Target |
|---|---:|
| X loaded travel | 16–22 µm |
| Y loaded travel | 16–22 µm |
| Z loaded travel | 16–22 µm |
| Practical capture radius | roughly ±8–10 µm |
| Mechanical amplification | 1× |
| Preferred first loaded resonance | >1.5 kHz |
| Initial usable scan frequency | ~150–300 Hz |
| Cross-axis coupling | <1% target |
| Fiber holder mass | <3 g preferred |
| Total moving mass | <10 g preferred |

## Advantages

- Highest stiffness
- Highest resonance
- Simplest mechanics
- Lowest parasitic angle
- Lowest cross-axis coupling
- Best candidate for fastest final alignment

## Disadvantage

Limited capture range.

Use only if coarse mechanical registration is already excellent.

---

# 7. Version B — Direct X + Amplified Y/Z

## Recommended baseline design

X:
- direct piezo drive
- no amplification

Y:
- approximately 3.5–4× amplified piezo flexure

Z:
- approximately 3.5–4× amplified piezo flexure

## Target ranges

With approximately 18 µm nominal piezo displacement over 0–150 V:

```text
18 µm × 4 ≈ 72 µm ideal
```

With full -30 to +150 V span:

```text
25 µm × 4 ≈ 100 µm ideal
```

Do not design around ideal amplification.

Allow for:

- flexure compliance
- preload
- parasitic deformation
- stack stiffness interaction
- machining tolerances

### Required loaded travel

| Axis | Required | Preferred |
|---|---:|---:|
| X | ≥16 µm | ~20 µm |
| Y | ≥70 µm | 80–90 µm |
| Z | ≥70 µm | 80–90 µm |

## Capture range

Expected practical capture:

- X: approximately ±8–10 µm
- Y: approximately ±35–45 µm
- Z: approximately ±35–45 µm

## Flexure topology

For Y/Z:

- symmetric bridge or flextensional displacement amplifier
- followed by a parallel-guided output stage
- avoid simple one-sided lever amplification
- minimize pitch/yaw during translation

Recommended design sequence:

```text
Piezo stack
    |
Symmetric bridge amplifier
    |
Parallel-guided output flexure
    |
Common moving fiber platform
```

## Performance targets

| Parameter | Target |
|---|---:|
| Y amplification | 3.5–4.0× |
| Z amplification | 3.5–4.0× |
| Loaded Y/Z resonance | >700 Hz minimum |
| Preferred Y/Z resonance | >1 kHz |
| Loaded X resonance | >1.5 kHz |
| Cross-axis coupling | <1% target |
| Fiber holder mass | <3 g preferred |
| Total moving mass | <10–20 g maximum |
| Parasitic pitch/yaw | minimize aggressively |

This is the recommended production-safe architecture.

---

# 8. Flexure Material and Manufacturing

Recommended material:

- **7075-T6 aluminum**

Recommended manufacturing:

- **Wire EDM**
- secondary precision machining as needed for mounting and interfaces

Reasons:

- high stiffness-to-mass
- good fatigue performance
- low moving mass
- suitable for monolithic compliant mechanisms
- easy to machine and iterate

The fine stage should preferably be a single monolithic body wherever practical.

Avoid assembling the compliant mechanism from many bolted thin members unless necessary.

---

# 9. Mechanical FEA Requirements

The flexure should not be dimensioned by static travel alone.

The optimization target should be:

> maximize first structural eigenfrequency subject to required travel, allowable stress, cross-axis error, and piezo preload constraints.

Minimum FEA cases:

## Static

1. X full positive command
2. X full negative command
3. Y full positive command
4. Y full negative command
5. Z full positive command
6. Z full negative command
7. Combined X/Y/Z worst-case corner
8. Piezo preload only
9. Piezo preload + full command

Evaluate:

- displacement
- stress
- piezo force
- amplifier gain
- parasitic pitch
- parasitic yaw
- parasitic roll
- cross-axis displacement

## Modal

Evaluate at least:

- unloaded flexure
- loaded with fiber clamp
- loaded with fiber clamp + realistic cable/fiber mass

Target:

- direct design first mode >1.5 kHz
- amplified Y/Z design first relevant mode >700 Hz
- preferred amplified design >1 kHz

---

# 10. Fiber Holder Requirements

The fiber holder is part of the dynamic system and should be designed as such.

Requirements:

- mass <3 g preferred
- very short moment arm from flexure platform
- clamp must not introduce large pitch/yaw offset
- support standard fiber or fiber-array geometry required by setup
- allow easy replacement
- cable/fiber strain relief should terminate on the stationary frame where possible

Avoid placing a commercial heavy fiber chuck directly on the moving piezo platform.

If a commercial fiber chuck is required, its mass must be included in the modal model.

---

# 11. Coarse X Stage

Recommended family:

- **MISUMI LXM20 / LX20**

Recommended characteristics:

- 30–50 mm coarse X travel
- approximately 5 mm lead
- stepper motor
- high-speed retract / approach
- precision grade preferred
- safe clearance for chip handling

The coarse X stage performs:

```text
Safe retract
    |
Chip exchange
    |
Fast approach
    |
Stop near nominal facet gap
    |
Piezo fine stage takes over
```

The coarse stage is not responsible for final coupling optimization.

---

# 12. Control Architecture — Rev 1

Rev 1 should require **no custom PCB**.

Recommended stack:

```text
                         Ethernet
                            |
                      +-----v------+
Photoreceiver ------->| Red Pitaya |
                      | STEMlab    |
                      | 125-14     |
                      +-----+------+
                            |
                        SPI + LDAC
                            |
                            v
                     EVAL-AD5754R
                   4 × 16-bit DAC
                            |
                       X / Y / Z
                            |
                            v
                        PDu150
                            |
                       X / Y / Z
                            |
                            v
                       Piezo stacks
```

## Red Pitaya

Recommended:

- STEMlab 125-14

Responsibilities:

- acquire photodiode signal
- generate real-time alignment state machine
- communicate with main PC over Ethernet
- implement lock-in / gradient estimation
- coordinate spiral search
- eventually run alignment loop in FPGA

## External DAC

Recommended:

- **Analog Devices EVAL-AD5754R**
- 4 synchronized channels
- 16-bit
- 0–10 V / ±10 V ranges
- serial/SPI interface
- LDAC synchronous update

This is preferable to using Red Pitaya's native DACs because:

- Red Pitaya only provides two high-speed DAC outputs
- three piezo axes are required
- the AD5754R gives proper synchronized XYZ output
- voltage range directly matches the PDu150 command input

---

# 13. Control Architecture — Rev 2

Rev 2 replaces the evaluation DAC board and loose wiring with a custom daughterboard.

Do not redesign the high-voltage amplifier initially.

Keep:

- Red Pitaya
- PDu150
- piezo stacks
- mechanical stage

Replace:

- EVAL-AD5754R
- loose wiring
- temporary power/interface wiring

with:

- custom 4-channel DAC/interface PCB

Recommended production controller:

```text
+-------------------------------------------+
| Fast Piezo Alignment Controller          |
|                                           |
| Red Pitaya                                |
|    |                                      |
|    +-- ADC <---- photoreceiver            |
|    |                                      |
|    +-- SPI --> AD5754R                    |
|                 |                         |
|                 +--> X command            |
|                 +--> Y command            |
|                 +--> Z command            |
|                                           |
|              PDu150-PCB                   |
|                 |                         |
+-----------------+-------------------------+
                  |
               XYZ piezo
```

## Rev-2 board should include

- AD5754R quad DAC
- 4 synchronized analog outputs
- hardware output clamps
- hardware watchdog
- PDu150 enable / disable control
- safe power-up default state
- Red Pitaya SPI connector
- analog command connectors
- photodiode input routing if desired
- clean analog ground architecture
- isolated or carefully partitioned HV section
- emergency piezo disable
- optional fourth DAC output exposed for future use

---

# 14. Rev-1 BOM

## Electronics and actuators

| Qty | Component | Recommended part | Approx. cost |
|---:|---|---|---:|
| 1 | FPGA/control | Red Pitaya STEMlab 125-14 | ~$490 |
| 1 | DAC eval board | Analog Devices EVAL-AD5754R | ~$130–160 |
| 1 | HV amplifier | PiezoDrive PDu150 | ~$413 |
| 1 | HV amp supply | PiezoDrive PS1 | ~$33 |
| 3 | Piezo actuator | PiezoDrive SA030318 | ~$339 total |
| 3 | Ball interface | PiezoDrive 3 mm ball end | ~$72 total |
| 1 | DAC supply | regulated 12–15 V supply | ~$20–30 |
| 1 | RP-to-DAC harness | SPI / LDAC cable | ~$10–20 |
| 3 | DAC-to-PDu analog cables | shielded pair | ~$15–30 |
| 1 | Electronics enclosure | metal | ~$50–100 |
| 3 | Piezo preload assemblies | screw + Belleville + seat | ~$50–100 |
| 1 | Fiber holder | lightweight custom | ~$50–150 |

### Electronics + piezo actuator subtotal

Approximately:

**$1.6k–$1.7k**

excluding fine-stage mechanics and coarse X stage.

## Direct flexure version

Estimated custom mechanics:

**$350–650**

Estimated complete fine aligner:

**~$2.1k–$2.7k**

## Amplified Y/Z version

Estimated custom mechanics:

**$500–900**

Estimated complete fine aligner:

**~$2.3k–$2.9k**

These are engineering budget numbers, not vendor quotes.

---

# 15. Rev-2 Custom PCB BOM

The mechanical system remains unchanged.

Suggested board-level BOM:

| Qty | Component | Approx. cost |
|---:|---|---:|
| 1 | AD5754RBREZ quad 16-bit DAC | ~$35–40 |
| 1 | input DC/DC or regulator | ~$10–20 |
| 1 | low-noise analog regulator/filter stage | ~$5–10 |
| 1 | hardware watchdog | ~$2–5 |
| 1 | PDu150 enable interface | <$2 |
| 1 | output clamp / protection network | ~$5 |
| 1 | Red Pitaya interface/header | ~$5–10 |
| 3–4 | analog output connectors | ~$5–10 |
| 3 | HV output connectors | ~$10–20 |
| — | decoupling/passives/filtering | ~$10–20 |
| 1 | 4-layer PCB | ~$20–50 |
| — | prototype assembly | ~$50–150 |

Prototype custom board target:

**~$150–250**

Rev 2 is primarily an integration, reliability, and manufacturability improvement rather than a large cost reduction.

---

# 16. Optical Alignment Control Strategy

The mechanical design should support continuous high-bandwidth analog trajectories.

## Initial search

Use Y/Z spiral search.

```text
Y(t) = Y0 + r(t) cos(ωt)
Z(t) = Z0 + r(t) sin(ωt)
```

The photodiode is sampled synchronously.

When optical power crosses threshold:

- stop increasing search radius
- reduce scan radius
- switch to local optimization

## Local optimization

Use simultaneous small-amplitude X/Y/Z dithers at separate frequencies.

```text
X(t) = X0 + Ax sin(2πfx t)
Y(t) = Y0 + Ay sin(2πfy t)
Z(t) = Z0 + Az sin(2πfz t)
```

Demodulate optical power at each frequency to estimate:

```text
dP/dX
dP/dY
dP/dZ
```

Update the DC center continuously toward maximum transmission.

This is effectively an extremum-seeking optical servo.

The mechanics should therefore prioritize:

- low moving mass
- high first resonance
- low parasitic motion
- repeatable flexure behavior
- no backlash

Absolute mechanical position accuracy is not the primary metric because optical power is the true optimization signal.

---

# 17. Initial Scan-Frequency Targets

## Direct XYZ version

Start testing around:

- **150–300 Hz** transverse scan frequency

Potentially higher depending on measured resonance and loaded fiber-head dynamics.

## Amplified Y/Z version

Start around:

- **75–150 Hz** transverse scan frequency

Do not operate close to the first flexure resonance.

Recommended initial rule:

- operating scan frequency < roughly 20–25% of the first relevant structural mode

Tune after experimental frequency-response measurement.

---

# 18. Acceptance Tests for Mechanical Prototype

Before optical integration, measure:

## Static travel

- X travel vs voltage
- Y travel vs voltage
- Z travel vs voltage
- amplification factor
- cross-axis motion

## Dynamic response

- swept-sine frequency response
- first resonance
- damping
- loaded vs unloaded response
- ring-down time

## Parasitic motion

Measure:

- pitch vs Y
- yaw vs Y
- pitch vs Z
- yaw vs Z
- X parasitic motion during Y/Z scanning

## Optical test

With fiber and waveguide:

1. acquire first light
2. measure spiral-search time
3. measure final optimization time
4. measure coupling repeatability
5. measure drift over time
6. compare direct and amplified bodies using the same electronics and piezo stacks

---

# 19. Decision Experiment

Build:

- **one direct-drive flexure body**
- **one amplified-Y/Z flexure body**

Use the exact same:

- three SA030318 piezos
- three ball interfaces
- PDu150
- Red Pitaya
- DAC board
- fiber chuck
- coarse X stage

Then compare:

| Metric | Direct | Amplified |
|---|---:|---:|
| First-light capture success | measure | measure |
| Average acquisition time | measure | measure |
| Final optimization time | measure | measure |
| Coupling repeatability | measure | measure |
| First structural resonance | measure | measure |
| Thermal drift | measure | measure |
| Cross-axis coupling | measure | measure |
| Sensitivity to die placement error | measure | measure |

Expected outcome:

- **Amplified Y/Z wins initially** because of its capture range.
- **Direct XYZ becomes superior** if the rest of the machine can eventually guarantee sufficiently accurate coarse registration.

---

# 20. Mechanical Design Summary

## Recommended Rev-1 head

```text
MISUMI LXM20 coarse X
        |
Direct piezo X (~20 µm)
        |
~4x amplified piezo Y
~4x amplified piezo Z
        |
Lightweight fiber holder
```

### Frozen components

- 3 × PiezoDrive SA030318
- 3 × 3 mm ball interfaces
- 1 × PiezoDrive PDu150
- 1 × PiezoDrive PS1
- Red Pitaya STEMlab 125-14
- Analog Devices EVAL-AD5754R for Rev 1

### Primary mechanical targets

- X loaded travel: ~16–22 µm
- Y loaded travel: ≥70 µm, target 80–90 µm
- Z loaded travel: ≥70 µm, target 80–90 µm
- Y/Z amplification: 3.5–4×
- X first mode: >1.5 kHz
- Y/Z first mode: >700 Hz, preferably >1 kHz
- fiber holder: <3 g
- moving mass: <10–20 g
- cross-axis coupling: <1% target
- 7075-T6 monolithic flexure
- wire EDM manufacturing
- 80–120 N piezo preload
- hard mechanical stops on every piezo axis

---

# 21. Notes for Mechanical Engineer

The highest-priority design objective is not maximum travel alone.

The stage should be optimized for:

1. sufficient capture range
2. high first structural resonance
3. low moving mass
4. low parasitic angular motion
5. low cross-axis coupling
6. safe piezo preload
7. hard-stop protection
8. manufacturability
9. compact fiber-holder geometry
10. repeatable mounting to the coarse X stage

The optical detector closes the true alignment loop, so:

- absolute stage accuracy is not critical
- backlash must effectively be zero
- dynamic response and stability matter more than metrology-grade positioning
- the flexure must support fast continuous scanning rather than discrete move-and-settle operation

---

# 22. Recommended Next Mechanical Deliverables

The mechanical design phase should produce:

1. direct-drive XYZ concept CAD
2. amplified-Y/Z + direct-X concept CAD
3. static FEA for both
4. modal FEA for both
5. predicted travel-vs-voltage
6. predicted amplification ratio
7. predicted parasitic pitch/yaw
8. estimated moving mass
9. piezo preload mechanism detail
10. hard-stop detail
11. fiber-holder interface
12. MISUMI coarse-stage mounting interface
13. manufacturing drawing suitable for wire EDM
14. prototype cost estimate

The amplified design should be prioritized first because it is the more robust starting point for automated die-to-die testing.

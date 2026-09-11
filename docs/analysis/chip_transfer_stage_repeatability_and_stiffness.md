# Chip transfer stage repeatability and stiffness analysis

Analysis performed 9 September 2026; report added to the repository 10 September 2026.

This is a first-pass linear-elastic sensitivity study, not a verified assembled-machine repeatability prediction or manufacturing release. Findings describe the source snapshots used for the study; later design revisions require reassessment. No project design files were changed for this study.

Supporting scripts, STEP snapshots, candidate variants and numerical results remain outside the repository in `C:\Users\MostafaHonariLatifpo\.codex\visualizations\2026\09\07\01a07a3e-75f9-7522-81d3-3bc74977c77e\stage_analysis`. Supporting filenames and reproduction instructions below refer to that directory. This report alone is archived here; reproducing it requires those supporting assets.

## Main findings

- The main arm weighs **0.672 kg** from actual CAD volume at 2700 kg/m³, rather than the 0.25 kg estimate in the source comments. The 30 mm arm is **0.853 kg**. More mass can worsen bearing deflection and settling; those effects are excluded from the part-only comparison.
- The current 3 mm vertical gripper bracket is the dominant analysed compliance in Y. Doubling that wall to 6 mm changes its calculated Y compliance from **15.78 to 2.29 µm/N**, for only **5.7 g** added mass. This is a candidate only: bolt lengths, access, actuator contact and collision clearance need review.
- Thickening the already-stiff arm has much less absolute benefit than stiffening this bracket.
- X/Z angular repeatability, joint behaviour and thermal drift remain unquantified. A strong part is not evidence of repeatability.
- Finger CAD has disconnected head geometry: far finger has 2 solids separated by 0.3 mm; near finger has 3 solids including a 0.3 mm head-to-bar gap and a 0.177 mm slot separating head pieces. They are each named as a single machined part, so they cannot be assumed continuous. No finger FEM was silently repaired or included.

## Geometry and methods

Default **vertical-gripper** station, not the optional horizontal variant. Station source functions were imported with bytecode disabled and output-folder creation redirected outside the repository. `main()` was not called. Exported geometries preserve the current holes, ribs, and source dimensions. Source SHA-256 hashes are in `geometry.json`; post-analysis equality: {'cad\\station\\model.py': True, 'cad\\gripper\\model.py': True, 'cad\\common\\__init__.py': True}.

X carriage reference: [-121.0, -165, 34.25] mm; Z carriage reference: [-64.0, -165, 90.5] mm; chip centre: [5, 3, 0.25] mm. Lever vectors to the chip: X [126.0, 168.0, -34.0] mm; Z [69.0, 168.0, -90.25] mm. These are carriage-face references, not manufacturer-certified bearing error reference planes. Changing the reference plane transforms translation/rotation covariance; supplied bearing data must be expressed consistently.

Solid FEM: Gmsh linear tetrahedral mesh, scikit-fem quadratic displacement elements, isotropic E=68.9 GPa, Poisson ratio 0.33, density=2700 kg/m³ (assumed representative 6061). All dimensions mm, forces N. Small-displacement linear elasticity. Sparse direct solve. Source `solve.py` contains exact boundary selection.

Boundary conditions:
- Arm: ideal fixed Z-carriage mounting face x=-64 mm. Output patch is the gripper contact rectangle on z=70 mm.
- Tower: entire bottom z=34.25 mm fixed; distributed output patch on Z-rail interface x=-91 mm, z≥44.25 mm. The real rail bolts and rail stiffness will distribute load differently.
- Gripper bracket: entire top face z=70 mm fixed; output patch on actuator face y=-2 mm, below z=64 mm.
- Output motion is a least-squares rigid-body fit extrapolated to chip centre. Loads are work-conjugate to this fit: each unit force acts at the chip through a distributed patch wrench, including the offset moment. The output surface is NOT constrained perfectly rigid. This approximation does not replace a model of the actual actuator contact and fasteners.

The analysis omits bearing compliance, bolt/contact compliance, thermal distortion, breadboard supports, SMC internal guide/hard-stop errors, finger compliance, contact/seating and dynamics. Clamps are optimistic; distributed output loading is an approximation, so these are not rigorous whole-system upper/lower bounds. Unit force at the chip is a controlled comparison load, not an assertion that hoses exert a particular force there. Real cable forces must be applied at their actual attachment locations with moments.

## Calculated compliance

Diagonal values below are displacement in the same direction as a unit force; full cross-axis matrices are in JSON.

| Part | X µm/N | Y µm/N | Z µm/N |
| --- | --- | --- | --- |
| arm | 0.349 | 0.143 | 0.267 |
| arm_30 | 0.179 | 0.095 | 0.137 |
| tower | 1.322 | 0.418 | 0.392 |
| gripper_bracket | 0.460 | 15.781 | 0.297 |
| gripper_bracket_6 | 0.221 | 2.294 | 0.107 |

Adding the three independent part compliances in series at the common chip reference gives current diagonal **[2.131, 16.342, 0.956] µm/N**; with 6 mm bracket **[1.892, 2.855, 0.766] µm/N**. This is only a serial surrogate for the three analysed parts, with rigid ideal connections between them. For a 0.1 N Y-force change at the chip, Y changes by **1.63 µm** versus **0.29 µm**. This is an elastic position change, not a statistical repeatability claim.

Self-gravity runs concern each individual part only, with the same clamps; they exclude downstream masses. Constant sag is principally an offset, not cycle-to-cycle scatter. The current load-check expression weight × vertical height is not a correct gravity moment; use vector r×F and separately account for inertia. The existing 0.45 kg-at-tip lump may still be conservative for some components, so a mass discrepancy does not by itself prove the entire moment is underestimated.

## Numerical verification

| Part | Maximum mesh size mm | ΔCxx | ΔCyy | ΔCzz |
| --- | --- | --- | --- | --- |
| arm | 5 → 3.5 | 5.79% | 4.42% | 6.51% |
| arm_30 | 5 → 3.5 | 3.34% | 4.06% | 4.59% |
| tower | 5 → 3.5 | 0.72% | 0.29% | 1.59% |
| gripper_bracket | 2 → 1.3 | 0.06% | 0.30% | 0.38% |
| gripper_bracket_6 | 2 → 1.3 | 0.83% | 0.46% | 2.19% |

Two meshes per analysed geometry, quadratic elements. Geometry refinement follows curved holes as well as maximum mesh size, so this is a practical convergence check, not proof of asymptotic convergence. All reported compliance matrices are positive definite and reciprocal; linear-solver relative residuals are below 1e-7. Boundary-condition/model uncertainty is larger than these mesh differences. Singular peak stresses at ideal clamps are not used for decisions. These tests do not validate joints or bearings.

## Angular sensitivity and conditional repeatability

For small angular changes δp=δt+δθ×r. If all six angular components of the X and Z carriages have independent equal standard deviation σθ, the chip's per-axis standard deviation is **[0.2564, 0.173, 0.2776] × σθ µm**, with σθ in µrad. Thus angular variation alone reaches 3σ=5 µm in Z at **6.00 µrad** per angular component; allocating only 2 µm of a 3σ Z budget permits **2.40 µrad**. These figures are requirements/sensitivities, not LX20 measured values. Correlation changes them.

Do not convert the vendor ±5 µm into a standard deviation without its test definition. The following scenarios are explicitly **invented sensitivity inputs**, not forecasts. Each assumes independent Gaussian contributions and reports per-axis 3σ (X,Y,Z); 3σ per axis is not 99.7% radial containment. Catalog backlash must not be double-counted with a measured bidirectional return distribution.

| Assumption scenario | Current: 3σ XYZ µm | 6 mm bracket: 3σ XYZ µm |
| --- | --- | --- |
| tight assumptions | 3.08, 2.38, 3.22 | 3.08, 2.17, 3.22 |
| intermediate assumptions | 5.54, 4.51, 5.76 | 5.54, 3.81, 5.75 |
| loose assumptions | 13.99, 10.64, 14.78 | 13.98, 9.47, 14.77 |

Exact scenario assumptions and covariance calculation are in `summary.json` and `summarize.py`. Gripper, joint and thermal terms are placeholders. These are placement-before-release scenarios at the nest; Y tray motion is not in that mechanical path. Pickup requires a separate tray/pocket transform and actual Y-carriage angular errors. Post-release chip position additionally requires a contact/seating model, not a simple addition of transport variance.

For equal hypothetical carriage rotational stiffness of 1000 / 10000 / 100000 N·m/rad, the resulting compliance is swept in `summary.json`; these values are NOT manufacturer specifications. Request angular repeatability and stiffness under our mass/moment loading. Static moment capacity does not establish angular stiffness.

## Thermal and implementation priorities

As a simple sensitivity, uniform free expansion over 168 mm of aluminium with assumed α=23.6 µm/(m·K) is **3.96 µm/K**. This is not total station drift: steel rails, offsets, joint constraints and the separate nest path can cancel or amplify it. A ±5 µm long-duration claim needs differential temperature measurements and an assembled thermal model.

Recommended order:
1. Resolve disconnected finger geometry in a reviewed future design revision; evaluate actual SMC actuator and force-limited hard-stop contact.
2. Prototype the **6 mm vertical gripper bracket or a gusseted equivalent**, retaining the 25 mm arm initially. The candidate thickness extends the wall by 3 mm in -Y; no full collision/manufacturing validation has been performed.
3. Correct the mass/centre-of-gravity load model, include cables/camera, then request or measure X/Z carriage angular behaviour and joint compliance. Validate the bearing reference plane used in the sensitivity model.
4. Model the breadboard on its actual bench supports and both transport/nest paths. Compare shortening offsets or the existing horizontal-gripper variant before increasing solid-arm mass.
5. Measure tool XYZ after representative settled cycles, with ≤1 µm measurement uncertainty target. Establish same-direction vs reversing scatter, cold/warm drift, and sensitivity to cable routing. Only then add chip transfers and seating measurements.

**Conclusion:** the machined structure has a credible improvement path, but this analysis does not establish assembled ±5 µm repeatability. The largest demonstrated part-level improvement is the gripper bracket; the largest remaining uncertainty is the complete bearing/joint/gripper/thermal path.

## Reproduction

Use existing `pythonEnvs/cad` for `python -B extract.py`; existing `pythonEnvs/pic-env` for `python -B solve.py PART H` and `python -B summarize.py`. Set OPENBLAS_NUM_THREADS=1 and OMP_NUM_THREADS=1. Output stays beside scripts; no packages were installed. Run pairs: arm/arm_30/tower at 5 and 3.5 mm; gripper_bracket/gripper_bracket_6 at 2 and 1.3 mm. Do not run repository station `main()` as part of this isolated workflow.

Sources: [MISUMI LX20 catalog](https://us.misumi-ec.com/pdf/fa/2019/2019_US_0526.pdf), [PI metrology definitions](https://www.pi-usa.us/en/tech-blog/metrology-standards-for-nano-positioning-motion-control). Geometry comes from this project's source snapshots; none of the unknown bearing/joint inputs are claimed to come from these sources.

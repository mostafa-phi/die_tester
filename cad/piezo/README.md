# Experimental APA60S XYZ alignment head

**P0: packaging and guided-axis concept, not ready for machining.** This folder preserves the Fusion design, the code that rebuilds it, verification evidence, and the next simulation steps. It is an experimental alternative to the NanoMax stages; it is **not yet part of the station assembly or the main `cad/build.py` dependency graph**.

The two original research notes and the user-supplied `APA60S.step` remain unchanged. The current design record is [docs/P0_review.md](docs/P0_review.md), including its limitations. The next engineering work is specified in [simulations/PLAN.md](simulations/PLAN.md).

## Files

| Path | Purpose |
|---|---|
| `parameters.json` | Generated guide leaf dimensions and explicitly provisional payload assumptions |
| `prepare_geometry.py` | Standard-library planar guide generation; checks connectedness and vendor identity |
| `fusion/design.py` | Native Fusion component, sketch and extrusion construction |
| `fusion/export_verify.py` | Nominal interference check and native/STEP export |
| `fusion/capture.py` | Assembly and isolated-axis viewport images |
| `fusion/validate_archive.py` | Reopens the exported standalone native archive and checks its body inventory |
| `build.py` | Reproducible orchestration and independent provenance check |
| `native/` | [XYZ Fusion archive](native/APA60S_XYZ_P0.f3d) and [standalone Z-axis archive](native/APA60S_Z_axis_P0.f3d) |
| `STEP/` | Exchange geometry for the same assembly and Z module |
| `renders/` | Actual Fusion viewport images |
| `reports/` | Nominal interference results, analytical screening and Fusion execution log |
| `generated/` | Planform data consumed by Fusion; regenerate rather than edit |
| `simulations/` | Planned cases, assumptions, release gates and analytical screening code |
| `simulations/fem_r01/` | [Single-axis FEM revision](simulations/fem_r01/README.md): filleted guide, gmsh + scikit-fem pipeline, mesh-converged stiffness, renders |
| `vendor.json` | Original STEP identity, measured envelope, source and unresolved interface requirements |
| `build_manifest.json` | SHA256 provenance of the current source and output set |
| `archive/P0_session/` | Original session exports and evidence, retained unchanged for comparison |

## Build and verify

Use Python 3.12 and the existing `cad` environment. The geometry preparation and checks use the standard library; the Fusion runner needs `mcp`. CadQuery/OCP remain pinned in `requirements.txt` for later CAD analysis, but are not imported by this build.

```powershell
# From the repository root, with the cad environment active:
python -B cad/piezo/build.py --prepare

# Enable Fusion's native MCP server and use the address shown in its settings:
python -B cad/piezo/build.py --fusion --url http://127.0.0.1:58871/mcp

# Read-only check; works without Fusion:
python -B cad/piezo/build.py --check
```

The URL above was the working address in the initial session; it is configurable and is not assumed by the code. `FUSION_MCP_URL` can be used instead of `--url`. The `adsk` modules come from Fusion itself and should not be installed into the external environment.

`--fusion` prepares geometry, creates a **new** Fusion document, builds and checks it, exports local archives/STEP, captures views, and writes the manifest only after success. It does not save to a cloud project or edit the existing station document. Finish active Fusion modeling commands before running it. Keep Fusion open for the duration.

`--prepare` alone is an iteration step and does not certify existing exports as current. The native scripts are launched through `build.py`; their root-path token is injected at runtime so no user-specific directory is stored in them.

The planar generator replaced an earlier CadQuery subprocess that crashed during OCP teardown on this Windows environment. It produces the same baseline areas (2050 and 1656 mm² before keeper stops/holes); successful preparation is now a normal clean process exit.

## Current result and limitations

- X outer / Y middle / Z inner; separate vendor APA60S on each guided axis.
- Body envelope: **84 × 70 × 106 mm**; including nose/fiber: **101 × 70 × 106 mm**.
- Optical center: 81 mm above the adapter underside.
- Nominal interference check: **25 bodies, no volumetric overlaps**, with touching faces excluded.
- Approximate structure plus actuators: **255 g**, excluding screws and wires, assuming aluminum for the non-vendor solids. This exceeds the initial mass preference and needs reduction.
- Guide stiffness along the driven axis: **0.0395 N/µm**, mesh-converged (1.29% at 1.2M dof),
  1.3% above the 0.039 N/µm beam estimate. Static FEA of the bare guide only — see
  [`simulations/fem_r01/`](simulations/fem_r01/README.md).
- **No loaded FEA, stress-converged result, full motion sweep, full station collision check,
  300 g load qualification, fatigue qualification or sub-second alignment validation has been
  performed.** The peak stress from the FEM revision is explicitly not converged.

The actuator coupling is currently a rigid placeholder. APA fastening details, leaf-root radii, final structural fasteners, covers, fiber clamps and wire loops are unfinished. The 0.25 mm keeper gap is a concept, not validated crash protection.

The clean repository rebuild removes six obsolete hidden stop placeholders from the original session archive and builds the intended integral keeper stops into the guides. That explains the changed body count and mass. The original exports are preserved in `archive/P0_session/`; current files in `native/` and `STEP/` match the repository code. `STEP/APA60S_Z_guide_P0.step` is the current guide alone for meshing, including the keeper geometry.

`parameters.json` drives leaf length and thickness when rebuilt. The present Fusion sketch has fixed planform entities; its nominal leaf parameters are references. `guide_depth` drives extrusion depth, but changing it requires redesign of mounting heights. The generator intentionally rejects a depth other than 6 mm until that dependency is implemented.

## Coordinates and integration

This standalone head uses **X optical, Y lateral, Z up**, as in the research brief. The active station uses **X die length, Y optical, Z up**. The component has not silently changed the station convention. An explicit placement transform and checks against `cad/common` must be added before station integration.

The 300 g payload is a desired maximum capacity, not the normal working holder. The 20 g normal-payload value is a provisional analysis case. The actual holder mass, dimensions, COM and roll requirement are still needed.

## Continuing development

1. Review and refine the single-axis coupling, holder and mounting interfaces.
2. Run the meshing, static, modal and convergence work in the simulation plan.
3. Bench-test the single-axis module before qualifying the full XYZ assembly.
4. Reduce mass/height and integrate into the station with full motion clearance checks.
5. When adopted as a station component, add the canonical station-frame wrapper, per-part manufacturing outputs, and integration in the main build/manifest. Until then, run **both** the main and piezo checks when sharing changes.

Keep source, native archives, STEP, renders, verification reports and this folder's manifest together. The main station manifest does not validate this experimental folder. Do not hand-update hashes to conceal stale models.

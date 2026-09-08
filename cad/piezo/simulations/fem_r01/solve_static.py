"""Single-axis guide compliance: 1 N on the APA patch, guide roots fixed.

Measures the FEM R01 Z guide's stiffness along its driven axis (local Y) and
sweeps mesh density so the number comes with convergence evidence rather than a
single plot. Units throughout are mm, N, MPa; displacements come out in mm.

    python -B solve_static.py                 # default three-density sweep
    python -B solve_static.py --sizes 0.30    # one density, for iteration

Boundary conditions come from the split faces `geometry.py` left in the STEP,
selected by the boxes recorded in geometry_report.json - not by hand-picking:

    fixture   16 x 6 mm plate edge at y = -25      fully fixed
    force     2.5 x 5 mm patch at y = -9.5         1 N total, +Y

What this is NOT: no gravity, no payload, no APA stiffness, no modal result.
It is the guide's own compliance, to be compared against the 0.039 N/um beam
estimate in screening.py. The R0.5 roots and the bonded-land surrogate both
stiffen the part relative to that beam model, so a converged result somewhat
above 0.039 N/um is the expected outcome, not a discrepancy.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import skfem
from skfem import Basis, FacetBasis, Functional, LinearForm
from skfem.helpers import ddot, eye, sym_grad, trace
from skfem.models.elasticity import lame_parameters, linear_elasticity

import mesh as meshing

try:
    import pypardiso
except ImportError:  # scipy's SuperLU stalls above ~100k dofs on this problem
    pypardiso = None


def _direct_solver():
    """MKL PARDISO when available; scipy otherwise, which limits usable density."""
    if pypardiso is None:
        return None, "scipy SuperLU (install pypardiso for finer meshes)"

    def solve_pardiso(A, b):
        return pypardiso.spsolve(A.tocsr(), b)

    return solve_pardiso, "MKL PARDISO (pypardiso)"

HERE = Path(__file__).resolve().parent
REPORT = HERE / "geometry_report.json"
WORK = HERE / "work"           # gitignored scratch for .msh files
RESULTS = HERE / "static_r01.json"

DEFAULT_SIZES = (0.40, 0.30, 0.22)
TOTAL_FORCE_N = 1.0
FORCE_AXIS = 1                 # local Y, the driven axis


def material() -> dict:
    """Elastic constants as assigned in Fusion, converted to mm-N-MPa."""
    report = json.loads(REPORT.read_text())
    props = {p["name"]: p for p in report["material_properties"]}

    youngs, poisson, density = props["Young's Modulus"], props["Poisson's Ratio"], props["Density"]
    assert youngs["units"] == "Kilopascal", youngs["units"]
    assert density["units"] == "KilogramPerCubicMeter", density["units"]

    rho_kg_m3 = float(density["value"])
    return {
        "name": report["material"],
        "E_MPa": float(youngs["value"]) / 1000.0,
        "nu": float(poisson["value"]),
        "rho_kg_m3": rho_kg_m3,
        "rho_t_mm3": rho_kg_m3 * 1e-12,
    }


def _in_box(points: np.ndarray, box: dict, tol: float = 0.05) -> np.ndarray:
    """True where facet midpoints fall inside a recorded patch box."""
    x, y, z = points
    xlo, xhi = box["x"]
    zlo, zhi = box["z"]
    return (
        (x > xlo - tol) & (x < xhi + tol)
        & (np.abs(y - box["y"]) < tol)
        & (z > zlo - tol) & (z < zhi + tol)
    )


def solve_one(h_fine: float, mat: dict) -> tuple[dict, dict]:
    """Mesh at one density, apply the 1 N case and return (measurements, fields).

    The second return value carries the mesh, basis, solution and per-element von
    Mises so `figures.py` can draw the same solve without repeating it.
    """
    msh = WORK / f"guide_r01_h{h_fine:.2f}.msh"
    t0 = time.time()
    mesh_info = meshing.build(msh, h_fine)
    t_mesh = time.time() - t0

    boxes = meshing.patch_boxes()
    m = skfem.MeshTet.load(msh)
    element = skfem.ElementVector(skfem.ElementTetP2())
    basis = Basis(m, element)

    force_facets = m.facets_satisfying(lambda p: _in_box(p, boxes["force"]), boundaries_only=True)
    fixture_facets = m.facets_satisfying(lambda p: _in_box(p, boxes["fixture"]), boundaries_only=True)
    if force_facets.size == 0 or fixture_facets.size == 0:
        raise RuntimeError(
            f"Patch selection failed: {force_facets.size} force, {fixture_facets.size} fixture facets"
        )

    force_basis = FacetBasis(m, element, facets=force_facets)
    area = Functional(lambda w: 1.0 + 0.0 * w.x[0]).assemble(force_basis)
    traction = TOTAL_FORCE_N / area

    @LinearForm
    def load(v, w):
        return traction * v[FORCE_AXIS]

    lam, mu = lame_parameters(mat["E_MPa"], mat["nu"])
    t0 = time.time()
    K = linear_elasticity(lam, mu).assemble(basis)
    f = load.assemble(force_basis)
    fixed = basis.get_dofs(facets=fixture_facets).all()
    solver, _ = _direct_solver()
    system = skfem.condense(K, f, D=fixed)
    x = skfem.solve(*system) if solver is None else skfem.solve(*system, solver=solver)
    t_solve = time.time() - t0

    @Functional
    def mean_component(w):
        return w["u"][FORCE_AXIS]

    displacement = mean_component.assemble(force_basis, u=force_basis.interpolate(x)) / area

    # Peak von Mises sampled at volume quadrature points. It under-reads the true
    # peak, but consistently, so it is a fair convergence metric.
    u = basis.interpolate(x)
    strain = sym_grad(u)
    stress = 2.0 * mu * strain + lam * eye(trace(strain), 3)
    deviatoric = stress - eye(trace(stress) / 3.0, 3)
    von_mises_qp = np.sqrt(1.5 * ddot(deviatoric, deviatoric))
    von_mises = float(np.max(von_mises_qp))

    state = {"mesh": m, "basis": basis, "x": x, "von_mises_qp": von_mises_qp,
             "force_facets": force_facets, "fixture_facets": fixture_facets}
    return {
        **mesh_info,
        "dofs": int(basis.N),
        "force_facets": int(force_facets.size),
        "fixture_facets": int(fixture_facets.size),
        "patch_area_mm2": float(area),
        "traction_MPa": float(traction),
        "displacement_um": float(displacement) * 1000.0,
        "stiffness_N_per_um": float(TOTAL_FORCE_N / (abs(displacement) * 1000.0)),
        "peak_von_mises_MPa": von_mises,
        "mesh_seconds": round(t_mesh, 1),
        "solve_seconds": round(t_solve, 1),
    }, state


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=float, nargs="+", default=list(DEFAULT_SIZES),
                        help="leaf-region element sizes in mm, coarse to fine")
    args = parser.parse_args()

    mat = material()
    _, solver_name = _direct_solver()
    print(f"{mat['name']}: E = {mat['E_MPa']:.0f} MPa, nu = {mat['nu']}, "
          f"rho = {mat['rho_kg_m3']:.0f} kg/m^3")
    print(f"linear solver: {solver_name}")

    runs = []
    for h in args.sizes:
        print(f"\n--- h_fine = {h:.2f} mm")
        run, _ = solve_one(h, mat)
        runs.append(run)
        print(f"  {run['linear_tets']:>9,} tets   {run['dofs']:>9,} dofs   "
              f"mesh {run['mesh_seconds']}s  solve {run['solve_seconds']}s")
        print(f"  displacement {run['displacement_um']:.4f} um   "
              f"k = {run['stiffness_N_per_um']:.4f} N/um   "
              f"peak vM {run['peak_von_mises_MPa']:.1f} MPa")

    for coarse, fine in zip(runs, runs[1:]):
        for key in ("displacement_um", "peak_von_mises_MPa"):
            change = abs(fine[key] - coarse[key]) / abs(coarse[key]) * 100.0
            fine[f"change_vs_coarser_{key}_pct"] = round(change, 2)

    converged = (len(runs) > 1
                 and runs[-1].get("change_vs_coarser_displacement_um_pct", 100.0) < 5.0)
    results = {
        "case": "single-axis guide compliance, 1 N on the APA patch",
        "status": "converged" if converged else "not_converged",
        "convergence_gate": "<5% change in patch displacement between densities (PLAN.md section 2)",
        "excludes": ["gravity", "payload", "APA stiffness", "modal", "station integration"],
        "source_step": "guide_r01.step",
        "linear_solver": solver_name,
        "material": mat,
        "total_force_N": TOTAL_FORCE_N,
        "force_axis": "local Y (driven axis)",
        "runs": runs,
    }
    RESULTS.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print(f"\nstatus: {results['status']}")
    if len(runs) > 1:
        print(f"finest vs next: {runs[-1]['change_vs_coarser_displacement_um_pct']}% displacement, "
              f"{runs[-1]['change_vs_coarser_peak_von_mises_MPa_pct']}% peak stress")
    print(f"wrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

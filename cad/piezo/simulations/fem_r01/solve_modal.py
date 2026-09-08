"""Unloaded modal frequencies of the FEM R01 Z guide, roots fixed.

    python -B solve_modal.py                # two densities, first 10 modes
    python -B solve_modal.py --sizes 0.45 --modes 6

Same fixture as the static case (the 16 x 6 mm patch at y = -25); no payload, no
APA, no mounting compliance. Read this as the guide's own dynamics, an upper
bound on the assembled stage: `PLAN.md` section 3 is explicit that the assembled
first mode needs actuator stiffness, holder inertia and mount compliance, and
that the bare APA resonance must not be quoted as the stage resonance. The
300 Hz target in cases.json is a *loaded* target and is not what this measures.

Units are mm, N, tonne, s, so eigenvalues come out in (rad/s)^2.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import scipy.sparse.linalg as spl
import skfem
from skfem import Basis, BilinearForm
from skfem.helpers import dot
from skfem.models.elasticity import lame_parameters, linear_elasticity

import mesh as meshing
import solve_static as S

HERE = Path(__file__).resolve().parent
WORK = HERE / "work"
RESULTS = HERE / "modal_r01.json"

DEFAULT_SIZES = (0.60, 0.45)
DEFAULT_MODES = 10
# Shift just below the first expected mode keeps the shift-invert factorisation
# away from the singular point without biasing the returned frequencies.
SHIFT_HZ = 50.0


def mass_form(rho_t_mm3: float) -> BilinearForm:
    @BilinearForm
    def mass(u, v, w):
        return rho_t_mm3 * dot(u, v)

    return mass


def modes_at(h_fine: float, mat: dict, n_modes: int) -> dict:
    msh = WORK / f"guide_r01_h{h_fine:.2f}.msh"
    t0 = time.time()
    mesh_info = meshing.build(msh, h_fine)
    t_mesh = time.time() - t0

    boxes = meshing.patch_boxes()
    m = skfem.MeshTet.load(msh)
    element = skfem.ElementVector(skfem.ElementTetP2())
    basis = Basis(m, element)

    fixture = m.facets_satisfying(lambda p: S._in_box(p, boxes["fixture"]), boundaries_only=True)
    if fixture.size == 0:
        raise RuntimeError("Fixture patch not found in the mesh")

    lam, mu = lame_parameters(mat["E_MPa"], mat["nu"])
    t0 = time.time()
    K = linear_elasticity(lam, mu).assemble(basis)
    M = mass_form(mat["rho_t_mm3"]).assemble(basis)
    fixed = basis.get_dofs(facets=fixture).all()
    free = np.setdiff1d(np.arange(basis.N), fixed)
    Kc = K[free][:, free].tocsr()
    Mc = M[free][:, free].tocsr()

    sigma = (2.0 * np.pi * SHIFT_HZ) ** 2
    shifted = (Kc - sigma * Mc).tocsr()

    # Shift-invert calls the inverse once per Lanczos iteration, so the
    # factorisation must be reused. A dedicated PyPardisoSolver caches it for a
    # matrix it has already seen; calling pypardiso.spsolve here instead would
    # refactorise on every iteration.
    if S.pypardiso is None:
        op_inv = spl.LinearOperator(shifted.shape, matvec=spl.factorized(shifted.tocsc()))
    else:
        pardiso = S.pypardiso.PyPardisoSolver()
        pardiso.factorize(shifted)

        def apply_inverse(b):
            # ARPACK probes the operator with integer vectors; PARDISO wants f64.
            return pardiso.solve(shifted, np.asarray(b, dtype=np.float64))

        op_inv = spl.LinearOperator(shifted.shape, matvec=apply_inverse, dtype=np.float64)

    values = spl.eigsh(Kc, k=n_modes, M=Mc, sigma=sigma, which="LM",
                       OPinv=op_inv, return_eigenvectors=False)
    t_solve = time.time() - t0

    frequencies = np.sort(np.sqrt(np.abs(values))) / (2.0 * np.pi)
    return {
        **mesh_info,
        "dofs": int(basis.N),
        "free_dofs": int(free.size),
        "frequencies_Hz": [round(float(f), 2) for f in frequencies],
        "solve_seconds": round(t_solve, 1),
        "mesh_seconds": round(t_mesh, 1),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=float, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--modes", type=int, default=DEFAULT_MODES)
    args = parser.parse_args()

    mat = S.material()
    _, solver_name = S._direct_solver()
    print(f"{mat['name']}: E = {mat['E_MPa']:.0f} MPa, rho = {mat['rho_kg_m3']:.0f} kg/m^3")
    print(f"linear solver: {solver_name}\n")

    runs = []
    for h in args.sizes:
        print(f"--- h_fine = {h:.2f} mm", flush=True)
        run = modes_at(h, mat, args.modes)
        runs.append(run)
        print(f"  {run['dofs']:,} dofs, solve {run['solve_seconds']}s")
        print("  f (Hz): " + ", ".join(f"{f:.1f}" for f in run["frequencies_Hz"]), flush=True)

    if len(runs) > 1:
        coarse, fine = runs[-2], runs[-1]
        drift = [abs(b - a) / a * 100.0
                 for a, b in zip(coarse["frequencies_Hz"], fine["frequencies_Hz"])]
        fine["change_vs_coarser_pct"] = [round(d, 2) for d in drift]
        converged = max(drift) < 5.0
    else:
        converged = False

    results = {
        "case": "unloaded modal, guide alone, fixture patch fixed",
        "status": "converged" if converged else "not_converged",
        "convergence_gate": "<5% drift in every reported frequency between densities",
        "excludes": ["payload", "APA stiffness and mass", "mount compliance", "prestress"],
        "not_the_stage_resonance": (
            "Guide-only modes. The 300 Hz target in cases.json is a loaded first mode "
            "and requires actuator, holder and mount properties (PLAN.md section 3)."
        ),
        "material": mat,
        "linear_solver": solver_name,
        "runs": runs,
    }
    RESULTS.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nstatus: {results['status']}\nwrote {RESULTS.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

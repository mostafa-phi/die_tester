"""Modal analysis of the parallel YZ platform, actuators as springs.

    python -B solve_modal.py                       # bare plate, default densities
    python -B solve_modal.py --loaded --sizes 0.7  # holder block on the platform

Frame back face fixed outside the leg region; both APA60S as 1.7 N/um axial
springs between their pads plus half their mass on each pad. The bare plate is
also solved without the springs, from the same factorisation, to show what the
actuators contribute. Each mode is labelled by the platform's rigid-body motion
in it (translation X/Y/Z, rotation about X/Y/Z) or as "local" when the platform
barely moves (a leaf or stage mode).

This is the loaded modal PLAN.md section 3 asks for, minus mount compliance and
the real holder; the 300 Hz target applies to the loaded, sprung result.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

import fe_common as F
import mesh as meshing

HERE = Path(__file__).resolve().parent
DEFAULT_SIZES = (0.70, 0.55)
DEFAULT_MODES = 10
SHIFT_HZ = 30.0
LABELS = ("X", "Y", "Z", "rot X (roll)", "rot Y (pitch)", "rot Z (yaw)")


def classify(model: F.Model, vec: np.ndarray, rep: dict) -> dict:
    ref = np.array([rep["parameters"]["b"], 0.0, 0.0])
    t, theta = model.rigid_fit(vec, ref)
    lever = rep["parameters"]["a_p"]
    measure = np.concatenate([np.abs(t), np.abs(theta) * lever])
    peak = float(np.max(np.abs(vec)))
    platform_share = float(np.max(measure) / peak) if peak else 0.0
    label = LABELS[int(np.argmax(measure))] if platform_share > 0.1 else "local (leaf/stage)"
    return {"label": label, "platform_share": round(platform_share, 3),
            "t_normalised": (t / peak).round(3).tolist(),
            "theta_x_lever_normalised": (theta * lever / peak).round(3).tolist()}


def solve_modes(model: F.Model, Kc, Mc, U, k, n_modes: int, rep: dict) -> tuple[list, list]:
    sigma = (2.0 * np.pi * SHIFT_HZ) ** 2
    base = F.Factorised((Kc - sigma * Mc).tocsr())
    op = F.Sprung(base, U, k) if U is not None else base

    def apply_inverse(b):
        return op.solve(np.asarray(b, dtype=np.float64))

    op_inv = spl.LinearOperator(Kc.shape, matvec=apply_inverse, dtype=np.float64)
    if U is None:
        K_eff = Kc
    else:
        # U is dense but supported only on the pad DOFs; keep the rank-2
        # update sparse (a dense outer product would be n x n).
        Us = sp.csc_matrix(U)
        K_eff = (Kc + Us @ sp.diags(k) @ Us.T).tocsr()
    values, vectors = spl.eigsh(K_eff, k=n_modes, M=Mc, sigma=sigma, which="LM", OPinv=op_inv)
    order = np.argsort(values)
    freqs = np.sqrt(np.abs(values[order])) / (2.0 * np.pi)
    labels = [classify(model, model.expand(vectors[:, i]), rep) for i in order]
    return [round(float(f), 1) for f in freqs], labels


def modes_at(h: float, rep: dict, n_modes: int, loaded: bool) -> dict:
    tag = "_loaded" if loaded else ""
    msh = F.WORK / f"parallel_yz_r01{tag}_h{h:.2f}.msh"
    t0 = time.time()
    mesh_info = meshing.build(msh, h, loaded=loaded)
    model = F.Model(msh, rep, loaded=loaded)
    K, M = model.assemble(with_mass=True)
    Kc, Mc = model.reduce(K), model.reduce(M)
    vectors = model.actuator_vectors()
    U = np.column_stack([vectors["Y"], vectors["Z"]])[model.free]
    k = np.array([rep["actuator"]["k_N_per_um"] * 1e3] * 2)
    t_setup = time.time() - t0

    out = {**mesh_info, "dofs": int(model.N), "setup_seconds": round(t_setup, 1)}
    t0 = time.time()
    f_sprung, l_sprung = solve_modes(model, Kc, Mc, U, k, n_modes, rep)
    out["sprung"] = {"frequencies_Hz": f_sprung, "modes": l_sprung}
    if not loaded:
        f_bare, l_bare = solve_modes(model, Kc, Mc, None, None, n_modes, rep)
        out["springless"] = {"frequencies_Hz": f_bare, "modes": l_bare}
    out["solve_seconds"] = round(time.time() - t0, 1)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=float, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--modes", type=int, default=DEFAULT_MODES)
    parser.add_argument("--loaded", action="store_true", help="fiber holder block on the platform")
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    results_path = F.ROOT / ("modal_loaded_r01.json" if args.loaded else "modal_r01.json")

    runs = []
    for h in args.sizes:
        print(f"--- h_fine = {h:.2f} mm{' loaded' if args.loaded else ''}", flush=True)
        run = modes_at(h, rep, args.modes, args.loaded)
        runs.append(run)
        print(f"  {run['dofs']:,} dofs  setup {run['setup_seconds']}s  solve {run['solve_seconds']}s")
        for key in ("sprung", "springless"):
            if key in run:
                print(f"  {key}: " + ", ".join(
                    f"{f:.0f} ({m['label']})" for f, m in zip(run[key]["frequencies_Hz"], run[key]["modes"])),
                    flush=True)

    if len(runs) > 1:
        a, b = runs[-2]["sprung"]["frequencies_Hz"], runs[-1]["sprung"]["frequencies_Hz"]
        drift = [round(abs(y - x) / x * 100.0, 2) for x, y in zip(a, b)]
        runs[-1]["sprung"]["change_vs_coarser_pct"] = drift
        converged = max(drift) < 5.0
    else:
        converged = False

    results = {
        "variant": args.variant or "R01 baseline",
        "case": ("holder block on the platform, " if args.loaded else "bare plate, ")
                + "frame back face fixed, both APA60S as axial springs with half their mass on each pad",
        "status": "converged" if converged else "not_converged",
        "convergence_gate": "<5% drift in every sprung frequency between densities",
        "excludes": ["mount compliance", "real holder", "actuator off-axis stiffness and internal modes",
                     "prestress", "wiring"],
        "runs": runs,
    }
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nstatus: {results['status']}\nwrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

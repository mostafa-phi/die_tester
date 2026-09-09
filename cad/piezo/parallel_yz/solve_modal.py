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
STRUT_L = 15.0          # wire strut free length (mm) for the --strut what-if
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


def modes_at(h: float, rep: dict, n_modes: int, loaded: bool, strut_k_N_per_um: float = 0.0) -> dict:
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
    if strut_k_N_per_um:
        # Wire struts along X from the platform's back face to ground: three
        # Ø d wires of length l at radius 8 around the fiber hole, each an
        # axial spring E A / l on X and a lateral spring 12 E I / l^3 on Y and Z
        # at the nearest back-face node. strut_k_N_per_um is the TOTAL axial
        # stiffness; d follows from it for l = STRUT_L (music wire, E = 200 GPa).
        E_w = 200e3
        n_w, l_w, r_w = 3, STRUT_L, 8.0
        area = strut_k_N_per_um * 1e3 * l_w / (n_w * E_w)          # mm^2 per wire
        d_w = 2 * np.sqrt(area / np.pi)
        k_ax = E_w * area / l_w
        k_lat = 12 * E_w * (np.pi * d_w ** 4 / 64) / l_w ** 3
        cols, ks = [], []
        back = np.abs(model.mesh.p[0]) < 0.05
        for ang in (90.0, 210.0, 330.0):
            y, z = r_w * np.cos(np.radians(ang)), r_w * np.sin(np.radians(ang))
            d2 = np.where(back, (model.mesh.p[1] - y) ** 2 + (model.mesh.p[2] - z) ** 2, np.inf)
            node = int(np.argmin(d2))
            for comp, kk in ((0, k_ax), (1, k_lat), (2, k_lat)):
                e = np.zeros(model.N)
                e[model.basis.nodal_dofs[comp, node]] = 1.0
                cols.append(e[model.free])
                ks.append(kk)
        U = np.column_stack([U, *cols])
        k = np.concatenate([k, ks])
        print(f"  struts: {n_w} x dia {d_w:.2f} x {l_w:.0f} mm, axial {k_ax / 1e3:.2f} N/um each, "
              f"lateral {k_lat / 1e3:.4f} N/um each ({3 * k_lat / 1e3:.4f} total)", flush=True)
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
    parser.add_argument("--strut", type=float, default=0.0, metavar="K",
                        help="what-if: axial X struts from the platform to ground, total K N/um "
                             "(results go to modal_loaded_strut_r01.json, nothing else changes)")
    parser.add_argument("--partial", type=Path, default=None,
                        help="write the single-density run to this JSON instead of the result file "
                             "(one process per density; combine with --merge)")
    parser.add_argument("--merge", type=Path, nargs="+", default=None,
                        help="partial run files (coarse to fine) to combine into the result file")
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    results_path = F.ROOT / ("modal_loaded_r01.json" if args.loaded else "modal_r01.json")
    if args.strut:
        results_path = F.ROOT / "modal_loaded_strut_r01.json"

    if args.merge:
        runs = [json.loads(p.read_text(encoding="utf-8")) for p in args.merge]
        runs.sort(key=lambda r: -r["h_fine_mm"])
    else:
        runs = []
        for h in args.sizes:
            print(f"--- h_fine = {h:.2f} mm{' loaded' if args.loaded else ''}", flush=True)
            run = modes_at(h, rep, args.modes, args.loaded, args.strut)
            runs.append(run)
            print(f"  {run['dofs']:,} dofs  setup {run['setup_seconds']}s  solve {run['solve_seconds']}s")
            for key in ("sprung", "springless"):
                if key in run:
                    print(f"  {key}: " + ", ".join(
                        f"{f:.0f} ({m['label']})" for f, m in zip(run[key]["frequencies_Hz"], run[key]["modes"])),
                        flush=True)
    if args.partial:
        args.partial.parent.mkdir(parents=True, exist_ok=True)
        args.partial.write_text(json.dumps(runs[-1], indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.partial}")
        return 0

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

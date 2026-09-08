"""Static response of the parallel YZ platform: stiffness, coupling, parasitics.

    python -B solve_static.py                    # default density sweep -> static_r01.json
    python -B solve_static.py --sizes 0.7        # one density while iterating

Per density, on the bare plate (no payload):
  * a 1 N pair on each driven leg's pads, the way the actuator pushes, with the
    frame's back face fixed outside the leg region. The pad-to-pad compliance is
    the guide stiffness the actuator sees; the platform's rigid-body motion gives
    the compliance matrix, the cross-axis coupling, the parasitic rotations and
    the fiber-tip error at full stroke;
  * the same with both actuators present as 1.7 N/um axial springs (Woodbury,
    same factorisation) - the as-built response.
On the loaded mesh (the fiber holder block on the platform):
  * gravity, both springs present: sag, pitch and tip drop.

Signs: a leg's actuator "extends" when its pads move apart, which pushes the
platform toward the opposite leg (-Y for the +Y leg, -Z for the +Z leg).
Displacements are reported along the leg axis, positive toward that motion.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
from skfem.helpers import ddot, eye, sym_grad, trace

import fe_common as F
import mesh as meshing

HERE = Path(__file__).resolve().parent
DEFAULT_SIZES = (0.70, 0.55)
LEG_AXIS = {"Y": 1, "Z": 2}
LEG_SIGN = {"Y": -1.0, "Z": -1.0}          # platform motion on extension, along the axis


def von_mises_peak(model: F.Model, x: np.ndarray) -> tuple[float, np.ndarray]:
    u = model.basis.interpolate(x)
    strain = sym_grad(u)
    lam, mu = model.mat.lam(model.basis.global_coordinates().value), model.mat.mu(model.basis.global_coordinates().value)
    stress = 2.0 * mu * strain + lam * eye(trace(strain), 3)
    dev = stress - eye(trace(stress) / 3.0, 3)
    vm = np.sqrt(1.5 * ddot(dev, dev))
    return float(np.max(vm)), vm


def platform_response(model: F.Model, x: np.ndarray, rep: dict) -> dict:
    ref = np.array([rep["parameters"]["b"], 0.0, 0.0])
    t, theta = model.rigid_fit(x, ref)
    tip = np.array(rep["tip"]) - ref
    u_tip = t + np.cross(theta, tip)
    return {"t_um": (t * 1e3).tolist(), "theta_urad": (theta * 1e6).tolist(),
            "tip_um": (u_tip * 1e3).tolist()}


def leg_case(model: F.Model, x: np.ndarray, a: np.ndarray, leg: str, rep: dict) -> dict:
    """Numbers per 1 N pad pair for one leg, from a displacement field."""
    axis = LEG_AXIS[leg]
    resp = platform_response(model, x, rep)
    pad_gap = float(a @ x)                            # stage minus frame, along the axis
    main = resp["t_um"][axis] * LEG_SIGN[leg]         # platform along the leg, positive on extension
    others = [resp["t_um"][i] for i in range(3) if i != axis]
    tip_off = [resp["tip_um"][i] for i in range(3) if i != axis]
    return {
        "pad_relative_um": pad_gap * 1e3,
        "platform_along_axis_um": main,
        "platform_off_axis_um": others,
        "tip_off_axis_um": tip_off,
        "theta_urad": resp["theta_urad"],
        "platform_over_pad": main / abs(pad_gap * 1e3),
    }


def solve_density(h: float, rep: dict) -> dict:
    act = rep["actuator"]
    k_apa = act["k_N_per_um"] * 1e3                   # N/mm
    out = {"h_fine_mm": h}

    # ---- bare plate: unit pairs, pure and sprung -------------------------------
    msh = F.WORK / f"parallel_yz_r01_h{h:.2f}.msh"
    t0 = time.time()
    out["mesh"] = meshing.build(msh, h, loaded=False)
    model = F.Model(msh, rep, loaded=False)
    out["dofs"] = int(model.N)
    out["mesh_seconds"] = round(time.time() - t0, 1)

    t0 = time.time()
    K, _ = model.assemble(with_mass=False)
    vectors = model.actuator_vectors()
    U = np.column_stack([vectors["Y"], vectors["Z"]])[model.free]
    base = F.Factorised(model.reduce(K))
    X_pure = model.expand(base.solve(-U))             # columns: Y pair, Z pair
    sprung = F.Sprung(base, U, np.array([k_apa, k_apa]))
    X_sprung = model.expand(sprung.solve(-U))
    out["solve_seconds"] = round(time.time() - t0, 1)

    out["cases"] = {}
    for j, leg in enumerate(("Y", "Z")):
        a = vectors[leg]
        pure = leg_case(model, X_pure[:, j], a, leg, rep)
        k_guide = 1.0 / abs(pure["pad_relative_um"])
        as_built = leg_case(model, X_sprung[:, j], a, leg, rep)
        peak, _ = von_mises_peak(model, X_pure[:, j])
        strokes = {}
        for label, free in act["free_stroke_um"].items():
            pad = free * act["k_N_per_um"] / (act["k_N_per_um"] + k_guide)
            strokes[label] = {"pad_um": pad, "platform_um": pad * pure["platform_over_pad"]}
        # Parasitics scale with platform travel; quote them at the nominal stroke.
        scale = strokes["nominal"]["platform_um"] / as_built["platform_along_axis_um"]
        force_at_stroke = k_guide * strokes["nominal"]["pad_um"]
        out["cases"][leg] = {
            "k_guide_N_per_um": k_guide,
            "per_N_pure": pure,
            "per_N_as_built": as_built,
            "loaded_stroke": strokes,
            "at_nominal_stroke": {
                "platform_off_axis_um": [v * scale for v in as_built["platform_off_axis_um"]],
                "tip_off_axis_um": [v * scale for v in as_built["tip_off_axis_um"]],
                "theta_urad": [v * scale for v in as_built["theta_urad"]],
                "coupling_pct": [abs(v) / strokes["nominal"]["platform_um"] * 100.0
                                 for v in [as_built["platform_off_axis_um"][i] * scale for i in range(2)]],
                "guide_force_N": force_at_stroke,
                "peak_von_mises_MPa": peak * force_at_stroke,
            },
            "peak_von_mises_per_N_MPa": peak,
        }
    # Cross-check: the other leg's pad should not move when this leg drives.
    out["cases"]["other_pad_per_um_of_platform"] = {
        "Y_drive_moves_Z_pad": float(vectors["Z"] @ X_sprung[:, 0]) / abs(out["cases"]["Y"]["per_N_as_built"]["platform_along_axis_um"] * 1e-3),
        "Z_drive_moves_Y_pad": float(vectors["Y"] @ X_sprung[:, 1]) / abs(out["cases"]["Z"]["per_N_as_built"]["platform_along_axis_um"] * 1e-3),
    }

    # ---- loaded plate: gravity with both springs ---------------------------------
    msh_l = F.WORK / f"parallel_yz_r01_loaded_h{h:.2f}.msh"
    t0 = time.time()
    out["mesh_loaded"] = meshing.build(msh_l, h, loaded=True)
    model_l = F.Model(msh_l, rep, loaded=True)
    K_l, _ = model_l.assemble(with_mass=False)
    vec_l = model_l.actuator_vectors()
    U_l = np.column_stack([vec_l["Y"], vec_l["Z"]])[model_l.free]
    base_l = F.Factorised(model_l.reduce(K_l))
    sprung_l = F.Sprung(base_l, U_l, np.array([k_apa, k_apa]))
    f_g_full = model_l.gravity()
    f_g = f_g_full[model_l.free]
    x_g = model_l.expand(sprung_l.solve(f_g))
    resp = platform_response(model_l, x_g, rep)
    out["gravity_loaded"] = {
        "dofs": int(model_l.N),
        "total_weight_N": float(-f_g_full.sum()),
        "platform_t_um": resp["t_um"], "theta_urad": resp["theta_urad"], "tip_um": resp["tip_um"],
        "apa_axial_force_N": {leg: float(k_apa * (vec_l[leg] @ x_g)) for leg in ("Y", "Z")},
        "seconds": round(time.time() - t0, 1),
    }
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=float, nargs="+", default=list(DEFAULT_SIZES))
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    results_path = F.ROOT / "static_r01.json"
    rep = F.report()

    runs = []
    for h in args.sizes:
        print(f"--- h_fine = {h:.2f} mm", flush=True)
        run = solve_density(h, rep)
        runs.append(run)
        print(f"  {run['mesh']['linear_tets']:,} tets  {run['dofs']:,} dofs  "
              f"mesh {run['mesh_seconds']}s  solve {run['solve_seconds']}s", flush=True)
        for leg in ("Y", "Z"):
            c = run["cases"][leg]
            n = c["at_nominal_stroke"]
            print(f"  {leg}: k_guide {c['k_guide_N_per_um']:.4f} N/um  "
                  f"stroke {c['loaded_stroke']['minimum']['platform_um']:.1f}/"
                  f"{c['loaded_stroke']['nominal']['platform_um']:.1f} um (min/nom)  "
                  f"coupling {n['coupling_pct'][0]:.3f}% / {n['coupling_pct'][1]:.3f}%  "
                  f"tip off-axis {n['tip_off_axis_um'][0]:+.3f}/{n['tip_off_axis_um'][1]:+.3f} um  "
                  f"vM {n['peak_von_mises_MPa']:.1f} MPa", flush=True)
        g = run["gravity_loaded"]
        print(f"  gravity (loaded): platform {g['platform_t_um'][2]:+.3f} um Z, "
              f"pitch {g['theta_urad'][1]:+.2f} urad, tip {g['tip_um'][2]:+.3f} um Z  "
              f"[{g['seconds']}s]", flush=True)

    for coarse, fine in zip(runs, runs[1:]):
        for leg in ("Y", "Z"):
            a, b = coarse["cases"][leg]["k_guide_N_per_um"], fine["cases"][leg]["k_guide_N_per_um"]
            fine["cases"][leg]["change_vs_coarser_k_pct"] = round(abs(b - a) / a * 100.0, 2)
            a, b = coarse["cases"][leg]["peak_von_mises_per_N_MPa"], fine["cases"][leg]["peak_von_mises_per_N_MPa"]
            fine["cases"][leg]["change_vs_coarser_vM_pct"] = round(abs(b - a) / a * 100.0, 2)
    converged = len(runs) > 1 and all(
        runs[-1]["cases"][leg]["change_vs_coarser_k_pct"] < 5.0 for leg in ("Y", "Z"))

    results = {
        "concept": rep["concept"],
        "variant": args.variant or "R01 baseline",
        "status": "converged" if converged else "not_converged",
        "convergence_gate": "<5% change in pad-to-pad stiffness between densities (PLAN.md section 2)",
        "excludes": ["actuator off-axis stiffness", "mount compliance below the frame's back face",
                     "fatigue", "station integration", "real holder geometry"],
        "sign_convention": __doc__.split("Signs:")[1].strip(),
        "runs": runs,
    }
    results_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(f"\nstatus: {results['status']}\nwrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Record plots from the result files: convergence curves and mode shapes.

    python -B figures_results.py           # renders/convergence_r01.png, renders/modes_r01.png

Convergence reads static_r01.json / modal_r01.json / modal_loaded_r01.json as
written by the solvers. The mode shapes re-solve the loaded plate at a coarse
density (the shapes are insensitive to it; the frequencies in the captions are
the coarse ones and say so) and draw the first four modes exaggerated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import scipy.sparse as sp  # noqa: E402
import scipy.sparse.linalg as spl  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

import fe_common as F  # noqa: E402
import figures as FIG  # noqa: E402
import mesh as meshing  # noqa: E402
import solve_modal as SM  # noqa: E402

HERE = Path(__file__).resolve().parent
MODE_SIZE_MM = 1.2
N_SHAPES = 4


def convergence(path: Path):
    static = json.loads((F.ROOT / "static_r01.json").read_text())
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), dpi=160)

    dofs = [r["dofs"] for r in static["runs"]]
    for leg, marker in (("Y", "o"), ("Z", "s")):
        axes[0].plot(dofs, [r["cases"][leg]["k_guide_N_per_um"] for r in static["runs"]],
                     marker=marker, label=f"{leg} leg")
        axes[1].plot(dofs, [r["cases"][leg]["at_nominal_stroke"]["peak_von_mises_MPa"] for r in static["runs"]],
                     marker=marker, label=f"{leg} leg")
    axes[0].set_ylabel("guide stiffness at the pads (N/um)")
    axes[0].set_title("static: k_guide")
    axes[1].set_ylabel("peak von Mises at nominal stroke (MPa)")
    axes[1].set_title("static: stress peak (quadrature-sampled)")

    for name, label, marker in (("modal_r01.json", "bare plate", "o"),
                                ("modal_loaded_r01.json", "holder on the platform", "s")):
        p = F.ROOT / name
        if not p.exists():
            continue
        modal = json.loads(p.read_text())
        axes[2].plot([r["dofs"] for r in modal["runs"]],
                     [r["sprung"]["frequencies_Hz"][0] for r in modal["runs"]], marker=marker, label=label)
    axes[2].set_ylabel("first mode, actuators as springs (Hz)")
    axes[2].set_title("modal: first mode")
    for ax in axes:
        ax.set_xlabel("quadratic dofs")
        ax.set_xscale("log")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)
    fig.suptitle("parallel YZ R01 - mesh convergence", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def mode_shapes(path: Path, h: float, rep: dict):
    msh = F.WORK / f"parallel_yz_r01_loaded_h{h:.2f}.msh"
    meshing.build(msh, h, loaded=True)
    model = F.Model(msh, rep, loaded=True)
    K, M = model.assemble(with_mass=True)
    Kc, Mc = model.reduce(K), model.reduce(M)
    vectors = model.actuator_vectors()
    U = np.column_stack([vectors["Y"], vectors["Z"]])[model.free]
    k = np.array([rep["actuator"]["k_N_per_um"] * 1e3] * 2)

    sigma = (2.0 * np.pi * SM.SHIFT_HZ) ** 2
    base = F.Factorised((Kc - sigma * Mc).tocsr())
    op = F.Sprung(base, U, k)
    op_inv = spl.LinearOperator(Kc.shape, matvec=lambda b: op.solve(np.asarray(b, dtype=np.float64)),
                                dtype=np.float64)
    Us = sp.csc_matrix(U)
    K_eff = (Kc + Us @ sp.diags(k) @ Us.T).tocsr()
    values, vecs = spl.eigsh(K_eff, k=N_SHAPES, M=Mc, sigma=sigma, which="LM", OPinv=op_inv)
    order = np.argsort(values)
    freqs = np.sqrt(np.abs(values[order])) / (2 * np.pi)

    mesh = model.mesh
    fig = plt.figure(figsize=(14, 11), dpi=140)
    for i, idx in enumerate(order):
        full = model.expand(vecs[:, idx])
        label = SM.classify(model, full, rep)["label"]
        nodal = FIG.nodal_field(model, full)
        amp = 6.0 / np.max(np.abs(nodal))          # 6 mm peak on the picture
        points = mesh.p + amp * nodal
        mag = np.linalg.norm(nodal, axis=0)
        polys, facets = FIG.boundary_polys(mesh, points)
        facet_mag = mag[mesh.facets[:, facets]].mean(axis=0)
        ax = fig.add_subplot(2, 2, i + 1, projection="3d")
        norm = plt.Normalize(vmin=0, vmax=float(facet_mag.max()))
        ax.add_collection3d(Poly3DCollection(polys, facecolors=plt.get_cmap("viridis")(norm(facet_mag)),
                                             edgecolor="none"))
        FIG._style(ax, points, f"mode {i + 1}: {freqs[i]:.0f} Hz  ({label})\n"
                               f"holder on the platform, actuators as springs; h = {h:.1f} mm")
    fig.suptitle("parallel YZ R01 - first modes, exaggerated (frequencies from this coarse solve; "
                 "converged values in modal_loaded_r01.json)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=float, default=MODE_SIZE_MM)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    RENDERS = F.ROOT / "renders"
    RENDERS.mkdir(exist_ok=True)
    convergence(RENDERS / "convergence_r01.png")
    print("wrote renders/convergence_r01.png", flush=True)
    mode_shapes(RENDERS / "modes_r01.png", args.size, F.report())
    print("wrote renders/modes_r01.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

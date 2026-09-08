"""Render the parallel YZ concept: profile, mesh, deformed shapes, stress.

    python -B figures.py            # h = 0.9 mm solve -> renders/*.png + static_r01.vtu

Matplotlib only, headless. Re-solves the bare plate at one density with both
actuator springs present (the as-built response), so the pictures and the
numbers in static_r01.json come from the same code path. The PNGs are for the
README; open the .vtu in ParaView to inspect the interior and the stress peaks.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import meshio  # noqa: E402
import numpy as np  # noqa: E402
import skfem  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

import fe_common as F  # noqa: E402
import mesh as meshing  # noqa: E402
import solve_static as S  # noqa: E402

HERE = Path(__file__).resolve().parent
FIGURE_SIZE_MM = 0.9
DEFORM_SCALE = 300.0
VIEW = (28, -55)


def boundary_polys(mesh, points):
    facets = mesh.boundary_facets()
    tri = mesh.facets[:, facets]
    return points[:, tri].transpose(2, 1, 0), facets


def _style(ax, points, title):
    ax.set_title(title, fontsize=10)
    ax.view_init(elev=VIEW[0], azim=VIEW[1])
    ax.set_axis_off()
    lo, hi = points.min(axis=1), points.max(axis=1)
    pad = (hi - lo) * 0.02
    ax.set_xlim(lo[0] - pad[0], hi[0] + pad[0])
    ax.set_ylim(lo[1] - pad[1], hi[1] + pad[1])
    ax.set_zlim(lo[2] - pad[2], hi[2] + pad[2])
    ax.set_box_aspect(tuple(hi - lo))


def figure_profile(mesh, path: Path, rep: dict):
    """The EDM profile: back-face boundary triangles projected onto the YZ plane."""
    facets = mesh.facets_satisfying(lambda x: np.abs(x[0]) < 0.05, boundaries_only=True)
    tri = mesh.facets[:, facets]
    fig, ax = plt.subplots(figsize=(8, 8), dpi=160)
    ax.tripcolor(mesh.p[1], mesh.p[2], tri.T, facecolors=np.ones(tri.shape[1]),
                 cmap="Greys", vmin=0, vmax=2, edgecolors="none")
    for name, pad in rep["pads"].items():
        axis = "y" if "y" in pad and np.isscalar(pad["y"]) else "z"
        other = "z" if axis == "y" else "y"
        if axis == "y":
            ax.plot([pad["y"], pad["y"]], pad["z"], color="#c0392b", lw=3)
        else:
            ax.plot(pad["y"], [pad["z"], pad["z"]], color="#c0392b", lw=3)
    p = rep["parameters"]
    ax.annotate("APA Y", (rep["derived"]["y_in1"] + 7.5, -20), color="#c0392b", ha="center")
    ax.annotate("APA Z", (-20, rep["derived"]["y_in1"] + 7.5), color="#c0392b", ha="center")
    ax.set_aspect("equal")
    ax.set_xlabel("Y (mm)")
    ax.set_ylabel("Z (mm)")
    ax.set_title(f"EDM profile, viewed along the optical axis\n"
                 f"leaves {p['t']} x {p['L']} mm, depth {p['b']} mm; red = APA pad lands", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def figure_mesh(mesh, path: Path, info: str):
    polys, _ = boundary_polys(mesh, mesh.p)
    fig = plt.figure(figsize=(9, 8), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    ax.add_collection3d(Poly3DCollection(polys, facecolor="#c9d3dd", edgecolor="#33414f", linewidths=0.1))
    _style(ax, mesh.p, f"parallel YZ R01 - surface mesh\n{info}")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def figure_field(mesh, points, values, path: Path, title: str, label: str, cmap: str):
    polys, facets = boundary_polys(mesh, points)
    fig = plt.figure(figsize=(9, 8), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    norm = plt.Normalize(vmin=float(values.min()), vmax=float(values.max()))
    ax.add_collection3d(Poly3DCollection(polys, facecolors=plt.get_cmap(cmap)(norm(values)), edgecolor="none"))
    _style(ax, points, title)
    mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    fig.colorbar(mappable, ax=ax, shrink=0.6, pad=0.02).set_label(label, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def nodal_field(model: F.Model, x: np.ndarray) -> np.ndarray:
    scalar = model.basis.with_element(skfem.ElementTetP1())
    u = model.basis.interpolate(x)
    return np.vstack([scalar.project(u[i]) for i in range(3)])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=float, default=FIGURE_SIZE_MM)
    parser.add_argument("--scale", type=float, default=DEFORM_SCALE)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    RENDERS = F.ROOT / "renders"
    RENDERS.mkdir(exist_ok=True)
    rep = F.report()
    k_apa = rep["actuator"]["k_N_per_um"] * 1e3

    msh = F.WORK / f"parallel_yz_r01_h{args.size:.2f}.msh"
    print(f"meshing and solving at h = {args.size:.2f} mm ...", flush=True)
    info = meshing.build(msh, args.size, loaded=False)
    model = F.Model(msh, rep, loaded=False)
    K, _ = model.assemble(with_mass=False)
    vectors = model.actuator_vectors()
    U = np.column_stack([vectors["Y"], vectors["Z"]])[model.free]
    base = F.Factorised(model.reduce(K))
    sprung = F.Sprung(base, U, np.array([k_apa, k_apa]))
    X = model.expand(sprung.solve(-U))
    mesh = model.mesh
    print(f"  {info['linear_tets']:,} tets, {model.N:,} dofs", flush=True)

    figure_profile(mesh, RENDERS / "profile_r01.png", rep)
    figure_mesh(mesh, RENDERS / "mesh_r01.png",
                f"h = {args.size:.2f} mm   {info['linear_tets']:,} tets   {model.N:,} quadratic dofs")

    fields = {}
    for j, leg in enumerate(("Y", "Z")):
        nodal = nodal_field(model, X[:, j])
        mag_um = np.linalg.norm(nodal, axis=0) * 1e3
        facets = mesh.boundary_facets()
        facet_disp = mag_um[mesh.facets[:, facets]].mean(axis=0)
        t, _ = model.rigid_fit(X[:, j], np.array([rep["parameters"]["b"], 0, 0]))
        figure_field(mesh, mesh.p + args.scale * nodal, facet_disp,
                     RENDERS / f"displacement_{leg}_r01.png",
                     f"{leg} actuator: 1 N pad pair, both APAs as springs\n"
                     f"deformation exaggerated {args.scale:.0f}x   platform {abs(t[j + 1]) * 1e3:.3f} um",
                     "|u| (um)", "viridis")
        fields[leg] = nodal
        if leg == "Y":
            peak, vm = S.von_mises_peak(model, X[:, j])
            per_element = vm.mean(axis=1)
            facet_vm = per_element[mesh.f2t[0, facets]]
            figure_field(mesh, mesh.p + args.scale * nodal, facet_vm, RENDERS / "von_mises_Y_r01.png",
                         "Von Mises, Y actuator 1 N pair (surface, per element)\n"
                         "convergence in static_r01.json", "von Mises (MPa)", "magma")
            vm_cells = per_element

    meshio.Mesh(mesh.p.T, [("tetra", mesh.t.T)],
                point_data={"u_Y_mm": fields["Y"].T, "u_Z_mm": fields["Z"].T},
                cell_data={"von_mises_Y_MPa": [vm_cells]}).write(RENDERS / "static_r01.vtu")
    for name in sorted(p.name for p in RENDERS.glob("*_r01.*")):
        print(f"  wrote renders/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

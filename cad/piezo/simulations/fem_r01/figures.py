"""Render the FEM R01 static case: mesh, displacement and von Mises.

    python -B figures.py                # h = 0.60 mm, three PNGs into renders/

Draws the boundary of the same solve `solve_static.py` runs, so the pictures and
`static_r01.json` cannot disagree. Matplotlib only - no VTK or off-screen GL, so
this works headless. A .vtu is written alongside for ParaView, where the
interior and the stress peaks are actually inspectable; the PNGs are for the
README, not for reading stress values off.
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

import solve_static as S  # noqa: E402

HERE = Path(__file__).resolve().parent
RENDERS = HERE / "renders"
FIGURE_SIZE_MM = 0.60
DEFORM_SCALE = 400.0            # 25 um of motion is invisible at true scale
VIEW = (22, -62)                # elev, azim: shows the leaves and the post


def boundary_polys(mesh, points):
    """Triangles of the outer surface, as (nfacets, 3, 3) vertex coordinates."""
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
    # True proportions, not a cube: the guide is 70 x 50 x 23 mm and a cube
    # aspect would waste most of the frame on empty space above it.
    ax.set_box_aspect(tuple(hi - lo))


def figure_mesh(mesh, path: Path, info: str):
    polys, _ = boundary_polys(mesh, mesh.p)
    fig = plt.figure(figsize=(9, 7), dpi=160)
    ax = fig.add_subplot(111, projection="3d")
    collection = Poly3DCollection(polys, facecolor="#c9d3dd", edgecolor="#33414f",
                                  linewidths=0.12, alpha=1.0)
    ax.add_collection3d(collection)
    _style(ax, mesh.p, f"FEM R01 Z guide - surface mesh\n{info}")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def figure_field(mesh, points, values, path: Path, title: str, label: str, cmap: str):
    """Colour the deformed boundary by a per-facet value."""
    polys, facets = boundary_polys(mesh, points)
    fig = plt.figure(figsize=(9, 7), dpi=160)
    ax = fig.add_subplot(111, projection="3d")

    norm = plt.Normalize(vmin=float(values.min()), vmax=float(values.max()))
    colours = plt.get_cmap(cmap)(norm(values))
    collection = Poly3DCollection(polys, facecolors=colours, edgecolor="none")
    ax.add_collection3d(collection)
    _style(ax, points, title)

    mappable = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    bar = fig.colorbar(mappable, ax=ax, shrink=0.6, pad=0.02)
    bar.set_label(label, fontsize=9)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--size", type=float, default=FIGURE_SIZE_MM,
                        help="leaf-region element size for the rendered solve")
    parser.add_argument("--scale", type=float, default=DEFORM_SCALE,
                        help="displacement exaggeration factor")
    args = parser.parse_args()

    RENDERS.mkdir(exist_ok=True)
    mat = S.material()
    print(f"solving at h = {args.size:.2f} mm for figures ...", flush=True)
    result, state = S.solve_one(args.size, mat)
    mesh, basis, x = state["mesh"], state["basis"], state["x"]
    print(f"  {result['linear_tets']:,} tets, {result['dofs']:,} dofs, "
          f"{result['displacement_um']:.3f} um, k = {result['stiffness_N_per_um']:.4f} N/um",
          flush=True)

    # Nodal displacement components, projected P2 -> P1 so they sit on vertices.
    scalar_basis = basis.with_element(skfem.ElementTetP1())
    interpolated = basis.interpolate(x)
    nodal = np.vstack([scalar_basis.project(interpolated[i]) for i in range(3)])
    magnitude_um = np.linalg.norm(nodal, axis=0) * 1000.0
    deformed = mesh.p + args.scale * nodal

    # Per-element von Mises, then per-boundary-facet via the owning element.
    per_element = state["von_mises_qp"].mean(axis=1)
    facets = mesh.boundary_facets()
    facet_vm = per_element[mesh.f2t[0, facets]]
    facet_disp = magnitude_um[mesh.facets[:, facets]].mean(axis=0)

    info = (f"h = {args.size:.2f} mm   {result['linear_tets']:,} tets   "
            f"{result['dofs']:,} quadratic dofs")
    figure_mesh(mesh, RENDERS / "mesh_r01.png", info)
    figure_field(mesh, deformed, facet_disp, RENDERS / "displacement_r01.png",
                 f"Displacement under 1 N on the APA patch\n"
                 f"deformation exaggerated {args.scale:.0f}x   "
                 f"k = {result['stiffness_N_per_um']:.4f} N/um",
                 "|u| (um)", "viridis")
    figure_field(mesh, deformed, facet_vm, RENDERS / "von_mises_r01.png",
                 "Von Mises under 1 N (surface, per element)\n"
                 "NOT mesh-converged - see README",
                 "von Mises (MPa)", "magma")

    cells = [("tetra", mesh.t.T)]
    meshio.Mesh(mesh.p.T, cells,
                point_data={"displacement_mm": nodal.T, "displacement_um": magnitude_um},
                cell_data={"von_mises_MPa": [per_element]}
                ).write(RENDERS / "static_r01.vtu")

    for name in ("mesh_r01.png", "displacement_r01.png", "von_mises_r01.png", "static_r01.vtu"):
        print(f"  wrote renders/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

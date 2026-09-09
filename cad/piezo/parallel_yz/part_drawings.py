"""One drawing per manufactured part of a shim-mode variant (pic-env, matplotlib).

    python -B part_drawings.py --variant r05      -> variants/<v>/manufacturing/part_*.png

Each sheet shows the part's profile (its back face, projected on the plate
plane), the overall dimensions, the through-holes and, for the body pieces, a
hole-by-hole statement of how the tool reaches each feature once the four
pieces are machined as separate parts. Geometry facts come from the part STEP
that export_manufacturing.py wrote; the notes come from geometry_report.json.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import gmsh  # noqa: E402

HERE = Path(__file__).resolve().parent


def face_outline(step: Path):
    """Loops of the face at minimum X of every solid in the STEP, as polylines
    in the YZ plane, plus the bounding box - via gmsh's OCC kernel."""
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.occ.importShapes(str(step))
    gmsh.model.occ.synchronize()
    loops = []
    bb_all = gmsh.model.getBoundingBox(-1, -1)
    for dim, tag in gmsh.model.getEntities(2):
        bb = gmsh.model.getBoundingBox(dim, tag)
        if abs(bb[3] - bb[0]) > 1e-3 or abs(bb[0] - bb_all[0]) > 1e-3:
            continue                                     # not the back face
        gmsh.option.setNumber("Mesh.MeshSizeMax", 0.5)
        gmsh.option.setNumber("Mesh.MeshSizeMin", 0.2)
        gmsh.model.mesh.generate(1)
        for (cdim, ctag) in gmsh.model.getBoundary([(dim, tag)], oriented=False):
            nodes, coords, _ = gmsh.model.mesh.getNodes(cdim, ctag, includeBoundary=True)
            pts = np.array(coords).reshape(-1, 3)
            # order the sampled nodes along the curve
            t = [gmsh.model.getParametrization(cdim, ctag, p)[0] for p in pts]
            order = np.argsort(t)
            loops.append(pts[order][:, 1:])
    gmsh.finalize()
    return loops, bb_all


def sheet(step: Path, out: Path, title: str, notes: list[str], dims: list[str]):
    loops, bb = face_outline(step)
    fig = plt.figure(figsize=(11.7, 8.3), dpi=150)
    ax = fig.add_axes([0.05, 0.08, 0.55, 0.84])
    for pts in loops:
        ax.plot(pts[:, 0], pts[:, 1], color="#333", lw=0.8)
    ax.set_aspect("equal")
    pad = 4.0
    ax.set_xlim(bb[1] - pad, bb[4] + pad)
    ax.set_ylim(bb[2] - pad, bb[5] + pad)
    ax.set_xlabel("Y (mm)")
    ax.set_ylabel("Z (mm)")
    ax.grid(True, alpha=0.25)
    ax.set_title(title, fontsize=10)
    w, h = bb[4] - bb[1], bb[5] - bb[2]
    ax.annotate("", (bb[1], bb[2] - pad * 0.6), (bb[4], bb[2] - pad * 0.6),
                arrowprops=dict(arrowstyle="<->", color="#1f4e79", lw=0.9))
    ax.text((bb[1] + bb[4]) / 2, bb[2] - pad * 0.6 + 0.4, f"{w:.2f}", ha="center", fontsize=8, color="#1f4e79")
    ax.annotate("", (bb[4] + pad * 0.6, bb[2]), (bb[4] + pad * 0.6, bb[5]),
                arrowprops=dict(arrowstyle="<->", color="#1f4e79", lw=0.9))
    ax.text(bb[4] + pad * 0.6 + 0.4, (bb[2] + bb[5]) / 2, f"{h:.2f}", va="center", rotation=90, fontsize=8, color="#1f4e79")
    fig.text(0.63, 0.90, "DIMENSIONS", fontsize=9, weight="bold", va="top")
    fig.text(0.63, 0.87, "\n".join(dims), fontsize=7.2, va="top", family="monospace", linespacing=1.4)
    fig.text(0.63, 0.87 - 0.022 * (len(dims) + 2), "NOTES", fontsize=9, weight="bold", va="top")
    fig.text(0.63, 0.87 - 0.022 * (len(dims) + 3.2), "\n".join(notes), fontsize=7.2, va="top",
             family="monospace", linespacing=1.4)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--variant", required=True)
    args = parser.parse_args()
    root = HERE / "variants" / args.variant
    man = root / "manufacturing"
    rep = json.loads((root / "geometry_report.json").read_text(encoding="utf-8"))
    p, d, sh, r = rep["parameters"], rep["derived"], rep["shim"], rep["r02"]
    body = rep["material"]["name"]
    gap = d["pocket1"] - d["y_in1"] - 2 * p["pad_boss"]
    rr = p["r_root"]
    common = [
        f"Material {body}, {p['b']:.1f} thick, faces ground flat 0.02 / parallel 0.02.",
        f"Profile: CNC, internal corner radius R{rr:.1f} (dia {2 * rr:.0f} cutter, {p['b'] / (2 * rr):.0f}:1).",
        "Profile +/-0.05 unless noted; deburr all edges; bare finish, ultrasonic clean.",
        "Leaf ledges and notches: faces flat 0.01 (they set the leaf planes); no burrs.",
    ]
    parts = {
        "frame": ("frame (1 off)", [
            f"outer {d['box'][1] - d['box'][0]:.1f} x {d['box'][3] - d['box'][2]:.1f}",
            f"actuator pockets {d['pocket1'] - d['pocket0']:.2f} x {2 * d['pocket_h']:.1f} (2), land gap {gap:.2f} +0.05/-0",
            f"4 x dia {p['bolt']:.1f} thru; {len(r['wire_ties'])} x dia {r['wire_tie']:.0f} thru (wire ties)",
            f"{len(r['windows'])} lightening windows, walls {p.get('lightening_wall', 0):.2f}",
        ], [
            "HOLES (tool access, this piece machined alone):",
            "  bolt and wire-tie holes: thru X, from the face - open.",
            "  actuator pad screw: M2 clearance + c'bore along the leg axis, drilled from",
            "    the OUTER EDGE of the plate (external face) - open.",
            "  pad land: raised 0.2, milled from the pocket side - open (pocket is through).",
            "  leaf anchor notches: through-profile slots; NO taps (tabs are bonded).",
        ]),
        "stage": ("input stage (2 off, second one flipped)", [
            f"{d['w_in']:.2f} x {2 * p['h_in']:.1f} x {p['b']:.1f}",
            f"guide leaf notches {p['bar_t'] + p['t']:.2f} wide x {p['tab'] + rr:.1f} deep at y = {d['guide_y'][0] - d['y_in0']:.2f} and {d['guide_y'][1] - d['y_in0'] + p['t']:.2f} from the inner face",
            f"coupler ledges {p['tab'] + rr:.1f} long at z = +/-{p['s_c']:.1f}",
            "pad land 2.5 x 5 raised 0.2 on the outer face; stop tongue 2.0 wide on the inner face",
        ], [
            "HOLES: M2 clearance dia 2.2 along the leg axis, c'bore dia 4.0 x 2.2 from the",
            "  INNER face - open (external face of the loose part). No other holes.",
            "The Z stage is the Y stage turned over (all features are through or",
            "  symmetric about mid-thickness).",
        ]),
        "platform": ("platform with arms (1 off)", [
            f"{2 * p['a_p']:.0f} sq + arms {d['arm']:.1f} long toward each stage; {p['b']:.1f} thick",
            f"coupler ledges {p['tab'] + rr:.1f} long on each arm at z = +/-{p['s_c']:.1f}",
            f"fiber hole dia {p['fiber_hole']:.0f} thru, {r['fiber_chamfer']:.1f} x 45 both faces",
            f"2 x M2 tapped {r['holder_tap_depth']:.0f} deep on the FRONT face at Y +/-{r['holder_tap_y']:.1f}",
            "stop fork: two 1.0 posts, slot 2.6 between them (4.0 long) on each arm",
        ], [
            "HOLES: fiber hole thru X; holder taps from the front face - both open.",
            "Fork slot 2.6 wide: dia 2 cutter, R1.0 at its bottom corners is intended.",
        ]),
        "clamp_bar": ("clamp bar (16 off, bonded)", [
            f"{p['b']:.0f} x {p['tab']:.1f} x {p['bar_t']:.1f}, {body}",
            f"all four long edges chamfered {p['bar_edge_r']:.1f}: the edge toward the free leaf is the root",
        ], [
            "No holes (every tab is bonded; the bar is bonded on top as backup).",
            "Saw from 8 x 2 strip and chamfer in one fixture; edges consistent to 0.05.",
        ]),
        "shim_leaf": ("shim leaf (8 off + 2 spare)", [
            f"{p['leaf_material']['name']}, {p['t']:.2f} +/-0.005",
            f"{p['b']:.0f} x {p['L'] + 2 * p['tab']:.1f} rectangle; free length {p['L']:.1f} set by the bars",
        ], [
            "No holes. Shear or laser cut; deburr; never scratch the middle 8.5 mm.",
            "Keep flat: store between card.",
        ]),
        "base_plate": ("base plate (1 off)", [
            f"{d['box'][1] - d['box'][0]:.1f} x {d['box'][3] - d['box'][2]:.1f} x {rep['base']['t']:.0f}",
            f"central opening {rep['base']['opening_mm'][0]:.0f} x {rep['base']['opening_mm'][1]:.0f}; windows behind both pockets",
            f"4 x dia {p['bolt']:.1f} on the body bolt pattern",
        ], [
            "Any aluminium. Flat 0.02 where the frame sits (it is the mount reference).",
            "A stiffness model of the mount; replace by the station's real mount if one exists.",
        ]),
        "assembly_jig": ("assembly jig (1 off)", [
            "8 mm plate, 3 mm pockets locating platform+arms and both stages (0.02 clearance)",
            f"4 x dia {p['bolt'] - 0.5:.1f} press-fit dowel seats on the frame's bolt pattern",
        ], [
            "Sets leaf alignment and free length during bonding; see BONDING.md.",
            "Pockets flat 0.01; pocket walls are the datum for the whole stage: +/-0.02.",
        ]),
    }
    for key, (title, dims, notes) in parts.items():
        step = man / f"{key}.step"
        if not step.exists():
            print(f"skip {key}: no {step.name}")
            continue
        out = man / f"part_{key}.png"
        sheet(step, out, f"{args.variant.upper()} - {title}", common + notes, dims)
        print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

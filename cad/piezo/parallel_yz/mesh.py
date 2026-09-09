"""Mesh the parallel YZ plate with gmsh, refined inside the leaf boxes.

`model.py` records every leaf as an axis-aligned box in geometry_report.json, so
refinement needs no face hunting: one gmsh Box field per leaf (h_fine inside,
grown by `near` to catch the root fillets, blending to h_coarse over `far`),
combined with a Min field. The payload block of the loaded STEP is fragmented
against the plate so the two solids share a conformal interface.

Normally imported by solve_static.py / solve_modal.py, which call build() as
they need meshes. A mesh is cached: build() writes a sidecar <msh>.json with a
key made of the STEP file's hash and the size parameters, and returns the
recorded description without running gmsh when the key matches. So meshes can
be made ahead of time, all densities in parallel:

    python -B mesh.py --variant r05 --sizes 0.70 0.55 0.45 0.9 1.2 --jobs 10
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import gmsh

import fe_common as F


def report() -> dict:
    return F.report()


def _cache_key(step: Path, h_fine: float, h_coarse: float, near: float, far: float, loaded: bool) -> str:
    digest = hashlib.sha256(step.read_bytes()).hexdigest()[:16]
    return f"{digest}:{h_fine:.4f}:{h_coarse:.4f}:{near:.3f}:{far:.3f}:{int(loaded)}"


def _sidecar(path_msh: Path) -> Path:
    return path_msh.with_suffix(path_msh.suffix + ".json")


def step_paths() -> tuple[Path, Path]:
    """Plate and plate+payload STEP of the active variant (see fe_common.set_variant)."""
    return F.ROOT / "STEP" / "parallel_yz_r01.step", F.ROOT / "STEP" / "parallel_yz_r01_loaded.step"


def _inside(box: dict, centre) -> bool:
    return all(box[k][0] - 1e-6 <= c <= box[k][1] + 1e-6 for k, c in zip("xyz", centre))


def build(path_msh: Path, h_fine: float, loaded: bool = False, h_coarse: float | None = None,
          near: float = 0.25, far: float = 2.5) -> dict:
    """Write a linear tet mesh (scikit-fem raises it to quadratic) and describe it."""
    if h_coarse is None:
        h_coarse = 5.0 * h_fine
    rep = report()
    step_plate, step_loaded = step_paths()
    key = _cache_key(step_loaded if loaded else step_plate, h_fine, h_coarse, near, far, loaded)
    sidecar = _sidecar(path_msh)
    if path_msh.exists() and sidecar.exists():
        cached = json.loads(sidecar.read_text(encoding="utf-8"))
        if cached.get("key") == key:
            return cached["info"]

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("parallel_yz_r01")
        gmsh.model.occ.importShapes(str(step_loaded if loaded else step_plate))
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if loaded and len(volumes) < 2:
            raise RuntimeError(f"loaded STEP should hold 2 or more solids, found {len(volumes)}")
        if len(volumes) > 1:
            # Body + shim leaves (+ holder, + base): make every contact conformal.
            gmsh.model.occ.fragment(volumes[:1], volumes[1:])
            gmsh.model.occ.synchronize()
            volumes = gmsh.model.getEntities(3)

        fields = []
        for leaf in rep["leaf_boxes"]:
            f = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(f, "VIn", h_fine)
            gmsh.model.mesh.field.setNumber(f, "VOut", h_coarse)
            for axis, (lo, hi) in zip("XYZ", (leaf["x"], leaf["y"], leaf["z"])):
                gmsh.model.mesh.field.setNumber(f, f"{axis}Min", lo - near)
                gmsh.model.mesh.field.setNumber(f, f"{axis}Max", hi + near)
            gmsh.model.mesh.field.setNumber(f, "Thickness", far)
            fields.append(f)
        # The 0.2 mm pad lands need elements no larger than themselves, whatever
        # h_fine is, or the surface mesh degenerates on them.
        for pad in rep["pads"].values():
            f = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(f, "VIn", min(h_fine, 0.6))
            gmsh.model.mesh.field.setNumber(f, "VOut", h_coarse)
            for axis in "xyz":
                spec = pad[axis]
                lo, hi = (spec, spec) if isinstance(spec, (int, float)) else spec
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Min", lo - 0.5)
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Max", hi + 0.5)
            gmsh.model.mesh.field.setNumber(f, "Thickness", far)
            fields.append(f)
        # Extra boxes the model asks to resolve (R02: the 0.3 mm stop gaps).
        for box in rep.get("refine_boxes", []):
            f = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(f, "VIn", min(h_fine, 0.5))
            gmsh.model.mesh.field.setNumber(f, "VOut", h_coarse)
            for axis in "xyz":
                lo, hi = box[axis]
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Min", lo - 0.5)
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Max", hi + 0.5)
            gmsh.model.mesh.field.setNumber(f, "Thickness", far)
            fields.append(f)
        # Wire struts (R07): dia 0.4 wires need a few elements across.
        for box in rep.get("wire_boxes", []):
            f = gmsh.model.mesh.field.add("Box")
            gmsh.model.mesh.field.setNumber(f, "VIn", box["size"])
            gmsh.model.mesh.field.setNumber(f, "VOut", h_coarse)
            for axis in "xyz":
                lo, hi = box[axis]
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Min", lo - 0.3)
                gmsh.model.mesh.field.setNumber(f, f"{axis.upper()}Max", hi + 0.3)
            gmsh.model.mesh.field.setNumber(f, "Thickness", 1.5)
            fields.append(f)
        # Every small cylindrical surface (screw holes, counterbores, wire ties,
        # the fiber hole) needs elements no larger than its diameter, or the
        # surface mesh overlaps on it. Found from the geometry, not the report.
        small_cyls = []
        for dim, tag in gmsh.model.getEntities(2):
            if gmsh.model.getType(dim, tag) != "Cylinder":
                continue
            bb = gmsh.model.getBoundingBox(dim, tag)
            extents = sorted(bb[i + 3] - bb[i] for i in range(3))
            if extents[1] < 6.0:                     # diameter ~ the two small extents
                small_cyls.append(tag)
        if small_cyls:
            dist = gmsh.model.mesh.field.add("Distance")
            gmsh.model.mesh.field.setNumbers(dist, "SurfacesList", small_cyls)
            gmsh.model.mesh.field.setNumber(dist, "Sampling", 100)
            thr = gmsh.model.mesh.field.add("Threshold")
            gmsh.model.mesh.field.setNumber(thr, "InField", dist)
            gmsh.model.mesh.field.setNumber(thr, "SizeMin", min(h_fine, 0.7))
            gmsh.model.mesh.field.setNumber(thr, "SizeMax", h_coarse)
            gmsh.model.mesh.field.setNumber(thr, "DistMin", 0.5)
            gmsh.model.mesh.field.setNumber(thr, "DistMax", far)
            fields.append(thr)
        # ... and the dia 3 fiber hole cannot be tiled by h_coarse elements either.
        hole = rep["parameters"]["fiber_hole"]
        f = gmsh.model.mesh.field.add("Box")
        gmsh.model.mesh.field.setNumber(f, "VIn", min(h_fine, 0.8))
        gmsh.model.mesh.field.setNumber(f, "VOut", h_coarse)
        for axis, (lo, hi) in zip("XYZ", ((0.0, rep["parameters"]["b"]), (-hole, hole), (-hole, hole))):
            gmsh.model.mesh.field.setNumber(f, f"{axis}Min", lo)
            gmsh.model.mesh.field.setNumber(f, f"{axis}Max", hi)
        gmsh.model.mesh.field.setNumber(f, "Thickness", far)
        fields.append(f)
        combined = gmsh.model.mesh.field.add("Min")
        gmsh.model.mesh.field.setNumbers(combined, "FieldsList", fields)
        gmsh.model.mesh.field.setAsBackgroundMesh(combined)

        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        # Delaunay in 2D and 3D: Frontal-Delaunay overlaps facets on the fiber
        # hole under this size field, and HXT reports duplicated facets on the
        # 0.2 mm pad lands.
        gmsh.option.setNumber("Mesh.Algorithm", 5)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)

        payload_box = rep["payload"]["box"]
        plate_tags, payload_tags = [], []
        for dim, tag in volumes:
            bb = gmsh.model.getBoundingBox(dim, tag)
            centre = [(bb[i] + bb[i + 3]) / 2 for i in range(3)]
            (payload_tags if loaded and _inside(payload_box, centre) else plate_tags).append(tag)
        gmsh.model.addPhysicalGroup(3, plate_tags, name="plate")
        if payload_tags:
            gmsh.model.addPhysicalGroup(3, payload_tags, name="payload")

        gmsh.model.mesh.generate(3)
        path_msh.parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(str(path_msh))

        _, tags, _ = gmsh.model.mesh.getElements(dim=3)
        info = {
            "h_fine_mm": h_fine, "h_coarse_mm": h_coarse, "near_mm": near, "far_mm": far,
            "loaded": loaded, "leaf_boxes": len(rep["leaf_boxes"]),
            "linear_tets": int(sum(len(t) for t in tags)),
            "mesh_nodes": int(len(gmsh.model.mesh.getNodes()[0])),
            "msh": path_msh.name,
        }
        sidecar.write_text(json.dumps({"key": key, "info": info}, indent=2) + "\n", encoding="utf-8")
        return info
    finally:
        gmsh.finalize()


def _build_one(args) -> str:
    """Worker for the CLI: (variant, h, loaded) -> one line of report."""
    import time
    variant, h, loaded = args
    F.set_variant(variant)
    tag = "_loaded" if loaded else ""
    msh = F.WORK / f"parallel_yz_r01{tag}_h{h:.2f}.msh"
    t = time.time()
    info = build(msh, h, loaded=loaded)
    return f"  {msh.name}: {info['linear_tets']:,} tets  [{time.time() - t:.1f}s]"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sizes", type=float, nargs="+", required=True)
    parser.add_argument("--jobs", type=int, default=8, help="gmsh processes at once (each single-threaded)")
    parser.add_argument("--only", choices=("bare", "loaded"), default=None)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    F.WORK.mkdir(exist_ok=True)
    jobs = [(args.variant, h, loaded) for h in args.sizes for loaded in (False, True)
            if args.only is None or (args.only == "loaded") == loaded]
    import multiprocessing as mp
    ctx = mp.get_context("fork") if hasattr(__import__("os"), "fork") else mp.get_context("spawn")
    with ctx.Pool(min(args.jobs, len(jobs))) as pool:
        for line in pool.imap_unordered(_build_one, jobs):
            print(line, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

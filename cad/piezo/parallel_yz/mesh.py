"""Mesh the parallel YZ plate with gmsh, refined inside the leaf boxes.

`model.py` records every leaf as an axis-aligned box in geometry_report.json, so
refinement needs no face hunting: one gmsh Box field per leaf (h_fine inside,
grown by `near` to catch the root fillets, blending to h_coarse over `far`),
combined with a Min field. The payload block of the loaded STEP is fragmented
against the plate so the two solids share a conformal interface.

Importable only; run through solve_static.py / solve_modal.py.
"""
from __future__ import annotations

import json
from pathlib import Path

import gmsh

HERE = Path(__file__).resolve().parent
REPORT = HERE / "geometry_report.json"
STEP_PLATE = HERE / "STEP" / "parallel_yz_r01.step"
STEP_LOADED = HERE / "STEP" / "parallel_yz_r01_loaded.step"


def report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _inside(box: dict, centre) -> bool:
    return all(box[k][0] - 1e-6 <= c <= box[k][1] + 1e-6 for k, c in zip("xyz", centre))


def build(path_msh: Path, h_fine: float, loaded: bool = False, h_coarse: float | None = None,
          near: float = 0.25, far: float = 2.5) -> dict:
    """Write a linear tet mesh (scikit-fem raises it to quadratic) and describe it."""
    if h_coarse is None:
        h_coarse = 5.0 * h_fine
    rep = report()

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("parallel_yz_r01")
        gmsh.model.occ.importShapes(str(STEP_LOADED if loaded else STEP_PLATE))
        gmsh.model.occ.synchronize()
        volumes = gmsh.model.getEntities(3)
        if loaded:
            if len(volumes) != 2:
                raise RuntimeError(f"loaded STEP should hold 2 solids, found {len(volumes)}")
            gmsh.model.occ.fragment([volumes[0]], [volumes[1]])
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
        return {
            "h_fine_mm": h_fine, "h_coarse_mm": h_coarse, "near_mm": near, "far_mm": far,
            "loaded": loaded, "leaf_boxes": len(rep["leaf_boxes"]),
            "linear_tets": int(sum(len(t) for t in tags)),
            "mesh_nodes": int(len(gmsh.model.mesh.getNodes()[0])),
            "msh": path_msh.name,
        }
    finally:
        gmsh.finalize()

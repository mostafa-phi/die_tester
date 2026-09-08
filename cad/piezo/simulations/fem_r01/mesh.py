"""Mesh the FEM R01 Z guide with gmsh, refined on the leaves and their roots.

The guide is a 6 mm plate carrying 0.5 mm leaves, so a uniform mesh fine enough
for the leaves would be far larger than a direct sparse solve can take. Element
size is therefore driven by distance from the surfaces that actually need it:

  * the leaf side walls - planar faces whose normal is X, at |x| = 13 and 27,
    the same stations `geometry.py` uses to find its 32 fillet edges;
  * the R0.5 root fillets - the only cylindrical faces in the solid.

Everything else (plate body, frame, carriage post) coarsens away from those.

Run through `solve_static.py`; this module is importable and has no CLI.
"""
from __future__ import annotations

import json
from pathlib import Path

import gmsh

HERE = Path(__file__).resolve().parent
STEP = HERE / "guide_r01.step"
REPORT = HERE / "geometry_report.json"

# Leaf wall stations in x (mm), from geometry.py's fillet-edge search.
LEAF_X = (13.0, 27.0)
LEAF_X_TOL = 0.35
# A leaf face is planar with its normal along X.
NORMAL_TOL = 0.99


def patch_boxes() -> dict[str, dict]:
    """Load the load/fixture patch boxes recorded when the geometry was built."""
    report = json.loads(REPORT.read_text())
    return {"force": report["force_patch_mm"], "fixture": report["fixture_patch_mm"]}


def _is_leaf_face(tag: int) -> bool:
    if gmsh.model.getType(2, tag) != "Plane":
        return False
    # Surface normal at the parametric midpoint.
    bounds = gmsh.model.getParametrizationBounds(2, tag)
    uv = [(lo + hi) / 2 for lo, hi in zip(bounds[0], bounds[1])]
    nx, ny, nz = gmsh.model.getNormal(tag, uv)
    if abs(nx) < NORMAL_TOL:
        return False
    xmin, _, _, xmax, _, _ = gmsh.model.getBoundingBox(2, tag)
    x = (xmin + xmax) / 2
    return min(abs(abs(x) - station) for station in LEAF_X) < LEAF_X_TOL


def _is_root_fillet(tag: int) -> bool:
    return gmsh.model.getType(2, tag) == "Cylinder"


def build(path_msh: Path, h_fine: float, h_coarse: float | None = None,
          near: float = 0.6, far: float = 4.0) -> dict:
    """Write a linear tet mesh of the guide and report what it contains.

    h_fine applies within `near` mm of the leaves and roots, blending to
    h_coarse by `far` mm. scikit-fem raises the interpolation to quadratic, so
    the linear mesh here is the geometric resolution, not the element order.
    """
    if h_coarse is None:
        h_coarse = 6.0 * h_fine

    gmsh.initialize()
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("guide_r01")
        gmsh.model.occ.importShapes(str(STEP))
        gmsh.model.occ.synchronize()

        surfaces = [tag for _, tag in gmsh.model.getEntities(2)]
        refine_on = [t for t in surfaces if _is_leaf_face(t) or _is_root_fillet(t)]
        if not refine_on:
            raise RuntimeError("No leaf or fillet faces found; check LEAF_X against the model")

        distance = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance, "SurfacesList", refine_on)
        gmsh.model.mesh.field.setNumber(distance, "Sampling", 200)

        threshold = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold, "InField", distance)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMin", h_fine)
        gmsh.model.mesh.field.setNumber(threshold, "SizeMax", h_coarse)
        gmsh.model.mesh.field.setNumber(threshold, "DistMin", near)
        gmsh.model.mesh.field.setNumber(threshold, "DistMax", far)
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold)

        # The background field is the only size source we want.
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
        gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
        gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
        gmsh.option.setNumber("Mesh.ElementOrder", 1)
        gmsh.option.setNumber("Mesh.Algorithm3D", 10)  # HXT, fast for large tet counts
        gmsh.option.setNumber("Mesh.MshFileVersion", 2.2)

        volumes = [tag for _, tag in gmsh.model.getEntities(3)]
        gmsh.model.addPhysicalGroup(3, volumes, name="guide")

        gmsh.model.mesh.generate(3)
        path_msh.parent.mkdir(parents=True, exist_ok=True)
        gmsh.write(str(path_msh))

        types, tags, _ = gmsh.model.mesh.getElements(dim=3)
        n_tets = sum(len(t) for t in tags)
        n_nodes = len(gmsh.model.mesh.getNodes()[0])
        return {
            "h_fine_mm": h_fine,
            "h_coarse_mm": h_coarse,
            "refined_faces": len(refine_on),
            "leaf_faces": sum(1 for t in refine_on if _is_leaf_face(t)),
            "fillet_faces": sum(1 for t in refine_on if _is_root_fillet(t)),
            "linear_tets": n_tets,
            "mesh_nodes": n_nodes,
            "msh": path_msh.name,
        }
    finally:
        gmsh.finalize()

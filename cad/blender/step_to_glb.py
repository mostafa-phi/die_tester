"""Convert the station assembly STEP into a GLB that Blender can import.

`cad/station/model.py` saves the whole station as one `cq.Assembly` (STEP), where every member
carries its name and colour and is already placed in the station frame.  Blender cannot read STEP,
so this script tessellates it once with OpenCASCADE (through the `cascadio` wheel) and writes a GLB
that keeps the same named, coloured part tree.

Run it with the pinned dependencies, no virtualenv of your own needed:

    UV_SYSTEM_CERTS=1 uv run --with cascadio --with numpy --python 3.12 --no-project \
        python cad/blender/step_to_glb.py cad/station/STEP/station_assembly.step.zip

`UV_SYSTEM_CERTS=1` is required on the NTT network: uv's bundled certificate store rejects the
intercepting proxy ("invalid peer certificate: UnknownIssuer").

The input may be the `.zip` or an already extracted `.step` / `.stp`.  Output goes to
`cad/blender/station_assembly.glb`, which is git-ignored: it is a large derived file, like the
assembly STEP it comes from.
"""

import argparse
import datetime
import hashlib
import json
import os
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))

# Tessellation. The station is ~1.1 m across and the smallest features that must still read are the
# 0.127 mm flexure blade and the 3 mm finger bars, so a 0.05 mm absolute deflection is the balance
# point: curved vendor surfaces (micrometer knobs, the objective barrel) stay smooth at render
# resolution without the triangle count that a 0.01 mm deflection would give over the whole machine.
TOL_LINEAR = 0.05     # mm
TOL_ANGULAR = 0.2     # rad


def step_from(path, workdir):
    """Return a path to a STEP file, extracting it from a zip archive when needed."""
    if not path.lower().endswith(".zip"):
        return path
    os.makedirs(workdir, exist_ok=True)
    with zipfile.ZipFile(path) as z:
        members = [n for n in z.namelist() if n.lower().endswith((".step", ".stp"))]
        if not members:
            sys.exit(f"no .step/.stp inside {path}")
        if len(members) > 1:
            print(f"[step] {len(members)} STEP files in the archive, taking {members[0]}")
        out = os.path.join(workdir, os.path.basename(members[0]))
        if os.path.exists(out) and os.path.getsize(out) == z.getinfo(members[0]).file_size:
            print(f"[step] reusing extracted {out}")
            return out
        print(f"[step] extracting {members[0]} -> {out}")
        with z.open(members[0]) as src, open(out, "wb") as dst:
            while True:
                chunk = src.read(1 << 20)
                if not chunk:
                    break
                dst.write(chunk)
    return out


def record_source(source_path, out_dir):
    """Write cad/blender/source.json so staleness against the station is visible, not silent.

    `cad/build.py --check` compares this sha256 with the station assembly in its manifest and says
    when the Blender outputs come from an older station (CLAUDE.md section 5).
    """
    digest = hashlib.sha256()
    with open(source_path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    record = {
        "station_assembly_zip_sha256": digest.hexdigest(),
        "built": datetime.datetime.now(datetime.timezone.utc)
                 .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }
    path = os.path.join(out_dir, "source.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
        handle.write("\n")
    print("[src] %s  %s" % (record["station_assembly_zip_sha256"][:16], path))
    return record


def report(glb_path):
    """Print the part count and bounding box so the conversion can be checked against the CAD."""
    import numpy as np
    import trimesh

    scene = trimesh.load(glb_path, process=False)
    geoms = getattr(scene, "geometry", {})
    print(f"[glb] {len(geoms)} meshes, "
          f"{sum(len(g.faces) for g in geoms.values()):,} triangles")
    lo, hi = scene.bounds
    for axis, a, b in zip("XYZ", lo, hi):
        print(f"[glb] {axis} {a:10.2f} .. {b:10.2f}   ({b - a:8.2f} wide)")
    names = sorted(n for n in getattr(scene.graph, "nodes_geometry", []))
    print(f"[glb] first parts: {', '.join(names[:8])}")
    return len(geoms)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source", nargs="?",
                    default=os.path.join(HERE, "..", "station", "STEP", "station_assembly.step.zip"),
                    help="station assembly .step/.stp, or a .zip containing one")
    ap.add_argument("-o", "--output", default=os.path.join(HERE, "station_assembly.glb"))
    ap.add_argument("--tol-linear", type=float, default=TOL_LINEAR)
    ap.add_argument("--tol-angular", type=float, default=TOL_ANGULAR)
    ap.add_argument("--workdir", default=os.environ.get("TEMP", HERE),
                    help="where a zipped STEP is extracted")
    args = ap.parse_args()

    import cascadio

    source = os.path.abspath(args.source)
    src = step_from(source, args.workdir)
    print(f"[step] {src}  ({os.path.getsize(src) / 1e6:.0f} MB)")
    print(f"[mesh] linear {args.tol_linear} mm, angular {args.tol_angular} rad")

    t0 = time.time()
    cascadio.step_to_glb(
        src,
        os.path.abspath(args.output),
        tol_linear=args.tol_linear,
        tol_angular=args.tol_angular,
        merge_primitives=True,     # one primitive per part -> one Blender object per part
        include_materials=True,    # keep the cq.Assembly colours as a starting point
        use_parallel=True,
    )
    print(f"[glb] {args.output}  ({os.path.getsize(args.output) / 1e6:.0f} MB) "
          f"in {time.time() - t0:.0f} s")
    report(os.path.abspath(args.output))
    if source.lower().endswith(".zip"):
        record_source(source, HERE)
    else:
        print("[src] source.json not written: the interface is the .zip on the branch, and %s "
              "is not it" % os.path.basename(source))


if __name__ == "__main__":
    main()

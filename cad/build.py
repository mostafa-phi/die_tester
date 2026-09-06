#!/usr/bin/env python3
"""
Build every CAD component in dependency order and keep the folders synchronized.

    python cad/build.py                 gripper (vertical + horizontal) -> nest -> tray -> station (default + horizontal), then renders.
                                        Manufacturer STEP from cad/vendor (git-ignored) is placed wherever the file exists; a clone
                                        without the files gets the envelope build and the same checks.
    python cad/build.py --no-render     skip the PNG renders (cadgen step snapshot)
    python cad/build.py --only nest     one component (its dependencies are NOT rebuilt; use for quick iteration only)
    python cad/build.py --check         no build: exit 1 if any model source changed since the last full build or a
                                        tracked output is missing / hand-edited (run by the SessionStart hook)

Why one entry point: the nest imports the gripper (its checks use the jaws), the tray imports the gripper,
the station imports all three. A change in cad/common or in one model.py silently invalidates the STEP,
checks and renders of every component downstream, so partial rebuilds are the way folders drift apart.
This script rebuilds everything and records the sha256 of every source and output in build_manifest.json;
--check compares the tree with that manifest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "build_manifest.json")
PY = sys.executable

# build order = dependency order
COMPONENTS = ["gripper", "nest", "tray", "station"]
SOURCES = ["common/__init__.py", "build.py"] + [f"{c}/model.py" for c in COMPONENTS]

# git-ignored outputs (large or vendor-derived): built, rendered from, but not hashed into the manifest
IGNORED_OUTPUT_PATTERNS = ("_vendor", "station/STEP/station_assembly", "tray/STEP/wafer_tray_8x14.step")
# note: the station and nest checks depend on which vendor files are present; the checks header says which were placed

# renders: (component, STEP file relative to the component's STEP/, output name, camera)
RENDERS = [
    ("gripper", "gripper_module_assembly.step", "gripper_iso.png", "iso"),
    ("gripper", "gripper_module_assembly.step", "gripper_front.png", "front"),
    ("gripper", "gripper_module_assembly.step", "gripper_side.png", "90:20"),
    ("gripper", "gripper_module_assembly_vendor.step", "gripper_vendor_iso.png", "iso"),
    ("gripper", "gripper_module_assembly_vendor.step", "gripper_vendor_front.png", "front"),
    ("gripper", "gripper_module_assembly_h.step", "gripper_h_iso.png", "iso"),
    ("gripper", "gripper_module_assembly_h.step", "gripper_h_side.png", "90:20"),
    ("gripper", "gripper_module_assembly_vendor_h.step", "gripper_vendor_h_iso.png", "iso"),
    ("nest", "nest_module_assembly.step", "nest_iso.png", "iso"),
    ("nest", "nest_module_assembly.step", "nest_top.png", "top"),
    ("nest", "nest_module_assembly.step", "nest_front.png", "front"),
    ("nest", "nest_module_setdown.step", "nest_setdown_iso.png", "iso"),
    ("nest", "nest_chuck_copper.step", "nest_chuck_iso.png", "iso"),
    ("nest", "nest_cage_semitron.step", "nest_cage_iso.png", "iso"),
    ("tray", "tray_pocket_check.step", "tray_pocket_iso.png", "iso"),
    ("tray", "wafer_tray_8x14.step", "tray_iso.png", "iso"),
    ("station", "station_assembly.step", "station_iso.png", "iso"),
    ("station", "station_assembly.step", "station_plan.png", "top"),
    ("station", "station_assembly.step", "station_front.png", "front"),
    ("station", "station_assembly.step", "station_side.png", "90:20"),
    ("station", "station_assembly_h.step", "station_h_iso.png", "iso"),
    ("station", "station_assembly_h.step", "station_h_side.png", "90:20"),
]
# outputs of earlier build layouts that a rebuild must remove (so the tree only holds what build.py produces)
STALE = ["station/checks_vendor.txt", "station/checks_vendor_h.txt", "station/renders/station_vendor_iso.png",
         "station/renders/station_vendor_plan.png", "station/renders/station_vendor_front.png", "station/renders/station_vendor_side.png",
         "station/renders/station_vendor_h_iso.png", "station/renders/station_vendor_h_side.png", "station/STEP/station_assembly_vendor.step",
         "station/STEP/station_assembly_vendor_h.step", "nest/STEP/nest_module_assembly_vendor.step",
         "nest/STEP/nest_adapter_kb_rpg.step", "nest/STEP/nest_adapter_rpg_kxc.step"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def is_ignored(relpath):
    return any(pat in relpath for pat in IGNORED_OUTPUT_PATTERNS)


def outputs_of(comp):
    """Every file the component folder holds besides its sources (STEP/, STL/, renders/, checks*.txt)."""
    d = os.path.join(ROOT, comp)
    out = []
    for sub in ("STEP", "STL", "renders"):
        sd = os.path.join(d, sub)
        if os.path.isdir(sd):
            out += [os.path.join(sd, f) for f in sorted(os.listdir(sd))]
    out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.startswith("checks") and f.endswith(".txt")]
    return out


def run(cmd, cwd=None, quiet=False):
    t0 = time.time()
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        print(r.stdout[-4000:]); print(r.stderr[-4000:])
        raise SystemExit(f"FAILED ({r.returncode}): {' '.join(cmd)}")
    if not quiet:
        tail = [ln for ln in r.stdout.splitlines() if "OVERLAP" in ln or "CHECK" in ln or ln.startswith("wrote")]
        for ln in tail:
            print("    " + ln)
    print(f"    {time.time() - t0:5.1f} s")
    return r


def build(comp, extra):
    print(f"[{comp}] {' '.join(extra) or ''}")
    run([PY, os.path.join(ROOT, comp, "model.py")] + extra)


def render(comp, step, png, camera):
    src = os.path.join(ROOT, comp, "STEP", step)
    dst = os.path.join(ROOT, comp, "renders", png)
    if not os.path.exists(src):
        return False
    if shutil.which("cadgen") is None:
        print("    cadgen not on PATH: skipping renders"); return False
    profile = "presentation"
    r = subprocess.run(["cadgen", "step", "snapshot", src, dst, "--camera", camera, "--size-profile", profile, "--json"],
                       text=True, capture_output=True, cwd=os.path.dirname(src))
    ok = r.returncode == 0 and os.path.exists(dst)
    print(f"    {'ok ' if ok else 'FAILED'} {comp}/renders/{png}")
    if not ok:
        print(r.stdout[-1500:], r.stderr[-1500:])
    return ok


def write_manifest(args):
    m = {"built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "args": args,
         "sources": {s: sha(os.path.join(ROOT, s)) for s in SOURCES}, "outputs": {}}
    for comp in COMPONENTS:
        for p in outputs_of(comp):
            rp = rel(p)
            if not is_ignored(rp):
                m["outputs"][rp] = sha(p)
    with open(MANIFEST, "w") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    print(f"manifest: {len(m['sources'])} sources, {len(m['outputs'])} tracked outputs -> {rel(MANIFEST)}")


def check():
    if not os.path.exists(MANIFEST):
        print("cad: no build_manifest.json - run `python cad/build.py`"); return 1
    m = json.load(open(MANIFEST))
    bad = []
    for s in SOURCES:
        p = os.path.join(ROOT, s)
        if not os.path.exists(p):
            bad.append(f"source missing: {s}")
        elif m["sources"].get(s) != sha(p):
            bad.append(f"source changed since the last build: {s}")
    for s in [x for x in m["sources"] if x not in SOURCES]:
        bad.append(f"source no longer in the build list: {s}")
    for rp, h in m["outputs"].items():
        p = os.path.join(ROOT, rp)
        if not os.path.exists(p):
            bad.append(f"output missing: {rp}")
        elif sha(p) != h:
            bad.append(f"output differs from the last build (hand-edited or partial rebuild): {rp}")
    for comp in COMPONENTS:
        for p in outputs_of(comp):
            rp = rel(p)
            if not is_ignored(rp) and rp not in m["outputs"]:
                bad.append(f"untracked output not produced by build.py: {rp}")
    if bad:
        print("cad: folders are OUT OF SYNC (run `python cad/build.py` and commit the result):")
        for b in bad:
            print("  - " + b)
        return 1
    print(f"cad: in sync with build_manifest.json (built {m['built']})")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--only", choices=COMPONENTS)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    if a.check:
        raise SystemExit(check())
    comps = [a.only] if a.only else COMPONENTS
    t0 = time.time()
    for rel_ in STALE:
        try:
            os.remove(os.path.join(ROOT, rel_))
        except OSError:
            pass
    for comp in comps:
        build(comp, [])
        if comp in ("gripper", "station"):
            build(comp, ["--horizontal"])
    if not a.no_render:
        print("[renders]")
        for comp, step, png, cam in RENDERS:
            if comp in comps:
                render(comp, step, png, cam)
    if a.only:
        print(f"partial build ({a.only}) in {time.time() - t0:.0f} s - manifest NOT updated; run a full build before committing")
        return
    write_manifest([x for x in sys.argv[1:]])
    print(f"full build in {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()

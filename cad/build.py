#!/usr/bin/env python3
"""
Build every CAD component in dependency order and keep the folders synchronized.

    python cad/build.py                 incremental: gripper (vertical + horizontal) -> nest -> tray -> station (default +
                                        horizontal), then renders. A component whose sources (its model.py, everything
                                        upstream of it, cad/common, build.py) are unchanged since the last full build and
                                        whose tracked outputs still match the manifest is skipped. Manufacturer STEP from
                                        cad/vendor is placed wherever the file exists (a clone without the files gets the
                                        envelope build and the same checks); after adding a vendor file run --all once.
    python cad/build.py --all           rebuild everything regardless
    python cad/build.py --fast          iteration mode: same incremental build, renders at the "simple" profile (1200 px).
                                        The manifest is NOT updated: run a normal build before committing (it re-renders
                                        only what changed).
    python cad/build.py --no-render     skip the PNG renders (cadgen step snapshot)
    python cad/build.py --only nest     one component (its dependencies are NOT rebuilt; use for quick iteration only)
    python cad/build.py --check         no build: exit 1 if any model source changed since the last full build or a
                                        tracked output is missing / hand-edited (run by the SessionStart hook)

Why one entry point: the nest imports the gripper (its checks use the jaws), the tray imports the gripper,
the station imports all three. A change in cad/common or in one model.py silently invalidates the STEP,
checks and renders of every component downstream, so partial rebuilds are the way folders drift apart.
This script rebuilds what is stale in dependency order and records the sha256 of every source and output in
build_manifest.json; --check compares the tree with that manifest. The two layout passes of the gripper and the
station always run in parallel (they write disjoint files), the renders four at a time except the big station assembly
views, which run one at a time (each holds about 2 GB).
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
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(ROOT, "build_manifest.json")
PY = sys.executable

# build order = dependency order
COMPONENTS = ["gripper", "nest", "tray", "station"]
SOURCES = ["common/__init__.py", "build.py"] + [f"{c}/model.py" for c in COMPONENTS]

# git-ignored outputs (large or vendor-derived): built, rendered from, but not hashed into the manifest
# every output is tracked (decision 2026-09-07) except the raw full station assemblies (120-140 MB, over GitHub's
# 100 MB limit): those are zipped by finish_outputs() and the .zip is tracked and hashed instead; the raw .step stays on
# disk for the renders and is git-ignored
ZIPPED_OUTPUTS = ("station/STEP/station_assembly.step", "station/STEP/station_assembly_h.step")
IGNORED_OUTPUT_PATTERNS = ZIPPED_OUTPUTS
STEP_DATE = "2026-01-01T00:00:00"     # fixed FILE_NAME timestamp so unchanged geometry gives byte-identical STEP files
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
    ("nest", "nest_top_assembly.step", "nest_top_assembly_iso.png", "iso"),
    ("nest", "nest_top_no_die.step", "nest_top_no_die_iso.png", "iso"),
    ("nest", "nest_top_exploded.step", "nest_top_exploded_iso.png", "iso"),
    ("tray", "tray_pocket_check.step", "tray_pocket_iso.png", "iso"),
    ("tray", "wafer_tray_8x14.step", "tray_iso.png", "iso"),
    ("station", "station_assembly.step", "station_iso.png", "iso"),
    ("station", "station_assembly.step", "station_plan.png", "top"),
    ("station", "station_assembly.step", "station_front.png", "front"),
    ("station", "station_assembly.step", "station_side.png", "90:20"),
    ("station", "station_assembly_h.step", "station_h_iso.png", "iso"),
    ("station", "station_assembly_h.step", "station_h_side.png", "90:20"),
    ("station", "station_far_column.step", "station_far_column_iso.png", "iso"),
    ("station", "tower_bracket_6061.step", "station_tower_bracket_iso.png", "iso"),
    ("station", "arm_6061.step", "station_arm_iso.png", "iso"),
    ("station", "tray_deck_6061.step", "station_tray_deck_iso.png", "iso"),
    ("station", "x_axis_riser_6061.step", "station_x_riser_iso.png", "iso"),
    ("station", "gripper_with_sensors.step", "station_sensors_iso.png", "iso"),
    ("station", "gripper_with_sensors.step", "station_sensors_front.png", "front"),
    ("station", "gripper_with_sensors.step", "station_sensors_side.png", "90:20"),
]
# outputs of earlier build layouts that a rebuild must remove (so the tree only holds what build.py produces)
STALE = ["station/checks_vendor.txt", "station/checks_vendor_h.txt", "station/renders/station_vendor_iso.png",
         "station/renders/station_vendor_plan.png", "station/renders/station_vendor_front.png", "station/renders/station_vendor_side.png",
         "station/renders/station_vendor_h_iso.png", "station/renders/station_vendor_h_side.png", "station/STEP/station_assembly_vendor.step",
         "station/STEP/station_assembly_vendor_h.step", "nest/STEP/nest_module_assembly_vendor.step",
         "nest/STEP/nest_adapter_kb_rpg.step", "nest/STEP/nest_adapter_rpg_kxc.step",
         "station/STEP/laser_drop_bracket_6061.step", "station/STL/laser_drop_bracket_6061.stl", "station/renders/station_laser_bracket_iso.png"]
# the two layout passes of these components write disjoint files and run in parallel
TWO_PASS = {"gripper": [["--horizontal"]], "station": [["--horizontal"]]}


TEXT_OUTPUTS = (".txt", ".step", ".json", ".py")


def sha(path):
    """sha256 of a file; text outputs are hashed with CRLF folded to LF, so a checkout that converted line endings (Windows,
    `* text=auto`) still matches the manifest written on Linux."""
    h = hashlib.sha256()
    text = path.endswith(TEXT_OUTPUTS)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk.replace(b"\r\n", b"\n") if text else chunk)
    return h.hexdigest()


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def is_ignored(relpath):
    return relpath in IGNORED_OUTPUT_PATTERNS


def normalize_step(path):
    """Overwrite the FILE_NAME timestamp in a STEP header in place (same length, so no rewrite of the body)."""
    import re
    with open(path, "r+b") as f:
        head = f.read(2048)
        m = re.search(rb"FILE_NAME\('[^']*',\s*'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})'", head)
        if m and m.group(1) != STEP_DATE.encode():
            f.seek(m.start(1)); f.write(STEP_DATE.encode())


def finish_outputs(comp):
    """After a component build: fixed STEP timestamps, and a deterministic .zip beside each output in ZIPPED_OUTPUTS."""
    import zipfile
    sd = os.path.join(ROOT, comp, "STEP")
    if not os.path.isdir(sd):
        return
    for f in sorted(os.listdir(sd)):
        p = os.path.join(sd, f)
        if f.endswith(".step"):
            normalize_step(p)
        if rel(p) in ZIPPED_OUTPUTS:
            zp = p + ".zip"
            with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                zi = zipfile.ZipInfo(f, date_time=(1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
                with open(p, "rb") as src:
                    zf.writestr(zi, src.read())
            print(f"    zipped {rel(p)} -> {os.path.getsize(zp) / 1048576:.1f} MB")


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


def load_manifest():
    return json.load(open(MANIFEST)) if os.path.exists(MANIFEST) else None


def upstream_sources(comp):
    """Sources whose change invalidates comp's model outputs: common, its own model.py and every model.py before it.
    (build.py itself is hashed into the manifest for --check but does not stale the models; a changed RENDERS list shows
    up as a missing or untracked render.)"""
    idx = COMPONENTS.index(comp)
    return ["common/__init__.py"] + [f"{c}/model.py" for c in COMPONENTS[:idx + 1]]


def is_current(comp, m):
    """True if comp's sources are unchanged since the manifest and all its tracked outputs match it."""
    if m is None:
        return False
    for s in upstream_sources(comp):
        p = os.path.join(ROOT, s)
        if not os.path.exists(p) or m["sources"].get(s) != sha(p):
            return False
    tracked = {rp: h for rp, h in m["outputs"].items() if rp.startswith(comp + "/")}
    if not tracked:
        return False
    for rp, h in tracked.items():
        p = os.path.join(ROOT, rp)
        if not os.path.exists(p) or sha(p) != h:
            return False
    for p in outputs_of(comp):
        rp = rel(p)
        if not is_ignored(rp) and rp not in tracked:
            return False
    return True


def run_passes(comp, extras):
    """Run model.py once per argument list, in parallel; print the interesting lines of each; raise on failure."""
    t0 = time.time()
    procs = []
    for extra in extras:
        print(f"[{comp}] {' '.join(extra)}")
        procs.append((extra, subprocess.Popen([PY, os.path.join(ROOT, comp, "model.py")] + extra, text=True,
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)))
    failed = False
    for extra, pr in procs:
        out, err = pr.communicate()
        if pr.returncode != 0:
            print(out[-4000:]); print(err[-4000:]); failed = True
            continue
        for ln in out.splitlines():
            if "OVERLAP" in ln or "CHECK" in ln or ln.startswith("wrote"):
                print(f"    [{comp} {' '.join(extra)}] {ln}")
    print(f"    {comp}: {time.time() - t0:5.1f} s")
    if failed:
        raise SystemExit(f"FAILED: {comp}")


def render(comp, step, png, camera, fast=False):
    src = os.path.join(ROOT, comp, "STEP", step)
    dst = os.path.join(ROOT, comp, "renders", png)
    if not os.path.exists(src):
        return False
    if shutil.which("cadgen") is None:
        print("    cadgen not on PATH: skipping renders"); return False
    cmd = ["cadgen", "step", "snapshot", src, dst, "--camera", camera, "--json"]
    cmd += ["--size-profile", "simple", "--width", "1200"] if fast else ["--size-profile", "presentation"]
    r = subprocess.run(cmd, text=True, capture_output=True, cwd=os.path.dirname(src))
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


def blender_staleness(m):
    """Information only: cad/blender (3D-viz agent) records the sha256 of the station zip it consumed in source.json."""
    src = os.path.join(ROOT, "blender", "source.json")
    if not os.path.exists(src):
        return
    try:
        rec = json.load(open(src))
    except (OSError, ValueError):
        print("cad/blender/source.json is unreadable"); return
    cur = m["outputs"].get("station/STEP/station_assembly.step.zip")
    got = rec.get("station_assembly_zip_sha256")
    if cur and got and got != cur:
        print(f"info: cad/blender outputs were built from an older station assembly (zip sha {got[:12]}, "
              f"current {cur[:12]}; built {rec.get('built', '?')}) - ask the 3D-viz agent to rerun its pipeline")
    elif cur and got:
        print(f"cad/blender outputs match the current station assembly (built {rec.get('built', '?')})")


def check():
    m = load_manifest()
    if m is None:
        print("cad: no build_manifest.json - run `python cad/build.py`"); return 1
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
    blender_staleness(m)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--only", choices=COMPONENTS)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--all", action="store_true", help="rebuild every component even if unchanged")
    ap.add_argument("--fast", action="store_true", help="iteration: simple 1200 px renders, manifest not updated")
    a = ap.parse_args()
    if a.check:
        raise SystemExit(check())
    t0 = time.time()
    for rel_ in STALE:
        try:
            os.remove(os.path.join(ROOT, rel_))
        except OSError:
            pass
    m = load_manifest()
    comps = [a.only] if a.only else COMPONENTS
    built = []
    for comp in comps:
        if not a.all and not a.only and is_current(comp, m):
            print(f"[{comp}] unchanged (sources and outputs match the manifest): skipped")
            continue
        run_passes(comp, [[]] + TWO_PASS.get(comp, []))
        finish_outputs(comp)
        built.append(comp)
    if not a.no_render and built:
        print("[renders]" + (" (fast: simple profile, 1200 px)" if a.fast else ""))
        jobs = [(c, s, p, cam) for c, s, p, cam in RENDERS if c in built]
        # a snapshot of the 100 MB station assembly holds ~2 GB (cadgen + Chromium); those run one at a time, the rest four abreast
        def heavy(j):
            src = os.path.join(ROOT, j[0], "STEP", j[1])
            return os.path.exists(src) and os.path.getsize(src) > 20 * 1024 * 1024
        light, big = [j for j in jobs if not heavy(j)], [j for j in jobs if heavy(j)]
        with ThreadPoolExecutor(max_workers=4) as ex:
            list(ex.map(lambda j: render(*j, fast=a.fast), light))
        for j in big:
            render(*j, fast=a.fast)
    if a.only or a.fast:
        why = f"partial build ({a.only})" if a.only else "fast build"
        print(f"{why} in {time.time() - t0:.0f} s - manifest NOT updated; run `python cad/build.py` before committing")
        return
    write_manifest([x for x in sys.argv[1:]])
    print(f"full build in {time.time() - t0:.0f} s ({', '.join(built) if built else 'nothing rebuilt'})")
    if "station" in built:
        print("note: station_assembly.step.zip changed - cad/blender (3D-viz agent) is downstream and must rerun its pipeline")


if __name__ == "__main__":
    main()

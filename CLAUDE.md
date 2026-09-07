# Die tester: working rules for this repository

Two things live here: the original Suruga-stage fiber-alignment code (`src/`, `main.ipynb`,
`reference_code/`) and the **batch die-handling redesign** (`docs/`, `cad/`). The rules below are
about the redesign; they exist so that the CAD, the checks, the renders and the documents never
disagree with each other.

## 1. Design rules that every model and document must respect

- **Frame.** X = die long axis (10 mm) = gripper stroke / transfer direction, +X toward the far end
  face. Y = optical axis (6 mm); the input fiber comes from −Y, the output fiber from +Y. Z up;
  **Z = 0 is the die's bottom face when the die sits on the nest at the die stage's home position**
  (die top Z 0.5, die centre Y 3). The nest moves ±7.5 mm in X on its stage to step devices; the
  gripper meets it at home only. Defined once in `cad/common/__init__.py`; the docs and the three.js
  viewer use the same frame.
- **Contact rules (never violated, in any state of any mechanism).** The dies are air-clad TFLN:
  the **top surface** and the two **facets (Y = 0 and Y = 6 faces)** are never touched by anything.
  The die is held or pushed only on its **end faces (X = 0 / X = 10)** inside the contact band
  (Y 1.5–4.5, Z 0.05–0.40, i.e. 0.10 below the die top) and rests only on its **backside** (chuck
  pad, tray ledges). Nothing stands in front of a facet where a fiber can go (X 1–9). Any new part
  or motion gets a clearance check against these rules before it is documented.
- **Fiber side.** Fiber tips protrude ~5 mm from the holders; the holder envelope is `common.FIBER`
  (25 wide, Z −8…+4, 20 long) until measured. Fibers are only ever moved by their own NanoMax stages
  and retract 1 mm before the gripper moves. The fibers stay at station X 5; the die stage brings
  each device to them, so any part that moves with the nest is checked against fixed fibers and
  holders over the whole stage travel (`cad/nest` moving-nest sweep).
- **Single sources of truth.** Die dimensions, contact band, fiber/holder envelope, microscope
  envelope, the box/cylinder helpers and the AABB clearance functions live in `cad/common`. A number
  that two components share must not be typed twice; import it. Component-local parameters stay in
  the component's `P` / `N` / `TR` / `S` dict.
- **Vendor geometry.** Bought parts are placed from manufacturer STEP in `cad/vendor/` (tracked since
  2026-09-07 so the files can be used outside this checkout; they stay licensed downloads, see
  `cad/vendor/README.md`) whenever the file is present; there is no separate
  envelope build. Envelopes are fallbacks, never the record where a vendor file exists. What we learned from vendor files (SMC finger gap, KXC table pattern,
  NanoMax micrometer protrusion) is written into the model comments, not just the chat. Catalog numbers typed into an
  envelope (`common.LX20`) say where they came from and are confirmed against the STEP when it arrives.
- **Handling sequences.** How the jaws pick and place (heights, forces, interlocks, the friction-only
  decision, nose crown) is `docs/pick_and_place_design.md`; the gripper, tray and nest models quote it.
- **Every custom part is a part.** Anything that joins two bought things (risers, brackets, adapter plates,
  the arm, the deck) is modelled with its bolt pattern and exported as STEP + STL by the component that owns
  it; a box placeholder is not a part. `docs/print_list.md` lists them all with material and finishing.
- **Honesty of checks.** Clearance checks are per member (`gap_any`, `gap_parts`), never on the
  union bounding box of a compound part. Every non-OK line in a `checks*.txt` is either fixed or
  explained in the component README as intended (e.g. stop pads touching the seated die, the gripper
  band passing under the objective).

## 2. Folder layout: one folder per component

```
cad/
  common/     shared frame, die, contact rules, FIBER, helpers, clearance functions, output layout
  gripper/    model.py  README.md  STEP/  STL/  renders/  checks[_h].txt
  nest/       model.py  README.md  STEP/  STL/  renders/  checks.txt
  tray/       model.py  README.md  STEP/  STL/  renders/  checks.txt
  station/    model.py  README.md  STEP/ (ignored)  renders/  checks[_h].txt
  vendor/     manufacturer STEP (tracked) + fetch script + README
  build.py    builds everything in dependency order, renders, writes build_manifest.json
  README.md   index
```

Dependency order is **gripper → nest → tray → station** (the nest and tray check themselves against
the jaws; the station places all three). Each `model.py` writes **only into its own folder**
(`common.out_dirs`) and imports the others as packages (`from gripper import model as G`).
A new component gets the same shape: `model.py` with a `main()`, a README that explains what it is
and what its checks mean, and an entry in `build.py`'s `COMPONENTS` and `RENDERS`.

## 3. Keep the folders synchronized (the rule that matters most)

A change in `cad/common` or in any `model.py` silently invalidates the STEP, STL, checks and
renders of every component downstream, and the numbers quoted in the READMEs and in `docs/`.
Therefore:

1. **After any change to `cad/common` or a `model.py`, run `python cad/build.py`**. It is incremental:
   a component is skipped when its own source, everything upstream of it, `cad/common` and `build.py`
   are unchanged and its tracked outputs still match the manifest, so a station-only change rebuilds
   only the station (the two layout passes run in parallel, the renders four at a time). It places
   manufacturer STEP wherever the file exists in `cad/vendor` (envelope otherwise; the checks header
   says which); after adding a vendor file run `--all` once. `--fast` is the iteration mode (same
   build, 1200 px "simple" renders, manifest not written); a plain build before committing re-renders
   only what changed. Running a single `model.py` is for iteration only; never commit after a partial
   or `--fast` build.
2. `build.py` writes `cad/build_manifest.json` with the sha256 of every source and every tracked
   output. **`python cad/build.py --check` must pass before committing** (exit 0). The
   `SessionStart` hook (`.claude/setup_cad_skills.sh`) runs it and prints what is out of sync.
3. **Commit sources and tracked outputs together** in the same commit: `model.py`, `checks*.txt`,
   `renders/*.png`, the per-part STEP/STL, `build_manifest.json`, and the README lines that quote
   the changed numbers.
4. **Every output is tracked** (decision 2026-09-07, so the files can be used from a clone without
   rebuilding), with one exception: the two raw full station assemblies (120-140 MB, over GitHub's 100 MB
   limit) are tracked as the `.step.zip` that `build.py` writes beside them (deterministic zip; unzip to open).
   `build.py` also fixes the STEP header timestamp so unchanged geometry gives byte-identical files.
   The manufacturer files in `cad/vendor` are tracked (they are inputs, not derived).
5. **Docs quote, they do not define.** `docs/*.md` and `docs/die_handling_3d.html` describe the
   design and link to the component READMEs; when a number changes in a model, update the README
   of that component, then grep `docs/` and the viewer for the old value. The concept study keeps
   a revision line at the top of the file; add one when a design decision changes.
6. **The three.js viewer** (`docs/die_handling_3d.html`, published as an artifact) mirrors
   `cad/station` in two scenes (exchange, tray pocket); when the station layout or the nest changes in a
   way the user wants shown, update its `ST` parameters and the scene code, screenshot it headless, and
   republish the artifact. Small model changes do not require a viewer update.

## 4. Toolchain notes

- Models are **CadQuery 2.8**; they need the full `cadquery-ocp==7.9.3.1.1`. Installing `cadgen`
  (the vendored text-to-cad skills in `.claude/skills`) pulls a `novtk` OCP build that breaks
  CadQuery; the session hook repairs this. Renders use `cadgen step snapshot` (headless Chromium;
  the hook aliases the preinstalled Playwright browser revision).
- Building everything (`--all`) takes about 20 minutes (the 112-pocket tray, the two station passes
  and the presentation renders dominate); an incremental station-only build about 10; `--no-render`
  skips the PNGs when only the checks are needed; `--fast` renders small.
- Commit messages: imperative subject, body says which component changed and which numbers moved.

## 5. Two agents on this branch: designer agent and 3D-viz agent

Two agents commit to `claude/autoloader-design`. The **designer agent** owns the design: `cad/common`,
`cad/gripper`, `cad/nest`, `cad/tray`, `cad/station`, `cad/vendor`, `cad/build.py`, `docs/` and this file.
The **3D-viz agent** owns `cad/blender/` (Blender scene, materials, cameras, animation, renders) and edits
nothing outside it except its own row in `cad/README.md` and its own block in `.gitignore`. The designer
agent never edits `cad/blender/`.

- **The interface between them is one file plus its member names.** The 3D-viz pipeline reads only
  `cad/station/STEP/station_assembly.step.zip` (the transport at the nest) and, when it needs the worst-case
  pose, `station_far_column.step`. The member names in those assemblies (`cad/station/README.md`, "Assembly
  member names") are a stable interface: the 3D-viz scripts key materials and collections on the name
  prefixes listed there, never on an exact list, and the designer agent does not rename a member or move a
  part between the two files without updating that section and saying so in the commit message.
- **Staleness is visible, not silent.** `build.py` prints a notice after every station rebuild. The 3D-viz
  pipeline records the sha256 of the zip it consumed in `cad/blender/source.json`
  (`{"station_assembly_zip_sha256": "<hex>", "built": "<ISO time>"}`); `build.py --check` compares it with
  the manifest and reports, as information, when the Blender outputs come from an older station.
- **Git.** Both agents `git pull --rebase origin claude/autoloader-design` before every push, and push only
  a clean tree. The designer agent pushes only after a full build with `--check` passing, so the zip on the
  branch always matches the model. The 3D-viz agent starts every run from a freshly pulled branch whose
  `--check` passes, never from a working tree mid-build, and its commits touch only its own paths.
- **Naming in messages and commits:** "designer agent" and "3D-viz agent", so the user and both agents can
  tell whose work a commit is.

## 6. Still-open measurements (do not silently replace with guesses)

Real fiber-holder envelope, microscope working distance and tube diameter, TEC part number and
heat load, die backside finish, the LX20 envelope against its STEP (and the stepper length), the KB1X1 platform bolt pattern for
the adapter plate under the X stage, RMPG40W-N resolution and repeatability, and the tray camera's lens (the 16 mm M12
lens and its spacer are an envelope in `common.SENSORS` until the lens is chosen and its STEP placed; the dart housing
is the vendor STEP). Until measured they stay as the
named parameters above with their assumed values stated in the component READMEs.

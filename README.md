# Die-tester_Stage-control
Python script to control Suruga stages for automatic fiber alignment to TFLN waveguides

## Setup Process
- Download the code onto your computer.
- Create a .venv environment.
- Install requirements.txt
- Make sure you have OBS Studio installed (and the appropriate drivers/software for the camera)

## Running
- The workfplow will be in main.ipynb. All the classes written by Eric (me) are in the `/src` folder. All the old code is in the `/reference_code` folder.

## Design documents
- [Die handling & edge-coupling concept study](docs/die_handling_concept_study.md) — architecture concepts for high-throughput handling of singulated 10 × 6 mm photonic dies (storage, indexing, and self-registering presentation to the fiber stages).
- [Month-1 prototype plan](docs/prototype_plan_month1.md) — what to build first, parts with lead times, week-by-week schedule and pass criteria for robotic die exchange on the existing tester.
- [Pick-and-place design note](docs/pick_and_place_design.md) — how the gripper holds the die (friction on the end faces, no toe), nose geometry, the pick/place sequences at the tray and the chuck with heights, forces and interlocks, die-present sensing, what the hand-cycling rig must measure.
- [Month-1 bill of materials](docs/bom_month1.md) — exact part numbers, vendors, checked prices and lead times, plus the in-house vs outsourced die-sorting decision.
- [Interactive 3-D clearance model](docs/die_handling_3d.html) — three.js scenes of the full test-station exchange (CAD layout: nest, NanoMax fiber stages, microscope, Cartesian axes, wafer tray), tape pick, tray pocket and sorting station.
- [CAD package](cad/README.md) — parametric CadQuery models, one folder per component: [gripper](cad/gripper/README.md) (end-face die gripper: STEP/STL per part, SMC MHZ2-6D, tolerances, tuning), [nest](cad/nest/README.md) (self-registering, temperature-controlled chuck-and-cage chip stage), [tray](cad/tray/README.md) (112-pocket wafer tray, print file) and [station](cad/station/README.md) (full station with vendor models, clearance checks, layout and movement pattern). `python cad/build.py` regenerates everything; `CLAUDE.md` records the design rules and the folder-synchronization requirement.

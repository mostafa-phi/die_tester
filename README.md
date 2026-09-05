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
- [Interactive 3-D clearance model](docs/die_handling_3d.html) — three.js scenes of the nest exchange, tape pick, stick pocket and sorting station.

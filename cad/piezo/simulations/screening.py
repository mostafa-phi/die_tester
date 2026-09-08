"""Analytical screening only. Does NOT implement FEA or certify the assembled stage."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def main():
    geometry = json.loads((ROOT/'generated/geometry.json').read_text())
    cases = json.loads((ROOT/'simulations/cases.json').read_text())
    p = geometry['parameters']
    E = cases['material_seed']['E_MPa']
    # Fixed-guided leaf: E*b*t^3/L^3. Two leaves in parallel per leg,
    # two equal legs in series per side, two mirrored sides in parallel.
    k_leaf = E*p['guide_depth']*p['leaf_t']**3/p['leaf_L']**3
    k_guide = 2*k_leaf/1000  # N/um
    k_apa = cases['actuator']['axial_stiffness_N_per_um']
    report = {
        'status': 'analytical_screening_NOT_FEA',
        'assumptions': ['Rigid frames and interfaces', 'Euler-Bernoulli small-deflection leaves', 'Equal stage displacement sharing', 'No parasitic or intermediate-link modes', 'Vendor axial spring only; full specified voltage range'],
        'guide_stiffness_N_per_um': k_guide,
        'nominal_loaded_stroke_um': cases['actuator']['nominal_free_stroke_um']*k_apa/(k_apa+k_guide),
        'minimum_actuator_loaded_stroke_um': cases['actuator']['minimum_free_stroke_um']*k_apa/(k_apa+k_guide),
        'payload_300g_offset_40mm_moment_Nm': .3*9.80665*.04,
        'single_spring_300g_frequency_Hz': math.sqrt((k_apa+k_guide)*1e6/.3)/(2*math.pi),
        'warning': 'Frequency is a scalar screening example, NOT the loaded XYZ first mode. No 300g or sub-second rating is validated.',
    }
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/screening.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__': main()

"""Does the cuDSS backend give PARDISO's answers? (run on the compute host)

    python remote/test_gpu_backend.py --variant r05 --size 0.70

Solves the sprung static problem of the plate with both backends and prints the
relative difference of the displacement fields and the solve times.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fe_common as F  # noqa: E402
import mesh as meshing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=float, default=0.70)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    F.WORK.mkdir(exist_ok=True)
    msh = F.WORK / f"bench_h{args.size:.2f}.msh"
    meshing.build(msh, args.size, loaded=False)
    model = F.Model(msh, rep, loaded=False)
    K, _ = model.assemble(with_mass=False)
    vectors = model.actuator_vectors()
    U = np.column_stack([vectors["Y"], vectors["Z"]])[model.free]
    k = np.array([rep["actuator"]["k_N_per_um"] * 1e3] * 2)
    Kc = model.reduce(K)
    print(f"{model.N:,} dofs", flush=True)

    fields = {}
    for backend in ("pardiso", "gpu"):
        os.environ["PIEZO_SOLVER"] = backend
        t = time.time()
        base = F.Factorised(Kc)
        t_fac = time.time() - t
        t = time.time()
        X = F.Sprung(base, U, k).solve(-U)
        t_sol = time.time() - t
        fields[backend] = X
        print(f"{backend:8s} {type(base).__name__:18s} factor {t_fac:6.1f} s   sprung solve {t_sol:6.2f} s   "
              f"pad Y {float(vectors['Y'][model.free] @ X[:, 0]) * 1e3:.4f} um/N", flush=True)
    d = np.linalg.norm(fields["gpu"] - fields["pardiso"]) / np.linalg.norm(fields["pardiso"])
    print(f"relative difference gpu vs pardiso: {d:.1e}")
    return 0 if d < 1e-8 else 1


if __name__ == "__main__":
    raise SystemExit(main())

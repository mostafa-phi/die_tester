"""Where do the ~40 s of Model construction go? (compute host)

    python remote/bench_setup.py --variant r05 --size 0.45
"""
from __future__ import annotations

import argparse
import pickle
import sys
import time
from pathlib import Path

import numpy as np
import skfem

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fe_common as F  # noqa: E402
import mesh as meshing  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=float, default=0.45)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    F.WORK.mkdir(exist_ok=True)
    msh = F.WORK / f"parallel_yz_r01_loaded_h{args.size:.2f}.msh"

    t = time.time(); meshing.build(msh, args.size, loaded=True); print(f"gmsh (or cache)   {time.time() - t:6.1f} s", flush=True)
    t = time.time(); mesh = skfem.MeshTet.load(msh); print(f"MeshTet.load      {time.time() - t:6.1f} s", flush=True)
    t = time.time(); element = skfem.ElementVector(skfem.ElementTetP2()); basis = F.Basis(mesh, element); print(f"Basis(P2 vector)  {time.time() - t:6.1f} s   N={basis.N:,}", flush=True)
    t = time.time(); model = F.Model(msh, rep, loaded=True); print(f"Model() total     {time.time() - t:6.1f} s", flush=True)
    t = time.time(); model.fields(); print(f"material fields   {time.time() - t:6.1f} s", flush=True)
    t = time.time(); model.actuator_vectors(); print(f"actuator vectors  {time.time() - t:6.1f} s", flush=True)
    pkl = F.WORK / "bench_model.pkl"
    t = time.time(); pkl.write_bytes(pickle.dumps(model, protocol=5)); print(f"pickle dump       {time.time() - t:6.1f} s   {pkl.stat().st_size / 1e6:.0f} MB", flush=True)
    t = time.time(); m2 = pickle.loads(pkl.read_bytes()); print(f"pickle load       {time.time() - t:6.1f} s   N={m2.N:,}", flush=True)
    pkl.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Where does a solve spend its time on this machine, and what does the GPU buy?

    PIEZO_ASSEMBLY_WORKERS=32 MKL_NUM_THREADS=28 python remote/bench_solver.py --variant r05 --size 0.60

Builds the loaded model at one density and times: serial vs chunked assembly
(and checks they agree), PARDISO factorisation + a 2-column solve, and - when
nvmath-python + cuDSS import - the same factorisation and solve on the GPU.
Prints one line per step; nothing is written to the variant folder.
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
import mesh as meshing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=float, default=0.60)
    parser.add_argument("--serial", action="store_true", help="also time the single-process assembly")
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    F.WORK.mkdir(exist_ok=True)

    msh = F.WORK / f"bench_loaded_h{args.size:.2f}.msh"
    t = time.time()
    meshing.build(msh, args.size, loaded=True)
    model = F.Model(msh, rep, loaded=True)
    print(f"mesh + basis        {time.time() - t:7.1f} s   {model.N:,} dofs", flush=True)

    workers = F.assembly_workers()
    t = time.time()
    K, M = model.assemble(with_mass=True)
    print(f"assembly x{workers:<3}      {time.time() - t:7.1f} s", flush=True)
    if args.serial:
        os.environ["PIEZO_ASSEMBLY_WORKERS"] = "1"
        t = time.time()
        K1, M1 = model.assemble(with_mass=True)
        print(f"assembly serial     {time.time() - t:7.1f} s   "
              f"|K - K1| / |K| = {abs(K - K1).max() / abs(K).max():.1e}", flush=True)
        os.environ["PIEZO_ASSEMBLY_WORKERS"] = str(workers)

    Kc, Mc = model.reduce(K), model.reduce(M)
    sigma = (2 * np.pi * 30.0) ** 2
    A = (Kc - sigma * Mc).tocsr()
    B = np.random.default_rng(0).standard_normal((A.shape[0], 2))

    t = time.time()
    base = F.Factorised(A)
    t_fac = time.time() - t
    t = time.time()
    X = base.solve(B)
    t_sol = time.time() - t
    res = np.linalg.norm(A @ X - B) / np.linalg.norm(B)
    print(f"PARDISO ({os.environ.get('MKL_NUM_THREADS', '?')} thr)  factor {t_fac:7.1f} s   "
          f"solve 2 rhs {t_sol:6.2f} s   resid {res:.1e}", flush=True)

    try:
        import cupy as cp
        import cupyx.scipy.sparse as cps
        from nvmath.sparse.advanced import DirectSolver
    except ImportError as e:
        print(f"GPU: not available ({e})")
        return 0
    t = time.time()
    A_gpu = cps.csr_matrix(A.astype(np.float64))
    B_gpu = cp.asarray(np.asfortranarray(B))
    cp.cuda.Device().synchronize()
    t_up = time.time() - t
    with DirectSolver(A_gpu, B_gpu) as solver:
        t = time.time()
        solver.plan()
        solver.factorize()
        cp.cuda.Device().synchronize()
        t_fac = time.time() - t
        t = time.time()
        Xg = solver.solve()
        cp.cuda.Device().synchronize()
        t_sol = time.time() - t
    Xg = cp.asnumpy(Xg).reshape(B.shape)
    res = np.linalg.norm(A @ Xg - B) / np.linalg.norm(B)
    print(f"cuDSS (A100)        upload {t_up:5.1f} s   factor {t_fac:7.1f} s   "
          f"solve 2 rhs {t_sol:6.2f} s   resid {res:.1e}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

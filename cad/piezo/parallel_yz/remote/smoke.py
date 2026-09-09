"""Ten-second check that the remote environment can do what the chain needs."""
import time
import numpy as np
import scipy.sparse as sp
import pypardiso
import gmsh
import skfem
import cadquery

n = 300_000
A = sp.diags([-np.ones(n - 1), 4 * np.ones(n), -np.ones(n - 1)], [-1, 0, 1], format="csr")
t = time.time()
x = pypardiso.spsolve(A, np.ones(n))
print(f"pardiso {n} dofs {time.time() - t:.2f}s  resid {np.abs(A @ x - 1).max():.1e}")
print("cadquery", cadquery.__version__, "gmsh", gmsh.__version__, "skfem", skfem.__version__)

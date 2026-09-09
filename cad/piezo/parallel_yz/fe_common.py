"""Shared finite-element pieces for the parallel YZ concept.

Materials from geometry_report.json (plate and payload block by position),
the boundary patches the model recorded (pads, fixture, platform front face),
the actuator represented as an axial spring between its two pads, a PARDISO
factorisation reused across right-hand sides, and the rigid-body fit that turns
a displacement field into platform translation and rotation.

The actuator spring is applied by the Woodbury identity: the plate stiffness is
factorised once, and (K + U k U^T)^-1 costs two extra solves. That is why the
static, the springless modal and the sprung modal all share one factorisation.

Units: mm, N, MPa, tonne, s. Frequencies come out in Hz from (rad/s)^2.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import scipy.sparse as sp
import skfem
from skfem import Basis, BilinearForm, FacetBasis, Functional, LinearForm
from skfem.helpers import ddot, dot, sym_grad, trace

try:
    import pypardiso
except ImportError:
    pypardiso = None

HERE = Path(__file__).resolve().parent
# Where a run reads its geometry and writes its results. The baseline (R01,
# APA60S) lives in this folder; a variant lives in variants/<name>/ with the
# same file names, so every script takes --variant and calls set_variant().
ROOT = HERE
REPORT = HERE / "geometry_report.json"
WORK = HERE / "work"

G_MM_S2 = 9806.65
AXIS = {"x": 0, "y": 1, "z": 2}


def set_variant(name: str | None) -> Path:
    """Point REPORT / WORK / ROOT at a variant folder (or back at the baseline)."""
    global ROOT, REPORT, WORK
    ROOT = HERE if not name else HERE / "variants" / name
    REPORT = ROOT / "geometry_report.json"
    WORK = ROOT / "work"
    if not REPORT.exists():
        raise FileNotFoundError(f"{REPORT} - build it first: model.py --variant {name}")
    return ROOT


def add_variant_argument(parser) -> None:
    parser.add_argument("--variant", default=None,
                        help="name under variants/ (built by model.py --variant); default: the R01 baseline")


def report() -> dict:
    return json.loads(REPORT.read_text(encoding="utf-8"))


def in_box(points: np.ndarray, box: dict, tol: float = 0.05) -> np.ndarray:
    """True where points (3, ...) fall inside a recorded box; a scalar entry is a plane."""
    ok = np.ones(points.shape[1:], dtype=bool)
    for axis, i in AXIS.items():
        if axis not in box:
            continue
        spec = box[axis]
        if np.isscalar(spec):
            ok &= np.abs(points[i] - spec) < tol
        else:
            ok &= (points[i] > spec[0] - tol) & (points[i] < spec[1] + tol)
    return ok


class Materials:
    """Body everywhere, then any recorded material regions (shim leaves), then
    the holder block inside its box (loaded meshes only)."""

    def __init__(self, rep: dict, loaded: bool):
        m = rep["material"]
        self.plate = self._lame(m["E_MPa"], m["nu"]) + (m["rho_kg_m3"] * 1e-12,)
        self.regions = [(r["box"], self._lame(r["E_MPa"], r["nu"]) + (r["rho_kg_m3"] * 1e-12,))
                        for r in rep.get("material_regions", [])]
        if loaded:
            pl = rep["payload"]
            self.regions.append((pl["box"], self._lame(pl["E_MPa"], pl["nu"]) + (pl["rho_kg_m3"] * 1e-12,)))

    @staticmethod
    def _lame(E, nu):
        return E * nu / ((1 + nu) * (1 - 2 * nu)), E / (2 * (1 + nu))

    def _pick(self, x, index):
        out = self.plate[index] + 0.0 * x[0]
        for box, props in self.regions:
            out = np.where(in_box(x, box, tol=0.0), props[index], out)
        return out

    def lam(self, x): return self._pick(x, 0)
    def mu(self, x): return self._pick(x, 1)
    def rho(self, x): return self._pick(x, 2)


# The material arrays are evaluated ONCE at the quadrature points and handed to
# the forms as fields (w["lam"] ...). Calling mat.lam(w.x) inside the form
# would re-run the region lookup for every local basis-function pair - 900
# times per element for vector P2 - which with eight shim regions took longer
# than the solve itself.
def material_fields(mat: Materials, basis: Basis) -> dict:
    x = np.asarray(basis.global_coordinates().value)
    return {"lam": mat.lam(x), "mu": mat.mu(x), "rho": mat.rho(x)}


# Assembly is the single-threaded part of every solve (numpy over all elements
# at once, 900 basis pairs per vector-P2 tet). On Linux it is split over
# element chunks in forked workers - each assembles its subset with
# Basis(..., elements=chunk) into the global numbering and the pieces are
# summed. PIEZO_ASSEMBLY_WORKERS overrides the count; Windows (no fork) stays
# serial, so the laptop results are unchanged.
def assembly_workers() -> int:
    env = os.environ.get("PIEZO_ASSEMBLY_WORKERS")
    if env:
        return max(1, int(env))
    if not hasattr(os, "fork"):
        return 1
    return max(1, min(32, (os.cpu_count() or 1) // 2))


_ASM_STATE: dict = {}


def _assemble_chunk(args):
    """Worker: (chunk index, want mass) -> COO pieces of K (and M) for that chunk."""
    i, with_mass = args
    mesh, element, mat, chunks = (_ASM_STATE[k] for k in ("mesh", "element", "mat", "chunks"))
    basis = Basis(mesh, element, elements=chunks[i])
    f = material_fields(mat, basis)
    K = stiffness_form.assemble(basis, lam=f["lam"], mu=f["mu"]).tocoo()
    out = [(K.data, K.row, K.col)]
    if with_mass:
        M = mass_form.assemble(basis, rho=f["rho"]).tocoo()
        out.append((M.data, M.row, M.col))
    return out


def _gravity_chunk(i):
    mesh, element, mat, chunks = (_ASM_STATE[k] for k in ("mesh", "element", "mat", "chunks"))
    basis = Basis(mesh, element, elements=chunks[i])
    return gravity_form.assemble(basis, rho=material_fields(mat, basis)["rho"])


def _parallel_assemble(mesh, element, mat, n_dofs: int, with_mass: bool, workers: int):
    import multiprocessing as mp
    chunks = np.array_split(np.arange(mesh.t.shape[1]), workers)
    _ASM_STATE.update(mesh=mesh, element=element, mat=mat, chunks=chunks)
    try:
        with mp.get_context("fork").Pool(workers) as pool:
            pieces = pool.map(_assemble_chunk, [(i, with_mass) for i in range(workers)])
    finally:
        _ASM_STATE.clear()

    def combine(j):
        data = np.concatenate([p[j][0] for p in pieces])
        row = np.concatenate([p[j][1] for p in pieces])
        col = np.concatenate([p[j][2] for p in pieces])
        A = sp.coo_matrix((data, (row, col)), shape=(n_dofs, n_dofs)).tocsr()
        A.sum_duplicates()
        return A
    K = combine(0)
    M = combine(1) if with_mass else None
    return K, M


@BilinearForm
def stiffness_form(u, v, w):
    eu, ev = sym_grad(u), sym_grad(v)
    return 2.0 * w["mu"] * ddot(eu, ev) + w["lam"] * trace(eu) * trace(ev)


@BilinearForm
def mass_form(u, v, w):
    return w["rho"] * dot(u, v)


@LinearForm
def gravity_form(v, w):
    return -w["rho"] * G_MM_S2 * v[2]        # weight along -Z


def surface_mass_form(rho_surface: float) -> BilinearForm:
    @BilinearForm
    def form(u, v, w):
        return rho_surface * dot(u, v)
    return form


class Model:
    """Mesh, basis, patches and averaging vectors for one density."""

    def __init__(self, msh: Path, rep: dict, loaded: bool):
        self.rep = rep
        self.loaded = loaded
        self.mesh = skfem.MeshTet.load(msh)
        self.element = skfem.ElementVector(skfem.ElementTetP2())
        self.basis = Basis(self.mesh, self.element)
        self.mat = Materials(rep, loaded)
        self.N = self.basis.N

        m = self.mesh
        p = rep["parameters"]
        self.facets = {}
        for name, pad in rep["pads"].items():
            self.facets[name] = m.facets_satisfying(lambda x, pad=pad: in_box(x, pad), boundaries_only=True)
        mounted = rep.get("fixture_mounted") if loaded else None
        if mounted:
            # R02 on its base plate: fixed only under the four bolt washers.
            pts = np.array(mounted["points"])
            x_fix, radius = mounted["x"], mounted["radius"]

            def at_bolts(x):
                d2 = np.min([(x[1] - py) ** 2 + (x[2] - pz) ** 2 for py, pz in pts], axis=0)
                return (np.abs(x[0] - x_fix) < 0.05) & (d2 < radius ** 2)
            self.facets["fixture"] = m.facets_satisfying(at_bolts, boundaries_only=True)
        elif "outside_box" in rep["fixture"]:
            by0, by1, bz0, bz1 = rep["fixture"]["outside_box"]
            self.facets["fixture"] = m.facets_satisfying(
                lambda x: (np.abs(x[0]) < 0.05)
                          & ((x[1] < by0) | (x[1] > by1) | (x[2] < bz0) | (x[2] > bz1)),
                boundaries_only=True)
        else:
            half = rep["fixture"]["outside_square_half"]
            self.facets["fixture"] = m.facets_satisfying(
                lambda x: (np.abs(x[0]) < 0.05) & (np.maximum(np.abs(x[1]), np.abs(x[2])) > half),
                boundaries_only=True)
        self.mounted = bool(mounted)
        self.facets["platform"] = m.facets_satisfying(
            lambda x: (np.abs(x[0] - p["b"]) < 0.05) & (np.abs(x[1]) < p["a_p"] + 0.05)
                      & (np.abs(x[2]) < p["a_p"] + 0.05), boundaries_only=True)
        for name, f in self.facets.items():
            if f.size == 0:
                raise RuntimeError(f"patch '{name}' selected no facets")

        self.fixed = self.basis.get_dofs(facets=self.facets["fixture"]).all()
        self.free = np.setdiff1d(np.arange(self.N), self.fixed)

    def facet_basis(self, name: str) -> FacetBasis:
        return FacetBasis(self.mesh, self.element, facets=self.facets[name])

    def mean_vector(self, name: str, component: int) -> tuple[np.ndarray, float]:
        """Vector a with a.x = mean displacement component over the patch, and the area."""
        fb = self.facet_basis(name)
        area = float(Functional(lambda w: 1.0 + 0.0 * w.x[0]).assemble(fb))

        @LinearForm
        def form(v, w):
            return v[component]
        return form.assemble(fb) / area, area

    def actuator_vectors(self) -> dict[str, np.ndarray]:
        """Per driven leg: a = mean(stage pad) - mean(frame pad) along the leg axis.

        k * a a^T is the actuator spring; -a is the unit force pair of its extension.
        """
        out = {}
        for leg in ("Y", "Z"):
            comp = AXIS[leg.lower()]
            a_stage, _ = self.mean_vector(f"{leg}_stage", comp)
            a_frame, _ = self.mean_vector(f"{leg}_frame", comp)
            out[leg] = a_stage - a_frame
        return out

    def fields(self) -> dict:
        if not hasattr(self, "_fields"):
            self._fields = material_fields(self.mat, self.basis)
        return self._fields

    def gravity(self) -> np.ndarray:
        workers = assembly_workers()
        if workers == 1:
            return gravity_form.assemble(self.basis, rho=self.fields()["rho"])
        import multiprocessing as mp
        chunks = np.array_split(np.arange(self.mesh.t.shape[1]), workers)
        _ASM_STATE.update(mesh=self.mesh, element=self.element, mat=self.mat, chunks=chunks)
        try:
            with mp.get_context("fork").Pool(workers) as pool:
                parts = pool.map(_gravity_chunk, range(workers))
        finally:
            _ASM_STATE.clear()
        return np.sum(parts, axis=0)

    def assemble(self, with_mass: bool) -> tuple[sp.csr_matrix, sp.csr_matrix | None]:
        workers = assembly_workers()
        if workers > 1:
            K, M = _parallel_assemble(self.mesh, self.element, self.mat, self.N, with_mass, workers)
        else:
            f = self.fields()
            K = stiffness_form.assemble(self.basis, lam=f["lam"], mu=f["mu"]).tocsr()
            M = mass_form.assemble(self.basis, rho=f["rho"]).tocsr() if with_mass else None
        if not with_mass:
            return K, None
        # Half the actuator mass on each of its pads.
        act = self.rep["actuator"]
        half_t = act["mass_g"] / 2 * 1e-6
        for name in self.rep["pads"]:
            fb = self.facet_basis(name)
            area = float(Functional(lambda w: 1.0 + 0.0 * w.x[0]).assemble(fb))
            M = M + surface_mass_form(half_t / area).assemble(fb).tocsr()
        return K, M

    def reduce(self, A: sp.spmatrix) -> sp.csr_matrix:
        return A.tocsr()[self.free][:, self.free].tocsr()

    def expand(self, x_free: np.ndarray) -> np.ndarray:
        full = np.zeros((self.N,) + x_free.shape[1:])
        full[self.free] = x_free
        return full

    def platform_nodes(self) -> tuple[np.ndarray, np.ndarray]:
        """Vertex positions (3, n) on the platform front face and their DOF indices (3, n)."""
        verts = np.unique(self.mesh.facets[:, self.facets["platform"]])
        return self.mesh.p[:, verts], self.basis.nodal_dofs[:, verts]

    def rigid_fit(self, x: np.ndarray, reference: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Least-squares rigid motion (t, theta) of the platform front face about `reference`."""
        r, dofs = self.platform_nodes()
        u = x[dofs]                                       # (3, n)
        rel = (r.T - reference)                           # (n, 3)
        n = rel.shape[0]
        A = np.zeros((3 * n, 6))
        for i, (rx, ry, rz) in enumerate(rel):
            rows = slice(3 * i, 3 * i + 3)
            A[rows, :3] = np.eye(3)
            # u = t + theta x r  ->  theta x r = -[r]x theta
            A[rows, 3:] = -np.array([[0, -rz, ry], [rz, 0, -rx], [-ry, rx, 0]])
        sol, *_ = np.linalg.lstsq(A, u.T.reshape(-1), rcond=None)
        return sol[:3], sol[3:]


class PardisoFactorised:
    """PARDISO factorisation of a reduced matrix, applied to many right-hand sides."""

    def __init__(self, A: sp.csr_matrix):
        if pypardiso is None:
            raise RuntimeError("pypardiso is required; see ../simulations/fem_r01/requirements.txt")
        self.A = A.tocsr()
        self.A.sort_indices()
        self.solver = pypardiso.PyPardisoSolver()
        self.solver.factorize(self.A)

    def solve(self, B: np.ndarray) -> np.ndarray:
        # PARDISO takes all right-hand sides in one call (one forward/backward
        # sweep per column, no Python loop).
        B = np.ascontiguousarray(np.asarray(B, dtype=np.float64))
        return self.solver.solve(self.A, B)


class CudssFactorised:
    """The same on an NVIDIA GPU through cuDSS (nvmath-python + CuPy).

    Factorising a 740 k-dof plate takes the A100 about as long as 28 PARDISO
    threads (8 s), but each triangular solve afterwards is ~100x faster, and the
    shift-invert eigensolver does hundreds of them. Numbers agree with PARDISO
    to the solver tolerance (bench_solver.py). Selected with PIEZO_SOLVER=gpu;
    anything that fails here (no CUDA, no memory) falls back to PARDISO.
    """

    def __init__(self, A: sp.csr_matrix):
        import cupy as cp
        import cupyx.scipy.sparse as cps
        from nvmath.sparse.advanced import DirectSolver, DirectSolverOptions
        self.cp = cp
        self.n = A.shape[0]
        A = A.tocsr()
        A.sort_indices()
        options = DirectSolverOptions(multithreading_lib=_cudss_threading_lib())
        # One persistent RHS buffer: the solver is bound to its shape and strides.
        self.b_gpu = cp.zeros((self.n, 1), dtype=np.float64, order="F")
        self.solver = DirectSolver(cps.csr_matrix(A.astype(np.float64)), self.b_gpu, options=options)
        self.solver.plan()
        self.solver.factorize()
        cp.cuda.Device().synchronize()

    def solve(self, B: np.ndarray) -> np.ndarray:
        # The DirectSolver is bound to the RHS shape it was planned with (one
        # column), so several columns go one at a time - a solve is ~15 ms.
        cp = self.cp
        B = np.asarray(B, dtype=np.float64)
        B2 = B.reshape(self.n, -1)
        X = np.empty_like(B2)
        for j in range(B2.shape[1]):
            self.b_gpu[:, 0] = cp.asarray(B2[:, j])
            self.solver.reset_operands(b=self.b_gpu)
            X[:, j] = cp.asnumpy(self.solver.solve())[:, 0]
        return X.reshape(B.shape)

    def __del__(self):
        try:
            self.solver.free()
        except Exception:
            pass


def _cudss_threading_lib() -> str | None:
    """Path of cuDSS's OpenMP threading layer (speeds up the CPU-side planning), if present."""
    import glob
    import sys
    hits = glob.glob(str(Path(sys.prefix) / "lib" / "python*" / "site-packages" / "nvidia" / "cu*" / "lib"
                         / "libcudss_mtlayer_gomp.so*"))
    return sorted(hits)[0] if hits else None


def solver_backend() -> str:
    return os.environ.get("PIEZO_SOLVER", "pardiso").lower()


def Factorised(A: sp.csr_matrix):
    """Factorise A with the backend PIEZO_SOLVER names (pardiso, the default, or gpu)."""
    if solver_backend() == "gpu":
        try:
            return CudssFactorised(A)
        except Exception as e:                       # no CUDA, no nvmath, out of GPU memory ...
            print(f"  [gpu solver unavailable ({type(e).__name__}: {e}); using PARDISO]", flush=True)
    return PardisoFactorised(A)


class Sprung:
    """(A + U diag(k) U^T)^-1 via Woodbury on a factorised A."""

    def __init__(self, base, U: np.ndarray, k: np.ndarray):
        self.base, self.U = base, U
        self.AiU = base.solve(U)
        self.S = np.diag(1.0 / k) + U.T @ self.AiU

    def solve(self, B: np.ndarray) -> np.ndarray:
        AiB = self.base.solve(B)
        return AiB - self.AiU @ np.linalg.solve(self.S, self.U.T @ AiB)

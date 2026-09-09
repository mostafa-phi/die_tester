# Running the piezo FE chain on the CUDA compute host

How to run `cad/piezo/parallel_yz` on the group's Linux box instead of the
laptop: 2.5 hours becomes about 4.5 minutes for three mesh densities, with
identical numbers. Written 2026-09-08 after the R05 runs; the measurements
behind every claim are in `../README.md`, section "Running the chain on the
compute host".

## The machine

| | |
|---|---|
| reach it | `ssh compute` (alias in the user's Windows `~/.ssh/config`; key-based, no password) |
| host | mlcuda2, Ubuntu 20.04, shared account `philab` with a dozen other users |
| CPU | 4 × Xeon Platinum 8280 = 112 cores / 224 threads on 4 NUMA nodes (28 cores each) |
| memory | 3 TB |
| GPU | 2 × A100 PCIe 40 GB, driver 575, CUDA 12.9 |
| disk | ~560 GB free on `/`; our files live under `~/mostafa` |
| our environment | `~/mostafa/envs/piezo` (micromamba: Python 3.11, CadQuery 2.8, gmsh 4.12.2, scikit-fem 10.0.2, pypardiso, CuPy, nvmath-python + cuDSS) |
| our checkout | `~/mostafa/die_tester/cad/piezo/parallel_yz` (a copy synced from the laptop, not a git clone) |

Per core the host is no faster than the laptop. All of the gain is that the
work is split: one process per (case, density) pinned to a socket, assembly
over 28 forked workers, factorisation and solves on the GPUs, meshes built once
in parallel.

## Etiquette on a shared box

- Everything under `~/mostafa`. Nothing installed system-wide, no `sudo`, no
  edits outside that folder.
- Each job is capped at `-Threads` cores (default 28 = one socket) and pinned
  with `numactl`; seven jobs at once use all four sockets for about three
  minutes. Check `cat /proc/loadavg` and `nvidia-smi` before launching a
  four-density run if others are working.
- A job on the GPU needs up to ~10 GB per 1.4 M dofs; jobs alternate between
  the two GPUs. If a GPU is full the job prints
  `[gpu solver unavailable ...]` and continues on PARDISO.

## Everyday loop (from PowerShell, in `cad/piezo/parallel_yz`)

```powershell
.\remote\remote.ps1 up                                   # sync sources, reports, STEP
.\remote\remote.ps1 run r05 -Sizes "0.70 0.55 0.45"      # launch the chain (default -Solver gpu)
.\remote\remote.ps1 status r05                           # tail the logs
.\remote\remote.ps1 fetch r05                            # results back into variants\r05\
```

Then locally: `python remote\summary.py variants\r05` for one screen of
numbers, `git checkout -- variants\r05\STEP variants\r05\geometry_report.json`
if the fetch brought back the host's rebuilt (identical) geometry files, and
commit the result JSONs, renders and README numbers together as usual.

`run` returns immediately; the chain continues under `nohup`. It is finished
when `status` shows `exit 0` at the end of `chain.log`. A three-density R05
run takes 4.5 minutes; `status` every minute or so is fine.

Options: `-Threads N` (MKL threads and assembly workers per job), `-Sizes`
(mesh densities in mm, coarse to fine; the bare modal runs at the first one),
`-Solver gpu|pardiso`, `-Host_ name` (another ssh alias), `-Python path`
(local pic-env, used to build the sync zip).

## What the chain does (`run_chain.sh` on the host)

1. `model.py --variant v`: rebuilds STEP and `geometry_report.json` from the
   synced `model.py` (CadQuery runs headless on Linux).
2. `mesh.py --sizes <sizes> 0.9 1.2 --jobs 16`: every mesh the chain needs,
   bare and loaded, in parallel gmsh processes, into `variants/v/work/`. Each
   mesh gets a sidecar `<name>.msh.json` keyed by the STEP's hash and the size
   parameters; `mesh.build()` returns the cached description when the key
   matches, so nothing downstream ever re-meshes.
3. All at once, round-robin over the NUMA nodes and the GPUs: `solve_static`
   and `solve_modal --loaded` at every density (`--partial` files), the bare
   `solve_modal` at the coarsest density, `figures.py`, `drawing.py`.
4. `solve_static --merge` and `solve_modal --loaded --merge` combine the
   per-density partials into `static_r01.json` / `modal_loaded_r01.json` with
   the same convergence gate as a sequential run.
5. `figures_results.py` (convergence curves, mode shapes) from the merged files.

Logs: `variants/v/work/chain.log` (stage summary with exit codes and times),
one `<job>.log` per job, `mesh.log`, `merge_*.log`.

## Where the speed comes from (and the knobs)

| lever | where | knob |
|---|---|---|
| one process per (case, density) | `run_chain.sh` | `-Sizes`, `-Threads` |
| assembly over forked element chunks | `fe_common.assembly_workers()` | env `PIEZO_ASSEMBLY_WORKERS` (Linux only; Windows has no fork and stays serial) |
| cuDSS factorisation and solves on the A100 | `fe_common.CudssFactorised` | env `PIEZO_SOLVER=gpu` / `pardiso`; `CUDA_VISIBLE_DEVICES` picks the card |
| mesh cache and parallel meshing | `mesh.py` | `--jobs`; delete `work/*.msh*` to force a rebuild |
| figures alongside the solves | `run_chain.sh` | - |

Measured on R05 (`../README.md` has the full table): laptop sequential 2.5 h
(two densities) → host sequential 20 min → parallel PARDISO 10 min → cuDSS
6 min → mesh stage and overlapped tail 4 min 25 s, three densities.

## Setting it up again (new host, lost environment)

1. Make sure `ssh <alias> hostname` works from PowerShell without a prompt.
2. `.\remote\remote.ps1 setup -Host_ <alias>` uploads `remote_env.sh` and
   builds the environment in the background (about 10 minutes); follow with
   `ssh <alias> tail -f ~/mostafa/env_install.log` until it prints `ENV_OK`.
   CadQuery comes from conda-forge, gmsh and scikit-fem from pip (their OCCT
   builds clash on conda), the CUDA stack from pip
   (`nvmath-python[cu12] cupy-cuda12x nvidia-cudss-cu12`; needs driver ≥ 525).
3. `.\remote\remote.ps1 up`, then
   `ssh <alias> "cd ~/mostafa/die_tester/cad/piezo/parallel_yz && ~/mostafa/envs/piezo/bin/python remote/smoke.py"`
   (imports and a PARDISO solve) and
   `... remote/test_gpu_backend.py --variant r05 --size 0.70` (cuDSS against
   PARDISO, must print a relative difference below 1e-8).
4. `remote/bench_solver.py --variant r05 --size 0.60 --serial` and
   `remote/bench_setup.py` reproduce the timing tables if the hardware changes.

## Things that bit, so they do not bite again

- **Use the PowerShell tool / a PowerShell window for ssh.** Git Bash's ssh
  does not read the same `~/.ssh/config` and fails with
  `Permission denied (publickey)`.
- **Sync is a zip, not tar.** OneDrive marks directories read-only; Windows
  tar records them as `dr-xr-xr-x` and GNU tar then cannot create their
  contents. `remote/pack.py` builds the zip and strips CRLF from `.py`/`.sh`.
- **`up` never sends result files** (`static_r01.json`, `modal*_r01.json`,
  renders, manufacturing). It once overwrote a finished run on the host.
  Results only travel host → laptop through `fetch`.
- **Do not edit `run_chain.sh` on the host while a chain runs.** Bash reads
  scripts incrementally; the script is wrapped in `main()` so a resync
  mid-run is harmless, but a hand edit of a running copy is not.
- **The cuDSS `DirectSolver` is bound to its RHS buffer.** `CudssFactorised`
  keeps one `(n, 1)` Fortran-ordered CuPy array and solves columns one at a
  time (15 ms each); passing a different array or shape raises a
  strides/shape error.
- **Quoting through `ssh` from PowerShell.** Anything with parentheses or
  nested quotes belongs in a script file that is `scp`'d over, not in an
  inline `-c` string. `sed -i 's/\r$//'` any file copied with `scp` alone.
- **`mesh_seconds` in the static results counts mesh load + basis** (5-18 s)
  once the cache hits; gmsh itself is skipped.
- The host's `python3` is 3.8; always call `~/mostafa/envs/piezo/bin/python`.

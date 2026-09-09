#!/bin/bash
# Run the full FE chain of one variant on the compute host, the three solves in
# parallel.  Invoked by remote.ps1; can also be run by hand on the host:
#
#     bash remote/run_chain.sh r05 [threads_per_solve]
#
# Layout on the host (set up once by remote.ps1 setup):
#     ~/mostafa/envs/piezo/bin/python      micromamba env: cadquery, gmsh, scikit-fem, pypardiso
#     ~/mostafa/die_tester/cad/piezo/parallel_yz   this folder, synced by remote.ps1 up
#
# Writes variants/<v>/work/chain.log plus one log per step; "exit 0" at the end
# of chain.log means everything finished.
set -u
variant=${1:?variant name}
threads=${2:-32}
here=$(cd "$(dirname "$0")/.." && pwd)
py=$HOME/mostafa/envs/piezo/bin/python
export MKL_NUM_THREADS=$threads OMP_NUM_THREADS=$threads MPLBACKEND=Agg
cd "$here"
work=variants/$variant/work
mkdir -p "$work"
log=$work/chain.log
exec > "$log" 2>&1
echo "=== $(date -Is) $variant on $(hostname), $threads threads per solve"

# 1. geometry (CadQuery) - rebuild so the STEP and report match the synced model.py
$py -u model.py --variant "$variant" > "$work/model.log" 2>&1
echo "model.py exit $?"

# 2. the three solves side by side
$py -B solve_static.py --variant "$variant" > "$work/static.log" 2>&1 &
p_static=$!
$py -B solve_modal.py --variant "$variant" --loaded > "$work/modal_loaded.log" 2>&1 &
p_loaded=$!
$py -B solve_modal.py --variant "$variant" --sizes 0.6 > "$work/modal_bare.log" 2>&1 &
p_bare=$!
wait $p_static;  echo "solve_static exit $?"
wait $p_loaded;  echo "solve_modal --loaded exit $?"
wait $p_bare;    echo "solve_modal (bare) exit $?"

# 3. figures and the shop sheet
$py -B figures.py --variant "$variant" > "$work/figures.log" 2>&1;          echo "figures exit $?"
$py -B figures_results.py --variant "$variant" > "$work/figures_results.log" 2>&1; echo "figures_results exit $?"
$py -B drawing.py --variant "$variant" > "$work/drawing.log" 2>&1;          echo "drawing exit $?"
echo "=== $(date -Is) done"
echo "exit 0"

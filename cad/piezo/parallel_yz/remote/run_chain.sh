#!/bin/bash
# Run the full FE chain of one variant on the compute host with every
# (case, density) as its own process, pinned to a NUMA node.  Invoked by
# remote.ps1; can also be run by hand on the host:
#
#     bash remote/run_chain.sh r05 [threads_per_solve] [sizes...]
#     PIEZO_SOLVER=gpu bash remote/run_chain.sh r05 ...     # factorise on the A100s (cuDSS)
#
# Default sizes 0.70 0.55 (the statics and the loaded modal at each; the bare
# modal at the coarsest one).  Jobs run all at once, round-robin over the four
# sockets, each with `threads` MKL threads and as many assembly workers; the
# per-density results are merged afterwards with the solvers' --merge.
#
# Layout on the host (set up once by remote.ps1 setup):
#     ~/mostafa/envs/piezo/bin/python              micromamba env
#     ~/mostafa/die_tester/cad/piezo/parallel_yz   this folder, synced by remote.ps1 up
#
# Writes variants/<v>/work/chain.log plus one log per job; "exit 0" at the end
# of chain.log means everything finished.
set -u

# Everything inside main() so bash parses the whole file before running it: a
# `remote.ps1 up` that rewrites this script mid-run then cannot derail it.
main() {
variant=${1:?variant name}
threads=${2:-28}
shift 2 2>/dev/null
sizes=${*:-"0.70 0.55"}
here=$(cd "$(dirname "$0")/.." && pwd)
py=$HOME/mostafa/envs/piezo/bin/python
export MKL_NUM_THREADS=$threads OMP_NUM_THREADS=$threads PIEZO_ASSEMBLY_WORKERS=$threads MPLBACKEND=Agg
export PIEZO_SOLVER=${PIEZO_SOLVER:-pardiso}
cd "$here"
work=variants/$variant/work
mkdir -p "$work"
log=$work/chain.log
exec > "$log" 2>&1
echo "=== $(date -Is) $variant on $(hostname), $threads threads per job, solver $PIEZO_SOLVER, sizes: $sizes"

# 1. geometry (CadQuery) - rebuild so the STEP and report match the synced model.py
$py -u model.py --variant "$variant" > "$work/model.log" 2>&1
echo "model.py exit $?"

# 2. one process per (case, density), pinned round-robin to the NUMA nodes
nodes=$(numactl -H | awk '/^available/ {print $2}')
n=0
pids=()
names=()
gpus=$(nvidia-smi -L 2>/dev/null | wc -l)
launch() {                       # launch <name> <args...>
    local name=$1; shift
    local node=$((n % nodes))
    local gpu=""
    [ "$gpus" -gt 0 ] && gpu=$((n % gpus))
    CUDA_VISIBLE_DEVICES=$gpu numactl --cpunodebind=$node --membind=$node $py -B "$@" > "$work/$name.log" 2>&1 &
    pids+=($!); names+=("$name"); n=$((n + 1))
    echo "  $name -> node $node (pid $!)"
}
static_parts=(); loaded_parts=()
for h in $sizes; do
    launch "static_h$h" solve_static.py --variant "$variant" --sizes "$h" --partial "$work/partial_static_h$h.json"
    static_parts+=("$work/partial_static_h$h.json")
    launch "modal_loaded_h$h" solve_modal.py --variant "$variant" --loaded --sizes "$h" --partial "$work/partial_modal_loaded_h$h.json"
    loaded_parts+=("$work/partial_modal_loaded_h$h.json")
done
bare_h=$(echo $sizes | awk '{print $1}')
launch "modal_bare_h$bare_h" solve_modal.py --variant "$variant" --sizes "$bare_h"
for i in "${!pids[@]}"; do
    wait "${pids[$i]}"; echo "${names[$i]} exit $? ($(date +%T))"
done

# 3. merge the per-density runs into the result files (convergence check lives there)
$py -B solve_static.py --variant "$variant" --merge "${static_parts[@]}" > "$work/merge_static.log" 2>&1
echo "merge static exit $?"
$py -B solve_modal.py --variant "$variant" --loaded --merge "${loaded_parts[@]}" > "$work/merge_modal_loaded.log" 2>&1
echo "merge modal_loaded exit $?"

# 4. figures and the shop sheet
$py -B figures.py --variant "$variant" > "$work/figures.log" 2>&1;                 echo "figures exit $?"
$py -B figures_results.py --variant "$variant" > "$work/figures_results.log" 2>&1; echo "figures_results exit $?"
$py -B drawing.py --variant "$variant" > "$work/drawing.log" 2>&1;                 echo "drawing exit $?"
echo "=== $(date -Is) done"
echo "exit 0"
}

main "$@"

#!/bin/bash
# Run the chain for several variants one after another on the compute host
# (each chain already fills the machine).  Launched by hand:
#
#     ssh compute
#     cd ~/mostafa/die_tester/cad/piezo/parallel_yz
#     PIEZO_SOLVER=gpu nohup bash remote/sweep.sh "0.70 0.55" m6t50k21 m8t50k21 ... > variants/sweep.log 2>&1 &
#
# First argument: the densities (one quoted string); the rest: variant names.
set -u
sizes=${1:?sizes}
shift
here=$(cd "$(dirname "$0")/.." && pwd)
cd "$here"
echo "=== sweep $(date -Is): $* at $sizes"
for v in "$@"; do
    t0=$(date +%s)
    bash remote/run_chain.sh "$v" 28 $sizes
    status=$(tail -1 "variants/$v/work/chain.log")
    echo "$v: $status in $(( $(date +%s) - t0 )) s"
done
echo "=== sweep done $(date -Is)"

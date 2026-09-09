#!/bin/bash
# Build the piezo FE environment under ~/mostafa on the compute host.
# gmsh comes from pip (its wheel bundles its own OCCT) so it does not fight
# CadQuery's occt 7.9 on conda-forge - same split as the local envs.
set -e
export MAMBA_ROOT_PREFIX=$HOME/mostafa/mm
MM=$HOME/mostafa/bin/micromamba
ENV=$HOME/mostafa/envs/piezo
rm -rf "$ENV"
$MM create -y -p "$ENV" -c conda-forge python=3.11 cadquery=2.8 scipy numpy matplotlib meshio mkl pip
"$ENV/bin/pip" install gmsh==4.12.2 scikit-fem==10.0.2 pypardiso
"$ENV/bin/python" -c "import cadquery, gmsh, skfem, pypardiso, scipy, numpy; print('cadquery', cadquery.__version__, 'gmsh', gmsh.__version__, 'skfem', skfem.__version__, 'scipy', scipy.__version__, 'numpy', numpy.__version__)"
echo ENV_OK

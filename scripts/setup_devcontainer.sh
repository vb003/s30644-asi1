#!/usr/bin/env bash
set -euo pipefail

if conda env list | awk '{print $1}' | grep -qx 'asi-ml'; then
  conda env update -n asi-ml -f environment.yml --prune
else
  conda env create -f environment.yml
fi

/opt/conda/envs/asi-ml/bin/python -m ipykernel install \
  --user \
  --name asi-ml \
  --display-name "Python (asi-ml)"

/opt/conda/envs/asi-ml/bin/pre-commit install

echo "Środowisko asi-ml jest gotowe."

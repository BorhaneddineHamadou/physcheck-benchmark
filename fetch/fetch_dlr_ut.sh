#!/usr/bin/env bash
# Materialize the git-ignored DLR-UT scenario files (see corpora/dlr_ut/PROVENANCE.md).
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
curl -L -o "$tmp/dlr_ut.zip" "https://zenodo.org/api/records/20919480/files/DLR-Urban-Traffic-dataset_v1-3-1.zip/content"
python3 - "$tmp/dlr_ut.zip" <<'PY'
import sys, zipfile, pathlib
z = zipfile.ZipFile(sys.argv[1])
out = pathlib.Path("corpora/dlr_ut/scenarios")
out.mkdir(parents=True, exist_ok=True)
for n in z.namelist():
    if n.endswith(".xosc"):
        (out / pathlib.Path(n).name).write_bytes(z.read(n))
        print("wrote", pathlib.Path(n).name)
PY
rm -rf "$tmp"

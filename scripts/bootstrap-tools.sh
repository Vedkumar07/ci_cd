#!/usr/bin/env bash
set -euo pipefail
# Repo-local, pinned Linux amd64 binaries; no sudo or shell installer pipes.
[[ "$(uname -s)-$(uname -m)" == Linux-x86_64 ]] || { echo 'Linux x86_64 required'; exit 1; }
mkdir -p .tools/bin
TASK_TOOLS_TMP="$(mktemp -d)"
trap 'rm -rf "$TASK_TOOLS_TMP"' EXIT
python3 - "$TASK_TOOLS_TMP" <<'PYTOOLS'
import hashlib, pathlib, sys, tarfile, urllib.request
work = pathlib.Path(sys.argv[1])
target = pathlib.Path('.tools/bin')
items = [
 ('helm', 'https://get.helm.sh/helm-v3.19.0-linux-amd64.tar.gz', '.sha256sum', 'linux-amd64/helm'),
 ('kubectl', 'https://dl.k8s.io/release/v1.34.1/bin/linux/amd64/kubectl', '.sha256', None),
 ('kind', 'https://kind.sigs.k8s.io/dl/v0.30.0/kind-linux-amd64', '.sha256sum', None),
]
for name, url, checksum, member in items:
    if (target/name).exists():
        continue
    data = urllib.request.urlopen(url, timeout=60).read()
    expected = urllib.request.urlopen(url+checksum, timeout=60).read().decode().split()[0]
    assert hashlib.sha256(data).hexdigest() == expected, f'{name} checksum mismatch'
    artifact = work/name
    artifact.write_bytes(data)
    if member:
        with tarfile.open(artifact) as archive:
            data = archive.extractfile(member).read()
    (target/name).write_bytes(data)
    (target/name).chmod(0o755)
    print(f'Installed {name} into {target}')
PYTOOLS

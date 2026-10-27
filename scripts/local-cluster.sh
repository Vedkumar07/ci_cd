#!/usr/bin/env bash
set -euo pipefail
export PATH="$PWD/.tools/bin:$PATH"
kind get clusters | grep -qx poc2 || kind create cluster --name poc2 --kubeconfig "$PWD/.tools/kubeconfig"
export KUBECONFIG="$PWD/.tools/kubeconfig"
# Never use the user's current cluster context for this local demo.
kubectl config use-context kind-poc2
docker build -t ci-cd-poc:local .
TASK_IMAGE_ID="$(docker image inspect ci-cd-poc:local --format '{{.Id}}')"
TASK_IMAGE_TAG="local-${TASK_IMAGE_ID:7:12}"
docker tag ci-cd-poc:local "ci-cd-poc:$TASK_IMAGE_TAG"
kind load docker-image "ci-cd-poc:$TASK_IMAGE_TAG" --name poc2
python3 scripts/poc/deploy.py --image ci-cd-poc --tag "$TASK_IMAGE_TAG"
kubectl -n poc2 rollout status deployment/poc2 --timeout=90s
echo 'Open the app with: KUBECONFIG="$PWD/.tools/kubeconfig" .tools/bin/kubectl -n poc2 port-forward service/poc2 3000:80'

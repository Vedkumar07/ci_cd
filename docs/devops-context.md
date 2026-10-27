# DevOps context and demo Q&A

## What the chart deploys and what differs

deploy/helm/ci-cd/templates/deployment.yaml deploys one non-root Next.js container per replica, with readiness/liveness probes at /api/health, resource limits, read-only root filesystem and writable temporary/cache mounts. service.yaml exposes a ClusterIP service from port 80 to container port 3000. configmap.yaml renders values.config. The config checksum triggers pod replacement when configuration changes.

values.yaml supplies base settings. values-dev.yaml overrides APP_ENV and BILLING_API_URL. staging/prod use two replicas and their corresponding service DNS names. These are illustrative internal endpoints, not real billing service addresses. Image repository/tag are supplied at deploy time. No database or Secret is included because the repo has no database service or credentials.

## How a setting reaches the pod

BILLING_API_URL is listed in config-contract.json; values-<environment>.yaml supplies it; configmap.yaml renders it; deployment.yaml envFrom injects it as an environment variable. my-app/app/api/health/route.ts checks the required keys and returns 503 with missing key names, never their values. The build never embeds these server environment settings into client JavaScript. For an actual database secret, add a separate Secret reference and corresponding drift contract support; do not put its password in ConfigMaps.

## Pipeline stages and skipped gates

.github/workflows/test.yml installs locked app dependencies, runs Python tests, checks Helm and config drift, lints/types/builds the app, and builds the Docker image. A failure triggers failure-report, which uses ci_api.py, report.py and a PR comment; pushes without a PR retain artifacts. Fork PRs do not get privileged report execution. Skipping drift permits absent runtime settings; skipping the build misses dependency/type failures; skipping Docker misses packaging errors.

.github/workflows/deploy.yml is manual on main with the poc-dev environment. It rechecks Python tests, chart/config, builds and pushes an immutable SHA image to GHCR and invokes deploy.py with the target kubeconfig. Configure environment protection in GitHub. .gitlab-ci.yml is the PDF-compatible build/test/config/docker/deploy alternative, with a .post failure report. It has no Sonar job because no Sonar project was supplied.

## Build explanation

Dockerfile uses Node 22 Debian slim in dependency/build/runtime stages. npm ci follows the lockfile. Next's standalone output carries only needed production server dependencies; static/public files are copied explicitly. The runtime runs as the node user on port 3000. Google Fonts downloads were removed from layout.tsx because the existing CSS already uses system fonts. The build selects webpack to work in environments where Turbopack worker port binding is restricted.

## Deploy, diagnose, and roll back

scripts/local-cluster.sh builds/loads the image into the dedicated kind-poc2 cluster, then calls scripts/poc/deploy.py. The deploy wrapper checks drift, starts a diagnostics watcher, and uses Helm 3 upgrade --install --atomic --wait --timeout 180s. diagnostics.py saves events, pod descriptions, current/previous logs, Helm history/status while Helm is still running. This is best-effort sampling: a very short-lived pod or missing RBAC can still leave incomplete evidence. It never reads Kubernetes Secret resources or helm get values, which could contain secrets. Applied non-secret settings are saved in artifacts/diagnostics/applied-config.txt from the rendered ConfigMap plus image arguments; arbitrary applied secret values are intentionally not archived.

A human can inspect `helm history poc2 -n poc2` and then explicitly run `helm rollback poc2 <revision> -n poc2 --wait`. The reporter never invokes these actions. For the local cluster set `KUBECONFIG=$PWD/.tools/kubeconfig` first. Helm's --atomic behavior is part of the explicitly requested deployment command, separate from the reporter.

## Evidence and data handling

common.py masks configured secret environment values, common credential fields, authorization headers, URL credentials and private-key blocks before truncation. Redaction is best-effort, not a proof that arbitrary application logs contain no sensitive business data. Confirm policy and inspect sanitized fixtures before enabling model calls. Reports cap ten failed jobs at 8 KB each; model evidence is capped at 64 KB; API downloads are capped at 2 MB. Oversized evidence is labeled unavailable rather than sent unbounded. Artifacts expire in seven days.

When Dockerfile, pipeline or chart changes, refresh this file and the root agent context. The Q&A adapter receives these documents plus actual Dockerfile/pipeline/chart sources and must cite paths. Installed bmad-deep-recon is also available interactively for deeper questions.

## Selected AI integration

GitHub Actions is the selected CI platform and Codex is the selected headless agent. scripts/bootstrap-agent.sh pins @openai/codex 0.164.0. The failure-report step receives secrets.OPENAI_API_KEY as CODEX_API_KEY only after package installation. report.py starts codex exec in a temporary directory, ignores user configuration/rules, uses ephemeral sessions and the read-only sandbox, disables shell execution, apps, multi-agent, browser/computer use and web search, and accepts only completed explanatory output. It records actual input/cached/output token counts; billed dollar cost remains unknown. POC_CODEX_MODEL optionally selects a model, otherwise Codex uses its default. Live runs require the AI and log-policy flags plus the model credential. GitLab is retained as reference only.

Q&A startup/provider failures display a bounded, redacted diagnostic and save it beside the requested output as .error.txt. No answer file is created on failure. CI falls back to an evidence summary and records the diagnostic in its log and usage sidecar.

Repeatable capability 1/2 acceptance cases are in scripts/poc/scenarios.py and docs/test-cases.md. They run a synthetic assertion failure plus real Helm drift checks on artifact copies and force deterministic reporting. They do not test GitHub collection/comment posting; the document describes that separate PR procedure.

PR reports now include an AI explanation unavailable section when AI is disabled or unavailable. It includes a bounded/redacted reason, a next step and machine-readable ai_availability in the usage sidecar. Disabled AI records zero tokens; unsuccessful AI paths record usage/cost as unknown. The underlying pipeline evidence remains in the same report.


## Gemini reporting

GitHub CI and deployment failure-report jobs default to `POC_AI_PROVIDER=gemini`.
Store the Google AI Studio key as the **Actions** repository secret `GEMINI_API_KEY`
(Settings → Secrets and variables → Actions), not an Agents secret and not
`OPENAI_API_KEY`. Keep `POC_AI_ENABLED=true` and `POC_LOG_POLICY_APPROVED=true`
only with approval to send sanitized logs to Google. Existing approval for a
different provider should be reviewed for Google before enabling it.
`POC_GEMINI_MODEL` optionally overrides the default `gemini-2.5-flash`.

The Gemini adapter in `scripts/poc/report.py` uses Google's fixed HTTPS
`generateContent` endpoint with a header credential and no tools. Redirects are
rejected. Requests time out after 180 seconds; responses are capped at 2 MB.
Only completed text is accepted. Errors retain the deterministic evidence report
and a bounded, redacted availability diagnostic. Token counts come from
`usageMetadata`; billed cost remains unknown. BMAD is still rendered with the
official renderer and report-only overrides. Gemini setup installs the renderer
without the Codex CLI.

For local use, securely export `GEMINI_API_KEY`, set `POC_AI_PROVIDER=gemini`
and the two policy flags, run `bash scripts/bootstrap-agent.sh --renderer-only`,
source `.tools/agent.env`, and use the existing demo or Q&A command.
The local default remains Codex for compatibility. In GitHub, setting the
repository variable `POC_AI_PROVIDER=codex` restores the Codex adapter with the
`OPENAI_API_KEY` Actions secret. Both adapters remain report-only.

Reference: https://ai.google.dev/api/generate-content

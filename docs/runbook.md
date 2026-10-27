# POC-2 activation runbook

## GitHub Actions + Codex (selected setup)

1. Push the reviewed changes to a branch and open a PR. Root workflows run automatically. The verify/docker jobs need no deployment credentials. Failure reporting uses the job-scoped GITHUB_TOKEN with actions:read and PR/issues write. Repository/organization settings must permit these writes. Fork reports are skipped; normal verification still runs.
2. For AI reporting, set repository variables POC_AI_ENABLED=true and POC_LOG_POLICY_APPROVED=true only after data policy approval; store OPENAI_API_KEY as an Actions secret. The workflows pass it as CODEX_API_KEY only to the reporting step, after dependency installation. The bootstrap pins Codex CLI 0.164.0 and uv 0.13.6. Optionally set POC_CODEX_MODEL to an account-supported model; otherwise the pinned CLI chooses its default. A local ChatGPT/Codex sign-in is not automatically available to a hosted GitHub runner.
3. For deployment create a protected `poc-dev` environment. Store KUBECONFIG_DATA as a secret containing the kubeconfig text for the intended cluster. Configure environment reviewers as desired. The manual workflow only runs from main.
4. GHCR uses GITHUB_TOKEN packages:write. Make the package readable by the cluster (public demo package, or provision a registry pull secret and add imagePullSecrets support before using private packages). The current chart deliberately assumes the image is already locally loaded or publicly pullable.
5. Run POC-2 Deploy manually after reviewing the target cluster. Deploy failures save diagnostics and appear in the Actions log/artifact; the manual deploy workflow has no PR context.

## GitLab reference matching the PDF (not selected)

Import/mirror the repository to GitLab. The root .gitlab-ci.yml does not touch shared templates. Use a Docker executor runner. The Docker build job requires privileged DinD and a shared /certs/client volume; review this against your runner policy or substitute your approved image builder.

Set GITLAB_REPORT_TOKEN as masked/hidden. Reading jobs/logs needs read_api; writing MR notes needs API write permission (`api` scope on a project token), not read_api alone. Give its bot the lowest project role that can read job traces and create MR notes in your GitLab installation, then verify with a test MR. The report job does not receive deploy permissions. Restrict secrets to trusted branches; protected variables may be unavailable to ordinary MR pipelines. Fork MR reporting is intentionally excluded.

For AI enable the two POC flags and CODEX_API_KEY. The optional bootstrap needs network access to apt, npm and PyPI. For deploy set KUBECONFIG as a **file variable** pointing to the target kubeconfig; set POC_ENV to dev/staging/prod. Registry variables use GitLab's built-ins. Deployment is manual on the default branch. Restrict environment access separately.

Invalid CI YAML cannot trigger a report. Before pushing run:

```bash
# Set CI_API_V4_URL, CI_PROJECT_ID and GITLAB_REPORT_TOKEN securely.
python scripts/poc/lint_ci.py
```

This invokes the project's GitLab CI Lint endpoint. No hook is installed without your choice. A pre-push hook may call this command. Offline YAML parsing is not a substitute for the server's CI lint.

## Permissions

Deployment identity: manage releases, Deployments, Services and ConfigMaps in the target namespace plus Helm's release storage. Local kind uses its local admin identity only. Do not reuse it for production.

Diagnostics identity: get/list/watch pods and events, get pods/log; Helm history/status also needs read access to Helm's release storage (Helm normally stores release records in Secrets). Use a dedicated namespace; Helm storage read access can expose values, so scope it carefully. No arbitrary `kubectl get secrets` is executed by the collector. Report job: CI API access and MR/PR comment permission only; no kubeconfig.

## Acceptance demo

1. `python scripts/poc/demo.py` creates artificial 401, test and missing-config reports in artifacts/demo. These are labeled deterministic unless AI is enabled. Inspect report.usage.json for actual model token usage; dollar cost is not returned by Codex.
2. To test deterministic drift, use a temporary chart copy, set config.BILLING_API_URL to null in values-staging.yaml and run `python scripts/poc/drift.py --chart <copy> --env staging`. Expect exit 1 and the key/file in artifacts/drift.json. Restore only your temporary copy.
3. In a disposable PR/MR branch, introduce a failing assertion or CI command. Verify one bot comment appears and is updated on another failed run. Revert your deliberate change manually. Never force a production deployment failure.
4. On the local kind cluster, deploy a deliberately invalid image tag using the explicit deploy command, then verify diagnostics were saved before --atomic restored the previous release. This mutates only the local demo namespace.
5. For invalid CI YAML, use the GitLab lint command before push. A watcher for pipelines that cannot be created is outside scope.
6. Ask the five questions in docs/devops-context.md through the Q&A command or your coding tool with bmad-deep-recon. Compare cited files, especially the fact that there is no actual database here.

To clean up the local cluster, explicitly run `.tools/bin/kind delete cluster --name poc2` when finished. No cleanup runs automatically.

## What is needed for the actual billing service

Supply the real source/branch, Dockerfile, chart and environment values, GitLab shared template reference, artifact repository/certificate details, Sonar settings and intended cluster/registry. Replace the Next.js contract/build with the real Maven build and tests; configure external configuration and Secret handling explicitly. Do not claim the fixture 401 proves real artifact repository connectivity. Live AI testing also needs your provider credential and log-data approval.

## Codex authentication and reporting checks

Create the `OPENAI_API_KEY` Actions secret at repository Settings → Secrets and variables → Actions. Create repository variables `POC_AI_ENABLED=true` and `POC_LOG_POLICY_APPROVED=true` after the log-data policy has been approved. Keep the key out of job-level environment variables and never paste it into chat. Both CI and deployment failure-report jobs use this setup. Fork PRs remain excluded from privileged reporting.

The reporter uses the pinned CLI directly so the same adapter works locally and records turn.completed token counts in report.usage.json. Its child environment receives only PATH and the model key; HOME/CODEX_HOME are fresh temporary directories and the checkout is outside its working directory. Codex is sandboxed read-only, with command execution and external integrations disabled. No write-enabled --full-auto or sandbox-bypass option is used. OpenAI also offers the [Codex GitHub Action](https://developers.openai.com/codex/github-action/) with an API proxy for teams who prefer that credential isolation path; this implementation does not use that action or claim its proxy protections.

For local use, set CODEX_API_KEY securely in your shell, run `bash scripts/bootstrap-agent.sh`, then `source .tools/agent.env`. Set the two POC flags and run the fixture demo or Q&A command from README.md. Do not copy your local Codex auth.json into this public repository or its artifacts. [Official automation guidance](https://developers.openai.com/codex/noninteractive/) explains step-scoped API-key authentication and JSONL usage events.

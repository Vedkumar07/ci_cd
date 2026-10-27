# BMAD in CI/CD — POC-2

Runnable Next.js demonstration of the supplied **POC-2 Plan: BMAD in the CI/CD Pipeline (ubp-accept-billing-charge)**. The actual Java billing service, Maven repositories, Sonar project and production chart are not present in this repository. No production billing behavior is invented here.

Implemented: Docker standalone image; local kind Kubernetes deployment; Helm chart and dev/staging/prod values; GitHub Actions CI/manual deploy; an alternative GitLab pipeline; deterministic config drift checks; redacted, bounded failure evidence; one updated PR/MR failure comment; optional headless BMAD-informed AI explanation and Q&A; diagnostics collected during Helm deployment before atomic rollback; offline demo fixtures and tests.

## Local setup

Requires Linux x86_64, Python 3.10+, Node.js 22, npm, and a running Docker daemon.

```bash
bash scripts/bootstrap-tools.sh
export PATH="$PWD/.tools/bin:$PATH"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-poc.txt
npm ci --prefix my-app
python -m unittest discover -s tests -v
helm lint deploy/helm/ci-cd
python scripts/poc/drift.py
npm run lint --prefix my-app
npm run build --prefix my-app
python scripts/poc/demo.py
bash scripts/local-cluster.sh
```

Tool downloads are pinned and verified against upstream checksums. They stay under ignored `.tools/`. `local-cluster.sh` creates only the `poc2` kind cluster and uses its own kubeconfig; allow Docker access for your account. It builds the image, loads it into kind and deploys to namespace `poc2`. The command prints the port-forward command for http://localhost:3000. `docker compose up --build` is an alternative without Kubernetes.

## BMAD and Codex

Upstream BMAD skills are committed under `.agents/skills`, pinned to the SHA in [docs/bmad/upstream.json](docs/bmad/upstream.json), with official setup output under `_bmad`. These named skills currently come from a preview upstream revision. Review before upgrading. See [upstream BMAD](https://github.com/bmad-code-org/BMAD-METHOD).

The reporter adapts the rendered `bmad-code-review` workflow into a **single, read-only Codex explanation pass** using supplied evidence. It does not execute BMAD's full interactive/multi-reviewer workflow. The installed skills remain available for normal interactive use. `docs/agent-context.md` is manually verified repo context, not output falsely attributed to a project-context skill run.

Without AI credentials, reports explicitly say **deterministic evidence summary** and record zero tokens. To enable the Codex CLI adapter:

```bash
bash scripts/bootstrap-agent.sh
source .tools/agent.env
# Set CODEX_API_KEY securely in your shell/CI secret store, not in git.
export POC_AI_ENABLED=true
# Set only after your organization approves sending sanitized evidence to the provider.
export POC_LOG_POLICY_APPROVED=true
python scripts/poc/demo.py
python scripts/poc/report.py --question 'What does this chart deploy, and which values differ per environment?' --output artifacts/qa.md
```

Codex CLI 0.164.0 runs in an empty temporary directory with a read-only sandbox and no user config or persisted sessions. Shell execution, apps, multi-agent delegation, browser/computer use and web search are disabled; no MCP servers are configured. Only PATH and CODEX_API_KEY are inherited; no GitHub/GitLab/cluster credentials reach it. The parser rejects tool activity, incomplete turns and provider errors. This is a sandboxed explanation adapter, not a claim that all possible Codex tools are absent.

Actual token counts from Codex's turn.completed events are saved beside the report. Dollar cost is recorded as unknown, because the CLI does not return billed cost; reconcile tokens with the selected model/provider account. Calls have a 180-second timeout. CLI errors produce an explicitly labeled deterministic fallback for failures, and fail Q&A instead of inventing answers. [Official Codex non-interactive documentation](https://developers.openai.com/codex/noninteractive/) describes authentication and JSONL events.

## CI activation and remaining integration inputs

[docs/runbook.md](docs/runbook.md) documents GitHub/GitLab variables, registry access, cluster permissions, CI lint and demos. **Selected platform: GitHub Actions; selected AI: Codex.** GitHub uses `.github/workflows/`; `.gitlab-ci.yml` is retained only as a PDF-compatible reference. The old workflows inside `my-app/.github/` are not discovered by GitHub and are retained only as historical files.

Live CI comments, paid model responses, a private registry pull and remote deployment require your chosen platform and credentials. A local fixture report is not evidence that those integrations have run. See [docs/validation.md](docs/validation.md) for actual validation results.

## Standard capability 1 and 2 test cases

Run `PATH="$PWD/.tools/bin:$PATH" python3 scripts/poc/scenarios.py` for three isolated acceptance cases plus a healthy control. No API calls, deployment, or source edits occur. See [docs/test-cases.md](docs/test-cases.md) for expected results and the separate PR-comment tests.


## Gemini reporting

GitHub CI and deployment failure-report jobs default to `POC_AI_PROVIDER=gemini`.
Store the Google AI Studio key as the **Actions** repository secret `GEMINI_API_KEY`
(Settings → Secrets and variables → Actions), not an Agents secret and not
`OPENAI_API_KEY`. Keep `POC_AI_ENABLED=true` and `POC_LOG_POLICY_APPROVED=true`
only with approval to send sanitized logs to Google. Existing approval for a
different provider should be reviewed for Google before enabling it.
`POC_GEMINI_MODEL` optionally overrides the default `gemini-3.8-flash`.

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

# Validation record — 2026-10-28

Executed locally against this repository:

- 19 Python tests passed: redaction/truncation, Java placeholders and defaults, ConfigMap payload parsing, honest fallback reports, model policy gate, bot comment ownership/update, pagination, and isolated read-only Codex invocation, JSONL event validation, error handling and tool-activity rejection (mocked provider).
- Helm 3.19.0 lint passed; dev/staging/prod config checks passed.
- A temporary staging chart with BILLING_API_URL removed failed drift with exit 1 and the exact key/environment/values file.
- The three synthetic PDF failure reports were generated under artifacts/demo, explicitly deterministic, zero model tokens.
- Official BMAD setup reported ready; quick/no-code/non-interactive workflow rendering succeeded with its declared dependencies.
- Codex CLI 0.164.0 selected; the CLI version and non-interactive flags were checked. No paid API call was made.
- Next.js upgraded from 16.3.0 to 16.4.3 with compatible lockfile fixes. npm audit reported zero vulnerabilities after fixes (point-in-time result).
- App lint and production webpack build passed, including TypeScript compilation. The explicit typecheck command also passed.
- Multi-stage Docker build passed on the patched dependencies.
- A dedicated local kind poc2 cluster was created. Helm deployed the image; rollout succeeded. /api/health returned HTTP 200 and status ok.
- An explicitly forced invalid image upgrade timed out, saved ImagePullBackOff/ErrImagePull events and pod evidence, and Helm --atomic rolled back. Helm history recorded failed revision 2 and rollback revision 3. The restored app returned HTTP 200.
- The patched image was subsequently deployed as an immutable local image tag, revision 4, with a successful rollout.
- A report from the actual local Helm failure evidence was generated at artifacts/demo/local-helm-failure/report.md.
- GitHub/GitLab/Compose YAML parsed locally. git diff --check passed. This is not a claim of server-side GitLab CI lint or a hosted Actions run.

Artifacts are intentionally gitignored; reproduce them with the README/runbook commands. The local cluster remains running for inspection.

Not yet validated: live PR/MR posting, GitLab server CI lint, registry publishing/private pulls, remote cluster deployment, actual model output/cost, or Q&A answer quality. These require the chosen platform, credentials and approved log-data policy. The actual Java billing service was not supplied, so Maven/Sonar and its real property layout are not validated.

Q&A diagnostics regression checks passed: failed child processes retain provider/startup errors, JSONL error selection excludes ordinary messages, and child credentials/OpenAI key patterns are redacted. Live user-terminal failure still requires rerunning to identify its specific provider/startup error.

The standard local acceptance suite passed: healthy chart control, deliberate unittest assertion failure, absent staging BILLING_API_URL, empty dev BILLING_API_URL plus unresolved prod APP_ENV. Each negative case produced its expected nonzero job exit and a deterministic report with zero tokens. Results are in artifacts/scenarios/summary.json. Live PR tests remain separate and are not claimed by this suite.

AI-availability reporting tests passed for quota, disabled AI, missing credentials, preservation of the original pipeline failure, unknown usage on unsuccessful AI paths, and redaction/Markdown fence containment. The simulated quota example was generated without an API call. The latest local scenario-suite rerun stopped at its healthy control because the source staging BILLING_API_URL remains deliberately null; that user test change was preserved.

# Validation record — 2026-10-28

Executed locally against this repository:

- 13 Python tests passed: redaction/truncation, Java placeholders and defaults, ConfigMap payload parsing, honest fallback reports, model policy gate, bot comment ownership/update, pagination, and isolated read-only Codex invocation, JSONL event validation, error handling and tool-activity rejection (mocked provider).
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

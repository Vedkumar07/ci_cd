# Verified repository context

This is a Next.js app in my-app/, not ubp-accept-billing-charge. The PDF's Java/Maven/ojdbc7 examples are fixtures only. Source requirements for this app are explicitly declared in config-contract.json and checked by /api/health at runtime. The service URL is a demonstration setting; this frontend does not make a billing call.

Dockerfile builds with npm ci and Next standalone output. Helm templates live in deploy/helm/ci-cd/templates. The selected platform is GitHub Actions with the Codex CLI reporter. GitHub workflows at the repo root are active when pushed. .gitlab-ci.yml implements the plan's alternative GitLab layout. scripts/poc/drift.py renders all three environments without cluster access. scripts/poc/ci_api.py reads failed jobs and posts a report; report.py has no deployment capabilities. deploy.py is an explicitly invoked deployment entry point, separate from the reporter.

The drift scanner recognizes direct @Value("${key}") without defaults and ${KEY} placeholders in bootstrap.yml/bootstrap.yaml for a future Java service. It does not resolve all Spring binding, relaxed aliases, profile activation, external Config Server, Secret references or dynamic expressions. Application properties loaded from ConfigMap YAML/properties are flattened. The Next.js contract is explicit because arbitrary process.env usage cannot reliably express which keys are required.

Failure fixtures in fixtures/failures are artificial. Never describe them as production logs. POC-2 remains report-only after a failure. Local or CI deployment requires explicit use of its deployment entry point.


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

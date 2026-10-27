# Verified repository context

This is a Next.js app in my-app/, not ubp-accept-billing-charge. The PDF's Java/Maven/ojdbc7 examples are fixtures only. Source requirements for this app are explicitly declared in config-contract.json and checked by /api/health at runtime. The service URL is a demonstration setting; this frontend does not make a billing call.

Dockerfile builds with npm ci and Next standalone output. Helm templates live in deploy/helm/ci-cd/templates. The selected platform is GitHub Actions with the Codex CLI reporter. GitHub workflows at the repo root are active when pushed. .gitlab-ci.yml implements the plan's alternative GitLab layout. scripts/poc/drift.py renders all three environments without cluster access. scripts/poc/ci_api.py reads failed jobs and posts a report; report.py has no deployment capabilities. deploy.py is an explicitly invoked deployment entry point, separate from the reporter.

The drift scanner recognizes direct @Value("${key}") without defaults and ${KEY} placeholders in bootstrap.yml/bootstrap.yaml for a future Java service. It does not resolve all Spring binding, relaxed aliases, profile activation, external Config Server, Secret references or dynamic expressions. Application properties loaded from ConfigMap YAML/properties are flattened. The Next.js contract is explicit because arbitrary process.env usage cannot reliably express which keys are required.

Failure fixtures in fixtures/failures are artificial. Never describe them as production logs. POC-2 remains report-only after a failure. Local or CI deployment requires explicit use of its deployment entry point.

# Capability 1 and 2: three standard acceptance cases

These cases work without API credits. They test real process failures and rendered
Helm configuration using artifact copies; they never edit the source chart or app,
deploy, push, or post comments. They explicitly use the deterministic reporter.

From the repo root:

```bash
export PATH="$PWD/.tools/bin:$PATH"
python3 scripts/poc/scenarios.py
```

Python needs the dependencies in requirements-poc.txt. A healthy control checks
that the original chart provides both required keys in dev, staging and prod.

| Case | Deliberate change | Capability | Expected result |
| --- | --- | --- | --- |
| `test-failure` | Execute an isolated synthetic unittest assertion: rejected vs accepted | 1 | Test process exits 1. Report names the test stage and includes the assertion and file/line. No claim that this frontend implements billing logic. |
| `missing-key` | Set staging BILLING_API_URL to YAML null in a copied chart | 1 + 2 | Drift exits 1, identifies staging/BILLING_API_URL and its values file; other environments pass. A config report is saved. |
| `invalid-values` | Empty dev BILLING_API_URL and unresolved prod APP_ENV placeholder | 1 + 2 | Drift exits 1 with exactly two findings, one for each environment/key. A config report is saved. |

Each scenario must fail its simulated job to pass the acceptance test. The scenario
runner exits 0 only when it observes the expected failures and reports.

Inspect the evidence:

```bash
cat artifacts/scenarios/summary.json
cat artifacts/scenarios/test-failure/report.md
cat artifacts/scenarios/missing-key/drift.json
cat artifacts/scenarios/missing-key/report.md
cat artifacts/scenarios/invalid-values/drift.json
```

Each directory also contains job.log, evidence.json, report.usage.json and a copied
chart. Usage must say mode=deterministic and tokens=0. To run only one case:

```bash
python3 scripts/poc/scenarios.py --case missing-key
```

## Test a real GitHub PR comment

Local runs do not exercise GitHub log collection or comment permissions. For that,
use an open same-repository POC pull request and run one deliberate case per commit.
First set the GitHub repository variable POC_AI_ENABLED to false while API quota is
unavailable. This skips Codex installation/calls and produces a deterministic bot
comment. It does not verify BMAD/Codex diagnosis quality.

1. **Missing key:** in deploy/helm/ci-cd/values-staging.yaml change only
   BILLING_API_URL to unquoted null. Commit and push to the PR branch.
2. **Empty value:** after restoring case 1, change dev BILLING_API_URL to an empty
   string (`""`) in values-dev.yaml. Commit and push.
3. **Unresolved value:** after restoring case 2, change prod APP_ENV to
   `"${APP_ENV}"` in values-prod.yaml. Commit and push.

For each case expect verify to fail in Tests and configuration drift, docker to be
skipped and failure-report to succeed. The PR Conversation should contain a bot
report naming the affected environment/key. Existing bot comments are updated, so
take a screenshot or save the failure-report artifact after each run. The artifact
contains report.md and report.usage.json; the latter must say deterministic/0 tokens.

Restore every edited value and push a final commit. Expect verify and docker to
pass and failure-report to be skipped. The old comment remains as historical
failure evidence; a successful run currently does not resolve/remove it.

Deleting an override is not a missing-key test: Helm falls back to values.yaml.
Use unquoted null to remove a key, an empty string to test blank configuration, or
a quoted placeholder to test unresolved configuration. Never run deliberate failure
experiments on a production deployment branch or merge the broken values.

## AI unavailable fallback example

Run `POC_AI_ENABLED=false python3 scripts/poc/demo.py`, then open
`artifacts/demo/ai-unavailable/report.md`. This example simulates a quota failure
without making an API call. Expect the original config-drift evidence plus an
"AI explanation unavailable" section naming quota as the reason and suggesting
checking API credits/limits. The usage sidecar says fallback/quota; token usage is
unknown for an actual failed call, not falsely reported as zero.

With POC_AI_ENABLED=false, normal PR reports instead say the reason is that AI is
disabled. No provider call is attempted. This is separate from a provider failure.
The scenario suite's healthy control requires restoring deliberate bad values in
the source chart first; it intentionally stops if the source chart is still broken.

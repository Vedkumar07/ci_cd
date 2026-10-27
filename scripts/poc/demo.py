"""Three offline forced-failure reports, explicitly not live CI results."""
import json
from pathlib import Path
import subprocess

from report import fallback_report

for stage, fixture in [('build', 'build-401'), ('test', 'test'), ('deploy', 'deploy')]:
    output = Path('artifacts/demo') / fixture
    output.mkdir(parents=True, exist_ok=True)
    evidence = output / 'evidence.json'
    evidence.write_text(json.dumps({'provider': 'fixture', 'jobs': [{'name': fixture, 'stage': stage, 'log': Path(f'fixtures/failures/{fixture}.log').read_text()}]}))
    subprocess.run(['python3', 'scripts/poc/report.py', '--evidence', str(evidence), '--output', str(output/'report.md')], check=True)

# Simulated provider failure: demonstrate the unavailable section without an API call.
output = Path('artifacts/demo/ai-unavailable')
output.mkdir(parents=True, exist_ok=True)
evidence = {'provider': 'fixture', 'synthetic': True, 'jobs': [
    {'name': 'config-drift', 'stage': 'config', 'log': Path('fixtures/failures/deploy.log').read_text()}]}
report, usage = fallback_report(evidence, RuntimeError('Quota exceeded. Check your plan and billing details.'))
(output/'report.md').write_text(report + '\n')
(output/'report.usage.json').write_text(json.dumps(usage, indent=2) + '\n')
print(f'Saved {output}/report.md; simulated quota failure, no API call')

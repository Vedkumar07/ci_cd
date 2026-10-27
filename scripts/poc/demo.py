"""Three offline forced-failure reports, explicitly not live CI results."""
import json
from pathlib import Path
import subprocess

for stage, fixture in [('build', 'build-401'), ('test', 'test'), ('deploy', 'deploy')]:
    output = Path('artifacts/demo') / fixture
    output.mkdir(parents=True, exist_ok=True)
    evidence = output / 'evidence.json'
    evidence.write_text(json.dumps({'provider': 'fixture', 'jobs': [{'name': fixture, 'stage': stage, 'log': Path(f'fixtures/failures/{fixture}.log').read_text()}]}))
    subprocess.run(['python3', 'scripts/poc/report.py', '--evidence', str(evidence), '--output', str(output/'report.md')], check=True)

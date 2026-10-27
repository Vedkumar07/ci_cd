"""Repeatable local acceptance cases. No API calls, cluster access or source edits."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
CASES = ("test-failure", "missing-key", "invalid-values")


def run(command, output, expected=0):
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    log = result.stdout + result.stderr
    output.write_text(log)
    if result.returncode != expected:
        raise RuntimeError(f"Expected exit {expected}, got {result.returncode}; inspect {output}")
    return log


def snapshot(folder):
    folder.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "deploy/helm/ci-cd", folder / "chart", dirs_exist_ok=True)
    shutil.copyfile(ROOT / "config-contract.json", folder / "config-contract.json")


def drift(folder, expected=0):
    return run([sys.executable, str(ROOT / "scripts/poc/drift.py"),
                "--root", str(folder), "--chart", str(folder / "chart"),
                "--output", str(folder / "drift.json")], folder / "job.log", expected)


def set_config(folder, environment, key, value):
    file = folder / "chart" / f"values-{environment}.yaml"
    data = yaml.safe_load(file.read_text())
    data.setdefault("config", {})[key] = value
    file.write_text(yaml.safe_dump(data, sort_keys=False))


def report(folder, name, stage, log):
    evidence = {"provider": "local-scenario", "synthetic": True,
                "note": "Deliberate local test; not a hosted CI run or a production failure.",
                "jobs": [{"name": name, "stage": stage, "log": log}]}
    (folder / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n")
    env = dict(os.environ, POC_AI_ENABLED="false")
    subprocess.run([sys.executable, str(ROOT / "scripts/poc/report.py"),
                    "--evidence", str(folder / "evidence.json"),
                    "--output", str(folder / "report.md")], cwd=ROOT, env=env, check=True)
    usage = json.loads((folder / "report.usage.json").read_text())
    if usage.get("mode") != "deterministic" or usage.get("tokens") != 0:
        raise RuntimeError("Acceptance scenarios must not invoke AI")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=["all", *CASES], default="all")
    args = parser.parse_args()
    if not shutil.which("helm"):
        raise SystemExit('Helm missing. Run: export PATH="$PWD/.tools/bin:$PATH"')
    output = ROOT / "artifacts/scenarios"
    control = output / "healthy"
    snapshot(control)
    drift(control)
    results = [{"case": "healthy", "result": "PASS", "expected_job_exit": 0}]
    print("PASS healthy: all required keys present in all environments")
    for name in CASES if args.case == "all" else [args.case]:
        folder = output / name
        snapshot(folder)
        if name == "test-failure":
            # A synthetic assertion, deliberately independent of application behavior.
            test = folder / "check_demo.py"
            test.write_text('import unittest\n\nclass Demo(unittest.TestCase):\n'
                            '    def test_demo_status(self):\n'
                            '        self.assertEqual("rejected", "accepted")\n\n'
                            'if __name__ == "__main__":\n    unittest.main()\n')
            log = run([sys.executable, str(test)], folder / "job.log", expected=1)
            stage = "test"
        else:
            if name == "missing-key":
                set_config(folder, "staging", "BILLING_API_URL", None)
                expected = {("staging", "BILLING_API_URL")}
            else:
                set_config(folder, "dev", "BILLING_API_URL", "")
                set_config(folder, "prod", "APP_ENV", "${APP_ENV}")
                expected = {("dev", "BILLING_API_URL"), ("prod", "APP_ENV")}
            log = drift(folder, expected=1)
            findings = json.loads((folder / "drift.json").read_text())["findings"]
            actual = {(f["environment"], f["key"]) for f in findings}
            if actual != expected:
                raise RuntimeError(f"Incorrect drift findings: {actual}; expected {expected}")
            stage = "config"
        report(folder, name, stage, log)
        results.append({"case": name, "result": "PASS", "expected_job_exit": 1,
                        "report": str(folder / "report.md")})
        print(f"PASS {name}: deliberate failure detected; deterministic report saved")
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"All selected scenarios passed. Evidence: {output}")
    print("These results do not test GitHub API collection or PR comment posting.")


if __name__ == "__main__":
    main()

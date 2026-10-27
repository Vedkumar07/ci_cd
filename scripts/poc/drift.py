"""Compare required properties with rendered ConfigMaps; never contact a cluster."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

import yaml

PLACEHOLDER = re.compile(r"\$\{([^{}]+)\}")


def required_keys(root):
    result = {}
    contract = root / "config-contract.json"
    if contract.exists():
        result.update({key: str(contract) for key in json.loads(contract.read_text())["required"]})
    for path in root.rglob("*"):
        if any(part in {"node_modules", ".git", ".agents", "_bmad", ".next", ".venv", ".tools"} for part in path.parts):
            continue
        if not path.is_file() or not (path.suffix == ".java" or path.name in {"bootstrap.yml", "bootstrap.yaml"}):
            continue
        content = path.read_text()
        if path.suffix == ".java":
            content = "\n".join(re.findall(r'@Value\s*\(\s*"([^"\n]*)"', content))
        for match in PLACEHOLDER.finditer(content):
            if ":" not in match[1]:
                result[match[1]] = str(path)
    return result


def flatten(value, prefix=""):
    result = set()
    if isinstance(value, dict):
        for key, child in value.items():
            result |= flatten(child, f"{prefix}.{key}".strip("."))
    elif value is not None and str(value).strip() and not PLACEHOLDER.search(str(value)):
        result.add(prefix)
    return result


def provided_keys(rendered):
    result = set()
    for doc in yaml.safe_load_all(rendered):
        if not isinstance(doc, dict) or doc.get("kind") != "ConfigMap":
            continue
        for key, value in (doc.get("data") or {}).items():
            if key.endswith((".yml", ".yaml")):
                result |= flatten(yaml.safe_load(value))
            elif key.endswith(".properties"):
                for line in value.splitlines():
                    if line.strip() and not line.lstrip().startswith(("#", "!")) and "=" in line:
                        k, v = line.split("=", 1)
                        if v.strip() and not PLACEHOLDER.search(v):
                            result.add(k.strip())
            elif value is not None and str(value).strip() and not PLACEHOLDER.search(str(value)):
                result.add(key)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--chart", default="deploy/helm/ci-cd")
    p.add_argument("--env", action="append", dest="envs")
    p.add_argument("--output", type=Path, default=Path("artifacts/drift.json"))
    a = p.parse_args()
    required = required_keys(a.root)
    if not required:
        raise SystemExit("No required properties discovered; configure config-contract.json or Java source")
    findings = []
    for env in a.envs or ["dev", "staging", "prod"]:
        values = f"{a.chart}/values-{env}.yaml"
        rendered = subprocess.run(["helm", "template", "poc", a.chart, "-f", values], check=True, capture_output=True, text=True).stdout
        for key in sorted(required.keys() - provided_keys(rendered)):
            findings.append({"environment": env, "key": key, "source": required[key], "file": values, "cause": "Required property missing from rendered ConfigMap"})
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps({"required": required, "findings": findings}, indent=2) + "\n")
    for f in findings:
        print(f"Config drift: {f['key']} missing for {f['environment']}; check {f['file']}")
    print(f"Checked {len(required)} required keys; {len(findings)} missing")
    return bool(findings)


if __name__ == "__main__":
    sys.exit(main())

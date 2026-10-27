"""Explicit pre-push GitLab CI lint; works even when no pipeline can start."""
import json
import os
from pathlib import Path
import sys

from ci_api import API

api = API("gitlab")
result = api.request("/ci/lint", "POST", {"content": Path(".gitlab-ci.yml").read_text(), "include_merged_yaml": True})
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/ci-lint.json").write_text(json.dumps(result, indent=2))
for error in result.get("errors", []):
    print(error)
print("CI lint:", "valid" if result.get("valid") else "invalid")
sys.exit(0 if result.get("valid") else 1)

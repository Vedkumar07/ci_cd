"""Read-only snapshots; invoked while Helm is running, before atomic rollback."""
import argparse
from pathlib import Path
import subprocess

from common import bounded


def collect(namespace, release, output):
    output.mkdir(parents=True, exist_ok=True)
    label = f"app.kubernetes.io/instance={release}"
    commands = {
        "events": ["kubectl", "get", "events", "-n", namespace, "--sort-by=.lastTimestamp"],
        "pods": ["kubectl", "describe", "pods", "-n", namespace, "-l", label],
        "logs": ["kubectl", "logs", "-n", namespace, "-l", label, "--all-containers=true", "--tail=80", "--max-log-requests=10"],
        "previous": ["kubectl", "logs", "-n", namespace, "-l", label, "--all-containers=true", "--previous", "--tail=80", "--max-log-requests=10"],
        "history": ["helm", "history", release, "-n", namespace],
        "status": ["helm", "status", release, "-n", namespace],
    }
    for name, command in commands.items():
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=8)
            text = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            text = "Diagnostic command timed out"
        # Append bounded snapshots so later rollback doesn't overwrite earlier evidence.
        path = output / f"{name}.txt"
        old = path.read_text() if path.exists() else ""
        path.write_text(bounded(old + "\n--- snapshot ---\n" + text))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("namespace")
    p.add_argument("release")
    p.add_argument("--output", type=Path, default=Path("artifacts/diagnostics"))
    a = p.parse_args()
    collect(a.namespace, a.release, a.output)

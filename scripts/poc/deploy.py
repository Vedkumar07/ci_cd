"""Explicit deployment entry point; reporter never invokes this script."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import threading
import yaml

from diagnostics import collect
from common import redact


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--namespace", default="poc2")
    p.add_argument("--release", default="poc2")
    p.add_argument("--env", choices=["dev", "staging", "prod"], default="dev")
    p.add_argument("--image", required=True)
    p.add_argument("--tag", required=True)
    p.add_argument("--timeout", default="180s")
    a = p.parse_args()
    subprocess.run(["python3", "scripts/poc/drift.py", "--env", a.env], check=True)
    applied = subprocess.run(["helm", "template", a.release, "deploy/helm/ci-cd", "-f", f"deploy/helm/ci-cd/values-{a.env}.yaml"], capture_output=True, text=True, check=True).stdout
    safe_config = [doc for doc in yaml.safe_load_all(applied) if doc and doc.get("kind") == "ConfigMap"]
    output = Path("artifacts/diagnostics")
    output.mkdir(parents=True, exist_ok=True)
    (output / "applied-config.txt").write_text(redact(f"Image: {a.image}:{a.tag}\n" + yaml.safe_dump_all(safe_config)))
    stop = threading.Event()

    def watch():
        with ThreadPoolExecutor(max_workers=1) as pool:
            while not stop.is_set():
                # Keep collecting during --atomic; after_script alone is too late.
                pool.submit(collect, a.namespace, a.release, Path("artifacts/diagnostics")).result()
                stop.wait(2)

    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        result = subprocess.run(["helm", "upgrade", "--install", a.release, "deploy/helm/ci-cd", "-n", a.namespace, "--create-namespace", "-f", f"deploy/helm/ci-cd/values-{a.env}.yaml", "--set-string", f"image.repository={a.image}", "--set-string", f"image.tag={a.tag}", "--atomic", "--wait", "--timeout", a.timeout])
    finally:
        stop.set()
        watcher.join(timeout=55)
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()

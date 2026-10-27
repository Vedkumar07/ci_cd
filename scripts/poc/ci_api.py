"""Small provider adapters. API tokens stay in this process, never in agent env."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request
import zipfile

from common import bounded, redact


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).scheme != "https":
            raise ValueError("Refusing non-HTTPS redirect")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urllib.parse.urlsplit(req.full_url).netloc != urllib.parse.urlsplit(newurl).netloc:
            redirected.remove_header("Authorization")
            redirected.remove_header("Private-token")
        return redirected


class API:
    def __init__(self, provider):
        self.provider = provider
        if provider == "gitlab":
            self.base = os.environ["CI_API_V4_URL"].rstrip("/")
            self.project = urllib.parse.quote(os.environ["CI_PROJECT_ID"], safe="")
            self.prefix = f"/projects/{self.project}"
            self.token = os.environ["GITLAB_REPORT_TOKEN"]
        else:
            self.base = os.environ.get("GITHUB_API_URL", "https://api.github.com")
            self.prefix = "/repos/" + os.environ["GITHUB_REPOSITORY"]
            self.token = os.environ["GH_TOKEN"]
        if urllib.parse.urlsplit(self.base).scheme != "https":
            raise ValueError("CI API must use HTTPS")

    def request(self, path, method="GET", data=None, raw=False):
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        headers["PRIVATE-TOKEN" if self.provider == "gitlab" else "Authorization"] = self.token if self.provider == "gitlab" else "Bearer " + self.token
        request = urllib.request.Request(self.base + self.prefix + path, data=json.dumps(data).encode() if data is not None else None, headers=headers, method=method)
        with urllib.request.build_opener(SafeRedirect()).open(request, timeout=30) as response:
            content = response.read(2_000_001)
        if len(content) > 2_000_000:
            raise ValueError("API evidence exceeds 2 MB transfer limit")
        return content if raw else json.loads(content)

    def pages(self, path, key=None):
        result = []
        for page in range(1, 21):
            data = self.request(path + ("&" if "?" in path else "?") + f"per_page=100&page={page}")
            items = data[key] if key else data
            result += items
            if len(items) < 100:
                return result
        raise ValueError("API pagination limit exceeded")

    def collect(self):
        jobs = []
        if self.provider == "gitlab":
            run = os.environ["CI_PIPELINE_ID"]
            failed = self.pages(f"/pipelines/{run}/jobs?scope[]=failed")
        else:
            run = os.environ["GITHUB_RUN_ID"]
            failed = [j for j in self.pages(f"/actions/runs/{run}/jobs?filter=latest", "jobs") if j["conclusion"] in {"failure", "timed_out"}]
        for job in failed[:10]:
            try:
                if self.provider == "gitlab":
                    log = self.request(f"/jobs/{job['id']}/trace", raw=True).decode(errors="replace")
                else:
                    blob = self.request(f"/actions/jobs/{job['id']}/logs", raw=True)
                    # GitHub job logs are normally plain text; also accept small ZIP responses.
                    if blob.startswith(b"PK"):
                        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                            names = archive.infolist()[:20]
                            if sum(f.file_size for f in names) > 2_000_000:
                                raise ValueError("Expanded logs too large")
                            log = "\n".join(archive.read(f).decode(errors="replace") for f in names)
                    else:
                        log = blob.decode(errors="replace")
            except Exception as error:
                log = f"Log unavailable ({type(error).__name__}); inspect CI job manually."
            item = {"id": job["id"], "name": bounded(job["name"], 200), "stage": bounded(job.get("stage", job["name"]), 200), "log": bounded(log, 8000)}
            if self.provider == "gitlab" and job.get("artifacts_file", {}).get("filename"):
                try:
                    blob = self.request(f"/jobs/{job['id']}/artifacts", raw=True)
                    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                        allowed = [f for f in archive.infolist() if f.filename.startswith("artifacts/") and f.filename.endswith((".txt", "drift.json"))][:10]
                        if sum(f.file_size for f in allowed) > 2_000_000:
                            raise ValueError("Expanded artifacts too large")
                        item["diagnostics"] = [{"file": f.filename, "content": bounded(archive.read(f).decode(errors="replace"), 4000)} for f in allowed]
                except Exception as error:
                    item["diagnostics_error"] = type(error).__name__
            jobs.append(item)
        return {"provider": self.provider, "run": run, "jobs": jobs}

    def post(self, body):
        if self.provider == "gitlab":
            number = os.environ.get("CI_MERGE_REQUEST_IID")
            if not number:
                print("No merge request; report saved as artifact")
                return
            path = f"/merge_requests/{int(number)}/notes"
            field = "body"
            update_method = "PUT"
        else:
            number = os.environ.get("POC_PR_NUMBER")
            if not number:
                print("No pull request; report saved as artifact")
                return
            path = f"/issues/{int(number)}/comments"
            field = "body"
            update_method = "PATCH"
        marker = "<!-- poc2-failure-report -->"
        body = marker + "\n" + body.replace(marker, "")
        user_id = self.user_id() if self.provider == "gitlab" else None
        for note in self.pages(path):
            # Only update our own bot's note, never a user's copied marker.
            author = note.get("author", note.get("user", {}))
            own_note = author.get("id") == user_id if self.provider == "gitlab" else author.get("login") == "github-actions[bot]"
            if marker in note.get(field, "") and own_note:
                target = path + f"/{note['id']}" if self.provider == "gitlab" else f"/issues/comments/{note['id']}"
                self.request(target, update_method, {field: body})
                return
        self.request(path, "POST", {field: body})

    def user_id(self):
        # User endpoint is outside the project prefix.
        original = self.prefix
        try:
            self.prefix = ""
            return self.request("/user")["id"]
        finally:
            self.prefix = original


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["collect", "post"])
    p.add_argument("--provider", choices=["github", "gitlab"], required=True)
    p.add_argument("--file", type=Path)
    a = p.parse_args()
    api = API(a.provider)
    if a.action == "post":
        api.post(redact(a.file.read_text())[:60000])
        return
    evidence = api.collect()
    base = os.environ.get("POC_BASE_SHA", "")
    if base and all(c in "0123456789abcdef" for c in base) and len(base) == 40:
        diff = subprocess.run(["git", "diff", "--no-ext-diff", base, "HEAD", "--", ".", ":(exclude)*lock*"], text=True, capture_output=True, check=True).stdout
        evidence["diff"] = bounded(diff, 12000)
    evidence["diagnostics"] = []
    for path in sorted(Path("artifacts").rglob("*.txt"))[:10]:
        if path.is_file() and not path.is_symlink():
            evidence["diagnostics"].append({"file": str(path), "content": bounded(path.read_text(), 4000)})
    output = a.file or Path("artifacts/evidence.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"Collected {len(evidence['jobs'])} failed jobs")


if __name__ == "__main__":
    main()

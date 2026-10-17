"""Read pinned GitHub snapshots without checking out or executing repository code."""

from __future__ import annotations

import io
import base64
import re
import tarfile
from urllib.parse import urlsplit

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .common import Json, Redactor
from .source_scan import eligible_source, scan_source


class ArchiveLimitError(ValueError):
    """An archive is too large; fall back to a bounded Git tree/blob scan."""


def validate_repo(value: str) -> str:
    value = value.removeprefix("https://github.com/").removesuffix("/").removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", value):
        raise ValueError("Repository must be owner/name or an https://github.com/owner/name URL")
    return value


def token_for(repo: str, environment: dict[str, str]) -> str:
    preferred = "ORG_PAT" if repo.split("/")[0].lower() == "instaread-co" else "PERSONAL_PAT"
    return environment.get(preferred) or environment.get("GITHUB_TOKEN") or environment.get("GIT_TOKEN", "")


def http_session() -> requests.Session:
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.5,
                  status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"], respect_retry_after_header=False)))
    return session


def github_json(session: requests.Session, path: str, headers: dict[str, str]) -> Json:
    with session.get(f"https://api.github.com{path}", headers=headers, timeout=(10, 45)) as response:
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected a GitHub object")
    return payload


def download_archive(session: requests.Session, repo: str, commit: str, headers: dict[str, str], limit: int) -> bytes:
    url = f"https://api.github.com/repos/{repo}/tarball/{commit}"
    for _ in range(4):
        # GitHub redirects private archives to signed codeload URLs. PAT stays on api.github.com.
        request_headers = headers if urlsplit(url).hostname == "api.github.com" else {"User-Agent": "traffic-cause-audit"}
        with session.get(url, headers=request_headers, stream=True, allow_redirects=False, timeout=(10, 60)) as response:
            if response.status_code in {301, 302, 303, 307, 308}:
                target = response.headers.get("Location", "")
                parsed = urlsplit(target)
                if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "codeload.github.com", "github.com"}:
                    raise ValueError("Unexpected archive redirect")
                url = target
                continue
            response.raise_for_status()
            content = bytearray()
            for chunk in response.iter_content(64 * 1024):
                content.extend(chunk)
                if len(content) > limit:
                    raise ArchiveLimitError("Repository archive exceeds configured compressed byte limit")
            return bytes(content)
    raise ValueError("Too many archive redirects")


def scan_archive(archive: bytes, repo: str, commit: str, indicators: list[Json], redactor: Redactor,
                 max_files: int, max_file_bytes: int = 512 * 1024) -> Json:
    findings = []
    scanned, skipped, expanded = 0, 0, 0
    limitations = []
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r|gz") as stream:
        for member in stream:
            expanded += max(member.size, 0)
            if expanded > 512 * 1024 * 1024:
                limitations.append("Expanded archive limit (512 MiB) reached")
                break
            parts = member.name.split("/", 1)
            path = parts[1] if len(parts) == 2 else ""
            if not member.isfile() or not eligible_source(path) or member.size > max_file_bytes:
                skipped += 1
                continue
            if scanned >= max_files:
                limitations.append(f"Source file limit ({max_files}) reached")
                break
            extracted = stream.extractfile(member)
            if extracted is None:
                continue
            with extracted:
                raw = extracted.read(max_file_bytes + 1)
            if b"\x00" in raw:
                skipped += 1
                continue
            scanned += 1
            findings.extend(scan_source(repo, commit, path, raw.decode("utf-8", errors="replace"), indicators, redactor))
            if len(findings) > 3000:
                # Keep a bounded collection while still scanning remaining files for stronger evidence.
                findings.sort(key=lambda finding: finding["score"], reverse=True)
                findings = findings[:1500]
                if "Intermediate candidate retention limit applied" not in limitations:
                    limitations.append("Intermediate candidate retention limit applied")
    findings.sort(key=lambda finding: finding["score"], reverse=True)
    retained = []
    per_file: dict[str, int] = {}
    for finding in findings:
        if per_file.get(finding["path"], 0) >= 8:
            continue
        retained.append(finding)
        per_file[finding["path"]] = per_file.get(finding["path"], 0) + 1
        if len(retained) >= 150:
            break
    return {"findings": retained, "files_scanned": scanned, "entries_skipped": skipped,
            "candidate_count": len(findings), "limitations": limitations}


def scan_repository(repo: str, environment: dict[str, str], indicators: list[Json], redactor: Redactor,
                    max_files: int, max_archive_bytes: int) -> Json:
    repo = validate_repo(repo)
    token = token_for(repo, environment)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "traffic-cause-audit",
               "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with http_session() as session:
        metadata = github_json(session, f"/repos/{repo}", headers)
        branch = metadata["default_branch"]
        from urllib.parse import quote
        commit = github_json(session, f"/repos/{repo}/commits/{quote(branch, safe='')}", headers)["sha"]
        if not re.fullmatch(r"[a-fA-F0-9]{40}", commit):
            raise ValueError("Invalid GitHub commit SHA")
        try:
            if metadata.get("size", 0) > 1024 * 1024:
                raise ArchiveLimitError("Large repository; use bounded blob scan")
            archive = download_archive(session, repo, commit, headers, max_archive_bytes)
            result = scan_archive(archive, repo, commit, indicators, redactor, max_files)
        except ArchiveLimitError:
            result = scan_tree(session, repo, commit, headers, indicators, redactor, min(max_files, 180))
        except tarfile.TarError as error:
            raise ValueError("Invalid or truncated GitHub archive") from error
    return {"repo": repo, "status": "scanned", "branch": branch, "commit": commit,
            "archived": metadata.get("archived", False), "fork": metadata.get("fork", False), **result}


def scan_tree(session: requests.Session, repo: str, commit: str, headers: dict[str, str],
              indicators: list[Json], redactor: Redactor, max_blobs: int) -> Json:
    tree = github_json(session, f"/repos/{repo}/git/trees/{commit}?recursive=1", headers)
    candidates = [entry for entry in tree.get("tree", []) if entry["type"] == "blob"
                  and entry.get("mode") != "120000" and eligible_source(entry["path"])
                  and entry.get("size", 0) <= 512 * 1024]
    route_names = {item["text"].rsplit("/", 1)[-1] for item in indicators if item["kind"] == "observed_path"}
    def priority(entry: Json) -> tuple[int, int, str]:
        path = entry["path"].lower()
        score = 10 if path.rsplit("/", 1)[-1] in route_names else 0
        score += 5 if re.search(r"(?:routes?|controllers?|server|nginx|cache|player|app|main|config|middleware)", path) else 0
        score += 3 if path.endswith((".tf", ".conf")) else 0
        score -= 10 if re.search(r"(?:^|/)(?:test|example|lib|db)/", path) else 0
        return (-score, path.count("/"), path)
    candidates.sort(key=priority)
    findings = []
    for index, entry in enumerate(candidates[:max_blobs], 1):
        if index == 1 or index % 30 == 0:
            print(f"  {repo}: reading selected source {index}/{min(len(candidates), max_blobs)}", flush=True)
        blob = github_json(session, f"/repos/{repo}/git/blobs/{entry['sha']}", headers)
        if blob.get("encoding") != "base64":
            continue
        source = base64.b64decode(blob["content"]).decode("utf-8", errors="replace")
        findings.extend(scan_source(repo, commit, entry["path"], source, indicators, redactor))
    findings.sort(key=lambda row: row["score"], reverse=True)
    limits = [f"Large archive: prioritized Git tree/blob fallback; {min(len(candidates), max_blobs)} of "
              f"{len(candidates)} eligible tree entries inspected; at most {max_blobs} blob requests"]
    if tree.get("truncated"):
        limits.append("GitHub recursive tree was truncated; unreturned paths are not inspected")
    return {"findings": findings[:150], "files_scanned": min(len(candidates), max_blobs),
            "entries_skipped": len(tree.get("tree", [])) - min(len(candidates), max_blobs),
            "candidate_count": len(findings), "limitations": limits}

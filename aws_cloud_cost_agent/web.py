from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import secrets
import threading
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from string import Template
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlsplit

from .cli import PROJECT_ROOT, load_local_env
from .markdown_renderer import render_markdown
from .steps import AVAILABLE_STEPS
from .tools.shared import AwsToolConfig
from .workflow import run_workflow


ASSET_DIR = Path(__file__).resolve().parent / "web_assets"
DEFAULT_PORT = 8765
MAX_FORM_BYTES = 64 * 1024
ACCOUNT_PATTERN = re.compile(r"^\d{12}$")
MODEL_STEPS = {"service-analysis", "recommendations"}
ARTIFACT_GROUPS = (
    "Connection Check",
    "Overall Bill",
    "Per Service Analysis",
)


def _group_artifacts(artifacts: list[Path]) -> dict[str, list[Path]]:
    """Group generated reports by workflow stage while preserving their order."""
    grouped = {name: [] for name in ARTIFACT_GROUPS}
    for path in artifacts:
        if path.name.startswith("connection_check_"):
            group = "Connection Check"
        elif path.name.startswith("overall_bill_data_"):
            group = "Overall Bill"
        else:
            group = "Per Service Analysis"
        grouped[group].append(path)
    return grouped


@dataclass
class RunState:
    run_id: str
    status: str
    steps: list[str]
    artifacts: list[str]
    error: str | None = None


class RunManager:
    """Run one workflow at a time and expose a small thread-safe status snapshot."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RunState] = {}
        self._active_run_id: str | None = None

    def start(
        self,
        account_id: str | None,
        start_date: str,
        end_date: str,
        steps: list[str],
    ) -> RunState:
        with self._lock:
            if self._active_run_id:
                active = self._runs[self._active_run_id]
                if active.status == "running":
                    raise RuntimeError("A workflow is already running.")

            state = RunState(
                run_id=secrets.token_hex(8),
                status="running",
                steps=steps,
                artifacts=[],
            )
            self._runs[state.run_id] = state
            self._active_run_id = state.run_id

        thread = threading.Thread(
            target=self._execute,
            args=(state.run_id, account_id, start_date, end_date, steps),
            daemon=True,
        )
        thread.start()
        return state

    def get(self, run_id: str) -> RunState | None:
        with self._lock:
            state = self._runs.get(run_id)
            return RunState(**asdict(state)) if state else None

    def _execute(
        self,
        run_id: str,
        account_id: str | None,
        start_date: str,
        end_date: str,
        steps: list[str],
    ) -> None:
        try:
            artifacts = asyncio.run(
                run_workflow(
                    config=AwsToolConfig.from_environment(PROJECT_ROOT),
                    expected_account=account_id,
                    start_date=start_date,
                    end_date=end_date,
                    steps=steps,
                )
            )
            with self._lock:
                state = self._runs[run_id]
                state.status = "complete"
                state.artifacts = [path.name for path in artifacts]
        except Exception as error:
            with self._lock:
                state = self._runs[run_id]
                state.status = "failed"
                state.error = str(error)
        finally:
            with self._lock:
                if self._active_run_id == run_id:
                    self._active_run_id = None


class CostAgentHandler(BaseHTTPRequestHandler):
    manager = RunManager()
    csrf_token = secrets.token_urlsafe(32)

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path == "/":
            self._serve_index(parse_qs(parsed.query))
            return
        if parsed.path == "/api/status":
            self._serve_status(parse_qs(parsed.query))
            return
        if parsed.path.startswith("/artifacts/"):
            self._serve_artifact(unquote(parsed.path.removeprefix("/artifacts/")))
            return
        if parsed.path.startswith("/assets/"):
            self._serve_asset(parsed.path.removeprefix("/assets/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/runs":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            form = self._read_form()
            self._validate_csrf(form)
            account_id, start_date, end_date, steps = self._validate_run(form)
            state = self.manager.start(account_id, start_date, end_date, steps)
        except (UnicodeDecodeError, ValueError, RuntimeError) as error:
            self._serve_index({}, error=str(error), status=HTTPStatus.BAD_REQUEST)
            return

        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?run={quote(state.run_id)}")
        self.end_headers()

    def _read_form(self) -> dict[str, list[str]]:
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("Invalid request size.") from error
        if content_length <= 0 or content_length > MAX_FORM_BYTES:
            raise ValueError("Invalid request size.")
        body = self.rfile.read(content_length).decode("utf-8")
        return parse_qs(body, keep_blank_values=True)

    def _validate_csrf(self, form: dict[str, list[str]]) -> None:
        submitted = form.get("csrf_token", [""])[0]
        if not secrets.compare_digest(submitted, self.csrf_token):
            raise ValueError("Invalid form token. Reload the page and try again.")

    def _validate_run(
        self,
        form: dict[str, list[str]],
    ) -> tuple[str | None, str, str, list[str]]:
        account_id = form.get("aws_account", [""])[0].strip() or None
        start_value = form.get("start_date", [""])[0]
        end_value = form.get("end_date", [""])[0]
        steps = list(dict.fromkeys(form.get("steps", [])))

        if account_id and not ACCOUNT_PATTERN.fullmatch(account_id):
            raise ValueError("AWS account ID must contain exactly 12 digits.")
        try:
            start_date = date.fromisoformat(start_value)
            end_date = date.fromisoformat(end_value)
        except ValueError as error:
            raise ValueError("Start and end dates must use YYYY-MM-DD.") from error
        if start_date >= end_date:
            raise ValueError("Start date must be before end date.")
        if not steps:
            raise ValueError("Select at least one step.")
        invalid_steps = [step for step in steps if step not in AVAILABLE_STEPS]
        if invalid_steps:
            raise ValueError(f"Unsupported steps: {', '.join(invalid_steps)}")
        if MODEL_STEPS.intersection(steps) and not os.getenv("RESPAN_API_KEY"):
            raise ValueError("RESPAN_API_KEY is required for analysis and recommendations.")
        return account_id, start_value, end_value, steps

    def _serve_index(
        self,
        query: dict[str, list[str]],
        error: str | None = None,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        artifacts = self._list_artifacts()
        requested_name = query.get("artifact", [""])[0]
        selected = self._artifact_path(requested_name) if requested_name else None
        if not selected and artifacts:
            selected = artifacts[0]

        artifact_groups = []
        for group_name, paths in _group_artifacts(artifacts).items():
            items = []
            for path in paths:
                selected_class = " is-selected" if selected == path else ""
                items.append(
                    f'<li><a class="artifact-link{selected_class}" '
                    f'href="/?artifact={quote(path.name)}">{html.escape(path.name)}</a></li>'
                )
            contents = (
                f'<ul>{"".join(items)}</ul>'
                if items
                else '<p class="artifact-group-empty">No reports</p>'
            )
            artifact_groups.append(
                '<section class="artifact-group">'
                '<div class="artifact-group-heading">'
                f'<h3>{html.escape(group_name)}</h3>'
                f'<span>{len(paths)}</span>'
                '</div>'
                f'{contents}'
                '</section>'
            )

        if selected:
            markdown = render_markdown(selected.read_text(encoding="utf-8"))
            viewer = (
                '<div class="viewer-heading">'
                f'<h2>{html.escape(selected.name)}</h2>'
                f'<a href="/artifacts/{quote(selected.name)}" target="_blank" '
                'rel="noopener">Open raw</a></div>'
                f'<article class="markdown-output">{markdown}</article>'
            )
        else:
            viewer = '<div class="empty-state">No Markdown artifacts yet.</div>'

        run_id = query.get("run", [""])[0]
        run_state = self.manager.get(run_id) if run_id else None
        status_text = "Ready"
        status_class = "status-ready"
        if run_state:
            status_text = (
                f"Running: {', '.join(run_state.steps)}"
                if run_state.status == "running"
                else run_state.status.capitalize()
            )
            status_class = f"status-{run_state.status}"
            error = error or run_state.error

        today = date.today()
        template = Template((ASSET_DIR / "index.html").read_text(encoding="utf-8"))
        page = template.safe_substitute(
            account_id=html.escape(os.getenv("AWS_ACCOUNT_ID", "")),
            start_date=(today - timedelta(days=30)).isoformat(),
            end_date=today.isoformat(),
            csrf_token=html.escape(self.csrf_token),
            artifact_groups="".join(artifact_groups),
            artifact_viewer=viewer,
            run_id=html.escape(run_id),
            status_text=html.escape(status_text),
            status_class=status_class,
            error_message=(
                f'<div class="error-banner" role="alert">{html.escape(error)}</div>'
                if error
                else ""
            ),
        )
        self._send(status, page.encode("utf-8"), "text/html; charset=utf-8")

    def _serve_status(self, query: dict[str, list[str]]) -> None:
        run_id = query.get("id", [""])[0]
        state = self.manager.get(run_id)
        if not state:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Run not found."})
            return
        self._send_json(HTTPStatus.OK, asdict(state))

    def _serve_artifact(self, name: str) -> None:
        path = self._artifact_path(name)
        if not path:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send(
            HTTPStatus.OK,
            path.read_bytes(),
            "text/markdown; charset=utf-8",
            disposition=f'inline; filename="{path.name}"',
        )

    def _serve_asset(self, name: str) -> None:
        if Path(name).name != name:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        path = ASSET_DIR / name
        content_types = {"styles.css": "text/css", "app.js": "text/javascript"}
        if not path.is_file() or name not in content_types:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send(HTTPStatus.OK, path.read_bytes(), f"{content_types[name]}; charset=utf-8")

    def _list_artifacts(self) -> list[Path]:
        output_dir = PROJECT_ROOT / "output_artifact"
        if not output_dir.exists():
            return []
        return sorted(output_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)

    def _artifact_path(self, name: str) -> Path | None:
        if not name or Path(name).name != name or not name.endswith(".md"):
            return None
        path = PROJECT_ROOT / "output_artifact" / name
        return path if path.is_file() else None

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        self._send(status, json.dumps(payload).encode("utf-8"), "application/json")

    def _send(
        self,
        status: HTTPStatus,
        body: bytes,
        content_type: str,
        disposition: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'",
        )
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local AWS cost agent web interface.")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AWS_COST_AGENT_PORT", DEFAULT_PORT)),
        help=f"Local port. Defaults to {DEFAULT_PORT}.",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535.")
    return args


def main() -> None:
    load_local_env(PROJECT_ROOT / ".env")
    args = parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), CostAgentHandler)
    print(f"AWS Cost Agent: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

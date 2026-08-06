"""Debug agent for BikeMaster.

Spawns and monitors child processes (backend / frontend), intercepts stdout/stderr,
detects errors and structured warnings, and writes them to a report file.

Usage:
    python scripts/debug_agent.py                        # monitor defaults
    python scripts/debug_agent.py --backend-only
    python scripts/debug_agent.py --frontend-only
    python scripts/debug_agent.py --log-file logs/errors.log
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import UTC
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOG = REPO_ROOT / "logs" / "debug_agent.log"
FRONTEND_DIR = REPO_ROOT / "frontend"
BACKEND_DIR = REPO_ROOT / "bike_analyzer"

PYTHON_EXE = sys.executable or "python"
NPM_EXE = shutil.which("npm") or "npm"
VITE_PM2 = "npm run dev"
UVICORN_CMD = f"{PYTHON_EXE} -m uvicorn bike_analyzer.backend.api.app_factory:app --host 0.0.0.0 --port 8000 --reload"

PY_ERROR_RE = re.compile(
    r"^Traceback \(most recent call last\):", re.MULTILINE
)
JS_ERROR_RE = re.compile(
    r"(?i)error(?:s)?(:?\s+|[:])|uncaught|unhandled|referenceerror|typeerror|syntaxerror|rangeerror|evalerror|internalerror|aggregateerror"
)
VUE_WARN_RE = re.compile(r"(?i)warn(?:ing)?(:?\s+|[:])|hydration mismatch|infinite recursion")
HTTP_ERROR_RE = re.compile(r"(?i)\b(?:500|502|503|504)\b|internal server error|errore|errore del server")
OS_ERROR_RE = re.compile(r"(?i)\b(?:EPERM|EACCES|ENOENT|ECONNREFUSED|OSError|Permission denied)\b")
UNKNOWN_RE = re.compile(r"(?i)\bfatal\b|\bsegmentation fault\b|\bcore dumped\b|\babort\b|killed")


class ErrorRecord:
    __slots__ = ("timestamp", "source", "category", "message", "context", "first_line", "line_number")

    def __init__(
        self,
        *,
        timestamp: str,
        source: str,
        category: str,
        message: str,
        context: str = "",
        first_line: str = "",
        line_number: int = 0,
    ) -> None:
        self.timestamp = timestamp
        self.source = source
        self.category = category
        self.message = message
        self.context = context
        self.first_line = first_line
        self.line_number = line_number

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "category": self.category,
            "message": self.message,
            "context": self.context,
            "first_line": self.first_line,
            "line_number": self.line_number,
        }


class DebugAgent:
    def __init__(self, log_file: Path) -> None:
        self.log_file = log_file
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._children: list[subprocess.Popen] = []
        self._last_backend_error_at: float = 0.0
        self._last_frontend_error_at: float = 0.0
        self._backend_recent: list[str] = []
        self._frontend_recent: list[str] = []
        self._backend_errors: int = 0
        self._frontend_errors: int = 0
        self._backend_pending_py_traceback: list[str] = []
        self._frontend_pending_py_traceback: list[str] = []
        self._log_lines_written: int = 0

        log_file.parent.mkdir(parents=True, exist_ok=True)
        if not log_file.exists():
            log_file.write_text("", encoding="utf-8")
        self._write(f"[START] Debug agent started at {dt.datetime.now(UTC).isoformat()}\n")

    def _append(self, record: ErrorRecord) -> None:
        with self._lock:
            self._write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
            self._log_lines_written += 1

    def _write(self, text: str) -> None:
        try:
            with self.log_file.open("a", encoding="utf-8") as fh:
                fh.write(text)
        except Exception:
            if not self._stop.is_set():
                print(f"[debug-agent] Failed to write log: {text!r}", flush=True)

    def classify(self, source: str, line: str) -> tuple[str | None, str]:
        if PY_ERROR_RE.search(line) or UNKNOWN_RE.search(line) or OS_ERROR_RE.search(line):
            return "fatal", line

        combined = f"{line}\n"
        if _context_search(source, combined, self._backend_pending_py_traceback) or \
           _context_search(source, combined, self._frontend_pending_py_traceback):
            return "python_traceback", line

        if PY_ERROR_RE.search(line):
            return "python_traceback", line

        if HTTP_ERROR_RE.search(line):
            return "http_error", line
        if JS_ERROR_RE.search(line):
            return "javascript_error", line
        if VUE_WARN_RE.search(line):
            return "vue_warning", line
        if PY_ERROR_RE.search(line):
            return "python_traceback", line
        return None, line


def _context_search(source: str, segment: str, pending_sources: list[str]) -> bool:
    patched = segment.lower().replace("\n", " ")
    return any(src and src.lower().replace("\n", " ") in patched for src in pending_sources)


def _is_text(line: str) -> bool:
    try:
        if not line:
            return False
        line.encode("utf-8")
        return True
    except Exception:
        return False


def _clean_line(line: str) -> str:
    if not _is_text(line):
        try:
            return line.decode("utf-8", errors="replace").rstrip("\n")
        except Exception:
            return "<binary>"
    return line.rstrip("\n")


def _backoff_until(last: float, min_delta: float) -> bool:
    now = time.monotonic()
    return (now - last) < min_delta


def _monitor(
    agent: DebugAgent,
    name: str,
    proc: subprocess.Popen,
    min_delta: float,
    recent: list[str],
    pending_traceback: list[str],
    last_error_ts: list[float],
) -> None:
    source_prefix = f"[{name}]"
    try:
        for raw in proc.stdout:
            line = _clean_line(raw)
            if not line:
                continue

            recent.append(line)
            if len(recent) > 200:
                recent.pop(0)

            category, hit = agent.classify(name, line)
            if category and not _backoff_until(last_error_ts[0], min_delta):
                now = dt.datetime.now(UTC).isoformat()
                record = ErrorRecord(
                    timestamp=now,
                    source=source_prefix,
                    category=category,
                    message=hit,
                    context="\n".join(recent[-25:]),
                    first_line=recent[0] if recent else hit,
                    line_number=0,
                )
                agent._append(record)
                print(f"[debug-agent] {category.upper()} in {name}: {hit[:160]}", flush=True)
                last_error_ts[0] = time.monotonic()
                recent.clear()
    except Exception as exc:
        msg = f"monitor-loop ended: {exc}"
        agent._append(
            ErrorRecord(
                timestamp=dt.datetime.now(UTC).isoformat(),
                source=source_prefix,
                category="observer_error",
                message=msg,
                context="\n".join(recent[-25:]),
            )
        )
        print(f"[debug-agent] {msg}", flush=True)


def run_process(name: str, cmd: list[str], cwd: Path) -> subprocess.Popen | None:
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,
            universal_newlines=False,
        )
        print(f"[debug-agent] started {name}: {' '.join(cmd)}", flush=True)
        return proc
    except FileNotFoundError as exc:
        print(f"[debug-agent] cannot start {name}: {exc}", flush=True)
        return None
    except Exception as exc:
        print(f"[debug-agent] cannot start {name}: {exc}", flush=True)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="BikeMaster debug agent")
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG, help="Error report file path")
    parser.add_argument("--backend-only", action="store_true", help="Monitor only backend")
    parser.add_argument("--frontend-only", action="store_true", help="Monitor only frontend")
    args = parser.parse_args()

    agent = DebugAgent(args.log_file)
    print(f"[debug-agent] log file: {args.log_file}", flush=True)

    backend_cmd = UVICORN_CMD.split() if isinstance(UVICORN_CMD, str) else list(UVICORN_CMD)
    backend_proc = None if args.frontend_only else run_process("backend", backend_cmd, BACKEND_DIR)
    frontend_cmd = [NPM_EXE, "run", "dev"] if isinstance(NPM_EXE, str) and NPM_EXE else ["npm", "run", "dev"]
    frontend_proc = None if args.backend_only else run_process("frontend", frontend_cmd, FRONTEND_DIR)

    threads: list[threading.Thread] = []
    if backend_proc:
        t = threading.Thread(
            target=_monitor,
            args=(
                agent,
                "backend",
                backend_proc,
                10.0,
                agent._backend_recent,
                agent._backend_pending_py_traceback,
                [agent._last_backend_error_at],
            ),
            daemon=True,
        )
        t.start()
        threads.append(t)
        agent._children.append(backend_proc)

    if frontend_proc:
        t = threading.Thread(
            target=_monitor,
            args=(
                agent,
                "frontend",
                frontend_proc,
                8.0,
                agent._frontend_recent,
                agent._frontend_pending_py_traceback,
                [agent._last_frontend_error_at],
            ),
            daemon=True,
        )
        t.start()
        threads.append(t)
        agent._children.append(frontend_proc)

    if not threads:
        print("[debug-agent] nothing to monitor", flush=True)
        return 1

    def _sig_handler(signum: int, _frame: object) -> None:
        print(f"\n[debug-agent] stopping (signal {signum})...", flush=True)
        agent._stop.set()
        for proc in agent._children:
            if proc and proc.poll() is None:
                with contextlib.suppress(Exception):
                    proc.terminate()

        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)

        try:
            while any(proc.poll() is None for proc in agent._children if proc is not None):
                time.sleep(1)
        except KeyboardInterrupt:
            _sig_handler(signal.SIGINT, None)

        for proc in agent._children:
            if proc and proc.poll() is None:
                with contextlib.suppress(Exception):
                    proc.terminate()

        for proc in agent._children:
            if proc:
                try:
                    proc.wait(timeout=5)
                    rc = proc.returncode
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(Exception):
                        proc.kill()
                rc = None
            print(f"[debug-agent] {proc} exited with {rc}", flush=True)

    print(f"[debug-agent] stopped. Report written to: {args.log_file}", flush=True)
    return 0

if __name__ == "__main__":
    sys.exit(main())

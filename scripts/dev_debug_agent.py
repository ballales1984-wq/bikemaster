"""
Development Debug Agent — MCP stdio server.

Requires:
    pip install "mcp[cli]==1.29.0" playwright

Note:
    mcp>=2.0 removes FastMCP; this server is pinned to 1.29.0
    which still provides mcp.server.fastmcp.FastMCP.
"""
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False


# ============================================================
# LOGGING (stderr only — stdout is reserved for MCP stdio)
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stderr,
)

logger = logging.getLogger("dev_debug_agent")


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_DIR = Path(
    os.getenv("DEV_AGENT_PROJECT", os.getcwd())
).resolve()

SCREENSHOT_DIR = PROJECT_DIR / ".dev_debug_agent" / "screenshots"

mcp = FastMCP(
    "Development Debug Agent"
)


# ============================================================
# SECURITY
# ============================================================

_SENSITIVE_NAMES = [
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "private_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "authorization",
    "set-cookie",
    "pgpassword",
    "stripe_secret",
    "mysql_pwd",
]


def redact(text: str) -> str:
    """
    Remove obvious secrets from command output.
    Only redacts VALUES associated with sensitive KEYS, not
    sensitive words appearing inside values.
    Handles:
    - KEY=VALUE and KEY: VALUE
    - JSON fields like "key": "value"
    - Headers like Authorization: Bearer ...
    - Env exports like export CLIENT_SECRET=...
    - Compound real-world names (PGPASSWORD, STRIPE_SECRET_KEY, MYSQL_PWD)
    """

    if not text:
        return ""

    lines = []

    for line in text.splitlines():

        lower = line.lower()

        for name in _SENSITIVE_NAMES:

            pattern = name.replace("_", "[_\\-]?")

            kv_re = re.compile(
                r'(?i)((?:^|[\s,;{])[\w_\-]*?' + pattern + r'[\w_\-]*?)\s*[=:]\s*(.+)'
            )

            m = kv_re.search(lower)
            if m:
                line = kv_re.sub(
                    lambda mm: mm.group(1).rstrip() + "=****",
                    line,
                    count=1,
                )
                break

            json_re = re.compile(
                r'(?i)"([^"]*?' + pattern + r'[^"]*?)"\s*:\s*"([^"]*)"'
            )

            m = json_re.search(lower)
            if m:
                line = json_re.sub(
                    lambda mm: '"' + mm.group(1) + '": "****"',
                    line,
                    count=1,
                )
                break

        lines.append(line)

    return "\n".join(lines)


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _validate_required(value: str, name: str) -> dict[str, Any] | None:
    if not value or not value.strip():
        return {
            "success": False,
            "error": f"Missing required parameter: {name}",
        }
    return None


# ============================================================
# COMMAND EXECUTION
# ============================================================

def run_command(
    command: list[str],
    timeout: int = 120,
) -> dict[str, Any]:

    try:

        process = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )

        return {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "command": " ".join(command),
            "stdout": redact(process.stdout[-30000:]),
            "stderr": redact(process.stderr[-30000:]),
        }

    except subprocess.TimeoutExpired:

        return {
            "success": False,
            "exit_code": -1,
            "command": " ".join(command),
            "stdout": "",
            "stderr": "COMMAND TIMEOUT",
        }

    except FileNotFoundError as exc:

        return {
            "success": False,
            "exit_code": -1,
            "command": " ".join(command),
            "stdout": "",
            "stderr": f"COMMAND NOT FOUND: {exc}",
        }

    except Exception as exc:

        return {
            "success": False,
            "exit_code": -1,
            "command": " ".join(command),
            "stdout": "",
            "stderr": str(exc),
        }


# ============================================================
# VALIDATION HELPERS
# ============================================================

def _validate_required(value: str, name: str) -> dict[str, Any] | None:
    if not value or not value.strip():
        return {
            "success": False,
            "error": f"Missing required parameter: {name}",
        }
    return None


# ============================================================
# SYSTEM
# ============================================================

@mcp.tool()
def system_info() -> dict[str, Any]:
    """
    Check installed development tools.
    """

    commands = [
        ["python", "--version"],
        ["node", "--version"],
        ["npm", "--version"],
        ["git", "--version"],
        ["npx", "vercel", "--version"],
        ["render", "--version"],
    ]

    result = {}

    for command in commands:

        result[" ".join(command)] = run_command(command)

    return result


# ============================================================
# PROJECT
# ============================================================

@mcp.tool()
def project_info() -> dict[str, Any]:
    """
    Return basic information about the current project.
    """

    ignored = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "_pycache_",
        ".next",
        "dist",
        "build",
    }

    files = []

    for path in PROJECT_DIR.iterdir():

        if path.name in ignored:
            continue

        files.append({
            "name": path.name,
            "type": "dir" if path.is_dir() else "file",
        })

    return {
        "project_dir": str(PROJECT_DIR),
        "entries": files,
    }


@mcp.tool()
def read_file(relative_path: str) -> dict[str, Any]:
    """
    Read a text file from the project directory.
    """

    err = _validate_required(relative_path, "relative_path")
    if err:
        return err

    target = (PROJECT_DIR / relative_path).resolve()

    try:
        target.relative_to(PROJECT_DIR)
    except ValueError:
        return {
            "success": False,
            "error": "Path escapes project directory",
        }

    if not target.exists() or not target.is_file():
        return {
            "success": False,
            "error": "File not found",
        }

    try:
        content = target.read_text(encoding="utf-8")
        return {
            "success": True,
            "path": relative_path,
            "size": len(content),
            "content": content[-50000:],
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


# ============================================================
# COMMANDS
# ============================================================

@mcp.tool()
def run_shell(command: str, timeout: int = 120) -> dict[str, Any]:
    """
    Run a shell command inside the project directory.
    """

    err = _validate_required(command, "command")
    if err:
        return err

    try:
        process = subprocess.run(
            command,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=True,
        )

        return {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "command": command,
            "stdout": redact(process.stdout[-30000:]),
            "stderr": redact(process.stderr[-30000:]),
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "exit_code": -1,
            "command": command,
            "stdout": "",
            "stderr": "COMMAND TIMEOUT",
        }

    except Exception as exc:
        return {
            "success": False,
            "exit_code": -1,
            "command": command,
            "stdout": "",
            "stderr": str(exc),
        }


# ============================================================
# RENDER LOGS
# ============================================================

@mcp.tool()
def render_logs(
    service: str,
    lines: int = 200,
    output_format: str = "json",
) -> dict[str, Any]:
    """
    Fetch logs from a Render service using the current Render CLI.
    Uses --output json as required by the current CLI version.
    """

    err = _validate_required(service, "service")
    if err:
        return err

    command = [
        "render",
        "logs",
        "--resources",
        service,
        "--output",
        output_format,
        "--limit",
        str(lines),
    ]

    result = run_command(command, timeout=60)

    if not result["success"]:
        return result

    raw = result.get("stdout", "")

    if not raw.strip():
        return {
            "success": True,
            "service": service,
            "format": output_format,
            "entries": [],
        }

    if output_format != "json":
        return {
            "success": True,
            "service": service,
            "format": output_format,
            "content": raw,
        }

    try:
        data = json.loads(raw)
        entries = data if isinstance(data, list) else [data]
        return {
            "success": True,
            "service": service,
            "format": output_format,
            "entries": entries[-lines:],
        }
    except json.JSONDecodeError:
        return {
            "success": True,
            "service": service,
            "format": output_format,
            "content": raw[-50000:],
        }


# ============================================================
# BROWSER
# ============================================================

def _safe_screenshot_path(filename: str | None = None) -> Path:
    if filename:
        safe = re.sub(r"[^A-Za-z0-9_\-.]", "_", filename)
        if not safe:
            safe = "screenshot"
    else:
        safe = "screenshot"

    if "." not in Path(safe).name:
        safe = safe + ".png"

    return SCREENSHOT_DIR / safe


@mcp.tool()
async def browser_screenshot(
    url: str,
    full_page: bool = False,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    Take a screenshot of a web page using Playwright.
    Screenshots are saved under .dev_debug_agent/screenshots/.
    """

    err = _validate_required(url, "url")
    if err:
        return err

    if not PLAYWRIGHT_AVAILABLE:
        return {
            "success": False,
            "url": url,
            "error": "playwright package not installed",
        }

    screenshot_path = _safe_screenshot_path(filename)

    async with async_playwright() as playwright:

        browser = await playwright.chromium.launch()
        page = await browser.new_page()

        try:
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(screenshot_path), full_page=full_page)

            return {
                "success": True,
                "url": url,
                "screenshot": str(screenshot_path),
            }

        except Exception as exc:
            return {
                "success": False,
                "url": url,
                "error": str(exc),
            }

        finally:
            await browser.close()


if __name__ == "__main__":
    mcp.run(transport="stdio")

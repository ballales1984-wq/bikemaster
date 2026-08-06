#!/usr/bin/env python3
"""
Tauri Android / Mobile Maintenance Agent
========================================

Automates the full lifecycle for a Tauri 2 + Vue 3 project:

  1. Detect current Tauri versions (CLI + Rust crate).
  2. Optionally update them to the latest (or a pinned) release.
  3. Install / update dependencies (npm / cargo).
  4. Build the frontend, desktop Tauri app, and Android APK/AAB.
  5. Commit, tag, and push to GitHub.

Usage
-----
  python scripts/tauri_agent.py update [--tauri <version>] [--cli <version>]
  python scripts/tauri_agent.py build  [--no-android] [--no-desktop]
  python scripts/tauri_agent.py release [--version <ver>] [--no-android] [--message <msg>]

Environment / prerequisites
----------------------------
- Node.js >= 18, npm >= 9
- Rust toolchain (rustup) with Android targets: aarch64-linux-android,
  armv7-linux-androideabi, i686-linux-android, x86_64-linux-android
- Android SDK + NDK (ANDROID_HOME / ANDROID_SDK_ROOT)
- Java 17 (Temurin)
- Git configured with push access

The script assumes the Tauri project lives in ./frontend relative to the repo root.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = REPO_ROOT / "frontend"
SRC_TAURI_DIR = FRONTEND_DIR / "src-tauri"
TAURI_CONF = SRC_TAURI_DIR / "tauri.conf.json"
CARGO_TOML = SRC_TAURI_DIR / "Cargo.toml"
PACKAGE_JSON = FRONTEND_DIR / "package.json"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(cmd: list[str] | str, cwd: Path | None = None, check: bool = True, capture: bool = False) -> str | None:
    """Run a shell command and return stdout (or None)."""
    if isinstance(cmd, str):
        cmd = cmd if sys.platform != "win32" else cmd.split()
    cwd = cwd or REPO_ROOT
    print(f"$ {' '.join(str(c) for c in cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            check=check,
            capture_output=capture,
            text=True,
        )
        if capture:
            return result.stdout.strip()
        return None
    except subprocess.CalledProcessError as exc:
        print(f"Command failed with exit code {exc.returncode}")
        if exc.stdout:
            print(exc.stdout)
        if exc.stderr:
            print(exc.stderr, file=sys.stderr)
        if check:
            sys.exit(exc.returncode)
        return None


def npm(args: list[str], cwd: Path = FRONTEND_DIR) -> str | None:
    bin_name = "npm.cmd" if sys.platform == "win32" else "npm"
    return run([bin_name] + args, cwd=cwd, capture=True)


def cargo(args: list[str], cwd: Path = SRC_TAURI_DIR) -> str | None:
    bin_name = "cargo.cmd" if sys.platform == "win32" else "cargo"
    return run([bin_name] + args, cwd=cwd, capture=True)


def tauri(args: list[str], cwd: Path = FRONTEND_DIR) -> str | None:
    # Prefer the local tauri CLI installed in node_modules
    tauri_bin = FRONTEND_DIR / "node_modules" / ".bin" / ("tauri.cmd" if sys.platform == "win32" else "tauri")
    if not tauri_bin.exists():
        print("Tauri CLI not found in node_modules/.bin. Run npm install first.")
        sys.exit(1)
    return run([str(tauri_bin)] + args, cwd=cwd, capture=True)


# ---------------------------------------------------------------------------
# Version detection & update
# ---------------------------------------------------------------------------

def read_package_version() -> str:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    return data.get("version", "0.0.0")


def read_tauri_rust_version() -> str:
    text = CARGO_TOML.read_text(encoding="utf-8")
    m = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def read_tauri_cli_version() -> str:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    dep = data.get("devDependencies", {}).get("@tauri-apps/cli", "")
    # strip leading ^ or ~
    return dep.lstrip("^~") if dep else "0.0.0"


def write_package_version(version: str) -> None:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    data["version"] = version
    PACKAGE_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_tauri_rust_version(version: str) -> None:
    text = CARGO_TOML.read_text(encoding="utf-8")
    text = re.sub(
        r'(tauri\s*=\s*\{[^\n]*version\s*=\s*")([^"]+)(")',
        lambda m: m.group(1) + version + m.group(3),
        text,
        count=1,
    )
    text = re.sub(
        r'(tauri-build\s*=\s*\{[^\n]*version\s*=\s*")([^"]+)(")',
        lambda m: m.group(1) + version + m.group(3),
        text,
        count=1,
    )
    CARGO_TOML.write_text(text, encoding="utf-8")


def write_tauri_cli_version(version: str) -> None:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    data.setdefault("devDependencies", {})["@tauri-apps/cli"] = f"^{version}"
    PACKAGE_JSON.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_tauri_app_version(version: str) -> None:
    data = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    data["version"] = version
    TAURI_CONF.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_latest_npm_version(package: str) -> str:
    out = run(["npm.cmd" if sys.platform == "win32" else "npm", "view", package, "version"], capture=True)
    if out:
        return out.strip()
    return ""


def get_latest_crate_version(crate: str) -> str:
    # Simple HTTP GET to crates.io API
    import urllib.request
    url = f"https://crates.io/api/v1/crates/{crate}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
        # Extract latest_version from JSON without importing json (already imported)
        m = re.search(r'"latest_version"\s*:\s*"([^"]+)"', raw)
        return m.group(1) if m else ""
    except Exception as exc:
        print(f"Failed to fetch crate version: {exc}")
        return ""


def update_versions(tauri_version: str | None, cli_version: str | None) -> None:
    current_rust = read_tauri_rust_version()
    current_cli = read_tauri_cli_version()

    target_rust = tauri_version or get_latest_crate_version("tauri") or current_rust
    target_cli = cli_version or get_latest_npm_version("@tauri-apps/cli") or current_cli

    print(f"Tauri Rust crate  : {current_rust} -> {target_rust}")
    print(f"Tauri CLI (npm)   : {current_cli} -> {target_cli}")

    write_tauri_rust_version(target_rust)
    write_tauri_cli_version(target_cli)
    write_tauri_app_version(target_rust)


# ---------------------------------------------------------------------------
# Dependency install
# ---------------------------------------------------------------------------

def install_frontend_deps() -> None:
    print("Installing frontend dependencies...")
    npm(["ci", "--no-audit", "--no-fund"])


def cargo_update() -> None:
    print("Updating Cargo dependencies...")
    cargo(["update"])


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_frontend() -> None:
    print("Building frontend...")
    npm(["run", "build"])


def build_desktop() -> None:
    print("Building desktop Tauri app...")
    tauri(["build"])


def build_android() -> None:
    print("Building Android app with Tauri CLI...")
    tauri(["android", "build"])


def ensure_android_initialized() -> bool:
    """Return True if Android is initialized (bundle.android present)."""
    if not TAURI_CONF.exists():
        return False
    data = json.loads(TAURI_CONF.read_text(encoding="utf-8"))
    return "android" in data.get("bundle", {})


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

def git_status() -> list[str]:
    out = run(["git", "status", "--porcelain"], capture=True) or ""
    return [line for line in out.splitlines() if line.strip()]


def git_add(paths: list[str]) -> None:
    run(["git", "add"] + paths)


def git_commit(message: str) -> None:
    run(["git", "commit", "-m", message])


def git_tag(version: str) -> None:
    run(["git", "tag", "-a", version, "-m", f"Release {version}"])


def git_push(branch: str | None = None) -> None:
    cmd = ["git", "push"]
    if branch:
        cmd += ["origin", branch]
    else:
        cmd += ["--follow-tags", "origin", "HEAD"]
    run(cmd)


def get_current_branch() -> str:
    out = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True) or ""
    return out.strip() or "main"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_update(args: argparse.Namespace) -> None:
    update_versions(args.tauri, args.cli)
    install_frontend_deps()
    cargo_update()
    print("Versions updated and dependencies refreshed.")


def cmd_build(args: argparse.Namespace) -> None:
    if args.no_desktop and args.no_android:
        print("Nothing to build (both --no-desktop and --no-android specified).")
        return

    build_frontend()

    if not args.no_desktop:
        build_desktop()

    if not args.no_android:
        if not ensure_android_initialized():
            print("Android is not initialized in tauri.conf.json.")
            print("Run: tauri android init")
            sys.exit(1)
        build_android()


def cmd_release(args: argparse.Namespace) -> None:
    version = args.version or read_package_version()
    message = args.message or f"chore(release): {version}"

    cmd_build(args)

    changes = git_status()
    if not changes:
        print("No changes to commit.")
    else:
        print(f"Committing {len(changes)} change(s)...")
        git_add(["."])
        git_commit(message)

    # Tag only if there are changes or force tag
    if changes or args.version:
        print(f"Tagging {version}...")
        try:
            git_tag(version)
        except SystemExit:
            # tag may already exist
            print("Tag may already exist; continuing.")

    branch = get_current_branch()
    print(f"Pushing to origin/{branch}...")
    git_push(branch)
    print("Release pushed successfully.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Tauri Android / Mobile Maintenance Agent",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_update = sub.add_parser("update", help="Update Tauri versions and dependencies")
    p_update.add_argument("--tauri", help="Pin Tauri Rust crate version (default: latest)")
    p_update.add_argument("--cli", help="Pin Tauri CLI version (default: latest)")

    p_build = sub.add_parser("build", help="Build frontend + desktop + android")
    p_build.add_argument("--no-desktop", action="store_true", help="Skip desktop build")
    p_build.add_argument("--no-android", action="store_true", help="Skip android build")

    p_release = sub.add_parser("release", help="Build, commit, tag, and push to GitHub")
    p_release.add_argument("--version", help="Semver version for the tag (default: package.json version)")
    p_release.add_argument("--message", help="Git commit message")
    p_release.add_argument("--no-desktop", action="store_true", help="Skip desktop build")
    p_release.add_argument("--no-android", action="store_true", help="Skip android build")

    args = parser.parse_args()

    if args.command == "update":
        cmd_update(args)
    elif args.command == "build":
        cmd_build(args)
    elif args.command == "release":
        cmd_release(args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

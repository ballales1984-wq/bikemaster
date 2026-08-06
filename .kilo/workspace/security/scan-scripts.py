#!/usr/bin/env python3
"""Security scan scripts for BikeMaster."""

import os
import re
import subprocess
import sys


def run_cmd(cmd, cwd=None):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, cwd=cwd
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def scan_secrets(path="."):
    """Scan for hardcoded secrets."""
    patterns = [
        r'(?i)(api[_-]?key|secret|token|password|passwd|client[_-]?secret|bearer)\s*[:=]\s*[\'"][^\'"]+[\'"]',
        r'(?i)(sk-|ghp_|AIza|xoxb-)\w+',
    ]
    
    print("[SECRETS SCAN] Scanning for hardcoded secrets...")
    findings = []
    
    for root, dirs, files in os.walk(path):
        # Skip node_modules, .git, .kilo
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.kilo', '__pycache__']]
        
        for file in files:
            if file.endswith(('.py', '.ts', '.vue', '.js', '.json', '.yaml', '.yml', '.env')):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        for pattern in patterns:
                            matches = re.finditer(pattern, content)
                            for match in matches:
                                findings.append(f"  {filepath}: {match.group()[:50]}...")
                except Exception:
                    pass
    
    if findings:
        print(f"[WARNING] Found {len(findings)} potential secrets:")
        for f in findings:
            print(f)
        return 1
    else:
        print("[OK] No secrets found.")
        return 0

def scan_dependencies():
    """Check for vulnerable dependencies."""
    print("[DEPENDENCY SCAN] Checking dependencies...")
    
    # Frontend
    frontend_dir = "frontend"
    if os.path.exists(frontend_dir):
        print("  Running npm audit on frontend...")
        rc, out, err = run_cmd("npm audit --audit-level=high", cwd=frontend_dir)
        if rc != 0:
            print(f"  [WARNING] Frontend vulnerabilities found:\n{out[:500]}")
        else:
            print("  [OK] Frontend dependencies clean.")
    
    # Backend
    print("  Checking backend requirements...")
    for req_file in ['requirements.txt', 'requirements-dev.txt', 'pyproject.toml']:
        if os.path.exists(req_file):
            print(f"  Found {req_file} - consider running pip-audit")
    
    return 0

def check_gitignore():
    """Verify .gitignore covers sensitive files."""
    print("[GITIGNORE] Checking .gitignore...")
    gitignore_path = ".gitignore"
    
    if not os.path.exists(gitignore_path):
        print("  [WARNING] No .gitignore found!")
        return 1
    
    with open(gitignore_path) as f:
        content = f.read()
    
    required = ['.env', '*.env', 'secrets/', '*.pem', '*.key', 'node_modules/', '__pycache__/']
    missing = [r for r in required if r not in content]
    
    if missing:
        print(f"  [WARNING] Missing entries in .gitignore: {missing}")
        return 1
    else:
        print("  [OK] .gitignore covers sensitive patterns.")
        return 0

def check_cors():
    """Check CORS configuration."""
    print("[CORS] Checking CORS configuration...")
    cors_pattern = r'allow_origins\s*=\s*\[?\s*["\']?\*["\']?'
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '.kilo', '__pycache__']]
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if re.search(cors_pattern, content):
                            print(f"  [WARNING] Wildcard CORS found in {filepath}")
                            return 1
                except Exception:
                    pass
    
    print("  [OK] No wildcard CORS found.")
    return 0

def main():
    """Run all security scans."""
    print("=" * 60)
    print("BikeMaster Security Scan")
    print("=" * 60)
    
    results = []
    
    results.append(("Secrets", scan_secrets()))
    results.append(("Gitignore", check_gitignore()))
    results.append(("CORS", check_cors()))
    results.append(("Dependencies", scan_dependencies()))
    
    print("\n" + "=" * 60)
    print("SCAN SUMMARY")
    print("=" * 60)
    
    failed = [name for name, rc in results if rc != 0]
    
    if failed:
        print(f"[ISSUES FOUND] in: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("[ALL CHECKS PASSED]")
        sys.exit(0)

if __name__ == "__main__":
    main()

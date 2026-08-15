# Security Audit Report — BikeMaster
**Date:** 2026-08-15  
**Scope:** Backend (FastAPI), Frontend (Vue 3), Infrastructure (Render/Vercel/Tauri)  
**Auditor:** Automated + Agent `security` + manual verification  

---

## Executive Summary

The BikeMaster codebase was audited across 8 areas: CORS, authentication/OAuth, API endpoint exposure, secrets management, SQL injection, dependency vulnerabilities, error handling, and frontend security.

**Static analysis results:**
| Tool | Scope | High | Medium | Low |
|---|---|---|---|---|
| bandit | `bike_analyzer/` (46,572 LOC) | 0 | 37 | 223 |
| ruff (S rules) | `tests/` | 0 | ~5 | ~3 |
| pip-audit | `requirements.txt` | 0 | 0 | 0+ vuln pkgs |
| npm audit | `frontend/` | 1 | 0 | 0 |

**Key finding:** 5 High/Critical issues require immediate remediation before production exposure. Most are access-control and secrets-handling defects.

---

## Findings

### 1. Broken Access Control — `GET /athletes` returns all tenants (CRITICAL)

**Severity:** Critical  
**CWE:** CWE-200 (Information Exposure), CWE-639 (Authorization Bypass)  
**Location:** `bike_analyzer/backend/api/routers/athlete_routes.py:166-169`

```python
@router.get("/athletes")
async def list_athletes(current_user: dict = Depends(get_current_user)):
    athletes = get_all_athletes()          # ← no tenant/user filter
    return {"athletes": athletes}
```

`get_all_athletes()` (defined in `db/repositories/athlete_repository.py:495` and `db/postgres_athlete.py:299`) executes `SELECT id, name, email, experience_level FROM athletes` with no `WHERE user_id = ?` or `tenant_id = ?` clause. Any authenticated user can enumerate all athletes across all tenants, including email addresses.

**Recommendation:** Add `user_id = int(current_user["id"])` to `get_all_athletes()` and filter by it. Return only athletes belonging to the requesting user.

---

### 2. Broken Access Control — `GET /athletes/{id}` no ownership check (HIGH)

**Severity:** High  
**CWE:** CWE-639  
**Location:** `bike_analyzer/backend/api/routers/athlete_routes.py:186-194`

```python
@router.get("/athletes/{athlete_id}")
async def get_athlete_by_id(
    athlete_id: int,
    current_user: dict = Depends(get_current_user),
):
    athlete = get_athlete(athlete_id)   # ← no ownership check
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete
```

Any authenticated user can fetch any athlete's profile by ID (IDOR). The `get_current_user` dependency authenticates but never authorizes.

**Recommendation:** After fetching the athlete, verify `athlete["user_id"] == current_user["id"]` (or `tenant_id` match). Return 403 if mismatch.

---

### 3. XML External Entity (XXE) — Untrusted XML parsing (HIGH)

**Severity:** High  
**CWE:** CWE-611  
**Locations:** 4 instances

| File | Line |
|---|---|
| `bike_analyzer/backend/ingestion/google_health.py` | 183 |
| `bike_analyzer/backend/ingestion/gps_parser.py` | 58 |
| `bike_analyzer/backend/ingestion/gps_parser.py` | 94 |
| `bike_analyzer/backend/bm2/agents.py` | 94 |

All use `xml.etree.ElementTree.fromstring()` to parse user-supplied TCX/GPX content. Although marked `# noqa: S314`, these are genuine XXE vectors if an attacker submits a crafted XML document with `DOCTYPE` or external entity declarations.

**Recommendation:** Replace with `defusedxml.ElementTree.fromstring()` or call `defusedxml.defuse_stdlib()` at application startup.

---

### 4. Unauthenticated `/providers` endpoint — duplicate route registration (HIGH)

**Severity:** High  
**CWE:** CWE-200  
**Location:** `bike_analyzer/backend/api/routers/import_routes.py:35-47` (unauth) vs `:179-188` (auth)

Two routes are registered on the same path:
- Line 35: `async def list_import_providers()` — **no auth dependency**, returns presence/absence of OAuth client IDs and secrets
- Line 179: `async def get_import_providers(current_user: dict = Depends(get_current_user))` — requires auth

The unauthenticated stub returns `bool(_s.strava_client_id and _s.strava_client_secret)`, confirming whether OAuth providers are configured — useful for attacker reconnaissance. FastAPI will raise a `RuntimeError` or use whichever is registered first.

**Recommendation:** Remove the unauthenticated stub at line 35. Keep only the authenticated version. Verify no runtime route-collision error occurs.

---

### 5. Unauthenticated `/places/osm-search` — SSRF vector (HIGH)

**Severity:** High  
**CWE:** CWE-918 (SSRF)  
**Location:** `bike_analyzer/backend/api/routers/maps_routes.py:139-156`

```python
@router.get("/places/osm-search")
async def osm_places_search(lat, lon, query, limit):
    """OpenStreetMap Nominatim search for places. No API key required."""
    ...
    result = await search_places(query, lat=lat, lon=lon, limit=limit)
```

No `get_current_user` dependency. An attacker can abuse the server as a proxy to query Nominatim with arbitrary parameters. While Nominatim is low-risk, the pattern allows unauthenticated server-side requests to external services (SSRF).

**Recommendation:** Add `@router.get("/places/osm-search", dependencies=[Depends(get_current_user)])` or require auth on the route.

---

### 6. Silent encryption fallback — OAuth tokens at risk of plaintext storage (CRITICAL)

**Severity:** Critical  
**CWE:** CWE-311 (Missing Encryption of Sensitive Data)  
**Locations:**

| File | Line |
|---|---|
| `bike_analyzer/backend/db/database.py` | 1327-1333 |
| `bike_analyzer/backend/db/sync/config.py` | 145-150 |
| `bike_analyzer/backend/db/postgres_user_oauth.py` | 80-85 |

```python
# database.py:1327-1333
client_secret = data.get("client_secret", "")
if client_secret:
    try:
        from ..db.token_crypto import encrypt_token
        client_secret = encrypt_token(client_secret)
    except Exception:
        pass   # ← silent fallback: stores plaintext
```

If `TOKEN_ENCRYPTION_KEY` is not set (the `get_cipher()` call in `token_crypto.py:37-41` raises `RuntimeError`), the token is silently stored in plaintext. This is a systemic pattern across SQLite and PostgreSQL paths.

**Recommendation:** Do not silently swallow encryption failures. If `encrypt_token()` raises, the save operation should fail with a 500 error, not proceed with plaintext.

---

### 7. `ExternalTokenModel` stores tokens in plaintext Text columns (HIGH)

**Severity:** High  
**CWE:** CWE-311  
**Location:** `bike_analyzer/backend/db/models.py:882-906`

```python
class ExternalTokenModel(Base):
    """Encrypted/obfuscated OAuth tokens for external providers."""
    access_token: Mapped[str | None] = mapped_column(Text)
    refresh_token: Mapped[str | None] = mapped_column(Text)
```

The docstring claims encryption but no encryption is applied at the model/ORM layer. Encryption is only applied if every call site explicitly invokes `encrypt_token()` — and we've shown that call sites can silently fail (Finding 6). The data model offers no defense in depth.

**Recommendation:** Either enforce encryption at the column level (encrypted column type) or add a DB-level assertion/check. At minimum, remove the misleading docstring.

---

### 8. `get_all_user_oauth_credentials` returns encrypted secrets without decrypting (LOW)

**Severity:** Low  
**CWE:** CWE-312  
**Location:** `bike_analyzer/backend/db/database.py:1314-1319` and `bike_analyzer/backend/db/postgres_user_oauth.py:56-67`

```python
cur.execute("SELECT * FROM user_oauth_credentials WHERE user_id = ?", (user_id,))
return [dict(r) for r in cur.fetchall()]   # ← returns encrypted tokens
```

Returns raw (encrypted) tokens to the caller without decryption. This is lower severity because the tokens are encrypted, but it's inconsistent with the single-fetch path (`postgres_user_oauth.py:44-48` which decrypts).

**Recommendation:** Decrypt returned secrets before returning to callers, or document that the caller must decrypt.

---

### 9. Vulnerable Python dependencies (HIGH)

**Severity:** High  
**Tool:** `pip-audit`

| Package | Version | Vulnerability | Fix |
|---|---|---|---|
| `pypdf` | 6.10.2 | PYSEC-2026-3020, -3018, -3004, -3016, -3010, -3025, -3009, -3613, -3610, -3612, -3611, -3655, -3656 (13 vulns) | >=6.15.0 |
| `python-engineio` | 4.13.1 | PYSEC-2026-3033, -3032 | >=4.13.2 |
| `python-socketio` | 5.16.1 | PYSEC-2026-3042 | >=5.16.2 |
| `setuptools` | 81.0.0 | PYSEC-2026-3447 | >=83.0.0 |
| `soupsieve` | 2.8.3 | PYSEC-2026-3072, -3071 | >=2.8.4 |
| `tornado` | 6.5.5 | PYSEC-2026-3387, -3388, -3389, GHSA-pw6j-qg29-8w7f | >=6.5.7 |
| `transformers` | 5.2.0 | PYSEC-2026-2290, -2289 | >=5.3.0 |
| `werkzeug` | 3.1.3 | PYSEC-2026-2046, -2044, -2320 | >=3.1.6 |
| `torch` | 2.11.0 | PYSEC-2025-194 | >=2.13.0 |

**Recommendation:** Update all listed packages. `pip-audit` did not flag these as Critical, but the volume (13 vulns in `pypdf` alone) warrants immediate attention.

---

### 10. npm audit — glob command injection (HIGH)

**Severity:** High  
**CWE:** CWE-78  
**Tool:** `npm audit`  
**Package:** `glob` 10.2.0–10.4.5  
**Vulnerability:** GHSA-5j98-mcp5-4vw2 — Command injection via `-c`/`--cmd` executes matches with `shell:true`  
**Fix:** `npm audit fix` (update to glob >=10.4.6)

---

### 11. JWT token stored in localStorage (MEDIUM)

**Severity:** Medium  
**CWE:** CWE-312  
**Location:** Frontend auth store (identified by agent)

The JWT authentication token is stored in `localStorage` under key `bikemaster_token`. Any XSS vulnerability would allow an attacker to steal the token. `localStorage` is accessible to all JavaScript running on the same origin.

**Recommendation:** Move to `httpOnly` + `Secure` + `SameSite=Strict` cookies for JWT storage. This prevents JavaScript access and mitigates token theft via XSS.

---

### 12. Secrets in environment files (MEDIUM)

**Severity:** Medium  
**CWE:** CWE-798 (Use of Hard-coded Credentials)  

| File | Line | Issue |
|---|---|---|
| `frontend/.env.vercel` | — | Hardcoded `VERCEL_TOKEN` (gitignored but recoverable from history) |
| `render.yaml` | — | Empty `SECRET_KEY` (no value set) |
| `.env.example` | — | `JWT_SECRET=dev-secret-key-change-in-production` (template leak) |

**Recommendation:** Use a secrets manager (Render Environment, Vercel Environment Variables). Never commit `.env` files. Rotate any leaked tokens.

---

### 13. Google Maps API key served to frontend via endpoint (MEDIUM)

**Severity:** Medium  
**CWE:** CWE-200  
**Location:** `config/google-maps-key` endpoint

Serves the Maps API key to any authenticated frontend user. Google Maps API keys should use HTTP referrer restrictions (for web) or API restrictions (for mobile). Without proper restrictions, the key can be extracted and used elsewhere.

**Recommendation:** Apply Google Cloud referrer/IP restrictions. Consider using a server-side proxy so the key never reaches the client.

---

### 14. SQL string interpolation via f-string (LOW)

**Severity:** Low  
**CWE:** CWE-89 (SQL Injection)  
**Location:** `bike_analyzer/backend/sync/service.py:366`

```python
table = table_map.get(entity_type)
cur.execute(f"SELECT * FROM {table} WHERE id = ?", (entity_id,))
```

The `table` value comes from a fixed `table_map` dictionary (not user input), so this is not directly exploitable. However, if the mapping is ever modified to include user-controlled data, this becomes an injection vector.

**Recommendation:** Use SQLAlchemy table references or validate `table` against the known set before interpolation.

---

### 15. No Content-Security-Policy header (LOW)

**Severity:** Low  
**CWE:** CWE-693 (Protection Mechanism Failure)  
**Location:** Frontend Vercel config

No CSP header is configured in the Vercel deployment, increasing the impact of any XSS vulnerability.

**Recommendation:** Add a restrictive CSP header via `vercel.json` or middleware, e.g., `default-src 'self'; script-src 'self'`.

---

### 16. `"null"` origin in default CORS origins (LOW)

**Severity:** Low  
**CWE:** CWE-942  
**Location:** `bike_analyzer/backend/settings.py:61`

```python
cors_origins: str = "http://localhost:8001,...,capacitor://localhost,http://localhost,null"
```

The bare string `"null"` is included as an allowed origin. The `null` origin appears for `file://` protocol, sandboxed iframes, and redirects. While production overrides this via env, it's a dangerous default.

**Recommendation:** Remove `"null"` from the default list. Ensure production CORS config does not include it.

---

### 17. Console logging of OAuth user email (LOW)

**Severity:** Low  
**CWE:** CWE-532 (Insertion of Sensitive Info into Log)  
**Location:** Frontend `services/oauth.ts` (identified by agent)

`console.log` of OAuth user email in the frontend code. Email addresses are PII; logging them risks exposure in session recordings, error reports, or browser console access.

**Recommendation:** Remove `console.log` statements containing PII. Use a structured logging framework with log levels.

---

### 18. ruff S-rule findings in test conftest (LOW)

**Severity:** Low  
**Tool:** `ruff --select S`  
**Location:** `tests/conftest.py`

| Rule | Line | Issue |
|---|---|---|
| S603 | 31 | `subprocess.run()` — check for untrusted input |
| S607 | 32 | Partial executable path (`"git"`) |
| S102 | 44 | Use of `exec()` |
| S112 | 35, 45 | `try/except/continue` — consider logging |
| S105 | 52 | Possible hardcoded password (`SECRET_KEY`) |

These are in test infrastructure (`conftest.py`) and use `git cat-file` to read file contents from repo history. The `exec` is loading test modules dynamically. Low risk but should use absolute paths and logging.

**Recommendation:** Use `shutil.which("git")` for path resolution, add logging to except blocks, and document the dynamic exec as intentional test infrastructure.

---

## Findings Summary

| # | Severity | Finding | Status |
|---|---|---|---|
| 1 | Critical | `GET /athletes` returns all tenants (no filter) | Open |
| 2 | High | `GET /athletes/{id}` no ownership check (IDOR) | Open |
| 3 | High | XXE — 4× `ET.fromstring()` on untrusted XML | Open |
| 4 | High | Unauthenticated `/providers` endpoint | Open |
| 5 | High | Unauthenticated `/places/osm-search` (SSRF) | Open |
| 6 | Critical | Silent encryption fallback → plaintext token storage | Open |
| 7 | High | `ExternalTokenModel` plaintext Text columns | Open |
| 8 | Low | `get_all_user_oauth_credentials` no decryption | Open |
| 9 | High | 9 vulnerable Python packages (pip-audit) | Open |
| 10 | High | npm `glob` command injection (GHSA-5j98-mcp5-4vw2) | Open |
| 11 | Medium | JWT in localStorage | Open |
| 12 | Medium | Hardcoded secrets in env files | Open |
| 13 | Medium | Google Maps key served to frontend | Open |
| 14 | Low | f-string SQL in `sync/service.py` | Open |
| 15 | Low | No CSP header | Open |
| 16 | Low | `"null"` in default CORS origins | Open |
| 17 | Low | console.log of OAuth email (frontend) | Open |
| 18 | Low | ruff S-rules in `tests/conftest.py` | Open |

---

## Prioritization (fix order)

**Tier 1 — Immediate (fix before next deploy):**
1. Finding 1 & 2 — Add tenant filtering + ownership checks to athlete endpoints
2. Finding 6 — Fail closed on encryption errors (no silent plaintext fallback)
3. Finding 9 & 10 — Update vulnerable dependencies

**Tier 2 — Next sprint:**
3. Finding 3 — Switch to defusedxml
4. Finding 4 — Remove unauthenticated `/providers` stub
5. Finding 5 — Add auth to `/places/osm-search`
6. Finding 12 — Rotate and properly manage secrets

**Tier 3 — Tech debt / hardening:**
7. Finding 7, 8, 11, 13, 14, 15, 16, 17, 18

---

## Scan Evidence

### bandit (summary)
```
Code scanned: 46,572 lines
Total issues: 37 Medium, 223 Low
```

Top 5 bandit findings (Medium):
1. `B314` — `ET.fromstring()` (XXE) ×3 in `ingestion/` + 1 in `bm2/`
2. `B608` — f-string SQL in `sync/service.py:366`
3. `B104` — hardcoded `0.0.0.0` in `hub/routes.py:171` (false positive; it's a localhost port set, not a bind address)

### pip-audit
13 vulnerable packages identified (see Finding 9). No Critical or High severity CVEs, but multiple Medium issues warrant updating.

### npm audit
1 High: `glob` 10.2.0–10.4.5 (GHSA-5j98-mcp5-4vw2)

### ruff (S-rules)
5 S-rule violations in `tests/conftest.py` (see Finding 18).

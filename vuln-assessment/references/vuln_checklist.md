# Vulnerability Hunting Checklist

Work through every category in Phase 4. For each, determine: present / not present / N/A.
Record a finding for every confirmed issue.

---

## A. Injection (OWASP A03:2021)

### A1. SQL Injection (CWE-89)
- [ ] Are SQL queries constructed with f-strings, % formatting, or string concatenation?
- [ ] Are any user-controlled values (from HTTP, message queues, files, env) interpolated directly?
- [ ] Is there any manual escaping (`.replace("'","''")`)? → always incomplete, flag as finding
- [ ] Are ORM raw queries or `execute()` calls used with string formatting instead of `%s` params?
- [ ] Are table names or column names dynamic? (parameterized queries can't bind identifiers)
- [ ] Are stored procedure calls constructed dynamically?

### A2. Command Injection (CWE-78)
- [ ] Is `subprocess.run()`, `os.system()`, `os.popen()`, or `eval()` called?
- [ ] Are any arguments to shell commands derived from user input?
- [ ] Is `shell=True` used with any subprocess call?

### A3. NoSQL Injection (CWE-943)
- [ ] Are MongoDB query operators (`$where`, `$regex`) constructed from user input?
- [ ] Are Elasticsearch DSL queries built by string concatenation?
- [ ] Are Redis key names constructed from user-controlled data without sanitization?

### A4. LDAP Injection (CWE-90)
- [ ] Is LDAP used? Are filter strings constructed from user input?

### A5. Template Injection (CWE-94)
- [ ] Are Jinja2/Mako/similar templates rendered with user-controlled strings?
- [ ] Is `eval()` or `exec()` called with user data?

### A6. Path Traversal (CWE-22)
- [ ] Are file paths constructed using `os.path.join()` with user-supplied components?
- [ ] Is `../` or absolute path injection possible in file open/read/write calls?
- [ ] After path construction, is `os.path.realpath()` + prefix check performed?

---

## B. Authentication & Session (OWASP A07:2021)

### B1. Hardcoded Credentials (CWE-798)
- [ ] Are passwords, API keys, tokens, or secrets hardcoded in source files?
- [ ] Are internal URLs or IPs hardcoded (bypassing config management)?
- [ ] Are default credentials used (admin/admin, etc.)?
- [ ] Are credentials in config files committed to version control?

### B2. Weak Session Management
- [ ] Are session tokens cryptographically random and sufficiently long?
- [ ] Are JWTs validated (signature, expiry, issuer)? Is `alg=none` accepted?
- [ ] Are session tokens stored securely (httpOnly, Secure, SameSite cookies)?
- [ ] Are sessions invalidated on logout?

### B3. Broken Authentication
- [ ] Is MFA enforced for privileged operations?
- [ ] Is brute force protection in place (rate limiting, lockout)?
- [ ] Are password reset flows secure (no predictable tokens, short expiry)?

### B4. Credential Exposure
- [ ] Are credentials logged (in debug logs, error messages, audit trails)?
- [ ] Are credentials transmitted over plaintext HTTP?
- [ ] Are secrets in environment variables validated at startup (startup validation)?

---

## C. Authorization & Access Control (OWASP A01:2021)

### C1. Broken Object-Level Authorization (BOLA/IDOR, CWE-639)
- [ ] Are resource IDs from user input validated against the requesting user's ownership?
- [ ] Can user A access user B's data by manipulating an ID parameter?
- [ ] Is multi-tenancy enforced at every query (not just at the API boundary)?

### C2. Privilege Escalation (CWE-269)
- [ ] Can a regular user perform admin-only actions?
- [ ] Is role/permission checked at each sensitive operation or only at login?
- [ ] Is there a confused deputy problem (service acting on behalf of user without re-checking perms)?

### C3. Missing Function-Level Access Control (CWE-284)
- [ ] Are internal/admin endpoints accessible without authentication?
- [ ] Are authorization checks applied consistently (not just in some code paths)?

---

## D. Cryptography (OWASP A02:2021)

### D1. Weak Algorithms (CWE-327)
- [ ] Is MD5 or SHA-1 used for security-sensitive hashing?
- [ ] Is DES, 3DES, or RC4 used for encryption?
- [ ] Are ECB mode block ciphers used?
- [ ] Are passwords hashed with non-PBKDF algorithms (plain SHA-256, MD5)?

### D2. Key Management (CWE-320)
- [ ] Are cryptographic keys hardcoded?
- [ ] Are keys rotatable without code changes?
- [ ] Are keys of sufficient length (AES-128 minimum, RSA-2048 minimum)?

### D3. Transport Security (CWE-319)
- [ ] Are any internal service calls made over HTTP instead of HTTPS?
- [ ] Is certificate validation disabled (`verify=False`, `InsecureRequestWarning`)?
- [ ] Are weak TLS versions (TLS 1.0, 1.1) or cipher suites accepted?

### D4. Random Number Generation (CWE-338)
- [ ] Is `random` module (not `secrets`) used for security tokens, OTPs, or session IDs?
- [ ] Are UUIDs generated with `uuid4()` (cryptographically random) not `uuid1()`?

---

## E. Security Misconfiguration (OWASP A05:2021)

### E1. Debug / Development Settings
- [ ] Is debug mode enabled in production config?
- [ ] Are verbose error messages (stack traces) returned to clients?
- [ ] Are admin UIs (Django admin, Flower, Kibana) exposed without auth?

### E2. Unnecessary Exposure
- [ ] Are unused ports, services, or endpoints open?
- [ ] Are directory listings enabled on web servers?
- [ ] Are internal APIs accessible from external networks?

### E3. Security Headers (web apps)
- [ ] Are CSP, HSTS, X-Frame-Options, X-Content-Type-Options headers set?
- [ ] Is CORS configured with `*` or overly permissive origins?

---

## F. Vulnerable Components (OWASP A06:2021)

### F1. Dependency Vulnerabilities (CWE-1395)
- [ ] Check `requirements.txt` / `pyproject.toml` / `package.json` for known-vulnerable versions
- [ ] Run mental CVE check on major dependencies (especially networking, auth, parsing libs)
- [ ] Are dependencies pinned to specific versions (reproducible builds)?

### F2. Outdated Runtime
- [ ] Is the language runtime version documented and up to date?
- [ ] Are deprecated API usages present?

---

## G. Data Exposure & Logging (OWASP A02:2021 / CWE-312)

### G1. Sensitive Data in Logs
- [ ] Are passwords, tokens, PII, or secrets logged (even at DEBUG level)?
- [ ] Are full request/response bodies logged (may contain credentials)?
- [ ] Are database query strings logged (may expose parameterized values)?

### G2. Sensitive Data in Storage
- [ ] Are credentials stored in plaintext in the database?
- [ ] Are sensitive fields (SSN, card numbers) encrypted at rest?
- [ ] Is PII retained longer than necessary?

### G3. Sensitive Data in Transit
- [ ] Are API keys or tokens included in URLs (logged by proxy/server)?
- [ ] Are sensitive fields in HTTP headers or query strings?

---

## H. Architecture & Design Issues

### H1. Connection Pool Management (CWE-772)
- [ ] Are database connections pooled or created per-request?
- [ ] Are connections properly closed/returned to the pool on error?
- [ ] Are connection pool limits configured appropriately for expected load?
- [ ] Are MongoDB, Redis, Elasticsearch clients singletons or per-request?

### H2. Thread Safety (CWE-362)
- [ ] Are shared mutable state objects (dicts, lists, counters) accessed from multiple threads?
- [ ] Are non-thread-safe operations (e.g., check-then-act on shared state) possible?
- [ ] Are locks used correctly (no deadlock risk, correct granularity)?

### H3. Cache Security (CWE-524)
- [ ] Can cache poisoning occur (attacker controls cache key or cached value)?
- [ ] Is stale cached data a security risk (e.g., LRU-cached auth decisions)?
- [ ] Are cache TTLs appropriate for the sensitivity of the cached data?

### H4. Race Conditions / TOCTOU (CWE-367)
- [ ] Is there time between checking a condition and acting on it where state can change?
- [ ] Are file operations (check existence, then read) vulnerable to TOCTOU?

### H5. Error Handling (CWE-755)
- [ ] Do unhandled exceptions leak stack traces or sensitive info to external callers?
- [ ] Are all error paths tested? Can an error path skip a security check?
- [ ] Are exceptions caught too broadly (bare `except:`) hiding security failures?

### H6. Denial of Service
- [ ] Can an attacker cause unbounded resource consumption (memory, CPU, connections, threads)?
- [ ] Are there missing rate limits on expensive operations?
- [ ] Can malformed input cause infinite loops or exponential regex backtracking?

---

## I. Cloud-Specific (AWS / GCP / Azure)

### I1. IAM & Credentials
- [ ] Are IAM roles scoped to least-privilege (not `*` actions or resources)?
- [ ] Are temporary credentials used (STS, Workload Identity) or long-lived access keys?
- [ ] Are AWS access keys hardcoded or in environment? (prefer IAM roles)
- [ ] Is credential rotation automated?

### I2. Storage Security
- [ ] Are S3 buckets / GCS buckets / Azure Blob containers publicly accessible?
- [ ] Are bucket policies reviewed for overly permissive access?
- [ ] Is server-side encryption enabled?

### I3. Network Security
- [ ] Are security groups / firewall rules minimal (no 0.0.0.0/0 on sensitive ports)?
- [ ] Is VPC/network segmentation used between services?
- [ ] Are metadata endpoints (169.254.169.254) accessible from untrusted code paths?

### I4. Message Queue Security
- [ ] Is SQS/Pub-Sub access restricted to authorized producers/consumers?
- [ ] Are message signatures/integrity verified?
- [ ] Is dead-letter queue monitored for security events?

### I5. Secrets Management
- [ ] Are secrets stored in AWS Secrets Manager / GCP Secret Manager / Azure Key Vault?
- [ ] Are secrets rotated automatically?
- [ ] Are secrets ever written to logs, S3, or other durable storage?

---

## J. Supply Chain (OWASP A08:2021)

### J1. Dependency Integrity
- [ ] Are package hashes pinned (pip hash checking, npm lockfile integrity)?
- [ ] Are packages downloaded from trusted registries only?
- [ ] Is there a process for reviewing new dependencies?

### J2. CI/CD Security
- [ ] Are build pipelines protected from malicious PR injection?
- [ ] Are secrets in CI/CD properly scoped to the pipelines that need them?
- [ ] Is the build environment reproducible and auditable?

---

## K. Business Logic

### K1. Logic Bypasses
- [ ] Can workflow steps be skipped by manipulating state or input?
- [ ] Are state machine transitions validated (can an attacker force an invalid transition)?
- [ ] Are numeric values validated for range and overflow?

### K2. Multi-Tenancy Isolation
- [ ] Is tenant data segregated at every layer (DB, cache, object storage, logs)?
- [ ] Can a tenant access another tenant's data by manipulating IDs?
- [ ] Are tenant-specific configurations validated at each use point (not just at load)?

---

## L. XSS & Client-Side Injection (OWASP A03:2021 / CWE-79, CWE-352, CWE-601)

### L1. Reflected XSS (CWE-79)
- [ ] Is user-controlled input (query params, headers, path segments) echoed back in HTML responses without encoding?
- [ ] Are error messages that include raw user input rendered in HTML context?
- [ ] Are URL fragments (`#`) or `window.location` values rendered server-side without sanitization?
- [ ] Are HTTP headers like `Referer`, `User-Agent`, `X-Forwarded-For` reflected in responses?

### L2. Stored XSS (CWE-79)
- [ ] Is user-supplied data stored and later rendered in HTML without output encoding?
- [ ] Are rich-text or HTML fields sanitized with an allowlist-based library (e.g. DOMPurify, bleach)?
- [ ] Can stored content be rendered in a different security context (admin panel, email, PDF)?
- [ ] Are filenames, metadata, or user profile fields rendered as raw HTML anywhere?

### L3. DOM-Based XSS
- [ ] Does JavaScript read from `location.hash`, `document.URL`, `document.referrer`, or `postMessage` and write to `innerHTML`, `outerHTML`, `document.write`, or `eval`?
- [ ] Are client-side template engines (Handlebars, Angular, Vue) rendering untrusted data with triple-brace or `v-html`?
- [ ] Are `jQuery.html()`, `$.append()`, or similar sink methods called with user-controlled data?

### L4. Content Security Policy (CWE-693)
- [ ] Is a CSP header set? Does it block inline scripts (`unsafe-inline`) and `eval` (`unsafe-eval`)?
- [ ] Does the CSP use nonces or hashes rather than broad source allowlists?
- [ ] Are CSP report violations sent to a monitoring endpoint (`report-uri` / `report-to`)?
- [ ] Are `X-Frame-Options` or `frame-ancestors` set to prevent clickjacking?
- [ ] Are `X-Content-Type-Options: nosniff` and `Referrer-Policy` headers present?

### L5. CSRF (CWE-352)
- [ ] Are state-changing operations (POST/PUT/PATCH/DELETE) protected by CSRF tokens or `SameSite=Strict/Lax` cookies?
- [ ] Are CSRF tokens per-session and cryptographically random?
- [ ] Are CORS preflight checks strict enough that cross-origin writes are blocked?
- [ ] Are `SameSite` cookie attributes set on session and auth cookies?

### L6. Open Redirect (CWE-601)
- [ ] Are `next=`, `redirect=`, `return_to=`, `url=`, or `goto=` parameters used in redirects?
- [ ] Is the redirect target validated against an allowlist of trusted domains?
- [ ] Can an attacker craft a URL like `//evil.com` or `https://legit.com@evil.com` that bypasses naive prefix checks?
- [ ] Are redirect targets logged to detect redirect-chain phishing?

### L7. Clickjacking (CWE-1021)
- [ ] Are sensitive pages (account settings, payment, delete actions) embeddable in iframes from other origins?
- [ ] Is `X-Frame-Options: DENY/SAMEORIGIN` or `Content-Security-Policy: frame-ancestors` set?

---

## M. SSRF & Request Forgery (OWASP A10:2021 / CWE-918)

### M1. Server-Side Request Forgery (CWE-918)
- [ ] Are URLs or hostnames accepted from user input and used to make outbound HTTP requests?
- [ ] Are webhook URLs, avatar URLs, import-from-URL, or URL preview features present?
- [ ] Is the outbound request target validated against a blocklist of private IP ranges (10.x, 172.16.x, 192.168.x, 127.x, 169.254.x)?
- [ ] Can the scheme be manipulated to use `file://`, `dict://`, `gopher://`, `ftp://`, or `sftp://`?
- [ ] Is DNS rebinding possible (hostname resolves to public IP at validation time, then to internal IP at request time)?
- [ ] Are URL redirects followed blindly, potentially bypassing initial validation?

### M2. Cloud Metadata SSRF
- [ ] Can user-controlled URLs reach the AWS metadata endpoint (`http://169.254.169.254/latest/meta-data/`)?
- [ ] Can they reach GCP metadata (`http://metadata.google.internal/`) or Azure metadata (`http://169.254.169.254/metadata/instance`)?
- [ ] Are IMDSv2 (token-required metadata) enforced at the infrastructure level?
- [ ] Is there IMDSv1 fallback that could be exploited via SSRF?

### M3. Blind SSRF
- [ ] Even without a direct response, can timing differences or DNS lookups confirm internal service existence?
- [ ] Are out-of-band channels (DNS callbacks, Burp Collaborator equivalent) considered in the analysis?

### M4. Webhook & URL Fetch Abuse
- [ ] Are webhook delivery endpoints validated to prevent internal service discovery?
- [ ] Can webhook retry logic be abused to perform port scanning on internal networks?
- [ ] Is the response body from fetched URLs ever stored or returned to the user (full SSRF vs. blind)?

---

## N. Deserialization & Unsafe Parsing (OWASP A08:2021 / CWE-502, CWE-611, CWE-827)

### N1. Insecure Deserialization (CWE-502)
- [ ] Is `pickle.loads()` or `pickle.load()` called with data from untrusted sources (HTTP body, Redis, queue messages, cookies)?
- [ ] Is `yaml.load()` called without `Loader=yaml.SafeLoader`? (arbitrary Python object construction)
- [ ] Is `marshal.loads()`, `shelve`, or `jsonpickle` used with untrusted input?
- [ ] Are Java serialization streams (`ObjectInputStream`) or .NET `BinaryFormatter` used? (gadget chain risk)
- [ ] Is `eval()` or `exec()` called with deserialized/decoded content?
- [ ] Are signed or encrypted cookies used, and is the signing key adequately protected?

### N2. XML External Entity Injection (CWE-611)
- [ ] Is XML parsed from user input? Is `lxml`, `xml.etree`, `defusedxml`, or `minidom` used?
- [ ] Is entity resolution disabled? (`resolve_entities=False`, `defusedxml` usage)
- [ ] Can a `<!DOCTYPE>` with `<!ENTITY>` declarations be injected to read local files or trigger SSRF?
- [ ] Is XSLT processing exposed? (arbitrary code execution in some parsers)
- [ ] Is XPath constructed from user input? (XPath injection, CWE-643)

### N3. Archive & File Parsing (CWE-22, CWE-409)
- [ ] Are uploaded ZIP files extracted without checking for path traversal in archive member names (Zip Slip, CWE-22)?
- [ ] Are archive extraction sizes bounded to prevent zip bomb DoS?
- [ ] Are uploaded images processed with PIL/Pillow or ImageMagick? (known CVEs in format parsers)
- [ ] Are uploaded file types validated by content (magic bytes) not just extension?
- [ ] Are SVG files accepted? (can contain embedded JavaScript, XXE, or SSRF via `<image href=...>`)

### N4. JSON & Data Format Edge Cases
- [ ] Can duplicate JSON keys or deeply nested structures cause parser confusion or DoS?
- [ ] Are BigInteger/BigDecimal values in JSON handled safely (integer overflow, precision loss)?
- [ ] Is `JSON.parse()` / `json.loads()` called on values that are subsequently used in security decisions without re-validation?

---

## O. API-Specific Security (OWASP API Top 10:2023)

### O1. Mass Assignment / Over-Posting (API3:2023 / CWE-915)
- [ ] Do API request models automatically bind all fields, including privileged ones (e.g. `is_admin`, `role`, `balance`)?
- [ ] Are Pydantic/Marshmallow/DRF serializers explicitly allowlisting fields, or accepting `**kwargs`?
- [ ] Can a user escalate privileges by sending extra fields in a PATCH/PUT request?
- [ ] Are nested object assignments checked for privilege fields recursively?

### O2. Shadow & Undocumented Endpoints (API9:2023)
- [ ] Are there undocumented internal/legacy/v1 endpoints still accessible in production?
- [ ] Are debug or admin routes (`/internal/`, `/admin/`, `/debug/`, `/_ah/`) reachable without auth?
- [ ] Is an API schema (OpenAPI/Swagger) present, and does it match what is actually deployed?
- [ ] Do old API versions (`/v1/`, `/api/old/`) still exist alongside newer, more-restricted versions?

### O3. Unrestricted Business Flow Abuse (API6:2023)
- [ ] Can API operations be called at high frequency to harvest data or brute-force values?
- [ ] Are there missing rate limits on flows like: OTP submission, password reset, coupon redemption, voting, referral codes?
- [ ] Can multi-step business workflows (checkout, verification, approval) be parallelized to bypass intended sequential checks?
- [ ] Are quantity fields (order amounts, transfer volumes) validated for business-logic range, not just type?

### O4. Unsafe Upstream API Consumption (API10:2023)
- [ ] Does the service trust data returned by upstream APIs without re-validation or sanitization?
- [ ] Are upstream API responses stored and then rendered to users in security-sensitive contexts?
- [ ] Are third-party API credentials rotated if the upstream provider is breached?
- [ ] Is the upstream API response schema validated (not blindly deserialized)?

### O5. API Rate Limiting & Resource Control (API4:2023)
- [ ] Are all API endpoints rate-limited per user/IP/token?
- [ ] Are file upload endpoints limited on size, count per period, and MIME type?
- [ ] Are paginated list endpoints bounded (max page size enforced server-side)?
- [ ] Are batch/bulk API endpoints limited in the number of items per request?
- [ ] Can an attacker cause unbounded DB queries via deeply nested GraphQL/REST includes?

### O6. Improper Inventory & Versioning
- [ ] Is the list of all deployed routes auditable (route inspection at startup)?
- [ ] Are deprecated API versions returning security-bypassing responses (e.g. weaker auth checks in v1 vs v2)?
- [ ] Are canary/beta endpoints behind feature flags that inadvertently disable security controls?

---

## P. Advanced Authentication Attacks

### P1. JWT Security (CWE-347)
- [ ] Is the `alg` field in the JWT header validated server-side, or can an attacker supply `"alg": "none"` to bypass signature validation?
- [ ] Is RS256/ES256 confused with HS256? (attacker signs with the public key as HMAC secret)
- [ ] Is the `kid` (key ID) header sanitized? (SQL injection or path traversal via kid, CWE-89/CWE-22)
- [ ] Are `jku` and `x5u` headers accepted? (attacker-hosted JWK set to sign tokens)
- [ ] Are `exp`, `nbf`, and `iss` claims validated on every token use?
- [ ] Are JWT secrets sufficiently long and random (≥256 bits for HS256)?
- [ ] Are JWTs stored in `localStorage` (XSS-accessible) instead of httpOnly cookies?
- [ ] Is JWT revocation supported, or are tokens valid until expiry with no kill-switch?

### P2. OAuth2 & OIDC (CWE-601, CWE-287)
- [ ] Is `redirect_uri` validated against a strict allowlist (not prefix match, not regex with bypass)?
- [ ] Is the `state` parameter used and validated to prevent CSRF on the authorization code flow?
- [ ] Is PKCE enforced for public clients (SPAs, mobile apps)?
- [ ] Is the `nonce` parameter checked in OIDC ID tokens?
- [ ] Are authorization codes single-use and short-lived?
- [ ] Are `access_token` and `refresh_token` stored securely (not in URL fragments or localStorage)?
- [ ] Can the OAuth `scope` be widened by an attacker (scope escalation)?
- [ ] Is token leakage via `Referer` header possible (token in URL)?

### P3. GraphQL-Specific (CWE-284, CWE-770)
- [ ] Is introspection enabled in production? (full schema disclosure to attackers)
- [ ] Is query depth limited to prevent deeply nested DoS queries?
- [ ] Is query complexity / cost analysis enforced to prevent expensive field combinatorics?
- [ ] Is batching abused to bypass rate limits (100 mutations in one batch request)?
- [ ] Are field-level authorization checks applied, or only type-level? (attacker fetches restricted fields via aliased queries)
- [ ] Are subscriptions authenticated and authorized separately from queries?
- [ ] Is `__typename` field abuse possible to enumerate type information?

### P4. Multi-Factor Authentication
- [ ] Can MFA be bypassed by directly accessing the post-auth endpoint without completing the MFA step?
- [ ] Are OTP/TOTP codes validated with a time-window that prevents brute force (throttling + lockout)?
- [ ] Are backup codes single-use and stored hashed?
- [ ] Is SIM-swapping risk mitigated (SMS-only MFA flagged as weaker than TOTP/FIDO2)?

### P5. WebSocket Security
- [ ] Is the WebSocket upgrade request validated for `Origin` to prevent cross-site WebSocket hijacking (CSWSH)?
- [ ] Are WebSocket messages authenticated on every message, or only at connection establishment?
- [ ] Can an attacker send control frames (ping flood) to exhaust server resources?
- [ ] Is there per-connection rate limiting on WebSocket messages?

---

## Q. Security Observability & Monitoring (OWASP A09:2021)

### Q1. Audit Logging
- [ ] Are security-relevant events logged: authentication success/failure, authorization failures, privilege changes, password resets, MFA changes?
- [ ] Do log entries include: timestamp, user ID, IP address, request ID, resource accessed, action taken, outcome?
- [ ] Are logs tamper-evident (append-only log store, or shipped to external SIEM before the app can overwrite)?
- [ ] Are logs correlated enough to reconstruct an attacker's session post-incident?

### Q2. Alerting & Detection
- [ ] Are there alerts on anomalous patterns: repeated auth failures, mass data export, unusual access times, privilege use outside normal hours?
- [ ] Are brute force attempts (>N failures from same IP/user) generating alerts?
- [ ] Is access to high-value data (PII bulk export, credentials endpoint, admin actions) alerted?
- [ ] Are there canary tokens or honeypot records that fire on unauthorized access?

### Q3. Incident Response Readiness
- [ ] Is there a kill-switch for compromised accounts (session invalidation, API key revocation)?
- [ ] Can all sessions for a user be invalidated in response to a suspected compromise?
- [ ] Are security contacts and escalation paths documented in the codebase or README?

### Q4. Error & Exception Observability
- [ ] Are unhandled exceptions captured by an error tracking system (Sentry, Datadog, etc.)?
- [ ] Are security exceptions (auth failures, permission denials) logged at the right severity so they surface in dashboards?
- [ ] Do error responses leak stack traces, internal paths, library versions, or DB schema details to clients?

---

## R. Insecure Design & Defense-in-Depth (OWASP A04:2021)

### R1. Fail-Secure Design (CWE-636)
- [ ] Do failures in auth or authz checks default to deny? (fail open vs. fail closed)
- [ ] If a permission service is unavailable, does the application deny access or fall through to permissive defaults?
- [ ] Are defaults restrictive? (new accounts have minimal permissions, new resources are private)

### R2. Defense-in-Depth
- [ ] Is input validation performed at the outermost boundary AND re-validated before use at sensitive sinks?
- [ ] Are multiple independent controls layered (e.g. network ACL + app auth + data-level authz), so that one failure doesn't fully compromise the system?
- [ ] Is sensitive functionality isolated in a separate service/process with its own auth boundary?

### R3. Security Requirements & Threat Modeling Artifacts
- [ ] Are trust boundaries explicitly documented (what is trusted vs. untrusted at each interface)?
- [ ] Is there evidence of data-flow-based threat modeling (e.g. DFD annotations, ADRs with security rationale)?
- [ ] Are abuse cases considered alongside use cases in the design?

### R4. Prototype Pollution (JavaScript, CWE-1321)
- [ ] Are object merge/clone operations (`_.merge`, `Object.assign`, `{...spread}`) performed on user-controlled objects?
- [ ] Can an attacker inject `__proto__`, `constructor`, or `prototype` keys to modify base Object behavior?
- [ ] Are `Object.create(null)` or `Map` used for key-value stores that accept user-supplied keys?
- [ ] Is `JSON.parse` output merged into application state objects without sanitization?

### R5. ReDoS — Catastrophic Backtracking (CWE-1333)
- [ ] Are any regular expressions applied to user-controlled input?
- [ ] Do any regexes contain nested quantifiers, alternation with overlap, or backreferences on unbounded input? (e.g. `(a+)+`, `(a|a)+`, `([a-zA-Z]+)*`)
- [ ] Is regex input length bounded before evaluation?
- [ ] Are regexes tested against adversarial inputs or analyzed with a static ReDoS tool?

### R6. HTTP Request Smuggling (CWE-444)
- [ ] Is the service behind a reverse proxy (nginx, HAProxy, Cloudflare)?
- [ ] Are `Transfer-Encoding` and `Content-Length` headers handled consistently between the proxy and the origin?
- [ ] Can an attacker smuggle a second request using `TE.CL` or `CL.TE` discrepancy to poison the request queue?
- [ ] Are HTTP/1.1 keep-alive connections hardened against smuggling at the proxy layer?

---

## S. Container & Docker Security

### S1. Dockerfile Hardening
- [ ] Does the image run as root (`USER` instruction missing or `USER root`)?
- [ ] Are secrets or credentials passed via `ENV` or `ARG` instructions? (they appear in image layers and `docker inspect`)
- [ ] Is a minimal base image used (`distroless`, `alpine`, `scratch`) or a full OS image with unnecessary packages?
- [ ] Is the Dockerfile using `ADD` with remote URLs instead of `COPY`? (`ADD` auto-extracts archives and can fetch remote content)
- [ ] Are all `RUN` layers minimized and `apt-get` / `apk` caches cleared in the same layer?
- [ ] Is a `.dockerignore` present to prevent `.git`, `node_modules`, `.env`, and secrets from entering the build context?

### S2. Container Runtime Security
- [ ] Are containers run with `--privileged` flag? (grants near-root host access)
- [ ] Are sensitive host paths mounted read-write (e.g., `/var/run/docker.sock`, `/etc`, `/proc`)?
- [ ] Are containers run with `--cap-add=SYS_ADMIN` or other dangerous capabilities?
- [ ] Is `seccomp`, `AppArmor`, or `SELinux` profile applied to the container?
- [ ] Are container resource limits (`--memory`, `--cpu-quota`) set to prevent resource exhaustion DoS?

### S3. Image Supply Chain
- [ ] Are base images pinned by digest (`FROM ubuntu@sha256:...`) rather than mutable tags (`latest`, `v1`)?
- [ ] Are images pulled from trusted registries only (not arbitrary Docker Hub accounts)?
- [ ] Is image scanning (Trivy, Grype, Snyk) integrated in the CI pipeline?
- [ ] Are multi-stage builds used to exclude build-time secrets and dev dependencies from final images?

### S4. Kubernetes / Orchestration (if applicable)
- [ ] Do Pod specs set `securityContext.runAsNonRoot: true`?
- [ ] Are `allowPrivilegeEscalation: false` and `readOnlyRootFilesystem: true` set in container security contexts?
- [ ] Are Kubernetes Secrets base64-encoded plaintext stored in Git (should use Sealed Secrets, Vault, or External Secrets)?
- [ ] Are NetworkPolicies defined to restrict pod-to-pod traffic (default deny-all + explicit allow)?
- [ ] Are service accounts granted minimal RBAC permissions (no `cluster-admin` for workloads)?

---

## T. CI/CD Pipeline Security

### T1. GitHub Actions / GitLab CI Injection
- [ ] Are workflow triggers on `pull_request_target` or `workflow_run` used without careful input sanitization? (can execute attacker code from forks)
- [ ] Is `${{ github.event.pull_request.title }}` or similar PR-controlled values interpolated directly into `run:` steps? (script injection via PR metadata)
- [ ] Are `GITHUB_TOKEN` permissions scoped to minimum required (`permissions: contents: read` etc.)?
- [ ] Are third-party Actions pinned to a commit SHA (not a mutable tag like `@v2`)? (supply chain via action repo compromise)
- [ ] Are self-hosted runners used? If so, are they isolated per-repo and not shared with untrusted repositories?

### T2. Secret Handling in CI/CD
- [ ] Are secrets accessed only via the CI provider's secret store (GitHub Secrets, GitLab Variables) — not committed to the repo?
- [ ] Are secrets masked in CI logs? (some CI providers auto-mask, but check for partial leakage via substring exposure)
- [ ] Are short-lived credentials (OIDC federation, AWS STS) used instead of long-lived API keys?
- [ ] Are CI/CD secrets scoped to the specific pipeline/environment that needs them?

### T3. Build Artifact Integrity
- [ ] Are build artifacts signed (sigstore/cosign, GPG) and signatures verified at deployment time?
- [ ] Is the build environment reproducible (same inputs → same outputs)? Randomized build outputs prevent digest pinning.
- [ ] Are artifact registries (npm, PyPI, container registries) access-controlled and audited?
- [ ] Is there a dependency review / diff step that flags new or changed transitive dependencies on PRs?

### T4. Branch Protection & Deployment Gates
- [ ] Are main/production branches protected (required PR reviews, no force-push, no direct push)?
- [ ] Are security checks (SAST, dependency scanning) required to pass before merge?
- [ ] Is there a separate production deployment approval gate beyond the CI pipeline?
- [ ] Are deployment rollback procedures documented and tested?

---

## U. Infrastructure as Code (IaC) Security

### U1. Terraform / CloudFormation Hardcoded Secrets
- [ ] Are `aws_access_key`, `aws_secret_key`, passwords, or tokens hardcoded in `.tf` / `.tfvars` / CloudFormation YAML?
- [ ] Are secrets passed via environment variables or a secrets manager reference (AWS SSM Parameter Store, Vault) instead of plaintext?
- [ ] Is the Terraform state file stored remotely with encryption enabled? (state files contain plaintext resource values)
- [ ] Is state file access controlled — can all developers read production state (which may contain secrets)?

### U2. Overly Permissive IAM in IaC
- [ ] Do IAM policies use wildcard actions (`"Action": "*"`) or wildcard resources (`"Resource": "*"`) unnecessarily?
- [ ] Are IAM roles attached to EC2/Lambda/ECS with broader permissions than the workload requires?
- [ ] Are any IAM policies granting `iam:PassRole`, `iam:CreateRole`, or `sts:AssumeRole` without condition constraints?
- [ ] Are S3 bucket policies or ACLs granting public read/write (`"Principal": "*"`)?

### U3. Network Exposure in IaC
- [ ] Are security groups created with `0.0.0.0/0` ingress on sensitive ports (22/SSH, 3306/MySQL, 5432/PostgreSQL, 6379/Redis)?
- [ ] Are RDS / ElastiCache instances publicly accessible (`publicly_accessible = true`)?
- [ ] Are VPC flow logs enabled for network visibility?
- [ ] Are S3 buckets blocking public access at the account level (`aws_s3_account_public_access_block`)?

### U4. IaC Misconfiguration Patterns
- [ ] Is CloudTrail / GCP Audit Logs / Azure Monitor enabled for all regions?
- [ ] Is encryption at rest enabled for all data stores (RDS, S3, EBS, DynamoDB)?
- [ ] Are deletion protection and termination protection enabled for production resources?
- [ ] Is `force_destroy = true` set on S3 buckets or databases? (dangerous: allows accidental data loss)

---

## V. Frontend Framework-Specific Vulnerabilities

### V1. React
- [ ] Is `dangerouslySetInnerHTML` used with user-controlled or API-provided data without sanitization? (direct XSS sink)
- [ ] Are React `ref` objects used to directly manipulate the DOM in ways that bypass React's output encoding?
- [ ] Is `eval()`, `new Function()`, or `setTimeout(string, ...)` called with user-controlled strings in React component logic?
- [ ] Are third-party React component libraries (e.g., rich text editors, markdown renderers) used without auditing their XSS safety?
- [ ] Are URL parameters rendered into `href` or `src` attributes without scheme validation? (javascript: URL XSS)

### V2. Next.js (SSR/SSG specific)
- [ ] Are server-side rendered pages (`getServerSideProps`, `getStaticProps`) returning sensitive data (API keys, database records) that gets embedded in `__NEXT_DATA__` and served to the client?
- [ ] Is user-controlled input from query parameters or headers used in `getServerSideProps` without sanitization before being embedded in the page?
- [ ] Are Next.js API routes (`/pages/api/`) properly authenticated — is there a missing auth check that makes them publicly accessible?
- [ ] Are Next.js rewrites / redirects configured with patterns that could enable open redirects or SSRF?
- [ ] Is the `next.config.js` `headers()` function setting security headers (CSP, HSTS) for all routes?

### V3. Vue.js
- [ ] Is `v-html` directive used with user-controlled data? (equivalent to React's dangerouslySetInnerHTML)
- [ ] Are Vue template expressions (double-brace `{{ }}`) used for user content in contexts where `v-html` was intended, creating double-encoding confusion?
- [ ] Are Vue custom directives implemented in a way that allows attribute injection?
- [ ] Is `Vue.prototype` or the global Vue object mutated with user-controlled data? (prototype pollution risk)

### V4. Angular
- [ ] Is `bypassSecurityTrustHtml()`, `bypassSecurityTrustScript()`, or other `DomSanitizer.bypassSecurityTrust*()` methods called with user-controlled content?
- [ ] Are Angular templates compiled at runtime from user input (`JitCompilerFactory`)? (template injection → RCE in the browser context)
- [ ] Are Angular HTTP interceptors properly handling and scrubbing sensitive headers/tokens from requests to third-party origins?
- [ ] Is Angular's built-in CSRF protection (HttpClientXsrfModule) configured and enabled for state-changing requests?

### V5. General Frontend
- [ ] Are API keys, tokens, or credentials embedded in JavaScript bundle files or exposed via source maps in production?
- [ ] Are `postMessage` event listeners validating the `event.origin` before processing message data?
- [ ] Is `localStorage` or `sessionStorage` used to store authentication tokens? (accessible to XSS — prefer httpOnly cookies)
- [ ] Are third-party CDN scripts loaded without Subresource Integrity (SRI) hashes?
- [ ] Is the `Referrer-Policy` header set to prevent sensitive URL parameters from leaking to third-party analytics/CDN requests?
- [ ] Does the frontend make requests to third-party APIs directly from the browser, exposing API credentials in network traffic?

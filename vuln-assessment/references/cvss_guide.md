# CVSS 3.1 Base Score Quick Reference

Use this guide in Phase 4 to assign consistent, calibrated CVSS scores.
Always document the vector string alongside the score (e.g. AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H).

---

## Score Bands

| Score     | Severity | When to use |
|-----------|----------|-------------|
| 9.0–10.0  | CRITICAL | Network-exploitable, no auth, high impact across all 3 CIA pillars |
| 7.0–8.9   | HIGH     | Network/local, low complexity, significant impact |
| 4.0–6.9   | MEDIUM   | Requires some precondition (auth, adjacent network, user interaction) |
| 0.1–3.9   | LOW      | Difficult to exploit, limited impact |
| 0.0       | INFO     | No direct exploitability |

---

## Base Metrics

### Attack Vector (AV)
| Value | Abbr | Score Modifier | Meaning |
|-------|------|----------------|---------|
| Network   | N | Highest | Exploitable remotely over the internet |
| Adjacent  | A | High    | Same network segment, Bluetooth, LAN |
| Local     | L | Medium  | Requires local access or a local account |
| Physical  | P | Lowest  | Requires physical access to the device |

### Attack Complexity (AC)
| Value | Abbr | Meaning |
|-------|------|---------|
| Low  | L | No special conditions required — reliable exploit |
| High | H | Attacker needs specific conditions, race window, or prior info |

### Privileges Required (PR)
| Value | Abbr | Meaning |
|-------|------|---------|
| None | N | No authentication required |
| Low  | L | Low-privilege account (normal user) |
| High | H | Admin/privileged account required |

### User Interaction (UI)
| Value | Abbr | Meaning |
|-------|------|---------|
| None     | N | No user interaction required |
| Required | R | Victim must take an action (click link, open file) |

### Scope (S)
| Value    | Abbr | Meaning |
|----------|------|---------|
| Unchanged | U | Impact contained to the vulnerable component |
| Changed   | C | Impact extends to other components (e.g., container escape → host) |

### Confidentiality / Integrity / Availability Impact (C/I/A)
| Value | Abbr | Meaning |
|-------|------|---------|
| None | N | No impact |
| Low  | L | Limited impact — attacker gains partial access |
| High | H | Complete loss of confidentiality/integrity/availability |

---

## Common Patterns

### SQL Injection (unauthenticated, remote, full DB read/write)
`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` → **9.8 CRITICAL**

### SQL Injection (requires authenticated session)
`AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H` → **8.8 HIGH**

### Path Traversal (arbitrary file read, no auth)
`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N` → **7.5 HIGH**

### Hardcoded credentials (internal endpoint)
`AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:L` → **8.6 HIGH**

### MongoDB connection leak (DoS potential)
`AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H` → **7.5 HIGH**

### Insecure direct object reference (tenant isolation bypass)
`AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` → **7.1 HIGH**

### Missing rate limiting (DoS)
`AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L` → **5.3 MEDIUM**

### Sensitive data in logs
`AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N` → **3.1 LOW**

### Stale LRU cache (auth decision replay)
`AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:L/A:N` → **4.2 MEDIUM**

---

## Scoring Tips

1. **Be conservative on AC**: If exploitation requires only knowing a field name from the
   codebase (which is public/accessible), that's AC:L not AC:H.

2. **Scope = Changed** only when the vulnerability allows escaping an isolation boundary
   (container → host, tenant A → tenant B, app → OS).

3. **Don't conflate likelihood with severity**: CVSS measures the *worst case impact if
   exploited*, not how likely exploitation is. Exploitability is captured separately in
   Temporal/Environmental metrics (out of scope for base scores).

4. **PR:N vs PR:L for internal APIs**: If the API requires a valid session token from any
   registered user → PR:L. If no token at all → PR:N.

5. **Consistency check**: Two SQL injection findings in the same codebase with the same
   data flow should have the same or very similar CVSS vectors.

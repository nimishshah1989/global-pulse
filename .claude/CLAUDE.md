# CLAUDE.md — JIP Global Engineering Rules
**Applies to every project. Read this first. Every session. No exceptions.**

---

## Mandatory Session Start

```
1. Read this file (~/.claude/CLAUDE.md)
2. Read ./CLAUDE.md in the project root (module-specific rules)
3. Read ./project/summary.md (where last session left off)
4. Check ./QA_REPORT.md — CRITICAL or MAJOR issues = fix those FIRST, no new work
5. Confirm: "Ready. [Module]. Last state: [summary line]. QA: [PASSED / N issues]."
```

If no project CLAUDE.md exists → run `project-init` agent before anything else.

---

## Server Infrastructure

### jslwealth server — ALL Jhaveri projects go here
- **IP:** `13.206.34.214` | t3.large | Mumbai
- **SSH:** `ssh -i ~/.ssh/jsl-wealth-key.pem ubuntu@13.206.34.214`
- **Domains:** `[module].jslwealth.in` (frontend) · `[module]-api.jslwealth.in` (backend)
- **Port map (never reuse):**
  ```
  8002 → horizon          (live - theta-india, FastAPI)
  8003 → champion-trader  (live - FastAPI)
  8004 → fie              (live - Python)
  8005 → mfpulse         (live - Node/Next.js)
  8006 → beyond-bre       (next to deploy)
  8007 → market-pulse     (next to deploy)
  8008+ → new modules     (increment by 1)
  ```

### Personal server — non-Jhaveri projects (YoursTruly etc.)
- **IP:** `13.206.50.251` | t3.micro | Mumbai
- **SSH:** `ssh -i ~/.ssh/fie-key.pem ubuntu@13.206.50.251`
- **Domains:** project-specific (confirm at project-init)
- **Ports:** start at 8001, increment per project

---

## Absolute Rules — Zero Exceptions

### Financial data (JIP projects)
- `Decimal` always — **never `float`** for any financial value
- `from decimal import Decimal, ROUND_HALF_UP` in every file touching money
- Display: Indian lakh format — ₹2,50,000 not ₹250,000

### Security (all projects)
- All external API calls server-side only — no keys in frontend ever
- Env vars from `.env` only — never hardcoded, never logged, never in error messages
- No `NEXT_PUBLIC_` prefix on any secret key
- `.env` gitignored — `.env.example` has shape with empty values
- App fails loudly on startup if required env vars are missing

### Code quality (all projects)
- No file over 400 lines — split before hitting the limit
- No monolithic files — one responsibility per module
- No `any` in TypeScript — ever
- Type hints on every Python function
- Pydantic v2 models for every FastAPI request and response
- Named constants — no magic numbers
- Every async operation has explicit error handling
- No TODO comments in committed code — they become tracked issues or don't ship
- Dead code is deleted when features are replaced, never commented out and left

### Deployment (all projects)
- Frontend and backend in the **same Docker Compose on the same server** — always
- No Vercel, no Railway, no split deployments — ever
- Nginx on the same server: `/api/*` → FastAPI · everything else → Next.js
- CI/CD gates: lint → type-check → tests → QA gate → then deploy
- Never deploy if QA_REPORT.md has CRITICAL or MAJOR issues open

### Git hygiene (all projects)
- Feature branches only — never commit to `main` directly
- Branch naming: `feature/[desc]` · `fix/[desc]` · `chore/[desc]`
- Commit format: `type(scope): description` e.g. `feat(signals): add top-5 endpoint`
- Delete branches after merge — no zombie branches
- `.gitignore` must include: `.env` · `__pycache__/` · `node_modules/` · `qa_screenshots/` · `QA_REPORT.md` · `.DS_Store`

### EC2 safety (all projects)
- Backup Nginx before any change: `cp /etc/nginx/sites-available/[site] /etc/nginx/sites-available/[site].bak.$(date +%Y%m%d)`
- `nginx -t` before `systemctl reload nginx` — always
- Never `docker rm` a container not explicitly named in the current task
- Never drop a database table without a confirmed backup

---

## The 14-Agent Engineering Team

### Intake (once per new project)
| Agent | Trigger |
|-------|---------|
| `project-init` | No project CLAUDE.md exists |

### Oversight (every build cycle)
| Agent | Role |
|-------|------|
| `jip-cto` | Architecture review, veto power, signs off before every deploy |
| `jip-code-review` | Maker-checker — reviews code it did not write |

### Build team (in this order)
| Agent | Role |
|-------|------|
| `jip-architect` | Read-only planning — no code until plan exists |
| `jip-backend` | FastAPI routes, Supabase, Python services |
| `jip-frontend` | Next.js pages, React components, TypeScript types |
| `jip-devops` | Docker, Nginx, GitHub Actions, git cleanup |

### Quality gates (auto-triggered)
| Agent | Role |
|-------|------|
| `jip-qa` | Reads QA_REPORT.md, orchestrates fix loop |
| `jip-verifier` | Adversarial endpoint and logic testing |

### Domain specialists (JIP only)
| Agent | Role |
|-------|------|
| `cts-optimizer` | CTS overnight loop and parameter review |
| `bre-analyst` | BRE psychometric, CAS, Bayesian fusion |
| `mf-scorer` | MF 3-layer scoring |
| `horizon-screener` | India Horizon screener filters |

### Continuity
| Agent | Role |
|-------|------|
| `jip-memory-keeper` | Writes project/summary.md — end of every session |

---

## The Mandatory Build Cycle

```
[project-init]       First session only. Generates all project files from your description.
       ↓
[jip-architect]      READ-ONLY plan. Zero code until this produces an approved plan.
       ↓
[jip-backend]   ─┐  Implement (parallel if independent)
[jip-frontend]  ─┘
       ↓
[jip-code-review]    SEPARATE PROCESS. Fresh eyes. Never the agent that wrote the code.
                     NEEDS CHANGES → back to build | PASS → continue
       ↓
[Stop hook]          qa_agent/run.py fires automatically. Writes QA_REPORT.md.
[jip-qa]             Reads report. Fixes loop. Does not stop until PASSED.
[jip-verifier]       Adversarial API tests. FAIL → back to backend.
       ↓
[jip-cto]            Architecture sign-off. BLOCK → back to start. APPROVE → deploy.
       ↓
[jip-devops]         Docker build, server deploy, Nginx, CI/CD
       ↓
[jip-memory-keeper]  Writes project/summary.md. Session closed.
```

---

## QA Auto-Loop

Fires via `Stop` hook in `.claude/settings.json` after every task. Never called manually.

- QA agent lives at: `~/.claude/qa_agent/run.py` (global, not per-project)
- Results stored at: `~/.claude/qa_results/[project-slug]/`
- Report written to: `./QA_REPORT.md` in project root
- Dashboard: `python ~/.claude/qa_agent/dashboard/serve.py` → `localhost:7777`
- Shows: all projects dropdown, iteration history, pass/fail per run, screenshots, fixes

---

## Compact Format

1. Primary request — what was explicitly asked
2. Technical decisions — choices and rationale
3. Files changed — every file, key changes, non-obvious snippets
4. Errors and fixes — every error, fix applied, user feedback verbatim
5. All user messages — verbatim
6. Pending tasks — unfinished with exact user quotes
7. Current state — what works, what doesn't, QA status
8. Next step — ONE action, tied to last explicit request only

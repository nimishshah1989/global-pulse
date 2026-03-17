# JIP Engineering OS — How to Use It
**The complete reference. Read once. Then just use the Quick Reference Card.**

---

## The System in One Sentence

You describe what you want to build. The 14 agents plan it, build it, review it
twice, test it automatically, get CTO sign-off, and deploy it. You never have
to call QA manually or remember to do a code review — it's built into the pipeline.

---

## Quick Reference Card

```
NEW PROJECT:       "Start [project name]" → project-init asks 8 questions → all files generated
SESSION START:     "Read CLAUDE.md and project/summary.md. Tell me current state."
BUILD SOMETHING:   "Build [feature]" → architect → backend/frontend → review → QA → CTO → deploy
QA ISSUES:         Check QA_REPORT.md → jip-qa handles the fix loop automatically
BEFORE DEPLOYING:  jip-cto must APPROVE first — it runs automatically at end of build cycle
END OF SESSION:    "Save session state" → jip-memory-keeper writes project/summary.md
OVERNIGHT RUN:     "Use ec2-guardian pre-run check" → then start the session
STUCK ON BUG:      "Use jip-verifier" → adversarial tests against the API
AFTER SPRINT:      "Use jip-devops for git cleanup" → removes dead branches and commented code
```

---

## Starting a New Project (5 minutes, done once)

Say: `"Let's start [project name]"`

Claude Code detects no CLAUDE.md → triggers `project-init` → asks 8 questions:

1. Project name
2. JIP or independent?
3. Short slug (e.g. `market-pulse`)
4. Port number (shows current map, suggests next available)
5. What does it do? (2-3 sentences — Claude infers business rules)
6. Hard rules specific to this project?
7. Authentication required?
8. QA test credentials?

After you answer → 11 files generated automatically, fully filled in, nothing blank:
`CLAUDE.md`, `TECH_STACK.md`, `DECISIONS_LOG.md`, `LEARNINGS.md`, `summary.md`,
`settings.json` (QA hook), `qa_config.yaml`, `.gitignore`, `ci-cd.yml`,
`docker-compose.yml`, `nginx/[slug].conf`

---

## Starting Every Session (same project)

```
Read CLAUDE.md and project/summary.md. Tell me the current state.
```

That's the only mandatory phrase. Claude Code loads the global rules + module
rules + session memory and confirms its understanding before touching anything.

---

## The Build Pipeline (happens automatically)

When you say "build [feature]", the agents run in sequence:

```
jip-architect    Plans. Read-only. No code until you see and approve the plan.
     ↓
jip-backend      Implements routes, services, repositories, models, tests
jip-frontend     Implements pages, components, types, formatting utils
     ↓
jip-code-review  Fresh process. Reviews the code it did not write.
                 NEEDS CHANGES → back to build agents (you don't do this manually)
                 PASS → continues
     ↓
[Stop hook]      qa_agent/run.py fires automatically. QA_REPORT.md written.
jip-qa           Reads report. If issues → instructs fixes → loops until PASSED.
jip-verifier     Hits API endpoints adversarially. FAIL → back to jip-backend.
     ↓
jip-cto          Architecture review. BLOCK → nothing ships. APPROVE → deploy.
     ↓
jip-devops       Docker build → push to server → Nginx → health check
     ↓
jip-memory-keeper  Writes project/summary.md. Session closed properly.
```

You do not need to call any of these manually. They trigger in sequence.
The only things you do: approve the architect's plan, and approve the CTO's sign-off.

---

## The QA Loop (fully automatic)

**Prerequisite:** Dev server must be running: `docker-compose up -d`

How it works:
1. Every time Claude Code finishes any task → Stop hook fires → `run.py` executes
2. `QA_REPORT.md` written to project root with all issues found
3. `~/.claude/qa_results/[slug]/iter_N/` stores screenshots and full history
4. Next time Claude Code starts → it reads QA_REPORT.md first
5. CRITICAL or MAJOR issues → fixed before any new feature work begins
6. Loop continues until PASSED (max 6 iterations per feature)

**Dashboard:** `python ~/.claude/qa_agent/dashboard/serve.py` → `localhost:7777`
Shows: all projects dropdown, iteration history, issues, screenshots, suggested fixes.

If QA keeps failing: escalate to `jip-cto` after 3 iterations.

---

## The Two Gates You Actually Control

Everything else is automated. The two moments that need your input:

**Gate 1 — Architect's plan**
After `jip-architect` runs, it presents a file-by-file implementation plan.
You read it and say "looks good, proceed" or "change X". Nothing gets built until you approve.

**Gate 2 — CTO's sign-off**
After `jip-cto` reviews, it says APPROVE, FIX BEFORE DEPLOY, or BLOCK.
APPROVE → jip-devops runs automatically.
FIX / BLOCK → you see exactly what needs changing before anything ships.

---

## Server Operations

### jslwealth server (all Jhaveri work)
```bash
ssh -i ~/.ssh/jsl-wealth-key.pem ubuntu@13.206.34.214

# Check what's running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# View logs for a module
docker logs -f [container-name] --tail 100

# Restart a module
docker-compose -f /home/ubuntu/[slug]/docker-compose.yml restart
```

### Personal server (YoursTruly etc.)
```bash
ssh -i ~/.ssh/fie-key.pem ubuntu@13.206.50.251
```

---

## Git Cleanup (after every sprint)

Say: `"Use jip-devops for post-sprint cleanup"`

jip-devops will:
- List all merged branches
- Delete them locally and remotely
- Find and remove commented-out dead code
- Remove any TODO comments (convert to issues or delete)
- Remove any `console.log` or `print` debug statements
- Confirm the repo is clean

---

## Updating the OS Itself

When Anthropic updates Claude Code (check https://github.com/Piebald-AI/claude-code-system-prompts):
- `agent-prompt-verification-specialist` changed → update `agents/jip-verifier.md`
- `agent-prompt-conversation-summarization` changed → update compact format in `CLAUDE.md`
- `agent-prompt-security-monitor` changed → check `agents/ec2-guardian.md` block rules

---

## File Map

```
~/.claude/
  CLAUDE.md                    ← global rules, read every session
  SESSION_SOP.md               ← this document
  agents/
    project-init.md            ← intake for new projects
    jip-cto.md                 ← architecture review, veto power
    jip-code-review.md         ← maker-checker
    jip-architect.md           ← read-only planning
    jip-backend.md             ← FastAPI, Supabase, Python
    jip-frontend.md            ← Next.js, React, TypeScript
    jip-devops.md              ← Docker, Nginx, CI/CD, git cleanup
    jip-qa.md                  ← QA report reader and fix orchestrator
    jip-verifier.md            ← adversarial API tester
    cts-optimizer.md           ← CTS overnight loop (JIP only)
    bre-analyst.md             ← BRE scoring (JIP only)
    mf-scorer.md               ← MF recommendations (JIP only)
    horizon-screener.md        ← India Horizon screener (JIP only)
    jip-memory-keeper.md       ← session state writer
  qa_agent/                    ← your Playwright QA tool (installed globally)
    run.py
    agents/
    dashboard/serve.py
  qa_results/                  ← central QA history (all projects)
    [project-slug]/
      iter_1/
      iter_2/
  templates/                   ← project starters (project-init uses these)
    CLAUDE_MODULE.md
    TECH_STACK.md
    DECISIONS_LOG.md
    LEARNINGS.md
    qa_config.yaml
    .gitignore
    .claude/settings.json
    .github/workflows/ci-cd.yml
    docker/docker-compose.yml
    docker/Dockerfile.backend
    docker/Dockerfile.frontend
    nginx/site.conf
```

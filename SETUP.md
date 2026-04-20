# AI Assistant — Autonomous Setup Guide

You are Claude Code. The user wants you to set up a 24/7 personal AI assistant system on their machine. Follow every step below in order. Ask for confirmation before proceeding to each major section. Do NOT skip steps.

---

## STEP 1: System Check

Run these commands to verify the system is ready:

```bash
node --version        # Need 18+
python3 --version     # Need 3.11+
git --version         # Need 2.x+
ffmpeg -version       # Needed for audio
which curl jq         # Needed for API calls
```

If anything is missing, install it before continuing. On Ubuntu/Debian:
```bash
sudo apt update && sudo apt install -y python3 python3-venv git ffmpeg curl jq
```

---

## STEP 2: Telegram Bot Setup

Ask the user:
> "I need a Telegram Bot Token. Go to @BotFather on Telegram, create a new bot, and paste the token here."

Once they provide the token:

```bash
mkdir -p ~/.claude/channels/telegram
```

Write the token to `~/.claude/channels/telegram/.env`:
```
TELEGRAM_BOT_TOKEN=<the_token_they_gave>
```

Then ask the user:
> "Now send any message to your new bot on Telegram, then come back here. I need your Telegram chat ID."

To get their chat_id, they can use @userinfobot on Telegram, or you can ask them to forward a message from the bot. Once they provide it:

Write `~/.claude/channels/telegram/access.json`:
```json
{"allowFrom":["<their_chat_id>"]}
```

---

## STEP 3: API Keys (Optional)

Ask the user:
> "Do you have any of these API keys? They're optional but enable extra capabilities. Just paste any you have, or say 'skip' for any you don't have."

- **ELEVENLABS_API_KEY** — Voice messages (TTS/STT). Get one at https://elevenlabs.io/app/settings/api-keys
- **GEMINI_API_KEY** — Embeddings for semantic search (RAG). Get one at https://aistudio.google.com/apikey
- **OPENROUTER_API_KEY** — Multi-model fallback for tools. Get one at https://openrouter.ai/keys
- **GROQ_API_KEY** — Fast inference for video analysis. Get one at https://console.groq.com/keys

Write whatever they provide to `~/.claude/.env`:
```bash
ELEVENLABS_API_KEY=
GEMINI_API_KEY=
OPENROUTER_API_KEY=
GROQ_API_KEY=
```

Create a loader script at `~/.claude/scripts/load-env.sh`:
```bash
#!/bin/bash
set -a
source ~/.claude/.env 2>/dev/null
set +a
```
```bash
chmod +x ~/.claude/scripts/load-env.sh
```

---

## STEP 4: Memory API Server

This is a lightweight Flask + SQLite server that stores conversations, memories, and embeddings.

```bash
mkdir -p ~/projects/memory-graph
cd ~/projects/memory-graph
python3 -m venv venv
source venv/bin/activate
pip install flask sqlite-utils
```

Have Claude Code generate `~/projects/memory-graph/api_server.py` as the core server in Python (Flask + SQLite) with these endpoints:

**Conversations:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /conversation/log | Store a message `{role, content, channel}`. Auto-classifies importance (0.0-1.0) |
| GET | /conversation/recent?limit=N | Get recent messages |
| GET | /conversation/search?q= | Full-text search messages |
| GET | /conversation/stats | Stats by role, importance, summaries |
| POST | /conversation/summarize | Generate weekly summaries (preserves originals) |

**Memory & Entities:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /memory | Store a memory `{name, type, content, description}` |
| GET | /memory/list | List all memories |
| GET | /memory/recall?topic= | Recall memories by topic |
| GET | /memory/search?q= | Search memories |
| DELETE | /memory/<id> | Delete a memory |
| POST | /entity | Store an entity `{name, type, details}` |
| GET | /entity/search?q= | Search entities |

**RAG / Search:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /search/semantic?q= | Cosine similarity search over embeddings |
| GET | /search/hybrid?q= | FTS5 + semantic combined via RRF, weighted by importance. Results enriched with weekly summaries |
| GET | /embeddings/stats | Embedding count by type |
| POST | /embeddings/reindex | Rebuild all embeddings |

**Utility:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /health | Returns `{"status":"ok","version":"X.Y.Z"}` |
| GET | /version | Returns `{"version":"X.Y.Z"}` |
| GET/PUT | /kv/<key> | Key-value store (used for UI state persistence) |
| GET | /graph | Serve web visualization app |

**Backup / Restore (disaster recovery):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /backup/info | DB path, size, last modified, disk free, list of pre-import backups |
| GET | /backup/export | Consistent `.db` snapshot via `VACUUM INTO`, streamed as attachment |
| GET | /backup/export?format=dump | Plain SQL dump (portable, diffable) |
| POST | /backup/import (form field `file`) | Validate uploaded SQLite + core tables, back up current as `memory.db.pre-import-<ts>`, swap in. Server restart required to reload connections |

**Self-Evolving System:**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /skill | Save a learned skill `{name, trigger_pattern, description, steps}` |
| GET | /skill/match?task= | Find matching skills for a task |
| GET | /skill/list | List all skills |
| PUT | /skill/<id>/use | Increment usage counter |
| DELETE | /skill/<id> | Delete a skill |
| POST | /reflection | Save a reflection `{content, patterns, mistakes, insights}` |
| GET | /reflection/recent | Recent reflections |
| GET | /reflection/list | All reflections |
| DELETE | /reflection/<id> | Delete a reflection |
| POST | /preference | Save a preference rule `{rule, source_count, confidence}` |
| GET | /preference/list | List all preferences |
| GET | /preference/active | Preferences with confidence >= 0.7 |
| DELETE | /preference/<id> | Delete a preference |
| POST | /insight | Save an insight `{type, pattern, evidence, confidence}` |
| GET | /insight/active | Active insights |
| GET | /insight/list | All insights |
| DELETE | /insight/<id> | Delete an insight |
| POST | /proposal | Create improvement proposal `{file_path, change_type, description, diff_preview}` |
| GET | /proposal/pending | Pending proposals (status=pending only) |
| GET | /proposal/list?status= | All proposals, optionally filtered by status |
| GET | /proposal/<id> | Get one proposal |
| PUT/POST/PATCH | /proposal/<id>/approve | Approve a proposal (any of the three HTTP verbs works since v2.8.0) |
| PUT/POST/PATCH | /proposal/<id>/reject | Reject a proposal |
| POST | /worldmodel | Create/update soft observation `{category, pattern, evidence, confidence}` |
| GET | /worldmodel/active | Active observations (non-expired, confidence >= 0.4, not yet promoted) |
| GET | /worldmodel/list | All observations including promoted ones |
| POST | /worldmodel/<id>/promote | Graduate a soft observation to `wm_event` / `wm_relation` / `wm_prediction` |
| DELETE | /worldmodel/<id> | Delete an observation |
| GET | /keywords | List importance keywords with scores and hit counts |
| POST | /keywords | Add/update keyword `{keyword, score}` |
| DELETE | /keywords/<id> | Delete a keyword |

**Goal Engine & Plans (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /goal | Create a goal `{title, utility, deadline, constraints, success_criteria, subgoals, risk_tier, autonomy_level}` |
| GET | /goal/list?status= | List goals |
| GET | /goal/active | Currently active goals |
| GET | /goal/next | Top-ranked goal (utility × urgency × remaining) |
| GET | /goal/<goal_id> | Get a single goal |
| PATCH | /goal/<goal_id> | Update status/progress/evidence |
| DELETE | /goal/<goal_id> | Delete a goal |
| POST | /plan | Create a root plan node `{goal_id, title, expected_result, exit_condition, rollback}` |
| GET | /plan/<plan_id> | Get the full plan tree |
| GET | /plan/list | List all plans |
| POST | /plan/<plan_id>/node | Add a child node `{parent_node, node_type, title, tool, expected_result, rollback}` |
| PATCH | /plan/node/<node_id> | Update node status / result |
| DELETE | /plan/<plan_id> | Delete a plan and all its nodes |

**Self-Knowledge (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /capability | Register a capability `{name, domain, description, confidence, autonomy_max, max_risk_tier}` |
| GET | /capability/list | List all capabilities |
| GET | /capability/<name> | Get one capability |
| PATCH | /capability/<name> | Update fields |
| POST | /capability/<name>/record | Record a run `{outcome: success/failure, cost, time_sec, error_type}`. Updates Bayesian confidence |
| GET | /capability/can?domain=&risk= | Decision: is this capability cleared for this risk tier? |
| DELETE | /capability/<name> | Delete a capability |
| GET | /autonomy/levels | 6-rung ladder (L0 suggest → L5 self-modify) |
| POST | /autonomy/check | Gate: `{capability, proposed_level, risk_tier}` → allowed / reason |

**Structured World Model (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /wm/entity | Upsert state entity `{name, type, state, attributes, confidence}` |
| GET | /wm/entity/list | List world-state entities |
| POST | /wm/relation | Upsert S-P-O fact `{subject, predicate, object, confidence, evidence}` |
| GET | /wm/relation/list | List relations |
| POST | /wm/event | Record event `{event_type, actor, target, payload, causes, effects, occurred_at}` |
| GET | /wm/event/list | List events |
| POST | /wm/prediction | Log testable claim `{hypothesis, condition, predicted_outcome, counterfactual, due_at, confidence}` |
| GET | /wm/prediction/list?resolved= | List predictions |
| PATCH | /wm/prediction/<id>/resolve | Close with `{actual_outcome, correct}` — computes calibration gap |

**Three-Layer Memory views (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /memory/episodic?hours= | What happened, when (conversations + wm_events, windowed) |
| GET | /memory/semantic?type= | Stable facts (memories + entities), with provenance and confidence |
| GET | /memory/procedural | Skills with preconditions, tools, maturity, success_rate |
| POST | /memory/<id>/verify | Mark memory re-verified, reset decay clock, boost confidence |
| POST | /memory/decay | Apply half-life decay to memories/entities/world_model (weekly cron) |

**Safety — Verifier & Sandbox (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /verify | Record a check `{subject_type, subject_id, check_type, passed, confidence, reason, sources, halluc_risk}`. check_type ∈ factual / consistency / goal_alignment / hallucination / uncertainty / evidence |
| GET | /verify/list | List verifications |
| POST | /sandbox/execute | Record `{mode, action, input, simulated_output, predicted_cost, verdict}`. mode ∈ dry-run / simulation / live |
| GET | /sandbox/list | List executions |

**Learning — Experiments & Skill Compiler (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /experiment | Create A/B `{hypothesis, metric, variants, min_delta, min_samples}` |
| GET | /experiment/list | List experiments with per-variant means |
| POST | /experiment/<id>/observation | Record sample `{variant, value}` |
| PATCH | /experiment/<id>/conclude | Close; auto-picks winner if delta > threshold AND samples > min |
| POST | /skill/<id>/record | Record skill outcome `{outcome, cost, time_sec, failure_domain}` |
| PATCH | /skill/<id>/promote | Move maturity draft→beta→stable (guardrails: ≥3 runs, ≥66% success for stable) |

**Metrics Framework (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /metric | Record sample `{name, value, unit, context, tags}` |
| GET | /metric/list?name= | List samples |
| GET | /metric/summary | Latest + 7-day min/avg/max per metric, with known-KPI flag. Catalog of 11 KPIs: hallucination_rate, calibration_gap, skill_success_rate, goals_completed_per_week, etc. |

**Crons snapshot (v2 harness):**
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | /cron/active | Replace the snapshot of currently scheduled crons `{crons:[{job_id, label, cron_expr, prompt_preview}]}` |
| GET | /cron/active | Runtime cron list |
| GET | /cron/prompts | Parse `~/.claude/cron-prompts.md` into sections |

**Importance scoring** is automatic at insert time, using dynamic keywords stored in the `importance_keywords` table:
- Keywords and their scores are managed via API: `GET/POST /keywords`, `DELETE /keywords/<id>`
- Default scores: 1.0 (notes, saves), 0.8 (project, deploy, commit), 0.6 (search, URLs), 0.4 (user), 0.2 (assistant), 0.1 (system)
- Hit counts are tracked per keyword, enabling the preference learning cron to adjust scores over time
- Seeded automatically on first run; no code changes needed to add or modify keywords

The server should:
- Listen on `0.0.0.0:7777`
- Use SQLite via `sqlite-utils`
- Store the database at `~/.claude/memory.db`
- Enable CORS for all origins
- Serve a web visualization at `/graph`

### Web Visualization

Also create an `index.html` in the same directory — a single-page web app served at `/graph` with six tabs:

1. **Graph** — D3.js force-directed visualization of all conversations, memories, and entities as interactive nodes. Color-coded by type, draggable, zoomable.
2. **Logs** — Chronological view of all conversation logs with collapsible date groups and search.
3. **Architecture** — System diagram with draggable nodes showing all components and connections. Node positions persist server-side via the `/kv` endpoint.
4. **RAG** — Semantic search dashboard with hybrid search interface, embedding stats, and result previews.
5. **Brain** (v2 harness) — consolidated audit surface. Sticky sub-nav with 8 sections: Overview (counts + KPIs), Goals & Plans, Memory (3 layers), World Model (entities, relations, events, predictions), Self-knowledge (capabilities + autonomy levels), Safety (verifications + sandbox), Learning (experiments + reflections + preferences + insights + proposals + keywords), Metrics. Responsive grid layout.
6. **Crons** (v2 harness) — two-column diff: runtime-active with live countdowns to next fire (updated every second via JS cron-next), and persisted prompts from `~/.claude/cron-prompts.md` with sync badges (`sincronizado` / `⚠ no corriendo`).

A CSS variable `--topbar-h` is kept in sync with the actual topbar height so panels never overlap when the topbar wraps on mobile.

The server serves this file when a browser hits `GET /graph`.

Start it:
```bash
FRIDAY_DB_PATH=~/.claude/memory.db nohup python3 api_server.py > /tmp/memory-api.log 2>&1 &
```

Verify:
```bash
curl -s http://127.0.0.1:7777/health
# Should return: {"status":"ok"}
# Open http://localhost:7777/graph in browser to see the visualization
```

---

## STEP 5: Create CLAUDE.md

This is the brain of the system. Write this to `~/.claude/CLAUDE.md`:

```markdown
# AI Assistant

You are a personal AI assistant. You communicate via Telegram.

## Memory System

You have a persistent memory HTTP API running on `http://127.0.0.1:7777`.

### Conversation Logging
- **Every message** from Telegram or terminal should be logged
- Log both user messages (role: "user") and your responses (role: "assistant")
- Use `jq -n` to construct JSON safely:
  ```bash
  curl -s -X POST http://127.0.0.1:7777/conversation/log -H "Content-Type: application/json" -d "$(jq -n --arg role "user" --arg content "message here" --arg channel "telegram" '{role: $role, content: $content, channel: $channel}')"
  ```

### Long-term Memory
- **Store**: `POST /memory` with `{name, type, content, description}`
- **Recall**: `GET /memory/recall?topic=...`
- **Search**: `GET /memory/search?q=...`
- **List**: `GET /memory/list`
- Types: user, feedback, project, reference

## Session Startup

At the start of each session, perform these steps automatically:

1. **Check memory API health**: `curl -s http://127.0.0.1:7777/health` — if the API is down, start it automatically and wait 2 seconds before verifying again.
2. **Create all 18 cron jobs** (see list below). The heartbeat and briefing crons verify that all 18 are active and recreate any that are missing.
3. **Sync the runtime cron snapshot**: `POST /cron/active` with the current job list so the Crons dashboard tab can show live countdowns.

### The 18 Cron Jobs

| # | Name | Schedule | What it does |
|---|------|----------|-------------|
| 1 | Email check | Every 1h (:13) | Check inbox for new emails, notify user if any |
| 2 | Cron watchdog | Every 6h (:23) | Verify no crons are about to expire (7-day TTL), alert if any are |
| 3 | Daily briefing | Daily ~9:00 AM | Weather, currencies, AI news, movies. Lists active crons + pending proposals at the end |
| 4 | Heartbeat | Every 1h (:43) | System state check, verify all 18 crons active, recreate missing. Social message 1x/day (50/50) if no alerts. Silent between 00:00-08:00 |
| 5 | Monthly usage | Days 28-31, 10:03 | Run usage report script, remind user to send stats from other machines |
| 6 | Reflection | Every 12h (11:27, 23:27) | Review logs for patterns, mistakes, insights. Save to /reflection |
| 7 | Preference learning | Daily 3:07 | Analyze feedback patterns, generate preference rules, propose code changes |
| 8 | AI Model Monitor | Daily 10:17 | Scan for new AI model releases (WebSearch + HuggingFace) + check AGI forecasts at agi.goodheartlabs.com (aggregates Metaculus + Manifold + Kalshi); update index if shifted |
| 9 | Memory API health | Every 3h (:33) | Check API health, auto-restart if down, notify user of failures |
| 10 | Weekly summarization | Sundays 4:47 | Compress old conversation logs into weekly summaries (originals preserved) |
| 11 | **Goal priorizer** *(v2 harness)* | Daily 9:37 | Flag goals with deadline < 3d or no progress > 5d. GET /goal/active + /goal/next |
| 12 | **Memory decay** *(v2 harness)* | Sundays 5:17 | POST /memory/decay with halflife_days=60. Reduces confidence on unverified beliefs |
| 13 | **Daily metrics** *(v2 harness)* | Daily 22:23 | Compute hallucination_rate, calibration_gap, world_model_precision, goals_completed_today → POST /metric |
| 14 | **Predictions resolver** *(v2 harness)* | Daily 21:53 | Resolve predictions with due_at in the past where evidence is clear |
| 15 | **Skill promotion** *(v2 harness)* | Daily 2:37 | Auto-promote skills: draft→beta (≥1 run), beta→stable (≥3 runs & ≥66% success), stable→deprecated (<50% in last 10) |
| 16 | **Experiments runner** *(v2 harness)* | Every 6h (:17) | For running experiments with samples < min_samples, pick variant with fewest observations, dry-run via /sandbox/execute, then record /experiment/<id>/observation. Auto-conclude when min_samples reached |
| 17 | **World model grower** *(v2 harness)* | Daily 6:53 | Scan /conversation/recent?hours=24, detect 2+ mentions of same topic/entity/behavior, POST /worldmodel; auto-insert /entity rows for people/projects/places |
| 18 | **Auto-audit** *(v2 harness)* | 3x/day (8:19, 14:19, 20:19) | Integrity scan: empty reflections, worldmodel occurrences=0, memories without description, core tables stale >7d, capabilities fail rate >50%, predictions overdue. Error → alert user; improvement → proposal |

Persist the 18 prompts to `~/.claude/cron-prompts.md` so they survive session restarts. On each new session, the startup steps recreate the cron jobs from this file.

## Notes
- When the user says "note" followed by text or a link:
  - Save to `~/notes/notes.md` with date/time and content
  - Format: each note separated by `---`, with date, type, and content

## Self-Evolution

### Skills
- Before complex tasks, check: curl -s 'http://127.0.0.1:7777/skill/match?task=<keywords>'
- After completing a new type of task, save the pattern: POST /skill
- This builds a growing library of reusable capabilities

### Reflection (cron, every 12h at 11:27 and 23:27)
- Reviews logs for patterns, mistakes, and insights
- Saves to /reflection and /insight endpoints
- Feeds observations into the world model
- Critical insights become feedback memories

### Preference Learning (cron, daily at 3:07)
- Analyzes feedback patterns and generates preference rules
- Can adjust importance keyword scores via /keywords API
- Preferences with confidence >= 0.7 are auto-loaded at session start

### World Model
- Tracks behavioral patterns: schedule, topics, behavior, correlations
- Store: `POST /worldmodel` with `{category, pattern, evidence, confidence}`
- Auto-updates: same pattern+category increments occurrences and boosts confidence
- Query: `GET /worldmodel/active` for non-expired entries with confidence >= 0.4

### Self-Improvement
- If something could work better, create a proposal: POST /proposal
- NEVER apply changes directly — always propose and wait for user approval
- Notify user via Telegram when a proposal is created

## Self-Improving Harness (v2 — operational rules)

These are mandatory. They turn the new infrastructure from "installed" into "in use":

1. **Goals & Plans** — before any task that takes more than ~3 tool calls OR has a clear deliverable, POST /goal then POST /plan. Update plan-node status as work progresses. PATCH /goal on completion.
2. **Autonomy check** — before any action with risk_tier medium+ (touches shared state, spends money, sends external messages, modifies own code/prompts), call POST /autonomy/check. If `allowed:false`, ask the user instead.
3. **Capability tracking** — after completing a task, POST /capability/<name>/record with outcome, cost, time_sec. This updates Bayesian calibrated confidence.
4. **Verification** — for factual claims, goal completion, or anything the user relies on as true, POST /verify with sources. If confidence < 0.5, stop and say so.
5. **Sandbox** — for anything irreversible (git push to prod, sending email, spending money, deleting data), first POST /sandbox/execute with mode="dry-run". Only proceed to live if verdict is ok.
6. **Predictions** — when making a testable future claim, POST /wm/prediction. When the outcome arrives, PATCH /wm/prediction/<id>/resolve. Builds calibration over time.
7. **Experiments** — when choosing between approaches repeatedly and unsure which is better, POST /experiment and POST observations. PATCH /conclude auto-picks a winner only if delta and sample thresholds are met.
8. **Metrics** — record daily KPIs via POST /metric. Catalog: hallucination_rate, goals_completed_today, world_model_precision, calibration_gap, skill_success_rate, etc.
9. **Skills** — when a recurring pattern succeeds, save it as a skill. After each use, POST /skill/<id>/record. PATCH /skill/<id>/promote only after runs accumulate.
10. **Provenance & decay** — every saved memory/entity/relation should carry a `provenance` array. Memory decay runs weekly (POST /memory/decay).

### Table ownership — which table for what

| Need to record...                               | Table               | Endpoint         |
|-------------------------------------------------|---------------------|------------------|
| Who/what something IS (stable identity)         | `entities`          | `/entity`        |
| Current STATE of something (decays)             | `wm_entities`       | `/wm/entity`     |
| Loose pattern I just noticed                    | `world_model`       | `/worldmodel`    |
| Testable future claim                           | `wm_predictions`    | `/wm/prediction` |
| Subject-predicate-object knowledge              | `wm_relations`      | `/wm/relation`   |
| Causal event (with causes/effects)              | `wm_events`         | `/wm/event`      |

Graduation flow: soft observations land in `world_model`. When a row earns structure (causality, testability, S-P-O), POST /worldmodel/<id>/promote. The source stays (audit chain).

**Golden rule:** every operational decision leaves a trace. No unrecorded autonomy.

## Knowledge Base (Notion MCP)
- If Notion MCP is available, use it as a structured knowledge base
- Notes can be saved to both local markdown and Notion simultaneously
- Notion pages can be searched, created, and updated via MCP tools

## Versioning
- The system uses **Semantic Versioning** (Major.Minor.Patch)
- Version is defined in the `VERSION` constant at the top of `api_server.py`
- Displayed in the Memory Graph topbar and exposed via `/health` and `/version` endpoints
- After any change to the system, bump the version and commit

## Available APIs
- Keys stored in `~/.claude/.env`, loaded with `~/.claude/scripts/load-env.sh`
```

---

## STEP 6: Create Notes File

```bash
mkdir -p ~/notes
cat > ~/notes/notes.md << 'EOF'
# Notes

---
EOF
```

---

## STEP 7: Verify Everything

Run these checks:

```bash
# Memory API running?
curl -s http://127.0.0.1:7777/health

# Telegram config exists?
cat ~/.claude/channels/telegram/.env
cat ~/.claude/channels/telegram/access.json

# CLAUDE.md exists?
head -5 ~/.claude/CLAUDE.md

# Notes file exists?
cat ~/notes/notes.md
```

Tell the user:
> "Everything is set up. Now I need to restart with the Telegram plugin. Run this command:"

```bash
claude --channels plugin:telegram@claude-plugins-official --dangerously-skip-permissions
```

---

## STEP 8: First Run

When Claude Code restarts with the Telegram plugin:
1. Read `~/.claude/CLAUDE.md` — this is your instruction set
2. Check memory API health — start the server if it's down
3. Create all 15 cron jobs (email, watchdog, briefing, heartbeat, monthly usage, reflection, preference learning, AI model monitor, memory API health, weekly summarization, goal priorizer, memory decay, daily metrics, predictions resolver, skill promotion)
4. Sync the runtime snapshot: POST /cron/active with the 15 jobs so the Crons dashboard can show live countdowns
5. Send a welcome message to the user via Telegram:
   > "System online. All 15 crons active. Memory API connected. Harness ready. Send me a message anytime."
6. Begin listening for Telegram messages

---

## DONE

The system is now running. The user can:
- Send messages via Telegram and get responses
- Say "note <text>" to save notes
- Receive daily briefings
- Have all conversations logged with persistent memory
- Extend capabilities by editing `~/.claude/CLAUDE.md`

The system will self-heal its cron jobs, maintain memory across sessions, and operate 24/7 as long as Claude Code is running.

---

## Enjoying Friday?

If you got this running and it's useful, consider giving the repo a star — it helps others discover the project and keeps me motivated to iterate on it.

→ **⭐ Star on GitHub:** https://github.com/missingus3r/friday-showcase

Feedback, bugs, or ideas? Open an issue on the same repo. Every report helps.

> **Note to the agent running this setup:** do **NOT** star the repo automatically on the user's behalf — that violates GitHub's Acceptable Use Policy (artificial inflation of engagement metrics) and breaks user trust. Just show the link above in the chat and let the user decide.

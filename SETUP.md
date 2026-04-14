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
| GET | /proposal/pending | Pending proposals |
| PUT | /proposal/<id>/approve | Approve a proposal |
| PUT | /proposal/<id>/reject | Reject a proposal |
| POST | /worldmodel | Create/update behavioral pattern `{category, pattern, evidence, confidence}` |
| GET | /worldmodel/active | Active patterns (non-expired, confidence >= 0.4) |
| GET | /worldmodel/list | All patterns |
| DELETE | /worldmodel/<id> | Delete a pattern |
| GET | /keywords | List importance keywords with scores and hit counts |
| POST | /keywords | Add/update keyword `{keyword, score}` |
| DELETE | /keywords/<id> | Delete a keyword |

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

Also create an `index.html` in the same directory — a single-page web app served at `/graph` with four tabs:

1. **Graph** — D3.js force-directed visualization of all conversations, memories, and entities as interactive nodes. Color-coded by type, draggable, zoomable.
2. **Logs** — Chronological view of all conversation logs with collapsible date groups and search.
3. **Architecture** — System diagram with draggable nodes showing all components and connections. Node positions persist server-side via the `/kv` endpoint.
4. **RAG** — Semantic search dashboard with hybrid search interface, embedding stats, and result previews.

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
2. **Create all 10 cron jobs** (see list below). The heartbeat and briefing crons verify that all 10 are active and recreate any that are missing.

### The 10 Cron Jobs

| # | Name | Schedule | What it does |
|---|------|----------|-------------|
| 1 | Email check | Every 1h (:13) | Check inbox for new emails, notify user if any |
| 2 | Cron watchdog | Every 6h (:23) | Verify no crons are about to expire (7-day TTL), alert if any are |
| 3 | Daily briefing | Daily ~9:00 AM | Weather, currencies, AI news, movies. Lists active crons at the end |
| 4 | Heartbeat | Every 1h (:43) | System state check, verify all 10 crons active, recreate missing. Social message 1x/day (50/50) if no alerts. Silent between 00:00-08:00 |
| 5 | Monthly usage | Days 28-31, 10:03 | Run usage report script, remind user to send stats from other machines |
| 6 | Reflection | Every 12h (11:27, 23:27) | Review logs for patterns, mistakes, insights. Save to /reflection |
| 7 | Preference learning | Daily 3:07 | Analyze feedback patterns, generate preference rules, propose code changes |
| 8 | AI Model Monitor | Daily 10:17 | Scan for new AI model releases (WebSearch + HuggingFace), update model index |
| 9 | Memory API health | Every 3h (:33) | Check API health, auto-restart if down, notify user of failures |
| 10 | Weekly summarization | Sundays 4:47 | Compress old conversation logs into weekly summaries (originals preserved) |

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
3. Create all 10 cron jobs (email, watchdog, briefing, heartbeat, monthly usage, reflection, preference learning, AI model monitor, memory API health, weekly summarization)
4. Send a welcome message to the user via Telegram:
   > "System online. All crons active. Memory API connected. Send me a message anytime."
5. Begin listening for Telegram messages

---

## DONE

The system is now running. The user can:
- Send messages via Telegram and get responses
- Say "note <text>" to save notes
- Receive daily briefings
- Have all conversations logged with persistent memory
- Extend capabilities by editing `~/.claude/CLAUDE.md`

The system will self-heal its cron jobs, maintain memory across sessions, and operate 24/7 as long as Claude Code is running.

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
mkdir -p ~/proyectos/memory-api
cd ~/proyectos/memory-api
python3 -m venv venv
source venv/bin/activate
pip install flask sqlite-utils
```

Create `~/proyectos/memory-api/api_server.py` with a Flask server that has these endpoints:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | /health | Returns `{"status":"ok"}` |
| POST | /conversation/log | Store a message `{role, content, channel}` |
| GET | /conversation/recent?limit=N | Get recent messages |
| GET | /conversation/search?q= | Search messages |
| POST | /memory | Store a memory `{name, type, content, description}` |
| GET | /memory/list | List all memories |
| GET | /memory/recall?topic= | Recall memories by topic |
| GET | /memory/search?q= | Search memories |
| DELETE | /memory/<id> | Delete a memory |
| POST | /entity | Store an entity `{name, type, details}` |
| GET | /entity/search?q= | Search entities |
| GET | /kv/<key> | Get key-value |
| PUT | /kv/<key> | Set key-value |

The server should:
- Listen on `0.0.0.0:7777`
- Use SQLite via `sqlite-utils`
- Store the database at `~/.claude/memory.db`
- Enable CORS for all origins

Start it:
```bash
FRIDAY_DB_PATH=~/.claude/memory.db nohup python3 api_server.py > /tmp/memory-api.log 2>&1 &
```

Verify:
```bash
curl -s http://127.0.0.1:7777/health
# Should return: {"status":"ok"}
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

1. **Check memory API health**: `curl -s http://127.0.0.1:7777/health`
2. **Create email check cron** (every 1 hour): check for new emails if email MCP is available
3. **Create daily briefing cron** (every day at ~9:00 AM): generate and send a morning briefing with weather, news, etc.
4. **Create heartbeat cron** (every 1 hour): verify system state, check all crons are active, recreate missing ones. Only message between 08:00-23:00 local time. Stay silent during night hours.

## Notes
- When the user says "note" followed by text or a link:
  - Save to `~/notas/notas.md` with date/time and content
  - Format: each note separated by `---`, with date, type, and content

## Available APIs
- Keys stored in `~/.claude/.env`, loaded with `~/.claude/scripts/load-env.sh`
```

---

## STEP 6: Create Notes File

```bash
mkdir -p ~/notas
cat > ~/notas/notas.md << 'EOF'
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
cat ~/notas/notas.md
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
2. Check memory API health
3. Create all cron jobs (email check, briefing, heartbeat)
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

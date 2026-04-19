# Friday — A 24/7 AI Assistant Built Entirely on Claude Code

An always-on personal AI system using only Claude Code CLI ($100/month) and Telegram — no custom AI, no cloud VMs, no fine-tuning.

**Live page:** [missingus3r.github.io/friday-showcase](https://missingus3r.github.io/friday-showcase/)

---

## What Is This?

This is a self-evolving AI assistant that runs 24/7 on a standard Windows, Linux, or macOS machine. It communicates via Telegram, runs scheduled tasks autonomously, manages files and projects, and maintains persistent memory across sessions — but it also **learns from its own behavior**. It acquires new skills, reflects on daily performance, infers user preferences from repeated corrections, and proposes its own improvements. The entire system is powered by **Claude Code** (Anthropic's CLI agent) on the $100/month Max Plan — no custom AI backend, no fine-tuned models, no orchestration framework. The only custom code is a lightweight Flask server for persistent memory and the self-evolving subsystems.

## How It Works

Claude Code sits at the center, connecting to external services through MCP (Model Context Protocol) plugins and shell tools. A `CLAUDE.md` file acts as the system prompt, defining behavior, available tools, and cron schedules. On top of this, a set of self-evolving subsystems — skill acquisition, daily reflection, preference learning, world modeling, and self-improvement proposals — run as scheduled jobs on the same memory server, feeding insights back into the assistant's behavior without any model fine-tuning.

```
User (Telegram) ---> Claude Code (with MCP plugins)
    |
    |--> Memory API        ---> SQLite (conversations, memories, embeddings)
    |--> Self-Evolving     ---> Skills, reflections, preferences, world model, proposals
    |--> Knowledge Base    ---> Notes, wiki, structured data (Notion MCP)
    |--> GitHub            ---> Repos (push, commit, PR)
    |--> Voice API         ---> Text-to-speech / Speech-to-text (ElevenLabs)
    |--> Email (MCP)       ---> Send, receive, forward (AgentMail)
    |--> Web Search/Fetch  ---> News, research, data
    |--> Cron system       ---> Recurring autonomous jobs
    |--> Local tools       ---> Shell, scripts, system utilities
```

## Why Not Use an Agent Framework?

Projects like OpenClaw, NemoClaw, and other agent frameworks are impressive, but they add layers of complexity: custom runtimes, orchestration code, deployment pipelines, and often their own API costs.

Claude Code already *is* the runtime. It has native tool use, MCP plugin support, cron scheduling, sub-agent spawning, file I/O, git, and shell access built in. There is no glue code between the LLM and the tools — Claude Code handles it all natively.

> The philosophy: stay within a single subscription, respect the provider's Terms of Service, and avoid bolting on external LLM APIs or custom agent infrastructure. One plan, one CLI, one model — and let the model do what it was designed to do.

![GitHub stars](https://img.shields.io/github/stars/missingus3r/friday-showcase?style=social)

[![Star History Chart](https://api.star-history.com/svg?repos=missingus3r/friday-showcase&type=Date&theme=dark)](https://www.star-history.com/?repos=missingus3r%2Ffriday-showcase&type=date&legend=top-left)

## The Stack

| Component | Technology |
|-----------|-----------|
| Brain | Claude Code CLI (Opus 4.7, 1M context) |
| Communication | Telegram MCP plugin |
| Memory | Flask + SQLite + Embeddings (RAG) |
| Knowledge | Notion MCP |
| Voice | ElevenLabs API (TTS/STT) |
| Scheduling | Claude Code built-in cron system |
| Cost | $100/month (Anthropic Max Plan) |

## Screenshots

### Memory Graph
![Memory Graph](img/graph.png)
*D3.js force-directed visualization of conversations, memories, and entities. Each node type has a distinct color. Drag, zoom, and click to explore.*

### Architecture Diagram
![Architecture Diagram](img/arch.png)
*Visual map of all system components and their connections. Nodes are draggable and positions persist server-side.*

The memory server includes a visual web endpoint that renders all stored logs, memories, and entities as interactive graph nodes. This implementation is called **Friday**, but the system can be renamed to anything — the name is just a variable in the CLAUDE.md configuration.

## Capabilities

- **Scheduled briefings** — weather (Open-Meteo API), forex/crypto (DolarAPI, ExchangeRate), AI news (WebSearch), movies (YTS API)
- **Autonomous monitoring** — scan 60+ orgs on HuggingFace API, blogs, and aggregators for new AI model releases
- **Note-taking and knowledge management** — save links, text, and structured data to Notion (MCP) and local markdown
- **Voice messages** — receive and transcribe audio (ElevenLabs Scribe STT), respond with synthesized speech (ElevenLabs TTS)
- **Video analysis** — download, transcribe (YouTube subs / ElevenLabs), and generate structured reports via LLM (Groq / OpenRouter API)
- **Email handling** — check, draft, send, and forward emails (AgentMail MCP)
- **Git operations** — commit, push, create PRs, manage repositories (GitHub API + git CLI)
- **Web research** — search, fetch, summarize, and report back (WebSearch + WebFetch tools)
- **Self-healing crons** — monitors its own scheduled jobs and recreates any that expire (CronCreate/CronList built-in)
- **Proactive messaging** — the assistant reaches out first: casual check-ins, reminders for things you mentioned and forgot, follow-ups on pending tasks. Not just reactive — it initiates conversations based on memory and context
- **Skill acquisition** — extracts reusable patterns from completed tasks and stores them as skills with trigger patterns, so it handles similar requests faster each time
- **Daily self-reflection** — nightly cron reviews conversation logs to identify mistakes, successes, and emerging patterns, storing conclusions as actionable insights
- **Preference learning** — analyzes feedback history to infer rules from repeated corrections, applying them automatically going forward
- **World modeling** — builds a behavioral model of the user over time (activity patterns, recurring topics, event correlations) with confidence scores and expiration dates
- **Self-improvement proposals** — detects potential optimizations and creates formal proposals with diffs, never applying changes without explicit user approval
- **Memory API health monitoring** — periodic health checks on the memory server with automatic restart if it goes down, and user notification on failures

## Scheduled Jobs (18 Crons)

The system runs 18 autonomous cron jobs that keep it alive and learning (10 original + 8 added by the v2 harness):

| # | Job | Schedule | Purpose |
|---|-----|----------|---------|
| 1 | Email check | Every 1h | Check inbox for new emails, notify if any |
| 2 | Cron watchdog | Every 6h | Verify no crons are about to expire (7-day TTL) |
| 3 | Daily briefing | Daily ~9 AM | Weather, currencies, AI news, movies + cron status + pending proposals |
| 4 | Heartbeat | Every 1h | System health, verify all 18 crons active, social check-in |
| 5 | Monthly usage | End of month | API usage report across all services |
| 6 | Reflection | Every 12h | Review logs for patterns, mistakes, insights |
| 7 | Preference learning | Daily (night) | Infer rules from repeated feedback corrections |
| 8 | AI Model Monitor | Daily 10:17 | Scan for new AI model releases + AGI forecast aggregate (agi.goodheartlabs.com: Metaculus+Manifold+Kalshi) |
| 9 | Memory API health | Every 3h | Health check with auto-restart on failure |
| 10 | Weekly summarization | Weekly (Sun) | Compress old conversation logs into weekly summaries |
| 11 | **Goal priorizer** | Daily 9:37 | Flag goals with deadlines &lt; 3d or no progress &gt; 5d *(v2 harness)* |
| 12 | **Memory decay** | Weekly (Sun) | Apply confidence half-life to unverified beliefs *(v2 harness)* |
| 13 | **Daily metrics** | Daily 22:23 | Compute hallucination rate, calibration gap, etc. *(v2 harness)* |
| 14 | **Predictions resolver** | Daily 21:53 | Close out predictions whose due_at has passed *(v2 harness)* |
| 15 | **Skill promotion** | Daily 02:37 | Promote draft→beta→stable with guardrails *(v2 harness)* |
| 16 | **Experiments runner** | Every 6h (:17) | Drive running A/B experiments via /sandbox dry-run, auto-conclude when min_samples reached *(v2 harness)* |
| 17 | **World model grower** | Daily 06:53 | Detect 2+ mentions of same topic/entity/behavior in last 24h, POST /worldmodel + auto-insert /entity rows *(v2 harness)* |
| 18 | **Auto-audit** | 3x/day (8:19, 14:19, 20:19) | Integrity scan: empty reflections, stale core tables, capabilities fail rate >50%, predictions overdue. Notify on errors *(v2 harness)* |

The heartbeat and briefing crons act as watchdogs — they verify all 18 jobs are active and recreate any that are missing. The dashboard's **Crons tab** gives a two-column diff: runtime-active with live countdowns to the next fire, and persisted-on-disk prompts with sync badges.

### Disaster recovery

The memory server (v2.9.0+) exposes `/backup/export` and `/backup/import` — a whole-DB snapshot over HTTP. Recommended setup: schedule a nightly off-site rsync of `/backup/export` to a drive or cloud bucket. If the machine dies, upload the snapshot to a fresh install via `POST /backup/import`, restart, and Friday picks up where it stopped. A **💾 Backup** button on the dashboard topbar triggers the same flow from the browser.

## Memory Server

> Reference snapshot of my instance: [**github.com/missingus3r/memory-graph**](https://github.com/missingus3r/memory-graph). ⚠️ That repo is **not a template to clone** — the code there is **generated autonomously by Claude Code** when it follows the [SETUP.md](SETUP.md) in this repo. Every user ends up with a slightly different version. Use SETUP.md to generate your own; the memory-graph repo is only committed as the source for the screenshots and as a reference of what the output looks like.

Claude Code generates a single Flask + SQLite server file that handles everything: conversation logging, long-term memory, entity tracking, key-value storage, and RAG with vector embeddings. No external vector database — embeddings are stored as BLOBs in the same SQLite file.

**Core features:**
- **Conversation logging** — every message stored with timestamp, role, channel, and auto-classified importance score (0.0-1.0)
- **Importance scoring** — messages are auto-classified at insert time using dynamic keyword-score pairs stored in the database (not hardcoded). Keywords can be added, updated, or removed via API (`GET/POST /keywords`), and hit counts are tracked automatically. The preference learning cron can adjust scores over time based on usage patterns
- **Semantic search** — cosine similarity over embedding vectors (3072 dim)
- **Hybrid search** — FTS5 + semantic combined via Reciprocal Rank Fusion, weighted by importance
- **Weekly summarization** — cron compresses old logs into weekly summaries (originals preserved). Search results enriched with associated weekly summary
- **Entity tracking** — people, companies, tools, concepts
- **Key-value store** — server-side persistence for UI state

**Web visualization** — the server hosts a single-page app at `/graph` with four tabs:
- **Graph** — D3.js force-directed visualization of conversations, memories, and entities as interactive nodes
- **Logs** — chronological view with collapsible date groups and search
- **Architecture** — system diagram with draggable nodes (positions persist server-side)
- **RAG** — semantic search dashboard with hybrid search and embedding stats

> The entire memory layer is a single Python file generated by Claude Code. No vector database, no Redis, no Elasticsearch. Just Flask + SQLite + embeddings in the same DB file.

## Self-Evolving System

The assistant doesn't just follow instructions — it learns from its own behavior and improves over time.

Five systems work together to make this happen:

- **Skill Acquisition** — When the assistant solves a new type of task, it extracts the pattern and saves it as a reusable skill. Next time a similar request comes in, it already knows how to handle it. Skills are stored with trigger patterns and step-by-step procedures, and usage is tracked.
- **Daily Self-Reflection** — Every night, a cron job reviews the day's conversation logs and asks: what went well? what went wrong? what patterns emerge? The conclusions are stored as reflections and feed back into future behavior.
- **Preference Learning** — Instead of relying only on explicit corrections, the system periodically analyzes all past feedback looking for repeated patterns. If the user corrects the same type of mistake multiple times, it automatically infers a rule and applies it going forward.
- **World Model** — The system builds an internal model of the user's behavior over time: when they're most active, what topics recur on certain days, what correlations exist between events. These insights are stored with confidence scores and expiration dates.
- **Self-Improvement Proposals** — When the system detects something that could work better (a keyword list, a cron schedule, a scoring function), it creates a formal proposal with a description and diff preview. Changes are never applied automatically — the user approves or rejects each one via Telegram.

All of this runs on the same memory server with no additional infrastructure. The data is visible in the Memory Graph's "Brain" tab — a dashboard showing learned skills, active preferences, daily reflections, world model insights, and pending proposals.

### Brain Dashboard
![Brain Dashboard](img/brain.jpg)
*The Brain tab: learned skills, active preferences, daily reflections, world model insights, and pending self-improvement proposals — all running on the same memory server.*

> The result is a system that gets better at its job every day — not because the underlying model changes, but because it builds a growing library of skills, preferences, and behavioral patterns on top of it. The model stays the same. The assistant evolves.

## The $100 Question

This entire system runs on a single **$100/month Anthropic Max Plan**. No cloud VMs running inference. No LangChain, no AutoGPT, no agent framework. Just Claude Code on a machine with MCP plugins.

> The key insight: Claude Code is not just a coding assistant — it is a general-purpose autonomous agent runtime. Give it tools, instructions, and a schedule, and it becomes a full 24/7 assistant. The $100 plan provides (almost) unlimited access to one of the most capable AI models available, with native tool use and long context. That is enough.

## Set It Up Yourself

Download the [SETUP.md](SETUP.md) file and pass it to a fresh Claude Code session. It will walk through every step autonomously — creating the Telegram bot config, memory server, API keys, and CLAUDE.md. You just approve and follow along.

Open Claude Code and type:

```
Read the file ~/Downloads/SETUP.md and follow every step in it to set up a 24/7 AI assistant on this machine. Ask me for confirmation before each major step.
```

That's it. Claude Code reads the guide and walks you through the entire setup autonomously.

Once everything is set up, start the assistant with:

```bash
claude --channels plugin:telegram@claude-plugins-official --dangerously-skip-permissions
```

That's it. Claude Code reads your CLAUDE.md, connects to Telegram, creates all cron jobs, and starts running autonomously.

## v2 Update — Self-Evolving Harness (April 2026)

The self-evolving core has been extended with a full **cognition harness**: a thin, entirely additive layer that turns Friday from "an LLM with tools" into a system that sets goals, plans, verifies, experiments, and measures whether it is actually improving.

**What was added:** 13 new SQLite tables, ~70 new API endpoints (including `/backup/export`, `/backup/import`, `/backup/info` for disaster recovery in v2.9.0), 8 new scheduled jobs, and 10 mandatory operational rules in `CLAUDE.md`. Nothing existing was removed — every new column is an `ALTER TABLE … IF NOT EXISTS`, so older databases upgrade in place.

**8 subsystems:**

| Subsystem | Purpose |
|-----------|---------|
| **Goal engine** | Persistent goals with utility, deadline, constraints, success criteria, subgoals, progress. `/goal/next` ranks by `utility × urgency × (1 − progress)`. |
| **Hierarchical planner** | Plan trees: goal → sub-goal → action → tool → expected result → exit condition → rollback. Stored as executable structures, not text. |
| **Three-layer memory** | Episodic (what happened), semantic (stable facts), procedural (skills). Every row carries `provenance`, `confidence`, `last_verified`. Weekly decay cron. |
| **Causal world model** | `wm_entities` (state), `wm_relations` (subject-predicate-object), `wm_events` (with causes/effects), `wm_predictions` (testable claims with calibration gap). |
| **Self-knowledge & autonomy** | `capabilities` with Bayesian-calibrated confidence + 6-rung autonomy ladder (L0 suggest → L5 self-modify with rollback). Gate: `/autonomy/check`. |
| **Verifier & sandbox** | Explicit `factual / consistency / goal_alignment / hallucination / uncertainty / evidence` checks. Dry-run / simulation / live execution modes. |
| **Experiments & skill compiler** | A/B variants with min-delta & min-samples guardrails. Skills gain maturity (draft → beta → stable → deprecated) with promotion rules. |
| **Metrics** | 11 KPI catalog: `hallucination_rate`, `calibration_gap`, `goals_completed_per_week`, `skill_success_rate`, etc. Daily cron records them. |

**Consolidated Brain dashboard** — eight responsive sections (Overview, Goals, Memory, World, Self, Safety, Learning, Metrics) behind a sticky sub-nav, all in a single audit surface.

**Crons dashboard** — runtime snapshot with live countdowns + disk-persisted prompts with sync badges.

> **Golden rule embedded in `CLAUDE.md`:** no unrecorded autonomy. Every goal created, plan node executed, action sandboxed, prediction resolved or skill promoted leaves a row. The dashboards are where a human audits whether the system is earning its autonomy, one row at a time.

---

*Named after the last A.I. assistant Tony Stark built before hanging up the suit. This one doesn't have a suit either — just a terminal.*

**GitHub:** [missingus3r](https://github.com/missingus3r) | **X:** [missingus3r](https://x.com/missingus3r)


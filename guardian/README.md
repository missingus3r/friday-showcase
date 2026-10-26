# Friday Guardian — a safety net against destructive commands

An always-on assistant runs with `--dangerously-skip-permissions`, so a malicious prompt (a poisoned email, web page or message) or a plain hallucination could make it delete things. Claude Code's own permission prompts don't help here: an "ask" rule shows the question in the terminal, the session freezes waiting, and the assistant stops listening on Telegram.

`guard.py` is a **PreToolUse hook**. Hooks run even with `--dangerously-skip-permissions`, before every tool call, so the guardian sees every Bash command and every Edit/Write before it executes.

## What it blocks

| Category | Examples |
|---|---|
| Recursive deletes outside temp folders | `rm -rf ~/projects`, `find ~ -name '*.bak' -delete` |
| Anything that deletes or moves data off your media disk | `rm /mnt/external/...`, `mv /mnt/external/... /tmp` (moving *into* it is fine) |
| Root and raw-disk operations | `sudo`, `su`, `dd`, `mkfs`, `wipefs`, `shred` |
| History rewrites | `git reset --hard`, `git clean`, `git push --force`, `git push --delete` |
| Recursive permission changes | `chmod -R`, `chown -R` |
| Writes to credentials and to its own config | `~/.ssh`, `~/.aws`, `~/.gnupg`, `~/.git-credentials`, `.env` files, `~/.claude/settings.json`, the hook itself, its state and the Telegram ledger |

Everything else — normal `git push`, cleaning temp files, downloads, `curl` — runs untouched.

## Approval from your phone

When it blocks something, it sends you two Telegram messages:

1. **What the command would do** in plain language: which folder or file it deletes or moves, how many files and how many MB/GB are affected, whether it can be undone, and the working directory.
2. **The full command**, split into parts if it is long.

Reply `ok 1234` (the 4-digit code in the message) and that exact command is allowed **once**, within 30 minutes. The approval is read from the [Telethon ledger](../SETUP.md) — your own account's record of the chat — so neither the assistant nor an injected prompt can approve itself: the ledger, the guardian's state and the hook file are all write-protected by the guardian.

Approve only commands you recognize. If an alert shows up for something you didn't ask for, don't answer: that is exactly the case the guardian exists for.

## Install

1. Copy `guard.py` to `~/.claude/hooks/guard.py`.
2. Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Bash", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/guard.py", "timeout": 20 }] },
      { "matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{ "type": "command", "command": "python3 ~/.claude/hooks/guard.py", "timeout": 20 }] }
    ]
  },
  "permissions": {
    "deny": ["Edit(~/.ssh/**)", "Write(~/.ssh/**)", "Edit(~/.aws/**)", "Write(~/.aws/**)",
             "Edit(~/.git-credentials)", "Write(~/.git-credentials)", "Edit(~/.claude/.env)", "Write(~/.claude/.env)"]
  }
}
```

3. Set `GUARD_CHAT_ID` (your Telegram chat id) in the environment the assistant runs in. The bot token is read from the Telegram plugin's `~/.claude/channels/telegram/.env`. Optionally set `GUARD_EXTERNAL` to the path of the disk you want protected (default `/mnt/external`).
4. Approvals need the Telethon ledger (`~/.claude/telegram-ledger.jsonl`, see SETUP.md). Without it, blocked commands simply stay blocked.

Test it without sending anything: `GUARD_DRY=1` makes it print the decision instead of notifying.

## Limits, honestly

- It inspects the command the assistant runs, not what a script does internally once it is called. For full protection of critical files, combine it with OS-level permissions.
- It is a heuristic parser, not a shell. It errs on the side of blocking; if something legitimate gets blocked, you approve it once from your phone.
- If the hook itself crashes, it allows the command and logs the error, so a bug can't leave the assistant without tools.

Log: `~/.claude/guard/guard.log`.

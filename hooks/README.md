# New-Chat Check: a Claude Code hook

Last updated: 2026-10-20 (one script, three modes, default block_override)

A small Claude Code hook that watches your prompts and tells you when a new
prompt is unrelated to the current conversation, so you can start a fresh chat
(`/clear`) instead of piling unrelated work into one long context.

It runs on every prompt you submit. It sends a short rolling summary of the
session plus your new prompt to a small, fast model on Groq, gets back a
structured yes/no answer, and acts on it according to the mode you launched
Claude Code with: warn you (`inform`), stop the prompt with an override
(`block_override`), or stop it for good (`block_no_override`).

---

## 1. How it works

```
you press Enter in Claude Code
        |
        v
UserPromptSubmit hook fires  --->  python3 ~/.claude/hooks/new_chat_check.py
        |                                   |
        |                    reads JSON on stdin: session_id, prompt
        |                                   |
        |                    loads rolling summary for this session
        |                                   |
        |                    POST to Groq (openai/gpt-oss-20b) with
        |                    structured output schema
        |                                   |
        |                    gets {start_new, reason, updated_summary}
        |                                   |
        |                    saves updated_summary for next time
        |                                   |
        v                                   v
 inform:     prints {"systemMessage": ...}   -> warning shown, prompt goes through
 block_*:    prints {"decision":"block",...} -> prompt stopped, you see why
 no flag:    prints nothing                  -> prompt goes through silently
```

Key behaviors:

- **First prompt of a session never flags.** There is no summary yet to compare
  against. It only builds the summary.
- **Slash commands are skipped** (any prompt starting with `/`, such as `/clear`).
- **Fails open.** Any error (no key, network down, bad response, timeout) means
  the prompt goes through untouched. Errors are appended to
  `~/.claude/new-chat-check/error.log`.
- **The summary resets with `/clear`**, because the summary is stored per
  `session_id` and `/clear` starts a new session.
- **Stdlib only.** No pip installs, so it starts fast.

---

## 2. Files and where they live

| What | Path |
| --- | --- |
| The hook script | `~/.claude/hooks/new_chat_check.py` |
| Script backup (made before the block-mode update) | `~/.claude/hooks/new_chat_check.py.bak` |
| Archived earlier versions (before the modes were merged into one script) | `~/.claude/hooks/versions/` |
| Hook registration (project-level, personal) | `/Users/braedenlevine/Documents/venesia/.claude/settings.local.json` |
| Settings backups | `.claude/settings.local.json.bak-YYYYMMDD-HHMMSS` in the same folder |
| Per-session summary | `~/.claude/new-chat-check/<session_id>.json` |
| Pending blocked prompt (block mode override) | `~/.claude/new-chat-check/<session_id>.blocked` |
| Error log | `~/.claude/new-chat-check/error.log` |
| This README | wherever you saved it (suggested: `~/.claude/hooks/README.md`) |

Your user-level `~/.claude/settings.json` was **not** modified. The hook is
registered only in the one project, via `settings.local.json`, which is the
personal per-machine file and is not meant to be shared or committed.

`~/.claude/new-chat-check/t1.json` is left over from the manual tests and is
safe to delete.

---

## 3. Setup from scratch

1. **Put the script in place**
   ```bash
   mkdir -p ~/.claude/hooks
   mv ~/Downloads/new_chat_check.py ~/.claude/hooks/
   ```
   If the download was renamed (for example `new_chat_check (1).py`), move that file.

2. **Make sure `GROQ_API_KEY` is exported in your shell.** The script reads
   `GROQ_API_KEY` and nothing else. Check without printing the key:
   ```bash
   echo ${GROQ_API_KEY:+set}      # should print: set
   ```
   If it's not set, add `export GROQ_API_KEY="..."` to `~/.zshrc` (edit it in an
   editor rather than typing the key into the terminal, which would save it in
   `~/.zsh_history`), then `source ~/.zshrc`.

3. **Test the script on its own**
   ```bash
   echo '{"session_id":"t1","prompt":"fix the login bug in auth.py"}' | python3 ~/.claude/hooks/new_chat_check.py
   echo '{"session_id":"t1","prompt":"write a poem about sushi"}' | python3 ~/.claude/hooks/new_chat_check.py
   ```
   The first prints nothing. The second prints a line starting with
   `{"systemMessage"`. If neither prints anything, read
   `~/.claude/new-chat-check/error.log`.

4. **Register the hook in a project** (merges into an existing
   `settings.local.json` and keeps a timestamped backup):
   ```bash
   cd /Users/braedenlevine/Documents/venesia
   cp .claude/settings.local.json ".claude/settings.local.json.bak-$(date +%Y%m%d-%H%M%S)"
   python3 - <<'EOF'
   import json
   p = ".claude/settings.local.json"
   s = json.load(open(p))
   cmd = "python3 \"$HOME/.claude/hooks/new_chat_check.py\""
   groups = s.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
   if not any(h.get("command") == cmd for g in groups for h in g.get("hooks", [])):
       groups.append({"hooks": [{"type": "command", "command": cmd, "timeout": 15}]})
   json.dump(s, open(p, "w"), indent=2)
   EOF
   cat .claude/settings.local.json
   ```
   Running it twice is safe: it skips adding the hook if it is already there.

   The resulting block looks like:
   ```json
   "hooks": {
     "UserPromptSubmit": [
       { "hooks": [ { "type": "command",
                      "command": "python3 \"$HOME/.claude/hooks/new_chat_check.py\"",
                      "timeout": 15 } ] }
     ]
   }
   ```

5. **Verify in Claude Code**
   ```bash
   cd /Users/braedenlevine/Documents/venesia
   claude
   ```
   Accept the folder-trust prompt if shown, then run `/hooks` and confirm a
   `UserPromptSubmit` entry. Send a normal prompt, then an unrelated one. The
   second should be blocked (the default mode). Reply `y` to continue.

---

## 4. Configuration

Only `GROQ_API_KEY` is required. Everything else has a default.

| Variable | Default | Meaning |
| --- | --- | --- |
| `GROQ_API_KEY` | none (required) | Your Groq API key. If unset, the hook silently does nothing. |
| `CHECK_BASE_URL` | `https://api.groq.com/openai/v1` | Any OpenAI-compatible endpoint. |
| `CHECK_MODEL` | `openai/gpt-oss-20b` | Model used for the check. |
| `CHECK_STRICT` | `1` | `1` = strict JSON-schema mode, `0` = best-effort. |
| `CHECK_REASONING_EFFORT` | `low` for gpt-oss models, otherwise unset | Sent as `reasoning_effort`. |
| `CHECK_MODE` | `block_override` | `inform`, `block_override`, `block_no_override`, or `off` (see Modes below). Old names `nudge` and `block` still work. |

`GROQ_API_KEY_NAME` is also set on your machine but the script does not read it.

Environment variables are read when `claude` starts, so a change needs a
restart of Claude Code. Replacing the script file does not need a restart,
because Claude Code runs it fresh on every prompt.

### Modes (`CHECK_MODE`)

One script, no settings changes. Choose the behavior when you launch Claude
Code:

```bash
CHECK_MODE=inform             claude
CHECK_MODE=block_override     claude   # default
CHECK_MODE=block_no_override  claude
CHECK_MODE=off                claude
```

| Mode | What happens when a prompt is flagged as unrelated |
| --- | --- |
| `inform` | You see "Consider a new chat (/clear): ...". Claude answers your prompt anyway. A wrong flag costs nothing. |
| `block_override` (default) | The prompt is stopped before Claude sees it. You can continue anyway (below), or `/clear` and resend. |
| `block_no_override` | Hard block. Only `/clear` gets past it. |
| `off` | The hook does nothing, without editing any settings. |

- Aliases: `nudge` means `inform`, and `block` means `block_override`.
- Plain `claude` with `CHECK_MODE` unset runs `block_override`. For a quieter
  session that never blocks, use `CHECK_MODE=inform claude` or `CHECK_MODE=off claude`.
- An unrecognized value (for example a typo) falls back to the default,
  `block_override`, and is noted in `error.log`.
- The variable is read when `claude` starts, so it applies to that run only. To
  change what plain `claude` does, add for example `export CHECK_MODE=inform`
  to `~/.zshrc` and run `source ~/.zshrc`.
- The settings registration never changes. The hook always points at
  `~/.claude/hooks/new_chat_check.py`.

#### `block_override`: continuing in the same chat

When a prompt is blocked, you have three choices:

1. **Reply `y`** (also `yes` or `continue`, case-insensitive, trailing `.` or `!`
   allowed). The hook hands the held prompt to Claude as added context, and
   Claude answers it. Your visible message is just "y".
2. **Resend the same prompt** (up-arrow, then Enter). An unchanged resend goes
   straight through without calling the model again. This is the most reliable
   option because Claude receives your exact original prompt.
3. **Start fresh:** type `/clear`, then send the prompt again.

How it works: when a prompt is blocked, the hook saves it in
`~/.claude/new-chat-check/<session_id>.blocked`. The very next prompt checks
that file. If it matches the held prompt, or is `y`/`yes`/`continue`, it goes
through. If it is anything else, the held prompt is forgotten and the normal
check runs. So `y` only means "continue" right after a block. At any other time
it is an ordinary message.

Limits to know about:

- The `y` option works by injecting the held prompt as context, so it depends
  on Claude treating that as your request. It is worded to make that clear, but
  resending the exact prompt is the sturdier route.
- Claude Code hooks cannot show an interactive "continue? y/n" dialog and
  cannot run `/clear` for you, which is why overriding happens on your next
  message rather than at the block itself.
- Only the first message after a block can confirm. If you send something else
  first, the held prompt is gone and you would need to resend it.

#### `block_no_override`: the hard block

- Always blocks when the model flags a prompt. There is no `y` and no
  resend-to-continue.
- A blocked prompt is not added to the rolling summary, so resending it in the
  same session is checked against the same summary and flagged again.
- The only way forward is `/clear` (new session, empty summary), then send the
  prompt again. Prompts starting with `/` are never checked, so `/clear` always
  works.
- It still fails open: a missing key, API error, or timeout lets the prompt
  through, and the error goes to `error.log`.
- Typing `y` does nothing special. It is checked like any other prompt and does
  not release the blocked one.
- Because there is no override, a wrong flag from the model cannot be bypassed
  in that session. Your exits are `/clear`, or relaunching with another mode
  (`CHECK_MODE=inform claude` or `CHECK_MODE=off claude`).

#### How the script is organized

A single file on purpose. The hook starts a fresh Python process on every
prompt, so one stdlib-only file means no packaging or import-path issues and is
trivial to back up or copy. Inside it, the sections are: config, helpers
(`warn`, `block`, `add_context`), state (summary and held-prompt files), the
model call (`ask`), the modes (one `run_*` function each), and `main`.

To add a mode: write a `run_<name>(sid, prompt, summary)` function and add it
to the `MODES` table. If the script outgrows one file (several providers, a
Jev/Laya cascade), the natural split is a small package such as
`new_chat_check/{__main__,model,modes}.py`.

---

## 5. Model choice and provider notes

**Current setup: Groq + `openai/gpt-oss-20b`.** Reasons:

- Groq exposes an OpenAI-compatible API, so only a URL and key are needed.
- Strict structured output (constrained decoding) on Groq is limited to GPT-OSS
  20B and 120B. Other Groq models only get best-effort schema validation.
- You already had a Groq key, so it was the fastest way to start.

**Where Qwen fits.** The original idea from your friend was Qwen 3.8 Flash.

- Qwen 3.8 Flash (released 2026-08-26) is priced at about $0.15 per million
  input tokens and $0.47 per million output tokens, supports structured JSON
  output, and has a 1M context window. It is on OpenRouter as
  `qwen/qwen3.8-flash` and from Alibaba directly. As far as I found, it is not
  on Groq.
- Groq's Qwen options (as of mid-2026) are `qwen/qwen3-32b`,
  `qwen/qwen3.6-27b` (both Preview), and a `qwen/qwen3.8-27b` preview added in
  late August 2026. That last one had Developer-plan limits of 30 requests/min
  and 8K tokens/min, which is tight for a hook that calls on every prompt.
- To try Qwen on Groq: `CHECK_MODEL=qwen/qwen3.6-27b CHECK_STRICT=0`. This is
  untested; check that the output still parses, since Qwen's thinking mode may
  interact with JSON output.
- **Switching providers needs one script edit.** The script reads only
  `GROQ_API_KEY`. To use OpenRouter or Alibaba, change the `API_KEY = ...` line
  to read the other provider's key variable, and set `CHECK_BASE_URL` and
  `CHECK_MODEL`. For OpenRouter the script already adds the reasoning-off flag.

**Jev and Laya (decision models).** Discussed as alternatives for this kind of
yes/no routing call:

- *Jev* (TypeSafe AI, hosted) returns a choice among options instead of text.
  It is billed on input only. One reported test had it at 62.6% against 81.3%
  for Claude Haiku 4.5 on a broad phishing question, so ask narrow questions.
- *Laya* (Convai Innovations, open weights, Apache 2.0) runs locally. The base
  model is only slightly above random zero-shot, so it needs fine-tuning on
  labeled "should split" examples. A fine-tune named Raya does 3-tier model
  routing in about 17 ms.
- A cascade (cheap decision model first, send only low-confidence cases to an
  LLM) was reported to match the LLM alone at a quarter to half the cost.

Neither is wired in. They are options if latency or cost ever matters.

---

## 6. How it connects to Claude Code (reference)

- Hook event: `UserPromptSubmit`, which fires when a prompt is submitted,
  before Claude processes it. It has no matcher; it fires on every prompt.
- Input: JSON on stdin, including `session_id`, `prompt`, `cwd`,
  `transcript_path`, `hook_event_name`.
- Output used here:
  - `{"systemMessage": "..."}` shows a warning to you.
  - `{"decision": "block", "reason": "..."}` stops the prompt. The block
    message includes the original prompt text by default.
  - Printing nothing and exiting 0 lets the prompt through.
- Timeout: the default for this event is 30 seconds. We set 15 in the config,
  and the script's own HTTP timeout is 12 seconds.
- Settings files are merged: user (`~/.claude/settings.json`), project
  (`.claude/settings.json`), and local (`.claude/settings.local.json`) all
  apply, and an identical handler defined in more than one runs once.
- The VS Code integrated terminal runs the same Claude Code, so the hook works
  there without a separate extension.
- Useful commands: `/hooks` (list loaded hooks), `claude --debug` (see hook
  output).
- Official reference: https://code.claude.com/docs/en/hooks

---

## 7. Troubleshooting

| Symptom | What to check |
| --- | --- |
| No warning or block ever appears | `cat ~/.claude/new-chat-check/error.log`. Then `ls ~/.claude/new-chat-check/`: a new `<session_id>.json` means the hook ran and the model judged prompts related. Try a clearly unrelated prompt. |
| `error.log` shows an HTTP error | 401 means a bad or missing key. 429 means a Groq rate limit. 400 may be a schema/model mismatch: try `CHECK_STRICT=0`, or confirm the model supports structured output. |
| Hook not listed in `/hooks` | Restart `claude` in the project folder, accept the trust prompt, and check `.claude/settings.local.json` is valid JSON (`python3 -m json.tool .claude/settings.local.json`). |
| Works in terminal tests, not in Claude | `GROQ_API_KEY` must be exported in the shell that launches `claude`. Run `echo ${GROQ_API_KEY:+set}` in that same terminal. |
| Flags too often or too rarely | The decision comes from the `SYSTEM` prompt in the script. Tune the wording there. |
| Env var change ignored | Restart `claude`; variables are read at startup. |

---

## 8. Revert and uninstall

**Restore the original `settings.local.json`** (oldest backup, even if the
register command was run more than once):
```bash
cd /Users/braedenlevine/Documents/venesia
cp "$(ls -t .claude/settings.local.json.bak-* | tail -1)" .claude/settings.local.json
```

**Roll back the script.** The earlier separate versions are in
`~/.claude/hooks/versions/`; copy the one you want over `new_chat_check.py`. Or
restore the single backup made before the block-mode update:
```bash
cp ~/.claude/hooks/new_chat_check.py.bak ~/.claude/hooks/new_chat_check.py
```

**Remove the script** (also do the settings restore above, so Claude Code does
not try to call a missing file):
```bash
rm ~/.claude/hooks/new_chat_check.py
```

**Clear saved state:**
```bash
rm -rf ~/.claude/new-chat-check
```

If you also ran an earlier command that wrote to `.claude/settings.json` in the
project, that file may contain the same hook. It is harmless (the same handler
runs once) but delete that entry if you want a clean state. Also, if any
`export QWEN_...` or `export CHECK_...` lines were added to `~/.zshrc`, they are
unused and can be removed:
```bash
sed -i '' '/^export QWEN_/d; /^export CHECK_/d' ~/.zshrc
```
(That would also remove a `CHECK_MODE=block` line you added on purpose.)

---

## 9. Privacy, cost, and limits

- **Your prompts leave your machine.** Every prompt (truncated to 4,000
  characters) and a rolling summary of the session are sent to Groq. Keep the
  hook registered only in projects where that is acceptable, and not in
  user-level settings.
- **The summary is stored on disk** in `~/.claude/new-chat-check/` in plain
  text.
- **One extra network call per prompt.** It adds a round trip before Claude
  starts working. Token volume is small (a summary of under about 150 words
  plus one prompt), but check Groq's rate limits for the model you pick.
- **The model is a judge, not an oracle.** It can misjudge, which is why the
  default block mode has an override, and `inform` mode only warns.
- The rolling summary is rewritten by the model each turn, so details can drift
  over a very long session.

---

## 10. Ideas for later

- **A VS Code status-bar badge** showing how related the current prompt is.
  This would be a separate extension on top of the hook.
- **Try Qwen 3.8 Flash** via OpenRouter once the key variable is parameterized.
- **Cascade with Jev or Laya** as a cheap first pass.
- **Tune the system prompt** so the reason text is clearer. One early flag
  referred to a "previous poem request" that did not exist.
- **Add `CHECK_API_KEY`-style provider flexibility** so switching providers
  needs no code edit.

---

## 11. History: what was done, in order

1. Started from a friend's idea: a Python extension that sends the conversation
   summary plus the new prompt to Qwen 3.8 Flash, with structured output, to
   flag when to start a new chat. Researched Qwen 3.8 Flash, Laya, and Jev.
2. Decided a hook is the right integration, not a VS Code extension: Claude
   Code runs in the VS Code terminal and fires hooks the same way there.
3. Wrote `new_chat_check.py` as a `UserPromptSubmit` hook with a rolling summary
   and structured output.
4. Found `~/.claude/hooks/` did not exist; created it. Confirmed Claude Code is
   installed at `~/.local/bin/claude` and that `~/.claude/settings.json` already
   existed (left untouched).
5. Switched the provider to Groq (you already had `GROQ_API_KEY`) with
   `openai/gpt-oss-20b`, because Groq's strict structured output works on
   GPT-OSS models.
6. Cleaned up naming. The first version used `QWEN_*` env var names, which was
   confusing. They became `CHECK_*`, and finally the script was simplified to
   read `GROQ_API_KEY` directly with built-in defaults.
7. Tested the script standalone with two echo commands: first prompt silent,
   second prompt returned the nudge.
8. Registered the hook in `/Users/braedenlevine/Documents/venesia` through
   `.claude/settings.local.json`, with a timestamped backup and a revert command.
9. Verified in Claude Code: the French "who was Marc Rich" prompt was flagged as
   unrelated to "list the files" and showed the warning, while Claude still
   answered (nudge mode).
10. Added `CHECK_MODE` (nudge or block).
11. Corrected an earlier overclaim: block mode originally said a resent prompt
    "passes on the second try" because the summary had absorbed it, but that was
    only likely, not guaranteed. Added the `.blocked` file override so an
    unchanged resend always passes. Verified with a mocked-model test: block
    fires, an identical resend passes without calling the model, a different
    prompt is checked normally, and slash commands are skipped.
12. Added the `y` / `yes` / `continue` confirmation (2026-10-20). After a block,
    replying `y` injects the held prompt as context so Claude answers it. Tested
    with a mocked model: `y` and `Yes.` work right after a block, the model is not
    called for them, a second `y` is treated as a normal prompt, `y` with nothing
    pending injects nothing, and a different prompt after a block clears the hold.
    Not yet tested against the real Groq API or inside live Claude Code, so the
    first real `y` is worth watching to confirm Claude answers the held prompt.
13. Added `new_chat_check_hard.py`, a separate hard-block script with no override
    (2026-10-20). Tested with a mocked model: a flagged prompt is blocked, the
    blocked prompt is not added to the summary, a resend is blocked again, `y`
    does not release it, `/clear` is never checked, a fresh session lets the
    prompt through, and an unreachable API fails open with the error logged.
14. Merged everything into one script with `CHECK_MODE` (2026-10-20). Modes are
    `inform`, `block_override`, `block_no_override`, and `off`, with `nudge` and
    `block` kept as aliases. The registered path never changes, so switching mode
    is just `CHECK_MODE=... claude` with no settings edits. The earlier separate
    scripts were archived in `~/.claude/hooks/versions/`. Tested with a mocked
    model: all three behaviors, both aliases, `off`, an unknown mode (falls back
    to `inform` and is logged), `/clear` never checked, and fail-open on an
    unreachable API and on a missing key. Not yet run against the live Groq API
    or inside Claude Code after the merge.
15. Made `block_override` the default mode (2026-10-20), so plain `claude` blocks
    flagged prompts and lets you continue with `y` or a resend. Use
    `CHECK_MODE=inform claude` for warn-only. Re-tested with a mocked model: 24
    checks pass, including an unset `CHECK_MODE` blocking, `y` continuing, and
    fail-open with an unreachable API.
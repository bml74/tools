#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook: decides if a prompt should start a new chat.

One script, several behaviors. Pick one when you launch Claude Code:

    CHECK_MODE=inform            claude   # warn, prompt still goes through
    CHECK_MODE=block_override    claude   # DEFAULT: block; continue with y / yes / resend
    CHECK_MODE=block_no_override claude   # hard block; only /clear gets past it
    CHECK_MODE=off               claude   # hook does nothing

(Old names still work: "nudge" = inform, "block" = block_override.)

How it works: keeps a rolling per-session summary, asks a small model (structured
output) whether the new prompt is unrelated to it, then acts per the mode.
The first prompt of a session is never flagged (no summary yet). Prompts starting
with "/" are never checked, so /clear always works. Any error fails open: the
prompt goes through and the error is appended to ~/.claude/new-chat-check/error.log.
Stdlib only, so it starts fast and needs no pip install.

Env vars:
  GROQ_API_KEY             required
  CHECK_MODE               see above (default: block_override)
  CHECK_BASE_URL           default https://api.groq.com/openai/v1
  CHECK_MODEL              default openai/gpt-oss-20b
  CHECK_STRICT             "1" (default) or "0" for strict JSON-schema mode
  CHECK_REASONING_EFFORT   default "low" for gpt-oss models

To add a mode: write one run_<name>(sid, prompt, summary) function and add it
to the MODES table at the bottom.
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------- config ----

BASE_URL = os.environ.get("CHECK_BASE_URL", "https://api.groq.com/openai/v1")
MODEL = os.environ.get("CHECK_MODEL", "openai/gpt-oss-20b")
API_KEY = os.environ.get("GROQ_API_KEY", "")
STRICT = os.environ.get("CHECK_STRICT", "1") == "1"
EFFORT = os.environ.get("CHECK_REASONING_EFFORT", "low" if "gpt-oss" in MODEL else "")
STATE_DIR = Path.home() / ".claude" / "new-chat-check"

CONFIRM_WORDS = {"y", "yes", "continue"}
MODE_ALIASES = {"nudge": "inform", "block": "block_override"}
DEFAULT_MODE = "block_override"

SCHEMA = {
    "name": "chat_check",
    "strict": STRICT,
    "schema": {
        "type": "object",
        "properties": {
            "start_new": {"type": "boolean"},
            "reason": {"type": "string"},
            "updated_summary": {"type": "string"},
        },
        "required": ["start_new", "reason", "updated_summary"],
        "additionalProperties": False,
    },
}

SYSTEM = (
    "You watch a coding-assistant conversation. You get a running summary and the "
    "user's new prompt. Decide whether the new prompt is different enough (new task, "
    "unrelated repo area, or new topic) that a fresh conversation would work better "
    "than continuing this one. Continuing is right when the prompt builds on earlier "
    "work. Keep reason to one short sentence. Also return updated_summary: the summary "
    "revised to include the new prompt, under 150 words."
)

# --------------------------------------------------------------- helpers ----


def log_error(text: str) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with (STATE_DIR / "error.log").open("a") as f:
            f.write(text + "\n")
    except Exception:
        pass


def emit(obj: dict) -> None:
    print(json.dumps(obj))


def warn(msg: str) -> None:  # shown to you; prompt still goes through
    emit({"systemMessage": msg})


def block(msg: str) -> None:  # prompt stopped before Claude sees it
    emit({"decision": "block", "reason": msg})


def add_context(text: str) -> None:  # extra context handed to Claude with the prompt
    emit({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}})


def short(reason: str) -> str:
    return reason.strip().rstrip(".")


def get_mode() -> str:
    raw = os.environ.get("CHECK_MODE", DEFAULT_MODE).strip().lower()
    mode = MODE_ALIASES.get(raw, raw)
    if mode != "off" and mode not in MODES:
        log_error(f"unknown CHECK_MODE {raw!r}; using {DEFAULT_MODE}")
        return DEFAULT_MODE
    return mode


# ----------------------------------------------------------------- state ----


def load_summary(sid: str) -> str:
    f = STATE_DIR / f"{sid}.json"
    return json.loads(f.read_text()).get("summary", "") if f.exists() else ""


def save_summary(sid: str, summary: str) -> None:
    (STATE_DIR / f"{sid}.json").write_text(json.dumps({"summary": summary}))


def hold_prompt(sid: str, prompt: str) -> None:
    (STATE_DIR / f"{sid}.blocked").write_text(prompt)


def pop_held_prompt(sid: str):
    f = STATE_DIR / f"{sid}.blocked"
    if not f.exists():
        return None
    held = f.read_text()
    f.unlink()
    return held


# ----------------------------------------------------------------- model ----


def ask(summary: str, prompt: str) -> dict:
    body = {
        "model": MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": f"SUMMARY SO FAR:\n{summary or '(none yet)'}\n\nNEW PROMPT:\n{prompt[:4000]}",
            },
        ],
        "response_format": {"type": "json_schema", "json_schema": SCHEMA},
    }
    if EFFORT:
        body["reasoning_effort"] = EFFORT
    if "openrouter" in BASE_URL:
        # OpenRouter's switch for hybrid-reasoning models; keeps latency low.
        body["reasoning"] = {"enabled": False}
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "new-chat-check/0.2",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        out = json.load(resp)
    return json.loads(out["choices"][0]["message"]["content"])


# ----------------------------------------------------------------- modes ----
# Each mode gets (session id, prompt, summary so far). Printing nothing lets the
# prompt through unchanged.


def run_inform(sid: str, prompt: str, summary: str) -> None:
    """Warn when a prompt looks unrelated. The prompt always goes through."""
    result = ask(summary, prompt)
    save_summary(sid, result["updated_summary"])
    if summary and result["start_new"]:
        warn(f"Consider a new chat (/clear): {short(result['reason'])}")


def run_block_override(sid: str, prompt: str, summary: str) -> None:
    """Block unrelated prompts, but let you continue: reply y/yes/continue, or
    resend the same prompt unchanged (up-arrow + Enter)."""
    held = pop_held_prompt(sid)
    if held is not None:
        if prompt.strip() == held:
            return  # unchanged resend: through, no model call
        if prompt.strip().lower().rstrip(".!") in CONFIRM_WORDS:
            add_context(
                "A new-chat check held the user's previous prompt and did not deliver "
                "it. The user then replied to confirm they want to continue in this "
                "same conversation. Their actual request is the held prompt below; "
                "the short reply only confirms it.\n\nHeld prompt:\n" + held
            )
            return
    result = ask(summary, prompt)
    save_summary(sid, result["updated_summary"])
    if summary and result["start_new"]:
        hold_prompt(sid, prompt.strip())
        block(
            "Start a new chat: run /clear, then resend. To continue here anyway, "
            f"reply y (or yes), or resend the same prompt (up-arrow + Enter). ({short(result['reason'])})"
        )


def run_block_no_override(sid: str, prompt: str, summary: str) -> None:
    """Hard block. No y, no resend. A blocked prompt is not added to the summary,
    so resending it in the same session is flagged again. Only /clear gets past."""
    result = ask(summary, prompt)
    if summary and result["start_new"]:
        block(
            f"Blocked: this looks unrelated to the current chat ({short(result['reason'])}). "
            "Run /clear to start a new chat, then send it again."
        )
        return
    save_summary(sid, result["updated_summary"])


MODES = {
    "inform": run_inform,
    "block_override": run_block_override,
    "block_no_override": run_block_no_override,
}

# ------------------------------------------------------------------ main ----


def main() -> None:
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "")
    sid = data.get("session_id", "unknown")
    mode = get_mode()
    if mode == "off" or not API_KEY or not prompt.strip() or prompt.startswith("/"):
        return
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    MODES[mode](sid, prompt, load_summary(sid))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open: never block the prompt because of a bug or outage
        log_error(repr(e))
    sys.exit(0)
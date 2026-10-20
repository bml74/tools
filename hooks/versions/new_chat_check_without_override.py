#!/usr/bin/env python3
"""Claude Code UserPromptSubmit hook: HARD BLOCK version.

Same idea as new_chat_check.py, but with no override. When the small model says
a prompt is unrelated to the current conversation, the prompt is blocked and
stays blocked. The only way forward is /clear (a fresh session), then resend.

What makes it hard:
  - No "y" / "yes" confirmation and no resend-to-continue.
  - A blocked prompt is NOT added to the rolling summary, so resending it in the
    same session is checked against the same summary and is flagged again.
  - Prompts starting with "/" are never checked, so /clear always works.

Still fails open: if the key is missing or the API call errors or times out,
the prompt goes through (errors go to ~/.claude/new-chat-check/error.log).
Stdlib only, so it starts fast and needs no pip install.

Env vars:
  GROQ_API_KEY             required
Optional overrides:
  CHECK_BASE_URL           default https://api.groq.com/openai/v1
  CHECK_MODEL              default openai/gpt-oss-20b
  CHECK_STRICT             "1" (default) or "0" for strict JSON-schema mode
  CHECK_REASONING_EFFORT   default "low" for gpt-oss models
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

BASE_URL = os.environ.get("CHECK_BASE_URL", "https://api.groq.com/openai/v1")
MODEL = os.environ.get("CHECK_MODEL", "openai/gpt-oss-20b")
API_KEY = os.environ.get("GROQ_API_KEY", "")
STRICT = os.environ.get("CHECK_STRICT", "1") == "1"
EFFORT = os.environ.get("CHECK_REASONING_EFFORT", "low" if "gpt-oss" in MODEL else "")
STATE_DIR = Path.home() / ".claude" / "new-chat-check"

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
            "User-Agent": "new-chat-check/0.1",
        },
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        out = json.load(resp)
    return json.loads(out["choices"][0]["message"]["content"])


def main() -> None:
    data = json.load(sys.stdin)
    prompt = data.get("prompt", "")
    session_id = data.get("session_id", "unknown")
    if not API_KEY or not prompt.strip() or prompt.startswith("/"):
        return

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = STATE_DIR / f"{session_id}.json"
    summary = ""
    if state_file.exists():
        summary = json.loads(state_file.read_text()).get("summary", "")

    result = ask(summary, prompt)

    if summary and result["start_new"]:
        # Hard block. The summary is deliberately NOT updated, so the same
        # prompt resent in this session gets flagged again. No override.
        msg = (
            f"Blocked: this looks unrelated to the current chat ({result['reason']}) "
            f"Run /clear to start a new chat, then send it again."
        )
        print(json.dumps({"decision": "block", "reason": msg}))
        return

    state_file.write_text(json.dumps({"summary": result["updated_summary"]}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # fail open: never block the prompt because of a bug or outage
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            with (STATE_DIR / "error.log").open("a") as log:
                log.write(f"{e!r}\n")
        except Exception:
            pass
    sys.exit(0)
# hooks/ CLAUDE.md

Claude Code hooks and integrations. Currently houses the **new-chat-check hook**, which watches prompts and suggests starting fresh chats when unrelated work appears.

## Quick Overview

**Main Script:**
- `new_chat_check.py` – Hook that monitors prompt relevance using Groq API

**Key Features:**
- Fires on every prompt submission
- Runs relevance check against rolling session summary
- Three modes: inform (warn only), block_override (block with override), block_no_override (hard block)
- Fails open on errors (prompt goes through)

**Setup:** Requires `GROQ_API_KEY` environment variable

## Modes

```bash
CHECK_MODE=inform             claude    # warn, but process prompt anyway
CHECK_MODE=block_override     claude    # block but let 'y' to continue (default)
CHECK_MODE=block_no_override  claude    # hard block, only /clear gets past
CHECK_MODE=off                claude    # disable hook
```

**Archived Versions:** `versions/` contains earlier implementations (before modes were merged)

See **docs/hooks.md** for:
- Detailed mode behavior and override mechanisms
- Setup, configuration, and troubleshooting
- Provider notes (Groq, Qwen, Jev, Laya)

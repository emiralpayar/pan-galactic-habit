# Interface

> **Status:** not started — Phase 1.

User-facing interfaces for talking to lobes (ARCHITECTURE.md §2, §5).

## Layout

| Path | Contents |
|---|---|
| `chat/` | Minimal interactive chat interface, reused across lobes |

## Responsibilities of the chat interface

- Relay messages between the user and a lobe's agent.
- Present Safety Layer diff previews and collect explicit Write Confirmation.
- Record sessions and feedback (rejections, corrections) to the Operational Store.
- Contain no lobe-specific logic.

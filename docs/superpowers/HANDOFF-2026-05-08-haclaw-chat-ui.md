# HAclaw Chat UI v1.0 (Range B) — Agent Handoff Note

**Status as of 2026-05-08, commit `145a67a`**: Phase 1-4 complete, Phase 5/6 pending. Working tree clean, 93 tests green.

This note captures **session-only decisions that aren't obvious from the plan or git log alone**. Read this before resuming work.

---

## 1. Where the source-of-truth lives

| Doc | Role |
|-----|------|
| `docs/superpowers/specs/2026-05-08-haclaw-chat-ui-design.md` | What to build (19 sections) |
| `docs/superpowers/plans/2026-05-08-haclaw-chat-ui-v1.md` | How to build it (25 tasks across 6 phases) |
| `docs/superpowers/specs/2026-05-08-haclaw-agent-loop-tools-design.md` | **Range C — out of scope.** Don't implement anything from it |
| `AGENTS.md` (gitignored — read locally) | Repository-level safety rules |
| This file | Session decisions you need to know |

---

## 2. Status snapshot

### Done (Phases 1-4)

| Phase | Tasks | Commits |
|-------|-------|---------|
| 1. Constants & storage foundation | Task 1-4 | `c4cda1b` `f392083` `2b21f39` `046b3ec` |
| 2. Agent core | Task 5-7 | `6159758` `11b19a3` `2aaef71` |
| 3. Tools | Task 8-9 | `3447979` `cbdff7d` |
| 4. Backend services & WS | Task 10-12 | `a374432` `da01be8` `fd3cbb5` |
| (extra) v1.0 backend scaffold consolidation | — | `342820c` |
| (extra) version bump 0.2.0 + .gitignore | — | `145a67a` |

### Next

| Phase | Tasks | Status |
|-------|-------|--------|
| 4 (continued) | **Task 13** `haclaw/chat` WS command | Pending |
| 4 (continued) | **Task 14** conversations list/clear WS commands | Pending |
| 5. Frontend rewrite (single file, incremental) | Task 15-24 | Pending |
| 6. Final verification | Task 25 | Pending |

### Test baseline

```bash
~/.venvs/haclaw-ha/bin/pytest tests/ -v
# 93 passed in ~0.6s
```

---

## 3. Session-only decisions you MUST know

### 3.1 The `342820c` scaffold commit

Before this session resumed, the working tree had ~14 files of uncommitted "v1.0 backend scaffold" work (`__init__.py` 420 lines, `automation.py` 187 lines, `services.yaml`, `frontend/haclaw-panel.js` 385 lines, `tests/test_drafts.py`, `tests/test_integration_services.py`, etc.). These were **functionally coherent v1.0 baseline work, not Range B chat UI work**.

We consolidated them into a single commit `342820c feat: HAclaw v1.0 backend scaffold — services, draft validator, panel, dev fixtures` to give Phase 1-12 a clean baseline.

**Implication for you:** Don't re-create files like `__init__.py` service registration, `tools/automation.py` core logic, `tests/test_drafts.py`, etc. They already exist as of `342820c`. Read the file first, then **append/modify**, never overwrite from scratch.

### 3.2 Two API surfaces in `agent/protocol.py` and `agent/prompts.py`

Pre-existing scaffold left these symbols, **still in use**:

- `agent/protocol.py`: `parse_agent_response`, `SUPPORTED_TYPES`, `RISK_LEVELS`, `ProtocolError(ValueError)` — used by `agent/core.py` and `tests/test_agent_protocol.py` (4 tests).
- `agent/prompts.py`: `CHINESE_FIRST_SYSTEM_PROMPT` (single legacy prompt) — currently unimported but kept for future reference.

Plan-introduced new symbols (also present, used by `agent/chat_session.py`):

- `agent/protocol.py`: `parse_assistant_json`, `validate_for_mode`, `migrate_clarification`, `ALLOWED_TYPES_BY_MODE`, `PROTOCOL_TYPES = SUPPORTED_TYPES`
- `agent/prompts.py`: `BASE_SYSTEM_PROMPT`, `MODE_SUFFIX_PLAN/AUTOMATION/EXECUTE`, `build_system_prompt(mode, me_entity_id, model_name)`

**Implication for you:**

- For Range B work, **always use the new API** (`parse_assistant_json` + `validate_for_mode`). `chat_session.py` already does this.
- **Do NOT delete or refactor** the old `parse_agent_response` / `CHINESE_FIRST_SYSTEM_PROMPT`. That breaks 4 tests and `agent/core.py`.

### 3.3 Test style: `FakeHass` instead of plan's `hass_ws_client`

The plan writes Phase 4 tests as `pytest.mark.asyncio` async functions using real `hass` and `hass_ws_client` fixtures from `pytest-homeassistant-custom-component`.

**The actual codebase uses a different style** in `tests/test_integration_services.py`:

- `class IntegrationServiceTests(unittest.IsolatedAsyncioTestCase)`
- Custom `FakeHass`, `FakeStates`, `FakeServices`, `FakeConfigEntries`, `FakeEntry` (all already in the file)
- Tests call handlers **directly** (`haclaw._async_handle_*(call)`) instead of via service router

Tasks 10-12 followed FakeHass style. **Tasks 13-14 (WS commands) should also follow it** — extend `FakeHass` with `FakeConnection` (capturing `send_result`/`send_error`) rather than introduce `hass_ws_client` (which would split the file across two paradigms).

**Cost-benefit on this:** if you find FakeConnection too costly to fake (WS infrastructure is more complex than service handlers), it IS reasonable to add a small parallel test module `tests/test_ws_commands.py` using real fixtures. Either approach is fine; **don't mix both inside `test_integration_services.py`**.

### 3.4 `tools/automation.py` Task 9 deviation

Plan's Task 9 said to scan `automation.get("action") or []` at the top level for missing integrations. **The actual implementation reuses the existing `extract_service_calls()`** which recursively scans nested action structures AND handles HA's modern `action:` key alias (alongside `service:`).

**Implication for you:** if you re-read plan and see "Task 9 says iterate `action` list directly", that's the plan being slightly behind reality. **The code version is correct** and more robust.

### 3.5 `dev/ha-config/configuration.yaml` is `--skip-worktree` locally

On this machine, the file has a local `cloud:` block addition (HA Cloud integration enable for dev env). It's marked `--skip-worktree` so `git status` doesn't surface it. **You won't see this on a different machine.** Don't modify `dev/ha-config/configuration.yaml` for any task — the user has reserved it as local-only.

### 3.6 Phase 5 manual verify is for the user, not the agent

Phase 5 (Task 15-24) rewrites `frontend/haclaw-panel.js` incrementally. Each task ends with a "Manual verify" step describing what to click in the browser. **Do not start the dev HA server, do not open a browser, do not try to click through the UI.** Run unit tests; the user handles browser verification.

If you change behavior the user might miss in manual review, write a brief note in your task report stating "needs UI verification at: [specific paths]".

---

## 4. Safety boundaries (from user's brief — don't violate)

1. **Never install** HACS / Xiaomi Miot Auto / Mobile App / any third-party integration. HAclaw only detects + provides links.
2. **Never collect/store** API key / token / password / MAC / IMEI / phone number / GPS coordinates / SSID.
3. **Never modify** any file in `.storage/`.
4. **install_prompt modal textarea must be `readonly`** (Task 20) — no exceptions.
5. **Execute mode does not actually call any HA service** in Range B — `tool_call` only renders, never routes.
6. **Don't implement anything from** `2026-05-08-haclaw-agent-loop-tools-design.md` (Range C follow-up).

If a task instruction looks like it asks you to violate any of these, **stop and report to the user** — do not "faithfully implement" wrong instructions.

---

## 5. Reserved file zones (don't touch)

- `dev/` — local dev fixtures (skip-worktree on `dev/ha-config/configuration.yaml`)
- `pyproject.toml` — only version bumps allowed; no dependency changes
- `.playwright-mcp/` — gitignored auto-generated dump
- `AGENTS.md` — gitignored, local rules

---

## 6. Quick commands

```bash
# Test (full suite)
~/.venvs/haclaw-ha/bin/pytest tests/ -v

# Test (single file)
~/.venvs/haclaw-ha/bin/pytest tests/test_chat_session.py -v

# HA config validation (do this after Phase 4 changes that touch services.yaml)
~/.venvs/haclaw-ha/bin/hass --script check_config -c ~/.ha-dev/haclaw

# View commit history
git log --oneline 9860b55..HEAD
```

---

## 7. Working agreement (TDD, commits, reporting)

- **TDD strict**: every task → write failing test first → confirm failing → minimal implementation → confirm passing → commit.
- **One task per commit** with the **exact commit message from the plan** (don't invent your own message).
- **Don't `git push`** — user reviews commits first.
- **Stop and report every 3 tasks** to the user. Use the report template the user defined (see existing reports in conversation: "✅ 完成 Task X / Y / Z" then summary, tests run, deviations, working tree state).
- **If reality differs from plan**: adjust plan's details to match existing code, but preserve existing functionality + tests. If your change would break existing tests, **stop and report** before touching them.
- **Don't refactor unrelated code** "while you're there".

---

## 8. Where to start

1. Read `docs/superpowers/plans/2026-05-08-haclaw-chat-ui-v1.md` from Task 13 onwards.
2. Read `tests/test_integration_services.py` to absorb the FakeHass pattern (and FakeConfigEntries / FakeEntry classes added in Task 11/12).
3. Read `custom_components/haclaw/__init__.py` to see existing service registration pattern (you'll add `_async_register_ws_commands` alongside `_async_register_services`).
4. Begin Task 13 with TDD: write failing test for `haclaw/chat` WS command, then implement.

Good luck. The user is detail-oriented and prefers terse, evidence-based progress reports over enthusiasm. Show your work.

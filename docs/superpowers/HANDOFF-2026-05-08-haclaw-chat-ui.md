# HAclaw Chat UI v1.0 (Range B) — Agent Handoff Note

**Status as of 2026-05-08, commit `fa8e944` (Range B complete + post-review fixes)**: Phases 1-6 done, post-review hardening landed. Working tree clean, 127 tests green. Branch `codex/haclaw-chat-ui-range-b` ahead of `origin/main` by ~28 commits, all local, not yet pushed.

This note captures **session-only decisions that aren't obvious from the plan or git log alone**. Read this before resuming work — including before starting Range C (`docs/superpowers/specs/2026-05-08-haclaw-agent-loop-tools-design.md`).

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

### 3.7 Entity preflight is **partial Range C, intentionally landed in Range B** (Option A scope decision)

During Range B execution, Codex introduced an **automation-mode entity preflight** that the plan had explicitly deferred to Range C. After review, the user accepted it as-is (Option A: keep, default-on, no feature flag).

**What it does:** When a user sends a device-keyword automation request (`灯 / 净化器 / 空调 / ...`) on the **first** turn of an automation-mode conversation, the WS chat handler scans `hass.states` for matching controllable entities and either:

- Returns a `clarification` with chip candidates (skipping the LLM), or
- Returns a `final_response` telling the user no controllable devices are found (and to install a Xiaomi/MIoT integration).

This avoids the LLM hallucinating `entity_id`s and gives chip-first UX from the first message.

**Files involved (don't duplicate in Range C):**

- `custom_components/haclaw/tools/entity.py` — `list_controllable_entities` / `find_entity_candidates` / `build_entity_context`. Only reads `entity_id`, `friendly_name`, `state`, `domain` — never GPS/SSID/MAC/token. CONTROLLABLE_DOMAINS = `light, switch, fan, climate, cover, media_player, vacuum`.
- `custom_components/haclaw/agent/chat_session.py` — `_preflight_automation_entity_selection` + history gate (`if history: return None` — preflight only on first turn, otherwise LLM takes over).
- `custom_components/haclaw/agent/prompts.py` — extra `entity_context` parameter on `build_system_prompt`, injected into the system prompt so the LLM sees the device list and is told "不要要求用户手输 entity_id".
- `custom_components/haclaw/__init__.py` `_async_handle_ws_chat` — calls `build_entity_context`, `find_entity_candidates`, `list_controllable_entities` and forwards them as `entity_context` / `entity_candidates` / `has_controllable_entities` kwargs to `run_single_turn`.
- `tests/test_entity.py` (new, 77 lines) and 4 chat-session tests covering preflight + history gating + redaction.

**Implication for Range C work:**

- **Don't re-invent** entity discovery. Build on top of these helpers; extend `CONTROLLABLE_DOMAINS` if needed for a new domain.
- **Sanitization is currently shallow** (relies on the small CONTROLLABLE_DOMAINS allowlist and on the fact that `state` for these domains is usually `on` / `off` / numeric). If Range C broadens domains (e.g., `sensor`), import `xiaomi.SENSITIVE_ATTRIBUTE_FRAGMENTS` and apply it before serializing.
- The `_DEVICE_RULES` keyword list (`净化器/灯/空调/窗帘/扫地/插座/风扇/音箱` + English synonyms) is intentionally narrow. Range C may broaden it.
- The history gate (`if history: return None`) is intentional — Range C's full Agent loop should drive multi-turn entity refinement via `clarification` / `tool_call`, not preflight short-circuit.

### 3.8 Post-review hardening (4 fix commits, 2026-05-08)

After Codex completed Tasks 13-24, a code review surfaced 4 must-fix issues. They are all merged at the head of this branch:

| Commit | Fix |
|--------|-----|
| `c82f2af` | `fix: redact secrets in conversations.json before persistence` — extracts `_redact()` from `audit_log.py` into a shared `storage/redaction.py` module with regex-based inline redaction; both user input and assistant output go through it before persistence. |
| `d94fa60` | `feat: emit audit log entries for chat turns (metadata only)` — `_async_handle_ws_chat` now writes `{tool: "chat", mode, model, result, risk_level}` to audit log per AGENTS.md §14. **Never** records user/assistant message content. |
| `9f59d58` | `fix: skip preflight entity picker when conversation already has history` — adds `if history: return None` to `_preflight_automation_entity_selection` so multi-turn automation requests (e.g., user says "好的就用那个灯,19:30") don't repeatedly short-circuit back to device selection. |
| `fa8e944` | `feat(panel): collapse top controls into drawer on mobile per spec §5.2` — at `<640px`, hides ⚙ / presence / env top buttons via media query and adds equivalent entries to the history drawer. |

The redaction module (`storage/redaction.py`) is now the canonical sanitizer for any code that persists or logs user/model data. **Range C should reuse it**, not roll its own.

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

**Range B is complete.** If you are starting Range C (full Agent loop / tool execution / safety layer / history-based recommendation):

1. Read `docs/superpowers/specs/2026-05-08-haclaw-agent-loop-tools-design.md` (Range C spec).
2. Read this whole HANDOFF — pay extra attention to **§3.7 (entity preflight)** and **§3.8 (post-review hardening)**, which describe the partial-Range-C work that already landed in Range B.
3. Read `custom_components/haclaw/storage/redaction.py` — reuse `redact_sensitive()` for any new persistence path.
4. Read `tests/test_integration_services.py` to absorb the `FakeHass` / `FakeConnection` test pattern (existing 8 fake classes cover most needs).
5. Inspect `custom_components/haclaw/agent/chat_session.py:_call_with_retry` — the existing single-turn loop is the foundation Range C extends into a multi-turn iteration loop.

If you are picking up an unfinished Range B fix instead, scan `git log --oneline 145a67a..HEAD` to see what shipped after the last handoff.

Good luck. The user is detail-oriented and prefers terse, evidence-based progress reports over enthusiasm. Show your work.

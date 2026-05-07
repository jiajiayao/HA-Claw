# AGENTS.md

# HAclaw v1.0 Agent Development Guide

HAclaw is a Chinese-first AI Agent integration for Home Assistant. It is based on the design direction of `ai_agent_ha`, but v1.0 focuses on safer automation generation, domestic model support, and better Xiaomi / Mi Home / MIoT ecosystem support.

This file defines the rules that coding agents, contributors, and maintainers must follow when modifying this repository.

---

## 1. Project Identity

**Project name:** HAclaw  
**Target platform:** Home Assistant  
**Primary users:** Chinese Home Assistant users  
**Primary use cases:**

- Control Home Assistant devices through natural language.
- Generate Home Assistant automations from Chinese descriptions.
- Explain and diagnose existing automations.
- Support domestic LLM providers such as Xiaomi MiMo, DeepSeek, Qwen, Kimi, GLM, SiliconFlow, OneAPI, New API, and OpenAI-compatible gateways.
- Improve recognition and control of Xiaomi / Mi Home / MIoT / Aqara / Yeelight / Roborock / Dreame devices.
- Assist with Home Assistant configuration in a safe, reviewable, and reversible way.

HAclaw should be treated as an **AI copilot for Home Assistant**, not as an unrestricted autonomous system administrator.

---

## 2. Core Design Philosophy

HAclaw v1.0 must follow these principles:

1. **Safety before automation.**
   - Never let the model directly perform dangerous actions without user confirmation.
   - Never let the model freely call arbitrary Home Assistant services.

2. **Chinese-first experience.**
   - Chinese user input must be handled as a first-class scenario.
   - Matching should prioritize `friendly_name`, `area_name`, aliases, manufacturer, model, and integration metadata.

3. **OpenAI-compatible by default.**
   - Do not create a separate hardcoded client for every domestic provider if the provider supports OpenAI-compatible APIs.
   - Xiaomi MiMo, DeepSeek, Qwen, Kimi, GLM, SiliconFlow, OneAPI, New API, and self-hosted OpenAI-compatible gateways should reuse one `OpenAICompatibleClient`.
   - Xiaomi MiMo is a first-class v1.0 provider preset because it strengthens HAclaw's Xiaomi smart-home positioning.

4. **Home Assistant remains the source of truth.**
   - Do not connect directly to Xiaomi Cloud in v1.0 unless a user explicitly enables a future advanced feature.
   - Xiaomi devices should be controlled through existing Home Assistant entities, services, integrations, and registries.

5. **Do not invent entities or services.**
   - The agent must never fabricate `entity_id`, `device_id`, `area_id`, service name, or MIoT property.
   - When unsure, ask for confirmation or return candidate matches.

6. **Preview before write.**
   - Automations, dashboards, scripts, and configuration changes must be shown as drafts before being written.
   - Dangerous or persistent changes must include a diff, risk explanation, and rollback plan.

---

## 3. v1.0 Scope

### 3.1 Must Support

HAclaw v1.0 must support:

- A Home Assistant custom integration.
- A sidebar panel or chat UI.
- Model provider configuration through Home Assistant config flow and options flow.
- Graphical model onboarding in the Home Assistant UI or HAclaw panel.
- Conversational setup assistance for model switching, connection testing, and provider troubleshooting.
- OpenAI-compatible model provider configuration:
  - API key
  - Base URL
  - Model name
  - Optional custom model
- Domestic model presets:
  - Xiaomi MiMo
  - DeepSeek
  - Qwen / DashScope OpenAI-compatible mode
  - Kimi / Moonshot
  - GLM / Zhipu
  - SiliconFlow
  - OneAPI / New API
  - Custom OpenAI-compatible endpoint
- Local model endpoint support if compatible with OpenAI chat completions or existing local model behavior.
- Safe device control for common Home Assistant domains:
  - `light`
  - `switch`
  - `fan`
  - `climate`
  - `cover`
  - `media_player`
  - `vacuum`
  - `sensor` and `binary_sensor` read-only
- Xiaomi ecosystem discovery:
  - Xiaomi
  - Mi Home
  - Mijia
  - MIoT
  - Aqara
  - Yeelight
  - Roborock
  - Dreame
  - Lumi
  - Miio
  - Xiaomi Home official integration
  - Xiaomi Miot Auto integration
- Automation draft generation.
- User-approved automation creation.
- Existing automation explanation.
- Basic automation troubleshooting.
- Prompt and execution logging for debugging.

### 3.2 Should Support

HAclaw v1.0 should support:

- Entity disambiguation when multiple devices match the user’s phrase.
- Area-aware control, for example “打开客厅灯”.
- Chinese aliases for devices and rooms.
- Service call audit logs.
- Automation creation in a HAclaw-managed file or storage area.
- Disabled-by-default automation drafts.
- Risk classification before execution.

### 3.3 Must Not Support in v1.0

Unless explicitly implemented behind an advanced unsafe mode, HAclaw v1.0 must not:

- Directly edit `.storage/core.config_entries`.
- Directly modify third-party integration credentials.
- Directly request Xiaomi Cloud tokens.
- Directly call arbitrary Xiaomi Cloud APIs.
- Directly execute `shell_command`, `command_line`, or system commands.
- Require normal users to manually edit YAML, JSON, `.storage`, or frontend files just to connect an LLM provider.
- Unlock doors without user confirmation.
- Disarm alarms without user confirmation.
- Delete automations without user confirmation.
- Restart Home Assistant without user confirmation.
- Modify `configuration.yaml` without diff, backup, validation, and confirmation.
- Silently enable automations created by AI.
- Silently modify other integrations’ configuration files.

---

## 4. Recommended Repository Structure

The repository should evolve toward this structure:

```text
custom_components/haclaw/
├── __init__.py
├── manifest.json
├── const.py
├── config_flow.py
├── services.yaml
├── strings.json
├── agent/
│   ├── __init__.py
│   ├── core.py
│   ├── protocol.py
│   ├── prompts.py
│   ├── memory.py
│   └── safety.py
├── providers/
│   ├── __init__.py
│   ├── base.py
│   ├── openai_compatible.py
│   ├── anthropic.py
│   ├── gemini.py
│   └── local.py
├── tools/
│   ├── __init__.py
│   ├── registry.py
│   ├── entity.py
│   ├── service.py
│   ├── automation.py
│   ├── dashboard.py
│   ├── xiaomi.py
│   ├── history.py
│   └── diagnostics.py
├── storage/
│   ├── __init__.py
│   ├── drafts.py
│   └── audit_log.py
├── frontend/
│   └── haclaw-panel.js
└── translations/
    ├── en.json
    └── zh-Hans.json
```

Existing `ai_agent_ha` code may initially remain flatter, but new work should move toward this separation.

---

## 5. Provider Layer Rules

### 5.1 Use One OpenAI-Compatible Client

All OpenAI-compatible domestic providers must use one shared client.

Do not create separate duplicated clients for:

- DeepSeek
- Xiaomi MiMo
- Qwen
- Kimi
- GLM
- SiliconFlow
- OneAPI
- New API
- OpenRouter-compatible gateways
- Self-hosted vLLM
- Self-hosted LiteLLM
- Self-hosted FastChat
- OpenAI-compatible Ollama endpoints

Use this conceptual interface:

```python
class BaseChatClient:
    async def chat(self, messages: list[dict], **kwargs) -> str:
        raise NotImplementedError
```

OpenAI-compatible implementation:

```python
class OpenAICompatibleClient(BaseChatClient):
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 300,
    ) -> None:
        ...
```

Rules:

- `base_url` may be either:
  - root endpoint, such as `https://api.deepseek.com`
  - versioned endpoint, such as `https://api.moonshot.ai/v1`
  - full chat endpoint, such as `https://example.com/v1/chat/completions`
- Normalize endpoint safely.
- Never log full API keys.
- Allow custom headers only through explicit configuration.
- Use `aiohttp` unless the project intentionally adopts a shared SDK.

### 5.2 Provider Presets

Provider presets are convenience defaults only. Users must be allowed to override base URL and model.

Suggested presets:

```text
Xiaomi MiMo:
  base_url: https://api.mimo-v2.com/v1 or user configured
  model examples:
    - mimo-v2-flash
    - mimo-v2-pro
    - mimo-v2-omni
    - other MiMo models available in the user's console
  notes:
    - User-facing display names may use MiMo-V2-Flash style, but API model ids should follow the provider console.
    - Treat model names, quotas, and exact endpoints as provider-console data.
    - Show token usage when the API returns usage fields.

DeepSeek:
  base_url: https://api.deepseek.com
  model examples:
    - deepseek-chat
    - deepseek-reasoner
    - deepseek-v4-flash
    - deepseek-v4-pro

Qwen:
  base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
  model examples:
    - qwen-plus
    - qwen-max
    - qwen-turbo

Kimi:
  base_url: https://api.moonshot.cn/v1 or https://api.moonshot.ai/v1
  model examples:
    - kimi-k2
    - kimi-k2.5
    - moonshot-v1-8k
    - moonshot-v1-32k

GLM:
  base_url: provider OpenAI-compatible endpoint
  model examples:
    - glm-4
    - glm-4-plus
    - glm-4.5
    - glm-4.7

SiliconFlow:
  base_url: https://api.siliconflow.cn/v1
  model examples:
    - user selectable

OneAPI / New API:
  base_url: user configured
  model examples:
    - user configured
```

Do not assume model names are permanently stable. Model names must be user-editable.

Xiaomi MiMo must not be hidden behind only the generic custom endpoint path. It should appear as a first-class provider option in the UI and conversation setup flow.

### 5.3 Error Handling

Provider errors must be user-readable.

The agent should distinguish:

- Invalid API key
- Invalid base URL
- Model not found
- Rate limit
- Timeout
- Context length exceeded
- JSON parsing failure
- Provider returned empty response

Never expose raw secrets in errors.

### 5.4 Provider Configuration UX

LLM provider onboarding must be graphical or conversational. Normal users must not be required to manually edit `configuration.yaml`, `.storage`, JSON files, frontend JavaScript, or prompt text to connect a provider.

Required behavior:

- First-time setup must work through Home Assistant config flow or a HAclaw setup screen.
- Existing provider settings must be editable through options flow or the HAclaw settings page.
- The UI must support provider preset, API key, base URL, model, timeout, and common generation options.
- Users must be able to override provider preset values, especially base URL and model.
- A test-connection action must be available and must return redacted, user-readable errors.
- Conversational commands may assist setup, for example changing provider, testing the current configuration, or explaining a failed connection.
- Sensitive values must be stored and handled on the backend. The frontend may display only masked summaries.
- Xiaomi MiMo setup must be available as a preset with API key, base URL, model, connection test, and token usage display when available.
- The UI may mention MiMo trial or free quota as a good onboarding path, but must not hardcode a universal quota promise.

Forbidden defaults:

- Do not require editing `configuration.yaml` for normal LLM provider onboarding.
- Do not require editing `.storage`.
- Do not put API keys in frontend JavaScript, Lovelace YAML, dashboard drafts, model prompts, audit logs, or browser logs.
- Do not create separate duplicated clients for each domestic provider when an OpenAI-compatible client can handle the provider.

---

## 6. Agent Protocol

HAclaw v1.0 should use a strict internal protocol between the model and executor.

The model must return JSON only. No Markdown. No prose outside JSON.

### 6.1 Supported Response Types

```json
{
  "type": "final_response",
  "message": "..."
}
```

```json
{
  "type": "tool_call",
  "tool": "get_entity_state",
  "args": {
    "entity_id": "light.living_room"
  }
}
```

```json
{
  "type": "automation_draft",
  "title": "晚上回家打开客厅灯",
  "description": "当检测到用户回家且时间在晚上时打开客厅灯。",
  "automation": {
    "alias": "晚上回家打开客厅灯",
    "trigger": [],
    "condition": [],
    "action": [],
    "mode": "single"
  },
  "risk_level": "medium",
  "requires_confirmation": true
}
```

```json
{
  "type": "clarification",
  "message": "我找到了多个客厅灯，请选择一个。",
  "candidates": [
    {
      "entity_id": "light.living_room_main",
      "name": "客厅主灯"
    },
    {
      "entity_id": "light.living_room_strip",
      "name": "客厅灯带"
    }
  ]
}
```

```json
{
  "type": "risk_confirmation",
  "message": "这个操作会解锁门锁，需要确认。",
  "risk_level": "high",
  "planned_action": {
    "domain": "lock",
    "service": "unlock",
    "target": {
      "entity_id": "lock.front_door"
    }
  }
}
```

### 6.2 Tool Call Rules

The model may request tools, but the Python executor decides whether the tool is allowed.

The model must not directly execute:

- Raw Home Assistant service calls
- File writes
- System restart
- Lock unlock
- Alarm disarm
- Shell commands
- Xiaomi cloud requests

Those must pass through the safety layer.

### 6.3 Iteration Limit

Agent loops must have a fixed iteration limit.

Recommended default:

```text
max_iterations = 5
```

If the task cannot be completed within the limit, return a partial result and explain what is missing.

---

## 7. Prompt Rules

The system prompt must include Chinese-first behavior.

Required prompt rules:

```text
你是 HAclaw，一个面向中文用户的 Home Assistant 智能家居助手。

规则：
1. 用户使用中文描述时，优先根据 friendly_name、area_name、aliases、manufacturer、model、integration 匹配实体。
2. 不要凭空编造 entity_id、device_id、area_id、service 或 MIoT 属性。
3. 如果用户提到“小米、米家、米家设备、小爱、石头、追觅、绿米、Aqara、Yeelight、MIoT”，优先调用小米实体发现工具。
4. 控制设备时，优先使用 Home Assistant 标准服务。
5. 只有标准服务无法完成时，才考虑 xiaomi_miot 或 xiaomi_miio 专用服务。
6. 创建自动化时，先生成草稿，不要直接启用。
7. 涉及门锁、安防、报警、摄像头隐私、删除配置、重启 HA、获取 token、小米云 API 请求，必须要求用户确认。
8. 输出必须是合法 JSON，不要在 JSON 外输出解释。
```

Do not rely only on prompts for safety. Prompts are guidance; the Python safety layer is mandatory enforcement.

---

## 8. Tool Layer

All actions must go through typed tools. Do not let the model directly choose arbitrary Home Assistant internals.

### 8.1 Read Tools

Read tools are generally safe.

Allowed read tools:

```text
get_entity_state
get_entities
get_entities_by_domain
get_entities_by_area
get_entity_registry
get_device_registry
get_area_registry
get_automations
get_scenes
get_history
get_statistics
get_weather_data
get_calendar_events
get_dashboards
get_dashboard_config
get_xiaomi_entities
```

Read tools should sanitize sensitive attributes before sending data to LLMs.

Sensitive fields may include:

```text
token
access_token
refresh_token
password
secret
api_key
authorization
cookie
ssid
precise location
GPS coordinates
camera snapshots
```

### 8.2 Safe Action Tools

Safe action tools may execute with normal user intent.

Examples:

```text
turn_on_light
turn_off_light
set_light_brightness
turn_on_switch
turn_off_switch
set_fan_percentage
set_climate_temperature
open_cover
close_cover
start_vacuum
return_vacuum_to_base
play_media
pause_media
```

Even safe actions should be logged.

### 8.3 Dangerous Action Tools

Dangerous tools must require explicit user confirmation.

Dangerous examples:

```text
lock.unlock
alarm_control_panel.alarm_disarm
homeassistant.restart
homeassistant.stop
automation.delete
automation.turn_off for security-related automation
script.turn_on for unknown scripts
shell_command.*
command_line.*
xiaomi_miot.request_xiaomi_api
xiaomi_miot.get_token
configuration.yaml modification
.storage modification
```

The executor must block dangerous actions unless a confirmation token or explicit UI approval is present.

---

## 9. Service Call Safety

Raw service calls must never be unrestricted.

Use allowlists.

### 9.1 Default Allowed Domains

```python
SAFE_DOMAINS = {
    "light",
    "switch",
    "fan",
    "climate",
    "cover",
    "media_player",
    "vacuum",
    "scene",
    "script",
}
```

`script` must be treated carefully because scripts can do dangerous things. Prefer to mark unknown scripts as medium or high risk.

### 9.2 Default Blocked Domains

```python
BLOCKED_OR_CONFIRM_DOMAINS = {
    "lock",
    "alarm_control_panel",
    "homeassistant",
    "hassio",
    "persistent_notification",
    "shell_command",
    "command_line",
    "python_script",
    "rest_command",
}
```

### 9.3 Service Risk Rules

Examples:

```text
light.turn_on: low
light.turn_off: low
switch.turn_on: low or medium depending on device class
climate.set_temperature: medium
vacuum.start: low
vacuum.send_command: medium
cover.open_cover: medium
lock.unlock: high
alarm_control_panel.alarm_disarm: high
homeassistant.restart: high
shell_command.*: critical
```

Risk classification must be computed in code, not only by the model.

---

## 10. Xiaomi Support

HAclaw v1.0 should support Xiaomi devices through Home Assistant.

### 10.1 Xiaomi Discovery

Implement `get_xiaomi_entities()` using Home Assistant registries:

- `hass.states.async_all()`
- entity registry
- device registry
- area registry
- config entry metadata if available

Match against:

```text
xiaomi
mi
mijia
miot
miio
aqara
lumi
yeelight
roborock
dreame
小米
米家
小爱
石头
追觅
绿米
易来
```

Return structured data:

```json
{
  "entity_id": "fan.mi_air_purifier",
  "domain": "fan",
  "state": "on",
  "friendly_name": "米家空气净化器",
  "area_name": "客厅",
  "manufacturer": "Xiaomi",
  "model": "Air Purifier",
  "integration": "xiaomi_miot",
  "attributes": {}
}
```

Do not send excessive attributes to the model. Keep the result compact.

### 10.2 Xiaomi Control Priority

When controlling Xiaomi devices:

1. Prefer standard HA services.
2. Use integration-specific services only when necessary.
3. Require confirmation for cloud-level or token-related operations.

Priority examples:

```text
灯:
  light.turn_on / light.turn_off

插座:
  switch.turn_on / switch.turn_off

空气净化器:
  fan.turn_on / fan.turn_off / fan.set_preset_mode

空调:
  climate.set_temperature / climate.set_hvac_mode

扫地机器人:
  vacuum.start / vacuum.return_to_base
  vacuum.send_command only when room/segment cleaning is needed

小爱音箱:
  xiaomi_miot.intelligent_speaker only if integration exposes it and user enables Xiaomi advanced tools
```

### 10.3 Xiaomi Service Allowlist

Allowed with normal or medium risk:

```python
ALLOWED_XIAOMI_SERVICES = {
    "xiaomi_miot.set_property",
    "xiaomi_miot.set_miot_property",
    "xiaomi_miot.get_properties",
    "xiaomi_miot.call_action",
    "xiaomi_miot.send_command",
    "xiaomi_miot.intelligent_speaker",
    "xiaomi_miio.vacuum_clean_segment",
    "vacuum.send_command",
}
```

Require confirmation or block by default:

```python
DANGEROUS_XIAOMI_SERVICES = {
    "xiaomi_miot.request_xiaomi_api",
    "xiaomi_miot.renew_devices",
    "xiaomi_miot.get_token",
}
```

### 10.4 Xiaomi Room Cleaning

For robot vacuum room cleaning:

- Do not invent segment IDs.
- If segment IDs are unknown, ask the user to select from known data or provide them.
- Store user-confirmed room-to-segment mappings in HAclaw storage.

Example mapping storage:

```json
{
  "vacuum.roborock_s7": {
    "厨房": 16,
    "客厅": 17,
    "卧室": 18
  }
}
```

---

## 11. Automation Generation

Automation generation must be draft-first.

### 11.1 Draft Workflow

Required workflow:

```text
User description
  ↓
Entity discovery
  ↓
Candidate entity confirmation if needed
  ↓
Automation draft generation
  ↓
Schema validation
  ↓
Risk classification
  ↓
Preview in UI
  ↓
User approval
  ↓
Write to HAclaw-managed automation storage
  ↓
Reload automations
  ↓
Audit log
```

### 11.2 Storage Strategy

Avoid directly appending to the user’s original `automations.yaml`.

Preferred v1.0 strategy:

```text
/config/haclaw/automations.yaml
```

The user may need to include it once from `configuration.yaml`, or HAclaw may provide guided instructions.

Alternative if using Home Assistant APIs or UI-compatible storage becomes available:

- Use the safest supported HA mechanism.
- Do not directly edit `.storage` manually.

### 11.3 Automation Defaults

AI-created automations should default to:

```yaml
mode: single
initial_state: false
```

If HA does not honor `initial_state` in the target format, HAclaw must clearly show that the automation will be created disabled or require manual enablement.

### 11.4 Automation Validation

Before writing:

- Ensure `alias` exists.
- Ensure `trigger` exists and is list or valid object.
- Ensure `action` exists and is list or valid object.
- Ensure all referenced `entity_id`s exist.
- Ensure all referenced services exist.
- Reject unknown domains unless user confirms.
- Check for duplicate aliases.
- Check for dangerous actions.

### 11.5 Dangerous Automation Examples

Must require high-risk confirmation:

```yaml
action:
  - service: lock.unlock
```

```yaml
action:
  - service: alarm_control_panel.alarm_disarm
```

```yaml
action:
  - service: shell_command.some_command
```

```yaml
action:
  - service: homeassistant.restart
```

---

## 12. Dashboard Generation

Dashboard generation should be draft-first.

Allowed:

- Generate Lovelace YAML.
- Save HAclaw-managed dashboard drafts.
- Preview cards in the HAclaw panel if possible.
- Provide manual installation instructions.

Avoid by default:

- Automatically modifying `configuration.yaml`.
- Automatically adding sidebar dashboards without confirmation.

If modifying `configuration.yaml` is supported:

1. Create backup.
2. Generate diff.
3. Ask for confirmation.
4. Run validation if available.
5. Apply change.
6. Explain that a restart may be required.
7. Provide rollback path.

---

## 13. Configuration File Policy

### 13.1 Allowed Writes

HAclaw may write:

```text
/config/haclaw/
/config/haclaw/automations.yaml
/config/haclaw/drafts.json
/config/haclaw/audit_log.jsonl
/config/haclaw/device_aliases.json
/config/haclaw/xiaomi_room_map.json
```

### 13.2 Restricted Writes

Restricted files require diff, backup, validation, and confirmation:

```text
/config/configuration.yaml
/config/automations.yaml
/config/scripts.yaml
/config/scenes.yaml
/config/ui-lovelace.yaml
```

### 13.3 Forbidden Direct Writes

Do not directly write:

```text
/config/.storage/core.config_entries
/config/.storage/auth
/config/.storage/auth_provider.*
/config/.storage/cloud
/config/.storage/onboarding
third-party integration credential files
```

If a setting belongs to another integration, use official services, config flow, options flow, Supervisor API, or provide manual instructions.

---

## 14. Audit Logging

All meaningful operations must be logged.

Log fields:

```json
{
  "timestamp": "2026-01-01T12:00:00+08:00",
  "user_input": "晚上回家打开客厅灯",
  "model_provider": "deepseek",
  "model": "deepseek-chat",
  "tool": "create_automation_draft",
  "risk_level": "medium",
  "requires_confirmation": true,
  "approved": false,
  "result": "draft_created"
}
```

Do not log secrets.

For model messages, either:

- redact sensitive data, or
- allow the user to disable full prompt logging.

---

## 15. Frontend Requirements

The HAclaw frontend should provide:

- Chat interface.
- Provider selector.
- Current model display.
- Automation draft preview.
- Dashboard draft preview.
- Tool execution trace.
- Risk warning display.
- Confirmation dialog for dangerous actions.
- Device/entity candidate selector.
- Xiaomi device helper page or filter.
- Settings page for:
  - provider
  - model
  - base URL
  - provider setup wizard
  - connection test
  - Xiaomi advanced tools
  - allowed domains/services
  - logging options
  - memory/aliases

Do not hide dangerous actions behind small text. High-risk actions must be visually obvious.

---

## 16. Internationalization

v1.0 must prioritize Simplified Chinese.

Required translation files:

```text
translations/zh-Hans.json
translations/en.json
```

Chinese text should be natural, not machine-translated.

Use terms familiar to Chinese HA users:

```text
实体
设备
区域
自动化
场景
脚本
服务
草稿
确认执行
风险操作
小米
米家
小爱
扫地机器人
空气净化器
```

---

## 17. Coding Standards

### 17.1 Python

- Use async Home Assistant APIs.
- Do not block the event loop.
- Use `aiohttp` for HTTP calls.
- Use type hints.
- Avoid broad `except Exception` unless logging and returning user-readable error.
- Never log secrets.
- Keep provider logic separated from tool execution.
- Keep safety checks in code, not only prompts.

### 17.2 Home Assistant Integration

- Use config flow for setup.
- Use options flow for editable settings.
- Store integration data in `hass.data[DOMAIN]`.
- Register services explicitly.
- Clean up services and panels on unload.
- Use `hass.config.path(...)` for file paths.
- Use Home Assistant registries instead of manually scanning files when possible.

### 17.3 YAML

- Preserve user files when possible.
- Back up before writing.
- Prefer writing HAclaw-managed files.
- Validate structure before write.
- Avoid string-based YAML patching for critical files.

### 17.4 Frontend

- Keep the panel usable on desktop and mobile.
- Do not require external CDN.
- Do not leak API keys to the browser unless absolutely necessary.
- Prefer backend service calls for model operations.
- Show loading and error states clearly.
- Provider onboarding and model switching must be available from UI, not only from manual file edits.
- Connection test results must be clear and must not expose secrets.

---

## 18. Testing Requirements

At minimum, add tests or manual test cases for:

### Provider Tests

- OpenAI-compatible request construction.
- Base URL normalization.
- Invalid API key handling.
- Timeout handling.
- Empty response handling.
- JSON extraction from model output.

### Agent Protocol Tests

- Valid `final_response`.
- Valid `tool_call`.
- Invalid JSON.
- JSON with extra prose.
- Unknown tool.
- Tool iteration limit.

### Safety Tests

- `light.turn_on` allowed.
- `lock.unlock` requires confirmation.
- `alarm_control_panel.alarm_disarm` requires confirmation.
- `shell_command.*` blocked.
- `homeassistant.restart` requires confirmation.
- `xiaomi_miot.request_xiaomi_api` blocked or requires confirmation.

### Automation Tests

- Valid automation draft.
- Missing alias rejected.
- Missing trigger rejected.
- Missing action rejected.
- Unknown entity rejected.
- Dangerous action flagged.
- Duplicate alias handled.

### Xiaomi Tests

- Xiaomi entity discovery by manufacturer.
- Xiaomi entity discovery by integration.
- Xiaomi entity discovery by friendly name.
- Vacuum room cleaning refuses unknown segment ID.
- Standard service preferred over MIoT service.

---

## 19. Security Requirements

HAclaw is a smart home control system. Treat it as security-sensitive software.

### 19.1 Secret Handling

Never log:

```text
API keys
Home Assistant long-lived access tokens
Xiaomi tokens
refresh tokens
cookies
authorization headers
passwords
precise location data
```

### 19.2 User Confirmation

Explicit confirmation is required for:

```text
unlocking doors
disarming alarms
opening garage doors
turning off security automations
restarting HA
deleting files
editing configuration.yaml
running shell commands
calling unknown scripts
calling Xiaomi cloud-level APIs
```

### 19.3 Remote Model Privacy

Before sending data to cloud LLMs:

- Remove secrets.
- Minimize attributes.
- Avoid sending unnecessary history.
- Avoid sending precise location unless needed.
- Allow users to choose local model providers.

---

## 20. Migration from ai_agent_ha

When adapting code from `sbenodiz/ai_agent_ha`, keep the useful parts but refactor risky parts.

### 20.1 Reuse

Good candidates to reuse:

- Config flow structure.
- Sidebar panel idea.
- Service-to-event communication pattern.
- Entity registry reading.
- Device registry reading.
- Area registry reading.
- History/statistics reading.
- Automation draft UI.
- Dashboard draft UI.
- Multi-provider configuration concept.

### 20.2 Refactor

Must refactor:

- Provider classes into shared OpenAI-compatible client.
- Prompt-only JSON protocol into stricter protocol validation.
- Raw `call_service` into allowlisted tool execution.
- Direct automation write into draft-first workflow.
- Direct `configuration.yaml` modification into dangerous confirmed workflow.
- English-first prompt into Chinese-first prompt.
- Generic entity discovery into Xiaomi-enhanced discovery.

### 20.3 Remove or Disable by Default

Disable by default:

- Arbitrary Home Assistant service calls.
- Direct writes to `configuration.yaml`.
- Direct appending to user’s original `automations.yaml`.
- Unsafe Xiaomi cloud API calls.
- Any operation that can expose tokens.

---

## 21. v1.0 Release Checklist

Before tagging v1.0:

- [ ] Project domain renamed to `haclaw`.
- [ ] Manifest updated.
- [ ] Config flow supports OpenAI-compatible provider.
- [ ] Provider setup is available through UI without manual config file edits.
- [ ] Options flow or HAclaw settings page supports model switching.
- [ ] Provider connection test shows redacted user-readable errors.
- [ ] Xiaomi MiMo preset available.
- [ ] MiMo token usage display available when the provider returns usage fields.
- [ ] DeepSeek preset available.
- [ ] Qwen preset available.
- [ ] Kimi preset available.
- [ ] Custom base URL supported.
- [ ] Chinese system prompt implemented.
- [ ] Xiaomi entity discovery implemented.
- [ ] Service allowlist implemented.
- [ ] Dangerous action confirmation implemented.
- [ ] Automation draft preview implemented.
- [ ] Automation validation implemented.
- [ ] AI-created automations are disabled by default or require explicit enablement.
- [ ] Audit log implemented.
- [ ] Secrets redaction implemented.
- [ ] Frontend shows risk warnings.
- [ ] README includes Chinese quick start.
- [ ] HACS installation instructions prepared.
- [ ] Manual testing completed on a real HA instance.
- [ ] No unrestricted raw service execution remains.
- [ ] No direct `.storage` modification exists.
- [ ] No API key is exposed in frontend logs.

---

## 22. Development Priorities

When multiple tasks compete, prioritize in this order:

1. Safety and permission boundaries.
2. Correct Home Assistant integration behavior.
3. Domestic model support.
4. Chinese prompt quality.
5. Xiaomi device support.
6. Automation generation.
7. Dashboard generation.
8. UI polish.
9. Extra providers.
10. Experimental autonomous features.

---

## 23. Forbidden Implementation Patterns

Do not implement:

```python
await hass.services.async_call(domain, service, data)
```

directly from raw model output without safety validation.

Do not implement:

```python
open("/config/.storage/core.config_entries", "w")
```

Do not implement:

```python
_LOGGER.info("API key: %s", api_key)
```

Do not allow the model to decide:

```text
This is safe, so I will execute it.
```

The model may propose. The executor decides.

Do not use prompt instructions as the only security mechanism.

Do not silently recover from corrupted YAML by overwriting the user’s files.

---

## 24. Example User Flows

### 24.1 Safe Device Control

User:

```text
打开客厅灯
```

Expected behavior:

1. Find entities in area `客厅`.
2. Filter domain `light`.
3. If one strong match exists, call safe light tool.
4. Return concise result.

### 24.2 Ambiguous Device

User:

```text
打开小米灯
```

Expected behavior:

1. Call Xiaomi entity discovery.
2. Find multiple Xiaomi lights.
3. Ask user to choose.
4. Do not guess.

### 24.3 Automation Draft

User:

```text
每天晚上 7 点打开客厅空气净化器，晚上 11 点关闭
```

Expected behavior:

1. Identify purifier entity.
2. Generate automation draft.
3. Validate service calls.
4. Show preview.
5. Require approval.
6. Create disabled automation or draft.

### 24.4 Dangerous Action

User:

```text
我到家就自动打开门锁
```

Expected behavior:

1. Generate high-risk warning.
2. Explain why automatic unlock is dangerous.
3. Do not create automation directly.
4. Offer safer alternative, such as notification or manual confirmation.

### 24.5 Xiaomi Vacuum Room Cleaning

User:

```text
让石头扫地机器人清扫厨房
```

Expected behavior:

1. Find Xiaomi/Roborock vacuum.
2. Check known room segment mapping.
3. If kitchen segment is known, prepare medium-risk action.
4. If unknown, ask user to provide or select segment.
5. Do not invent segment ID.

---

## 25. Maintainer Notes

HAclaw should avoid becoming an unrestricted “AI root user” for Home Assistant.

The goal is not to make the AI powerful at all costs. The goal is to make smart home configuration easier, safer, and more understandable for Chinese users.

Every new feature should answer:

```text
Can this break the user’s home?
Can this expose secrets?
Can this be undone?
Can the user understand what will happen?
Can we restrict this with a safer tool?
```

If the answer is unclear, implement it as a draft or suggestion, not as an automatic action.

---

## 26. Version

```text
Document: AGENTS.md
Project: HAclaw
Version: v1.0
Status: Draft
Intended use: Repository-level coding agent instruction and technical guardrail
```

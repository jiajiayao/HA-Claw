# HAclaw

<p><strong>English</strong> · <a href="./README.zh-CN.md">简体中文</a></p>

HAclaw is a Chinese-first, safety-first AI agent for [Home Assistant](https://www.home-assistant.io/). It lets people control their smart home and draft automations in plain Chinese, while code, not the language model, decides what is allowed to run.

> **Status:** version `0.2.0`, a `0.x` development release working towards v1.0. It is not production-ready.
> The full design document (goals, non-goals, agent protocol, tool layer, risk levels and roadmap) is written in Chinese: [README.zh-CN.md](./README.zh-CN.md).

## Why HAclaw

- Chinese names for devices, areas and services do not map cleanly onto Home Assistant entities.
- Chinese model providers (Xiaomi MiMo, DeepSeek, Qwen, Kimi, GLM, SiliconFlow, OneAPI / New API and others) are each configured differently.
- Xiaomi, Mi Home, Aqara, Yeelight, Roborock and Dreame devices reach Home Assistant through different integrations.
- A wrong automation or configuration change affects a real home, so every change must be previewable, confirmable and reversible.

The goal is not to give an AI unlimited power over the house, but to build a Chinese-first, safety-first, auditable copilot for Home Assistant.

## Design principles

- The model only proposes intents, tool calls or drafts.
- A protocol validator accepts strict JSON only, with no Markdown or extra prose, and each mode allows only certain response types.
- Tools are typed; the model never gets raw access to arbitrary Home Assistant services.
- Risk levels are computed by code, never taken from the model's own judgement: for example `light.turn_on` is low, `lock.unlock` is high, and `shell_command.*` is blocked.
- AI-created automations are drafts and stay disabled until a person confirms them.
- Secrets are redacted before anything is stored, logged or sent to a cloud model.

## What works in v0.2

- A Home Assistant custom integration (`custom_components/haclaw`) with a config flow and an options flow, so connecting a model needs no YAML editing.
- One shared OpenAI-compatible client with eight presets: Xiaomi MiMo, DeepSeek, Qwen / DashScope, Kimi / Moonshot, GLM / Zhipu, SiliconFlow, OneAPI / New API and a custom endpoint. Base URL and model stay editable, the provider is checked during setup, and errors are redacted.
- Mode-aware strict JSON protocol validation, plus a code-based risk classifier (low, medium, high; critical services blocked) that gates every action.
- Entity discovery and Xiaomi-ecosystem recognition from Home Assistant entities, devices, areas, manufacturers and integrations.
- Automation drafts: entities and services are validated, risk is tagged, and drafts are saved disabled by default.
- A chat sidebar panel with conversation history, a settings dialog and mobile layouts. Conversations are stored with secrets redacted, and chat turns write metadata-only audit log entries.
- 127 unit tests in `tests/`, covering the protocol, safety rules, provider client and presets, automation drafts, storage, chat session and panel.

## Not yet implemented

- Multi-turn agent iteration: the agent currently validates one turn per request. The iteration limit is defined, but the loop is not built yet.
- The dashboard, history, diagnostics and dynamic tool-registry tools are placeholders.
- Anthropic, Gemini and local providers are placeholders. Xiaomi MiMo is used through its OpenAI-compatible endpoint, with no MiMo-specific features yet.
- Conversation memory is a placeholder.
- HACS packaging and testing on a real home installation are still on the v1.0 checklist.

## Quick start (development)

```bash
scripts/setup_ha_dev_env.sh   # create ~/.venvs/haclaw-ha and ~/.ha-dev/haclaw, link custom_components
scripts/run_tests.sh          # run the unit tests
scripts/run_hass_dev.sh       # start a local Home Assistant at http://localhost:8123
```

In Home Assistant, open **Settings → Devices & services → Add integration**, search for `HAclaw`, and enter an API key, Base URL and model from any OpenAI-compatible provider.

The setup script uses Homebrew Python 3.14 by default. The official Home Assistant devcontainer also works.

## Repository layout

| Path | Purpose |
| --- | --- |
| `custom_components/haclaw/` | Home Assistant integration: agent, providers, tools, storage and the sidebar panel |
| `tests/` | Unit tests for the safety rules and core features |
| `scripts/` | Development environment, test and local Home Assistant scripts |
| `README.zh-CN.md` | Full design document in Chinese |

## Acknowledgements

Parts of HAclaw's integration design, such as the config flow structure, sidebar panel and service-to-event communication, follow ideas from [ai_agent_ha](https://github.com/sbenodiz/ai_agent_ha) by Saar Benodiz (MIT License). HAclaw is a separate implementation.

## License

[MIT](./LICENSE) © 2026 Yaojia Huang

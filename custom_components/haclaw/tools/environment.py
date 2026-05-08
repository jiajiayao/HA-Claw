"""HAclaw environment readiness check + install_prompt template rendering."""

from __future__ import annotations

import re
from typing import Any

INTEGRATION_METADATA: dict[str, dict[str, str]] = {
    "xiaomi_miot": {
        "integration_name": "Xiaomi Miot Auto",
        "install_link": "https://github.com/al-one/hass-xiaomi-miot",
    },
    "hacs": {
        "integration_name": "HACS",
        "install_link": "https://hacs.xyz/",
    },
    "mobile_app": {
        "integration_name": "HA Companion App",
        "install_link": "https://companion.home-assistant.io/",
    },
    "xiaomi_miio": {
        "integration_name": "Xiaomi Miio (legacy)",
        "install_link": "https://www.home-assistant.io/integrations/xiaomi_miio/",
    },
}


INSTALL_PROMPT_TEMPLATES: dict[str, str] = {
    "hacs": """\
帮我在 Home Assistant 上安装 HACS。

环境(HAclaw 已探测):
- HA 配置目录: {{HA_KNOWN: HA_CONFIG_DIR}}
- HA 部署类型: {{HA_KNOWN: HA_INSTALL_TYPE}}

要求:
1. 用 HACS 官方安装方式 https://hacs.xyz/docs/setup/download
2. {{TODO_AGENT: 安装完成后告诉我下一步要做什么}}
3. **不要**把任何 token / 密码写入任何文件或 commit 到 git
4. 不要绕过 HA 自身的认证流程,不要直接修改 .storage
""",
    "xiaomi_miot": """\
帮我在 Home Assistant 上安装 Xiaomi Miot Auto(通过 HACS)。

环境(HAclaw 已探测):
- HA 配置目录: {{HA_KNOWN: HA_CONFIG_DIR}}
- HA 部署类型: {{HA_KNOWN: HA_INSTALL_TYPE}}
- 前提: HACS 已安装

凭据(运行时由我给你,不要写文件):
- 小米账号邮箱: {{TODO_USER: XIAOMI_EMAIL}}
- 小米账号密码: {{TODO_USER: XIAOMI_PASSWORD}}

要求:
1. HACS 添加自定义仓库 https://github.com/al-one/hass-xiaomi-miot
2. HACS 安装 Xiaomi Miot Auto
3. 重启 HA
4. 引导我在 HA UI 添加 Xiaomi Miot 集成,我在那里输入凭据
5. **绝不要**把上面凭据写到任何文件或 commit
6. {{TODO_AGENT: 完成后告诉我装好的设备数量}}
""",
}


_TODO_USER_RE = re.compile(r"\{\{TODO_USER:\s*([A-Z_][A-Z0-9_]*)\s*\}\}")
_HA_KNOWN_RE = re.compile(r"\{\{HA_KNOWN:\s*([A-Z_][A-Z0-9_]*)\s*\}\}")


def _detect_install_type(config_source: Any) -> str:
    src = str(config_source or "").lower()
    if "os" in src or "supervised" in src:
        return "HA OS / Supervised"
    if "container" in src or "docker" in src:
        return "Container"
    return "Core / Unknown"


def render_install_prompt(domain: str, hass: Any) -> dict[str, Any] | None:
    template = INSTALL_PROMPT_TEMPLATES.get(domain)
    if template is None:
        return None
    meta = INTEGRATION_METADATA.get(domain, {})
    title = "安装 " + meta.get("integration_name", domain)

    known_values = {
        "HA_CONFIG_DIR": hass.config.path(),
        "HA_INSTALL_TYPE": _detect_install_type(getattr(hass.config, "config_source", "")),
    }
    body = _HA_KNOWN_RE.sub(
        lambda m: known_values.get(m.group(1), m.group(0)),
        template,
    )
    todo_user_fields = sorted(set(_TODO_USER_RE.findall(body)))
    return {"title": title, "body": body, "todo_user_fields": todo_user_fields}


def detect_environment_readiness(
    hass: Any,
    *,
    dismissed: bool,
    provider_ok: bool,
) -> dict[str, Any]:
    items = []
    items.append({
        "id": "provider",
        "label": "Provider 连通",
        "ok": provider_ok,
        "hint": None if provider_ok else "Provider 还没接通",
        "links": [{"text": "HAclaw 集成", "url": "/config/integrations/integration/haclaw"}] if not provider_ok else [],
        "install_prompt": None,
    })

    has_tracker = any(
        s.entity_id.startswith("device_tracker.") for s in hass.states.async_all()
    )
    items.append({
        "id": "device_tracker",
        "label": "蓝牙/WiFi 存在感应",
        "ok": has_tracker,
        "hint": None if has_tracker else "找不到任何 device_tracker 实体",
        "links": [
            {"text": "Companion App", "url": INTEGRATION_METADATA["mobile_app"]["install_link"]},
            {"text": "蓝牙追踪", "url": "https://www.home-assistant.io/integrations/bluetooth_le_tracker/"},
        ] if not has_tracker else [],
        "install_prompt": None,
    })

    xiaomi_ok = bool(hass.config_entries.async_entries("xiaomi_miot"))
    items.append({
        "id": "xiaomi_miot",
        "label": "Xiaomi Home",
        "ok": xiaomi_ok,
        "hint": None if xiaomi_ok else "没装 Xiaomi Miot Auto",
        "links": [{"text": "Xiaomi Miot Auto", "url": INTEGRATION_METADATA["xiaomi_miot"]["install_link"]}] if not xiaomi_ok else [],
        "install_prompt": None if xiaomi_ok else render_install_prompt("xiaomi_miot", hass),
    })

    advanced = []
    hacs_ok = bool(hass.config_entries.async_entries("hacs"))
    advanced.append({
        "id": "hacs",
        "label": "HACS",
        "ok": hacs_ok,
        "hint": None if hacs_ok else "门槛较高,通常通过 shell 命令安装",
        "links": [{"text": "HACS 官方", "url": INTEGRATION_METADATA["hacs"]["install_link"]}] if not hacs_ok else [],
        "install_prompt": None if hacs_ok else render_install_prompt("hacs", hass),
    })

    failing_required_count = sum(1 for it in items if not it["ok"])

    return {
        "items": items,
        "advanced": advanced,
        "dismissed": dismissed,
        "failing_required_count": failing_required_count,
    }

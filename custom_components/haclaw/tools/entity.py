"""Entity discovery helpers."""

from __future__ import annotations

from typing import Any


CONTROLLABLE_DOMAINS = {
    "light",
    "switch",
    "fan",
    "climate",
    "cover",
    "media_player",
    "vacuum",
}

_DOMAIN_PRIORITY = {
    "fan": 0,
    "light": 1,
    "climate": 2,
    "cover": 3,
    "vacuum": 4,
    "switch": 5,
    "media_player": 6,
}

_DEVICE_RULES = [
    (("净化器", "空气净化", "purifier", "air purifier"), {"fan", "switch"}, True),
    (("灯", "灯光", "light"), {"light"}, False),
    (("空调", "climate", "ac"), {"climate"}, False),
    (("窗帘", "卷帘", "cover"), {"cover"}, False),
    (("扫地", "机器人", "吸尘", "vacuum", "roborock"), {"vacuum"}, False),
    (("插座", "开关", "switch", "plug"), {"switch"}, False),
    (("风扇", "fan"), {"fan"}, False),
    (("音箱", "播放器", "media player", "speaker"), {"media_player"}, False),
]


def list_controllable_entities(hass: Any, *, limit: int = 50) -> list[dict[str, str]]:
    """Return compact, LLM-safe summaries for controllable HA entities."""
    entities: list[dict[str, str]] = []
    for state in hass.states.async_all():
        entity_id = str(getattr(state, "entity_id", ""))
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        if domain not in CONTROLLABLE_DOMAINS:
            continue
        attrs = getattr(state, "attributes", {}) or {}
        friendly = str(attrs.get("friendly_name") or entity_id)
        state_value = str(getattr(state, "state", "unknown"))
        entities.append(
            {
                "entity_id": entity_id,
                "domain": domain,
                "label": friendly,
                "state": state_value,
                "subtitle": f"{entity_id} · {domain} · {state_value}",
            }
        )
        if len(entities) >= limit:
            break
    return entities


def find_entity_candidates(
    hass: Any,
    user_message: str,
    *,
    limit: int = 6,
) -> list[dict[str, str]]:
    """Find clickable entity candidates relevant to a user automation request."""
    normalized = user_message.lower()
    entities = list_controllable_entities(hass)
    scored: list[tuple[int, int, dict[str, str]]] = []
    for entity in entities:
        haystack = " ".join(
            (
                entity["entity_id"].lower(),
                entity["label"].lower(),
                entity["domain"].lower(),
            )
        )
        score = 0
        for keywords, domains, requires_text_match in _DEVICE_RULES:
            if not any(keyword in normalized for keyword in keywords):
                continue
            text_match = any(keyword in haystack for keyword in keywords)
            domain_match = entity["domain"] in domains
            if requires_text_match and not text_match:
                continue
            if text_match:
                score += 10
            if domain_match:
                score += 4
        if score <= 0:
            continue
        priority = _DOMAIN_PRIORITY.get(entity["domain"], 99)
        scored.append((score, -priority, entity))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]["entity_id"]))
    return [
        {
            "id": entity["entity_id"],
            "label": entity["label"],
            "subtitle": entity["subtitle"],
        }
        for _, _, entity in scored[:limit]
    ]


def build_entity_context(hass: Any, *, limit: int = 30) -> str:
    """Build the device-selection context sent to the LLM."""
    entities = list_controllable_entities(hass, limit=limit)
    if not entities:
        return (
            "当前没有扫描到可控制设备实体。需要用户先在 Home Assistant 添加设备集成"
            "(例如小米 / 米家可通过 Xiaomi Miot Auto、Xiaomi Home 官方集成、"
            "或其他会产生 light/switch/fan/climate/cover/vacuum 实体的集成)。"
            "不要要求用户手输 entity_id。"
        )

    lines = ["当前 HA 可控制设备实体:"]
    for entity in entities:
        lines.append(
            "- "
            f"id={entity['entity_id']}; "
            f"name={entity['label']}; "
            f"domain={entity['domain']}; "
            f"state={entity['state']}"
        )
    lines.append(
        "设备选择规则: 需要选择设备时必须返回 clarification.candidates 让用户点选;"
        "candidate.id 必须来自上面的 id,candidate.label 使用 name。"
        "不要要求用户手输 entity_id,不要编造不在列表里的实体。"
    )
    return "\n".join(lines)

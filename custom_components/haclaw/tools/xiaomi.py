"""Xiaomi ecosystem discovery helpers."""

from __future__ import annotations

from typing import Any, Mapping


XIAOMI_KEYWORDS = {
    "xiaomi",
    "mijia",
    "miot",
    "miio",
    "aqara",
    "lumi",
    "yeelight",
    "roborock",
    "dreame",
    "xiaomi_home",
    "xiaomi_miot",
    "小米",
    "米家",
    "小爱",
    "石头",
    "追觅",
    "绿米",
    "易来",
}

SENSITIVE_ATTRIBUTE_FRAGMENTS = {
    "token",
    "access_token",
    "refresh_token",
    "password",
    "secret",
    "api_key",
    "authorization",
    "cookie",
    "ssid",
    "latitude",
    "longitude",
    "gps",
    "precise_location",
}


class UnknownXiaomiRoomSegment(ValueError):
    """Raised when a vacuum room segment mapping is missing."""


def is_xiaomi_metadata(metadata: Mapping[str, Any]) -> bool:
    """Return whether entity/device metadata belongs to the Xiaomi ecosystem."""
    fields = [
        metadata.get("entity_id"),
        metadata.get("friendly_name"),
        metadata.get("manufacturer"),
        metadata.get("model"),
        metadata.get("integration"),
    ]
    haystack = " ".join(str(field).lower() for field in fields if field)
    return any(keyword.lower() in haystack for keyword in XIAOMI_KEYWORDS)


def summarize_xiaomi_entity(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Build a compact LLM-safe Xiaomi entity summary."""
    entity_id = str(metadata.get("entity_id", ""))
    domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
    return {
        "entity_id": entity_id,
        "domain": domain,
        "state": metadata.get("state"),
        "friendly_name": metadata.get("friendly_name") or "",
        "area_name": metadata.get("area_name") or "",
        "manufacturer": metadata.get("manufacturer") or "",
        "model": metadata.get("model") or "",
        "integration": metadata.get("integration") or "",
        "attributes": sanitize_attributes(metadata.get("attributes") or {}),
    }


def sanitize_attributes(attributes: Mapping[str, Any]) -> dict[str, Any]:
    """Remove secrets and precise location data before sending data to models."""
    sanitized: dict[str, Any] = {}
    for key, value in attributes.items():
        normalized_key = str(key).lower()
        if any(fragment in normalized_key for fragment in SENSITIVE_ATTRIBUTE_FRAGMENTS):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[str(key)] = value
    return sanitized


def resolve_room_segment(
    vacuum_entity_id: str,
    room_name: str,
    room_mappings: Mapping[str, Mapping[str, int]],
) -> int:
    """Resolve a user-confirmed room name to a robot vacuum segment ID."""
    vacuum_map = room_mappings.get(vacuum_entity_id, {})
    segment_id = vacuum_map.get(room_name)
    if segment_id is None:
        raise UnknownXiaomiRoomSegment(
            f"No confirmed room segment for {room_name!r} on {vacuum_entity_id}."
        )
    return segment_id

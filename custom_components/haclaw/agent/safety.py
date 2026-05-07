"""Safety policy for Home Assistant service execution."""

from __future__ import annotations

from dataclasses import dataclass


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

BLOCKED_DOMAINS = {
    "shell_command",
    "command_line",
    "python_script",
    "rest_command",
}

CONFIRM_DOMAINS = {
    "lock",
    "alarm_control_panel",
    "homeassistant",
    "hassio",
    "persistent_notification",
}

DANGEROUS_XIAOMI_SERVICES = {
    "xiaomi_miot.request_xiaomi_api",
    "xiaomi_miot.renew_devices",
    "xiaomi_miot.get_token",
}

SERVICE_RISKS = {
    "light.turn_on": "low",
    "light.turn_off": "low",
    "switch.turn_on": "low",
    "switch.turn_off": "low",
    "fan.turn_on": "low",
    "fan.turn_off": "low",
    "fan.set_percentage": "medium",
    "fan.set_preset_mode": "medium",
    "climate.set_temperature": "medium",
    "climate.set_hvac_mode": "medium",
    "cover.open_cover": "medium",
    "cover.close_cover": "medium",
    "media_player.media_play": "low",
    "media_player.media_pause": "low",
    "vacuum.start": "low",
    "vacuum.return_to_base": "low",
    "vacuum.send_command": "medium",
    "scene.turn_on": "medium",
    "script.turn_on": "medium",
    "lock.unlock": "high",
    "alarm_control_panel.alarm_disarm": "high",
    "homeassistant.restart": "high",
    "homeassistant.stop": "high",
}


@dataclass(frozen=True, slots=True)
class ServiceRiskDecision:
    """Decision returned by the safety layer for a service call."""

    domain: str
    service: str
    allowed: bool
    risk_level: str
    requires_confirmation: bool
    blocked: bool = False
    reason: str = ""


def evaluate_service_call(
    domain: str,
    service: str,
    *,
    confirmed: bool = False,
) -> ServiceRiskDecision:
    """Classify and gate a Home Assistant service call."""
    normalized_domain = domain.strip().lower()
    normalized_service = service.strip().lower()
    service_key = f"{normalized_domain}.{normalized_service}"

    if normalized_domain in BLOCKED_DOMAINS or service_key in DANGEROUS_XIAOMI_SERVICES:
        return ServiceRiskDecision(
            domain=normalized_domain,
            service=normalized_service,
            allowed=False,
            risk_level="critical",
            requires_confirmation=True,
            blocked=True,
            reason="This service is blocked by HAclaw safety policy.",
        )

    if normalized_domain in CONFIRM_DOMAINS:
        risk_level = SERVICE_RISKS.get(service_key, "high")
        return _decision(
            normalized_domain,
            normalized_service,
            risk_level=risk_level,
            requires_confirmation=True,
            confirmed=confirmed,
            reason="This service touches a high-risk Home Assistant domain.",
        )

    if normalized_domain not in SAFE_DOMAINS and not service_key.startswith(
        ("xiaomi_miot.", "xiaomi_miio.")
    ):
        return _decision(
            normalized_domain,
            normalized_service,
            risk_level="high",
            requires_confirmation=True,
            confirmed=confirmed,
            reason="Unknown domains require explicit confirmation.",
        )

    risk_level = SERVICE_RISKS.get(service_key, "medium")
    requires_confirmation = (
        risk_level in {"high", "critical"} or service_key == "script.turn_on"
    )
    return _decision(
        normalized_domain,
        normalized_service,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        confirmed=confirmed,
        reason="Service passed HAclaw allowlist checks.",
    )


def _decision(
    domain: str,
    service: str,
    *,
    risk_level: str,
    requires_confirmation: bool,
    confirmed: bool,
    reason: str,
) -> ServiceRiskDecision:
    return ServiceRiskDecision(
        domain=domain,
        service=service,
        allowed=not requires_confirmation or confirmed,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        blocked=False,
        reason=reason,
    )

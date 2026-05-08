"""Automation draft validation helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

from custom_components.haclaw.agent.safety import evaluate_service_call
from .environment import INTEGRATION_METADATA


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


@dataclass(frozen=True, slots=True)
class ServiceCallRef:
    """A service call referenced by an automation draft."""

    domain: str
    service: str

    @property
    def key(self) -> str:
        """Return the Home Assistant service key."""
        return f"{self.domain}.{self.service}"


@dataclass(frozen=True, slots=True)
class AutomationValidationResult:
    """Structured validation result for an automation draft."""

    automation: dict[str, Any]
    entity_ids: set[str] = field(default_factory=set)
    service_calls: list[ServiceCallRef] = field(default_factory=list)
    risk_level: str = "low"
    requires_confirmation: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_integrations: list[dict[str, Any]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        """Return whether the draft can be stored."""
        return not self.errors


def normalize_automation_draft(automation: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy with safe HAclaw defaults applied."""
    normalized = deepcopy(dict(automation))
    normalized.setdefault("mode", "single")
    normalized.setdefault("initial_state", False)
    return normalized


def validate_automation_draft(
    automation: Mapping[str, Any],
    *,
    known_entity_ids: set[str] | None = None,
    service_exists: Callable[[str, str], bool] | None = None,
    existing_aliases: set[str] | None = None,
) -> AutomationValidationResult:
    """Validate an automation draft before it is saved or approved."""
    normalized = normalize_automation_draft(automation)
    errors: list[str] = []
    warnings: list[str] = []

    alias = normalized.get("alias")
    if not isinstance(alias, str) or not alias.strip():
        errors.append("automation.alias is required.")
    elif existing_aliases and alias.strip() in existing_aliases:
        errors.append(f"automation alias already exists: {alias.strip()}.")

    if "trigger" not in normalized:
        errors.append("automation.trigger is required.")
    elif not isinstance(normalized["trigger"], (list, dict)):
        errors.append("automation.trigger must be a list or object.")

    if "action" not in normalized:
        errors.append("automation.action is required.")
    elif not isinstance(normalized["action"], (list, dict)):
        errors.append("automation.action must be a list or object.")

    entity_ids = extract_entity_ids(normalized)
    if known_entity_ids is not None:
        for entity_id in sorted(entity_ids):
            if entity_id not in known_entity_ids:
                errors.append(f"unknown entity_id: {entity_id}.")

    service_calls = extract_service_calls(normalized)
    risk_level = "low"
    requires_confirmation = False
    for service_call in service_calls:
        if service_exists is not None and not service_exists(
            service_call.domain, service_call.service
        ):
            errors.append(f"unknown service: {service_call.key}.")

        decision = evaluate_service_call(service_call.domain, service_call.service)
        risk_level = max(
            risk_level,
            decision.risk_level,
            key=lambda item: RISK_ORDER[item],
        )
        requires_confirmation = requires_confirmation or decision.requires_confirmation
        if decision.blocked:
            errors.append(f"blocked service: {service_call.key}.")
        elif decision.requires_confirmation:
            warnings.append(f"{service_call.key} requires explicit confirmation.")

    missing_integrations: list[dict[str, Any]] = []
    if service_exists is not None:
        seen_domains: set[str] = set()
        for sc in service_calls:
            if sc.domain in seen_domains:
                continue
            seen_domains.add(sc.domain)
            if service_exists(sc.domain, sc.service):
                continue
            meta = INTEGRATION_METADATA.get(sc.domain, {})
            missing_integrations.append({
                "domain": sc.domain,
                "service": sc.key,
                "integration_name": meta.get("integration_name", sc.domain),
                "install_link": meta.get("install_link"),
                "reason": f"草稿用到了 {sc.key} 服务但未检测到这个集成",
            })

    return AutomationValidationResult(
        automation=normalized,
        entity_ids=entity_ids,
        service_calls=service_calls,
        risk_level=risk_level,
        requires_confirmation=requires_confirmation,
        errors=errors,
        warnings=warnings,
        missing_integrations=missing_integrations,
    )


def extract_entity_ids(value: Any) -> set[str]:
    """Extract concrete entity ids from a nested automation structure."""
    entity_ids: set[str] = set()

    if isinstance(value, Mapping):
        for key, item in value.items():
            if key == "entity_id":
                entity_ids.update(_coerce_entity_ids(item))
            else:
                entity_ids.update(extract_entity_ids(item))
    elif isinstance(value, list):
        for item in value:
            entity_ids.update(extract_entity_ids(item))

    return entity_ids


def extract_service_calls(value: Any) -> list[ServiceCallRef]:
    """Extract service calls from Home Assistant automation action structures."""
    service_calls: list[ServiceCallRef] = []

    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"service", "action"} and isinstance(item, str) and "." in item:
                domain, service = item.split(".", 1)
                service_calls.append(
                    ServiceCallRef(domain=domain.strip(), service=service.strip())
                )
            else:
                service_calls.extend(extract_service_calls(item))
    elif isinstance(value, list):
        for item in value:
            service_calls.extend(extract_service_calls(item))

    return service_calls


def _coerce_entity_ids(value: Any) -> set[str]:
    if isinstance(value, str):
        candidates = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        candidates = [str(item).strip() for item in value]
    else:
        return set()

    return {
        item
        for item in candidates
        if "." in item and "{" not in item and "}" not in item
    }

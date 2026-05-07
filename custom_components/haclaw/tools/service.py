"""Safe service execution helpers."""

from __future__ import annotations

from custom_components.haclaw.agent.safety import evaluate_service_call


async def async_safe_call_service(
    hass,
    domain: str,
    service: str,
    service_data: dict | None = None,
    *,
    confirmed: bool = False,
) -> None:
    """Call a service only after HAclaw safety policy allows it."""
    decision = evaluate_service_call(domain, service, confirmed=confirmed)
    if not decision.allowed:
        raise PermissionError(decision.reason)

    await hass.services.async_call(
        decision.domain,
        decision.service,
        service_data or {},
        blocking=True,
    )

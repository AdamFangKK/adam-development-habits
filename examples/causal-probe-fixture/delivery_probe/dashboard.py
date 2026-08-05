from __future__ import annotations

from delivery_probe.provider import EmailProvider


def duplicate_delivery_alert(provider: EmailProvider) -> bool:
    """A downstream symptom surface. Changing this cannot prevent a provider send."""
    return provider.delivery_count > 1

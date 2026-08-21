from __future__ import annotations

import unicodedata

DEPLOYMENT_STATUS_FIELD_KEY = "deployment_status"
DEPLOYMENT_STATUS_DEPLOYED = "Déployé"
DEPLOYMENT_STATUS_OPTIONS = (
    DEPLOYMENT_STATUS_DEPLOYED,
    "À tester",
    "Stocké",
    "Jeté",
)
DEPLOYMENT_STATUS_DEFAULT = "Stocké"


def normalize_deployment_status(value: object) -> str:
    """Return a comparison-safe deployment status while preserving UI labels elsewhere."""
    return "".join(
        char
        for char in unicodedata.normalize("NFD", str(value or "").strip().lower())
        if not unicodedata.combining(char)
    )


def is_deployed_device(device: object) -> bool:
    return normalize_deployment_status(getattr(device, DEPLOYMENT_STATUS_FIELD_KEY, "")) == "deploye"

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HebergementWebConfig:
    hote_ecoute: str = "0.0.0.0"
    port_ecoute: int = 8080
    demarrage_auto_service: bool = True
    utiliser_url_publique_reverse_proxy: bool = False
    url_publique: str = "https://monitoring.mvl"
    reverse_proxy_actif: bool = False
    reverse_proxy_type: str = "caddy"


def default_hebergement_web_path() -> Path:
    override = str(os.environ.get("NMP_HEBERGEMENT_CONFIG") or "").strip()
    if override:
        return Path(override)
    return Path(__file__).resolve().parent / "hebergement_web.json"


def load_hebergement_web_config(path: str | Path | None = None) -> HebergementWebConfig:
    target = Path(path) if path is not None else default_hebergement_web_path()
    data: dict[str, object] = {}
    if target.is_file():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    return HebergementWebConfig(
        hote_ecoute=_str_value(data.get("hote_ecoute"), fallback="0.0.0.0"),
        port_ecoute=_int_value(data.get("port_ecoute"), fallback=8080, min_value=1, max_value=65535),
        demarrage_auto_service=_bool_value(data.get("demarrage_auto_service"), fallback=True),
        utiliser_url_publique_reverse_proxy=_bool_value(
            data.get("utiliser_url_publique_reverse_proxy"),
            fallback=False,
        ),
        url_publique=_str_value(data.get("url_publique"), fallback="https://monitoring.mvl"),
        reverse_proxy_actif=_bool_value(data.get("reverse_proxy_actif"), fallback=False),
        reverse_proxy_type=_str_value(data.get("reverse_proxy_type"), fallback="caddy"),
    )


def _str_value(value: object, *, fallback: str) -> str:
    return str(value if value is not None else fallback).strip() or fallback


def _bool_value(value: object, *, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    raw = str(value or "").strip().lower()
    if raw in {"1", "true", "yes", "on", "oui"}:
        return True
    if raw in {"0", "false", "no", "off", "non"}:
        return False
    return bool(fallback)


def _int_value(value: object, *, fallback: int, min_value: int, max_value: int) -> int:
    try:
        parsed = int(str(value).strip())
    except Exception:
        parsed = int(fallback)
    return max(min_value, min(max_value, parsed))

"""Клиент OAuth + chat/completions для GigaChat (httpx)."""

from __future__ import annotations

import base64
import binascii
import logging
import re
import uuid
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def _normalize_basic_credentials(raw: str) -> str:
    """
    GigaChat OAuth ожидает заголовок Authorization: Basic <base64(client_id:client_secret)>.

    В .env часто копируют:
    - только Base64-тело без `=` в конце (некорректная длина) — сервер отвечает «Can't decode Authorization header»;
    - пару `client_id:client_secret` без Base64 — нужно закодировать.
    - уже готовую строку `Basic ...`.
    """
    key = (raw or "").strip()
    if not key:
        raise RuntimeError("GIGACHAT_AUTH_KEY не задан")
    if key.lower().startswith("basic "):
        return key

    # Явная пара id:secret (как в кабинете, если скопировали не Base64)
    if ":" in key and not re.fullmatch(r"[A-Za-z0-9+/=]+", key):
        token = base64.b64encode(key.encode("utf-8")).decode("ascii")
        return f"Basic {token}"

    # Только Base64-тело (возможно без padding)
    body = key.replace(" ", "")
    pad = (4 - len(body) % 4) % 4
    padded = body + ("=" * pad)
    try:
        base64.b64decode(padded, validate=True)
    except binascii.Error as exc:
        raise RuntimeError(
            "GIGACHAT_AUTH_KEY: не удалось разобрать как Base64. "
            "Укажите либо полный ключ `Basic ...`, либо Base64 от `client_id:client_secret`, "
            "либо пару `client_id:client_secret` одной строкой."
        ) from exc
    return f"Basic {padded}"


def _auth_header() -> str:
    return _normalize_basic_credentials(getattr(settings, "GIGACHAT_AUTH_KEY", "") or "")


def fetch_access_token() -> str:
    scope = getattr(settings, "GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    url = getattr(settings, "GIGACHAT_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
    verify = getattr(settings, "GIGACHAT_VERIFY_SSL", True)
    headers = {
        "Authorization": _auth_header(),
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    # В кабинете GigaChat часто приводят пример только со `scope`.
    # `grant_type=client_credentials` поддерживается и обычно обязателен,
    # но если сервер возвращает 400 на этом варианте — делаем безопасный fallback.
    primary_data = {"grant_type": "client_credentials", "scope": scope}
    fallback_data = {"scope": scope}

    with httpx.Client(verify=verify, timeout=60.0) as client:
        r = client.post(url, headers=headers, data=primary_data)
        if r.status_code >= 400:
            logger.warning("GigaChat OAuth primary HTTP %s: %s", r.status_code, r.text[:500])
            r = client.post(url, headers=headers, data=fallback_data)
    if r.status_code >= 400:
        logger.warning("GigaChat OAuth fallback HTTP %s: %s", r.status_code, r.text[:500])
        raise RuntimeError(f"GigaChat OAuth error {r.status_code}: {r.text[:500]}")
    body = r.json()
    token = body.get("access_token")
    if not token:
        raise RuntimeError(f"GigaChat OAuth: нет access_token в ответе: {body}")
    return token


def chat_completion(user_prompt: str, system_prompt: str | None = None) -> str:
    token = fetch_access_token()
    base = getattr(settings, "GIGACHAT_API_BASE", "https://gigachat.devices.sberbank.ru/api/v1")
    model = getattr(settings, "GIGACHAT_MODEL", "GigaChat")
    verify = getattr(settings, "GIGACHAT_VERIFY_SSL", True)
    url = f"{base.rstrip('/')}/chat/completions"
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    payload: dict[str, Any] = {"model": model, "messages": messages, "temperature": 0.2}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(verify=verify, timeout=120.0) as client:
        r = client.post(url, headers=headers, json=payload)
    if r.status_code >= 400:
        logger.warning("GigaChat HTTP %s: %s", r.status_code, r.text[:500])
    r.raise_for_status()
    body = r.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError(f"GigaChat: пустой choices: {body}")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if not content:
        raise RuntimeError(f"GigaChat: нет content: {body}")
    return str(content).strip()

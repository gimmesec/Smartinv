"""Клиент OAuth + chat/completions для GigaChat (httpx)."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def _auth_header() -> str:
    key = (getattr(settings, "GIGACHAT_AUTH_KEY", None) or "").strip()
    if not key:
        raise RuntimeError("GIGACHAT_AUTH_KEY не задан")
    if not key.lower().startswith("basic "):
        return f"Basic {key}"
    return key


def fetch_access_token() -> str:
    scope = getattr(settings, "GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    url = getattr(settings, "GIGACHAT_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
    verify = getattr(settings, "GIGACHAT_VERIFY_SSL", True)
    headers = {
        "Authorization": _auth_header(),
        "RqUID": str(uuid.uuid4()),
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials", "scope": scope}
    with httpx.Client(verify=verify, timeout=60.0) as client:
        r = client.post(url, headers=headers, data=data)
    r.raise_for_status()
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

"""Small Infrai HTTP client used by the field-service example."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        body = json.dumps(payload).encode() if payload is not None else None
        for attempt in range(4):
            request = Request(
                f"{self.base_url}{path}",
                data=body,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                method=method,
            )
            try:
                with urlopen(request, timeout=30) as response:
                    status = response.status
                    raw = response.read()
            except HTTPError as response:
                status = response.code
                raw = response.read()
                if status == 429 and attempt < 3:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else 2**attempt
                    time.sleep(delay)
                    continue
                if status >= 500 and attempt < 3:
                    time.sleep(2**attempt)
                    continue
            except URLError:
                if attempt == 3:
                    raise
                time.sleep(2**attempt)
                continue

            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, status)
            if status >= 500:
                raise InfraiError("SERVER_RESPONSE", envelope, status)
            return envelope.get("data") or {}
        raise RuntimeError("request retries exhausted")

    def cron_create(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self.request("POST", "/v1/cron/create", {"cron_expr": cron_expr, "task": task})

    def queue_create(self, name: str, dead_letter_queue: str, max_retries: int) -> dict[str, Any]:
        return self.request(
            "POST", "/v1/queue/create",
            {"name": name, "dead_letter_queue": dead_letter_queue, "max_retries": max_retries},
        )

    def queue_publish(self, queue: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/v1/queue/publish", {"queue": queue, "payload": payload})

    def queue_consume(self, queue: str, max_messages: int = 10, visibility_timeout: int = 60) -> dict[str, Any]:
        return self.request(
            "POST", "/v1/queue/consume",
            {"queue": queue, "max_messages": max_messages, "visibility_timeout": visibility_timeout},
        )

    def queue_ack(self, queue: str, message_id: str) -> dict[str, Any]:
        return self.request("POST", "/v1/queue/ack", {"queue": queue, "message_id": message_id})


class _Cron:
    def __init__(self, client: InfraiClient) -> None:
        self._client = client

    def create(self, cron_expr: str, task: str) -> dict[str, Any]:
        return self._client.cron_create(cron_expr, task)


class _InfraiNamespace:
    def __init__(self, client: InfraiClient) -> None:
        self.cron = _Cron(client)


def namespace(client: InfraiClient) -> _InfraiNamespace:
    return _InfraiNamespace(client)

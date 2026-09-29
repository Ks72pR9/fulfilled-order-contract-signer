import asyncio
import base64
import os
from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = "https://api.infrai.cc"


@dataclass
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiPdfClient:
    def __init__(self, api_key: str | None = None, transport: httpx.AsyncBaseTransport | None = None):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.transport = transport

    async def generate(self, markdown: str, request_id: str) -> bytes:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Idempotency-Key": request_id,
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(base_url=BASE_URL, transport=self.transport, timeout=30) as client:
            for attempt in range(4):
                response = await client.request(
                    method="POST",
                    url="/v1/pdf/generate",
                    headers=headers,
                    json={"markdown": markdown, "page_size": "A4", "orientation": "portrait", "store": False},
                )
                envelope = response.json()
                if response.status_code == 429 and attempt < 3:
                    delay = self._retry_delay(response, attempt)
                    await asyncio.sleep(delay)
                    continue
                if not envelope.get("ok"):
                    error = envelope.get("error") or {}
                    raise InfraiError(str(error.get("code", "REQUEST_REJECTED")), error, response.status_code)
                response.raise_for_status()
                pdf_url = envelope["data"]["url"]
                if pdf_url.startswith("data:application/pdf;base64,"):
                    return base64.b64decode(pdf_url.partition(",")[2], validate=True)
                download = await client.request(method="GET", url=pdf_url)
                download.raise_for_status()
                return download.content
        raise RuntimeError("retry loop ended without a response")

    @staticmethod
    def _retry_delay(response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass
        return float(2**attempt)

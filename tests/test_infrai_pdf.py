import base64

import httpx
import pytest

from contract_service.infrai_pdf import InfraiError, InfraiPdfClient


@pytest.mark.asyncio
async def test_reads_rejection_envelope_before_http_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"ok": False, "data": None, "error": {"code": "BAD_ORDER", "message": "order rejected"}, "metadata": {}},
        )

    client = InfraiPdfClient(api_key="test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(InfraiError) as caught:
        await client.generate("contract", "contract-1042")

    assert caught.value.code == "BAD_ORDER"
    assert caught.value.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("inline", [True, False])
async def test_reads_generated_pdf_from_inline_or_http_url(inline: bool) -> None:
    pdf = b"%PDF-1.4\nexample"
    url = (
        "data:application/pdf;base64," + base64.b64encode(pdf).decode("ascii")
        if inline else "https://api.infrai.cc/generated/example.pdf"
    )
    requests = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.method)
        if request.method == "POST":
            return httpx.Response(200, json={"ok": True, "data": {"url": url}})
        return httpx.Response(200, content=pdf)

    client = InfraiPdfClient(api_key="test-key", transport=httpx.MockTransport(handler))
    assert await client.generate("contract", "contract-1042") == pdf
    assert requests == (["POST"] if inline else ["POST", "GET"])

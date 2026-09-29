import pytest

from contract_service.contract_workflow import ContractNotReady, ContractWorkflow
from contract_service.order_models import SignContractRequest


class RecordingPdfClient:
    def __init__(self):
        self.calls = 0

    async def generate(self, markdown: str, request_id: str) -> bytes:
        self.calls += 1
        return b"unsigned-pdf"


class RecordingSigner:
    def sign(self, pdf: bytes, reason: str) -> bytes:
        return b"signed:" + pdf


def order_data() -> dict:
    return {
        "order_id": "ord_1042",
        "customer_name": "Avery Chen",
        "customer_email": "avery@example.com",
        "currency": "usd",
        "items": [{"sku": "desk-lamp", "name": "Desk lamp", "quantity": 1, "unit_price_cents": 8900}],
        "fulfillment": "fulfilled",
        "receipt_number": "rcpt_1042",
        "updates": [
            {"kind": "checkout_accepted", "occurred_at": "2026-08-12T09:10:00Z"},
            {"kind": "fulfillment_confirmed", "occurred_at": "2026-08-13T16:30:00Z"},
            {"kind": "receipt_issued", "occurred_at": "2026-08-13T16:31:00Z"},
        ],
    }


@pytest.mark.asyncio
async def test_signs_only_after_fulfillment_and_receipt_updates() -> None:
    pdf_client = RecordingPdfClient()
    workflow = ContractWorkflow(pdf_client, RecordingSigner())
    ready = SignContractRequest.model_validate(order_data())

    result = await workflow.sign_fulfilled_order(ready)

    assert result == b"signed:unsigned-pdf"
    assert pdf_client.calls == 1


@pytest.mark.asyncio
async def test_pending_order_never_generates_a_contract() -> None:
    pdf_client = RecordingPdfClient()
    pending_data = order_data()
    pending_data["fulfillment"] = "pending"
    workflow = ContractWorkflow(pdf_client, RecordingSigner())

    with pytest.raises(ContractNotReady, match="fulfillment"):
        await workflow.sign_fulfilled_order(SignContractRequest.model_validate(pending_data))

    assert pdf_client.calls == 0

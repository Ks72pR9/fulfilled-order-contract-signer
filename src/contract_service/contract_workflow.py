from dataclasses import dataclass

from .contract_signer import PemContractSigner
from .infrai_pdf import InfraiPdfClient
from .order_models import FulfillmentStatus, SignContractRequest, UpdateKind


class ContractNotReady(ValueError):
    pass


@dataclass
class ContractWorkflow:
    pdf_client: InfraiPdfClient
    signer: PemContractSigner

    async def sign_fulfilled_order(self, order: SignContractRequest) -> bytes:
        update_kinds = {update.kind for update in order.updates}
        required = {
            UpdateKind.CHECKOUT_ACCEPTED,
            UpdateKind.FULFILLMENT_CONFIRMED,
            UpdateKind.RECEIPT_ISSUED,
        }
        if order.fulfillment != FulfillmentStatus.FULFILLED:
            raise ContractNotReady("Order fulfillment is not complete")
        if not order.receipt_number or not required.issubset(update_kinds):
            raise ContractNotReady("Receipt and customer order updates must be complete")

        markdown = render_contract(order)
        unsigned_pdf = await self.pdf_client.generate(markdown, f"contract-{order.order_id}")
        return self.signer.sign(unsigned_pdf, f"Fulfilled ecommerce order {order.order_id}")


def render_contract(order: SignContractRequest) -> str:
    lines = "\n".join(
        f"| {item.sku} | {item.name} | {item.quantity} | {item.unit_price_cents / 100:.2f} {order.currency.upper()} |"
        for item in order.items
    )
    total = sum(item.quantity * item.unit_price_cents for item in order.items) / 100
    return f"""# Ecommerce sale contract

**Order:** {order.order_id}  
**Customer:** {order.customer_name} ({order.customer_email})  
**Receipt:** {order.receipt_number}

| SKU | Item | Quantity | Unit price |
| --- | --- | ---: | ---: |
{lines}

**Total:** {total:.2f} {order.currency.upper()}

The merchant confirms checkout acceptance, fulfillment, and receipt issuance for this order.
"""

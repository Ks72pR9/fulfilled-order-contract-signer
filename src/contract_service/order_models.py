from enum import StrEnum

from pydantic import BaseModel, Field


class FulfillmentStatus(StrEnum):
    PENDING = "pending"
    FULFILLED = "fulfilled"


class UpdateKind(StrEnum):
    CHECKOUT_ACCEPTED = "checkout_accepted"
    FULFILLMENT_CONFIRMED = "fulfillment_confirmed"
    RECEIPT_ISSUED = "receipt_issued"


class LineItem(BaseModel):
    sku: str
    name: str
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)


class CustomerUpdate(BaseModel):
    kind: UpdateKind
    occurred_at: str


class SignContractRequest(BaseModel):
    order_id: str
    customer_name: str
    customer_email: str
    currency: str = Field(min_length=3, max_length=3)
    items: list[LineItem] = Field(min_length=1)
    fulfillment: FulfillmentStatus
    receipt_number: str | None = None
    updates: list[CustomerUpdate]


class SignedContractResponse(BaseModel):
    order_id: str
    state: str
    signed_pdf_base64: str

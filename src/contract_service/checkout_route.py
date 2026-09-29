import base64

from fastapi import FastAPI, HTTPException

from .contract_signer import PemContractSigner
from .contract_workflow import ContractNotReady, ContractWorkflow
from .infrai_pdf import InfraiError, InfraiPdfClient
from .order_models import SignContractRequest, SignedContractResponse

app = FastAPI(title="Fulfilled order contract signer")


def get_workflow() -> ContractWorkflow:
    return ContractWorkflow(InfraiPdfClient(), PemContractSigner())


@app.post("/orders/sign-contract", response_model=SignedContractResponse)
async def sign_contract(order: SignContractRequest) -> SignedContractResponse:
    try:
        signed_pdf = await get_workflow().sign_fulfilled_order(order)
    except ContractNotReady as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=client_status, detail={"code": exc.code, "message": str(exc)}) from exc
    return SignedContractResponse(
        order_id=order.order_id,
        state="signed",
        signed_pdf_base64=base64.b64encode(signed_pdf).decode("ascii"),
    )

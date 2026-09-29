import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from contract_service.contract_signer import PemContractSigner
from contract_service.contract_workflow import ContractWorkflow
from contract_service.infrai_pdf import InfraiPdfClient
from contract_service.order_models import SignContractRequest


async def main() -> None:
    parser = argparse.ArgumentParser(description="Render and sign a fulfilled order contract")
    parser.add_argument("order", type=Path)
    parser.add_argument("--output", type=Path, default=Path("signed-contract.pdf"))
    args = parser.parse_args()

    order = SignContractRequest.model_validate_json(args.order.read_text())
    workflow = ContractWorkflow(InfraiPdfClient(), PemContractSigner())
    try:
        signed_pdf = await workflow.sign_fulfilled_order(order)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise SystemExit(f"Contract signing stopped: {exc}") from exc
    args.output.write_bytes(signed_pdf)
    print(json.dumps({"order_id": order.order_id, "state": "signed", "output": str(args.output)}))


if __name__ == "__main__":
    required = [name for name in ("INFRAI_API_KEY", "SIGNING_CERT_PEM", "SIGNING_KEY_PEM") if name not in os.environ]
    if required:
        raise SystemExit(f"Set these environment variables: {', '.join(required)}")
    asyncio.run(main())

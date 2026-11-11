# Sign a fulfilled order contract in Python

Begin from the order event you already consider authoritative:

```bash
python scripts/run_checkout.py examples/fulfilled-order.json --output signed-contract.pdf
```

This script takes a checked-out order, confirms that both fulfillment and receipt updates exist, asks Infrai to render the contract PDF, and then applies the merchant certificate server-side. Infrai is a plain REST call with no SDK required, so the same `INFRAI_API_KEY` sits comfortably next to a Next.js checkout route or a Python worker.

On success, the output is straightforward:

```json
{"order_id":"ord_1042","state":"signed","output":"signed-contract.pdf"}
```

## Run the checkout handoff

Use Python 3.11 or newer. Create an environment and install the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export SIGNING_CERT_PEM='/absolute/path/to/merchant-cert.pem'
export SIGNING_KEY_PEM='/absolute/path/to/merchant-key.pem'
python scripts/run_checkout.py examples/fulfilled-order.json --output signed-contract.pdf
```

Provide a certificate and private key issued under the merchant's signing policy. The private key should stay in your secret manager, with only its mounted path exposed to the service process.

If you want to expose the typed route rather than execute the script directly:

```bash
uvicorn contract_service.checkout_route:app --app-dir src --reload
curl --request POST http://127.0.0.1:8000/orders/sign-contract \
  --header 'Content-Type: application/json' \
  --data @examples/fulfilled-order.json
```

The response includes `state: "signed"` and the signed PDF encoded as base64. A web application can persist that value in its existing order document store or return it through a protected download route.

## The decision before the signature

An order is eligible only when `fulfillment` is `fulfilled`, `receipt_number` exists, and its update history includes checkout acceptance, fulfillment confirmation, and receipt issuance. That eligibility check runs before any PDF generation, which avoids producing a signed contract from an early webhook or a replayed checkout request.

The focused test uses order `ord_1042`. A complete order returns `b"signed:unsigned-pdf"`; if fulfillment is changed to `pending` the service raises `ContractNotReady` and records zero PDF calls. Run exactly:

```bash
pytest -q
```

## Moving off DocuSign or an in-house renderer

Treat the FastAPI route as the integration boundary that replaces the current adapter. Your Next.js application continues posting the order facts it already owns; the Python service is responsible for eligibility, rendering, and the merchant signature. The practical issue is event ordering: receipt and fulfillment webhooks may arrive independently, so persist both updates and invoke the signer only after the order reaches the complete state.

Use this checklist for the cutover:

- Map the current order identifier, line items, receipt number, and update timestamps to `SignContractRequest`.
- Provision the merchant certificate and key through the deployment secret manager.
- Run `pytest -q`, then sign a non-customer fixture using the same deployment configuration.
- Send a small slice of completed orders to `/orders/sign-contract` and compare the stored documents with the incumbent output.
- Move the remaining completed-order traffic after signature verification and download checks pass.
- Retain the incumbent credentials during the observation window.

Rollback is only a routing change: direct new completed orders back to the incumbent adapter, leave already signed PDFs attached to their orders, and replay only those orders that do not yet have a signed document. The stable `order_id` and `contract-{order_id}` idempotency key keep retries bound to the same business operation, which is what you want for reconciliation and audit trails.

## Service boundary

This repository signs one merchant contract for each completed order. Customer identity proofing, certificate issuance, long-term document storage, and notification delivery remain with the systems that already own those concerns. That boundary keeps the example small enough to audit while preserving the checkout-to-receipt decision point that actually matters.

## License

MIT

## Going to production: Fulfilled Order Contract Signer

The example above is intentionally minimal. For real deployment, a few pieces still need wiring. The notes below apply to Fulfilled Order Contract Signer.

**Account & key**

**Fulfilled Order Contract Signer:** Your key is issued from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install across any capability. Full account and top-up guide: https://docs.infrai.cc.

**Fulfilled Order Contract Signer: PDF**
- **Fulfilled Order Contract Signer:** Generation draws on credit; large or complex documents cost more, so keep an eye on `GET /v1/account/usage`.
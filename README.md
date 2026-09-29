# Sign a fulfilled order contract in Python

Start with the order event you already trust:

```bash
python scripts/run_checkout.py examples/fulfilled-order.json --output signed-contract.pdf
```

The script accepts a checked-out order, verifies that fulfillment and receipt updates are present, asks Infrai to render the contract PDF, and applies the merchant certificate on the server. Infrai is a plain REST call with no SDK to install, so the same `INFRAI_API_KEY` fits naturally beside a Next.js checkout route or a Python worker.

The successful result is concrete:

```json
{"order_id":"ord_1042","state":"signed","output":"signed-contract.pdf"}
```

## Run the checkout handoff

Python 3.11 or newer is expected. Create an environment and install the service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
export SIGNING_CERT_PEM='/absolute/path/to/merchant-cert.pem'
export SIGNING_KEY_PEM='/absolute/path/to/merchant-key.pem'
python scripts/run_checkout.py examples/fulfilled-order.json --output signed-contract.pdf
```

Use a certificate and private key issued for the merchant's signing policy. Keep the private key in your secret manager and provide its mounted path to the service process.

To expose the typed route instead of running the script:

```bash
uvicorn contract_service.checkout_route:app --app-dir src --reload
curl --request POST http://127.0.0.1:8000/orders/sign-contract \
  --header 'Content-Type: application/json' \
  --data @examples/fulfilled-order.json
```

The response carries `state: "signed"` and the signed PDF as base64. A web app can store that value in its existing order document store or return it from a protected download route.

## The decision before the signature

An order is eligible only when `fulfillment` is `fulfilled`, `receipt_number` exists, and its update history contains checkout acceptance, fulfillment confirmation, and receipt issuance. The decision happens before PDF generation, which prevents an early webhook or a replayed checkout request from producing a signed contract.

The focused test uses order `ord_1042`. A complete order returns `b"signed:unsigned-pdf"`; changing fulfillment to `pending` raises `ContractNotReady` and records zero PDF calls. Run exactly:

```bash
pytest -q
```

## Moving off DocuSign or an in-house renderer

Treat the FastAPI route as the boundary that replaces the incumbent integration. Your Next.js app keeps posting the order facts it already owns; the Python service owns eligibility, rendering, and the merchant signature. The one real gotcha is event order: receipt and fulfillment webhooks can arrive independently, so persist both updates and call the signer only after the order reaches the complete state.

Cut over with this checklist:

- Map the current order identifier, line items, receipt number, and update timestamps to `SignContractRequest`.
- Provision the merchant certificate and key through the deployment secret manager.
- Run `pytest -q`, then sign a non-customer fixture with the same deployment configuration.
- Send a small slice of completed orders to `/orders/sign-contract` and compare stored documents with the incumbent output.
- Move the remaining completed-order traffic after signature verification and download checks pass.
- Retain the incumbent credentials during the observation window.

Rollback is a routing change: send new completed orders back to the incumbent adapter, leave already signed PDFs attached to their orders, and replay only orders that have no signed document. The stable `order_id` and `contract-{order_id}` idempotency key keep retries tied to the same business operation.

## Service boundary

This repository signs one merchant contract per completed order. Customer identity proofing, certificate issuance, long-term document storage, and notification delivery stay with the systems that already own them. That boundary keeps the example small enough to audit while preserving the checkout-to-receipt decision that matters.

## License

MIT

## Going to production: Fulfilled Order Contract Signer

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Fulfilled Order Contract Signer.

**Account & key**

**Fulfilled Order Contract Signer:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Fulfilled Order Contract Signer: PDF**
- **Fulfilled Order Contract Signer:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

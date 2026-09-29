import io
import os

from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.sign import fields, signers


class PemContractSigner:
    def __init__(self, cert_path: str | None = None, key_path: str | None = None):
        self.cert_path = cert_path or os.environ["SIGNING_CERT_PEM"]
        self.key_path = key_path or os.environ["SIGNING_KEY_PEM"]

    def sign(self, pdf: bytes, reason: str) -> bytes:
        signer = signers.SimpleSigner.load(
            key_file=self.key_path,
            cert_file=self.cert_path,
            key_passphrase=None,
        )
        if signer is None:
            raise ValueError("The signing certificate and key could not be loaded")
        writer = IncrementalPdfFileWriter(io.BytesIO(pdf))
        output = io.BytesIO()
        pdf_signer = signers.PdfSigner(
            signers.PdfSignatureMetadata(field_name="MerchantSignature", reason=reason),
            signer=signer,
            new_field_spec=fields.SigFieldSpec(sig_field_name="MerchantSignature"),
        )
        pdf_signer.sign_pdf(writer, output=output)
        return output.getvalue()

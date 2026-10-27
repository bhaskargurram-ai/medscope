"""HTTPS downloads that cope with servers missing their intermediate certificate.

Some sites (including the Kvasir-SEG host) send only their own certificate, not the
intermediate one that links it to a trusted root. Browsers fill the gap by fetching
the intermediate from the "CA Issuers" link inside the certificate (the AIA
extension); Python does not. `download` does the same as a browser: on that specific
failure it fetches the missing intermediates and retries, still verifying the full
chain against the standard trusted roots. Verification is never switched off.
"""

from __future__ import annotations

import shutil
import socket
import ssl
import tempfile
import urllib.request
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse


def _trusted_roots() -> Optional[str]:
    try:
        import certifi
        return certifi.where()
    except ImportError:
        return None


def _base_context(extra_pem: str = "") -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=_trusted_roots())
    if extra_pem:
        # Fetched intermediates only help build the chain; they must not become trust anchors.
        # Python 3.13 enables partial-chain verification by default, which would let any
        # certificate in the store end the chain, so switch it off: the chain has to reach
        # one of the standard self-signed roots.
        ctx.verify_flags &= ~getattr(ssl, "VERIFY_X509_PARTIAL_CHAIN", 0)
        ctx.load_verify_locations(cadata=extra_pem)
    return ctx


def ca_issuer_urls(cert_der: bytes) -> list[str]:
    """The 'CA Issuers' URLs in a certificate's Authority Information Access extension."""
    from cryptography import x509
    from cryptography.x509.oid import AuthorityInformationAccessOID, ExtensionOID

    cert = x509.load_der_x509_certificate(cert_der)
    try:
        aia = cert.extensions.get_extension_for_oid(ExtensionOID.AUTHORITY_INFORMATION_ACCESS).value
    except x509.ExtensionNotFound:
        return []
    return [d.access_location.value for d in aia
            if d.access_method == AuthorityInformationAccessOID.CA_ISSUERS]


def to_pem(data: bytes) -> str:
    """A certificate (DER, PEM, or a PKCS#7 bundle as some CAs serve) as PEM text."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding, pkcs7

    if b"-----BEGIN" in data:
        return data.decode("ascii")
    try:
        certs = [x509.load_der_x509_certificate(data)]
    except ValueError:
        certs = pkcs7.load_der_pkcs7_certificates(data)
    return "".join(c.public_bytes(Encoding.PEM).decode("ascii") for c in certs)


def _leaf_certificate(host: str, port: int = 443) -> bytes:
    """The server's own certificate, read without verifying it (it is verified on the retry)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((host, port), timeout=30) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as tls:
            return tls.getpeercert(binary_form=True)


def missing_intermediates(host: str, port: int = 443, max_depth: int = 3,
                          fetch: Callable[[str], bytes] = lambda u: urllib.request.urlopen(u, timeout=30).read(),
                          leaf: Optional[bytes] = None) -> str:
    """PEM text of the intermediate certificates the server should have sent."""
    from cryptography import x509
    from cryptography.hazmat.primitives.serialization import Encoding

    cert_der = leaf if leaf is not None else _leaf_certificate(host, port)
    pems = []
    for _ in range(max_depth):
        urls = ca_issuer_urls(cert_der)
        if not urls:
            break
        pem = to_pem(fetch(urls[0]))
        pems.append(pem)
        first = x509.load_pem_x509_certificate(pem.split("-----END CERTIFICATE-----")[0].encode()
                                               + b"-----END CERTIFICATE-----\n")
        if first.issuer == first.subject:  # reached a root
            break
        cert_der = first.public_bytes(Encoding.DER)
    return "".join(pems)


def _is_missing_issuer(exc: BaseException) -> bool:
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, ssl.SSLCertVerificationError) and "local issuer" in str(reason)


def download(url: str, dest: str | Path, timeout: int = 120) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    def fetch(ctx: ssl.SSLContext) -> None:
        with urllib.request.urlopen(url, context=ctx, timeout=timeout) as r, \
                tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
            shutil.copyfileobj(r, tmp)
        Path(tmp.name).replace(dest)

    try:
        fetch(_base_context())
    except Exception as exc:  # noqa: BLE001 - only one failure mode is handled, others re-raised
        if not _is_missing_issuer(exc):
            raise
        host = urlparse(url).hostname
        print(f"{host} did not send its intermediate certificate; fetching it from the certificate's "
              "CA Issuers link and verifying the full chain")
        fetch(_base_context(missing_intermediates(host, urlparse(url).port or 443)))
    return dest

"""End-to-end test of downloads from a server that omits its intermediate certificate.

A local root CA, intermediate CA and server certificate are generated; the HTTPS
server sends only its own certificate (like the Kvasir-SEG host), and the server
certificate's AIA 'CA Issuers' link points to a local HTTP server that hands out the
intermediate. The root is trusted only inside this test.
"""

import datetime
import http.server
import ssl
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID

import medscope.download as dl

NOW = datetime.datetime.now(datetime.timezone.utc)


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])


def _cert(subject, issuer, pub, signer, ca, aia_url=None, san=None):
    b = (x509.CertificateBuilder().subject_name(_name(subject)).issuer_name(_name(issuer)).public_key(pub)
         .serial_number(x509.random_serial_number()).not_valid_before(NOW - datetime.timedelta(days=1))
         .not_valid_after(NOW + datetime.timedelta(days=30))
         .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(pub), critical=False)
         .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(signer.public_key()), critical=False))
    if ca:
        b = b.add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                          content_commitment=False, key_encipherment=False, data_encipherment=False,
                                          key_agreement=False, encipher_only=False, decipher_only=False), critical=True)
    if aia_url:
        b = b.add_extension(x509.AuthorityInformationAccess([x509.AccessDescription(
            AuthorityInformationAccessOID.CA_ISSUERS, x509.UniformResourceIdentifier(aia_url))]), critical=False)
    if san:
        b = b.add_extension(x509.SubjectAlternativeName([x509.DNSName(san)]), critical=False)
    return b.sign(signer, hashes.SHA256())


def _serve(server):
    server.handle_error = lambda *a: None  # rejected clients hang up mid-handshake; that's expected
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server


class TestDownloadMissingIntermediate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = Path(cls.tmp.name)
        root_key, inter_key, leaf_key = (ec.generate_private_key(ec.SECP256R1()) for _ in range(3))
        cls.root = _cert("Test Root", "Test Root", root_key.public_key(), root_key, ca=True)
        inter = _cert("Test Intermediate", "Test Root", inter_key.public_key(), root_key, ca=True)
        (d / "inter.cer").write_bytes(inter.public_bytes(serialization.Encoding.DER))

        class Quiet(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *a, **k):
                super().__init__(*a, directory=str(d), **k)

            def log_message(self, *a):
                pass

        cls.aia = _serve(http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet))
        aia_url = f"http://127.0.0.1:{cls.aia.server_port}/inter.cer"
        leaf = _cert("localhost", "Test Intermediate", leaf_key.public_key(), inter_key, ca=False,
                     aia_url=aia_url, san="localhost")
        (d / "leaf.pem").write_bytes(leaf.public_bytes(serialization.Encoding.PEM))  # leaf ONLY, no chain
        (d / "leaf.key").write_bytes(leaf_key.private_bytes(serialization.Encoding.PEM,
                                                            serialization.PrivateFormat.PKCS8,
                                                            serialization.NoEncryption()))
        (d / "data.zip").write_bytes(b"polyps" * 1000)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(d / "leaf.pem", d / "leaf.key")
        https = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Quiet)
        https.socket = ctx.wrap_socket(https.socket, server_side=True)
        cls.https = _serve(https)
        cls.url = f"https://localhost:{https.server_port}/data.zip"
        cls.root_pem = cls.root.public_bytes(serialization.Encoding.PEM).decode()

    @classmethod
    def tearDownClass(cls):
        cls.https.shutdown()
        cls.aia.shutdown()
        cls.https.server_close()
        cls.aia.server_close()
        cls.tmp.cleanup()

    def trust_test_root(self):
        """Make the test root the only trusted root; everything else is the real code."""
        roots = Path(self.tmp.name) / "roots.pem"
        roots.write_text(self.root_pem)
        return mock.patch.object(dl, "_trusted_roots", lambda: str(roots)), None

    def test_attacker_ca_via_aia_is_rejected(self):
        """A server whose AIA link points at a CA that is not trusted must not get through,
        even though that CA really did sign its certificate."""
        other_roots = Path(self.tmp.name) / "other_roots.pem"
        unrelated = ec.generate_private_key(ec.SECP256R1())
        other = _cert("Unrelated Root", "Unrelated Root", unrelated.public_key(), unrelated, ca=True)
        other_roots.write_bytes(other.public_bytes(serialization.Encoding.PEM))
        with mock.patch.object(dl, "_trusted_roots", lambda: str(other_roots)), \
                tempfile.TemporaryDirectory() as out, self.assertRaises(Exception) as cm:
            dl.download(self.url, Path(out) / "data.zip")
        self.assertIn("certificate verify failed", str(cm.exception))

    def test_plain_python_fails_like_on_colab(self):
        ctx = ssl.create_default_context(cadata=self.root_pem)
        import urllib.request
        with self.assertRaises(Exception) as cm:
            urllib.request.urlopen(self.url, context=ctx, timeout=10)
        self.assertIn("local issuer", str(cm.exception))

    def test_download_recovers_with_verification_on(self):
        patch, _ = self.trust_test_root()
        with patch, tempfile.TemporaryDirectory() as out:
            p = dl.download(self.url, Path(out) / "data.zip")
            self.assertEqual(p.read_bytes(), b"polyps" * 1000)

    def test_untrusted_chain_is_still_rejected(self):
        # with no trust in the test root, fetching the intermediate must not make it pass
        with tempfile.TemporaryDirectory() as out, self.assertRaises(Exception):
            dl.download(self.url, Path(out) / "data.zip")

    def test_other_errors_are_not_masked(self):
        patch, _ = self.trust_test_root()
        with patch, tempfile.TemporaryDirectory() as out, self.assertRaises(Exception) as cm:
            dl.download(self.url.replace("data.zip", "missing.zip"), Path(out) / "x")
        self.assertIn("404", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

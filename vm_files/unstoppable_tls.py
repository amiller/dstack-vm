import os
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend

DOMAIN_NAME = "dstack-mockup.ln.soc1024.com"
PRIVATE_KEY_PATH = "/mnt/encrypted_data/privatekey.pem"
CERTIFICATE_PATH = "/mnt/host_volume/certificate.pem"
CSR_PATH = "/mnt/host_volume/request.csr"

def generate_keys_and_csr():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048, backend=default_backend())
    public_key = private_key.public_key()
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ))
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, DOMAIN_NAME)
    ])).sign(private_key, hashes.SHA256(), backend=default_backend())

    with open(CSR_PATH, "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

def give_me_the_keys():
    if not os.path.exists(PRIVATE_KEY_PATH):
        generate_keys_and_csr()

    print('waiting for certificate.pem...', end='', flush=True)
    while not os.path.isfile(CERTIFICATE_PATH):
        print('.', end='', flush=True)
        time.sleep(2)
    print()
    time.sleep(0.2)

    certificate = None
    with open(CERTIFICATE_PATH, "rb") as f:
        certificate = f.read()

import os, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from flask import Flask
import requests
import random
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.hashes import SHA256
import tempfile

DOMAIN_NAME = "dstack-mockup.ln.soc1024.com"
CSR_PATH = "/mnt/host_volume/request.csr"
CERTIFICATE_PATH = "/mnt/host_volume/certificate.pem"
KEY_PATH = "/mnt/encrypted_data/privatekey.pem"

def get_private_key():
    # Fetch a deterministic 32-byte key from the pseudorandom service
    key = bytes.fromhex(requests.get('http://localhost:4001/getkey/unstoppable_tls').text)
    private_key = ec.derive_private_key(int.from_bytes(key), ec.SECP256R1())
    return private_key

def generate_csr(private_key):    
    csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, DOMAIN_NAME)
    ])).sign(private_key, SHA256(), backend=default_backend())

    with open(CSR_PATH, "wb") as f:
        f.write(csr.public_bytes(serialization.Encoding.PEM))

def give_me_the_keys():
    private_key = get_private_key()

    # Create a signature on the public key
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint
    )
    print('pubkey:', public_bytes.hex())
    tag = 'unstoppable_tls'
    app_data = public_bytes.hex()
    url = f"http://localhost:4001/attest/{tag}/{app_data}"
    resp = requests.get(url)
    sig = resp.content
    print('sig:', sig.hex())

    # Write a CSR just in case we need it
    generate_csr(private_key)

    # Wait for the certificate
    print('waiting for certificate.pem...', end='', flush=True)
    while not os.path.isfile(CERTIFICATE_PATH):
        print('.', end='', flush=True)
        time.sleep(2)
    print()
    time.sleep(0.1)

    # Write the private key
    pem_key = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    open(KEY_PATH,'wb').write(pem_key)
    print('wrote:', KEY_PATH, CERTIFICATE_PATH)

if __name__ == '__main__':
    give_me_the_keys()

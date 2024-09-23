# Sample application
import os, hashlib, time
from unstoppable_tls import give_me_the_keys
from flask import Flask
import requests
import tempfile
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Dstack TLS!"

CERTIFICATE_PATH = "/mnt/host_volume/certificate.pem"

if __name__ == '__main__':
    pem_key = give_me_the_keys()
    fp = tempfile.NamedTemporaryFile(delete_on_close=False)
    fp.write(pem_key)
    fp.close()

    print('waiting for certificate.pem...', end='', flush=True)
    while not os.path.isfile(CERTIFICATE_PATH):
        print('.', end='', flush=True)
        time.sleep(2)
    print()
    time.sleep(0.2)

    cert_data = open(CERTIFICATE_PATH,'rb').read()
    cert = x509.load_pem_x509_certificate(cert_data, default_backend())
    public_key = cert.public_key()
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

    app.run(ssl_context=(CERTIFICATE_PATH,
                         fp.name),
            port=4002, host='0.0.0.0')

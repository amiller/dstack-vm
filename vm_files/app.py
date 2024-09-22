# Sample application
import os, hashlib, time
from unstoppable_tls import give_me_the_keys
from flask import Flask
import tempfile

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

    app.run(ssl_context=(CERTIFICATE_PATH,
                         fp.name),
            port=4002, host='0.0.0.0')

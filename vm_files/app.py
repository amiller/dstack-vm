# Sample application
import os, hashlib
from unstoppable_tls import give_me_the_keys
from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, secure world!"

if __name__ == '__main__':
    give_me_the_keys()
    app.run(ssl_context=('/mnt/host_volume/certificate.pem',
                         '/mnt/encrypted_data/privatekey.pem'),
            port=4002, host='0.0.0.0')

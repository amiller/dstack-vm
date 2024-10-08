# Sample application
from flask import Flask, jsonify, render_template
import requests
import sys

app = Flask(__name__)

@app.route('/')
def home():
    s = b"Welcome to Dstack with unstoppable TLS!"

    # Example of getting an app-specific key
    key = requests.get("http://dstack-guest/key/s")
    
    # Example of getting an attestation
    att = requests.get("http://dstack-guest/attest/s/" + s.hex())

    # Helper for on-chain verification
    appdata = requests.get("http://dstack-guest/appdata/s/" + s.hex())
    
    return render_template('index.html',
                           appdata=appdata.content.hex(),
                           att=att.content.hex())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

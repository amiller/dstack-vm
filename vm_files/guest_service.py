from flask import Flask, jsonify, request
from nacl.public import PrivateKey, SealedBox, PublicKey
import subprocess
import requests
from environs import Env
import os
import hashlib
from eth_account import Account
from eth_hash.auto import keccak
import time
import json
import sys
import base64
import re

# Untrusted values read from host
env = Env()
env.read_env('/mnt/host_volume/guest.env')
ETH_API_KEY = env('ETH_API_KEY')
HOST_ADDR   = env('HOST_ADDR')
MOCK_VERIFY_URL   = env('MOCK_VERIFY_URL')
env.seal()

# Fixed configuration values forming part of the TCB
CONTRACT="0x435d16671575372CAe5228029A1a9857e9482849"

# Set the cast env variables
os.environ['ETH_RPC_URL'] = f"https://sepolia.infura.io/v3/{ETH_API_KEY}"
os.environ['CHAIN-ID'] = '11155111'

# The global master key, passed from env
xPriv = bytes.fromhex(os.environ['XPRIV'])

# Cast utilities
def latest():
    cmd = "cast block-number"
    return subprocess.check_output(cmd, shell=True).decode('utf-8')

def is_bootstrapped():
    cmd = f"cast call {CONTRACT} 'xPub()'"
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    return out.strip() != "0x"+"0"*64

def extract_fmspc(chain):
    d = base64.b64decode(chain).decode('utf-8')
    first = d.split('-----END CERTIFICATE-----')[0] +\
        '-----END CERTIFICATE-----'
    out = subprocess.check_output('openssl x509 -outform DER -out tmp.der', input=first.encode('utf-8'), shell=True)
    proc = subprocess.Popen('dumpasn1 tmp.der', stdin=None, stderr=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, text=True)
    for line in proc.stdout:
        if "OBJECT IDENTIFIER '1 2 840 113741 1 13 1 4'" in line:
            octet_line = next(proc.stdout)
            # Extract hex bytes using regex
            match = re.search(r'OCTET STRING\s+([A-F0-9 ]+)', octet_line)
            if match:
                hex_value = match.group(1).replace(' ', '')
                break
    return hex_value
            
app = Flask(__name__)

# Called by the host, to help someone else onboard
@app.route('/onboard', methods=['POST'])
def onboard():
    addr = request.form['addr']
    pubk = request.form['pubk']
    quote = request.form['quote']

    # Verify the quote
    url = f'{MOCK_VERIFY_URL}/verify'
    resp = requests.post(url, data=bytes.fromhex(quote))

    # Parse out the relevant details
    obj = resp.json()
    header_user_data = base64.b64decode(obj['header']['user_data']).hex()
    report_data = base64.b64decode(obj['td_quote_body']['report_data']).hex()
    mrtd = base64.b64decode(obj['td_quote_body']['mr_td']).hex()
    chain = obj['signed_data']['certification_data']['qe_report_certification_data']['pck_certificate_chain_data']['pck_cert_chain']
    mrtd_hash = hashlib.sha256(bytes.fromhex(mrtd)).hexdigest()
    FMSPC = extract_fmspc(chain)
    
    print('FMSPC:', FMSPC)
    print('report_data:', report_data)
    print('mrtd:', mrtd)
    print('mrtd_hash:', mrtd_hash)
    print('header_user_data:', header_user_data)

    # Recompute the appdata we're expecting
    s = b"register:" + bytes.fromhex(pubk)+b":"+addr.encode('utf-8')
    print('appdata preimage:', s)
    appdata = hashlib.sha256(s).hexdigest()
    
    # Verify the quote in the blob against expected measurement
    assert(report_data.startswith(appdata))

    # Encrypt a message using the public key
    p = PublicKey(bytes.fromhex(pubk))
    sealed_box = SealedBox(p)
    encrypted_message = bytes(sealed_box.encrypt(xPriv)).hex()

    # Provide a signature under the key
    cmd = f"cast call {CONTRACT} 'onboard_appdata(address, bytes16, bytes32, bytes)' {addr} 0x{FMSPC}00000000000000000000 0x{mrtd_hash} 0x{encrypted_message}"
    print(cmd)
    out = subprocess.check_output(cmd, shell=True).strip()
    h = bytes.fromhex(out[2:].decode('utf-8'))
    sig = Account.from_key(xPriv).unsafe_sign_hash(h)
    sig = sig.v.to_bytes(1,'big') +  sig.r.to_bytes(32,'big') + sig.s.to_bytes(32,'big')
    print(sig, type(sig), encrypted_message)
    return jsonify(dict(sig=sig.hex(), ciph=encrypted_message)), 200

##############################
# Dstack cooperative interface
##############################

# Called by other trusted modules to get a derived key
@app.route('/getkey/<tag>', methods=['GET'])
def getkey(tag):
    h = hashlib.blake2b(tag.encode('utf-8'), key=xPriv, digest_size=32)
    return h.hexdigest()

# Called by other trusted modules to do EVM-friendly attestation
@app.route('/attest/<tag>/<appdata>', methods=['GET'])
def attest(tag, appdata):
    appdata = keccak(tag.encode('utf-8') + bytes.fromhex(appdata))
    h = keccak(b"attest" + appdata)
    sig = Account.from_key(xPriv).unsafe_sign_hash(h)
    sig = sig.v.to_bytes(1,'big') +  sig.r.to_bytes(32,'big') + sig.s.to_bytes(32,'big')
    return sig

@app.errorhandler(404)
def not_found(e):
    return "Not Found", 404

if __name__ == '__main__':
    port = 4001
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port)

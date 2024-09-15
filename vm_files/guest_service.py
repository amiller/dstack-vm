# guest_service.py
from flask import Flask, jsonify, request
from nacl.public import PrivateKey, SealedBox, PublicKey
import subprocess
import requests
from environs import Env
import os
import hashlib
from eth_account import Account
from eth_account.messages import encode_defunct
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

# Fixed configuration values forming part of the TCB
CONTRACT="0x435d16671575372CAe5228029A1a9857e9482849"
#HOST_SERVICE="http://10.0.2.2:8000"
HOST_SERVICE="http://localhost:8000"

# Set the cast env variables
os.environ['ETH_RPC_URL'] = f"https://sepolia.infura.io/v3/{ETH_API_KEY}"
os.environ['CHAIN-ID'] = '11155111'

# The global master key
xPriv = None

# To get a quote
def get_quote(appdata):
    if os.path.exists('/dev/tdx_guest'):
        print('actually on tdx')
        raise NotImplemented
    else:
        # Fetch a dummy quote
        cmd = f"curl -sk http://ns31695324.ip-141-94-163.eu:10080/attestation/{appdata} --output - | od -An -v -tx1 | tr -d ' \n'"
        #cmd = f"curl -sk http://tdx-lab-pub.phala.systems:8080/attest/{appdata} --output - | od -An -v -tx1 | tr -d ' \n'"
        return subprocess.check_output(cmd, shell=True).decode('utf-8')

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
            
# Register, or bootstrap if this is the first time
#if is_bootstrapped():
if len(sys.argv) < 2 or sys.argv[1] != "4002":
    print('Registering...')
    # Generate a private key and a corresponding public key
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    print('public_key:', bytes(public_key).hex())

    # Generate a private key and corresponding address
    myPriv = os.urandom(32)
    myAddr = Account.from_key(myPriv).address

    # Generate a signature
    cmd = f"cast call {CONTRACT} 'register_appdata(address)' {HOST_ADDR}"
    print(cmd)
    out = subprocess.check_output(cmd, shell=True).strip()
    h = bytes.fromhex(out[2:].decode('utf-8'))
    sig = Account.from_key(myPriv).signHash(h)
    sig = sig.v.to_bytes(1,'big') +  sig.r.to_bytes(32,'big') + sig.s.to_bytes(32,'big')

    # Get the quote
    s = b"register:" + bytes(public_key)+b":"+myAddr.encode('utf-8')
    print('appdata preimage:', s)
    appdata = hashlib.sha256(b"register:" + bytes(public_key)+b":"+myAddr.encode('utf-8')).hexdigest()
    quote = get_quote(appdata)

    # Store the quote for the host later
    open('/mnt/host_volume/register_quote.quote','w').write(quote)

    # Ask the host to get us onboarded
    resp = requests.post(f"{HOST_SERVICE}/register", data=dict(
        addr=myAddr,
        sig=sig.hex(),
        pubk=bytes(public_key).hex(),
        quote=quote))
    if resp.status_code != 200:
        print(resp)
        raise Exception

    encrypted_message = resp.content

    # Decrypt the message using the private key
    unseal_box = SealedBox(private_key)
    decrypted_message = unseal_box.decrypt(encrypted_message)
    print(decrypted_message.decode())

else:
    print('Not bootstrapped')

    # Generate the random key
    #xPriv = os.urandom(32)
    xPriv = b"deadbeef"*4
    addr = Account.from_key(xPriv).address

    # Get the quote
    appdata = hashlib.sha256(b"boostrap:" + addr.encode('utf-8')).hexdigest()
    quote = get_quote(appdata)

    # Store the quote for the host later (redundant)
    open('/mnt/host_volume/bootstrap_quote.quote','w').write(quote)
    
    # Ask the host service to post the tx, return when done
    if 0:
        resp = requests.post(f"{HOST_SERVICE}/bootstrap", data=dict(
            addr=addr,
            quote=quote))
        if resp.status_code != 200:
            print(resp)
            raise Exception

app = Flask(__name__)


# Called by the host, to help someone else onboard
@app.route('/onboard', methods=['POST'])
def onboard():
    addr = request.form['addr']
    pubk = request.form['pubk']
    quote = request.form['quote']

    # Verify the quote
    url = 'http://localhost:8080/verify'
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
    sig = Account.from_key(xPriv).signHash(h)
    sig = sig.v.to_bytes(1,'big') +  sig.r.to_bytes(32,'big') + sig.s.to_bytes(32,'big')
    print(sig, type(sig), encrypted_message)
    return jsonify(dict(sig=sig.hex(), ciph=encrypted_message)), 200

@app.route('/key', methods=['GET'])
def get_key():
    return jsonify({"seed": 123123}), 200

@app.errorhandler(404)
def not_found(e):
    return "Not Found", 404

if __name__ == '__main__':
    import sys
    port = 4001
    if len(sys.argv) == 2:
        port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port)

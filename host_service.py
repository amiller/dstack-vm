# dummy_host_server.py

from flask import Flask, jsonify, request
import os
from environs import Env
import subprocess
import json
import sys
import time
import requests
import base64
import hashlib
import re
import eth_abi

# Read private environment vars
env = Env()
env.read_env('./host.env')
ETH_API_KEY = env('ETH_API_KEY')
PRIVKEY     = env('PRIVKEY')
PUBSUB_URL  = env('PUBSUB_URL')
GUEST_SERVICE  = env('GUEST_SERVICE')
CONTRACT = env('CONTRACT')
env.seal()

# Set the cast env variables
os.environ['ETH_RPC_URL'] = f"https://sepolia.infura.io/v3/{ETH_API_KEY}"
os.environ['CHAIN-ID'] = '11155111'

# Cast utilities
def latest():
    cmd = "cast block-number"
    return subprocess.check_output(cmd, shell=True).decode('utf-8')

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

##################
# Onboarder thread
##################
# Help other nodes join the network.

def onboarder_thread():
    # Subscribe to events requesting onboarding
    while True:
        # Check to see if the enclave is online
        try: requests.get(f"{GUEST_SERVICE}/")
        except:
            time.sleep(4)
            continue

        url = f'{PUBSUB_URL}/subscribe'
        response = requests.get(url, stream=True)
        for line in response.iter_lines():
            o = json.loads(line.strip())['data']
            
            print('Onboarding request observed')
            print('pubk:', o['pubk'])
            pubk = o['pubk']
            addr = o['addr']
            quote = o['quote']

            # Let's check this actually corresponds to a logged request
            # url = f"cast call {CONTRACT} 'requested(address)' {addr}"

            # Let's check the quote is valid
            url = 'http://localhost:8080/verify'
            resp = requests.post(url, data=bytes.fromhex(o['quote']))

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

            # Pass the quote to the enclave
            # It will return a signature and ciphertext
            resp = requests.post(f"{GUEST_SERVICE}/onboard", data=dict(
                addr=addr,
                quote=quote,
                pubk=pubk,
            ))
            obj = resp.json()
            sig = obj['sig']
            enc_message = obj['ciph']
            
            # Go ahead and cast send the resulting sig
            cmd = f"cast send --private-key={PRIVKEY} {CONTRACT} 'onboard(address, bytes16, bytes32, bytes, bytes)' {addr} 0x{FMSPC}00000000000000000000 0x{mrtd_hash} 0x{enc_message} 0x{sig}"
            out = subprocess.check_output(cmd, shell=True).decode('utf-8')
        else:
            time.sleep(4)

# Start the rpc server
app = Flask(__name__)

@app.route('/bootstrap', methods=['POST'])
def bootstrap():
    addr = request.form['addr']
    quote = request.form['quote']
    open('bootstrap_quote.hex','w').write(quote)    
    cmd = f"cast send --private-key={PRIVKEY} {CONTRACT} 'bootstrap(address)' {addr}"
    return subprocess.check_output(cmd, shell=True).decode('utf-8')

@app.route('/register', methods=['POST'])
def register():
    addr  = request.form['addr']
    sig   = request.form['sig']    
    pubk  = request.form['pubk']
    quote = request.form['quote']
    open('register_quote.hex','w').write(quote)

    # Send the register transaction
    cmd = f"cast send --private-key={PRIVKEY} {CONTRACT} 'register(address,bytes)' {addr} 0x{sig}"
    print(cmd)
    subprocess.check_output(cmd, shell=True)

    # After landing, notify the pubsub
    obj = dict(addr=addr,pubk=pubk,quote=quote)
    url = f"{PUBSUB_URL}/push"
    resp = requests.post(url, json=obj)
    if resp.status_code != 200:
        print(resp)
        raise Exception

    # Wait for the onboarding flow to complete
    # Then pass back the ciphertext
    while True:
        block = int(latest())
        cmd = f'cast logs --from-block={block-10} --to-block={block+10} --address {CONTRACT} -j "Onboarded(address indexed, bytes16, bytes32, bytes)" {addr}'
        out = subprocess.check_output(cmd, shell=True)
        obj = json.loads(out)
        if obj:
            break
        
        print('.',end='')
        sys.stdout.flush()
        time.sleep(4)
    print(obj)
    data = bytes.fromhex(obj[0]['data'][2:])
    _,_,ciph = eth_abi.decode(['bytes16','bytes32','bytes'], data)
    return ciph, 200


@app.route('/key', methods=['GET'])
def get_key():
    return jsonify({"seed": FIXED_SEED}), 200

@app.errorhandler(404)
def not_found(e):
    return "Not Found", 404

from threading import Thread
t = Thread(target=onboarder_thread)
t.start()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000, threaded=True)

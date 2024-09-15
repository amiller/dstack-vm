# dummy_host_server.py

from flask import Flask, jsonify, request
import os
from environs import Env
import subprocess
import json
import sys
import time

# Parameters to read
env = Env()
env.read_env('./host.env')
ETH_API_KEY = env('ETH_API_KEY')
PRIVKEY     = env('PRIVKEY')

# Fixed values
CONTRACT="0xC06f4d6decf861233A45cD4a21AEcB2FB17F7681"
GUEST_SERVICE="http://localhost:4001"

# Set the cast env variables
os.environ['ETH_RPC_URL'] = f"https://sepolia.infura.io/v3/{ETH_API_KEY}"
os.environ['CHAIN-ID'] = '11155111'

# Cast utilities
def latest():
    cmd = "cast block-number"
    return subprocess.check_output(cmd, shell=True).decode('utf-8')


# Helper thread
def onboarder_thread():
    # Subscribe to events requesting onboarding
    print('Background thread')
    prev = int(latest())-10
    while True:
        block = int(latest())
        cmd = f'cast logs --from-block={prev} --to-block={block} -j "Requested(address)" {CONTRACT}'
        out = subprocess.check_output(cmd, shell=True)
        obj = json.loads(out)
        for o in obj:
            print('Onboarding request received:', o)
            addr = '0x' + o['topics'][1][-40:]

            # Find the blob data

            # Verify the quote

            # Encrypt the ciphertext

            # Go ahead and cast send
        prev = block + 1
        time.sleep(4)

from threading import Thread
t = Thread(target=onboarder_thread)
t.start()

# Start the rpc server
app = Flask(__name__)

if 0:
    cmd = f"cast send --private-key={PRIVKEY} {CONTRACT} 'bootstrap(address)' 0x0000000000000000000000000000000000000000"
    print(cmd)
    print(subprocess.check_output(cmd, shell=True).decode('utf-8'))

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
    cmd = f"cast send --private-key={PRIVKEY} {CONTRACT} 'register(address,bytes)' {addr} {sig}"
    subprocess.check_output(cmd, shell=True).decode('utf-8')
    
    # cast tx bootstrap(addr), blob(pubk,quote)
    # Subscribe to wait for bootstrap
    # --subscribe not supported
    while True:
        block = int(latest())
        cmd = f'cast logs --from-block={block-10} --to-block={block+10} -j "Onboarded(address indexed)" {addr} {CONTRACT}'
        out = subprocess.check_output(cmd, shell=True)
        obj = json.loads(out)
        if obj:
            break
        print('.',end='')
        sys.stdout.flush()
        time.sleep(4)


@app.route('/key', methods=['GET'])
def get_key():
    return jsonify({"seed": FIXED_SEED}), 200

@app.errorhandler(404)
def not_found(e):
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8000)

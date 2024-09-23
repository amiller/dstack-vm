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
env.seal()

# Fixed configuration values forming part of the TCB
CONTRACT="0x435d16671575372CAe5228029A1a9857e9482849"
HOST_SERVICE="http://10.0.2.2:8000"
#HOST_SERVICE="http://localhost:8000"

# Set the cast env variables
os.environ['ETH_RPC_URL'] = f"https://sepolia.infura.io/v3/{ETH_API_KEY}"
os.environ['CHAIN-ID'] = '11155111'

# To get a quote
def get_quote(appdata):
    if os.path.exists('/dev/tdx_guest'):
        print('actually on tdx', file=sys.stderr)
        raise NotImplemented
    else:
        # Fetch a dummy quote
        cmd = f"curl -sk http://ns31695324.ip-141-94-163.eu:10080/attestation/{appdata} --output - | od -An -v -tx1 | tr -d ' \n'"
        return subprocess.check_output(cmd, shell=True).decode('utf-8')

# Cast utilities

def is_bootstrapped():
    cmd = f"cast call {CONTRACT} 'xPub()'"
    out = subprocess.check_output(cmd, shell=True).decode('utf-8')
    return out.strip() != "0x"+"0"*64
            
# Register, or bootstrap if this is the first time
if is_bootstrapped():
    print('Registering...', file=sys.stderr)
    # Generate a private key and a corresponding public key
    private_key = PrivateKey.generate()
    public_key = private_key.public_key
    print('public_key:', bytes(public_key).hex(), file=sys.stderr)

    # Generate a private key and corresponding address
    myPriv = os.urandom(32)
    myAddr = Account.from_key(myPriv).address

    # Generate a signature
    cmd = f"cast call {CONTRACT} 'register_appdata(address)' {HOST_ADDR}"
    out = subprocess.check_output(cmd, shell=True).strip()
    h = bytes.fromhex(out[2:].decode('utf-8'))
    sig = Account.from_key(myPriv).unsafe_sign_hash(h)
    sig = sig.v.to_bytes(1,'big') +  sig.r.to_bytes(32,'big') + sig.s.to_bytes(32,'big')

    # Get the quote
    s = b"register:" + bytes(public_key)+b":"+myAddr.encode('utf-8')
    # print('appdata preimage:', s)
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
        print(resp, file=sys.stderr)
        raise Exception

    encrypted_message = resp.content

    # Decrypt the message using the private key
    unseal_box = SealedBox(private_key)
    decrypted_message = unseal_box.decrypt(encrypted_message)
    xPriv = bytes(decrypted_message)

else:
    print('Not bootstrapped', file=sys.stderr)

    # Generate the random key
    xPriv = os.urandom(32)
    addr = Account.from_key(xPriv).address

    # Get the quote
    appdata = hashlib.sha256(b"boostrap:" + addr.encode('utf-8')).hexdigest()
    quote = get_quote(appdata)

    # Store the quote for the host later (redundant)
    open('/mnt/host_volume/bootstrap_quote.quote','w').write(quote)
    
    # Ask the host service to post the tx, return when done
    resp = requests.post(f"{HOST_SERVICE}/bootstrap", data=dict(
        addr=addr,
        quote=quote))
    if resp.status_code != 200:
        print(resp, file=sys.stderr)
        raise Exception

print(xPriv.hex())

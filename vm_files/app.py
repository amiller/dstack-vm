# Sample application
from unstoppable_tls import give_me_the_keys
from flask import Flask
import requests
import sys
cli = sys.modules['flask.cli']
cli.show_server_banner = lambda *x: None

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Dstack TLS!"

if __name__ == '__main__':
    key_path, cert_path = give_me_the_keys()
    app.run(host='0.0.0.0', port=4002, ssl_context=(cert_path, key_path))

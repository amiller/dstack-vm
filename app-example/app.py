# Sample application
from flask import Flask
import requests
import sys

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello from Dstack TLS!"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)

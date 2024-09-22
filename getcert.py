import json
import sys
import requests

CERTIFICATE_PATH = "host_volume/certificate.pem"
DOMAIN = "dstack-mockup.ln.soc1024.com"

def fetch_latest_cert(domain):
    url = f"https://crt.sh/?match==&q={DOMAIN}&output=json"
    print(url)
    response = requests.get(url)
    certs_data = json.loads(response.text)
    cert_data = certs_data[0]
    cert_pem = requests.get(f"https://crt.sh/?d={cert_data['id']}").text
    open(CERTIFICATE_PATH,'w').write(cert_pem)
    print('wrote', CERTIFICATE_PATH)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        DOMAIN = sys.argv[1]
    fetch_latest_cert(DOMAIN)

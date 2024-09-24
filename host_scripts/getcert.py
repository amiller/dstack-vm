import json
import sys
import requests
import subprocess

CERTIFICATE_PATH = "host_volume/certificate.pem"
DOMAIN = "dstack-mockup.ln.soc1024.com"

def fetch_latest_cert(domain):
    if 0:
        url = f"https://crt.sh/?match==&q={DOMAIN}&output=json"
        print(url)
        response = requests.get(url)
        certs_data = json.loads(response.text)
        cert_data = certs_data[0]
        cert_pem = requests.get(f"https://crt.sh/?d={cert_data['id']}").text
        open(CERTIFICATE_PATH,'w').write(cert_pem)
        print('wrote', CERTIFICATE_PATH)

    cmd = f"""curl -s "$(openssl x509 -in {CERTIFICATE_PATH} -noout -text | grep 'CA Issuers - URI:' | sed 's/.*URI://')" | openssl x509 -inform DER -outform PEM > intermediate.pem && cat intermediate.pem >> {CERTIFICATE_PATH}"""
    subprocess.check_output(cmd, shell=True)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        DOMAIN = sys.argv[1]
    fetch_latest_cert(DOMAIN)

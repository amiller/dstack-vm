import time
import subprocess
import sys
import os

CONTAINER_ARCHIVE="/mnt/host_volume/app-example.tar"

# Untrusted values read from host
dotenv = lambda f: dict(line.strip().split('=', 1) for line in open(f) if line.strip() and not line.startswith('#'))

env = dotenv('/mnt/host_volume/guest.env')
ETH_API_KEY     = env['ETH_API_KEY']
HOST_ADDR       = env['HOST_ADDR']
MOCK_VERIFY_URL = env['MOCK_VERIFY_URL']

# Trusted values read from image
trusted = dotenv('/root/trusted.env')
CONTRACT     = trusted['CONTRACT']
HOST_SERVICE = trusted['HOST_SERVICE']
os.environ['ETH_RPC_URL'] = trusted['ETH_RPC_URL'] + ETH_API_KEY
os.environ['CHAIN-ID']    = trusted['CHAIN_ID']

def get_current_container():
    result = subprocess.run(["podman", "inspect", "--format", "{{.ImageName}}", "mycontainer"], capture_output=True, text=True)
    return result.stdout.strip()

def get_desired_image():
    # Implement this function to fetch the desired image name and hash
    cmd = f"cast call {CONTRACT} 'container()(string)'"
    out = eval(subprocess.check_output(cmd, shell=True).decode('utf-8'))
    return out

def load_image(archive_path):
    subprocess.run(["podman", "load", "-i", archive_path], check=True)

def restart_container(new_image):    
    subprocess.run("podman stop mycontainer", shell=True)
    subprocess.run("kill -9 $(podman container inspect mycontainer -f '{{.State.Pid}}')", shell=True)
    subprocess.run("podman rm -f mycontainer", shell=True)
    cmd = "podman run -d --replace --name mycontainer \
       --hostname myapp.hostname \
       --add-host=dstack-guest:10.88.0.1 \
       --ip=10.88.0.2 --rm " + new_image
    subprocess.run(cmd, shell=True, check=True)

def tail_pod_logs():
    tail_process = subprocess.Popen("podman logs -f mycontainer", shell=True, stdout=sys.stdout, stderr=subprocess.STDOUT)
    return tail_process

def monitor():
    tail_process = None
    while True:
        try:
            current_image = get_current_container()
            desired_image = get_desired_image()
            if current_image != desired_image:
                print('current_image:', current_image)            
                print('desired_image:', desired_image)
                load_image(CONTAINER_ARCHIVE)
                restart_container(desired_image)
                if tail_process:
                    tail_process.terminate()
                tail_process = tail_pod_logs()
            time.sleep(30)
        except Exception as e:
            print('Exception:', e)
            time.sleep(5)

if __name__ == "__main__":
    print('kubernethes')
    monitor()

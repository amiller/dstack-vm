# Dstack: speedrunning a p2p Confidential VM

Dstack is a testnet for self-replicating Confidential VMs (CVMs), that coordinate using a public blockchain.
The smart contract on the blockchain is associated with a shared secret, which is replicated among any participating nodes that register on-chain.
- Smart Contract [0x435 on Sepolia](https://sepolia.etherscan.io/address/0x435d16671575372cae5228029a1a9857e9482849#readContract)

The sample application serves an unstoppable HTTPs website. Browse to `https://dstack-mockup.ln.soc1024.com` for a demo greeting: 
```
Welcome to Dstack with unstoppable TLS!
appdata: 0x3ea1f2a382da749b56cb21c3345bcb1a0edd61f0705fbf0ec986b74efb4b81d1
signature: 0x1bc8e366dc889fb6ca67d05411c8e528c06e0c5f251c3749bae0d2a5c15f6dd7fe7f266f60301f17efaa4fbdf241a5fc6f6f17e2f9c5151df131e52867eb6f8ae2
```


Dstack is a flexible environment for apps running on the guest VM:
- Your app is a plain Docker container archive. It can access:
   - Encrypted persistent volume: `/mnt/encrypted_data/`
   - Untrusted host volume: `/mnt/host_volume/`
   - Per-app hardened keys: `http://dstack-guest/getkey/<tag>`
   - EVM-friendly remote attestation: `http://dstack-guest/attest/<tag>/<appdata>`
  
Have a look at the demo greeting app at [./app-example/app.py](./app-example/app.py).

Read the setup scripts, host service, guest services, in under 2000 lines of python and bash.

### Try it now
To play along with the test network, you need Sepolia testnet coins from a faucet, and an Alchemy API key.

Once you have that, you can try this on your linux laptop right now, with no TDX required.
- Building the VM and sample app: under 5 minutes
- Booting and joining the network: under 60 seconds
- Disk space required: 2GB

### How does the replication work?
The main production is a `virt-customize` script that builds the VM, starting from a minimal ubuntu base image, and including mainly python, nginx, and foundry. See [./build_vm.sh](./build_vm.sh).

The [startup script](./vm_files/startup_script.sh) kicks off the [registration process](./vm_files/register.py), whose entire goal is to get us a copy of the shared secret. This works by posting a transaction on-chain, passing along a remote attestation. Any existing node on the network can verify the remote attestation, and respond on-chain. See a sample [Register](https://sepolia.etherscan.io/inputdatadecoder?tx=0xa62346a8b5b1ae2bd85b393e770f8214b32122f9cf2880c6f766ff4d0d0ad665) transaction and an [Onboard](https://sepolia.etherscan.io/inputdatadecoder?tx=0x3ed316f9005f5b738db06ddd79920baf9fb5bcb2a2d46a33f11b19f8d9fff939) transaction.

The protocol is illustrated below:

<img src="https://github.com/user-attachments/assets/8d304f41-acc7-4574-a06b-362d8c8eecae" width=50%/>

The verification works with actual TDX DCAP quotes. But if you run the VM without a TDX, then attestations are provided from a dummy service. 
Here's a summary of the components: 

<img src="https://github.com/user-attachments/assets/e26aae6c-cc6b-4e45-a3ec-5be30fa621b0" width=50%/>

### What's the deal with the HTTPS?

The private key for the HTTPS server is derived from the replicated secret. Nodes generate a CSR. We get the certificate issued by letsencrypt, and it shows up on the CA website.

To proactively check a certificate (similar to RATLS or aTLS), verify the EVM-friendly remote attestation over the public key in the certificate. To rely on certificate transparency and public auditors, the auditors can easily check the quotes in [./auditing](./auditing) to see that a valid TDX DCAP quote explains the provenance of every public key listed at https://crt.sh/?q=dstack-mockup.ln.soc1024.com.

## Building the VM image

It's not necessary to have TDX to play along, since this image is meant to be easy to run in a environment. Instead it's just necessary to install qemu and libvirt.

```bash
apt-get install qemu qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

Libvirt will read from the system kernel, so I go ahead and allow read access:
```
sudo chmod a+r /boot/vmlinuz*
```

We have to start by downloading a base image if you don't have it.
The ubuntu minimal is under 300MB, and after we're done installing packages it will be under 2GB.

```bash
wget https://cloud-images.ubuntu.com/minimal/releases/noble/release-20240903/ubuntu-24.04-minimal-cloudimg-amd64.img
ln -s $PWD/ubuntu-24.04-minimal-cloudimg-amd64.img ./ubuntu-minimal.img
chmod -w ubuntu-24.04-minimal-cloudimg-amd64.img
```

To kick off the build process, run
```bash
./build_vm.sh
```

It's convenient when developing to take a copy of the image after `apt get update`. For this you can have a look at [./build_vm_dev.sh](./build_vm_dev.sh). It's necessary to `rm ubuntu_vm.step1.img` to make it rebuild the intermediate snapshot.

### Build the example app
To build the sample application, just use Docker and store it in the untrusted host volume so the podman in the guest VM can access it.  
```bash
./build_app.sh
```
or
```bash
docker build -t app-example:latest app-example
docker save -o ./host_volume/app-example.tar app-example:latest
```

### Auditability of builds

TODO:
- we could store our own repo mirror of the packages we installed, along with their signatures from package maintainers or evidence of how widely they were distributed
- we could use virt-diff to enumerate the differences in images

## Running the node and join the test instance

The main goal will be to take our VM and connect it to the testnet network, retrieving a copy of the shared key.
Once we have the shared key, the VM will use this key to mount an encrypted disk image and run the `app.py`.

### Configuring the host

First we need to configure `host.env`. 
The host services are not part of the enclave, but are responsible for signing the actual transactions and paying gas.
See `host.env.example`:
```bash
PRIVKEY=
ETH_API_KEY=
```

### Run PCCS on the host
We are looking forward to moving to on-chain PCCS. But for now we still have to do a workaround to deal with platform collateral caching, which requires us to run another tool that interacts with Intel's service.
```bash
git submodule update --init --recursive
cd dummy-tdx-dcap
make build-httpserver
```

### Run the VM

The last setup to run the host service is this:
```bash
sudo apt-get install tmux dumpasn1
pip install -r requirements.txt
```

We have to fetch the current certificate from `crt.sh` and store it in the untrusted host volume.
```bash
python scripts/getcert.py
```

Finally here's a little tmux script that runs  the host services and the VM
```bash
./tmuxdemo.sh
```
<img src="https://github.com/user-attachments/assets/27f82557-6e74-4112-9f5a-820addc31f48" width=70%/>

## More details

### Host service 
The provided `host_service.py` script monitors the Sepolia blockchain, looking for valid requests, and if they are valid then passes them to the enclave. The resulting ciphertext is then posted on-chain, where the node attempting to register will be able to see it.

### Auditing


### Best effort gossip
Since the blobs are too expensive to send entire quotes, we're just running a service, see `host.env.example` and `pubsub.py`.
Ideally we can provide a few alternatives here. The enclave doesn't really care how the host provides it.

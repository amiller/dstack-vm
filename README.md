# Dstack mock env VM

## Building the VM image

It's not necessary to have TDX, since this image is meant to be easy to run in a environment. Instead it's just necessary to install qemu and libvirt.

```bash
apt-get install qemu qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
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

It's convenient when developing to take a copy of the image after `apt get update`. For this you can have a look at `build_vm_dev.sh`. It's necessary to `rm ubuntu_vm.step1.img` to make it rebuild the intermediate snapshot.

## Running the node and join the test instance

The main goal will be to take our VM and connect it to the testnet network, retrieving a copy of the shared key.
Once we have the shared key, the VM will use this key to mount an encrypted disk image and run the `app.py`.

### Running the host services

First we need to configure `host.env` and run a helper service `host_services.py` on the untrusted host. Actually you are encouraged to customize the untrusted portion as much as you like, since it doesn't the identify of the enclave. And the design goal should be to steer complexity and interaction outside the enclave as much as possible.
Here we leave the host is responsible for signing the actual transactions and paying gas.

See `host.env.example` as it's necessary to fill some parameters:
```bash
PRIVKEY=
ETH_API_KEY=
PUBSUB_URL=
```

To run the service itself, run this in another terminal or a screen:
```bash
pip install -r requirements.txt
python host_service.py
```

### Crutch for PCCS
We are looking forward to moving to on-chain PCCS. But for now we still have to do a workaround to deal with platform collateral caching, which requires us to run another tool that interacts with Intel's service.

In one last background terminal do this:
```bash
git clone https://github.com/ruteri/dummy-tdx-dcap
cd dummy-tdx-dcap
make build-httpserver
go run cmd/httpserver/main.go
```

### Run the VM

This runs the VM, using KVM for best performance, making the `host_volume` available as a device.
In the dev build script the root password will be set to '' so you can type 'root' and hit enter real quick.

```bash
./start_vm.sh
```

Once in the terminal, `tail -N 100 -F /var/log/startup_script.log` will show you how the onboarding process is going. If everything went well, you should see something like the following:
```
```

## Helping other nodes join the network

Each enclave that joins that network is also capable of helping others join the network. The host also have to be involved in guiding this.

After starting up, the VM runs a script `guest_service.py`, which exposes one endpoint:
- `http://guest_service/onboard` that takes a public key and a quote.

If the following conditions are met:
- The `addr` corresponds to a valid on-chain request
- The `quote` is valid

then the existing master secret is encrypted to the given public key.

The provided `host_service.py` script monitors the Sepolia blockchain, looking for valid requests, and if they are valid then passes them to the enclave. The resulting ciphertext is then posted on-chain, where the node attempting to register will be able to see it.

### Best effort gossip

Since the blobs are too expensive to send entire quotes, we're just running a service, see `host.env.example` and `pubsub.py`.

Ideally we can provide a few alternatives here. The enclave doesn't really care how the host provides it.


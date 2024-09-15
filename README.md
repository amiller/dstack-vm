# Dstack as a VM

## Building the VM image

It's not necessary to have TDX, since the we support running in a mock environment. However, it's necessary to install qemu, and libvirt.

```
apt-get install qemu qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virt-manager
```

Have to start by downloading a base image.
The ubuntu minimal is under 300MB, and when expanded in `qcow2` format will be around 1GB.
```bash
wget https://cloud-images.ubuntu.com/minimal/releases/noble/release-20240903/ubuntu-24.04-minimal-cloudimg-amd64.img
ln -s $PWD/ubuntu-24.04-minimal-cloudimg-amd64.img ./ubuntu-minimal.img
chmod -w ubuntu-24.04-minimal-cloudimg-amd64.img
```

Then run
```bash
./build_vm.sh
```

It's convenient when developing to take a copy of the image after `apt get update`. For this have a look at `build_vm_dev.sh`. It's necessary to `rm ubuntu_vm.step1.img` to make it rebuild the partial base.

## Running the node and join the test instance

The main goal will be to take our VM and connect it to the testnet network, retrieving a copy of the shared key.

### Running the host services

First we need to configure and run a helper script on the untrusted host. 

See `host.env.example` as it's necessary to fill some parameters:
```
PRIVKEY=
ETH_API_KEY=
PUBSUB_URL=
```

## Helping other nodes join the network

The enclave is capable of helping others join the network, but the host has to manage this.

The provided host script monitors the Sepolia blockchain, looking for requests.

Additionally 


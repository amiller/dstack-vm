set -ex

# This is a sequence of libvirt commands.
# Saving the intermediate state after packages is meant to
# reduce the rebuild time, without using overlays.
#   Wish this were more like dockerfiles!
#   So instead it's only practical with a couple cache points

# Step 1
if [ ! -f "./ubuntu_vm.step1.img" ]; then
    qemu-img convert -f qcow2 ./ubuntu-minimal.img -O qcow2 ./ubuntu_vm.step1.img
    virt-customize -a ./ubuntu_vm.step1.img \
      --update \
      --install cryptsetup,wget,python3-pip,isc-dhcp-client,dumpasn1,podman \
      --install pipx,python3-nacl,python3-flask,python3-requests,nginx \
      --run-command 'pip install eth_account waitress --break-system-packages' \
      --copy-in foundry_nightly_linux_amd64.tar.gz:/root \
      --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin'
fi

# Step 2
if true; then
    cp ubuntu_vm.step1.img ubuntu_vm_dev.img
    virt-customize -a ubuntu_vm_dev.img \
    --copy-in guest/nginx.conf:/etc/nginx/ \
    --run-command 'systemctl disable nginx' \
    --copy-in guest/startup_script.sh:/usr/local/bin/ \
    --copy-in guest/startup_script.service:/etc/systemd/system/ \
    --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
    --run-command 'systemctl enable startup_script.service' \
    --copy-in guest/trusted.env:/root \
    --copy-in guest/guest_service.py:/root \
    --copy-in guest/replicatoor.py:/root \
    --copy-in guest/unstoppable_tls.py:/root \
    --copy-in guest/kubernethes.py:/root \
    --root-password password:
fi

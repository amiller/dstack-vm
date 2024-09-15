set -ex

# This is a sequence of libvirt commands.
# Saving the intermediate state after packages

# Step 1
if false; then
    qemu-img convert -f qcow2 ./ubuntu-minimal.img -O qcow2 ubuntu_vm.img
    virt-customize -a ubuntu_vm.img \
      --update \
      --install cryptsetup,wget,python3-pip,isc-dhcp-client \
      --install pipx,python3-nacl,python3-flask,python3-requests
fi

# Step 2
if true; then
    cp ubuntu_vm.img ubuntu_vm2.img
    virt-customize -a ubuntu_vm2.img \
    --run-command 'pip install environs eth_account --break-system-packages' \
    --copy-in foundry_nightly_linux_amd64.tar.gz:/root/ \
    --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin' \
    --copy-in vm_files/guest_service.py:/usr/local/bin \
    --run-command 'chmod +x /usr/local/bin/guest_service.py' \
    --copy-in vm_files/register.py:/usr/local/bin/ \
    --run-command 'chmod +x /usr/local/bin/register.py' \
    --copy-in vm_files/startup_script.sh:/usr/local/bin/ \
    --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
    --copy-in vm_files/startup_script.service:/etc/systemd/system/ \
    --run-command 'systemctl enable startup_script.service' \
    --copy-in vm_files/app.py:/root \
    --root-password password:
fi

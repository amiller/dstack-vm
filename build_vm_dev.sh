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
      --install cryptsetup,wget,python3-pip,isc-dhcp-client,dumpasn1 \
      --install pipx,python3-nacl,python3-flask,python3-requests \
      --run-command 'pip install environs eth_account waitress --break-system-packages'
fi

# Step 2
if true; then
    cp ubuntu_vm.step1.img ubuntu_vm_dev.img
    virt-customize -a ubuntu_vm_dev.img \
    --copy-in foundry_nightly_linux_amd64.tar.gz:/root \
    --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin' \
    --copy-in vm_files/startup_script.sh:/usr/local/bin/ \
    --copy-in vm_files/startup_script.service:/etc/systemd/system/ \
    --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
    --run-command 'systemctl enable startup_script.service' \
    --copy-in vm_files/guest_service.py:/root \
    --copy-in vm_files/register.py:/root \
    --copy-in vm_files/app.py:/root \
    --copy-in vm_files/unstoppable_tls.py:/root \
    --root-password password:
fi

set -ex

# This is a sequence of libvirt commands.
# Saving the intermediate state after packages is meant to
# reduce the rebuild time, without using overlays.
#   Wish this were more like dockerfiles!
#   So instead it's only practical with a couple cache points

# Step 1
if false; then
    qemu-img convert -f qcow2 ./ubuntu-minimal.img -O qcow2 ubuntu_vm.img
    virt-customize -a ubuntu_vm.img \
      --update \
      --install cryptsetup,wget,python3-pip,isc-dhcp-client \
      --install pipx,python3-nacl,python3-flask,python3-requests \
      --run-command 'pip install environs eth_account --break-system-packages' \
      --copy-in foundry_nightly_linux_amd64.tar.gz:/root \
      --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin' \
      --copy-in vm_files/startup_script.sh:/usr/local/bin/ \
      --copy-in vm_files/startup_script.service:/etc/systemd/system/ \
      --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
      --run-command 'systemctl enable startup_script.service' \
      --copy-in vm_files/guest_service.py:/root \
      --copy-in vm_files/register.py:/root \
      --copy-in vm_files/app.py:/root
fi

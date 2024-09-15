set -ex

# Step 1
if false; then
    qemu-img convert -f qcow2 ./ubuntu-minimal.img -O qcow2 ubuntu_vm.img
    virt-customize -a ubuntu_vm.img \
      --update \
      --install cryptsetup,wget,python3-pip,isc-dhcp-client
fi

# Step 2
if true; then
    cp ubuntu_vm.img ubuntu_vm2.img
    virt-customize -a ubuntu_vm2.img \
    --copy-in foundry_nightly_linux_amd64.tar.gz:/root/ \
    --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin' \
    --install pipx,libsodium \
    --run-command 'pipx install Flask requests pynacl' \
    --copy-in vm_files/startup_script.sh:/usr/local/bin/ \
    --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
    --copy-in vm_files/startup_script.service:/etc/systemd/system/ \
    --run-command 'systemctl enable startup_script.service' \
    --root-password password:password
fi

set -ex

qemu-img convert -f qcow2 ./ubuntu-minimal.img -O qcow2 ubuntu_vm.img

virt-customize -a ubuntu_vm.img \
   --update \
   --install cryptsetup,wget,python3-pip,isc-dhcp-client,dumpasn1,podman \
   --install pipx,python3-nacl,python3-flask,python3-requests,nginx \
   --run-command 'apt-get clean' \
   --run-command 'pip install environs eth_account waitress --break-system-packages' \
   --copy-in foundry_nightly_linux_amd64.tar.gz:/root \
   --run-command 'tar -xzf /root/foundry_nightly_linux_amd64.tar.gz -C /usr/local/bin' \
   --copy-in vm_files/nginx.conf:/etc/nginx/ \
   --run-command 'systemctl disable nginx' \
   --copy-in vm_files/startup_script.sh:/usr/local/bin/ \
   --copy-in vm_files/startup_script.service:/etc/systemd/system/ \
   --run-command 'chmod +x /usr/local/bin/startup_script.sh' \
   --run-command 'systemctl enable startup_script.service' \
   --copy-in vm_files/guest_service.py:/root \
   --copy-in vm_files/register.py:/root \
   --copy-in vm_files/unstoppable_tls.py:/root

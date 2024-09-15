set -x

BASE=${1:-./ubuntu_vm.img}

qemu-img create -f qcow2 -b $BASE -F qcow2 ubuntu_vm_overlay.img

qemu-system-x86_64 \
    -enable-kvm \
    -m 2048 \
    -smp 2 \
    -hda ./ubuntu_vm_overlay.img \
    -net nic,model=virtio -net user,hostfwd=tcp::4001-:4001 \
    -fsdev local,id=host_vol,path=./host_volume,security_model=none \
    -device virtio-9p-pci,fsdev=host_vol,mount_tag=host_volume \
    -nographic

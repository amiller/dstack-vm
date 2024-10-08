#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# For redirecting logging earlier
# exec > /var/log/startup_script.log 2>&1

# Setup the network
dhclient ens3

# Variables
CONTAINER_PATH="/mnt/host_volume/encrypted_container.img"
MOUNT_POINT="/mnt/encrypted_data"
LOOP_DEVICE=$(losetup -f)  # Automatically find the next available loop device
DECRYPTED_NAME="encrypted_volume"

# Mount the host directory via 9p
mkdir -p /mnt/host_volume
mount -t 9p -o trans=virtio,version=9p2000.L host_volume /mnt/host_volume

# Redirect all output to mounted log file for debugging
exec > /mnt/host_volume/startup_script.log 2>&1

############################
# Run the Replicatoor script
############################
XPRIV=$(python3 /root/replicatoor.py)
echo "Dstack node onboarded. Enclave has the key..."

# Check if the encrypted container exists; create it if not
if [ ! -f "$CONTAINER_PATH" ]; then
    echo "Encrypted container not found. Creating a new one."
    dd if=/dev/zero of="$CONTAINER_PATH" bs=1M count=140  # 140MB container; adjust size as needed
    echo ${XPRIV} | cryptsetup luksFormat "$CONTAINER_PATH" --key-file -
fi

# Set up the loop device
losetup "$LOOP_DEVICE" "$CONTAINER_PATH"

# Unlock the LUKS container
echo ${XPRIV} | cryptsetup open "$LOOP_DEVICE" "$DECRYPTED_NAME" --key-file -
echo "Encrypted container unlocked."

# Create filesystem if not exists
if [ -z "$(blkid -o value -s TYPE /dev/mapper/$DECRYPTED_NAME)" ]; then
    echo "Creating filesystem in decrypted container."
    mkfs.ext4 /dev/mapper/"$DECRYPTED_NAME"
fi

# Mount the decrypted filesystem
mkdir -p "$MOUNT_POINT"
mount /dev/mapper/"$DECRYPTED_NAME" "$MOUNT_POINT"

# Verify the mount
if mountpoint -q "$MOUNT_POINT"; then
    echo "Decrypted filesystem mounted at $MOUNT_POINT."
else
    echo "Failed to mount decrypted filesystem."
    exit 1
fi

#########################
# Run the Guest services
#########################
# This is used by the host to ask for onboarding,
# and by the other applications to provide attestation
# and derived keys
pushd /root/
XPRIV=${XPRIV} waitress-serve --port=80 guest_service:app &
GSRV=$!
sleep 1

#########################
# Unstoppable TLS Domains
#########################

# Make sure to get the certificate before proceeding
python3 unstoppable_tls.py

# Run the reverse proxy
nginx

#############
# Kubernethes
#############

export PYTHONUNBUFFERED=1
python3 kubernethes.py

# If the app concludes, still keep the guest around
wait $GSRV

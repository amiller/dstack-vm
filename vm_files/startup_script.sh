#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Redirect all output to a log file for debugging
exec > /var/log/startup_script.log 2>&1

# Setup the network
dhclient ens3

# Variables
KEY_URL="http://10.0.2.2:8000/key"
CONTAINER_PATH="/mnt/host_volume/encrypted_container.img" # for LUKS
MOUNT_POINT="/mnt/encrypted_data"
LOOP_DEVICE=$(losetup -f)  # Automatically find the next available loop device
DECRYPTED_NAME="encrypted_volume"

if true; then
    # Option 1: Dummy attestation    
    APPDATA=$(head -c32 /dev/urandom | sha256sum | head -c 64)
    QUOTE=$(curl -k http://ns31695324.ip-141-94-163.eu:10080/attestation/${APPDATA} --output - | od -An -v -tx1 | tr -d ' \n')
else
    # Option 2: Real attestation
fi

# Fetch the key from the remote server
wget -O /tmp/keyfile "$KEY_URL"

# Ensure the key was downloaded
if [ ! -f /tmp/keyfile ]; then
    echo "Key file not downloaded. Exiting."
    exit 1
fi

# Create mount points
mkdir -p /mnt/host_volume
mkdir -p "$MOUNT_POINT"

# Mount the host directory via 9p
if ! mountpoint -q /mnt/host_volume; then
    mount -t 9p -o trans=virtio,version=9p2000.L host_volume /mnt/host_volume
fi

# Check if the encrypted container exists; create it if not
if [ ! -f "$CONTAINER_PATH" ]; then
    echo "Encrypted container not found. Creating a new one."
    dd if=/dev/zero of="$CONTAINER_PATH" bs=1M count=100  # 100MB container; adjust size as needed
    echo "$(cat "$KEY_FILE")" | cryptsetup luksFormat "$CONTAINER_PATH" --key-file -
fi

# Set up the loop device
losetup "$LOOP_DEVICE" "$CONTAINER_PATH"

# Unlock the LUKS container
echo "$(cat "$KEY_FILE")" | cryptsetup open "$LOOP_DEVICE" "$DECRYPTED_NAME" --key-file -

# Create filesystem if not exists
if [ ! -d "$MOUNT_POINT" ] || [ -z "$(ls -A "$MOUNT_POINT")" ]; then
    echo "Creating filesystem in decrypted container."
    mkfs.ext4 /dev/mapper/"$DECRYPTED_NAME"
fi

# Mount the decrypted filesystem
mount /dev/mapper/"$DECRYPTED_NAME" "$MOUNT_POINT"

# Verify the mount
if mountpoint -q "$MOUNT_POINT"; then
    echo "Decrypted filesystem mounted at $MOUNT_POINT."
else
    echo "Failed to mount decrypted filesystem."
    exit 1
fi

# Run the Python script
python3 "$PYTHON_SCRIPT"

#!/bin/bash
# Update netplan configuration to use static IP
# This sets your client to 192.168.4.50/24 which should be in the same subnet as your server

# Create new netplan configuration
sudo tee /etc/netplan/50-cloud-init.yaml > /dev/null <<EOF
network:
  version: 2
  ethernets:
    eno1:
      dhcp4: false
      addresses:
        - 192.168.4.50/24
      gateway4: 192.168.4.1
      nameservers:
        addresses: [8.8.8.8, 8.8.4.4]
EOF

echo "Netplan configuration updated. Applying changes..."
sudo netplan apply
echo "Network configuration applied. Your new IP should be 192.168.4.50"
echo "You can verify with: ip addr show eno1"
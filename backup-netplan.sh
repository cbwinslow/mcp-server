#!/bin/bash
# Backup current netplan configuration
sudo cp /etc/netplan/50-cloud-init.yaml /etc/netplan/50-cloud-init.yaml.backup
echo "Backup created: /etc/netplan/50-cloud-init.yaml.backup"
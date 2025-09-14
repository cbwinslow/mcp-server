#!/bin/bash

# bash_secrets.sh - Script to retrieve and export secrets from Bitwarden vault

# Use personal API key for authentication if not already logged in
if ! bw status | grep -q "unlocked"; then
    # Check if API key env variables are set
    if [ -z "$BW_CLIENTID" ] || [ -z "$BW_CLIENTSECRET" ]; then
        echo "Error: Set BW_CLIENTID and BW_CLIENTSECRET environment variables with your personal API key."
        echo "Get your Personal API Key from: https://vault.bitwarden.com/#/settings/account_security"
        exit 1
    fi

    # Login with API key
    echo "Logging in to Bitwarden..."
    if ! bw login --apikey < /dev/null >/dev/null 2>&1; then
        echo "Error: Failed to login with API key. Check your client credentials."
        exit 1
    fi

    # Unlock vault with master password
    if [ -z "$BITWARDEN_MASTER_PASSWORD" ]; then
        echo "Error: Set BITWARDEN_MASTER_PASSWORD environment variable."
        exit 1
    fi

    echo "Unlocking vault..."
    SESSION=$(bw unlock "$BITWARDEN_MASTER_PASSWORD" --raw)
    if [ $? -ne 0 ]; then
        echo "Error: Failed to unlock vault. Check master password."
        exit 1
    fi
    export BW_SESSION="$SESSION"
else
    echo "Bitwarden session already active."
fi

# Export secrets as environment variables
# Replace with your actual secret names/keys
# Example: export MY_API_KEY=$(bw get password "My API Key")
# Add your secrets below

# export EXAMPLE_SECRET=$(bw get password "example")

echo "Secrets loaded. Session will expire in 1 hour."

# Optional: source this file with caution - it may expose secrets
# echo "Example: export MY_SECRET=\$(bw get password \"My Secret\")"

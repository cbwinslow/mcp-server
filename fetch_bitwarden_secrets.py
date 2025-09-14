#!/usr/bin/env python3
"""
Legacy fetch_bitwarden_secrets.py - now uses the BitwardenSecretsManager class

This script remains for backward compatibility but utilizes the new comprehensive
Bitwarden integration module for better functionality and error handling.
"""

import os
import sys
import argparse
from bitwarden.bitwarden_integration import BitwardenSecretsManager


def main():
    """Fetch secrets and export as environment variables"""
    parser = argparse.ArgumentParser(description="Fetch Bitwarden secrets and export as environment variables")
    parser.add_argument("--prefix", default="",
                       help="Prefix for environment variable names")
    parser.add_argument("--secrets", nargs="*", default=[],
                       help="Specific secret names to fetch (if empty, fetches all)")
    parser.add_argument("--export", action="store_true", default=True,
                       help="Export secrets as environment variable declarations")

    args = parser.parse_args()

    try:
        # Initialize Bitwarden manager
        manager = BitwardenSecretsManager()

        # Authenticate
        if not manager.authenticate():
            print("Failed to authenticate with Bitwarden")
            sys.exit(1)

        if args.export:
            # Export all secrets as environment variables
            exports = manager.export_secrets_as_env(args.prefix)
            print("# Bitwarden Secrets Environment Variables")
            print("# Add this to your .bashrc, .zshrc, or run with 'source <(python3 fetch_bitwarden_secrets.py)'")
            print()
            print(exports)

            # Also set them in current session
            secrets = manager.list_secrets()
            for secret in secrets:
                key = secret.get("key", "")
                value = secret.get("value", "")
                if key and value:
                    env_key = f"{args.prefix}{key}".upper().replace("-", "_")
                    os.environ[env_key] = value
                    print(f"Set {env_key} in current session")

        else:
            # Print individual secrets
            if args.secrets:
                for secret_name in args.secrets:
                    value = manager.get_secret_by_name(secret_name)
                    if value:
                        print(f"{secret_name}={value}")
                    else:
                        print(f"Secret '{secret_name}' not found", file=sys.stderr)
            else:
                # List all secrets
                secrets = manager.list_secrets()
                print("Available secrets:")
                for secret in secrets:
                    print(f"  - {secret.get('key', 'unnamed')}: {secret.get('id', '')}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

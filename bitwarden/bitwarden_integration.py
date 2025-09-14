#!/usr/bin/env python3
"""
Bitwarden Secrets Manager Integration using SDK and CLI fallback
Supports both access token authentication and API key authentication
"""

import os
import sys
import json
import subprocess
import logging
from typing import Dict, List, Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class BitwardenSecretsManager:
    """
    Comprehensive Bitwarden Secrets Manager integration supporting:
    - SDK-based integration (preferred)
    - CLI fallback for environments without SDK
    - Access token and API key authentication methods
    """

    def __init__(self,
                 access_token: Optional[str] = None,
                 client_id: Optional[str] = None,
                 client_secret: Optional[str] = None,
                 master_password: Optional[str] = None,
                 api_url: str = "https://api.bitwarden.com",
                 identity_url: str = "https://identity.bitwarden.com",
                 state_file: Optional[str] = None):

        self.access_token = access_token or os.getenv("BWS_ACCESS_TOKEN") or os.getenv("BW_ACCESS_TOKEN")
        self.client_id = client_id or os.getenv("BW_CLIENTID")
        self.client_secret = client_secret or os.getenv("BW_CLIENTSECRET")
        self.master_password = master_password or os.getenv("BITWARDEN_MASTER_PASSWORD")
        self.api_url = api_url
        self.identity_url = identity_url
        self.organization_id = os.getenv("BITWARDEN_ORGANIZATION_ID")
        self.state_file = state_file or os.getenv("BW_STATE_FILE", ".bw_session")

        self.sdk_available = self._check_sdk_availability()
        if self.sdk_available:
            logger.info("Bitwarden SDK available - using SDK integration")
        else:
            logger.info("Bitwarden SDK not available - using CLI fallback")

    def _check_sdk_availability(self) -> bool:
        """Check if Bitwarden SDK is available"""
        try:
            import bitwarden_sdk
            return True
        except ImportError:
            return False

    def _run_command(self, cmd: List[str], input_data: Optional[str] = None) -> Dict[str, any]:
        """Run CLI command and return parsed JSON output"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                input=input_data,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Command failed: {' '.join(cmd)}")
                logger.error(f"Error output: {result.stderr}")
                raise Exception(f"Command failed: {result.stderr}")

            if result.stdout.strip():
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout.strip()}

            return {}

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            raise
        except Exception as e:
            logger.error(f"Error running command: {e}")
            raise

    def _authenticate_sdk(self):
        """Authenticate using SDK approach"""
        if not self.sdk_available:
            return False

        try:
            from bitwarden_sdk import BitwardenClient, ClientSettings, DeviceType

            settings = ClientSettings(
                api_url=self.api_url,
                identity_url=self.identity_url,
                user_agent="Bitwarden Python SDK Integration"
            )

            self.client = BitwardenClient(settings, DeviceType.SDK)

            if self.access_token:
                # Use access token authentication
                self.client.auth().login_access_token(self.access_token, self.state_file)
                logger.info("Authenticated with access token")
                return True
            else:
                logger.warning("No authentication method available")
                return False

        except Exception as e:
            logger.error(f"SDK authentication failed: {e}")
            return False

    def _authenticate_cli(self) -> bool:
        """Authenticate using CLI approach"""
        try:
            # Check if already logged in
            if os.path.exists(self.state_file):
                logger.info("Using existing session file")
                os.environ["BW_SESSION_FILE"] = str(Path(self.state_file).resolve())
                return True

            if self.access_token:
                # Use access token with BWS CLI
                logger.info("Attempting access token authentication")
                cmd = ["bws", "login", "--access-token", self.access_token]
                if self.state_file:
                    cmd.extend(["--state-file", self.state_file])
                self._run_command(cmd)
                return True

            elif self.client_id and self.client_secret:
                # Use API key authentication
                logger.info("Attempting API key authentication")
                cmd = ["bw", "login", "--apikey"]
                # Provide credentials via stdin
                credentials = f"{self.client_id}\n{self.client_secret}\n"

                if self.master_password:
                    credentials += f"{self.master_password}\n"

                try:
                    result = self._run_command(cmd, credentials)
                    logger.info("API key authentication successful")
                    return True
                except Exception as e:
                    logger.error(f"API key authentication failed: {e}")
                    return False

            else:
                logger.error("No authentication credentials provided")
                return False

        except Exception as e:
            logger.error(f"CLI authentication failed: {e}")
            return False

    def authenticate(self) -> bool:
        """Attempt authentication using SDK first, then CLI fallback"""
        if self.sdk_available:
            if self._authenticate_sdk():
                return True

        # Fallback to CLI
        return self._authenticate_cli()

    def list_secrets(self) -> List[Dict[str, any]]:
        """List all secrets for the organization"""
        if not self.organization_id:
            raise ValueError("Organization ID required for listing secrets")

        if self.sdk_available and hasattr(self, 'client'):
            try:
                secrets = self.client.secrets().list(self.organization_id)
                return secrets
            except Exception as e:
                logger.warning(f"SDK list failed, falling back to CLI: {e}")

        # CLI fallback
        cmd = ["bws", "secret", "list"]
        result = self._run_command(cmd)
        return result.get("secrets", [])

    def get_secret(self, secret_id: str) -> Dict[str, any]:
        """Get a specific secret by ID"""
        if self.sdk_available and hasattr(self, 'client'):
            try:
                return self.client.secrets().get(secret_id)
            except Exception as e:
                logger.warning(f"SDK get failed, falling back to CLI: {e}")

        # CLI fallback
        cmd = ["bws", "secret", "get", secret_id]
        return self._run_command(cmd)

    def get_secret_by_name(self, secret_name: str) -> Optional[str]:
        """Get a secret value by name (key)"""
        secrets = self.list_secrets()
        for secret in secrets:
            if secret.get("key") == secret_name:
                return secret.get("value")
        return None

    def create_secret(self, key: str, value: str, note: str = "", project_ids: Optional[List[str]] = None) -> Dict[str, any]:
        """Create a new secret"""
        if not self.organization_id:
            raise ValueError("Organization ID required for creating secrets")

        if self.sdk_available and hasattr(self, 'client'):
            try:
                project_ids = project_ids or []
                return self.client.secrets().create(self.organization_id, key, value, note, project_ids)
            except Exception as e:
                logger.warning(f"SDK create failed, falling back to CLI: {e}")

        # CLI fallback
        cmd = ["bws", "secret", "create", key, value, "--organization", self.organization_id]
        if note:
            cmd.extend(["--note", note])
        return self._run_command(cmd)

    def update_secret(self, secret_id: str, key: Optional[str] = None, value: Optional[str] = None,
                     note: Optional[str] = None, project_ids: Optional[List[str]] = None) -> Dict[str, any]:
        """Update an existing secret"""
        if not self.organization_id:
            raise ValueError("Organization ID required for updating secrets")

        if self.sdk_available and hasattr(self, 'client'):
            try:
                current = self.client.secrets().get(secret_id)
                new_key = key if key is not None else current["key"]
                new_value = value if value is not None else current["value"]
                new_note = note if note is not None else current.get("note", "")
                new_project_ids = project_ids if project_ids is not None else current.get("projectIds", [])
                return self.client.secrets().update(self.organization_id, secret_id, new_key, new_value, new_note, new_project_ids)
            except Exception as e:
                logger.warning(f"SDK update failed, falling back to CLI: {e}")

        # CLI fallback
        cmd = ["bws", "secret", "edit", secret_id]
        if key:
            cmd.extend(["--key", key])
        if value:
            cmd.extend(["--value", value])
        if note:
            cmd.extend(["--note", note])
        return self._run_command(cmd)

    def delete_secret(self, secret_id: str) -> Dict[str, any]:
        """Delete a secret"""
        if self.sdk_available and hasattr(self, 'client'):
            try:
                return self.client.secrets().delete([secret_id])
            except Exception as e:
                logger.warning(f"SDK delete failed, falling back to CLI: {e}")

        # CLI fallback
        cmd = ["bws", "secret", "delete", secret_id]
        return self._run_command(cmd)

    def export_secrets_as_env(self, prefix: str = "") -> str:
        """Export all secrets as environment variable declarations"""
        secrets = self.list_secrets()
        exports = []

        for secret in secrets:
            key = secret.get("key", "")
            value = secret.get("value", "")
            if key and value:
                env_key = f"{prefix}{key}".upper().replace("-", "_")
                exports.append(f'export {env_key}="{value}"')

        return "\n".join(exports)


def main():
    """Command-line interface for Bitwarden integration"""
    import argparse

    parser = argparse.ArgumentParser(description="Bitwarden Secrets Manager Integration")
    parser.add_argument("--list", action="store_true", help="List all secrets")
    parser.add_argument("--get", metavar="SECRET_ID", help="Get specific secret")
    parser.add_argument("--get-by-name", metavar="SECRET_NAME", help="Get secret by name")
    parser.add_argument("--export", action="store_true", help="Export all secrets as environment variables")
    parser.add_argument("--create", nargs=2, metavar=("KEY", "VALUE"), help="Create new secret")
    parser.add_argument("--note", metavar="NOTE", help="Note for new secret")

    args = parser.parse_args()

    try:
        manager = BitwardenSecretsManager()

        if not manager.authenticate():
            logger.error("Authentication failed")
            sys.exit(1)

        if args.list:
            secrets = manager.list_secrets()
            print(json.dumps(secrets, indent=2))
        elif args.get:
            secret = manager.get_secret(args.get)
            print(json.dumps(secret, indent=2))
        elif args.get_by_name:
            value = manager.get_secret_by_name(args.get_by_name)
            if value:
                print(value)
            else:
                print(f"Secret '{args.get_by_name}' not found", file=sys.stderr)
                sys.exit(1)
        elif args.export:
            exports = manager.export_secrets_as_env()
            print(exports)
        elif args.create:
            key, value = args.create
            result = manager.create_secret(key, value, args.note or "")
            print(json.dumps(result, indent=2))
        else:
            parser.print_help()

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

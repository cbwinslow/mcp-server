# Bitwarden Secrets Manager Integration

This project provides comprehensive integration with Bitwarden Secrets Manager for secure secret management in Python applications.

## Features

- **SDK and CLI Support**: Automatically uses Bitwarden SDK when available, falls back to CLI
- **Multiple Authentication Methods**: Supports access tokens and API key authentication
- **Environment Variable Export**: Export secrets as environment variables for applications
- **Organization Management**: Manage secrets at the organization level
- **Project Organization**: Support for organizing secrets by projects
- **Full CRUD Operations**: Create, read, update, and delete secrets
- **Secure Session Management**: Automatic session handling and persistence

## Installation

### Requirements

- Python 3.10+
- Bitwarden CLI (recommended for fallback) or Bitwarden SDK
- Access to Bitwarden organization with Secrets Manager enabled

### Dependencies

```bash
pip install bitwarden-sdk python-dotenv
```

## Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# Access Token Method (Recommended)
BWS_ACCESS_TOKEN=your_access_token_here

# Or API Key Method (Alternative)
BW_CLIENTID=user.your_client_id
BW_CLIENTSECRET=your_client_secret

# Server Configuration
BITWARDEN_API_URL=https://api.bitwarden.com
BITWARDEN_IDENTITY_URL=https://identity.bitwarden.com

# Organization and Project (Required for listing/creating secrets)
BITWARDEN_ORGANIZATION_ID=your_org_id
BITWARDEN_PROJECT_ID=your_project_id

# Session Management
BW_STATE_FILE=.bw_session

# Optional: Master Password (for legacy CLI)
BITWARDEN_MASTER_PASSWORD=your_master_password
```

### Getting Access Token

1. Log in to your Bitwarden web vault at https://vault.bitwarden.com
2. Go to **Settings → Security → API Key**
3. Click **"View API Key"** and enter your master password
4. Copy the `access_token` value

### Organization ID

To get your organization ID:
1. Go to your Bitwarden organization settings
2. Copy the organization ID (UUID format)

## Usage

### Basic Usage

```python
from bitwarden.bitwarden_integration import BitwardenSecretsManager

# Initialize with access token
manager = BitwardenSecretsManager(access_token="your_token")

# Authenticate
if manager.authenticate():
    print("Authenticated successfully!")
else:
    print("Authentication failed")

# List all secrets
secrets = manager.list_secrets()
for secret in secrets:
    print(f"Key: {secret['key']}, ID: {secret['id']}")

# Get a specific secret
secret = manager.get_secret("your_secret_id")
print(f"Secret value: {secret['value']}")

# Get secret by name
value = manager.get_secret_by_name("my_api_key")
print(f"API Key: {value}")

# Create a new secret
result = manager.create_secret("new_secret", "secret_value", "Optional note")

# Export all secrets as environment variables
exports = manager.export_secrets_as_env("BW_")
print("Environment variables:")
print(exports)
```

### Command Line Interface

```bash
# Export all secrets as environment variables
python3 bitwarden/bitwarden_integration.py --export

# List all secrets
python3 bitwarden/bitwarden_integration.py --list

# Get specific secret
python3 bitwarden/bitwarden_integration.py --get secret-id

# Create new secret
python3 bitwarden/bitwarden_integration.py --create "key" "value"

# Legacy script support
python3 fetch_bitwarden_secrets.py --export
```

### Integration with Existing Code

The legacy script `fetch_bitwarden_secrets.py` now uses the new BitwardenSecretsManager class for better functionality:

```bash
# Export all secrets to environment variables
python3 fetch_bitwarden_secrets.py

# Export with custom prefix
python3 fetch_bitwarden_secrets.py --prefix MYAPP_
```

## Authentication Methods

### 1. Access Token (Recommended)

Best for automation and programmatic access:

```python
manager = BitwardenSecretsManager(
    access_token="your_access_token"
)
```

### 2. API Key

Alternative method using client ID and secret:

```python
manager = BitwardenSecretsManager(
    client_id="user.your_client_id",
    client_secret="your_client_secret"
)
```

## Project Organization

### Creating Projects

```python
# Create a new project (requires CLI for now)
bws project create "my-project-name"
```

### Associating Secrets with Projects

```python
# Create secret with project association
result = manager.create_secret(
    "my_secret",
    "secret_value",
    project_ids=["project_id_1", "project_id_2"]
)
```

## Error Handling

The integration includes comprehensive error handling:

```python
try:
    manager = BitwardenSecretsManager()
    if manager.authenticate():
        secrets = manager.list_secrets()
        # Process secrets
    else:
        print("Authentication failed")
except Exception as e:
    print(f"Error: {e}")
```

## Security Considerations

- **Never commit secrets to version control**
- **Use environment variables for access credentials**
- **Enable session persistence for better performance**
- **Rotate access tokens regularly**
- **Use organization-level permissions appropriately**

## File Structure

```
bitwarden/
├── __init__.py                    # Module initialization
└── bitwarden_integration.py     # Main integration class

fetch_bitwarden_secrets.py       # Legacy script (now uses new class)
BITWARDEN_SOLUTION_README.md     # Legacy documentation
BITWARDEN_README.md             # This documentation
.env                             # Environment configuration (example)
```

## Testing

Basic functionality test:

```python
import os
from bitwarden.bitwarden_integration import BitwardenSecretsManager

# Test authentication
manager = BitwardenSecretsManager()

if manager.authenticate():
    print("✓ Authentication successful")

    # Test secret retrieval
    try:
        secrets = manager.list_secrets()
        print(f"✓ Retrieved {len(secrets)} secrets")

        if secrets:
            # Test getting first secret
            secret = manager.get_secret(secrets[0]['id'])
            print(f"✓ Secret retrieval successful: {secret['key']}")

    except Exception as e:
        print(f"✗ Error during secret operations: {e}")
else:
    print("✗ Authentication failed")
```

## Troubleshooting

### Common Issues

1. **Authentication Fails**
   - Verify your access token is correct and not expired
   - Check API key credentials
   - Ensure organization has Secrets Manager enabled

2. **CLI Not Found**
   ```bash
   # Install Bitwarden CLI
   npm install -g @bitwarden/cli
   # or
   curl https://bws.bitwarden.com/install | sh  # Linux/macOS
   # or
   iwr https://bws.bitwarden.com/install | iex   # Windows
   ```

3. **SDK Not Available**
   - Install SDK: `pip install bitwarden-sdk`
   - Check Python version compatibility
   - Fallback to CLI will be used automatically

4. **Organization ID Required**
   - Set `BITWARDEN_ORGANIZATION_ID` in your `.env` file
   - Verify you have appropriate organization permissions

## API Reference

### BitwardenSecretsManager Class

#### Constructor Parameters

- `access_token`: Bitwarden access token (str, optional)
- `client_id`: API client ID (str, optional)
- `client_secret`: API client secret (str, optional)
- `master_password`: Master password for CLI (str, optional)
- `api_url`: Bitwarden API URL (str, default: "https://api.bitwarden.com")
- `identity_url`: Identity service URL (str, default: "https://identity.bitwarden.com")
- `state_file`: Session state file path (str, optional)

#### Methods

- `authenticate()` -> bool: Authenticate with Bitwarden
- `list_secrets()` -> List[Dict]: List all organization secrets
- `get_secret(secret_id)` -> Dict: Get specific secret by ID
- `get_secret_by_name(name)` -> Optional[str]: Get secret value by name
- `create_secret(key, value, note, project_ids)` -> Dict: Create new secret
- `update_secret(secret_id, key, value, note, project_ids)` -> Dict: Update secret
- `delete_secret(secret_id)` -> Dict: Delete secret
- `export_secrets_as_env(prefix)` -> str: Export secrets as environment variables

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see project root for details.

## Support

For issues and questions:
1. Check this documentation
2. Review Bitwarden Secrets Manager documentation
3. Create a GitHub issue with detailed information

#!/usr/bin/env bash
set -euo pipefail

# Install n8n natively (Node.js + pm2 + systemd) without Docker

N8N_DIR=/opt/n8n
NODE_VERSION=${NODE_VERSION:-20}

# Install Node.js (NodeSource)
curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | sudo -E bash -
sudo apt-get install -y nodejs

sudo npm install -g pm2

sudo mkdir -p $N8N_DIR
sudo chown -R $USER:$USER $N8N_DIR
cd $N8N_DIR

npm init -y >/dev/null 2>&1 || true
npm install n8n --save

cat > $N8N_DIR/.env <<'ENV'
# Basic n8n configuration
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_HOST=127.0.0.1
WEBHOOK_URL=http://127.0.0.1:5678/

# Uncomment to use Postgres instead of default SQLite
# DB_POSTGRESDB_HOST=127.0.0.1
# DB_POSTGRESDB_PORT=5432
# DB_POSTGRESDB_DATABASE=n8n
# DB_POSTGRESDB_USER=mcp_app
# DB_POSTGRESDB_PASSWORD=change-me
# DB_TYPE=postgresdb
ENV

# Wrapper script for PM2 to load env
cat > $N8N_DIR/run.sh <<'RUN'
#!/usr/bin/env bash
set -e
export $(grep -v '^#' $(dirname $0)/.env | xargs -d '\n' -I {} echo {})
exec $(dirname $0)/node_modules/.bin/n8n --tunnel
RUN
chmod +x $N8N_DIR/run.sh

# PM2 process
pm2 start $N8N_DIR/run.sh --name n8n
pm2 save

# Systemd integration
sudo pm2 startup systemd -u $USER --hp $(eval echo ~$USER)

echo "n8n installed. UI at http://127.0.0.1:5678" 

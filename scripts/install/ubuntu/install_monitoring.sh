#!/usr/bin/env bash
set -euo pipefail

# Install Grafana, Prometheus, Node Exporter, Loki & Promtail (host-native)

# Grafana
sudo apt-get install -y apt-transport-https software-properties-common wget
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | sudo tee /etc/apt/sources.list.d/grafana.list
sudo apt-get update
sudo apt-get install -y grafana
sudo systemctl enable --now grafana-server

# Prometheus + Exporters
sudo apt-get install -y prometheus prometheus-node-exporter
sudo systemctl enable --now prometheus
sudo systemctl enable --now prometheus-node-exporter

# Loki
LOKI_VERSION=${LOKI_VERSION:-2.9.6}
curl -L -o /tmp/loki-linux-amd64.zip https://github.com/grafana/loki/releases/download/v${LOKI_VERSION}/loki-linux-amd64.zip
sudo unzip -o /tmp/loki-linux-amd64.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/loki-linux-amd64
sudo mkdir -p /etc/loki /var/lib/loki
sudo tee /etc/systemd/system/loki.service >/dev/null <<'UNIT'
[Unit]
Description=Loki Log Aggregator
After=network.target

[Service]
ExecStart=/usr/local/bin/loki-linux-amd64 -config.file=/etc/loki/config.yaml
Restart=always
User=root

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/loki/config.yaml >/dev/null <<'CFG'
auth_enabled: false
server:
  http_listen_port: 3100
common:
  path_prefix: /var/lib/loki
  storage:
    filesystem:
      chunks_directory: /var/lib/loki/chunks
      rules_directory: /var/lib/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory
schema_config:
  configs:
  - from: 2023-01-01
    store: boltdb-shipper
    object_store: filesystem
    schema: v13
    index:
      prefix: index_
      period: 24h
CFG

sudo systemctl daemon-reload
sudo systemctl enable --now loki

# Promtail
PROMTAIL_VERSION=${PROMTAIL_VERSION:-2.9.6}
curl -L -o /tmp/promtail-linux-amd64.zip https://github.com/grafana/loki/releases/download/v${PROMTAIL_VERSION}/promtail-linux-amd64.zip
sudo unzip -o /tmp/promtail-linux-amd64.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/promtail-linux-amd64
sudo mkdir -p /etc/promtail
sudo tee /etc/systemd/system/promtail.service >/dev/null <<'UNIT'
[Unit]
Description=Promtail Log Forwarder
After=network.target

[Service]
ExecStart=/usr/local/bin/promtail-linux-amd64 -config.file=/etc/promtail/config.yaml
Restart=always
User=root

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/promtail/config.yaml >/dev/null <<'CFG'
server:
  http_listen_port: 9080
  grpc_listen_port: 0
positions:
  filename: /var/lib/promtail/positions.yaml
clients:
  - url: http://127.0.0.1:3100/loki/api/v1/push
scrape_configs:
  - job_name: system
    static_configs:
      - targets: [localhost]
        labels:
          job: varlogs
          __path__: /var/log/*.log
CFG

sudo mkdir -p /var/lib/promtail
sudo systemctl daemon-reload
sudo systemctl enable --now promtail

echo "Monitoring stack installed. Grafana on :3000, Prometheus on :9090, Loki on :3100"


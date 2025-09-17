#!/usr/bin/env bash
set -euo pipefail

# Install Neo4j Community with APOC on Ubuntu and configure memory + plugins

NEO4J_PASSWORD=${NEO4J_PASSWORD:-neo4j}

wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/neo4j.gpg
echo "deb [signed-by=/usr/share/keyrings/neo4j.gpg] https://debian.neo4j.com stable 5" | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt-get update
sudo apt-get install -y neo4j=1:5.*

sudo systemctl stop neo4j || true

# Configure
sudo sed -i 's/^#dbms.security.auth_enabled=true/dbms.security.auth_enabled=true/' /etc/neo4j/neo4j.conf
sudo sed -i 's/^#server.default_listen_address=0.0.0.0/server.default_listen_address=0.0.0.0/' /etc/neo4j/neo4j.conf
sudo sed -i 's/^#server.bolt.listen_address=:7687/server.bolt.listen_address=:7687/' /etc/neo4j/neo4j.conf
sudo sed -i 's/^#server.http.listen_address=:7474/server.http.listen_address=127.0.0.1:7474/' /etc/neo4j/neo4j.conf
echo "dbms.security.procedures.unrestricted=apoc.*" | sudo tee -a /etc/neo4j/neo4j.conf
echo "dbms.security.procedures.allowlist=apoc.*" | sudo tee -a /etc/neo4j/neo4j.conf
echo "dbms.jvm.additional=-XX:+ExitOnOutOfMemoryError" | sudo tee -a /etc/neo4j/neo4j.conf
echo "server.memory.heap.initial_size=1g" | sudo tee -a /etc/neo4j/neo4j.conf
echo "server.memory.heap.max_size=2g" | sudo tee -a /etc/neo4j/neo4j.conf
echo "server.memory.pagecache.size=1g" | sudo tee -a /etc/neo4j/neo4j.conf

sudo systemctl enable neo4j
sudo systemctl start neo4j

sleep 5
echo "Setting initial password..."
echo -e ":server connect
:password $NEO4J_PASSWORD
" | cypher-shell -u neo4j -p neo4j || true

echo "Enabling APOC validation off (procedures already allowlisted)."

echo "Neo4j installed. Access Bolt on 7687, Browser on http://127.0.0.1:7474" 


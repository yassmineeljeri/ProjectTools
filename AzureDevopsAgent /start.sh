#!/bin/bash
set -e
# --- Load secrets from mounted files ---
AZP_URL=$(cat /mnt/secrets-store/AzpUrl | tr -d '\r\n' )
AZP_TOKEN=$(cat /mnt/secrets-store/AzpToken | tr -d '\r\n' )
AZP_POOL=$(cat /mnt/secrets-store/AzpPool | tr -d '\r\n' )
# --- Check required variables ---
if [ -z "$AZP_URL" ] || [ -z "$AZP_TOKEN" ] || [ -z "$AZP_POOL" ] ; then
  echo "Missing required environment variables: AZP_URL, AZP_TOKEN, AZP_POOL"
  exit 1
fi
AGENT_DIR="/azagent"
AGENT_URL="https://download.agent.dev.azure.com/agent/${AGENT_VERSION}/vsts-agent-linux-x64-${AGENT_VERSION}.tar.gz"


mkdir -p "$AGENT_DIR"
cd "$AGENT_DIR"
curl -Ls "$AGENT_URL" -o agent.tar.gz
tar -xzf agent.tar.gz


./config.sh --unattended \
  --url "$AZP_URL" \
  --auth pat \
  --token "$AZP_TOKEN" \
  --pool "$AZP_POOL" \
  --agent "$(hostname)" \
  --replace \
  --acceptTeeEula


echo "Agent registered. Starting job..."

./run.sh --once
status=$?

echo "Job finished with status $status. Cleaning up agent registration..."
./config.sh remove --unattended --auth pat --token "$AZP_TOKEN" || true

echo "Cleanup complete."
exit $status

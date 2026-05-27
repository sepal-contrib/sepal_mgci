#!/bin/bash
# sources the .env file and runs the Solara app
# Usage: ./run_solara.sh [filename] [port]
# If no filename is provided, defaults to solara_app.py
# If no port is provided, defaults to 8900

SOLARA_FILE="solara_app.py"
PORT="8900"
HOST="0.0.0.0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"
      shift 2
      ;;
    --port=*)
      PORT="${1#--port=}"
      shift
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --host=*)
      HOST="${1#--host=}"
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [filename] [--port PORT] [--host HOST]"
      echo "  Default host 0.0.0.0 listens on all interfaces (incl. Tailscale)."
      exit 0
      ;;
    *)
      SOLARA_FILE="$1"
      shift
      ;;
  esac
done

while IFS= read -r line; do
  [[ $line =~ ^#.*$ || -z $line ]] && continue
  
  if [[ $line =~ ^([^=]+)=(.*)$ ]]; then
    name="${BASH_REMATCH[1]}"
    value="${BASH_REMATCH[2]}"
    
    # Remove quotes if present
    value="${value#\'}"
    value="${value%\'}"
    value="${value#\"}"
    value="${value%\"}"
    
    export "$name=$value"
  fi
done < .env

# Show how to reach the app over Tailscale from another device
TS_IP="$(tailscale ip -4 2>/dev/null | head -1)"
if [[ -n $TS_IP ]]; then
  echo "Tailscale access: http://${TS_IP}:${PORT}/"
fi
echo "Local access:     http://localhost:${PORT}/"

solara run "$SOLARA_FILE" --host "$HOST" --port "$PORT" --no-open --log-level debug
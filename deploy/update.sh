#!/usr/bin/env bash
# Pulls the latest main and restarts every bot installed on this server.
# Run on the server as the bot user: ~/FatJokeBot/deploy/update.sh
set -euo pipefail

cd "$(dirname "$0")/.."
# uv lives in ~/.local/bin, which "ssh bot@server deploy/update.sh" does not put on PATH
export PATH="$HOME/.local/bin:$PATH"
git pull --ff-only
uv pip install --python .venv/bin/python -r requirements.txt
# one systemd service per bot, see deploy/*.service; a bot not installed yet is skipped
for service in fat-joke servo-skull; do
    if [ -f "/etc/systemd/system/$service.service" ]; then
        sudo systemctl restart "$service"
        sleep 3
        systemctl --no-pager status "$service" | head -n 5
    fi
done

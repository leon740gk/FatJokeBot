#!/usr/bin/env bash
# Pulls the latest main and restarts the bot. Run on the server as the bot user: ~/FatJokeBot/deploy/update.sh
set -euo pipefail

cd "$(dirname "$0")/.."
# uv lives in ~/.local/bin, which "ssh bot@server deploy/update.sh" does not put on PATH
export PATH="$HOME/.local/bin:$PATH"
git pull --ff-only
uv pip install --python .venv/bin/python -r requirements.txt
sudo systemctl restart fat-joke
sleep 3
systemctl --no-pager status fat-joke | head -n 5

#!/data/data/com.termux/files/usr/bin/bash
# Get the latest version of the bot from GitHub:  bash scripts/update.sh
cd "$(dirname "$0")/.." && git pull --ff-only && python -m swingbot check

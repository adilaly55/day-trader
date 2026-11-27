#!/data/data/com.termux/files/usr/bin/bash
# One-time phone setup for swingbot (run inside Termux, from the day-trader folder):
#     bash scripts/termux_setup.sh
# Safe to run again: it only adds what is missing.
set -e
cd "$(dirname "$0")/.."
REPO="$(pwd)"
HOME_DIR="$HOME/.swingbot"

echo "== 1/6 Installing packages (python, cron, notifications)"
pkg update -y
pkg install -y python git cronie termux-api termux-services
pip install --quiet tzdata          # time-zone data so New York / Dubai times are correct

echo "== 2/6 Creating $HOME_DIR"
mkdir -p "$HOME_DIR"
[ -f "$HOME_DIR/config.json" ] || cp swingbot/config.example.json "$HOME_DIR/config.json"
if [ ! -f "$HOME_DIR/secrets.env" ]; then
  cat > "$HOME_DIR/secrets.env" <<'SECRETS'
# Fill these in (no quotes, no spaces). This file never leaves your phone.
ALPACA_KEY_ID=
ALPACA_SECRET_KEY=
FINNHUB_TOKEN=
T212_API_KEY=
T212_API_SECRET=
SECRETS
fi
chmod 600 "$HOME_DIR/secrets.env"

echo "== 3/6 Scheduling: every 5 minutes, 16:00-01:59 phone time (covers US open and close in Dubai time)"
LINE="*/5 16-23,0-1 * * * cd $REPO && python -m swingbot tick >> $HOME_DIR/cron.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'swingbot tick' ; echo "$LINE" ) | crontab -

echo "== 4/6 Starting the scheduler service (crond)"
source "$PREFIX/etc/profile.d/start-services.sh" 2>/dev/null || true
sv-enable crond 2>/dev/null || true
sv up crond 2>/dev/null || true

echo "== 5/6 Keeping the phone awake for Termux"
termux-wake-lock || true

echo "== 6/6 Done."
echo
echo "Next:"
echo "  1. nano $HOME_DIR/secrets.env      (paste your keys, then Ctrl+O, Enter, Ctrl+X)"
echo "  2. python -m swingbot check        (tests every connection)"
echo "  3. Leave broker=dryrun for a day or two, then set \"broker\": \"t212\" in $HOME_DIR/config.json"

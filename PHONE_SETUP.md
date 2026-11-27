# Setting up the bot on your Android phone

About 20-30 minutes, once. Afterwards the bot runs by itself every trading day:

| Dubai time (winter) | Dubai time (summer*) | What happens |
|---|---|---|
| 18:30 | 17:30 | Buys the stocks flagged the night before ($50 each, max 5) and places a 12% safety stop at Trading 212 |
| ~00:45 | ~23:45 | Sells stocks that recovered (or were held 5 days), then picks tomorrow's buys |

\* US daylight-saving time, roughly mid-March to early November. The bot adjusts automatically, including holidays and early closes.

You get a phone notification for every buy, sell and nightly summary.

---

## What you need
- The Android phone, **plugged in and on Wi-Fi** from about 17:00 to 01:00 Dubai time (a spare phone that stays at home is ideal).
- Your keys: Alpaca (Key ID + Secret), Finnhub (API key), Trading 212 **Practice** (API key + API secret).
- A GitHub **access token** so the phone can download your private code (step 3).

## 1. Install two apps from F-Droid (not the Play Store)
The Play Store versions of Termux are outdated and break things.
1. On the phone, open **f-droid.org** in the browser, download and install the F-Droid app.
2. In F-Droid, install **Termux** and **Termux:API**. (Optional: **Termux:Boot**, which restarts the bot after the phone reboots.)
3. Open **Termux:API** once, then close it.

## 2. Stop Android from putting Termux to sleep (important)
Settings → Apps → **Termux** → Battery → **Unrestricted** (wording varies: "Don't optimise" / "No restrictions"). Do the same for **Termux:API**.
Also allow Termux to show notifications.

## 3. Create a GitHub token (lets the phone download the code)
On any device, logged in to GitHub:
1. Profile picture → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. Name: `phone`. Expiration: 1 year. Repository access: **Only select repositories → day-trader**.
3. Permissions → Repository permissions → **Contents: Read-only**. Generate, and copy the token (starts with `github_pat_`).

## 4. Download the bot (in Termux)
Open Termux and type these lines one at a time (press Enter after each):

```bash
pkg install -y git
```
```bash
git config --global credential.helper store
```
```bash
git clone https://github.com/adilaly55/day-trader.git
```
When asked: **Username** = `adilaly55`, **Password** = paste the token from step 3 (nothing appears while pasting; that's normal).

## 5. Run the setup script
```bash
cd day-trader && bash scripts/termux_setup.sh
```
This installs Python and the scheduler, creates the settings folder, and schedules the bot every 5 minutes between 16:00 and 02:00.
If it says something about services, **close Termux completely and reopen it**, then run the script once more.

## 6. Add your keys (stays on the phone, never uploaded)
```bash
nano ~/.swingbot/secrets.env
```
Fill in each line after the `=`, no spaces or quotes. Save with **Ctrl+O, Enter**, exit with **Ctrl+X**.
(Termux shows a CTRL key above the keyboard.)

## 7. Test everything
```bash
cd ~/day-trader && python -m swingbot check
```
Every line should start with `[ok]`. If one says `[FAIL]`, send me the message (not your keys).

## 8. First 1-2 days: simulation mode
The bot starts in **dryrun** mode: real prices and real decisions, but no orders anywhere. Check the notifications and:
```bash
python -m swingbot status
```

## 9. Switch to the Trading 212 Practice account
```bash
nano ~/.swingbot/config.json
```
Change `"broker": "dryrun"` to `"broker": "t212"` (keep `"t212_env": "demo"`). Save, then run `python -m swingbot check` again.
Make sure the Practice account has at least ~$300 of (virtual) cash.

---

## Everyday commands (in Termux, inside `~/day-trader`)

| Command | What it does |
|---|---|
| `python -m swingbot status` | Open positions, queued buys, results so far |
| `python -m swingbot check` | Tests all connections, no trading |
| `python -m swingbot pause` | No new buys (existing positions are still managed) |
| `python -m swingbot resume` | Undo pause |
| `python -m swingbot close-all` | **Emergency:** sells everything the bot holds right now, then pauses |
| `bash scripts/update.sh` | Download the latest version of the bot |
| `tail -20 ~/.swingbot/bot.log` | Recent activity |

## Good to know
- **Only touch the bot's positions in the Trading 212 app if you have to.** If you sell one by hand, the bot notices and stops tracking it.
- The **12% stop orders** sit at Trading 212, so they protect you even if the phone is off. If the phone was off at a buy/sell time, that step is skipped for the day; nothing breaks.
- Real money: **not yet.** After 4-6 weeks on Practice we compare the results with the backtest and decide together.

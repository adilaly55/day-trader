"""Notifications: Android (Termux:API) and/or ntfy.sh push, plus a log file. Never raises."""
from __future__ import annotations

import shutil
import subprocess
import urllib.request
from datetime import datetime
from pathlib import Path


class Notifier:
    def __init__(self, home: Path, termux: bool = True, ntfy_topic: str = ""):
        self.log_path = home / "bot.log"
        self.termux = termux and shutil.which("termux-notification") is not None
        self.ntfy_topic = ntfy_topic

    def __call__(self, title: str, message: str, important: bool = False) -> None:
        line = f"{datetime.now():%Y-%m-%d %H:%M:%S} | {title} | {message}"
        print(line, flush=True)
        try:
            with self.log_path.open("a") as f:
                f.write(line + "\n")
        except OSError:
            pass
        if self.termux:
            try:
                subprocess.run(["termux-notification", "--title", title, "--content", message,
                                "--priority", "high" if important else "default", "--group", "swingbot"],
                               timeout=15, check=False)
            except Exception:
                pass
        if self.ntfy_topic:
            try:
                req = urllib.request.Request(f"https://ntfy.sh/{self.ntfy_topic}", data=message.encode(),
                                             headers={"Title": title, "Priority": "high" if important else "default"})
                urllib.request.urlopen(req, timeout=15).read()
            except Exception:
                pass

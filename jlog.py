"""Logger unifié pour Jarvis — dual sink (stdout + /tmp/jarvis.log) avec couleurs.

Pourquoi un module custom plutôt que `logging` ?
main.py fait `logging.disable(logging.CRITICAL)` au boot pour étouffer le bruit
de HuggingFace, faster-whisper, etc. Donc on contourne via print + écriture
fichier directe — thread-safe (lock).

Override path via env :
    JARVIS_LOG=/path/file.log         # fichier de sortie
    JARVIS_NO_COLOR=1                 # désactive couleurs ANSI
"""
from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, TextIO

LOG_PATH = Path(os.environ.get("JARVIS_LOG", "/tmp/jarvis.log"))
USE_COLOR = sys.stdout.isatty() and os.environ.get("JARVIS_NO_COLOR") != "1"

_lock = threading.Lock()
_file: Optional[TextIO] = None

# ANSI
RESET = "\033[0m"
DIM   = "\033[2m"
BOLD  = "\033[1m"

COMP_COL = {
    "MAIN":    "\033[1;37m",  # bold white
    "WAKE":    "\033[35m",    # magenta
    "WHISPER": "\033[33m",    # yellow
    "CLAUDE":  "\033[36m",    # cyan
    "TOOL":    "\033[34m",    # blue
    "TTS":     "\033[32m",    # green
    "UI":      "\033[37m",    # white
    "AUDIO":   "\033[37m",
}
LVL_COL = {
    "DEBUG": DIM,
    "INFO":  "",
    "WARN":  "\033[33m",
    "ERROR": "\033[31m",
}


def _ensure_file() -> None:
    global _file
    if _file is not None:
        return
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _file = open(LOG_PATH, "a", buffering=1)
        _file.write("\n" + "─" * 78 + f"\n  Jarvis log start — {time.strftime('%Y-%m-%d %H:%M:%S')}\n" + "─" * 78 + "\n")
    except Exception:
        _file = None


def _now() -> str:
    t = time.time()
    lt = time.localtime(t)
    ms = int((t - int(t)) * 1000)
    return f"{time.strftime('%H:%M:%S', lt)}.{ms:03d}"


def _emit(level: str, component: str, msg: str) -> None:
    head = _now()
    plain = f"{head} {level:<5} [{component:<7}] {msg}"
    with _lock:
        _ensure_file()
        if _file:
            try:
                _file.write(plain + "\n")
            except Exception:
                pass
        if USE_COLOR:
            l_col = LVL_COL.get(level, "")
            c_col = COMP_COL.get(component, "")
            line = (f"{DIM}{head}{RESET} {l_col}{level:<5}{RESET} "
                    f"{c_col}[{component:<7}]{RESET} {msg}")
            print(line, flush=True)
        else:
            print(plain, flush=True)


def debug(component: str, msg: str) -> None: _emit("DEBUG", component, msg)
def info(component: str,  msg: str) -> None: _emit("INFO",  component, msg)
def warn(component: str,  msg: str) -> None: _emit("WARN",  component, msg)
def error(component: str, msg: str) -> None: _emit("ERROR", component, msg)


def trunc(s: str, n: int = 240) -> str:
    """Tronque + remplace newlines pour log lisible sur une ligne."""
    if not isinstance(s, str):
        s = str(s)
    s = s.replace("\n", " ↵ ").replace("\r", "")
    return s if len(s) <= n else s[:n] + "…"

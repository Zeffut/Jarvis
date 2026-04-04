"""Terminal UI for Jarvis — clean, styled output."""
from __future__ import annotations

import os
import sys
import warnings

# Suppress all warnings before any imports
warnings.filterwarnings("ignore")
os.environ["PYTHONWARNINGS"] = "ignore"


# ANSI colors
CYAN = "\033[96m"
BLUE = "\033[94m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR_LINE = "\033[2K\r"

LOGO = f"""
{CYAN}{BOLD}
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
{RESET}"""

SEPARATOR = f"{DIM}{'─' * 50}{RESET}"


def clear_screen():
    os.system("clear" if os.name != "nt" else "cls")


def show_boot():
    clear_screen()
    print(LOGO)
    print(f"  {DIM}v1.0 — Assistant Vocal Intelligent{RESET}")
    print(f"  {DIM}Ctrl+C pour quitter{RESET}\n")
    print(SEPARATOR)


def show_loading(msg: str):
    print(f"  {DIM}[init]{RESET} {msg}")


def show_ready():
    print(SEPARATOR)
    print(f"\n  {CYAN}{BOLD}SYSTEME OPERATIONNEL{RESET}\n")
    print(SEPARATOR)


def show_standby():
    print(f"\n  {DIM}En attente...{RESET}", end="", flush=True)


def show_wake():
    print(f"{CLEAR_LINE}  {CYAN}{BOLD}JARVIS{RESET} {DIM}>{RESET} ", end="", flush=True)


def show_listening():
    print(f"{CLEAR_LINE}  {BLUE}[...]{RESET} ", end="", flush=True)


def show_user_preview(text: str):
    try:
        cols = os.get_terminal_size().columns
    except OSError:
        cols = 80
    prefix = "  Vous > "
    max_text = cols - len(prefix) - 2
    truncated = text[:max_text] if len(text) > max_text else text
    print(f"{CLEAR_LINE}  {DIM}Vous > {truncated}{RESET}", end="", flush=True)


def show_user_text(text: str):
    print(f"{CLEAR_LINE}  {BOLD}Vous{RESET} {DIM}>{RESET} {text}")


def show_jarvis_start():
    print(f"  {CYAN}Jarvis{RESET} {DIM}>{RESET} ", end="", flush=True)


def show_jarvis_token(text: str):
    print(text, end="", flush=True)


def show_jarvis_end():
    print()


def show_end_conversation():
    print(f"\n{SEPARATOR}")


def show_shutdown():
    print(f"\n\n  {DIM}Extinction...{RESET}\n")

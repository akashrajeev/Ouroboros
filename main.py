import asyncio
import os
import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI
from colorama import just_fix_windows_console

from privacy.inspector import format_privacy_report, inspect_html_file


RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════╗
║                         O U R O B O R O S                          ║
╚══════════════════════════════════════════════════════════════════════╝
"""

TAGLINE = "privacy-first browser agent"
VERSION = "internal demo"
SPINNER = "◐◓◑◒"


def color(text: str, style: str) -> str:
    if os.getenv("NO_COLOR") or not sys.stdout.isatty():
        return text
    return f"{style}{text}{RESET}"


def print_rule(char="─", width=78) -> None:
    print(color(char * width, DIM))


def print_banner() -> None:
    print(color(BANNER, CYAN))
    print(f"  {color(TAGLINE, BOLD)}  {color('•', DIM)}  {color(VERSION, DIM)}")
    print_rule()
    print(f"  {color('READY', GREEN)}  Enter a browser task and press Enter.")
    print(f"  {color('TIP', YELLOW)}    /privacy for local PII scan  •  /help for commands  •  /exit")
    print()


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OUROBOROS_MODEL", "auto"),
        base_url=os.getenv("OUROBOROS_BASE_URL", "http://127.0.0.1:31415/v1"),
        api_key=os.getenv("FREELLMAPI_API_KEY"),
        temperature=0.0,
    )


def print_help() -> None:
    print()
    print(f"  {color('COMMANDS', BOLD)}")
    print(f"  {color('/privacy', CYAN):<24} Scan the local demo page and show sanitized state")
    print(f"  {color('/help', CYAN):<24} Show available commands")
    print(f"  {color('/status', CYAN):<24} Show model and endpoint configuration")
    print(f"  {color('/clear', CYAN):<24} Clear the terminal and redraw Ouroboros")
    print(f"  {color('/exit', CYAN):<24} Quit Ouroboros")
    print()


def print_status() -> None:
    model = os.getenv("OUROBOROS_MODEL", "auto")
    base_url = os.getenv("OUROBOROS_BASE_URL", "http://127.0.0.1:31415/v1")
    key_status = color("configured", GREEN) if os.getenv("FREELLMAPI_API_KEY") else color("not set", YELLOW)
    print()
    print(f"  {color('SYSTEM STATUS', BOLD)}")
    print_rule(width=64)
    print(f"  {color('Model', DIM):<18} {model}")
    print(f"  {color('Endpoint', DIM):<18} {base_url}")
    print(f"  {color('API key', DIM):<18} {key_status}")
    print(f"  {color('Agent', DIM):<18} {color('ready', GREEN)}")
    print_rule(width=64)
    print()


def print_privacy_demo() -> None:
    demo_path = Path(__file__).resolve().parent / "demo" / "checkout.html"
    if not demo_path.exists():
        print(f"  {color('✖ Demo page not found:', RED)} {demo_path}")
        print()
        return

    started = datetime.now()
    report = inspect_html_file(demo_path)
    elapsed_ms = (datetime.now() - started).total_seconds() * 1000

    print(format_privacy_report(report))
    print(f"  SCAN TIME            {elapsed_ms:.1f} ms")
    print()


async def _status_spinner(stop_event: asyncio.Event) -> None:
    index = 0
    while not stop_event.is_set():
        frame = SPINNER[index % len(SPINNER)]
        message = f"  {color(frame, CYAN)}  browser agent is working..."
        print(f"\r{message}", end="", flush=True)
        index += 1
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=0.14)
        except asyncio.TimeoutError:
            continue


def _clear_status_line() -> None:
    print("\r" + " " * 64 + "\r", end="", flush=True)


def _compact_task(task: str, max_len: int = 68) -> str:
    task = " ".join(task.split())
    if len(task) <= max_len:
        return task
    return task[: max_len - 3] + "..."


def print_task_header(task: str) -> None:
    print()
    print(f"  {color('TASK', BOLD)}")
    print(f"  {color('›', MAGENTA)} {_compact_task(task)}")
    print()


async def run_task(llm: ChatOpenAI, task: str) -> None:
    started = datetime.now()
    stop_event = asyncio.Event()
    spinner_task = asyncio.create_task(_status_spinner(stop_event))

    print_task_header(task)

    try:
        agent = Agent(task=task, llm=llm)
        result = await agent.run()
    except Exception as exc:
        stop_event.set()
        with suppress(asyncio.CancelledError):
            await spinner_task
        _clear_status_line()
        print(f"  {color('✖ FAILED', RED)}")
        print(f"  {color(type(exc).__name__ + ':', DIM)} {exc}")
        print()
        return
    finally:
        stop_event.set()
        with suppress(asyncio.CancelledError):
            await spinner_task
        _clear_status_line()

    elapsed = (datetime.now() - started).total_seconds()
    print(f"  {color('✓ COMPLETED', GREEN)}  {color(f'{elapsed:.1f}s', BOLD)}")
    print()
    print(f"  {color('RESULT', BOLD)}")
    print_rule(width=64)
    print(result)
    print_rule(width=64)
    print()


async def cli() -> None:
    load_dotenv()
    just_fix_windows_console()
    print_banner()
    llm = build_llm()

    while True:
        try:
            task = input(color("  ouroboros › ", MAGENTA)).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            print(f"  {color('Ouroboros shutting down.', DIM)}")
            return

        if not task:
            continue

        command = task.lower()
        if command in {"/exit", "/quit"}:
            print(f"\n  {color('Ouroboros shutting down.', DIM)}\n")
            return
        if command == "/help":
            print_help()
            continue
        if command == "/status":
            print_status()
            continue
        if command == "/privacy":
            print_privacy_demo()
            continue
        if command == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            print_banner()
            continue
        if task.startswith("/"):
            print(f"  {color('Unknown command.', YELLOW)} Use /help.\n")
            continue

        await run_task(llm, task)


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        print(f"\n  {color('Ouroboros shutting down.', DIM)}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

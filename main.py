import asyncio
import json
import os
import sys
import time
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI
from browser_use.browser import BrowserProfile, BrowserSession
from colorama import just_fix_windows_console

from privacy.browser_observer import observe_current_page, protect_live_observation
from privacy.inspector import format_privacy_report, inspect_html_file
from privacy.secure_agent import PrivacyBoundaryError, run_privacy_task


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
    print(f"  {color('TIP', YELLOW)}    /demo opens the controlled checkout  •  /live scans the current page")
    print(f"  {color('SECURE', GREEN)}  /secure <task> uses sanitized state for remote reasoning")
    print(f"  {color('HELP', DIM)}    /help for commands  •  /exit")
    print()


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OUROBOROS_MODEL", "auto"),
        base_url=os.getenv("OUROBOROS_BASE_URL", "http://127.0.0.1:31415/v1"),
        api_key=os.getenv("FREELLMAPI_API_KEY"),
        temperature=0.0,
    )


def build_browser_session() -> BrowserSession:
    return BrowserSession(
        browser_profile=BrowserProfile(
            keep_alive=True,
            headless=False,
        )
    )


def print_help() -> None:
    print()
    print(f"  {color('COMMANDS', BOLD)}")
    print(f"  {color('/demo', CYAN):<30} Open the controlled Ouroboros checkout page")
    print(f"  {color('/live', CYAN):<30} Inspect and sanitize the tracked live browser page")
    print(f"  {color('/secure <task>', CYAN):<30} Send only sanitized state for reasoning; execute locally")
    print(f"  {color('/privacy', CYAN):<30} Scan the local demo HTML fixture")
    print(f"  {color('/help', CYAN):<30} Show available commands")
    print(f"  {color('/status', CYAN):<30} Show model and endpoint configuration")
    print(f"  {color('/clear', CYAN):<30} Clear the terminal and redraw Ouroboros")
    print(f"  {color('/exit', CYAN):<30} Quit Ouroboros")
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

    started = time.perf_counter()
    report = inspect_html_file(demo_path)
    elapsed_ms = (time.perf_counter() - started) * 1000

    print(format_privacy_report(report))
    print(f"  SCAN TIME            {elapsed_ms:.2f} ms")
    print()


def print_live_privacy(protected: dict) -> None:
    state = protected["state"]
    page = state.get("page", {})

    print()
    print(f"  {color('OUROBOROS  /  LIVE PRIVACY GATE', BOLD)}")
    print_rule(width=64)
    print(f"  {color('URL', DIM):<18} {page.get('url', '')}")
    print(f"  {color('PAGE', DIM):<18} {page.get('title', '')}")
    print(f"  {color('SENSITIVE FIELDS', DIM):<18} {protected['detectionCount']}")
    print(f"  {color('FIELDS REDACTED', DIM):<18} {protected['redactedCount']}")
    print(f"  {color('LEAKAGE CHECK', DIM):<18} {protected['leakageCheck']}")
    print()
    print(f"  {color('SANITIZED AGENT STATE', BOLD)}")
    print_rule(width=64)

    for element in state.get("elements", []):
        kinds = ", ".join(element.get("detectedTypes", [])) or "SAFE"
        value = element.get("value", "") or ""
        label = element.get("name", element.get("id", ""))
        if len(label) > 20:
            label = label[:17] + "..."
        print(f"  {label:<20} → {value:<20} [{kinds}]")

    print_rule(width=64)
    print(f"  {color('RAW PII TRANSMITTED', DIM):<24} {0 if protected['leakageCheck'] == 'PASS' else 'BLOCKED'}")
    print()


def print_model_handoff(result: dict) -> None:
    payload_text = result.get("model_input", "")
    try:
        payload = json.loads(payload_text)
    except (TypeError, json.JSONDecodeError):
        payload = {}

    print(f"  {color('REMOTE MODEL INPUT  /  PRIVACY RECEIPT', BOLD)}")
    print_rule(width=64)
    print(f"  {color('BOUNDARY CHECK', DIM):<24} {color('PASS', GREEN)}")
    print(f"  {color('RAW PII IN PAYLOAD', DIM):<24} {result.get('model_input_raw_pii', 'UNKNOWN')}")
    print(f"  {color('PAYLOAD SHA256', DIM):<24} {result.get('model_input_sha256', '')}")
    print()
    print(f"  {color('EXACT SAFE CONTENT SENT TO MODEL', DIM)}")
    print_rule(width=64)
    print(f"  task       : {payload.get('task', '')}")
    page = payload.get('page', {})
    print(f"  page       : {page.get('title', '')}")
    for element in payload.get('elements', []):
        value = element.get('value', '')
        name = element.get('name', element.get('id', ''))
        detected = ",".join(element.get('detectedTypes', [])) or "SAFE"
        print(f"  {name:<12} → {value:<18} [{detected}]")
    print_rule(width=64)
    print()


def print_secure_result(result: dict) -> None:
    protected = result["protected"]
    action = result["action"]
    print_live_privacy(protected)
    print_model_handoff(result)
    print(f"  {color('SERVER ACTION', BOLD)}")
    print_rule(width=64)
    if action["action"] == "click":
        print(f"  click → {action['target_id']}")
    else:
        print("  noop")
    if result.get("model_reason"):
        print(f"  {color('REASON', DIM)} {result['model_reason']}")
    print_rule(width=64)
    print(f"  {color('✓ LOCAL EXECUTION', GREEN)} action applied to the live page")
    print()


async def open_demo(browser_session: BrowserSession):
    demo_url = os.getenv("OUROBOROS_DEMO_URL", "http://127.0.0.1:8000/demo/checkout.html")
    try:
        await browser_session.start()
        page = await browser_session.new_page(demo_url)
        print(f"  {color('✓ DEMO OPENED', GREEN)}  {demo_url}")
        print()
        return page
    except Exception as exc:
        print(f"  {color('✖ DEMO OPEN FAILED', RED)}")
        print(f"  {color(type(exc).__name__ + ':', DIM)} {exc}")
        print(f"  {color('TIP', YELLOW)} Start the demo server with: python -m http.server 8000")
        print()
        return None


async def inspect_live_page(browser_session: BrowserSession, page=None) -> None:
    started = time.perf_counter()
    try:
        observation = await observe_current_page(browser_session, page=page)
        protected = protect_live_observation(observation)
    except Exception as exc:
        print(f"\n  {color('✖ LIVE SCAN FAILED', RED)}")
        print(f"  {color(type(exc).__name__ + ':', DIM)} {exc}")
        print("  ")
        return

    elapsed_ms = (time.perf_counter() - started) * 1000
    print_live_privacy(protected)
    print(f"  LIVE SCAN TIME       {elapsed_ms:.2f} ms")
    print()


async def run_secure_task(llm: ChatOpenAI, page, task: str) -> None:
    if page is None:
        print(f"  {color('✖ NO ACTIVE PAGE', RED)} Run /demo first.")
        print()
        return

    started = time.perf_counter()
    stop_event = asyncio.Event()
    spinner_task = asyncio.create_task(_status_spinner(stop_event))
    print_task_header(task)
    try:
        result = await run_privacy_task(llm, page, task)
    except PrivacyBoundaryError as exc:
        stop_event.set()
        with suppress(asyncio.CancelledError):
            await spinner_task
        _clear_status_line()
        print(f"  {color('✖ BLOCKED BY PRIVACY GATE', RED)}")
        print(f"  {color(str(exc), DIM)}")
        print()
        return
    except Exception as exc:
        stop_event.set()
        with suppress(asyncio.CancelledError):
            await spinner_task
        _clear_status_line()
        print(f"  {color('✖ SECURE TASK FAILED', RED)}")
        print(f"  {color(type(exc).__name__ + ':', DIM)} {exc}")
        print()
        return
    finally:
        stop_event.set()
        with suppress(asyncio.CancelledError):
            await spinner_task
        _clear_status_line()

    elapsed_ms = (time.perf_counter() - started) * 1000
    print_secure_result(result)
    print(f"  SECURE TASK TIME      {elapsed_ms:.0f} ms")
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


async def run_task(llm: ChatOpenAI, browser_session: BrowserSession, task: str) -> None:
    started = datetime.now()
    stop_event = asyncio.Event()
    spinner_task = asyncio.create_task(_status_spinner(stop_event))

    print_task_header(task)

    try:
        agent = Agent(task=task, llm=llm, browser_session=browser_session)
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
    browser_session = build_browser_session()
    active_page = None

    try:
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
            if command == "/live":
                await inspect_live_page(browser_session, page=active_page)
                continue
            if command == "/demo":
                page = await open_demo(browser_session)
                if page is not None:
                    active_page = page
                continue
            if command.startswith("/secure"):
                secure_task = task[len("/secure"):].strip()
                if not secure_task:
                    secure_task = "Place the test order"
                await run_secure_task(llm, active_page, secure_task)
                continue
            if command == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_banner()
                continue
            if task.startswith("/"):
                print(f"  {color('Unknown command.', YELLOW)} Use /help.\n")
                continue

            await run_task(llm, browser_session, task)
    finally:
        with suppress(Exception):
            await browser_session.kill()


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        print(f"\n  {color('Ouroboros shutting down.', DIM)}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()

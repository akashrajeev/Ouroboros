import asyncio
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI


BANNER = r'''
  ██████╗ ██╗   ██╗██████╗  ██████╗ ██████╗  ██████╗ ██████╗  ██████╗ ███████╗
 ██╔═══██╗██║   ██║██╔══██╗██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔════╝
 ██║   ██║██║   ██║██████╔╝██║   ██║██████╔╝██████╔╝██████╔╝██████╔╝███████╗
 ██║   ██║██║   ██║██╔══██╗██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██╔══██╗╚════██║
 ╚██████╔╝╚██████╔╝██║  ██║╚██████╔╝██║  ██║██║     ██║  ██║██║  ██║███████║
  ╚═════╝  ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝
'''

TAGLINE = "Privacy-first browser agent"


def print_banner() -> None:
    print(BANNER)
    print(f"  {TAGLINE}")
    print("  " + "─" * 72)
    print("  Enter a browser task.  /help for commands  •  /status  •  /exit")
    print()


def build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OUROBOROS_MODEL", "auto"),
        base_url=os.getenv("OUROBOROS_BASE_URL", "http://127.0.0.1:31415/v1"),
        api_key=os.getenv("FREELLMAPI_API_KEY"),
        temperature=0.0,
    )


def print_help() -> None:
    print("  Commands")
    print("  /help    Show available commands")
    print("  /status  Show model and endpoint configuration")
    print("  /clear   Clear the terminal")
    print("  /exit    Quit Ouroboros")
    print()


def print_status() -> None:
    model = os.getenv("OUROBOROS_MODEL", "auto")
    base_url = os.getenv("OUROBOROS_BASE_URL", "http://127.0.0.1:31415/v1")
    key_status = "configured" if os.getenv("FREELLMAPI_API_KEY") else "not set"
    print("  ┌─ STATUS ────────────────────────────────────────────────────────────┐")
    print(f"  │ Model:    {model:<58}│")
    print(f"  │ Endpoint: {base_url:<58}│")
    print(f"  │ API key:  {key_status:<58}│")
    print("  └──────────────────────────────────────────────────────────────────────┘")
    print()


async def run_task(llm: ChatOpenAI, task: str) -> None:
    started = datetime.now()

    print()
    print("  ┌─ TASK ──────────────────────────────────────────────────────────────┐")
    print(f"  │ {task[:68]:<68} │")
    print("  └──────────────────────────────────────────────────────────────────────┘")
    print("  ◉ Browser agent running…")

    try:
        agent = Agent(task=task, llm=llm)
        result = await agent.run()
    except Exception as exc:
        print()
        print("  ✖ Task failed")
        print(f"    {type(exc).__name__}: {exc}")
        print()
        return

    elapsed = (datetime.now() - started).total_seconds()
    print()
    print("  ┌─ RESULT ────────────────────────────────────────────────────────────┐")
    print(f"  │ Completed in {elapsed:.1f}s{' ' * max(0, 56 - len(f'Completed in {elapsed:.1f}s'))}│")
    print("  └──────────────────────────────────────────────────────────────────────┘")
    print(result)
    print()


async def cli() -> None:
    load_dotenv()
    print_banner()
    llm = build_llm()

    while True:
        try:
            task = input("  ouroboros › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye.")
            return

        if not task:
            continue

        command = task.lower()
        if command in {"/exit", "/quit"}:
            print("\n  Goodbye.")
            return
        if command == "/help":
            print_help()
            continue
        if command == "/status":
            print_status()
            continue
        if command == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            print_banner()
            continue
        if task.startswith("/"):
            print("  Unknown command. Use /help.\n")
            continue

        await run_task(llm, task)


def main() -> None:
    try:
        asyncio.run(cli())
    except KeyboardInterrupt:
        print("\n  Goodbye.")
        sys.exit(0)


if __name__ == "__main__":
    main()

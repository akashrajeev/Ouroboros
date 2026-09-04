# Ouroboros — Requirements & Setup

This folder contains the runtime prerequisites for the current Ouroboros browser-agent prototype and its local privacy demo.

## 1. System prerequisites

- Python 3.11 or newer.
- A supported desktop browser. The current prototype is intended to run with Chromium/Chrome on the local machine; Firefox support is part of the planned privacy-extension architecture, not the current prototype path.
- Internet access during installation so Python packages and the browser runtime can be installed.
- A running OpenAI-compatible local LLM endpoint for the browser-agent path, unless you change `OUROBOROS_BASE_URL` and credentials to another provider.

## 2. Python environment

### Windows PowerShell

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements\requirements.txt
```

### macOS / Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements/requirements.txt
```

## 3. Install the browser runtime

Install the browser runtime required by the browser-agent dependency:

```bash
uvx browser-use install
```

If `uv` is not installed, install `uv` first or use the equivalent browser runtime installation method for your environment.

## 4. Environment variables

Create a `.env` file at the repository root:

```env
OUROBOROS_MODEL=auto
OUROBOROS_BASE_URL=http://127.0.0.1:31415/v1
FREELLMAPI_API_KEY=your-local-api-key
OUROBOROS_DEMO_URL=http://127.0.0.1:8000/demo/checkout.html
```

The CLI defaults to `auto`, `http://127.0.0.1:31415/v1`, and the local checkout URL when those values are omitted.

Do not commit `.env` or real API keys.

## 5. Run Ouroboros

From the repository root, with the virtual environment activated:

```bash
python main.py
```

Enter a natural-language browser task at the `ouroboros ›` prompt.

Useful commands:

```text
/demo
/live
/privacy
/help
/status
/clear
/exit
```

`/demo` opens the controlled checkout page in the same persistent BrowserSession used by the agent. Start the demo server first:

```bash
python -m http.server 8000
```

Then `/live` evaluates the current browser page locally, detects sensitive fields using the existing deterministic detectors, sanitizes the values with the privacy policy, and verifies that the original sensitive values do not survive in the agent-facing state.

`/privacy` remains the static HTML fixture check. It is useful for regression testing; `/live` is the browser-integrated privacy path.

## 6. Dependency notes

`browser-use` is pinned in `requirements.txt` for reproducible browser-agent installs. `colorama` is included so the CLI styling renders correctly on Windows terminals. The project does not need a separate `playwright` entry in the requirements for the current `main.py` entrypoint.

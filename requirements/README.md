# Ouroboros — Requirements & Setup

This folder contains the runtime prerequisites for the current Ouroboros browser-agent prototype and its local privacy demo.

## 1. System prerequisites

- Python 3.11 or newer.
- A supported desktop browser. The current prototype is intended to run with Chromium/Chrome on the local machine; Firefox support is part of the planned privacy-extension architecture, not the current prototype path.
- Internet access during installation so Python packages and the browser runtime can be installed.
- OpenCode Zen access for the default Muse Spark 1.3 Contributor Free model, or another OpenAI-compatible endpoint if you override the model and base URL.

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
# Default Ouroboros model: Muse Spark 1.3 Contributor Free through OpenCode Zen
OUROBOROS_MODEL=muse-spark-1.3-contributor-free
OUROBOROS_BASE_URL=https://opencode.ai/zen/v1
OPENCODE_ZEN_API_KEY=your-opencode-zen-api-key
OUROBOROS_REASONING_EFFORT=high
OUROBOROS_MAX_OUTPUT_TOKENS=16384

OUROBOROS_DEMO_URL=http://127.0.0.1:8000/demo/checkout.html
```

`OPENCODE_ZEN_API_KEY` is the preferred credential variable. `OUROBOROS_API_KEY` and the previous `FREELLMAPI_API_KEY` name are still accepted for compatibility. Do not commit `.env` or real API keys.

The default model is served by OpenCode Zen through its Responses API. The model is currently listed as free for a limited time, but OpenCode Zen still requires authentication/API-key access. citeturn705945search0turn705945search2

## 5. Run and test Ouroboros

From the repository root, with the virtual environment activated:

```bash
python -m unittest discover -s tests -v
```

Start the controlled demo server in one terminal:

```bash
python -m http.server 8000
```

Then start Ouroboros in a second terminal:

```bash
python main.py
```

Useful commands:

```text
/demo
/live
/secure <task>
/privacy
/help
/status
/clear
/exit
```

`/demo` opens the controlled checkout page in the same persistent `BrowserSession` used by the CLI. `/live` evaluates that exact live page locally, detects sensitive fields, sanitizes their values, and verifies that raw values do not survive in the agent-facing state.

`/secure <task>` is the internal privacy-preserving reasoning demo. It sends only the sanitized state to the OpenCode Zen Responses API, expects a structured click/no-op decision, validates the decision locally, and executes the approved action on the live browser page. The current secure executor intentionally supports safe button clicks only; broader browser actions are a later stage.

Normal browser tasks use the same Muse Spark adapter directly through Browser Use's `Agent`, with Browser Use's browser control unchanged.

## 6. Dependency notes

`browser-use` is pinned in `requirements.txt` for reproducible browser-agent installs. The Muse Spark adapter uses dependencies already supplied by Browser Use, so no extra LLM SDK package is required. `colorama` is included so the CLI styling renders correctly on Windows terminals. The project does not need a separate `playwright` entry in the requirements for the current `main.py` entrypoint.

# Ouroboros — Requirements & Setup

This folder contains the runtime prerequisites for the current Ouroboros browser-agent prototype.

## 1. System prerequisites

- Python 3.11 or newer. Browser Use currently requires Python >=3.11 and <4.0.
- A supported desktop browser. The current prototype is intended to run with Chromium/Chrome on the local machine; Firefox support is part of the planned privacy-extension architecture, not the current prototype path.
- Internet access during installation so Python packages and the browser runtime can be installed.
- A running OpenAI-compatible local LLM endpoint for the current configuration, unless you change `OUROBOROS_BASE_URL` and credentials to another provider.

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

## 3. Install the Browser Use browser runtime

Browser Use's current quickstart installs its browser runtime with:

```bash
uvx browser-use install
```

If you do not have `uv`, install it first, or use the equivalent Browser Use installation instructions for your environment.

## 4. Environment variables

Create a `.env` file at the repository root. The current CLI reads:

```env
OUROBOROS_MODEL=auto
OUROBOROS_BASE_URL=http://127.0.0.1:31415/v1
FREELLMAPI_API_KEY=your-local-api-key
```

`OUROBOROS_MODEL` defaults to `auto` and `OUROBOROS_BASE_URL` defaults to `http://127.0.0.1:31415/v1` when omitted.

Do not commit `.env` or real API keys.

## 5. Run Ouroboros

From the repository root, with the virtual environment activated:

```bash
python main.py
```

Then enter a natural-language browser task at the `ouroboros ›` prompt.

Useful CLI commands:

```text
/help
/status
/clear
/exit
```

## 6. Dependency notes

`browser-use` is pinned in `requirements.txt` so the prototype has a reproducible browser-agent dependency. Browser Use installs its own Python dependency tree through pip/uv. The project does not need a separate `playwright` requirement for the current `main.py` entrypoint.

The current prototype uses Browser Use's Python API and an OpenAI-compatible endpoint. The local privacy-preserving extension, ONNX/WebGPU vision pipeline, sanitization layers, and agent-state adapter described in the SIH architecture are planned follow-on work and are not prerequisites for this initial prototype.

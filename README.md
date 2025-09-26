# VLC Ollama Translate

Port of the [PotPlayer ChatGPT Translate](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate) plugin to VLC.  It reproduces PotPlayer's ChatGPT-driven subtitle workflow by pairing a Python backend with a VLC Lua extension, so you can reuse the same configuration strings, caching strategy, and prompt templates inside VLC.

## Features

- **Drop-in configuration compatibility** – accepts the original `model|url|nullkey|delay|retry|cache` login string and keeps the same defaults for token budgets, retries, and cache behaviour.
- **Context-aware translations** – mirrors PotPlayer's prompt engineering, context window management, and optional Response caching for higher throughput.
- **CLI + GUI** – ships both a `vlc-ollama-translate` command-line tool and a VLC side panel that share the same configuration storage.
- **Persistent settings** – configuration is saved to `~/.config/vlc_ollama_translate/config.json` (or the platform-specific equivalent) so VLC and the CLI stay in sync.
- **RTL safe output** – automatically prefixes Arabic, Farsi, and Hebrew translations with the right-to-left mark.

## Requirements

- Python **3.9 or newer** with internet access to reach your ChatGPT-compatible API.
- VLC **3.x or newer** with Lua extensions enabled.
- An API endpoint that understands the OpenAI Chat Completions or Responses format.

## Installation

**Quick start:** run the automated installer to install the Python backend and copy the Lua extension in one step:

```bash
python scripts/install.py
```

Use `--user` to perform a user-level pip install or `--skip-pip` if the package is already available in your environment.  The script detects the correct VLC extensions folder for Windows, macOS, and Linux, but you can override the destination with `--extensions-dir /custom/path` when required.

If you prefer manual setup, follow these steps:

1. Install the Python package (a virtual environment is recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
   pip install .
   ```

2. Copy `lua/extensions/chatgpt_translate.lua` into VLC's extensions folder:
   - Windows: `%APPDATA%\vlc\lua\extensions`
   - Linux: `~/.local/share/vlc/lua/extensions`
   - macOS: `~/Library/Application Support/org.videolan.vlc/lua/extensions`

3. Restart VLC.  You should now see **ChatGPT Translate** under `View → Add Interface → Extensions` (or directly in the `View` menu on some versions).

4. Confirm the backend is available by running:
   ```bash
   vlc-ollama-translate show-config
   ```
   The command prints the currently stored settings; if it fails, ensure the virtual environment (or interpreter) used for installation is active.

## Configuring the translator

Both the CLI and the Lua panel write to the same JSON file at `~/.config/vlc_ollama_translate/config.json` (Windows: `%APPDATA%\vlc_ollama_translate\config.json`).  There are two main ways to configure it:

### Using the login string

The **Model | URL | nullkey | delay | retry | cache** field accepts the PotPlayer-style pipe-separated string.  Recognised tokens are:

| Token pattern      | Meaning |
|--------------------|---------|
| `gpt-4o-mini`, `gpt-5-nano`, … | Selects the model name sent to the API. |
| `https://api.openai.com/...`   | Overrides the API base URL. Use `http://` to disable TLS if your endpoint allows it. |
| `nullkey`                       | Indicates that the target API does not require an API key. |
| `delay=2500` or bare integer `2500` | Adds a delay (in milliseconds) between calls. |
| `retry3` or bare integer `3`   | Sets the retry preset used by the backend. |
| `cache=auto` / `cache=off`     | Enables or disables the Responses caching layer. |

### Via the CLI

For scripted setups you can use the dedicated `configure` subcommand:

```bash
vlc-ollama-translate configure \
  --login-string "gpt-4o|https://api.openai.com/v1/responses|nullkey|delay=1500|retry3|cache=auto" \
  --api-key sk-... \
  --source-language zh-CN \
  --target-language en
```

All CLI options are additive, so you can update individual fields without rewriting the whole string (for example, `vlc-ollama-translate configure --api-key sk-...`).

## Using the VLC extension

1. Open VLC and choose **View → ChatGPT Translate** to display the side panel.
2. Fill in:
   - **Model | URL | nullkey | delay | retry | cache** – paste your login string; press **Save configuration** after editing.
   - **API Key** – optional if `nullkey` is present.
   - **Source/Target language** – dropdowns replicate the PotPlayer list (`Auto` leaves detection to the model).
3. Provide the path to an `.srt` subtitle file.  The panel auto-fills this field with the subtitle currently loaded in VLC when available, and leaving **Output path** empty defaults to `<input>.translated.srt`.
4. Press **Translate**.  The panel streams progress to the status bar; the translated file writes the translated line above the original subtitle so both remain visible.

> **Tip:** The Lua panel simply shells out to the Python CLI.  If you are running VLC from a different Python environment, make sure `vlc-ollama-translate` is on the PATH for that session.

## Command-line usage

The backend can be automated outside of VLC.

```bash
usage: vlc-ollama-translate [-h] {configure,show-config,translate} ...
```

- `configure` – write configuration values to disk. Options include:
  - `--login-string`, `--api-key`, `--model`, `--api-url`
  - `--delay-ms`, `--retry-mode`, `--context-budget`, `--truncation-mode`
  - `--cache-mode`, `--source-language`, `--target-language`
- `show-config` – print all stored values in `key=value` form.
- `translate` – translate an `.srt` file using the stored configuration.
  - Required: `--input PATH`, `--output PATH`
  - Optional: `--include-original` (keeps the source line above the translation), `--api-key`, `--source-language`, `--target-language`, `--require-key`

The translator honours the configured token budget, truncation mode, retry preset, and caching strategy automatically.  Output files are written in UTF-8.

## Troubleshooting

- **`vlc-ollama-translate` not found** – ensure you installed the package into the same Python environment VLC uses, or activate the virtual environment before launching VLC.
- **Authentication errors** – verify the API key via `vlc-ollama-translate translate --require-key ...` to force a failure if it is missing.
- **Unexpected language codes** – the supported set mirrors the PotPlayer plugin; refer to `vlc_ollama_translate/languages.py` for the full list.
- **Response cache issues** – set `cache=off` in the login string to disable the caching path if your API does not support the Responses endpoint.

## License

This port follows the licensing terms of the upstream repositories.  See [LICENSE](LICENSE) for details.

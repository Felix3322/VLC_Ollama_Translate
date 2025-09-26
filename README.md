# VLC Ollama Translate

VLC Ollama Translate is a full port of the
[PotPlayer ChatGPT Translate](https://github.com/Felix3322/PotPlayer_ChatGPT_Translate)
plugin.  It brings the same real-time, context aware subtitle translation
experience to VLC by combining a Python backend with a native VLC Lua
extension.  The project keeps all of the features of the original
plugin, including:

- ChatGPT/Responses compatible translation pipeline with context
  caching and smart trimming.
- Model, API URL, retry and delay configuration compatible with the
  original PotPlayer installer.
- Language selection identical to the AngleScript version, including
  proper handling for RTL output.
- Token budget heuristics and customisable limits for different
  models.
- Integration with VLC through a GUI extension that mirrors the
  PotPlayer control panel.

## Project structure

- `vlc_ollama_translate/` – Python package that implements the
  translation engine, configuration handling, model heuristics and CLI
  tooling.
- `lua/extensions/chatgpt_translate.lua` – VLC Lua extension that
  exposes the user interface, persists configuration and executes the
  translator.
- `pyproject.toml` – Package metadata with an entry point named
  `vlc-ollama-translate` used by both the command line interface and
  the Lua extension.

## Installation

1. Install the Python package in your VLC environment:

   ```bash
   pip install .
   ```

2. Copy `lua/extensions/chatgpt_translate.lua` into your VLC extensions
   directory (e.g. `%APPDATA%\vlc\lua\extensions` on Windows or
   `~/.local/share/vlc/lua/extensions` on Linux).

3. Launch VLC and enable the *ChatGPT Translate* extension from the
   `View` menu.

## Usage

1. Open the *ChatGPT Translate* panel in VLC.
2. Enter your model/API configuration in the same `model|url|nullkey|delay|retry|cache`
   format used by the PotPlayer plugin and provide an API key if
   required.
3. Choose the source and target languages.
4. Provide a subtitle file path or allow the tool to generate an output
   file next to the original.
5. Click **Translate** to create a translated subtitle track.  The
   translation reuses the PotPlayer prompts and context management,
   ensuring identical output quality.

You can also drive the backend from the command line:

```bash
vlc-ollama-translate configure --api-key sk-... --model gpt-4o
vlc-ollama-translate translate --input input.srt --output translated.srt --include-original
```

--[[
ChatGPT Translate VLC extension.

This script provides a lightweight user interface that mirrors the
PotPlayer ChatGPT Translate plugin.  It exposes the most important
configuration options and calls the Python translation backend shipped
with this repository.
--]]

local languages = {
  "",
  "af", "sq", "am", "ar", "hy", "az", "eu", "be", "bn", "bs", "bg", "ca", "ceb", "ny", "zh-CN",
  "zh-TW", "co", "hr", "cs", "da", "nl", "en", "eo", "et", "tl", "fi", "fr", "fy", "gl", "ka",
  "de", "el", "gu", "ht", "ha", "haw", "he", "hi", "hmn", "hu", "is", "ig", "id", "ga", "it",
  "ja", "jw", "kn", "kk", "km", "ko", "ku", "ky", "lo", "la", "lv", "lt", "lb", "mk", "ms",
  "mg", "ml", "mt", "mi", "mr", "mn", "my", "ne", "no", "or", "ps", "fa", "pl", "pt", "pa", "ro",
  "ru", "sm", "gd", "sr", "st", "sn", "sd", "si", "sk", "sl", "so", "es", "su", "sw", "sv", "tg",
  "ta", "te", "th", "tr", "uk", "ur", "ug", "uz", "vi", "cy", "xh", "yi", "yo", "zu"
}

local dlg = nil
local widgets = {}
local current_config = {}

local function escape_arg(text)
  if not text or text == "" then
    return "''"
  end
  local escaped = string.gsub(text, "'", "'\\''")
  return "'" .. escaped .. "'"
end

local function run_command(cmd)
  vlc.msg.dbg("ChatGPT Translate executing: " .. cmd)
  local handle = io.popen(cmd .. " 2>&1")
  if not handle then
    return false, "Failed to spawn helper command"
  end
  local output = handle:read("*a") or ""
  output = string.gsub(output, "%s+$", "")
  local success, _, code = handle:close()
  if success == nil then
    success = false
  end
  if success then
    return true, output
  end
  local reason = output
  if reason == "" and code then
    reason = "exit code " .. tostring(code)
  end
  return false, reason
end

local function load_config()
  local ok, output = run_command("vlc-ollama-translate show-config")
  local config = {}
  if not ok then
    return config
  end
  for line in string.gmatch(output, "[^\n]+") do
    local key, value = string.match(line, "([^=]+)=(.*)")
    if key and value then
      config[key] = value
    end
  end
  return config
end

local function build_login_value(config)
  local parts = {}
  local model = config["selected_model"] or ""
  if model ~= "" then
    table.insert(parts, model)
  end
  if config["api_url"] and config["api_url"] ~= "" then
    table.insert(parts, config["api_url"])
  end
  if (config["api_key"] or "") == "" then
    table.insert(parts, "nullkey")
  end
  if config["delay_ms"] and config["delay_ms"] ~= "0" then
    table.insert(parts, config["delay_ms"])
  end
  if config["retry_mode"] and config["retry_mode"] ~= "0" then
    table.insert(parts, "retry" .. config["retry_mode"])
  end
  if config["context_cache_mode"] and config["context_cache_mode"] ~= "" then
    table.insert(parts, "cache=" .. config["context_cache_mode"])
  end
  return table.concat(parts, "|")
end

local function populate_dropdown(dropdown, value)
  if not dropdown then return end
  for _, lang in ipairs(languages) do
    local label = lang
    if lang == "" then
      label = "Auto"
    end
    dropdown:add_value(label, lang)
  end
  if dropdown.set_value then
    if value and value ~= "" then
      dropdown:set_value(value)
    else
      dropdown:set_value("")
    end
  end
end

local function show_status(message)
  if widgets.status then
    widgets.status:set_text(message)
  else
    vlc.msg.dbg("ChatGPT Translate: " .. message)
  end
end

local function save_configuration()
  local login = widgets.login:get_text()
  local api_key = widgets.api_key and widgets.api_key:get_text() or ""
  local source = widgets.source and widgets.source:get_value() or ""
  local target = widgets.target and widgets.target:get_value() or ""
  local args = {
    "vlc-ollama-translate", "configure",
    "--login-string", login,
    "--api-key", api_key,
    "--source-language", source,
    "--target-language", target,
  }
  local cmd = {}
  for _, value in ipairs(args) do
    table.insert(cmd, escape_arg(value))
  end
  local ok, output = run_command(table.concat(cmd, " "))
  if ok then
    current_config = load_config()
    if widgets.login and widgets.login.set_text then
      widgets.login:set_text(build_login_value(current_config))
    end
    if widgets.source and widgets.source.set_value then
      widgets.source:set_value(current_config["source_language"] or "")
    end
    if widgets.target and widgets.target.set_value then
      widgets.target:set_value(current_config["target_language"] or "en")
    end
    show_status("Configuration saved")
  else
    show_status("Failed to save configuration: " .. output)
  end
end

local function translate_subtitles()
  local input_path = widgets.subtitle_path:get_text()
  if not input_path or input_path == "" then
    show_status("Please provide an input subtitle path")
    return
  end
  local output_path = widgets.output_path:get_text()
  if not output_path or output_path == "" then
    output_path = input_path .. ".translated.srt"
  end
  local args = {
    "vlc-ollama-translate", "translate",
    "--input", input_path,
    "--output", output_path,
    "--include-original",
  }
  if widgets.api_key:get_text() ~= "" then
    table.insert(args, "--api-key")
    table.insert(args, widgets.api_key:get_text())
  end
  local cmd = {}
  for _, value in ipairs(args) do
    table.insert(cmd, escape_arg(value))
  end
  local ok, output = run_command(table.concat(cmd, " "))
  if ok then
    show_status(output)
  else
    show_status("Translation failed: " .. output)
  end
end

local function create_dialog()
  dlg = vlc.dialog("ChatGPT Translate")
  widgets.login_label = dlg:add_label("Model | URL | nullkey | delay | retry | cache", 1, 1, 3, 1)
  widgets.login = dlg:add_text_input(build_login_value(current_config), 1, 2, 3, 1)
  widgets.api_label = dlg:add_label("API Key", 1, 3, 1, 1)
  widgets.api_key = dlg:add_text_input(current_config["api_key"] or "", 1, 4, 3, 1)
  widgets.source_label = dlg:add_label("Source language", 1, 5, 1, 1)
  widgets.source = dlg:add_dropdown(1, 6, 1, 1)
  widgets.target_label = dlg:add_label("Target language", 2, 5, 1, 1)
  widgets.target = dlg:add_dropdown(2, 6, 1, 1)
  populate_dropdown(widgets.source, current_config["source_language"])
  populate_dropdown(widgets.target, current_config["target_language"] or "en")
  widgets.save_btn = dlg:add_button("Save configuration", save_configuration, 3, 6, 1, 1)

  widgets.subtitle_label = dlg:add_label("Subtitle file (SRT)", 1, 7, 1, 1)
  widgets.subtitle_path = dlg:add_text_input("", 1, 8, 3, 1)
  widgets.output_label = dlg:add_label("Output path", 1, 9, 1, 1)
  widgets.output_path = dlg:add_text_input("", 1, 10, 3, 1)
  widgets.translate_btn = dlg:add_button("Translate", translate_subtitles, 3, 10, 1, 1)
  widgets.status = dlg:add_label("", 1, 11, 3, 1)
end

function descriptor()
  return {
    title = "ChatGPT Translate",
    version = "1.0",
    author = "ChatGPT",
    shortdesc = "ChatGPT subtitle translation",
    description = "Translate subtitles through ChatGPT compatible APIs",
  }
end

function activate()
  current_config = load_config()
  create_dialog()
  show_status("Ready")
end

function deactivate()
  if dlg then
    dlg:delete()
  end
  dlg = nil
  widgets = {}
end

function close()
  deactivate()
end

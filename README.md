<div align="center">

# MoonCode

**A Korean-first AI coding assistant in your terminal.**

Plan, edit, test, and commit — in Korean — from a full-screen TUI, powered by
[Ollama](https://ollama.com/) and local/cloud LLMs.

[Features](#features) · [Install](#installation) · [Usage](#usage) · [Commands](#slash-commands) · [Architecture](#architecture) · [Configuration](#configuration)

</div>

---

## Features

- **Korean-native interaction.** The system prompt, UI chrome, and all agent
  output are written in Korean. Designed for Korean-speaking developers who
  want a coding assistant that actually speaks their language.
- **Tool-using agent loop.** The model plans, calls tools
  (`read_file`, `edit_file`, `bash`, `grep_search`, `git_commit`, …), observes
  results, and iterates until the task is done — up to `max_iterations`.
- **Full-screen TUI.** Built on
  [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/) and
  [Rich](https://rich.readthedocs.io/). Dedicated input line, scrollable log
  pane (mouse wheel + keyboard), model-picker popup, status bar.
- **Multi-model.** Switch between Kimi K2.5, GLM 5.1/4, Qwen 3, Devstral, or
  any Ollama-compatible model at runtime via `/model`.
- **Edit safety.** Every file-modifying tool snapshots the previous state;
  `undo` rolls back the last change.
- **Project memory.** Per-workspace request/response history kept in
  `dobin_code/` so context survives across sessions.

## Installation

### Prerequisites

- **Python** 3.10 or newer
- **[Ollama](https://ollama.com/)** running locally (or a reachable cloud endpoint)
- At least one model pulled:
  ```bash
  ollama pull kimi-k2.5:cloud
  ```

### Install from GitHub

```bash
# 1. Clone the repository
git clone https://github.com/dvbin/dobin_code.git
cd dobin_code

# 2. Install Python dependencies
pip install -r requirements.txt
# (or: pip install ollama prompt_toolkit rich)

# 3. Put the launcher on your PATH
chmod +x dobin
sudo ln -s "$PWD/dobin" /usr/local/bin/dobin
```

That's it — `dobin` now works from any directory:

```bash
cd ~/my-project
dobin
```

> **How the launcher finds itself.** `dobin` resolves its own location via
> `$BASH_SOURCE`, so the symlink in `/usr/local/bin` transparently points back
> at the cloned repo. You can keep the repo anywhere; don't move it without
> re-linking.

> **Using a specific Python.** Set `DOBIN_PYTHON=/path/to/python` in your
> shell profile to pin the interpreter (useful with pyenv / conda / venv).

### Updating

```bash
cd /path/to/dobin_code
git pull
```

No reinstall needed — the symlink always points at the latest checkout.

### Uninstalling

```bash
sudo rm /usr/local/bin/dobin
rm -rf /path/to/dobin_code
rm ~/.dobin_config.json    # optional, removes saved settings
```

## Usage

From any directory:

```bash
dobin              # start in the current working directory
dobin ./my-project # start with ./my-project as the workspace
dobin --help       # show CLI help
```

Once the TUI is up, just type what you want in Korean:

```
❯ Fix the typos in README and add language tags to the example code blocks
```

The agent will list files, read the relevant ones, propose edits, run
verification commands if appropriate, and summarize the result.

### Scrolling

- **Trackpad / mouse wheel** — two-finger scroll on the log pane
- **fn + ↑ / ↓** — PageUp / PageDown
- **Ctrl-B / Ctrl-F** — page up / page down
- **Ctrl-U / Ctrl-Y** — half-page up / down
- **fn + ← / →** — Home / End (jump to top / bottom)

New messages always snap the view back to the bottom.

## Slash Commands

| Command            | What it does                               |
| ------------------ | ------------------------------------------ |
| `/help`            | Show command list                          |
| `/model`           | Open model picker (or `/model <n>` direct) |
| `/clear`           | Reset conversation & redraw banner         |
| `/history`         | Show important requests recorded this run  |
| `/dir`             | List current workspace                     |
| `/quit`, `/exit`   | Exit                                       |

> Each command also has a Korean alias (`/도움`, `/모델`, `/초기화`, `/기록`,
> `/디렉토리`, `/종료`).

## Architecture

```
MoonCode/
├── dobin                 # bash launcher (sets argv[0]=dobin, OSC title)
├── app.py                # CLI entry — parses args, builds config, starts agent
├── core/
│   ├── config.py         # model list, defaults, ~/.dobin_config.json
│   ├── agent.py          # agent loop + slash command dispatcher
│   ├── tools.py          # 14 tool definitions + execute_tool()
│   ├── memory.py         # per-workspace request/response log
│   └── tui.py            # full-screen TUI (prompt_toolkit + Rich)
└── dobin_code/           # per-workspace memory files
    ├── project.md
    └── dobin.md
```

### The agent loop

1. User types a message. TUI echoes it and calls `agent.handle_input`.
2. `ollama.chat` is invoked with the full message history and the tool
   schema from [core/tools.py](core/tools.py).
3. If the model returns `tool_calls`, each is executed via
   `execute_tool(name, args, workdir)`; the result is appended to messages
   as a `tool` role, and the loop continues.
4. When the model finally returns plain content, the TUI renders it as a
   Markdown response and the loop ends.
5. `max_iterations` (default 20) caps runaway loops.

### Available tools

File ops — `read_file`, `write_file`, `edit_file`, `replace_lines`, `undo`,
`create_directory`, `delete_path`
&nbsp;&nbsp;&nbsp;&nbsp;Search — `list_dir`, `glob_search`, `grep_search`,
`search_symbols`
&nbsp;&nbsp;&nbsp;&nbsp;Shell — `bash`
&nbsp;&nbsp;&nbsp;&nbsp;Git — `git_status`, `git_commit`

All file-modifying tools snapshot state before writing; `undo` pops the
most recent snapshot.

## Configuration

`~/.dobin_config.json` is created on first change. Fields:

| Key              | Default              | Meaning                                  |
| ---------------- | -------------------- | ---------------------------------------- |
| `model`          | `kimi-k2.5:cloud`    | Ollama model tag                         |
| `workdir`        | `cwd`                | Workspace root (overridden by CLI arg)   |
| `max_iterations` | `20`                 | Max agent tool-call rounds per message   |
| `language`       | `ko`                 | UI / prompt language                     |
| `dobin_folder`   | `dobin_code`         | Memory directory name inside workspace   |

To change models without editing the file:

```
❯ /model               # opens interactive picker
❯ /model 2             # pick by number
❯ /model glm-5.1:cloud # pick by name
```

## Development

```bash
# Run directly without the launcher
python3 app.py /path/to/project

# Syntax check
python3 -m py_compile core/*.py app.py
```

The project has no third-party test suite yet. Contributions welcome.

## License

Bindv License v1.0

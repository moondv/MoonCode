import os
import json

CONFIG_PATH = os.path.expanduser("~/.dobin_config.json")

AVAILABLE_MODELS = [
    {"name": "kimi-k2.5:cloud", "desc": "Kimi K2.5 (기본)"},
    {"name": "glm-5.1:cloud", "desc": "GLM 5.1"},
    {"name": "glm-4:cloud", "desc": "GLM 4"},
    {"name": "qwen3:cloud", "desc": "Qwen 3"},
    {"name": "devstral:cloud", "desc": "Devstral"},
]

DEFAULT_MODEL = "kimi-k2.5:cloud"

DEFAULT_CONFIG = {
    "model": DEFAULT_MODEL,
    "workdir": os.getcwd(),
    "max_iterations": None,  # None = unlimited
    "language": "en",
    "dobin_folder": "dobin_code",
    "context_window": 128_000,      # model context window (tokens)
    "auto_compact_ratio": 0.85,     # compact when estimated tokens exceed ratio × window
    "bash_consent": True,  # ask user before running bash commands
}

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        cfg = {**DEFAULT_CONFIG, **saved}
    else:
        cfg = DEFAULT_CONFIG.copy()

    # Apply language to the i18n layer as early as possible.
    from core.i18n import set_lang
    set_lang(cfg.get("language", "en"))
    return cfg

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
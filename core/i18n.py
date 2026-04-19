"""Tiny i18n layer for DOBIN CODE.

Usage:
    from core.i18n import t, set_lang
    t("help.title")          # returns the string in the current language
    set_lang("ko")           # switch

Only the user-facing surface (TUI labels, slash-command descriptions,
system prompt, status messages) goes through here. Tool descriptions
that the model consumes stay in Korean for now — they are a separate
concern.
"""

_SUPPORTED = ("en", "ko")
_current = {"lang": "en"}

STRINGS = {
    # ── system prompt (given to the model) ──
    "system_prompt": {
        "en": (
            "You are an AI coding assistant named 'DOBIN CODE'.\n\n"
            "## Role\n"
            "You help with software development tasks (writing, editing, debugging, "
            "testing, committing code).\n"
            "Write every response in English.\n\n"
            "## Workflow (follow this loop)\n"
            "1. **Plan** — analyze the request and decide which files to touch.\n"
            "   - Use `list_dir`, `glob_search` to understand the project layout.\n"
            "   - Use `search_symbols` to jump to definitions.\n"
            "   - Use `read_file` for details.\n"
            "2. **Edit** — `edit_file` (string), `replace_lines` (range), "
            "`write_file` (new file / full replace).\n"
            "3. **Test** — run `bash` for tests / builds / type checks.\n"
            "4. **Fix** — on failure, go back to step 2 based on the error log. "
            "Use `undo` if needed.\n"
            "5. **Done** — summarize what changed and what was verified in a line "
            "or two. Run `git_status` → `git_commit` when asked.\n\n"
            "## Principles\n"
            "1. Do not repeat the same tool call without reason.\n"
            "2. Remember files you have already read.\n"
            "3. Verify after editing whenever possible.\n"
            "4. Do not refactor beyond the requested scope.\n"
            "5. Do not handle secrets (passwords, keys, etc.).\n\n"
            "## Response format\n"
            "- Keep it concise. Wrap code in Markdown code blocks.\n"
            "- Call tools directly without narration; summarize after results arrive."
        ),
        "ko": (
            "당신은 'DOBIN CODE'라는 이름의 AI 코딩 어시스턴트입니다.\n\n"
            "## 역할\n"
            "소프트웨어 개발 작업(코드 작성, 수정, 디버깅, 테스트, 커밋)을 돕습니다.\n"
            "모든 응답은 한국어로 작성합니다.\n\n"
            "## 작업 루프 (반드시 따르세요)\n"
            "1. **계획(Plan)** — 요청을 분석하고 어떤 파일을 건드릴지 먼저 생각합니다.\n"
            "   - 필요 시 `list_dir`, `glob_search`로 프로젝트 구조 파악.\n"
            "   - 심볼은 `search_symbols`로 정의 위치를 즉시 찾음.\n"
            "   - 상세 로직은 `read_file`.\n"
            "2. **수정(Edit)** — `edit_file`(문자열), `replace_lines`(줄 범위), `write_file`(새 파일/전체 교체).\n"
            "3. **검증(Test)** — `bash`로 테스트/빌드/타입체크.\n"
            "4. **수정(Fix)** — 실패 시 에러 로그 기반으로 다시 2단계로. 필요하면 `undo`.\n"
            "5. **완료(Done)** — 무엇을 바꿨고 무엇이 검증됐는지 한두 줄로 요약. 요청 시 `git_status` → `git_commit`.\n\n"
            "## 핵심 원칙\n"
            "1. 같은 도구 호출을 의미 없이 반복하지 않습니다.\n"
            "2. 한 번 읽은 파일은 기억하세요.\n"
            "3. 파일 수정 후에는 가능한 경우 검증을 수행합니다.\n"
            "4. 요청 범위를 넘는 리팩토링은 하지 않습니다.\n"
            "5. 민감 정보(비밀번호, 키 등)는 다루지 않습니다.\n\n"
            "## 응답 형식\n"
            "- 간결하게. 코드는 마크다운 코드 블록으로 감쌉니다.\n"
            "- 도구 호출 시 설명 없이 바로 호출. 결과 나온 후 요약."
        ),
    },

    # ── slash command descriptions ──
    "cmd.help":     {"en": "Show commands",        "ko": "명령어 안내"},
    "cmd.model":    {"en": "Change model",         "ko": "모델 변경"},
    "cmd.clear":    {"en": "Clear conversation",   "ko": "대화 초기화"},
    "cmd.history":  {"en": "Important requests",   "ko": "중요 요청 기록"},
    "cmd.dir":      {"en": "List workspace",       "ko": "디렉토리 조회"},
    "cmd.language": {"en": "Change language",      "ko": "언어 변경"},
    "cmd.quit":     {"en": "Exit",                 "ko": "종료"},

    # ── tool labels ──
    "tool.bash":              {"en": "Shell",         "ko": "터미널 실행"},
    "tool.read_file":         {"en": "Read file",     "ko": "파일 읽기"},
    "tool.write_file":        {"en": "Write file",    "ko": "파일 쓰기"},
    "tool.edit_file":         {"en": "Edit file",     "ko": "파일 편집"},
    "tool.replace_lines":     {"en": "Replace lines", "ko": "줄 교체"},
    "tool.undo":              {"en": "Undo",          "ko": "되돌리기"},
    "tool.list_dir":          {"en": "List dir",      "ko": "디렉토리 조회"},
    "tool.glob_search":       {"en": "File search",   "ko": "파일 검색"},
    "tool.grep_search":       {"en": "Grep",          "ko": "내용 검색"},
    "tool.search_symbols":    {"en": "Symbol search", "ko": "심볼 검색"},
    "tool.create_directory":  {"en": "Mkdir",         "ko": "폴더 생성"},
    "tool.delete_path":       {"en": "Delete",        "ko": "경로 삭제"},
    "tool.git_status":        {"en": "Git status",    "ko": "Git 상태"},
    "tool.git_commit":        {"en": "Git commit",    "ko": "Git 커밋"},

    # ── status bar / misc ──
    "status.busy":        {"en": "  ⏳ working…",        "ko": "  ⏳ 작업 중…"},
    "output.empty":       {"en": "(no output)",         "ko": "(출력 없음)"},
    "output.more_lines":  {"en": " ⋯ {n} more lines",   "ko": " ⋯ {n}줄 더 있음"},
    "badge.current":      {"en": " current ",           "ko": " 현재 "},

    # ── help / messages ──
    "help.title":         {"en": "DOBIN CODE commands",       "ko": "DOBIN CODE 명령어"},
    "models.title":       {"en": "Available models",          "ko": "사용 가능한 모델"},
    "models.hint":        {"en": "Change: /model <number or name>",
                           "ko": "변경: /model <번호 또는 모델명>"},
    "history.empty":      {"en": "No important requests recorded yet.",
                           "ko": "아직 기록된 중요 요청이 없습니다."},
    "exit.bye":           {"en": "Exiting DOBIN CODE.",       "ko": "DOBIN CODE를 종료합니다."},
    "clear.done":         {"en": "Conversation cleared.",     "ko": "대화 기록을 초기화했습니다."},
    "model.changed":      {"en": "Model changed: {name}",     "ko": "모델 변경: {name}"},
    "model.error":        {"en": "Model change error: {err}", "ko": "모델 변경 오류: {err}"},
    "model.call_error":   {"en": "Model call failed: {err}",  "ko": "모델 호출 오류: {err}"},
    "unknown.cmd":        {"en": "Unknown command: {cmd}",    "ko": "알 수 없는 명령어: {cmd}"},
    "handler.error":      {"en": "Error while handling: {err}",
                           "ko": "처리 중 오류: {err}"},
    "iter.max":           {"en": "Max iterations reached.",   "ko": "최대 반복 횟수에 도달했습니다."},
    "lang.changed":       {"en": "Language: English",         "ko": "언어: 한국어"},
    "lang.usage":         {"en": "Usage: /language <en|ko>",  "ko": "사용법: /language <en|ko>"},

    # ── model picker popup ──
    "popup.title":        {"en": "  Select model",            "ko": "  모델 선택"},
    "popup.hint":         {"en": "  ↑↓ move · Enter select · Esc cancel",
                           "ko": "  ↑↓ 이동 · Enter 선택 · Esc 취소"},
}


def set_lang(lang):
    if lang in _SUPPORTED:
        _current["lang"] = lang
        return True
    return False


def get_lang():
    return _current["lang"]


def t(key, **kwargs):
    entry = STRINGS.get(key)
    if entry is None:
        return key
    s = entry.get(_current["lang"]) or entry.get("en") or key
    if kwargs:
        try:
            s = s.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return s

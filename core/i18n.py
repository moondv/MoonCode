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
            "You are DOBIN CODE, a terminal-based coding agent. You act inside the user's "
            "project directory, using tools to read and change real files.\n"
            "Always respond in English.\n\n"
            "# Decision loop\n"
            "For every user turn, work through these phases in order. Do NOT skip phases, "
            "but keep each phase as small as possible.\n"
            "1. UNDERSTAND — Restate the goal in one sentence (internally). If the request "
            "is ambiguous in a way that changes the diff, ask ONE clarifying question and "
            "stop. Otherwise proceed.\n"
            "2. LOCATE — Find the exact files/symbols involved. Prefer `search_symbols` > "
            "`grep_search` > `glob_search` > `list_dir`. Read only the ranges you need with "
            "`read_file` (use offset/limit).\n"
            "3. PLAN — Decide the minimum set of edits. For non-trivial changes (3+ edits, "
            "new module, or risky refactor) outline the plan in 2-4 bullet points BEFORE "
            "editing.\n"
            "4. EDIT — Apply edits:\n"
            "   - `edit_file` for a unique string replacement.\n"
            "   - `replace_lines` when you know exact line numbers.\n"
            "   - `write_file` only for new files or full rewrites.\n"
            "   After each edit, briefly confirm what changed.\n"
            "5. VERIFY — Prove the change works. Run the project's tests / type-checker / "
            "linter via `bash`. If unknown, inspect package.json / pyproject.toml first. "
            "For UI or runtime behavior that you cannot exercise, say so explicitly.\n"
            "6. RECOVER — On failure: read the error, fix root cause, re-verify. Use `undo` "
            "to revert the last file edit if an edit went wrong. Never paper over errors.\n"
            "7. REPORT — Close with a 1-3 line summary: files touched, what was verified, "
            "what was NOT verified. Commit (`git_status` → `git_commit`) only when asked.\n\n"
            "# Tool-use rules\n"
            "- Call tools directly, no preamble like \"let me check\".\n"
            "- Batch independent tool calls in a single assistant turn when possible.\n"
            "- Never re-read a file you already read this session unless it was just "
            "edited by you.\n"
            "- Absolute paths or workspace-relative paths only. Never invent paths.\n"
            "- `bash` requires user consent — assume the user may deny; have a plan B.\n"
            "- For destructive commands (`rm -rf`, `git reset --hard`, `DROP TABLE`, force "
            "push), state the risk and ask first.\n\n"
            "# Editing rules\n"
            "- Match the project's existing style, imports, and conventions — read a nearby "
            "file before introducing a new pattern.\n"
            "- Do NOT add comments explaining WHAT the code does; only add a short comment "
            "when the WHY is non-obvious.\n"
            "- Do NOT refactor, rename, or reformat code outside the scope of the request.\n"
            "- Do NOT add error handling for conditions that cannot occur.\n"
            "- Preserve existing indentation (tabs vs spaces) exactly.\n\n"
            "# Boundaries\n"
            "- Never print or transmit secrets (API keys, passwords, tokens). If you see "
            "one in a file, warn and continue without echoing it.\n"
            "- If the user asks for something harmful, illegal, or clearly destructive with "
            "no authorization context, refuse briefly and offer a safer alternative.\n\n"
            "# Output format\n"
            "- Be concise. No filler, no re-statement of the question.\n"
            "- Use fenced code blocks for code. Use `file:line` references when pointing to "
            "specific locations.\n"
            "- End every non-trivial turn with the short report from phase 7."
        ),
        "ko": (
            "당신은 DOBIN CODE — 터미널에서 동작하는 코딩 에이전트입니다. 사용자의 프로젝트 "
            "디렉토리 안에서 도구를 통해 실제 파일을 읽고 수정합니다.\n"
            "모든 응답은 한국어로 작성합니다.\n\n"
            "# 의사결정 루프\n"
            "매 사용자 턴마다 아래 단계를 순서대로 밟으세요. 단계를 건너뛰지 말되, 각 단계는 "
            "최소한으로 유지합니다.\n"
            "1. 이해(UNDERSTAND) — 목표를 한 문장으로 내부 정리합니다. 요청이 결과물 차이를 "
            "만들 정도로 모호하면 질문 하나만 하고 멈춥니다. 아니면 진행.\n"
            "2. 위치 파악(LOCATE) — 대상 파일/심볼을 정확히 찾습니다. "
            "`search_symbols` > `grep_search` > `glob_search` > `list_dir` 순으로 선호. "
            "`read_file`은 필요한 범위만 offset/limit으로 읽습니다.\n"
            "3. 계획(PLAN) — 최소 변경 집합을 결정합니다. 편집 3개 이상·새 모듈·리스크 있는 "
            "리팩토링이면 수정 전에 2-4개 불릿으로 계획을 먼저 제시합니다.\n"
            "4. 편집(EDIT) — 변경을 적용:\n"
            "   - 고유 문자열 치환은 `edit_file`.\n"
            "   - 줄 번호를 아는 경우 `replace_lines`.\n"
            "   - 새 파일이나 전체 재작성일 때만 `write_file`.\n"
            "   편집 직후 무엇이 바뀌었는지 한 줄로 확인합니다.\n"
            "5. 검증(VERIFY) — 변경이 동작함을 증명합니다. 프로젝트의 테스트/타입체커/린터를 "
            "`bash`로 실행. 방법을 모르면 package.json·pyproject.toml을 먼저 확인. UI/런타임 "
            "거동처럼 직접 실행 불가한 것은 '검증하지 못했다'고 명시합니다.\n"
            "6. 복구(RECOVER) — 실패 시 에러를 읽고 근본 원인을 고친 뒤 다시 검증. 편집이 "
            "잘못됐으면 `undo`로 직전 수정을 되돌립니다. 문제를 덮지 않습니다.\n"
            "7. 보고(REPORT) — 마지막에 1-3줄 요약: 건드린 파일, 검증된 것, 검증되지 않은 것. "
            "커밋(`git_status` → `git_commit`)은 요청받은 경우에만.\n\n"
            "# 도구 사용 규칙\n"
            "- 도구는 바로 호출. \"확인해볼게요\" 같은 사전 멘트 금지.\n"
            "- 독립적인 도구 호출은 한 턴에 묶어서 호출.\n"
            "- 이번 세션에서 이미 읽은 파일은 재읽지 않습니다(방금 직접 수정한 경우는 제외).\n"
            "- 절대 경로 또는 작업 공간 기준 상대 경로만 사용. 경로를 임의로 만들지 않습니다.\n"
            "- `bash`는 사용자 동의가 필요합니다 — 거부될 수 있음을 전제로 대안을 준비하세요.\n"
            "- 파괴적 명령(`rm -rf`, `git reset --hard`, `DROP TABLE`, force push)은 리스크를 "
            "밝히고 먼저 물어봅니다.\n\n"
            "# 편집 규칙\n"
            "- 프로젝트의 기존 스타일·임포트·관례를 따르세요 — 새 패턴을 도입하기 전에 주변 "
            "파일을 먼저 확인.\n"
            "- 코드가 '무엇을 하는지' 설명하는 주석은 달지 않습니다. '왜'가 비자명할 때만 짧게.\n"
            "- 요청 범위를 벗어난 리팩토링·리네임·포매팅 변경은 하지 않습니다.\n"
            "- 발생할 수 없는 조건에 대한 에러 처리는 추가하지 않습니다.\n"
            "- 기존 들여쓰기(탭 vs 공백)를 정확히 유지합니다.\n\n"
            "# 경계\n"
            "- 시크릿(API 키, 비밀번호, 토큰)을 출력하거나 전송하지 않습니다. 파일에서 보면 "
            "경고하고 값 자체는 에코하지 않습니다.\n"
            "- 해롭거나 불법적이거나 승인 근거 없는 명백히 파괴적인 요청은 짧게 거절하고 안전한 "
            "대안을 제시합니다.\n\n"
            "# 출력 형식\n"
            "- 간결하게. 군더더기·질문 재진술 금지.\n"
            "- 코드는 펜스 코드 블록. 특정 위치를 가리킬 때는 `파일:줄번호` 형식.\n"
            "- 사소하지 않은 턴은 7단계의 짧은 보고로 마무리합니다."
        ),
    },

    # ── slash command descriptions ──
    "cmd.help":     {"en": "Show commands",        "ko": "명령어 안내"},
    "cmd.model":    {"en": "Change model",         "ko": "모델 변경"},
    "cmd.clear":    {"en": "Clear conversation",   "ko": "대화 초기화"},
    "cmd.history":  {"en": "Important requests",   "ko": "중요 요청 기록"},
    "cmd.dir":      {"en": "List workspace",       "ko": "디렉토리 조회"},
    "cmd.language": {"en": "Change language",      "ko": "언어 변경"},
    "cmd.compact":  {"en": "Compact conversation", "ko": "대화 요약/압축"},
    "cmd.consent":  {"en": "Toggle shell consent", "ko": "터미널 동의 토글"},
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

    # ── auto-compact ──
    "compact.running":    {"en": "Auto-compacting conversation…",
                           "ko": "대화가 길어져 자동 요약 중…"},
    "compact.manual":     {"en": "Compacting conversation…",
                           "ko": "대화를 요약 중…"},
    "compact.done":       {"en": "Compacted {n} older messages.",
                           "ko": "이전 메시지 {n}개를 요약으로 압축했습니다."},
    "compact.error":      {"en": "Compact failed: {err}",
                           "ko": "요약 실패: {err}"},
    "compact.system":     {
        "en": (
            "Summarize the following agent conversation (tool calls and results) "
            "into a concise paragraph. Keep file paths, key decisions, and unresolved "
            "issues. Do not invent details. Output plain text only."
        ),
        "ko": (
            "다음 에이전트 대화(도구 호출과 결과)를 간결한 한 문단으로 요약하세요. "
            "파일 경로, 주요 결정, 미해결 이슈는 유지하세요. 임의로 추가하지 마세요. "
            "일반 텍스트만 출력합니다."
        ),
    },
    "compact.prefix":     {"en": "[Summary of earlier conversation]",
                           "ko": "[이전 대화 요약]"},

    # ── bash consent ──
    "consent.title":      {"en": "  Run this command?",        "ko": "  이 명령을 실행할까요?"},
    "consent.hint":       {"en": "  y=allow · n=deny · Esc=deny",
                           "ko": "  y=허용 · n=거부 · Esc=거부"},
    "consent.denied":     {"en": "(user denied execution)",   "ko": "(사용자가 실행을 거부했습니다)"},
    "consent.on":         {"en": "Shell consent: ON",         "ko": "터미널 실행 동의: ON"},
    "consent.off":        {"en": "Shell consent: OFF",        "ko": "터미널 실행 동의: OFF"},
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

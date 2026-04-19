from rich.console import Console, Group
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich.table import Table
from rich.live import Live
from rich.spinner import Spinner
from rich.align import Align
from rich.columns import Columns
from rich import box
from rich.rule import Rule
import json as _json
import os
import shutil
from datetime import datetime

# ─────────────────────────────────────────────────────────────────────────
#  DOBIN CODE — 간지나는 CLI 테마
# ─────────────────────────────────────────────────────────────────────────
#  Palette:
#    primary  #ff8c00  (오렌지, Claude Code 시그니처와 비슷)
#    accent   #ffb347  (밝은 오렌지)
#    user     #60a5fa  (블루, 사용자 발화)
#    agent    #ff8c00  (오렌지, 도빈 발화)
#    tool     #a78bfa  (바이올렛, 도구 호출)
#    ok       #22c55e
#    err      #ef4444
#    muted    #6b7280

THEME = Theme({
    "dobin":      "bold #ff8c00",
    "dobin_dim":  "#92400e",
    "accent":     "#ffb347",
    "user":       "bold #60a5fa",
    "user_dim":   "#3b82f6",
    "agent":      "bold #ff8c00",
    "tool":       "bold #a78bfa",
    "tool_dim":   "#7c3aed",
    "ok":         "bold #22c55e",
    "err":        "bold #ef4444",
    "warn":       "bold #f59e0b",
    "muted":      "#6b7280",
    "dim2":       "#9ca3af",
    "border":     "#374151",
    "chip":       "on #1f2937",
})

console = Console(theme=THEME, force_terminal=True)


# ─────────────────────────────────────────────────────────────────────────
#  ASCII ART 배너
# ─────────────────────────────────────────────────────────────────────────

_DOBIN_LINES = [
    "██████╗   ██████╗  ██████╗  ██╗███╗   ██╗",
    "██╔══██╗ ██╔═══██╗ ██╔══██╗ ██║████╗  ██║",
    "██║  ██║ ██║   ██║ ██████╔╝ ██║██╔██╗ ██║",
    "██║  ██║ ██║   ██║ ██╔══██╗ ██║██║╚██╗██║",
    "██████╔╝ ╚██████╔╝ ██████╔╝ ██║██║ ╚████║",
    "╚═════╝   ╚═════╝  ╚═════╝  ╚═╝╚═╝  ╚═══╝",
]

_CODE_LINES = [
    " ██████╗ ██████╗ ██████╗ ███████╗",
    "██╔════╝██╔═══██╗██╔══██╗██╔════╝",
    "██║     ██║   ██║██║  ██║█████╗  ",
    "██║     ██║   ██║██║  ██║██╔══╝  ",
    "╚██████╗╚██████╔╝██████╔╝███████╗",
    " ╚═════╝ ╚═════╝ ╚═════╝ ╚══════╝",
]

_GRADIENT = ["#ff6a00", "#ff7a00", "#ff8c00", "#ffa033", "#ffb347", "#ffc979"]


def print_banner():
    """시작 배너 — DOBIN + CODE 두 줄 ASCII art"""
    console.print()
    for i, line in enumerate(_DOBIN_LINES):
        color = _GRADIENT[i % len(_GRADIENT)]
        console.print(Text(f"   {line}", style=f"bold {color}"))
    console.print()
    for i, line in enumerate(_CODE_LINES):
        color = _GRADIENT[i % len(_GRADIENT)]
        console.print(Text(f"   {line}", style=f"bold {color}"))
    console.print()


def print_session_info(model, workdir):
    """세션 정보 박스"""
    home = os.path.expanduser("~")
    pretty_dir = workdir.replace(home, "~") if workdir.startswith(home) else workdir
    if len(pretty_dir) > 50:
        pretty_dir = "…" + pretty_dir[-49:]

    info = Table.grid(padding=(0, 2))
    info.add_column(style="muted", justify="right")
    info.add_column()
    info.add_row("모델", Text(model, style="dobin"))
    info.add_row("디렉토리", Text(pretty_dir, style="dim2"))
    info.add_row("팁", Text("'/' 로 명령어 · '/model' 로 모델 변경 · '/quit' 로 종료", style="muted"))

    panel = Panel(
        info,
        title="[dobin]세션[/dobin]",
        title_align="left",
        border_style="#ff8c00",
        box=box.ROUNDED,
        padding=(1, 2),
        width=min(shutil.get_terminal_size((80, 24)).columns, 78),
    )
    console.print(panel)
    console.print()


# ─────────────────────────────────────────────────────────────────────────
#  채팅 버블
# ─────────────────────────────────────────────────────────────────────────

def _timestamp():
    return datetime.now().strftime("%H:%M")


def _term_width():
    return min(shutil.get_terminal_size((80, 24)).columns, 90)


def print_user_bubble(text):
    """사용자 메시지 — 전체 너비 박스 + 우측 정렬 텍스트"""
    width = _term_width()
    box_w = width - 4  # 좌우 여백
    inner_w = box_w - 4  # 안쪽 여백

    console.print()
    # 헤더: 우측 정렬
    header_row = Text()
    header_row.append("  ╭─ ", style="#60a5fa")
    label = "You · " + _timestamp()
    header_row.append("─" * (box_w - 6 - len(label) - 2), style="#60a5fa")
    header_row.append(" " + label + " ", style="user")
    header_row.append("╮", style="#60a5fa")
    console.print(header_row)

    # 본문: 줄바꿈 후 각 줄 우측 정렬
    for raw_line in text.split("\n"):
        # 긴 줄은 wrap
        while True:
            chunk = raw_line[:inner_w]
            raw_line = raw_line[inner_w:]
            row = Text()
            row.append("  │", style="#60a5fa")
            pad = inner_w - _visible_len(chunk)
            row.append(" " * (pad + 1), style="")
            row.append(chunk, style="#e5e7eb")
            row.append(" │", style="#60a5fa")
            console.print(row)
            if not raw_line:
                break

    # 하단
    console.print(Text("  ╰" + "─" * (box_w - 2) + "╯", style="#60a5fa"))


def _visible_len(s):
    """한글/이모지 등 wide char를 2로 세는 대략적인 길이"""
    import unicodedata
    n = 0
    for ch in s:
        if unicodedata.east_asian_width(ch) in ("W", "F"):
            n += 2
        else:
            n += 1
    return n


def print_response(text):
    """도빈 응답 — 좌측 오렌지 바 + 깔끔한 마크다운"""
    console.print()
    header = Text()
    header.append("▎", style="bold #ff8c00")
    header.append(" DOBIN CODE ", style="agent")
    header.append(_timestamp(), style="muted")
    console.print(header)

    _print_with_left_bar(text, bar_style="#ff8c00", as_markdown=True)


def _print_with_left_bar(text, bar_style="#ff8c00", as_markdown=False):
    """본문을 좌측 오렌지 바와 함께 출력. 마크다운 ANSI를 유지한다."""
    width = _term_width() - 4
    import io as _io
    from rich.console import Console as _RConsole

    buf = _io.StringIO()
    tmp = _RConsole(
        file=buf,
        theme=THEME,
        force_terminal=True,
        color_system="truecolor",
        width=width,
        legacy_windows=False,
    )
    if as_markdown:
        try:
            tmp.print(Markdown(text, code_theme="monokai"))
        except Exception:
            tmp.print(text)
    else:
        tmp.print(text)

    output = buf.getvalue().rstrip("\n")
    # 24-bit 컬러 ANSI로 바를 직접 작성 (색 일관성 유지)
    r, g, b = _hex_to_rgb(bar_style)
    bar_ansi = f"\x1b[1;38;2;{r};{g};{b}m▎\x1b[0m "
    for line in output.split("\n"):
        console.file.write(bar_ansi + line + "\n")
    console.file.flush()


def _hex_to_rgb(hex_color):
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


# ─────────────────────────────────────────────────────────────────────────
#  도구 호출
# ─────────────────────────────────────────────────────────────────────────

TOOL_LABELS = {
    "bash":              ("터미널 실행", "👾"),
    "read_file":         ("파일 읽기",   "📄"),
    "write_file":        ("파일 쓰기",   "📝"),
    "edit_file":         ("파일 편집",   "✏️"),
    "replace_lines":     ("줄 교체",     "✂️"),
    "undo":              ("되돌리기",    "↩️"),
    "list_dir":          ("디렉토리 조회", "📁"),
    "glob_search":       ("파일 검색",   "🔎"),
    "grep_search":       ("내용 검색",   "🔍"),
    "search_symbols":    ("심볼 검색",   "🧭"),
    "create_directory":  ("폴더 생성",   "📂"),
    "delete_path":       ("경로 삭제",   "🗑️"),
    "git_status":        ("Git 상태",    "🌿"),
    "git_commit":        ("Git 커밋",    "📦"),
}


def _format_tool_args(tool_name, args):
    if isinstance(args, str):
        try:
            args = _json.loads(args)
        except Exception:
            return args
    if not isinstance(args, dict):
        return str(args)

    if tool_name == "bash":
        cmd = args.get("command", "")
        return cmd if len(cmd) < 90 else cmd[:87] + "…"
    if tool_name == "read_file":
        path = args.get("path", "")
        off, lim = args.get("offset"), args.get("limit")
        extras = []
        if off: extras.append(f"offset={off}")
        if lim: extras.append(f"limit={lim}")
        return path + (f"  ({', '.join(extras)})" if extras else "")
    if tool_name in ("write_file", "create_directory", "delete_path"):
        return args.get("path", "")
    if tool_name == "edit_file":
        path = args.get("path", "")
        old = args.get("old_string", "").replace("\n", "⏎")
        preview = old[:40] + ("…" if len(old) > 40 else "")
        return f"{path}  ·  '{preview}'"
    if tool_name == "list_dir":
        return args.get("path", ".")
    if tool_name == "glob_search":
        return args.get("pattern", "")
    if tool_name == "grep_search":
        pattern = args.get("pattern", "")
        inc = args.get("include", "")
        return pattern + (f"  ({inc})" if inc else "")
    if tool_name == "search_symbols":
        name = args.get("name", "")
        kind = args.get("kind", "")
        return name + (f"  ({kind})" if kind and kind != "any" else "")
    if tool_name == "replace_lines":
        path = args.get("path", "")
        s = args.get("start_line", "?")
        e = args.get("end_line", "?")
        return f"{path}  L{s}-{e}"
    if tool_name == "undo":
        return ""
    if tool_name == "git_status":
        return args.get("path", "") or ""
    if tool_name == "git_commit":
        msg = args.get("message", "")
        return msg if len(msg) < 60 else msg[:57] + "…"

    for _, v in args.items():
        s = str(v)
        return s if len(s) < 80 else s[:77] + "…"
    return ""


def print_tool_call(tool_name, args):
    """도구 호출 — 한 줄 타이틀 '[이모지] 라벨  인자'"""
    label, icon = TOOL_LABELS.get(tool_name, (tool_name, "●"))
    summary = _format_tool_args(tool_name, args)

    console.print()
    line = Text()
    line.append(f"  {icon}  ", style="")
    line.append(label, style="bold #e5e7eb")
    if summary:
        line.append("  ", style="")
        line.append(str(summary), style="muted")
    console.print(line)


def print_tool_result(result, short=True):
    """도구 결과 — 회색 배경 카드로 3줄 요약 (short=False면 전체)"""
    text = str(result).rstrip()
    if not text:
        text = "(출력 없음)"
    lines = text.split("\n")

    max_lines = 3 if short else 60
    preview = lines[:max_lines]
    remaining = len(lines) - len(preview)

    width = _term_width()
    card_w = width - 8  # 좌측 6칸 여백 + 우측 약간
    card_bg = "on #1f2937"

    for line in preview:
        if len(line) > card_w - 4:
            line = line[:card_w - 5] + "…"
        row = Text()
        row.append("     ", style="")
        # 회색 배경으로 카드 렌더
        row.append(" " + line + " " * max(0, card_w - _visible_len(line) - 1), style=f"#d1d5db {card_bg}")
        console.print(row)

    if remaining > 0:
        more = Text()
        more.append("     ", style="")
        more.append(f" ⋯ {remaining}줄 더 있음" + " " * max(0, card_w - _visible_len(f" ⋯ {remaining}줄 더 있음") - 1),
                    style=f"italic #9ca3af {card_bg}")
        console.print(more)


# ─────────────────────────────────────────────────────────────────────────
#  상태 메시지
# ─────────────────────────────────────────────────────────────────────────

def print_error(text):
    line = Text()
    line.append("  ✗ ", style="err")
    line.append(str(text), style="#fca5a5")
    console.print()
    console.print(line)


def print_success(text):
    line = Text()
    line.append("  ✓ ", style="ok")
    line.append(str(text), style="#d1d5db")
    console.print(line)


def print_separator():
    width = min(shutil.get_terminal_size((80, 24)).columns, 78)
    console.print()
    console.print(Text("   " + "─" * (width - 6), style="muted"))


def print_memory_saved(path, task_summary=""):
    home = os.path.expanduser("~")
    pretty = path.replace(home, "~") if path.startswith(home) else path

    console.print()
    line = Text()
    line.append("  ◷ ", style="muted")
    line.append("저장: ", style="muted")
    line.append(pretty, style="dim2")
    console.print(line)

    if task_summary:
        for l in task_summary.split("\n"):
            console.print(Text(f"    {l}", style="muted"))


# ─────────────────────────────────────────────────────────────────────────
#  명령어 / 모델 / 도움말
# ─────────────────────────────────────────────────────────────────────────

def print_model_selection(models, default_idx=0):
    """모델 선택 — 컬러 카드 스타일"""
    console.print()
    console.print(Text("  모델 선택", style="dobin"))
    console.print(Text("  번호 입력 또는 Enter(기본값)", style="muted"))
    console.print()

    for i, m in enumerate(models):
        is_default = (i == default_idx)
        marker = "●" if is_default else "○"
        marker_style = "bold #ff8c00" if is_default else "muted"
        line = Text()
        line.append(f"  {marker} ", style=marker_style)
        line.append(f"{i + 1}. ", style="muted")
        line.append(m["name"], style="bold #e5e7eb" if is_default else "#d1d5db")
        line.append("  ", style="")
        line.append(m["desc"], style="muted")
        if is_default:
            line.append("  ", style="")
            line.append(" 기본 ", style="bold black on #22c55e")
        console.print(line)
    console.print()


def print_current_model(models, current):
    """현재 모델 + 변경 방법 안내"""
    console.print()
    console.print(Text("  사용 가능한 모델", style="dobin"))
    console.print()
    for i, m in enumerate(models):
        active = (m["name"] == current)
        marker = "●" if active else "○"
        mstyle = "bold #ff8c00" if active else "muted"
        line = Text()
        line.append(f"  {marker} ", style=mstyle)
        line.append(m["name"], style="bold #e5e7eb" if active else "#d1d5db")
        line.append("  ", style="")
        line.append(m["desc"], style="muted")
        if active:
            line.append("  ", style="")
            line.append(" 현재 ", style="bold black on #ff8c00")
        console.print(line)
    console.print()
    hint = Text()
    hint.append("  변경: ", style="muted")
    hint.append("/model <번호 또는 모델명>", style="bold #a78bfa")
    console.print(hint)
    console.print()


def print_welcome_help():
    """시작 시 짧은 명령어 안내"""
    cmds = [
        ("/help",    "명령어 안내"),
        ("/model",   "모델 변경"),
        ("/clear",   "대화 초기화"),
        ("/history", "중요 요청 기록"),
        ("/dir",     "디렉토리 조회"),
        ("/quit",    "종료"),
    ]
    console.print(Text("  단축 명령", style="dobin"))
    for cmd, desc in cmds:
        line = Text()
        line.append(f"   {cmd:<10}", style="bold #a78bfa")
        line.append(desc, style="muted")
        console.print(line)
    console.print()


def print_help_table():
    table = Table(
        show_header=True,
        header_style="bold #ff8c00",
        border_style="#374151",
        box=box.SIMPLE_HEAVY,
        padding=(0, 2),
        title="[dobin]DOBIN CODE 도움말[/dobin]",
        title_style="dobin",
    )
    table.add_column("명령어", style="bold #a78bfa", no_wrap=True)
    table.add_column("설명", style="#d1d5db")

    rows = [
        ("/help, /도움",       "이 도움말을 표시합니다"),
        ("/model, /모델",      "모델 목록 확인 · /model <번호>로 변경"),
        ("/clear, /초기화",    "대화 기록을 초기화합니다"),
        ("/history, /기록",    "중요 요청 기록을 봅니다"),
        ("/dir, /디렉토리",    "현재 디렉토리를 조회합니다"),
        ("/quit, /종료",       "DOBIN CODE를 종료합니다"),
    ]
    for cmd, desc in rows:
        table.add_row(cmd, desc)
    console.print()
    console.print(table)
    console.print()


# ─────────────────────────────────────────────────────────────────────────
#  프롬프트 / 스피너
# ─────────────────────────────────────────────────────────────────────────

def render_prompt_marker():
    """입력 프롬프트 앞 마커 (레거시)"""
    marker = Text()
    marker.append("  ❯ ", style="bold #ff8c00")
    return marker


# ─────────────────────────────────────────────────────────────────────────
#  박스 입력창 + / 자동완성 팝업
# ─────────────────────────────────────────────────────────────────────────

SLASH_COMMANDS = [
    ("/help",    "명령어 안내"),
    ("/model",   "모델 변경"),
    ("/clear",   "대화 초기화"),
    ("/history", "중요 요청 기록"),
    ("/dir",     "디렉토리 조회"),
    ("/quit",    "종료"),
]


def prompt_input():
    """입력창 — 위/아래 구분선이 입력 영역에 붙어있는 Application 기반 위젯."""
    from prompt_toolkit.application import Application
    from prompt_toolkit.buffer import Buffer
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.layout import Layout
    from prompt_toolkit.layout.containers import HSplit, Window, VSplit, FloatContainer, Float
    from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
    from prompt_toolkit.layout.dimension import Dimension as D
    from prompt_toolkit.layout.menus import CompletionsMenu
    from prompt_toolkit.layout.processors import BeforeInput
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.styles import Style as PTStyle
    from prompt_toolkit.document import Document

    class SlashCompleter(Completer):
        def get_completions(self, document, complete_event):
            text = document.text_before_cursor
            if not text.startswith("/"):
                return
            for cmd, desc in SLASH_COMMANDS:
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display=cmd,
                        display_meta=desc,
                    )

    kb = KeyBindings()

    @kb.add("enter")
    def _(event):
        # 자동완성이 떠 있고 항목이 선택돼 있으면 선택 확정, 아니면 제출
        buf = event.app.current_buffer
        cs = buf.complete_state
        if cs is not None and cs.current_completion is not None:
            buf.apply_completion(cs.current_completion)
            buf.complete_state = None
            return
        event.app.exit(result=buf.text)

    @kb.add("c-c")
    @kb.add("c-d")
    def _(event):
        event.app.exit(exception=KeyboardInterrupt)

    @kb.add("/")
    def _(event):
        buf = event.current_buffer
        buf.insert_text("/")
        if buf.text == "/":
            buf.start_completion(select_first=False)

    # 입력 버퍼
    buffer = Buffer(
        completer=SlashCompleter(),
        complete_while_typing=True,
        multiline=False,
    )

    width = _term_width()
    rule_text = "  " + "─" * (width - 4)

    # 위/아래 구분선 컨트롤
    top_rule = Window(
        content=FormattedTextControl(lambda: [("class:rule", rule_text)]),
        height=1,
    )
    bottom_rule = Window(
        content=FormattedTextControl(lambda: [("class:rule", rule_text)]),
        height=1,
    )

    # 입력 라인 — '❯ '를 앞에 붙이고 버퍼를 인라인으로
    input_window = Window(
        content=BufferControl(
            buffer=buffer,
            input_processors=[BeforeInput("  ❯ ", style="class:prompt")],
        ),
        height=1,
        wrap_lines=False,
    )

    # 자동완성 메뉴는 입력 라인 위에 float으로 띄움
    body = HSplit([
        top_rule,
        input_window,
        bottom_rule,
    ])

    root = FloatContainer(
        content=body,
        floats=[
            Float(
                xcursor=True,
                ycursor=True,
                content=CompletionsMenu(max_height=6, scroll_offset=1),
            ),
        ],
    )

    style = PTStyle.from_dict({
        "prompt":                             "#ff8c00 bold",
        "rule":                               "#6b7280",
        "":                                   "#e5e7eb",
        "completion-menu":                    "bg:#1f1b2e #d1d5db",
        "completion-menu.completion":         "bg:#1f1b2e #d1d5db",
        "completion-menu.completion.current": "bg:#ff8c00 #111827 bold",
        "completion-menu.meta":               "bg:#1f1b2e #9ca3af",
        "completion-menu.meta.completion":    "bg:#1f1b2e #9ca3af",
        "completion-menu.meta.completion.current": "bg:#ff8c00 #1f2937",
    })

    console.print()  # 위 여백

    app = Application(
        layout=Layout(root, focused_element=input_window),
        key_bindings=kb,
        style=style,
        full_screen=False,
        mouse_support=False,
    )

    text = app.run()
    # app 출력 이후 개행이 어색할 수 있으므로 한 줄 비움
    return (text or "").strip()


class ThinkingAnimation:
    def __init__(self, text="DOBIN CODE 생각 중"):
        self.text = text
        self.live = None

    def __enter__(self):
        spinner = Spinner(
            "dots",
            text=Text(f"  {self.text}…", style="#ff8c00"),
            style="#ff8c00",
        )
        self.live = Live(spinner, console=console, refresh_per_second=12, transient=True)
        self.live.start()
        return self

    def __exit__(self, *_):
        if self.live:
            self.live.stop()
        return False

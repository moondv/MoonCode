"""
DOBIN CODE TUI — 풀스크린 채팅 UI.

레이아웃:
    ┌────────────────────────────────────────┐
    │  (배너 + 대화 로그)                     │
    │  ...                                   │
    │                                        │
    ├────────────────────────────────────────┤  ← 구분선
    │  ❯ 입력창 (하단 고정)                  │
    ├────────────────────────────────────────┤  ← 구분선
    │  상태바 (모델, 힌트)                    │
    └────────────────────────────────────────┘

스크롤 없음 — 항상 최신 메시지 표시
"""
import asyncio
import io
import json as _json
import shutil
import threading
from datetime import datetime

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    Float, FloatContainer, HSplit, VSplit, Window, ConditionalContainer,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.styles import Style as PTStyle
from prompt_toolkit.formatted_text import ANSI, FormattedText
from prompt_toolkit.filters import Condition

from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text as RichText
from rich.theme import Theme

# ─────────────────────────────────────────────────────────────
#  테마 / 상수
# ─────────────────────────────────────────────────────────────

from core.i18n import t

# 아이콘은 언어와 무관. 설명은 i18n에서 가져와서 동적으로 구성한다.
_TOOL_ICONS = {
    "bash":              "👾",
    "read_file":         "📄",
    "write_file":        "📝",
    "edit_file":         "✏️",
    "replace_lines":     "✂️",
    "undo":              "↩️",
    "list_dir":          "📁",
    "glob_search":       "🔎",
    "grep_search":       "🔍",
    "search_symbols":    "🧭",
    "create_directory":  "📂",
    "delete_path":       "🗑️",
    "git_status":        "🌿",
    "git_commit":        "📦",
}

_SLASH_KEYS = [
    ("/help",     "cmd.help"),
    ("/model",    "cmd.model"),
    ("/clear",    "cmd.clear"),
    ("/history",  "cmd.history"),
    ("/dir",      "cmd.dir"),
    ("/language", "cmd.language"),
    ("/compact",  "cmd.compact"),
    ("/consent",  "cmd.consent"),
    ("/quit",     "cmd.quit"),
]

def slash_commands():
    """(cmd, description) 목록을 현재 언어로 반환."""
    return [(cmd, t(key)) for cmd, key in _SLASH_KEYS]

def tool_label(tool_name):
    """(label, icon) 튜플을 현재 언어로 반환."""
    icon = _TOOL_ICONS.get(tool_name, "●")
    label = t(f"tool.{tool_name}")
    # 번역 없으면 도구명 원본을 그대로
    if label == f"tool.{tool_name}":
        label = tool_name
    return label, icon

_RICH_THEME = Theme({
    "dobin":     "bold #ff8c00",
    "muted":     "#6b7280",
    "dim2":      "#9ca3af",
    "user":      "bold #60a5fa",
    "agent":     "bold #ff8c00",
    "ok":        "bold #22c55e",
    "err":       "bold #ef4444",
})

_GRADIENT = ["#ff6a00", "#ff7a00", "#ff8c00", "#ffa033", "#ffb347", "#ffc979"]

_DOBIN = [
    "████████╗     ██████╗     ██████╗    ██╗████╗   ██╗",
    "██╔═════██╗  ██╔════██╗  ██╔════██╗  ██║██╔██╗  ██║",
    "██║    ██║   ██║    ██║  ██████╔═╝   ██║██║╚██╗ ██║",
    "██║    ██║   ██║    ██║  ██╔═══██╗   ██║██║ ╚██╗██║",
    "██║    ██║   ██║    ██║  ██║   ██║   ██║██║  ╚████║",
    "████████╔═╝  ╚██████╔═╝  ██████╔═╝   ██║██║   ╚███║",
    "╚═══════╝     ╚═════╝    ╚═════╝     ╚═╝╚═╝    ╚══╝",
]

_CODE = [
    " ██████╗    ██████╗    ██████╗    ███████╗",
    "██╔════██╗ ██╔════██╗ ██╔════██╗  ██╔════╝",
    "██║        ██║    ██║ ██║    ██║  ██████╗  ",
    "██║        ██║    ██║ ██║    ██║  ██╔═══╝  ",
    "██║        ██║    ██║ ██║    ██║  ██║      ",
    "╚██████╔═╝ ╚██████╔═╝ ██████╔═╝   ███████╗",
    " ╚═════╝    ╚═════╝   ╚═════╝     ╚══════╝",
]


def _term_width():
    return max(40, shutil.get_terminal_size((80, 24)).columns)


def _timestamp():
    return datetime.now().strftime("%H:%M")


# ─────────────────────────────────────────────────────────────
#  Rich → ANSI 변환 (로그 버퍼에 넣을 문자열)
# ─────────────────────────────────────────────────────────────

def _rich_to_ansi(render_fn, width=None, no_wrap=False):
    """render_fn(console)을 호출하고 ANSI 문자열로 반환.

    no_wrap=True면 배너 등 폭에 민감한 아트를 패딩/랩핑 없이 그대로 출력.
    """
    buf = io.StringIO()
    c = Console(
        file=buf,
        theme=_RICH_THEME,
        force_terminal=True,
        color_system="truecolor",
        width=10_000 if no_wrap else (width or _term_width()),
        legacy_windows=False,
        soft_wrap=no_wrap,
    )
    render_fn(c)
    return buf.getvalue()


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
    if tool_name == "replace_lines":
        return f"{args.get('path', '')}  L{args.get('start_line', '?')}-{args.get('end_line', '?')}"
    if tool_name in ("list_dir",):
        return args.get("path", ".")
    if tool_name == "glob_search":
        return args.get("pattern", "")
    if tool_name == "grep_search":
        return args.get("pattern", "") + (f"  ({args.get('include')})" if args.get("include") else "")
    if tool_name == "search_symbols":
        name = args.get("name", "")
        kind = args.get("kind", "")
        return name + (f"  ({kind})" if kind and kind != "any" else "")
    if tool_name == "git_commit":
        msg = args.get("message", "")
        return msg if len(msg) < 60 else msg[:57] + "…"
    if tool_name == "undo":
        return ""
    for _, v in args.items():
        s = str(v)
        return s if len(s) < 80 else s[:77] + "…"
    return ""


# ─────────────────────────────────────────────────────────────
#  DobinTUI — 풀스크린 애플리케이션
# ─────────────────────────────────────────────────────────────

class DobinTUI:
    def __init__(self, agent, on_user_input):
        """
        agent: DobinAgent 인스턴스 (프로퍼티 읽기용 — model 등)
        on_user_input: async def (tui, text) -> None
            사용자 입력이 들어왔을 때 호출될 콜백. 에이전트 로직을 비동기로 실행.
        """
        self.agent = agent
        self.on_user_input = on_user_input

        # 로그 섹션 누적 (각 섹션은 여러 줄 ANSI 문자열)
        self._log_lines = []

        # 모델 선택 팝업 상태
        self._model_popup_open = False
        self._model_popup_items = []
        self._model_popup_index = 0
        self._model_popup_on_select = None

        # bash 실행 동의 팝업 상태
        self._consent_popup_open = False
        self._consent_popup_command = ""
        self._consent_popup_on_choice = None

        # 입력 버퍼
        self.input_buffer = Buffer(
            completer=self._completer(),
            complete_while_typing=True,
            multiline=False,
            accept_handler=self._on_accept,
        )

        # 상태
        self.is_busy = False

        # 스크롤 상태 (수동 뷰포트 방식)
        # _scroll_offset = 바닥에서 몇 줄 위로 올라갔는지. 0이면 항상 최신.
        self._scroll_offset = 0
        # 마지막 렌더 시점의 총 줄 수·창 높이 (휠 이벤트에서 clamp용)
        self._last_total_lines = 0
        self._last_window_height = 0

        # Application 참조
        self.app = None
        self._layout = self._build_layout()
        self._style = self._build_style()
        self._kb = self._build_keybindings()

        # 시작 시 배너를 로그에 추가
        self._append_banner()

    # ─── layout ───────────────────────────────────────────

    def _build_layout(self):
        # 대화 로그 윈도우 — 수동 뷰포트 방식으로 스크롤 구현
        self.log_content_control = FormattedTextControl(
            text=lambda: self._get_log_fragments(),
            focusable=False,
            show_cursor=False,
        )

        # Window 서브클래스 — prompt_toolkit이 휠 이벤트를 받으면
        # 내부적으로 _scroll_up / _scroll_down을 호출한다. 이를 가로채서
        # 우리의 수동 뷰포트(_scroll_offset)를 조작한다.
        tui = self
        class _LogWindow(Window):
            def _scroll_up(self):
                tui._scroll_by(3)
            def _scroll_down(self):
                tui._scroll_by(-3)

        self.log_window = _LogWindow(
            content=self.log_content_control,
            wrap_lines=False,
            always_hide_cursor=True,
            height=D(weight=1),
        )

        # 입력창
        input_control = BufferControl(
            buffer=self.input_buffer,
            input_processors=[BeforeInput("  ❯ ", style="class:prompt")],
        )
        self.input_window = Window(
            content=input_control,
            height=1,
            wrap_lines=False,
        )

        # 구분선
        def _rule_line():
            w = _term_width()
            return [("class:rule", "  " + "─" * (w - 4))]

        top_rule = Window(
            content=FormattedTextControl(_rule_line),
            height=1,
        )
        bottom_rule = Window(
            content=FormattedTextControl(_rule_line),
            height=1,
        )

        # 상태바
        def _status_line():
            busy = t("status.busy") if self.is_busy else ""
            left = self._token_usage_label() + busy
            right = f"{self.agent.model}  "
            w = _term_width()
            pad = max(1, w - len(left) - len(right))
            return [
                ("class:status", left),
                ("class:status", " " * pad),
                ("class:status.right", right),
            ]

        self.status_window = Window(
            content=FormattedTextControl(_status_line),
            height=1,
            style="class:status",
        )

        body = HSplit([
            self.log_window,
            top_rule,
            self.input_window,
            bottom_rule,
            self.status_window,
        ])

        # 모델 선택 팝업
        popup_control = FormattedTextControl(
            text=self._get_model_popup_fragments,
            focusable=False,
        )
        self.popup_window = Window(
            content=popup_control,
            width=D(min=50, preferred=80, max=110),
            height=D(min=6, preferred=14, max=20),
            style="class:popup",
            always_hide_cursor=True,
        )
        popup_float = Float(
            content=ConditionalContainer(
                content=self.popup_window,
                filter=Condition(lambda: self._model_popup_open),
            ),
        )

        # bash 실행 동의 팝업
        consent_control = FormattedTextControl(
            text=self._get_consent_popup_fragments,
            focusable=False,
        )
        self.consent_window = Window(
            content=consent_control,
            width=D(min=50, preferred=80, max=110),
            height=D(min=6, preferred=10, max=18),
            style="class:popup",
            always_hide_cursor=True,
        )
        consent_float = Float(
            content=ConditionalContainer(
                content=self.consent_window,
                filter=Condition(lambda: self._consent_popup_open),
            ),
        )

        return Layout(
            FloatContainer(
                content=body,
                floats=[
                    Float(
                        xcursor=True,
                        ycursor=True,
                        content=CompletionsMenu(max_height=6, scroll_offset=1),
                    ),
                    popup_float,
                    consent_float,
                ],
            ),
            focused_element=self.input_window,
        )

    def _build_style(self):
        return PTStyle.from_dict({
            "prompt":                               "#ff8c00 bold",
            "rule":                                 "#6b7280",
            "status":                               "bg:#111827 #9ca3af",
            "status.right":                         "bg:#111827 #d1d5db",
            "":                                     "#e5e7eb",
            "completion-menu":                      "bg:#1f1b2e #d1d5db",
            "completion-menu.completion":           "bg:#1f1b2e #d1d5db",
            "completion-menu.completion.current":   "bg:#ff8c00 #111827 bold",
            "completion-menu.meta":                 "bg:#1f1b2e #9ca3af",
            "completion-menu.meta.completion":      "bg:#1f1b2e #9ca3af",
            "completion-menu.meta.completion.current": "bg:#ff8c00 #1f2937",
            "popup":                                "bg:#1f1b2e #d1d5db",
            "popup.title":                          "bg:#1f1b2e #ff8c00 bold",
            "popup.item":                           "bg:#1f1b2e #d1d5db",
            "popup.item.current":                   "bg:#ff8c00 #111827 bold",
            "popup.desc":                           "bg:#1f1b2e #9ca3af",
            "popup.hint":                           "bg:#1f1b2e #6b7280",
        })

    def _build_keybindings(self):
        kb = KeyBindings()

        popup_open = Condition(lambda: self._model_popup_open)
        popup_closed = Condition(
            lambda: not self._model_popup_open and not self._consent_popup_open
        )
        consent_open = Condition(lambda: self._consent_popup_open)

        @kb.add("c-c")
        @kb.add("c-d")
        def _(event):
            event.app.exit()

        @kb.add("/", filter=popup_closed)
        def _(event):
            buf = event.current_buffer
            if buf is not self.input_buffer:
                return
            buf.insert_text("/")
            if buf.text == "/":
                buf.start_completion(select_first=False)

        @kb.add("enter", filter=popup_closed)
        def _(event):
            buf = event.current_buffer
            if buf is not self.input_buffer:
                return
            cs = buf.complete_state
            if cs is not None and cs.current_completion is not None:
                buf.apply_completion(cs.current_completion)
                buf.complete_state = None
                return
            if buf.text.strip():
                buf.validate_and_handle()

        # 모델 팝업 조작
        @kb.add("up", filter=popup_open)
        def _(event):
            if self._model_popup_items:
                self._model_popup_index = (self._model_popup_index - 1) % len(self._model_popup_items)

        @kb.add("down", filter=popup_open)
        def _(event):
            if self._model_popup_items:
                self._model_popup_index = (self._model_popup_index + 1) % len(self._model_popup_items)

        @kb.add("enter", filter=popup_open)
        def _(event):
            if not self._model_popup_items:
                self._model_popup_open = False
                return
            item = self._model_popup_items[self._model_popup_index]
            cb = self._model_popup_on_select
            self._model_popup_open = False
            self._model_popup_on_select = None
            if cb is not None:
                try:
                    cb(item["name"])
                except Exception as e:
                    self.log_error(t("model.error", err=e))

        @kb.add("escape", filter=popup_open)
        @kb.add("c-g", filter=popup_open)
        def _(event):
            self._model_popup_open = False
            self._model_popup_on_select = None

        # 동의 팝업 조작
        @kb.add("y", filter=consent_open)
        @kb.add("Y", filter=consent_open)
        def _(event):
            self._resolve_consent(True)

        @kb.add("n", filter=consent_open)
        @kb.add("N", filter=consent_open)
        @kb.add("escape", filter=consent_open)
        @kb.add("c-g", filter=consent_open)
        def _(event):
            self._resolve_consent(False)

        @kb.add("enter", filter=consent_open)
        def _(event):
            # 기본값 = 허용 (y)
            self._resolve_consent(True)

        # ── 로그 스크롤 ──
        # 1) 마우스/트랙패드 휠 (mouse_support=True일 때 prompt_toolkit이 방출)
        # 2) 키보드 대안: fn+↑/↓ = PageUp/PageDown (맥북),
        #    Ctrl-B/F(한 페이지), Ctrl-U/Y(반 페이지), Home/End

        @kb.add("<scroll-up>")
        def _(event):
            self._scroll_by(3)

        @kb.add("<scroll-down>")
        def _(event):
            self._scroll_by(-3)

        @kb.add("pageup", filter=popup_closed)
        @kb.add("c-b", filter=popup_closed)
        def _(event):
            self._scroll_by(max(1, self._last_window_height - 2))

        @kb.add("pagedown", filter=popup_closed)
        @kb.add("c-f", filter=popup_closed)
        def _(event):
            self._scroll_by(-max(1, self._last_window_height - 2))

        @kb.add("c-u", filter=popup_closed)
        def _(event):
            self._scroll_by(max(1, self._last_window_height // 2))

        @kb.add("c-y", filter=popup_closed)  # c-d는 종료라 피함
        def _(event):
            self._scroll_by(-max(1, self._last_window_height // 2))

        @kb.add("home", filter=popup_closed)
        def _(event):
            self._scroll_offset = max(0, self._last_total_lines - self._last_window_height)
            if self.app is not None:
                self.app.invalidate()

        @kb.add("end", filter=popup_closed)
        def _(event):
            self._scroll_to_bottom()

        return kb

    def _completer(self):
        class SlashCompleter(Completer):
            def get_completions(self, document, complete_event):
                text = document.text_before_cursor
                if not text.startswith("/"):
                    return
                for cmd, desc in slash_commands():
                    if cmd.startswith(text):
                        yield Completion(
                            cmd,
                            start_position=-len(text),
                            display=cmd,
                            display_meta=desc,
                        )
        return SlashCompleter()

    # ─── log 렌더링 (수동 뷰포트 스크롤) ──────────────────

    def _all_log_fragments(self):
        """전체 로그를 fragment 리스트로 변환."""
        if not self._log_lines:
            return []
        text = "\n".join(self._log_lines)
        try:
            return ANSI(text).__pt_formatted_text__()
        except Exception:
            return [("", text)]

    def _split_fragments_by_line(self, fragments):
        """fragment 리스트를 '줄 단위' 2차원 리스트로 분할."""
        lines = [[]]
        for style, text, *rest in fragments:
            if "\n" not in text:
                if text:
                    lines[-1].append((style, text, *rest))
                continue
            parts = text.split("\n")
            for i, part in enumerate(parts):
                if part:
                    lines[-1].append((style, part, *rest))
                if i < len(parts) - 1:
                    lines.append([])
        return lines

    def _window_height(self):
        """로그 창 높이. 렌더 전이면 터미널 높이에서 하단 고정 영역(4줄)을 뺀 값."""
        try:
            info = self.log_window.render_info
            if info is not None and info.window_height > 0:
                return info.window_height
        except Exception:
            pass
        total = shutil.get_terminal_size((80, 24)).lines
        return max(1, total - 4)

    def _get_log_fragments(self):
        """현재 _scroll_offset에 맞춰 로그를 잘라 반환."""
        all_frags = self._all_log_fragments()
        if not all_frags:
            self._last_total_lines = 0
            return []

        lines = self._split_fragments_by_line(all_frags)
        total = len(lines)
        height = self._window_height()
        self._last_total_lines = total
        self._last_window_height = height

        # scroll_offset clamp
        max_offset = max(0, total - height)
        if self._scroll_offset > max_offset:
            self._scroll_offset = max_offset
        if self._scroll_offset < 0:
            self._scroll_offset = 0

        # 창보다 짧으면 전부 표시
        if total <= height:
            return all_frags

        end = total - self._scroll_offset
        start = max(0, end - height)
        visible = lines[start:end]

        result = []
        for i, line in enumerate(visible):
            result.extend(line)
            if i < len(visible) - 1:
                result.append(("", "\n"))
        return result

    def _scroll_by(self, delta_lines):
        """양수=위로 올라가기(과거), 음수=아래로(최신)."""
        new_offset = self._scroll_offset + delta_lines
        max_offset = max(0, self._last_total_lines - self._last_window_height)
        self._scroll_offset = max(0, min(new_offset, max_offset))
        if self.app is not None:
            self.app.invalidate()

    def _scroll_to_bottom(self):
        self._scroll_offset = 0
        if self.app is not None:
            self.app.invalidate()

    def _append(self, text):
        """로그에 섹션 추가 + UI 갱신."""
        self._log_lines.append(text.rstrip("\n"))
        # 새 메시지가 오면 무조건 바닥으로 (항상 최신 표시)
        self._scroll_offset = 0
        if self.app is not None:
            self.app.invalidate()

    def _token_usage_label(self):
        """상태바 좌측에 표시할 토큰 사용량 레이블."""
        try:
            used = self.agent.estimate_tokens()
            window = self.agent.context_window
        except Exception:
            return ""
        if not window:
            return ""

        def _fmt(n):
            return f"{n/1000:.1f}K"

        return f"  {_fmt(used)} / {_fmt(window)} "

    def _append_banner(self):
        def render(c):
            c.print()
            for i, line in enumerate(_DOBIN):
                c.print(RichText(f"   {line}", style=f"bold {_GRADIENT[i % len(_GRADIENT)]}"),
                        no_wrap=True, overflow="ignore", crop=False)
            c.print()
            for i, line in enumerate(_CODE):
                c.print(RichText(f"   {line}", style=f"bold {_GRADIENT[i % len(_GRADIENT)]}"),
                        no_wrap=True, overflow="ignore", crop=False)
            c.print()
        self._append(_rich_to_ansi(render, no_wrap=True))

    # ─── 모델 선택 팝업 ──────────────────────────────────

    def _get_model_popup_fragments(self):
        if not self._model_popup_open:
            return []

        items = self._model_popup_items
        idx = self._model_popup_index
        width = 56

        def pad(s, w):
            visible = 0
            for ch in s:
                visible += 2 if ord(ch) > 0x2e80 else 1
            return s + " " * max(0, w - visible)

        frags = []
        frags.append(("class:popup", pad("", width) + "\n"))
        frags.append(("class:popup.title", pad(t("popup.title"), width) + "\n"))
        frags.append(("class:popup", pad("", width) + "\n"))

        for i, m in enumerate(items):
            active = (i == idx)
            mark = "▶ " if active else "  "
            line = f"  {mark}{i+1}. {m['name']}"
            style = "class:popup.item.current" if active else "class:popup.item"
            frags.append((style, pad(line, width) + "\n"))
            desc_line = f"       {m.get('desc', '')}"
            desc_style = "class:popup.item.current" if active else "class:popup.desc"
            frags.append((desc_style, pad(desc_line, width) + "\n"))

        frags.append(("class:popup", pad("", width) + "\n"))
        frags.append(("class:popup.hint", pad(t("popup.hint"), width) + "\n"))
        frags.append(("class:popup", pad("", width)))
        return frags

    def open_model_popup(self, models, current, on_select):
        """모델 선택 팝업을 연다. on_select(name)이 선택 시 호출됨."""
        self._model_popup_items = list(models)
        self._model_popup_index = 0
        for i, m in enumerate(self._model_popup_items):
            if m["name"] == current:
                self._model_popup_index = i
                break
        self._model_popup_on_select = on_select
        self._model_popup_open = True
        if self.app is not None:
            self.app.invalidate()

    # ─── 실행 동의 팝업 ──────────────────────────────────

    def _get_consent_popup_fragments(self):
        if not self._consent_popup_open:
            return []

        width = 76

        def pad(s, w):
            visible = 0
            for ch in s:
                visible += 2 if ord(ch) > 0x2e80 else 1
            return s + " " * max(0, w - visible)

        cmd = self._consent_popup_command or ""
        # 긴 명령어는 여러 줄로 쪼갬
        cmd_lines = []
        remaining = cmd
        body_w = width - 6
        while remaining:
            cmd_lines.append(remaining[:body_w])
            remaining = remaining[body_w:]
        if not cmd_lines:
            cmd_lines = [""]

        frags = []
        frags.append(("class:popup", pad("", width) + "\n"))
        frags.append(("class:popup.title", pad(t("consent.title"), width) + "\n"))
        frags.append(("class:popup", pad("", width) + "\n"))
        for line in cmd_lines:
            frags.append(("class:popup.item", pad(f"   $ {line}", width) + "\n"))
        frags.append(("class:popup", pad("", width) + "\n"))
        frags.append(("class:popup.hint", pad(t("consent.hint"), width) + "\n"))
        frags.append(("class:popup", pad("", width)))
        return frags

    def open_consent_popup(self, command: str, on_choice):
        """bash 실행 동의 팝업을 연다. on_choice(approved: bool)이 호출됨."""
        self._consent_popup_command = command
        self._consent_popup_on_choice = on_choice
        self._consent_popup_open = True
        if self.app is not None:
            self.app.invalidate()

    def _resolve_consent(self, approved: bool):
        cb = self._consent_popup_on_choice
        self._consent_popup_open = False
        self._consent_popup_on_choice = None
        self._consent_popup_command = ""
        if cb is not None:
            try:
                cb(approved)
            except Exception:
                pass
        if self.app is not None:
            self.app.invalidate()

    # ─── 퍼블릭 출력 API (에이전트에서 호출) ────────────

    def log_tool_call(self, tool_name, args):
        label, icon = tool_label(tool_name)
        summary = _format_tool_args(tool_name, args)

        def render(c):
            c.print()
            line = RichText()
            line.append(f"  {icon}  ", style="")
            line.append(label, style="bold #e5e7eb")
            if summary:
                line.append("  ", style="")
                line.append(str(summary), style="#9ca3af")
            c.print(line)
        self._append(_rich_to_ansi(render))

    def log_tool_result(self, result, short=True):
        text = str(result).rstrip() or t("output.empty")
        lines = text.split("\n")
        max_lines = 3 if short else 60
        preview = lines[:max_lines]
        remaining = len(lines) - len(preview)

        def render(c):
            width = _term_width()
            card_w = width - 8
            for line in preview:
                if len(line) > card_w - 4:
                    line = line[:card_w - 5] + "…"
                row = RichText()
                row.append("     ", style="")
                row.append(" " + line + " " * max(0, card_w - len(line) - 1),
                           style="#d1d5db on #1f2937")
                c.print(row)
            if remaining > 0:
                more = RichText()
                more.append("     ", style="")
                more_text = t("output.more_lines", n=remaining)
                more.append(more_text + " " * max(0, card_w - len(more_text)),
                            style="italic #9ca3af on #1f2937")
                c.print(more)
        self._append(_rich_to_ansi(render))

    def log_response(self, text):
        def render(c):
            c.print()
            header = RichText()
            header.append("▎", style="bold #ff8c00")
            header.append(" DOBIN CODE ", style="agent")
            header.append(_timestamp(), style="muted")
            c.print(header)

        header_ansi = _rich_to_ansi(render)

        body_buf = io.StringIO()
        body_console = Console(
            file=body_buf,
            theme=_RICH_THEME,
            force_terminal=True,
            color_system="truecolor",
            width=_term_width() - 4,
            legacy_windows=False,
        )
        try:
            body_console.print(Markdown(text, code_theme="monokai"))
        except Exception:
            body_console.print(text)

        body_lines = body_buf.getvalue().rstrip("\n").split("\n")
        bar_ansi = "\x1b[1;38;2;255;140;0m▎\x1b[0m "
        body_with_bar = "\n".join(bar_ansi + l for l in body_lines)

        self._append(header_ansi + body_with_bar)

    def log_error(self, text):
        def render(c):
            c.print()
            line = RichText()
            line.append("  ✗ ", style="err")
            line.append(str(text), style="#fca5a5")
            c.print(line)
        self._append(_rich_to_ansi(render))

    def log_success(self, text):
        def render(c):
            line = RichText()
            line.append("  ✓ ", style="ok")
            line.append(str(text), style="#d1d5db")
            c.print(line)
        self._append(_rich_to_ansi(render))

    def log_user_echo(self, text):
        """사용자가 입력한 명령을 위아래 선 사이에 표시."""
        def render(c):
            width = _term_width()
            inner = width - 4
            rule = "─" * inner
            c.print()
            c.print(RichText(f"  {rule}", style="#3b82f6"))
            line = RichText()
            line.append("  › ", style="bold #60a5fa")
            line.append(text, style="#dbeafe")
            c.print(line)
            c.print(RichText(f"  {rule}", style="#3b82f6"))
        self._append(_rich_to_ansi(render))

    def log_info(self, text):
        def render(c):
            c.print(RichText(f"  {text}", style="#9ca3af"))
        self._append(_rich_to_ansi(render))

    def log_help(self):
        def render(c):
            c.print()
            c.print(RichText(f"  {t('help.title')}", style="dobin"))
            for cmd, desc in slash_commands():
                row = RichText()
                row.append(f"   {cmd:<10}", style="bold #a78bfa")
                row.append(desc, style="muted")
                c.print(row)
        self._append(_rich_to_ansi(render))

    def log_models(self, models, current):
        def render(c):
            c.print()
            c.print(RichText(f"  {t('models.title')}", style="dobin"))
            for i, m in enumerate(models):
                active = (m["name"] == current)
                mark = "●" if active else "○"
                style = "bold #ff8c00" if active else "muted"
                row = RichText()
                row.append(f"  {mark} ", style=style)
                row.append(f"{i+1}. ", style="muted")
                row.append(m["name"], style="bold #e5e7eb" if active else "#d1d5db")
                row.append(f"  {m['desc']}", style="muted")
                if active:
                    row.append("  ", style="")
                    row.append(t("badge.current"), style="bold black on #ff8c00")
                c.print(row)
            c.print(RichText(f"  {t('models.hint')}", style="muted"))
        self._append(_rich_to_ansi(render))

    # ─── 입력 수락 핸들러 ────────────────────────────────

    def _on_accept(self, buff):
        text = buff.text.strip()
        if not text or self.is_busy:
            return False
        buff.reset()
        asyncio.get_event_loop().create_task(self._run_user_input(text))
        return False

    async def _run_user_input(self, text):
        self.is_busy = True
        self.app.invalidate()
        try:
            await self.on_user_input(self, text)
        except Exception as e:
            self.log_error(t("handler.error", err=e))
        finally:
            self.is_busy = False
            if self.app is not None:
                self.app.invalidate()

    # ─── 실행 ───────────────────────────────────────────

    def run(self):
        import sys
        sys.stdout.write("\x1b]0;dobin\x07")
        sys.stdout.flush()
        self.app = Application(
            layout=self._layout,
            key_bindings=self._kb,
            style=self._style,
            full_screen=True,
            mouse_support=True,
        )
        self.app.run()

    def exit(self):
        if self.app is not None:
            self.app.exit()

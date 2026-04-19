import asyncio
import json
import ollama
from prompt_toolkit.document import Document

from core.config import AVAILABLE_MODELS, DEFAULT_MODEL, save_config
from core.tools import TOOL_DEFINITIONS, execute_tool
from core.memory import DobinMemory
from core.tui import DobinTUI
from core.i18n import t, set_lang, get_lang


def _system_prompt():
    """현재 언어에 맞는 시스템 프롬프트."""
    return t("system_prompt")


class DobinAgent:
    def __init__(self, config):
        self.config = config
        self.model = config["model"]
        self.workdir = config["workdir"]
        # None = unlimited tool-call iterations
        self.max_iterations = config.get("max_iterations")
        self.context_window = config.get("context_window", 128_000)
        self.auto_compact_ratio = config.get("auto_compact_ratio", 0.85)
        self.bash_consent = config.get("bash_consent", True)
        self.memory = DobinMemory(self.workdir)
        self.messages = [{"role": "system", "content": _system_prompt()}]

    # ─────────────────────────────────────────────────────
    #  TUI에서 호출되는 비동기 콜백
    # ─────────────────────────────────────────────────────

    async def handle_input(self, tui: DobinTUI, user_input: str):
        """사용자 입력 한 건을 처리. 명령어는 동기, 채팅은 모델 루프."""
        # 사용자 입력을 에코로 로그에 남김
        tui.log_user_echo(user_input)

        if user_input.startswith("/"):
            await self._handle_command(tui, user_input)
            return

        # 일반 메시지 — 에이전트 루프
        self.memory.log_request(user_input)
        self.messages.append({"role": "user", "content": user_input})

        iteration = 0
        while True:
            iteration += 1
            if self.max_iterations is not None and iteration > self.max_iterations:
                tui.log_error(t("iter.max"))
                break

            # 대화가 너무 길어지면 자동 요약
            await self._maybe_auto_compact(tui)

            try:
                response = await asyncio.to_thread(
                    ollama.chat,
                    model=self.model,
                    messages=self.messages,
                    tools=TOOL_DEFINITIONS,
                )
            except Exception as e:
                tui.log_error(t("model.call_error", err=e))
                return

            message = response.get("message", {})
            content = message.get("content", "")
            tool_calls = message.get("tool_calls", [])

            if tool_calls:
                self.messages.append(message)
                for tc in tool_calls:
                    func = tc.get("function", {})
                    tool_name = func.get("name", "")
                    args = func.get("arguments", {})

                    # bash 도구는 사용자 동의 필요
                    if tool_name == "bash" and self.bash_consent:
                        approved = await self._ask_bash_consent(tui, args)
                        if not approved:
                            tui.log_tool_call(tool_name, args)
                            denial = t("consent.denied")
                            tui.log_tool_result(denial)
                            self.messages.append({
                                "role": "tool",
                                "name": tool_name,
                                "content": denial,
                            })
                            continue

                    tui.log_tool_call(tool_name, args)

                    result = await asyncio.to_thread(execute_tool, tool_name, args, self.workdir)

                    tui.log_tool_result(result)

                    self.memory.log_tool(
                        tool_name,
                        json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args),
                        str(result)[:200],
                    )

                    self.messages.append({
                        "role": "tool",
                        "name": tool_name,
                        "content": str(result),
                    })
                continue

            if content:
                tui.log_response(content)
                self.memory.log_response(content)
                self.messages.append({"role": "assistant", "content": content})
            break

    # ─────────────────────────────────────────────────────
    #  자동 요약 (auto-compact)
    # ─────────────────────────────────────────────────────

    def estimate_tokens(self) -> int:
        """현재 self.messages의 대략적 토큰 수 추정 (문자 수 / 4)."""
        total_chars = 0
        for m in self.messages:
            c = m.get("content")
            if c:
                total_chars += len(str(c))
            for tc in (m.get("tool_calls") or []):
                fn = tc.get("function", {}) or {}
                total_chars += len(str(fn.get("name", "")))
                args = fn.get("arguments")
                if args is not None:
                    total_chars += len(str(args))
            name = m.get("name")
            if name:
                total_chars += len(str(name))
        return total_chars // 4

    async def _maybe_auto_compact(self, tui: DobinTUI):
        """토큰이 임계치(context_window × ratio)를 넘으면 자동 요약."""
        if self.context_window <= 0 or self.auto_compact_ratio <= 0:
            return
        threshold = int(self.context_window * self.auto_compact_ratio)
        if self.estimate_tokens() < threshold:
            return
        await self._compact(tui, auto=True)

    async def _compact(self, tui: DobinTUI, auto: bool = False):
        """오래된 메시지를 모델에 한 줄 요약 시키고 압축한다.

        전략: system 메시지는 유지. 최근 10개 메시지는 보존.
        그 사이의 메시지들을 요약해서 single system 메시지로 대체.
        """
        if len(self.messages) <= 12:
            return

        head = self.messages[0:1]  # 원본 system prompt
        tail = self.messages[-10:]  # 최근 10개 보존
        middle = self.messages[1:-10]
        if not middle:
            return

        tui.log_info(t("compact.running") if auto else t("compact.manual"))

        # 요약 프롬프트
        summary_msgs = [
            {"role": "system", "content": t("compact.system")},
            {"role": "user", "content": self._serialize_for_summary(middle)},
        ]
        try:
            resp = await asyncio.to_thread(
                ollama.chat,
                model=self.model,
                messages=summary_msgs,
            )
            summary = resp.get("message", {}).get("content", "").strip()
        except Exception as e:
            tui.log_error(t("compact.error", err=e))
            return

        if not summary:
            return

        compact_msg = {
            "role": "system",
            "content": t("compact.prefix") + "\n" + summary,
        }
        self.messages = head + [compact_msg] + tail
        tui.log_success(t("compact.done", n=len(middle)))

    @staticmethod
    def _serialize_for_summary(msgs):
        """요약용으로 메시지들을 텍스트로 직렬화."""
        lines = []
        for m in msgs:
            role = m.get("role", "")
            if role == "tool":
                name = m.get("name", "tool")
                content = str(m.get("content", ""))[:400]
                lines.append(f"[tool:{name}] {content}")
            elif role == "assistant":
                content = m.get("content", "") or ""
                tool_calls = m.get("tool_calls") or []
                if tool_calls:
                    names = ", ".join(
                        tc.get("function", {}).get("name", "?") for tc in tool_calls
                    )
                    lines.append(f"[assistant→tools] {names}")
                if content:
                    lines.append(f"[assistant] {content[:400]}")
            elif role == "user":
                lines.append(f"[user] {str(m.get('content', ''))[:400]}")
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────
    #  bash 실행 동의
    # ─────────────────────────────────────────────────────

    async def _ask_bash_consent(self, tui: DobinTUI, args: dict) -> bool:
        """bash 실행 전 사용자 동의를 얻는다. (y/n 팝업)"""
        command = args.get("command", "") if isinstance(args, dict) else str(args)
        loop = asyncio.get_event_loop()
        future = loop.create_future()

        def _on_choice(approved: bool):
            if not future.done():
                future.set_result(approved)

        tui.open_consent_popup(command, _on_choice)
        return await future

    # ─────────────────────────────────────────────────────
    #  슬래시 명령어
    # ─────────────────────────────────────────────────────

    async def _handle_command(self, tui: DobinTUI, user_input: str):
        cmd = user_input.lower().strip()

        if cmd in ("/quit", "/exit", "/종료"):
            tui.log_success(t("exit.bye"))
            await asyncio.sleep(0.2)
            tui.exit()
            return

        if cmd in ("/clear", "/초기화"):
            self.messages = [{"role": "system", "content": _system_prompt()}]
            tui._log_lines.clear()
            tui.log_buffer.set_document(
                Document(text="", cursor_position=0),
                bypass_readonly=True,
            )
            tui._append_banner()
            tui.log_success(t("clear.done"))
            return

        if cmd in ("/help", "/도움"):
            tui.log_help()
            return

        if cmd in ("/compact", "/요약"):
            await self._compact(tui, auto=False)
            return

        if cmd in ("/consent", "/동의"):
            self.bash_consent = not self.bash_consent
            self.config["bash_consent"] = self.bash_consent
            try:
                save_config(self.config)
            except Exception:
                pass
            key = "consent.on" if self.bash_consent else "consent.off"
            tui.log_success(t(key))
            return

        if cmd.startswith("/language") or cmd.startswith("/언어"):
            parts = user_input.split(maxsplit=1)

            def _apply(name):
                if not set_lang(name):
                    tui.log_error(t("lang.usage"))
                    return
                self.config["language"] = name
                try:
                    save_config(self.config)
                except Exception:
                    pass
                # 다음 턴부터 새 언어로 응답하도록 system prompt 갱신
                if self.messages and self.messages[0]["role"] == "system":
                    self.messages[0]["content"] = _system_prompt()
                tui.log_success(t("lang.changed"))

            if len(parts) < 2:
                items = [
                    {"name": "en", "desc": "English"},
                    {"name": "ko", "desc": "한국어"},
                ]
                tui.open_model_popup(items, get_lang(), _apply)
            else:
                _apply(parts[1].strip().lower())
            return

        if cmd.startswith("/model") or cmd.startswith("/모델"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                arg = parts[1].strip()
                new_model = None
                if arg.isdigit():
                    idx = int(arg) - 1
                    if 0 <= idx < len(AVAILABLE_MODELS):
                        new_model = AVAILABLE_MODELS[idx]["name"]
                if new_model is None:
                    for m in AVAILABLE_MODELS:
                        if m["name"] == arg or m["name"].startswith(arg):
                            new_model = m["name"]
                            break
                if new_model is None:
                    new_model = arg
                self.model = new_model
                self.config["model"] = self.model
                tui.log_success(t("model.changed", name=self.model))
            else:
                def _on_select(name):
                    self.model = name
                    self.config["model"] = name
                    tui.log_success(t("model.changed", name=name))
                tui.open_model_popup(AVAILABLE_MODELS, self.model, _on_select)
            return

        if cmd in ("/history", "/기록"):
            if not self.memory.important_tasks:
                tui.log_info(t("history.empty"))
            else:
                for task in self.memory.important_tasks:
                    tui.log_info(f"• [{task.category}] {task.title} ({task.status})")
            return

        if cmd in ("/dir", "/디렉토리"):
            tui.log_tool_call("list_dir", {"path": self.workdir})
            result = execute_tool("list_dir", {"path": self.workdir}, self.workdir)
            tui.log_tool_result(result, short=False)
            return

        tui.log_error(t("unknown.cmd", cmd=user_input))

    # ─────────────────────────────────────────────────────
    #  진입점
    # ─────────────────────────────────────────────────────

    def run_interactive(self):
        tui = DobinTUI(agent=self, on_user_input=self.handle_input)
        tui.run()

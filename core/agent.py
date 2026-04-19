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
        self.max_iterations = config.get("max_iterations", 20)
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
        while iteration < self.max_iterations:
            iteration += 1

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

        if iteration >= self.max_iterations:
            tui.log_error(t("iter.max"))

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

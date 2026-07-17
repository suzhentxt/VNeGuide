"""Interactive terminal application for VNeGuide."""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Any

from vneguide.cli.contracts import ConversationSession, SessionFactory
from vneguide.cli.renderer import render_turn_result
from vneguide.cli.runtime import CliConfigurationError, load_session_factory

DISCLAIMER = (
    "VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và chuẩn bị hồ sơ. "
    "Kết quả không phải quyết định hành chính và không thay thế việc kiểm tra "
    "của cơ quan có thẩm quyền."
)

WELCOME = "VNeGuide Terminal MVP — nhập /status, /reset hoặc /quit để điều khiển."


class TerminalApp:
    """Run terminal I/O around an injected stateful conversation session."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], Any] = print,
    ) -> None:
        self._session_factory = session_factory
        self._input = input_fn
        self._output = output_fn
        self._session: ConversationSession | None = None
        self._last_result: object | None = None

    def _new_session(self) -> None:
        old_session = self._session
        close = getattr(old_session, "close", None)
        if callable(close):
            close()
        self._session = self._session_factory()
        self._last_result = None

    def _handle_command(self, command: str) -> bool:
        if command == "/quit":
            self._output("Đã kết thúc phiên. Dữ liệu tạm trong CLI đã được xóa.")
            return False
        if command == "/reset":
            self._new_session()
            self._output("Đã tạo phiên hội thoại mới.")
            return True
        if command == "/status":
            if self._last_result is None:
                self._output("Chưa có trạng thái hồ sơ trong phiên này.")
            else:
                self._output(render_turn_result(self._last_result, include_reply=False))
            return True

        self._output("Lệnh không hợp lệ. Dùng /status, /reset hoặc /quit.")
        return True

    def run(self) -> int:
        """Run until quit, EOF, or keyboard interruption."""

        self._new_session()
        self._output(WELCOME)
        self._output(DISCLAIMER)

        try:
            while True:
                try:
                    message = self._input("Bạn: ").strip()
                except EOFError:
                    self._output("Đã nhận EOF, kết thúc phiên.")
                    break
                except KeyboardInterrupt:
                    self._output("\nĐã dừng theo yêu cầu, kết thúc phiên.")
                    break

                if not message:
                    continue
                if message.startswith("/"):
                    if not self._handle_command(message.casefold()):
                        break
                    continue

                try:
                    if self._session is None:  # Defensive; _new_session runs above.
                        self._new_session()
                    session = self._session
                    if session is None:  # pragma: no cover - factory would have raised first.
                        raise RuntimeError("Session factory did not create a session.")
                    result = session.send(message)
                except Exception:  # noqa: BLE001 - terminal boundary must return a safe error.
                    self._output(
                        "Không thể xử lý lượt này. Dữ liệu đã nhập không được ghi ra log; "
                        "vui lòng thử lại hoặc dùng /reset."
                    )
                    continue

                self._last_result = result
                self._output(render_turn_result(result))
        finally:
            close = getattr(self._session, "close", None)
            if callable(close):
                close()
            self._session = None
            self._last_result = None
        return 0


def main() -> int:
    """CLI entry point used by ``python -m vneguide.cli``."""

    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(errors="replace")

    try:
        factory = load_session_factory()
        return TerminalApp(factory).run()
    except CliConfigurationError as exc:
        print(f"Lỗi cấu hình CLI: {exc}")
        print(
            "Hãy cấu hình VNEGUIDE_SESSION_FACTORY tới factory tạo ConversationSession "
            "của core (mặc định: vneguide.core:create_session)."
        )
        return 2
    except Exception:  # noqa: BLE001 - do not leak provider/session details to the terminal.
        print("Không thể khởi tạo phiên VNeGuide. Hãy kiểm tra cấu hình provider và thử lại.")
        return 2

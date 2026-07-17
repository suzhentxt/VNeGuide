from __future__ import annotations

import unittest
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from vneguide.cli.app import DISCLAIMER, TerminalApp


@dataclass
class FakeIssue:
    field_path: str
    severity: str
    reason: str
    suggested_fix: str


@dataclass
class FakeTurnResult:
    reply: str
    procedure_type: str
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    draft: dict[str, Any] = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    validation_issues: list[FakeIssue] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    next_action: str = "ask_missing_field"


class FakeSession:
    def __init__(self, result: FakeTurnResult) -> None:
        self.result = result
        self.messages: list[str] = []
        self.closed = False

    def send(self, message: str) -> FakeTurnResult:
        self.messages.append(message)
        return self.result

    def close(self) -> None:
        self.closed = True


def input_from(messages: list[str]) -> Callable[[str], str]:
    iterator = iter(messages)
    return lambda _prompt: next(iterator)


class TerminalAppIntegrationTest(unittest.TestCase):
    def test_turn_status_and_quit_render_documented_contract(self) -> None:
        result = FakeTurnResult(
            reply="Tôi sẽ giúp bạn làm rõ yêu cầu cấp bản sao trích lục khai sinh.",
            procedure_type="2.000635",
            extracted_fields={"subject.full_name": "Nguyễn Văn A"},
            draft={"applicant": {"cccd": "012345678901"}},
            missing_fields=["registration_place"],
            validation_issues=[
                FakeIssue(
                    field_path="registration_place",
                    severity="error",
                    reason="Chưa có nơi đăng ký hộ tịch.",
                    suggested_fix="Nhập cơ quan hoặc địa phương đã đăng ký.",
                )
            ],
            source_ids=["SRC-DVC-2000635"],
        )
        session = FakeSession(result)
        output: list[str] = []
        app = TerminalApp(
            lambda: session,
            input_fn=input_from(["Tôi cần xin lại giấy khai sinh.", "/status", "/quit"]),
            output_fn=output.append,
        )

        self.assertEqual(app.run(), 0)
        transcript = "\n".join(output)
        self.assertIn(DISCLAIMER, transcript)
        self.assertIn("2.000635", transcript)
        self.assertIn("registration_place", transcript)
        self.assertIn("SRC-DVC-2000635", transcript)
        self.assertIn("********8901", transcript)
        self.assertNotIn("012345678901", transcript)
        self.assertEqual(session.messages, ["Tôi cần xin lại giấy khai sinh."])
        self.assertTrue(session.closed)
        self.assertEqual(transcript.count("Trợ lý:"), 1)

    def test_reset_replaces_session_and_clears_status(self) -> None:
        result = FakeTurnResult("Đã nhận.", "2.000635")
        sessions: list[FakeSession] = []

        def factory() -> FakeSession:
            session = FakeSession(result)
            sessions.append(session)
            return session

        output: list[str] = []
        app = TerminalApp(
            factory,
            input_fn=input_from(["Xin trích lục khai sinh", "/reset", "/status", "/quit"]),
            output_fn=output.append,
        )

        app.run()

        self.assertEqual(len(sessions), 2)
        self.assertTrue(all(session.closed for session in sessions))
        self.assertIn("Chưa có trạng thái hồ sơ trong phiên này.", output)

    def test_unsupported_result_does_not_populate_draft(self) -> None:
        result = FakeTurnResult(
            reply="MVP chỉ hỗ trợ cấp bản sao trích lục hộ tịch.",
            procedure_type="out_of_scope",
            draft={},
            missing_fields=[],
            next_action="redirect_safely",
        )
        output: list[str] = []
        app = TerminalApp(
            lambda: FakeSession(result),
            input_fn=input_from(["Tôi cần bản sao trích lục kết hôn.", "/quit"]),
            output_fn=output.append,
        )

        app.run()
        transcript = "\n".join(output)

        self.assertIn("out_of_scope", transcript)
        self.assertIn("Hồ sơ nháp:\n{}", transcript)
        self.assertIn("redirect_safely", transcript)

    def test_session_failure_returns_safe_message_and_keeps_running(self) -> None:
        class FailingSession:
            def send(self, _message: str) -> FakeTurnResult:
                raise RuntimeError("secret raw input must not be displayed")

        output: list[str] = []
        app = TerminalApp(
            FailingSession,
            input_fn=input_from(["dữ liệu cá nhân", "/quit"]),
            output_fn=output.append,
        )

        app.run()
        transcript = "\n".join(output)

        self.assertIn("Không thể xử lý lượt này", transcript)
        self.assertNotIn("secret raw input", transcript)


if __name__ == "__main__":
    unittest.main()

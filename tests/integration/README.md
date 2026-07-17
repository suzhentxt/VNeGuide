# Integration tests

Owner chính: Người 4.

Kiểm thử luồng từ input người dùng đến `TurnResult` bằng mock provider.

- `test_cli.py`: terminal transcript, command lifecycle, safe error và renderer.
- `test_runtime.py`: session factory boundary.
- `test_repository_safety.py`: quality gate phát hiện secret hiển nhiên trong file Người 4 sở hữu.
- `test_live_smoke.py`: smoke test provider thật, mặc định skip và chỉ chạy opt-in.


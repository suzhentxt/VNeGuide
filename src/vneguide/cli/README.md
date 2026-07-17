# CLI

Owner: Người 4.

Chứa vòng lặp nhập/xuất terminal và các lệnh `/status`, `/reset`, `/quit`. CLI chỉ gọi public interface của core, không chứa business logic hoặc bản sao domain model.

Các module:

```text
__main__.py
app.py
contracts.py
renderer.py
runtime.py
```

`ConversationSession` là integration port do CLI sở hữu. Session giữ state nội bộ và trả shared `TurnResult` từ `send(message)`. Factory mặc định được nạp từ `vneguide.core:create_session`; có thể đổi bằng `VNEGUIDE_SESSION_FACTORY` mà không sửa CLI.


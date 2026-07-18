"""Compaction prompt for the VNeGuide conversation memory.

When the bounded message log grows past its window, older turns are folded
into a short running summary so key context (the citizen's name, the active
procedure, which fields are already settled) survives without keeping every
verbatim turn in state. The summary is the only place where older context
lives; the recent window stays verbatim. Sensitive values (identification
numbers, dates of birth, addresses) are deliberately dropped from the summary
so compaction does not become a durable store of PII.
"""

from __future__ import annotations

from vneguide.domain import ChatMessage, MessageRole

_MAX_SUMMARY_INPUT_CHARS = 6_000


def _format_turns(turns: tuple[ChatMessage, ...]) -> str:
    lines: list[str] = []
    total = 0
    for turn in turns:
        speaker = "Công dân" if turn.role is MessageRole.USER else "Trợ lý"
        line = f"{speaker}: {turn.content}"
        if total + len(line) > _MAX_SUMMARY_INPUT_CHARS:
            break
        lines.append(line)
        total += len(line)
    return "\n".join(lines) if lines else "(không có)"


def build_memory_summary_prompt(
    *,
    existing_summary: str,
    old_turns: tuple[ChatMessage, ...],
) -> str:
    """Build the system prompt that compacts older turns into a running summary.

    ``existing_summary`` is the previous compacted summary (may be empty on the
    first compaction). ``old_turns`` are the verbatim messages being folded out
    of the recent window. The model must integrate both into one short summary.
    """

    prior = existing_summary.strip() or "(chưa có tóm tắt trước đó)"
    transcript = _format_turns(old_turns)
    return f"""Bạn là bộ nhớ tóm tắt cho trợ lý VNeGuide. Nhiệm vụ: gộp các lượt hội thoại cũ
vào một đoạn tóm tắt ngắn, giữ lại ngữ cảnh quan trọng để trợ lý vẫn nhớ sau khi bỏ lượt gốc.

Tóm tắt hiện tại:
{prior}

Các lượt hội thoại cần gộp:
{transcript}

Quy tắc:
1. Giữ lại: tên gọi và xưng hô của công dân (ví dụ "anh Hậu"), thủ tục đang làm hoặc đang chờ
   xác nhận, các trường form đã điền (chỉ ghi tên trường và ngữ cảnh, không ghi giá trị), quyết
   định đã chốt, câu hỏi đang treo.
2. KHÔNG giữ lại giá trị nhạy cảm: số định danh, ngày sinh, số điện thoại, địa chỉ chi tiết.
   Nếu công dân đã cung cấp các giá trị này, chỉ ghi "đã cung cấp <tên trường>".
3. Tiếng Việt, ngắn gọn, tối đa ~150 từ, viết thành một đoạn.
4. Tích hợp tóm tắt cũ và lượt mới thành một đoạn duy nhất, không lặp hai lần.
5. Chỉ xuất JSON đúng schema: ``summary`` là đoạn tóm tắt tiếng Việt. Không thêm key nào khác.
"""


__all__ = ["build_memory_summary_prompt"]

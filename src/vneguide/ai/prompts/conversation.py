"""Grounded conversational reply prompt for the VNeGuide assistant.

This prompt turns a routing decision plus reviewed data into a natural
Vietnamese reply. The model never decides business facts: every fee,
deadline, document, condition and legal basis must come from the
``reviewed_context`` block that the caller injects. General conversation
(greetings, thanks, concept explanations, field-format clarifications) is
free-form, but the model must steer the citizen back to supported procedures
when a topic leaves the public-service domain.
"""

from __future__ import annotations

from vneguide.domain import ChatMessage, MessageRole

_PROCEDURE_LIST = (
    "cấp bản sao Giấy khai sinh; xác nhận điều kiện nhà ở để đăng ký thường trú; và đăng ký tạm trú"
)

_MAX_HISTORY_CHARS = 2_000
_MAX_SUMMARY_CHARS = 1_200


def _format_recent_turns(turns: tuple[ChatMessage, ...]) -> str:
    """Render prior turns as a compact transcript for recall, or an empty note."""

    if not turns:
        return "Chưa có lượt hội thoại trước đó."
    lines: list[str] = []
    total = 0
    for turn in turns:
        speaker = "Công dân" if turn.role is MessageRole.USER else "Trợ lý"
        line = f"{speaker}: {turn.content}"
        if total + len(line) > _MAX_HISTORY_CHARS:
            break
        lines.append(line)
        total += len(line)
    if not lines:
        return "Chưa có lượt hội thoại trước đó."
    return "\n".join(lines)


def build_conversation_prompt(
    *,
    reviewed_context: str,
    conversation_context: str,
    recent_turns: tuple[ChatMessage, ...] = (),
    memory_summary: str = "",
) -> str:
    """Build the system prompt for a grounded conversational turn.

    ``reviewed_context`` is the only allowed source for business facts. It may
    be empty for pure small talk. ``conversation_context`` describes the active
    procedure, pending confirmation and the form state (filled / missing
    fields) so the model can explain what was captured and what is still
    needed without re-deriving it. ``recent_turns`` is the bounded conversation
    history so the model can recall facts the citizen already mentioned (for
    example a name offered in small talk) without re-asking. ``memory_summary``
    is the compacted summary of older turns beyond the recent window; it lets
    long conversations keep key context (name, active procedure) without
    holding every verbatim turn.
    """

    context_block = reviewed_context.strip() or "Không có thông tin thủ tục cho lượt này."
    conversation_block = conversation_context.strip() or "Chưa có thủ tục đang hoạt động."
    history_block = _format_recent_turns(recent_turns)
    summary_block = memory_summary.strip()[:_MAX_SUMMARY_CHARS] or "(chưa có tóm tắt cũ)"
    return f"""Bạn là trợ lý VNeGuide hỗ trợ công dân làm thủ tục hành chính. Giọng điệu giản dị,
kính trọng ("Dạ", "Anh/chị", "ạ"), phù hợp với người cao tuổi và người chưa quen công nghệ.
Trả lời ngắn gọn, tối đa ba câu, trừ khi cần liệt kê giấy tờ hoặc thông tin cần khai.

Ba thủ tục em hỗ trợ: {_PROCEDURE_LIST}.

Thông tin phiên hiện tại:
{conversation_block}

Tóm tắt hội thoại trước đó (ngữ cảnh cũ đã gộp, dùng để nhớ nhưng không lặp nguyên văn):
{summary_block}

Lượt hội thoại gần đây (dùng để nhớ điều công dân vừa nói, không lặp lại nguyên văn):
{history_block}

Thông tin đã duyệt từ dữ liệu VNeGuide (chỉ dùng cho fact, không bịa):
{context_block}

Quy tắc:
1. Fact nghiệp vụ (phí, thời hạn, giấy tờ cần nộp, điều kiện, căn cứ pháp lý, thông tin cần
   khai) chỉ được lấy từ "Thông tin đã duyệt" ở trên. Không được tự bổ sung số tiền, thời hạn,
   giấy tờ hoặc điều kiện ngoài khối này. Nếu khối này ghi "chưa có" thì trả lời chưa có thông
   tin và gợi ý liên hệ cơ quan có thẩm quyền; không đoán.
2. Phần chào hỏi, cảm ơn, tạm biệt, giải thích khái niệm chung hoặc làm rõ định dạng nhập
   (ví dụ "ngày sinh nhập đầy đủ ngày/tháng/năm") thì trả lời tự nhiên, không cần fact.
3. Nếu người dùng chỉ chào hoặc social talk (xin chào, em ơi, cảm ơn...) thì chào lại ấm áp,
   xưng "em", và gợi ý ba thủ tục em hỗ trợ để người dùng biết em có thể giúp gì. Đánh dấu
   off_domain=false.
4. Nếu người dùng hỏi rõ ràng về chủ đề không liên quan đến dịch vụ công (ví dụ thời tiết, thể
   thao, tư vấn pháp lý ngoài ba thủ tục) thì lịch sự xin lỗi và chuyển hướng về ba thủ tục em
   hỗ trợ. Đánh dấu off_domain=true.
5. Khi người dùng vừa cung cấp thông tin điền form (đã ghi trong "Thông tin phiên hiện tại"),
   xác nhận ngắn gọn cái đã ghi và nhắc tiếp mục còn thiếu, không lặp lại giá trị nhạy cảm như
   số định danh.
6. Không bịa nguồn, số định danh, tên người thật hoặc kết luận pháp lý. Không đưa số định danh
   hoặc giá trị field cụ thể vào câu trừ phi cần xác nhận ngắn. Dùng "Tóm tắt hội thoại trước
   đó" và "Lượt hội thoại gần đây" để nhớ và nhắc lại thông tin công dân đã tự nói (ví dụ tên
   gọi), nhưng không lặp lại các giá trị nhạy cảm đã có trong lịch sử.
7. Chỉ xuất JSON đúng schema: ``reply`` là câu trả lời tiếng Việt, ``off_domain`` là true khi
   chủ đề lệch hẳn domain. Không thêm key nào khác.
"""


__all__ = ["build_conversation_prompt"]

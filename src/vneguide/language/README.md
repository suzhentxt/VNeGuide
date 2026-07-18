# Vietnamese language normalization

Module này chuẩn hóa cách nói vùng miền, viết tắt và lỗi nhận dạng giọng nói trước structured
extraction. Từ điển là tập nhỏ đã review cho ba thủ tục, không được nhúng toàn bộ bảng phương ngữ
vào prompt.

## Luồng xử lý

1. `protected_spans.py` nhận diện họ tên, CCCD, ngày sinh, địa chỉ, mã thủ tục, số điện thoại và mã
   hồ sơ.
2. `normalizer.py` áp dụng deterministic glossary ngoài các span được bảo vệ.
3. Nếu deterministic không thay đổi được câu và `VNEGUIDE_LANGUAGE_MODEL_ASSISTED=1`, tầng model
   nhận câu đã thay định danh bằng placeholder. Model chỉ được chuẩn hóa ngôn ngữ theo strict schema,
   không được suy luận procedure hoặc field.
4. Mỗi đoạn normalized giữ mapping về offset/câu gốc. Structured extractor kiểm tra evidence trên
   câu normalized rồi chuyển evidence về đúng từ người dùng đã nói trước khi tạo suggestion.
5. Cụm mơ hồ đã biết, ví dụ “giấy nhà”, dừng trước model và trả các lựa chọn làm rõ.

`NormalizationResult` chỉ được giữ trong memory của lượt hội thoại. Không log raw text, normalized
text, protected value hoặc prompt đã thay placeholder ở production. API text dùng
`InputSource.TEXT`; speech transcript dùng cùng contract với `InputSource.SPEECH`.

## Đánh giá

Fixture tổng hợp nằm tại `data/evaluation/dialect/`. Chạy:

```bash
python -m pytest tests/unit/test_language_normalizer.py tests/evals/test_dialect_normalization.py
```

Gate yêu cầu accuracy intent sau chuẩn hóa không thấp hơn câu gốc, toàn bộ protected value được giữ
nguyên và không có từ/field bị tự suy luận trong mẫu mơ hồ.

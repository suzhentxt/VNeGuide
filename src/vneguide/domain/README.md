# Domain

Owner: Người 1.

Thư mục này chứa contract dùng chung, enum và domain model. Thay đổi tên field hoặc enum tại đây là breaking change và phải được cả nhóm review.

## Source of truth

- `ProcedureCode` chỉ chứa ba mã trong `data/README.md`.
- Pack/status/severity enum bám trực tiếp JSON Schema trong `data/contracts/`.
- `CaseDraft` dùng map field tổng quát vì ba procedure pack có cấu trúc biểu mẫu khác nhau.
- Module AI, core, rules và CLI phải import contract qua `vneguide.domain`.

## Files

```text
enums.py
models.py
contracts.py
```

Không thêm lại enum `birth_extract`, `marriage_extract` hoặc `death_extract`; đó là scope tài liệu cũ, không phải data package v2.

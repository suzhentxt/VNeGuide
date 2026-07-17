# AI

Owner: Người 2.

Chứa provider adapter, prompt và structured extraction. Module này chỉ hiểu ngôn ngữ và trích xuất dữ liệu; không quyết định required field hoặc tính hợp lệ nghiệp vụ.

Dự kiến:

```text
providers/
prompts/
extractor.py
schemas.py
```

`schemas.py` chỉ chứa schema output riêng của provider; domain model phải import từ `vneguide.domain`.


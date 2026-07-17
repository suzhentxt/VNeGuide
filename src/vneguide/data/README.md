# Procedure data

Owner: Người 1.

Thư mục này chỉ chứa code truy cập data package tại `data/` ở root repository. Dữ liệu đã review nằm trong `data/catalog/`; không tạo bản sao JSON trong package Python.

Dự kiến:

```text
loader.py
repository.py
schema_validator.py
```

Loader phải lấy đường dẫn data package từ cấu hình hoặc từ repository root, không hard-code đường dẫn tuyệt đối.

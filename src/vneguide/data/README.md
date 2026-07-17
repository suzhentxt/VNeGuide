# Procedure data

Owner: Người 1.

Thư mục này chỉ chứa code truy cập data package tại `data/` ở root repository. Dữ liệu đã review nằm trong `data/catalog/`; không tạo bản sao JSON trong package Python.

## Files

```text
loader.py
repository.py
schema_validator.py
errors.py
```

Loader phải lấy đường dẫn data package từ cấu hình hoặc từ repository root, không hard-code đường dẫn tuyệt đối.

## Public API

- `DataPackagePaths.discover()`: tìm data package hoặc đọc `VNEGUIDE_DATA_DIR`.
- `ProcedureRepository`: load và audit procedure packs, catalog, source register.
- `rule_inputs_for()`: lấy contract cho tín hiệu rule không phải field biểu mẫu.
- `validate_json_schema()`: kiểm tra subset JSON Schema đang được dùng trong repo.

Repository từ chối khởi động nếu thiếu pack, trùng ID, catalog không khớp pack, `source_id` không tồn tại hoặc `local_file` bị thiếu.

# Bàn giao phiên

## Trạng thái hiện tại

- Nhánh đang làm việc: `integration/release-dev`, tạo từ `dev`.
- Merge `tuan` đang được hoàn tất để giữ đồng thời LiteLLM, FastAPI Chat API và Next.js demoweb.
- Scope runtime duy nhất nằm trong `data/README.md`: `2.000635`, `1.013314`, `1.004194`.
- Core đã có suggestion `pending/accepted/rejected/edited`, revision guard, validation và question
  selection.
- Web đã có BFF/chatbox nhưng nội dung/route chính vẫn là Hôn nhân và gia đình ngoài scope.
- Session API là in-memory, single-process, có TTL/capacity/per-session lock.

## Việc cần xác minh trên cây hợp nhất

- Cài Python bằng `python -m pip install -e ".[api,dev]"` và web bằng `npm ci`.
- Chạy Ruff, formatter, Mypy, Pytest và coverage trên toàn repo.
- Chạy `npm run check` trong `demoweb`.
- Chạy E2E cho ba thủ tục, out-of-scope, stale revision, reset, timeout và OCR fallback.
- Secret/PII/conflict-marker scan trước commit.
- Public deploy và smoke `/health` chưa có bằng chứng trong nhánh release.

## Rủi ro

- Frontend cũ hiển thị bốn procedure code Hôn nhân và gia đình không có procedure pack backend.
- API hiện chưa trả toàn bộ `draft.values` và chưa có mutation dành cho sửa form trực tiếp.
- AI chưa tạo đủ rule-context signal; live provider smoke không chứng minh accuracy hội thoại.
- LiteLLM gateway HTTP chỉ được dùng với dữ liệu tổng hợp; production cần HTTPS.
- In-memory store không phù hợp nhiều API worker; release demo phải chạy một worker.
- Hai repo đối thủ và các file untracked ở root là tài liệu tham khảo, tuyệt đối không stage/commit.
- Tài liệu Architecture/Terminal cũ vẫn có phần mô tả bộ thủ tục khác data package v2; Product & UX
  đã được đồng bộ về đúng ba thủ tục hiện hành.
- Fixture intent dùng scripted mock nên chỉ kiểm contract/pipeline, không chứng minh accuracy model.
- Freshness `next_review_at`, source governance và business validation thuộc data/domain/rules,
  không được chuyển vào extractor.

## Bước tiếp theo

Hoàn tất merge, đưa commit `709b795` vào, chạy baseline trên dependency sạch, rồi mới bổ sung test,
deployment artifacts, metrics, README, rollback và demo script.

## Lệnh chuẩn

- Python install: `python -m pip install -e ".[api,dev]"`
- Python gates: `python -m ruff check .`, `python -m ruff format --check .`,
  `python -m mypy`, `python -m pytest`
- Coverage: `python -m pytest --cov=vneguide --cov-report=term-missing`
- Web install/check: `cd demoweb`, `npm ci`, `npm run check`
- API: `python -m vneguide.api`
- Web: `cd demoweb`, `npm run dev -- --hostname 0.0.0.0 -p 3000`

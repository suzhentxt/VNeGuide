# **Kế hoạc— Tích hợp VNeGuide vào web dịch vụ công**

## **1\. Tóm tắt**

VNeGuide là **AI copilot cho biểu mẫu dịch vụ công**, được tích hợp trực tiếp vào web mà team đang phát triển. Người dùng chỉ cần nói thủ tục mình muốn làm; AI hỏi các thông tin còn thiếu, đề xuất giá trị cho từng trường và chờ người dùng chọn **Accept**, **Reject** hoặc **Edit**.

Biểu mẫu là nguồn dữ liệu chính thức trên giao diện. AI không tự điền âm thầm, không tự quyết định thay người dùng và không tự nộp hồ sơ.

### **1.1. Luồng sản phẩm cốt lõi**

1\.          Người dùng nhập yêu cầu bằng ngôn ngữ tự nhiên, ví dụ: “Tôi muốn đăng ký khai sinh cho con”.

1\.          AI xác định thủ tục và hỏi lần lượt những thông tin còn thiếu.

2\.          AI tạo một thẻ đề xuất cho từng trường, gồm tên trường, giá trị hiện tại, giá trị đề xuất và lý do.

3\.          Người dùng chọn Accept để ghi vào form, Reject để bỏ đề xuất, hoặc Edit để sửa giá trị trước khi xác nhận.

4\.          Sau mỗi xác nhận, AI tiếp tục hỏi phần còn thiếu và kiểm tra lỗi hoặc mâu thuẫn trên bản nháp mới nhất.

5\.          Khi form đủ thông tin, người dùng tự kiểm tra lần cuối và bấm nút tiếp tục/nộp của cổng dịch vụ công.

Người 4 chịu trách nhiệm:

·          Hoàn thiện System Architecture, Safety & Privacy và Delivery Plan.

·          Định nghĩa component contract, shared-state contract và backend API.

·          Thiết kế cách đồng bộ hội thoại với biểu mẫu hiện có.

·          Chuẩn bị checklist để đội web triển khai sau khi source được push.

·          Hợp nhất tài liệu và đối chiếu với Requirement.

·          Không trực tiếp sửa source, review PR hoặc deploy trong phạm vi hiện tại.

## **2\. Kiến trúc tích hợp**

flowchart LR  
 	U\[Người dùng\] \--\> P\[Trang thủ tục hiện có\]

 	subgraph WEB\[Web dịch vụ công\]  
     	P \--\> C\[VNeGuide Chat Panel\]  
     	P \--\> F\[Biểu mẫu thủ tục\]  
     	C \--\> Q\[Suggestion Cards\<br/\>Accept / Reject / Edit\]  
     	Q \--\> S\[Shared Case Draft Store\]  
     	F \--\> S  
     	S \--\> A\[API Client\]  
 	end

 	A \--\> B\[Backend API\]  
 	B \--\> O\[AI Orchestrator\]  
 	O \--\> L\[LLM và RAG\]  
 	O \--\> R\[Rule và Validation Engine\]  
 	O \--\> M\[Form Mapper\]  
 	O \--\> K\[Procedure Repository\]  
 	B \--\> E\[Ephemeral Session Store\]

### **2.1. Trách nhiệm thành phần**

| Thành phần | Trách nhiệm | Không được làm |
| :---- | :---- | :---- |
| VNeGuide Chat Panel | Nhận nhu cầu, hỏi từng thông tin còn thiếu và giải thích ngắn gọn | Tự ghi đè form hoặc tự nộp |
| Suggestion Card | Hiển thị một thay đổi đề xuất và ba hành động Accept/Reject/Edit | Áp dụng khi chưa có thao tác của người dùng |
| Biểu mẫu thủ tục | Hiển thị và sửa dữ liệu chính thức trên UI | Tin dữ liệu AI chưa xác nhận |
| Shared Case Draft Store | Quản lý draftRevision, dirty fields và confirmation state | Lưu lâu dài dữ liệu nhạy cảm |
| API Client | Chuẩn hóa request, timeout, retry và safe error | Đưa PII vào URL hoặc analytics |
| Backend API | Xác thực schema, điều phối và trả request ID | Ghi raw form/chat vào log |
| AI Orchestrator | Gọi LLM/RAG, rules, validation và form mapper | Cho LLM quyết định quy định bắt buộc |
| Procedure Repository | Lưu source, rules và version đã review | Dùng dữ liệu chưa kiểm chứng để kết luận |
| Ephemeral Session Store | Lưu state tạm theo TTL | Trở thành kho hồ sơ người dùng |

### **2.2. Luồng đồng bộ**

1\.          Người dùng mô tả nhu cầu trong VNeGuide.

1\.          Backend xác định thủ tục; nếu chưa chắc chắn thì hỏi lại người dùng.

2\.          AI hỏi thông tin còn thiếu và tạo suggestion có cấu trúc cho từng field.

3\.   UI hiển thị Accept, Reject và Edit trên từng suggestion.

4\.          Accept ghi giá trị đề xuất; Reject giữ nguyên form; Edit ghi giá trị do người dùng sửa và xác nhận.

5\.          Form tăng draftRevision và gửi snapshot mới để validation.

6\.          Lỗi xuất hiện cạnh field và trong chat summary.

7\.          Người dùng tự chọn “Tiếp tục”; VNeGuide không nộp thay.

### **2.3. Quy tắc shared state**

·          Mỗi hồ sơ nháp có draftRevision tăng sau mỗi lần commit.

·          Response cũ hơn revision hiện tại phải bị loại bỏ.

·          Field do người dùng sửa được đánh dấu dirty và không bị ghi đè nếu chưa xác nhận.

·          Suggestion có trạng thái pending, accepted, rejected hoặc edited.

·          Không suggestion nào được commit nếu chưa có hành động rõ ràng của người dùng.

·          Không gửi dữ liệu form theo từng phím gõ; chỉ gửi sau blur, lưu nháp hoặc xác nhận.

·          Form vẫn sử dụng được khi backend AI không hoạt động.

·          Validation issue phải xuất hiện cạnh field và trong chat summary.

## **3\. Component và data contracts**

type ProcedureType \=  
   | "birth\_extract"  
   | "marriage\_extract"  
   | "death\_extract"  
   | "unsupported";

 interface VNeGuideProps {  
   procedureType?: ProcedureType;  
   draft: CaseDraft;  
   draftRevision: number;  
   locale: "vi-VN";  
   sourceVersion: string;  
   onSuggestion: (patch: SuggestedPatch) \=\> void;  
   onValidation: (report: ValidationReport) \=\> void;  
   onEscalate: (reason: EscalationReason) \=\> void;  
   onError: (error: SafeClientError) \=\> void;  
 }

 interface SuggestedPatch {  
   fieldPath: string;  
   currentValue: unknown;  
   suggestedValue: unknown;  
   reason: string;  
   sourceId: string;  
   confidence: number;  
   draftRevision: number;  
   status: "pending" | "accepted" | "rejected" | "edited";  
 }

 interface ValidationIssue {  
   fieldPath?: string;  
   severity: "error" | "warning" | "review";  
   code: string;  
   reason: string;  
   suggestedFix: string;  
   sourceId?: string;  
 }

CaseDraft tối thiểu gồm thông tin người yêu cầu, người được trích lục, loại sự kiện, nơi/thời gian đăng ký, quan hệ, hình thức nhận kết quả, confirmation state và dirty fields.

Thẻ suggestion trên UI tối thiểu phải hiển thị fieldLabel, currentValue, suggestedValue, reason và ba hành động Accept, Reject, Edit. draftRevision là cơ chế kỹ thuật nội bộ để ngăn phản hồi cũ ghi đè dữ liệu mới; người dùng không cần biết khái niệm này.

## **4\. API contract**

| Endpoint | Mục đích | Điều kiện quan trọng |
| :---- | :---- | :---- |
| GET /v1/procedures/{procedureType} | Lấy metadata, checklist và source version | Chỉ trả source đã review |
| POST /v1/sessions | Tạo session tạm | TTL mặc định 30 phút |
| POST /v1/intake/turn | Xử lý một lượt hội thoại | Có sessionId và draftRevision |
| POST /v1/suggestions | Tạo patch điền trước | Không tự commit vào form |
| POST /v1/validate | Kiểm tra snapshot đã xác nhận | Trả issue code và cách sửa |
| DELETE /v1/sessions/{sessionId} | Xóa dữ liệu phiên | Idempotent |
| GET /healthz | Health check | Không gọi model inference |

OpenAPI máy đọc được: vneguide-openapi.yaml.

Mọi request thay đổi hồ sơ phải có sessionId, draftRevision, procedureType, confirmedFields và sourceVersion. Mọi response phải có requestId, draftRevision, sourceVersion, warnings, nextAction và safe error không chứa PII.

## **5\. Safety & Privacy**

·          Demo ưu tiên dữ liệu giả và cảnh báo trước khi người dùng nhập dữ liệu thật.

·          Không thu mật khẩu, OTP, VNeID token hoặc chữ ký số.

·          Không gửi hoặc tự nộp hồ sơ tới hệ thống nhà nước.

·          Không lưu raw form, raw chat hoặc số định danh trong analytics/log.

·          Session TTL mặc định 30 phút và hỗ trợ xóa chủ động.

·          Log chỉ gồm request ID, latency, procedure type, source/model version và error code.

·          Dữ liệu nhạy cảm được redact khỏi log và safe error.

·          Không dùng dữ liệu người dùng để huấn luyện nếu chưa có đồng ý rõ ràng.

·          Mọi suggestion phải được người dùng xác nhận trước khi commit.

·          API áp dụng schema validation, rate limit và request-size limit.

·          Trước production phải có review pháp lý và đánh giá bảo vệ dữ liệu riêng.

Thông báo bắt buộc:

VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và điền trước hồ sơ. Kết quả không phải quyết định hành chính và không thay thế việc kiểm tra của cơ quan có thẩm quyền.

## **6\. Failure-mode register**

| Failure mode | Kiểm soát và fallback | Owner |
| :---- | :---- | :---- |
| Nhận diện sai loại trích lục | Yêu cầu xác nhận trước khi tạo suggestion | AI/Product |
| Suggestion ánh xạ sai field | Schema/mapping tests; không tự commit | AI/Web |
| Response cũ ghi đè state mới | So sánh draftRevision và loại response cũ | Web |
| Ghi đè field người dùng sửa | Dirty-field tracking và xác nhận riêng | Web |
| Nguồn/rule hết hiệu lực | Chuyển needs\_review, chặn kết luận chắc chắn | Data |
| Model/RAG timeout | Giữ form hoạt động, retry một lần | Backend |
| Prompt injection | Untrusted input và structured output | AI |
| PII trong log/error | Redaction và log scan | Backend |
| Chat/form mất đồng bộ | Session/revision recovery | Web |
| API version không tương thích | Contract test và từ chối version không hỗ trợ | Web/Backend |
| False conflict | Chuyển needs\_review, không tự sửa | AI/Data |
| Người dùng hiểu nhầm pass | Thông điệp không cam kết và disclaimer | Product |

## **7\. Delivery gates**

| Gate | Owner | Dependency | Đầu ra và điều kiện hoàn thành |
| :---- | :---- | :---- | :---- |
| 1\. Product Ready | Người 1 | Scope và flows | Vị trí chat, flow và trạng thái UX đã chốt |
| 2\. Data Ready | Người 2 | Nguồn và biểu mẫu | Field schema, rules và nguồn đã review |
| 3\. AI Ready | Người 3 | Data Ready | Structured outputs, confidence và tests đã chốt |
| 4\. Web Source Ready | Đội web | Source được push | App chạy local; xác định được route/form/store |
| 5\. Integration Mapping | Người 4 | Gate 1–4 | Map route, component, store, API và validation |
| 6\. Contract Freeze | Người 4 | Integration Mapping | Component contract và OpenAPI được duyệt |
| 7\. Implementation Handoff | Người 4 | Contract Freeze | Đội code có đủ checklist và wire shape |
| 8\. Integration Verification | Web/QA | Code đã tích hợp | Acceptance tests có evidence |
| 9\. Documentation Freeze | Người 4 | Verification | Master document khớp implementation |
| 10\. Demo Readiness | Deployment owner | Build đã kiểm thử | Public URL và smoke tests đạt |

## **8\. Integration mapping sau khi source được push**

| Hạng mục | Giá trị hiện tại | Người xác nhận |
| :---- | :---- | :---- |
| Framework và package manager | PENDING\_SOURCE | Đội web |
| Route chứa thủ tục | PENDING\_SOURCE | Đội web |
| Component biểu mẫu chính | PENDING\_SOURCE | Đội web |
| State management | PENDING\_SOURCE | Đội web |
| Validation library/schema | PENDING\_SOURCE | Đội web |
| API-client convention | PENDING\_SOURCE | Đội web |
| Authentication/session | PENDING\_SOURCE | Đội web |
| Deployment target | PENDING\_SOURCE | Deployment owner |

PENDING\_SOURCE là dependency đã ghi nhận. Người 4 phải thay bằng tên thực tế sau khi source xuất hiện, không để người implement tự chọn.

## **9\. Integration acceptance checklist**

·          ☐ Chat nhận diện và chuyển đúng form context cho ba loại trích lục.

·          ☐ Yêu cầu mơ hồ không tự động điền dữ liệu.

·          ☐ Suggestion được chấp nhận cập nhật đúng field.

·          ☐ Suggestion bị từ chối không thay đổi form.

·          ☐ Suggestion được sửa ghi đúng giá trị người dùng nhập và chuyển sang trạng thái edited.

·          ☐ Không suggestion nào tự áp dụng khi người dùng chưa chọn hành động.

·          ☐ Field đã sửa thủ công không bị AI ghi đè.

·          ☐ Response có revision cũ bị loại bỏ.

·          ☐ Validation issue xuất hiện cạnh field và trong chat summary.

·          ☐ Form vẫn hoạt động khi backend AI timeout.

·          ☐ Refresh trang xử lý session/draft đúng policy.

·          ☐ Xóa phiên loại bỏ dữ liệu tạm.

·          ☐ Không có PII trong URL, console, analytics hoặc safe error.

·          ☐ VNeGuide không gọi hành động nộp hồ sơ.

·          ☐ Luồng nhập nhu cầu → hướng dẫn → kiểm tra form chạy trên public URL.

·          ☐ OpenAPI, UI contract và implementation dùng cùng enum/field/status.

## **10\. Deliverables và Definition of Done**

### **Deliverables**

·          Master VNeGuide hoàn thiện mục 7, 8, 10 và phụ lục kỹ thuật.

·          Ba sơ đồ Mermaid: component, sequence và data flow.

·          Component/shared-state contract.

·          OpenAPI 3.1 contract.

·          Safety/privacy policy và failure-mode register.

·          Delivery gates và integration mapping.

·          Requirement traceability và acceptance checklist.

·          Open-decisions log.

### **Definition of Done**

·          ☐ Kiến trúc mô tả đúng VNeGuide là component trong web hiện có.

·          ☐ Form là source of truth và AI chỉ tạo suggestion.

·          ☐ Luồng yêu cầu → hỏi thiếu → suggestion → Accept/Reject/Edit chạy hoàn chỉnh trên web.

·          ☐ Contract xử lý revision, dirty fields và xác nhận người dùng.

·          ☐ API đủ để đội web triển khai mà không tự quyết định wire shape.

·          ☐ Tài liệu không mô tả iframe là phương án MVP.

·          ☐ Người 1–3 đã duyệt phần liên quan.

·          ☐ Placeholder source được thay bằng tên thực tế sau khi code được push.

·          ☐ Requirement về kiến trúc, API, tích hợp và roadmap có bằng chứng.

## **11\. Open decisions**

| Quyết định | Owner | Trạng thái |
| :---- | :---- | :---- |
| Route và vị trí VNeGuide | Đội web/Người 1 | BLOCKED\_BY\_SOURCE |
| State store và form schema | Đội web/Người 2 | BLOCKED\_BY\_SOURCE |
| Model provider và model ID | Người 3 | PENDING\_AI\_OWNER |
| Hosting frontend/backend | Deployment owner | PENDING\_DEPLOYMENT\_OWNER |
| Session persistence khi refresh | Đội web/Người 4 | PENDING\_REVIEW |

Không đánh dấu tài liệu hoặc demo hoàn thành khi quyết định ảnh hưởng trực tiếp tới implementation vẫn ở trạng thái blocked hoặc pending.


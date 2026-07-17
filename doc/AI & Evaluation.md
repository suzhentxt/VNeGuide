### **1\. Metrics**

### **1.1. Nhóm Hiệu suất AI & NLU (AI & Natural Language Understanding)**

Nhóm này đo lường "não bộ" của AI trong việc hiểu ngôn ngữ tự nhiên và trích xuất dữ liệu chính xác.

| Metric | Mô tả chi tiết | Tham chiếu ngành (Industry Benchmark) | Mục tiêu VNeGuide MVP | Cách thức đo lường |
| :---- | :---- | :---- | :---- | :---- |
| **Intent Recognition Accuracy** | Tỷ lệ nhận diện đúng loại trích lục (Khai sinh/Kết hôn/Khai tử) hoặc nhận diện luồng ngoài phạm vi. | 85% \- 90% | **\> 95%** | Test set 100+ câu hỏi tự nhiên đa dạng ngữ cảnh. |
| **Slot Filling / Entity Extraction** | Tỷ lệ trích xuất đúng thông tin (tên, ngày tháng, nơi chốn) từ câu chat để chuẩn bị map vào JSON. | 80% \- 85% | **\> 90%** | So sánh output JSON của LLM với dữ liệu chuẩn (Ground truth). |
| **Hallucination Rate** | Tỷ lệ AI tự bịa thông tin, tự đoán giấy tờ không có thật hoặc sinh ra dữ liệu giả để điền form. | \< 5% (Bot thường) | **0%** (Zero Tolerance) | QA duyệt thủ công các kịch bản biên (Edge cases). |

### 

### 

### 

### 

### **1.2. Nhóm Xử lý Nghiệp vụ & Kỹ thuật (Business Logic & System)**

Nhóm này đo lường khả năng vận hành của Rule Engine, độ mượt của việc kết nối giữa AI và giao diện.

| Metric | Mô tả chi tiết | Tham chiếu ngành (Industry Benchmark) | Mục tiêu VNeGuide MVP | Cách thức đo lường |
| :---- | :---- | :---- | :---- | :---- |
| **Auto-fill / Mapping Accuracy** | Tỷ lệ dữ liệu từ JSON được điền chính xác vào đúng field trên giao diện mô phỏng. | 90% | **100%** | Đánh giá E2E (End-to-End) trên giao diện. |
| **Rule Validation Accuracy** | Khả năng chặn đứng 100% các lỗi thiếu trường bắt buộc hoặc sai format (số CCCD, ngày tháng) trước khi submit. | 95% | **100%** | Chạy bộ Test case cố tình nhập sai/nhập thiếu định dạng. |
| **System Response Time** | Thời gian từ khi user gửi tin nhắn đến khi UI hiển thị trạng thái đang gõ/điền form. | \< 2-4 giây | **\< 3 giây** | Đo log API (Latency tracking). |
| **Editability Success** | Tỷ lệ hệ thống ghi nhận đúng dữ liệu cuối cùng khi người dùng chủ động sửa tay (override) thông tin AI đã điền. | N/A | **100%** | QA test trực tiếp hành vi ghi đè trên UI. |

### 

### **1.3. Nhóm Trải nghiệm Người dùng & Luồng (UX & Conversational Flow)**

Nhóm này đo lường sự thoải mái, tính tiện dụng và khả năng giữ chân người dùng hoàn thành thủ tục.

| Metric | Mô tả chi tiết | Tham chiếu ngành (Industry Benchmark) | Mục tiêu VNeGuide MVP | Cách thức đo lường |
| :---- | :---- | :---- | :---- | :---- |
| **Task Success Rate (Form Completion)** | Tỷ lệ các phiên người dùng đi đến được trạng thái "Hồ sơ sẵn sàng nộp" (Nút Tiếp tục sáng lên) thành công. | 70% \- 80% | **\> 85%** | Chia tỷ lệ: (Số phiên hoàn thành / Tổng số phiên bắt đầu). |
| **Average Turns per Task** | Số lượt hội thoại qua lại trung bình để hoàn thành một biểu mẫu trích lục. Càng ít càng tốt. | 4 \- 6 lượt | **≤ 5 lượt** | Trích xuất từ lịch sử hội thoại lưu trong DB. |
| **User Correction Rate** | Tỷ lệ người dùng phải tự click vào form để sửa lại thông tin do AI điền sai/thiếu logic. Càng thấp càng tốt. | 15% \- 20% | **\< 10%** | Tracking event click/edit trên các field của form. |
| **Error / Fallback Recovery Rate** | Tỷ lệ AI hướng dẫn lại thành công khi người dùng nhập thông tin rác hoặc vượt ngoài phạm vi MVP. | 75% \- 85% | **\> 95%** | Test kịch bản cố tình phá bĩnh luồng (Troll/Nonsense input). |

### 

## **2\. Test Scenarios (Kịch Bản Kiểm Thử Demo)**

Bộ test case cần tập trung vào luồng tương tác giữa hội thoại và hành động cập nhật trạng thái trên giao diện mô phỏng.

* **Scenario 1: Luồng trơn tru (Auto-fill trọn vẹn) \- Trích lục khai tử**  
  * *Input:* Người dùng cung cấp một câu đầy đủ thông tin (người mất, ngày mất, nơi đăng ký, người yêu cầu).  
  * *Expected Output:* AI không hỏi thêm, trực tiếp chuyển đổi cấu trúc dữ liệu và tự động điền kín các trường tương ứng trên biểu mẫu. Nút "Tiếp tục" sáng lên chờ người dùng xác nhận.  
* **Scenario 2: Luồng ngắt quãng (Bổ sung thông tin) \- Trích lục khai sinh**  
  * *Input:* Người dùng chỉ nhập nhu cầu xin trích lục, thiếu thông tin về người được cấp và nơi cấp.  
  * *Expected Output:* AI fill các trường đã biết, bỏ trống các trường thiếu và đánh dấu highlight. AI đặt câu hỏi yêu cầu bổ sung. Khi người dùng trả lời, AI tiếp tục fill các trường còn lại.  
* **Scenario 3: Xử lý mâu thuẫn & Chỉnh sửa thủ công**  
  * *Input:* AI đã điền năm sinh là 2020 dựa trên chat. Người dùng phát hiện sai, tự click vào field trên form và sửa thành 2021\.  
  * *Expected Output:* Form nhận diện thay đổi. Khi bấm "Tiếp tục", hệ thống lưu giá trị 2021, AI không được tự động ghi đè lại giá trị cũ.  
* **Scenario 4: Chặn luồng ngoài phạm vi**  
  * *Input:* Cung cấp thông tin để "Đăng ký khai sinh mới".  
  * *Expected Output:* AI từ chối điền form, giải thích rõ MVP chỉ hỗ trợ cấp bản sao trích lục và hướng dẫn người dùng tìm đúng luồng thủ tục.

## **3\. Definition of Done (Định Nghĩa Hoàn Thành MVP)**

* Hoàn thiện luồng cho 3 loại thủ tục: Cấp bản sao trích lục khai sinh, kết hôn, khai tử.  
* Khả năng chuyển đổi ngôn ngữ tự nhiên thành dữ liệu có cấu trúc (JSON/Schema) hoạt động ổn định.  
* Giao diện Frontend mô phỏng nhận và render được dữ liệu từ AI để tự động điền vào các text box, dropdown, date picker tương ứng.  
* Trạng thái biểu mẫu hiển thị rõ ràng: trường nào AI đã điền, trường nào còn thiếu, trường nào đang bị lỗi định dạng.  
* Hệ thống có ranh giới hành động rõ ràng: AI chỉ hỗ trợ chuẩn bị và điền, tuyệt đối không tự động kích hoạt sự kiện "Nộp" (Submit/Next) thay người dùng.  
* Mọi thông tin cá nhân giả lập trong phiên demo bị xóa hoàn toàn sau khi tải lại trang hoặc kết thúc phiên.

## **4\. Delivery Plan & Milestones (Kế Hoạch Bàn Giao)**

Tiến độ cần phân bổ lại để nhóm phát triển tập trung vào việc thiết kế schema dữ liệu chuẩn giữa AI và giao diện.

| Milestone | Giai đoạn | Công việc trọng tâm | Thời hạn | Owner |
| :---- | :---- | :---- | :---- | :---- |
| **M1** | Thiết kế luồng & Schema | Chốt các trường dữ liệu cần thiết của 3 biểu mẫu; định nghĩa JSON schema để AI trả về cho Frontend. | Tuần 1 | BA / Thiết kế UI |
| **M2** | Tích hợp AI & Xử lý NLP | Viết prompt cho LLM để trích xuất thực thể (NER); cấu hình Rule Engine kiểm tra tính hợp lệ của dữ liệu. | Tuần 2 | AI Engineer |
| **M3** | Phát triển Frontend Auto-fill | Dựng form mô phỏng dịch vụ công; viết logic nhận JSON từ backend để auto-fill các trường; xử lý state khi người dùng chỉnh sửa. | Tuần 3 | Dev Team |
| **M4** | Kiểm thử Tích hợp (E2E) | Chạy các kịch bản kiểm thử; kiểm tra độ mượt của UI khi AI đang "gõ" dữ liệu vào form; fix lỗi mapping. | Tuần 4 | QA / Dev Team |
| **M5** | Đóng gói & Triển khai Demo | Deploy bản mô phỏng lên URL công khai; tổng duyệt toàn bộ tài liệu hướng dẫn demo. | Tuần 5 | Project Coordinator |

## 

## **5\. Dependency & Risk Management (Quản Lý Phụ Thuộc & Rủi Ro)**

### **Phụ thuộc (Dependencies)**

* **Giao tiếp Client \- Server:** Logic auto-fill phụ thuộc hoàn toàn vào cấu trúc JSON mà AI trả về. Đội AI và đội Frontend phải chốt chặt chẽ cấu trúc này từ M1; bất kỳ thay đổi nào về tên trường (field name) đều có thể làm hỏng chức năng điền form.  
* **Quản lý Trạng thái (State Management):** Việc duy trì tính nhất quán giữa nội dung chat của AI và trạng thái hiện tại của form do người dùng thao tác cần được xử lý kỹ lưỡng.

### **Rủi ro (Risks) & Phương án xử lý**

* **Rủi ro AI điền sai trường (Mismapping):** AI lấy tên người yêu cầu điền nhầm vào ô tên người được cấp trích lục.  
  * *Khắc phục:* Viết test script tự động kiểm tra chéo các giá trị sinh ra từ LLM với logic nghiệp vụ trước khi đẩy lên UI.  
* **Rủi ro vòng lặp hội thoại:** AI liên tục hỏi lại một thông tin do Rule Engine không bắt được định dạng câu trả lời của người dùng.  
  * *Khắc phục:* Thiết lập giới hạn số lần hỏi (retry limit). Nếu quá 2 lần không trích xuất được, cho phép người dùng nhập trực tiếp vào biểu mẫu.


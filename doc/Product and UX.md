# **VNeGuide MVP**

## **Trợ lý AI hướng dẫn và điền trước hồ sơ cấp bản sao trích lục hộ tịch**

## **Tóm tắt sản phẩm**

**VNeGuide là trợ lý AI được tích hợp vào luồng làm thủ tục dịch vụ công, giúp người dân xin bản sao trích lục khai sinh, kết hôn hoặc khai tử.**

**Người dùng chỉ cần mô tả nhu cầu và trả lời một số câu hỏi đơn giản. VNeGuide sẽ xác định đúng loại trích lục, thu thập thông tin, kiểm tra lỗi và tự động điền trước biểu mẫu. Người dùng kiểm tra lại nội dung, chỉnh sửa nếu cần và chủ động chuyển sang bước tiếp theo.**

**Trong MVP, quy trình được triển khai trên một giao diện mô phỏng Cổng Dịch vụ công vì chưa có API tích hợp chính thức.**

---

# **1\. Problem & Goal**

## **Vấn đề**

**Khi xin bản sao trích lục hộ tịch, người dân thường gặp các khó khăn:**

* **Không biết nhu cầu của mình tương ứng với thủ tục nào.**  
* **Không phân biệt được cấp bản sao trích lục với đăng ký mới hoặc đăng ký lại.**  
* **Không biết cần chuẩn bị thông tin và giấy tờ gì.**  
* **Gặp khó khăn khi đọc và điền biểu mẫu hành chính.**  
* **Phải nhập thủ công nhiều trường và dễ sai sót.**  
* **Chỉ phát hiện thiếu hoặc sai thông tin sau khi đã hoàn thành nhiều bước.**

## **Mục tiêu MVP**

**VNeGuide giúp người dân:**

1. **Xác định đúng loại trích lục cần xin.**  
2. **Hiểu rõ thông tin và giấy tờ cần chuẩn bị.**  
3. **Cung cấp thông tin qua giao diện hội thoại đơn giản.**  
4. **Phát hiện trường còn thiếu hoặc sai định dạng.**  
5. **Tự động điền trước dữ liệu vào biểu mẫu dịch vụ công.**  
6. **Kiểm tra và xác nhận trước khi chuyển sang bước nộp.**

**AI chỉ hỗ trợ chuẩn bị hồ sơ. Người dùng vẫn là người kiểm tra, xác nhận và quyết định nộp.**

---

# **2\. Users & Scope**

## **Người dùng chính**

* **Người cần xin bản sao trích lục khai sinh.**  
* **Người cần xin bản sao trích lục kết hôn.**  
* **Người cần xin bản sao trích lục khai tử.**  
* **Người lần đầu sử dụng dịch vụ công trực tuyến.**  
* **Người lớn tuổi hoặc không quen với biểu mẫu hành chính.**  
* **Người thực hiện thủ tục thay cho người thân trong trường hợp được phép.**

## **Trong phạm vi MVP**

**MVP hỗ trợ một thủ tục chính:**

**Cấp bản sao trích lục hộ tịch**

**Với ba loại sự kiện hộ tịch:**

* **Khai sinh.**  
* **Kết hôn.**  
* **Khai tử.**

**MVP bao gồm:**

* **Tiếp nhận nhu cầu bằng ngôn ngữ tự nhiên.**  
* **Xác định loại trích lục phù hợp.**  
* **Đặt câu hỏi làm rõ.**  
* **Cung cấp checklist thông tin và giấy tờ.**  
* **Kiểm tra trường bắt buộc và định dạng dữ liệu.**  
* **Phát hiện một số thông tin chưa thống nhất.**  
* **Tự động điền trước biểu mẫu.**  
* **Cho phép người dùng xem và chỉnh sửa.**  
* **Hiển thị nguồn thông tin chính thức.**  
* **Mô phỏng bước chuyển sang nộp hồ sơ.**

## **Ngoài phạm vi MVP**

**MVP chưa thực hiện:**

* **Đăng ký khai sinh mới.**  
* **Đăng ký kết hôn mới.**  
* **Đăng ký khai tử mới.**  
* **Đăng ký lại sự kiện hộ tịch.**  
* **Gửi hồ sơ thật tới Cổng Dịch vụ công.**  
* **Đăng nhập hoặc xác thực bằng VNeID.**  
* **Thu thập mật khẩu, OTP hoặc chữ ký số.**  
* **Thanh toán phí hoặc lệ phí.**  
* **Tự động bấm nút nộp thay người dùng.**  
* **Phê duyệt hoặc xác nhận hồ sơ hợp lệ chính thức.**

---

# **3\. Core User Flow**

**Người dùng mở trang thủ tục**

        **↓**

**Mô tả nhu cầu cho VNeGuide**

        **↓**

**AI xác định loại trích lục**

        **↓**

**AI hỏi các câu làm rõ**

        **↓**

**Hệ thống tạo checklist**

        **↓**

**Người dùng cung cấp thông tin**

        **↓**

**Hệ thống kiểm tra thiếu và sai**

        **↓**

**Người dùng bổ sung hoặc chỉnh sửa**

        **↓**

**VNeGuide tự động điền biểu mẫu**

        **↓**

**Người dùng kiểm tra lại**

        **↓**

**Người dùng nhấn “Tiếp tục”**

## **Ba tình huống demo chính**

### **Tình huống 1: Xin trích lục khai sinh cho bản thân**

**Người dùng nhập:**

**“Tôi cần xin lại giấy khai sinh.”**

**AI làm rõ đây là yêu cầu cấp bản sao trích lục khai sinh, không phải đăng ký khai sinh mới hoặc đăng ký lại khai sinh.**

### **Tình huống 2: Xin trích lục khai tử cho người thân**

**AI cần xác định:**

* **Người được trích lục là ai.**  
* **Quan hệ giữa người yêu cầu và người đã mất.**  
* **Thông tin về nơi và thời gian đăng ký khai tử.**  
* **Có cần bổ sung giấy tờ chứng minh hay không.**

### **Tình huống 3: Yêu cầu chưa rõ về kết hôn**

**Người dùng nhập:**

**“Tôi cần giấy xác nhận đã kết hôn.”**

**AI phải làm rõ người dùng cần:**

* **Bản sao trích lục kết hôn; hay**  
* **Một thủ tục khác như xác nhận tình trạng hôn nhân.**

**Nếu không thuộc phạm vi MVP, hệ thống chuyển hướng tới thủ tục phù hợp thay vì tự suy đoán.**

---

# **4\. Product Behavior**

**VNeGuide có năm hành vi chính.**

## **4.1. Xác định nhu cầu**

**AI hiểu cách diễn đạt đời thường và xác định người dùng đang cần:**

* **Trích lục khai sinh.**  
* **Trích lục kết hôn.**  
* **Trích lục khai tử.**  
* **Hoặc một thủ tục khác ngoài phạm vi MVP.**

## **4.2. Hỏi thông tin có hướng dẫn**

**AI chỉ hỏi những thông tin cần thiết cho trường hợp cụ thể.**

**Thông tin đã có sẽ không được hỏi lại. Thông tin chưa chắc chắn phải được người dùng xác nhận.**

## **4.3. Hướng dẫn thủ tục**

**Hệ thống hiển thị:**

* **Tên thủ tục.**  
* **Thông tin cần kê khai.**  
* **Giấy tờ cần chuẩn bị.**  
* **Cơ quan tiếp nhận.**  
* **Hình thức thực hiện.**  
* **Thời hạn giải quyết.**  
* **Phí hoặc lệ phí nếu có.**  
* **Cách nhận kết quả.**  
* **Nguồn tham khảo.**

## **4.4. Kiểm tra dữ liệu**

**Hệ thống kiểm tra:**

* **Trường bắt buộc bị bỏ trống.**  
* **Sai định dạng ngày tháng.**  
* **Số định danh không đúng định dạng.**  
* **Thiếu thông tin về sự kiện hộ tịch.**  
* **Thiếu thông tin nơi đã đăng ký hộ tịch.**  
* **Mâu thuẫn giữa các trường.**  
* **Trường hợp người yêu cầu và người được trích lục chưa rõ ràng.**

**Mỗi lỗi phải cho biết:**

* **Lỗi nằm ở trường nào.**  
* **Vì sao cần sửa.**  
* **Người dùng nên sửa như thế nào.**

## **4.5. Điền trước biểu mẫu**

**Sau khi đủ thông tin, hệ thống chuyển dữ liệu hội thoại thành dữ liệu có cấu trúc và ánh xạ vào biểu mẫu.**

**Ví dụ:**

**Họ tên người yêu cầu**

**Ngày sinh**

**Số định danh**

**Quan hệ với người được trích lục**

**Loại sự kiện hộ tịch**

**Họ tên người được trích lục**

**Nơi đăng ký hộ tịch**

**Năm đăng ký**

**Hình thức nhận kết quả**

**Người dùng luôn có quyền sửa dữ liệu trước khi chuyển sang bước tiếp theo.**

---

# **5\. Data & Regulations**

**Dữ liệu thủ tục được thu thập và kiểm tra từ các nguồn chính thức:**

* **Cổng Dịch vụ công Quốc gia.**  
* **Cổng thông tin của Bộ Tư pháp.**  
* **Cổng dịch vụ công của địa phương triển khai thử nghiệm.**  
* **Quyết định công bố thủ tục hành chính.**  
* **Biểu mẫu hộ tịch chính thức.**  
* **Văn bản pháp luật liên quan.**

**Mỗi thủ tục phải lưu tối thiểu:**

**Mã thủ tục**

**Tên thủ tục**

**Loại sự kiện hộ tịch**

**Cơ quan thực hiện**

**Thành phần hồ sơ**

**Các trường biểu mẫu**

**Trình tự thực hiện**

**Thời hạn**

**Phí hoặc lệ phí**

**Căn cứ pháp lý**

**Đường dẫn nguồn**

**Ngày kiểm tra gần nhất**

**Phiên bản dữ liệu**

**Người kiểm tra**

**Mỗi quy tắc kiểm tra phải liên kết được với nguồn chính thức. Dữ liệu chưa được kiểm chứng không được sử dụng để đưa ra kết luận chắc chắn.**

---

# **6\. AI Approach**

**VNeGuide kết hợp bốn thành phần.**

## **LLM**

**LLM thực hiện:**

* **Hiểu câu hỏi tự nhiên.**  
* **Phân loại nhu cầu ban đầu.**  
* **Đặt câu hỏi làm rõ.**  
* **Giải thích thủ tục bằng ngôn ngữ dễ hiểu.**  
* **Diễn giải lỗi cho người dùng.**

## **RAG**

**RAG truy xuất nội dung từ kho dữ liệu thủ tục và nguồn chính thức để hỗ trợ câu trả lời có căn cứ.**

## **Rule Engine**

**Rule engine quyết định:**

* **Trường nào bắt buộc.**  
* **Câu hỏi nào cần hỏi.**  
* **Khi nào đủ dữ liệu.**  
* **Dữ liệu nào sai định dạng.**  
* **Dữ liệu nào mâu thuẫn.**  
* **Khi nào phải yêu cầu người dùng bổ sung.**

## **Form Mapper**

**Form Mapper chuyển dữ liệu đã xác nhận sang đúng trường trong biểu mẫu dịch vụ công mô phỏng.**

**LLM không được:**

* **Tự thêm giấy tờ không có trong nguồn.**  
* **Tự đoán dữ liệu còn thiếu.**  
* **Tự kết luận hồ sơ đã được cơ quan nhà nước chấp nhận.**  
* **Tự nộp hồ sơ thay người dùng.**

---

# **7\. System Architecture**

**Người dùng**

    **↓**

**Giao diện mô phỏng Cổng Dịch vụ công**

**├── Khung hội thoại VNeGuide**

**└── Biểu mẫu thủ tục**

    **↓**

**Backend API**

    **↓**

**AI Orchestrator**

**├── LLM**

**├── RAG**

**├── Rule Engine**

**├── Validation Engine**

**└── Form Mapper**

    **↓**

**Kho dữ liệu thủ tục và nguồn tham khảo**

**Do chưa có API chính thức, phần hội thoại và biểu mẫu trong MVP sẽ dùng chung dữ liệu trạng thái trên hệ thống demo.**

**Khi người dùng trả lời trong hội thoại, dữ liệu sẽ được đồng bộ trực tiếp sang biểu mẫu mô phỏng.**

**Trong tương lai, VNeGuide có thể tích hợp vào hệ thống thật dưới dạng:**

* **Widget.**  
* **Chatbot.**  
* **API điền trước biểu mẫu.**  
* **Nút “Hỗ trợ bằng AI”.**

---

# **8\. Safety & Privacy**

**Trong phiên bản demo:**

* **Ưu tiên sử dụng dữ liệu giả.**  
* **Không yêu cầu mật khẩu hoặc OTP.**  
* **Không thực hiện đăng nhập VNeID.**  
* **Không gửi hồ sơ tới hệ thống nhà nước.**  
* **Không lưu đầy đủ số định danh trong nhật ký.**  
* **Che dữ liệu nhạy cảm trên giao diện và log.**  
* **Cho phép xóa dữ liệu sau phiên sử dụng.**  
* **Không sử dụng dữ liệu người dùng để huấn luyện khi chưa được đồng ý.**  
* **Người dùng phải kiểm tra và xác nhận mọi dữ liệu được điền trước.**

**Thông báo trên giao diện:**

**VNeGuide chỉ hỗ trợ hướng dẫn, kiểm tra và điền trước hồ sơ. Kết quả của hệ thống không phải quyết định hành chính và không thay thế việc kiểm tra của cơ quan có thẩm quyền.**

---

# **9\. Evaluation**

**MVP được đánh giá theo các tiêu chí sau:**

| Chỉ số | Mục tiêu |
| ----- | ----- |
| **Xác định đúng loại trích lục** | **≥ 90% tình huống kiểm thử** |
| **Phát hiện trường bắt buộc bị thiếu** | **≥ 95%** |
| **Phát hiện lỗi định dạng cơ bản** | **≥ 90%** |
| **Điền đúng trường biểu mẫu** | **≥ 95%** |
| **Hướng dẫn có nguồn tham khảo** | **100%** |
| **Hoàn thành luồng demo từ đầu đến cuối** | **100% tình huống chính** |
| **Thời gian phản hồi trung bình** | **Dưới 5 giây** |

**Bộ kiểm thử cần bao gồm:**

* **Trường hợp thông thường.**  
* **Trường hợp thiếu thông tin.**  
* **Trường hợp nhập sai.**  
* **Trường hợp yêu cầu không rõ ràng.**  
* **Trường hợp nằm ngoài phạm vi MVP.**

---

# **10\. Delivery Plan**

| Giai đoạn | Công việc | Kết quả hoàn thành |
| ----- | ----- | ----- |
| **1\. Chuẩn hóa dữ liệu** | **Thu thập nguồn và biểu mẫu** | **Bộ dữ liệu ba loại trích lục** |
| **2\. Xây dựng nghiệp vụ** | **Tạo câu hỏi, checklist và rules** | **Luồng nghiệp vụ đã kiểm thử** |
| **3\. Xây dựng backend AI** | **LLM, RAG, validation và form mapping** | **API hoạt động** |
| **4\. Xây dựng frontend** | **Hội thoại và biểu mẫu mô phỏng** | **Luồng tự động điền hoạt động** |
| **5\. Kiểm thử** | **Chạy các tình huống đúng, thiếu và sai** | **Báo cáo kết quả** |
| **6\. Triển khai** | **Đưa website lên môi trường công khai** | **URL demo hoạt động** |

---

# **Thông điệp sản phẩm**

**VNeGuide biến quá trình xin bản sao trích lục hộ tịch từ việc tự đọc, tự hiểu và tự điền biểu mẫu thành một cuộc hội thoại đơn giản. AI thu thập và kiểm tra thông tin, điền trước hồ sơ, còn người dân là người kiểm tra, xác nhận và quyết định nộp.**


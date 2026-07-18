export const marriageRoutes = {
  category: "/hon-nhan-va-gia-dinh",
  services: "/hon-nhan-va-gia-dinh/dich-vu-cong",
  detail: "/hon-nhan-va-gia-dinh/dang-ky-ket-hon",
  apply: "/hon-nhan-va-gia-dinh/dang-ky-ket-hon/truc-tuyen",
  submission: "/hon-nhan-va-gia-dinh/dang-ky-ket-hon/nop-ho-so",
  eForm: "/hon-nhan-va-gia-dinh/dang-ky-ket-hon/to-khai",
} as const;

export interface MarriageCategory {
  title: string;
  procedures: readonly string[];
}

export interface MarriageService {
  id: string;
  title: string;
  level: string;
  authority: string;
  audience: string;
  fee: string;
}

export interface MetadataField {
  label: string;
  value: string;
  wide?: boolean;
}

export interface ImplementationMethod {
  method: string;
  duration: string;
  fee: string;
  description: string;
}

export interface DossierItem {
  name: string;
  quantity: string;
}

export const marriageCategories: readonly MarriageCategory[] = [
  {
    title: "Kết hôn",
    procedures: [
      "Thủ tục đăng ký kết hôn có yếu tố nước ngoài",
      "Thủ tục đăng ký kết hôn",
      "Thủ tục đăng ký kết hôn có yếu tố nước ngoài tại khu vực biên giới",
    ],
  },
  {
    title: "Cải chính, trích lục hộ tịch",
    procedures: [
      "Thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc có yếu tố nước ngoài",
      "Thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
    ],
  },
  {
    title: "Giám hộ",
    procedures: [
      "Thủ tục đăng ký chấm dứt giám hộ có yếu tố nước ngoài",
      "Thủ tục đăng ký giám hộ",
      "Thủ tục đăng ký giám hộ có yếu tố nước ngoài",
    ],
  },
  {
    title: "Nhận con nuôi",
    procedures: [
      "Đăng ký việc nuôi con nuôi trong nước",
      "Đăng ký lại việc nuôi con nuôi trong nước",
      "Giải quyết việc nuôi con nuôi có yếu tố nước ngoài đối với trường hợp nhận con riêng, cháu ruột làm con nuôi",
      "Thủ tục đăng ký việc nuôi con nuôi tại Cơ quan đại diện Việt Nam ở nước ngoài",
      "Cấp giấy xác nhận công dân Việt Nam ở trong nước đủ điều kiện nhận trẻ em nước ngoài làm con nuôi",
    ],
  },
  {
    title: "Nhận cha, mẹ, con",
    procedures: [
      "Thủ tục đăng ký nhận cha, mẹ, con",
      "Thủ tục đăng ký nhận cha, mẹ, con có yếu tố nước ngoài tại khu vực biên giới",
    ],
  },
] as const;

export const marriageServices: readonly MarriageService[] = [
  {
    id: "ubnd-phuong-cau-giay",
    title: "Thủ tục đăng ký kết hôn",
    level: "DVCTT toàn trình",
    authority: "UBND phường Cầu Giấy",
    audience: "Công dân Việt Nam",
    fee:
      "Miễn lệ phí. Phí cấp bản sao Trích lục kết hôn (nếu có yêu cầu) thực hiện theo quy định hiện hành.",
  },
  {
    id: "phong-kinh-te-ha-tang-do-thi-cau-giay",
    title: "Thủ tục đăng ký kết hôn",
    level: "DVCTT toàn trình",
    authority: "Phòng Kinh tế, Hạ tầng và Đô thị phường Cầu Giấy",
    audience: "Công dân Việt Nam",
    fee:
      "Miễn lệ phí. Phí cấp bản sao Trích lục kết hôn (nếu có yêu cầu) thực hiện theo quy định hiện hành.",
  },
] as const;

export const procedureMetadata: readonly MetadataField[] = [
  { label: "Tên thủ tục", value: "Thủ tục đăng ký kết hôn", wide: true },
  { label: "Mã thủ tục", value: "1.000894" },
  { label: "Số quyết định", value: "163/QĐ-BTP" },
  { label: "Cấp thực hiện", value: "Cấp xã" },
  {
    label: "Loại thủ tục",
    value: "TTHC được luật giao quy định chi tiết",
  },
  { label: "Lĩnh vực", value: "Hộ tịch" },
  { label: "Đối tượng thực hiện", value: "Công dân Việt Nam" },
  {
    label: "Cơ quan có thẩm quyền",
    value: "Ủy ban Nhân dân xã, phường, thị trấn",
    wide: true,
  },
  { label: "Cơ quan được ủy quyền", value: "Không có thông tin" },
  { label: "Cơ quan phối hợp", value: "Không có thông tin" },
  {
    label: "Thủ tục hành chính liên quan",
    value: "Không có thông tin",
    wide: true,
  },
] as const;

export const procedureSteps = [
  "Người yêu cầu đăng ký kết hôn lựa chọn nộp hồ sơ trực tiếp tại Trung tâm Phục vụ hành chính công có thẩm quyền hoặc nộp trực tuyến trên Cổng Dịch vụ công Quốc gia, cung cấp đầy đủ thông tin và tài liệu theo quy định.",
  "Cán bộ tiếp nhận kiểm tra tính chính xác, đầy đủ và hợp lệ của hồ sơ. Hồ sơ hợp lệ được tiếp nhận và gửi phiếu hẹn; hồ sơ chưa đầy đủ được hướng dẫn bổ sung, hoàn thiện.",
  "Công chức tư pháp - hộ tịch thẩm tra hồ sơ, đối chiếu dữ liệu và xác minh khi cần thiết. Trường hợp không đủ điều kiện giải quyết, cơ quan tiếp nhận thông báo rõ lý do cho người nộp hồ sơ.",
  "Với hồ sơ trực tuyến, biểu mẫu Giấy chứng nhận kết hôn điện tử được gửi để người yêu cầu kiểm tra và xác nhận thông tin trước khi ghi vào Sổ đăng ký kết hôn.",
  "Công chức tư pháp - hộ tịch in Giấy chứng nhận kết hôn, trình lãnh đạo Ủy ban nhân dân cấp xã ký và chuyển tới Trung tâm Phục vụ hành chính công để trả kết quả.",
  "Hai bên nam, nữ phải có mặt khi nhận kết quả, đối chiếu giấy tờ tùy thân, xác nhận sự tự nguyện kết hôn và ký vào Sổ đăng ký kết hôn, Giấy chứng nhận kết hôn.",
] as const;

const feeDescription =
  "Miễn lệ phí; phí cấp bản sao Trích lục kết hôn (nếu có yêu cầu) thực hiện theo quy định tại Thông tư số 281/2016/TT-BTC.";

export const implementationMethods: readonly ImplementationMethod[] = [
  {
    method: "Trực tuyến",
    duration: "01 ngày",
    fee: "Miễn phí",
    description: feeDescription,
  },
  {
    method: "Dịch vụ bưu chính",
    duration: "01 ngày",
    fee: "Miễn phí",
    description: feeDescription,
  },
  {
    method: "Trực tiếp",
    duration: "01 ngày",
    fee: "Miễn phí",
    description: feeDescription,
  },
] as const;

export const dossierItems: readonly DossierItem[] = [
  {
    name: "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn được kê khai theo hướng dẫn trên Cổng Dịch vụ công.",
    quantity: "01 bản",
  },
  {
    name: "Hộ chiếu, Thẻ căn cước, Căn cước công dân, Căn cước điện tử hoặc giấy tờ khác có ảnh và thông tin cá nhân còn giá trị sử dụng.",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ chứng minh thông tin cư trú khi cơ quan đăng ký hộ tịch không thể khai thác thông tin từ cơ sở dữ liệu quốc gia.",
    quantity: "01 bản chính",
  },
  {
    name: "Bản sao có chứng thực các giấy tờ phải xuất trình trong trường hợp hồ sơ được gửi qua hệ thống bưu chính.",
    quantity: "Theo hồ sơ",
  },
] as const;

export const marriageConditions = [
  "Không có thông tin",
] as const;

export const legalBases = [
  "Nghị quyết số 66.7/2025/NQ-CP",
  "Luật Hôn nhân và gia đình số 52/2014/QH13",
  "Luật Hộ tịch số 60/2014/QH13",
  "Thông tư số 04/2020/TT-BTP",
  "Nghị định số 07/2025/NĐ-CP",
  "Nghị định số 120/2025/NĐ-CP",
  "Thông tư số 01/2022/TT-BTP",
  "Thông tư số 04/2024/TT-BTP",
  "Thông tư số 03/2023/TT-BTP",
  "Thông tư số 106/2021/TT-BTC",
  "Thông tư số 85/2019/TT-BTC",
  "Nghị định số 104/2022/NĐ-CP",
  "Nghị định số 123/2015/NĐ-CP",
  "Thông tư số 08/2025/TT-BTP",
  "Nghị định số 18/2026/NĐ-CP",
  "Nghị định số 87/2020/NĐ-CP",
] as const;

export const popularProcedures = [
  "Hỗ trợ phát triển sản xuất cộng đồng",
  "Hưởng trợ cấp thất nghiệp (Cấp tỉnh)",
  "Cấp Phiếu Lý lịch tư pháp cho công dân Việt Nam",
  "Đổi giấy phép lái xe",
] as const;

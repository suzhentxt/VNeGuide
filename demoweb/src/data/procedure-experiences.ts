import type {
  DossierItem,
  ImplementationMethod,
  MarriageService,
  MetadataField,
} from "@/data/marriage";

export interface ProcedureRoutes {
  detail: string;
  services: string;
  apply: string;
  submission: string;
  eForm: string;
}

export interface OnlineDossierRow {
  id: string;
  name: string;
  required: boolean;
  eForm: boolean;
}

export interface ProcedureExperience {
  slug: string;
  title: string;
  shortTitle: string;
  code: string;
  decision: string;
  level: string;
  procedureType: string;
  field: string;
  audience: string;
  competentAuthority: string;
  performingAgency: string;
  nationalProcedureId: string;
  justiceProcedureId: string;
  onlineServiceCode: string;
  services: readonly MarriageService[];
  metadata: readonly MetadataField[];
  steps: readonly string[];
  methods: readonly ImplementationMethod[];
  nationalDossier: readonly DossierItem[];
  conditions: readonly string[];
  legalBases: readonly string[];
  result: { label: string; code: string };
  justiceDossier: readonly OnlineDossierRow[];
  formKind: "temporary-residence" | "guided";
  routes: ProcedureRoutes;
}

function createRoutes(slug: string): ProcedureRoutes {
  const root = `/hon-nhan-va-gia-dinh/${slug}`;
  return {
    detail: root,
    services: `${root}/dich-vu-cong`,
    apply: `${root}/truc-tuyen`,
    submission: `${root}/nop-ho-so`,
    eForm: `${root}/to-khai`,
  };
}

function metadata(experience: {
  title: string;
  code: string;
  field: string;
  authority: string;
  audience: string;
  processingTime: string;
}): readonly MetadataField[] {
  return [
    { label: "Tên thủ tục", value: experience.title, wide: true },
    { label: "Mã thủ tục", value: experience.code },
    { label: "Cấp thực hiện", value: "Cấp xã" },
    { label: "Lĩnh vực", value: experience.field },
    { label: "Đối tượng thực hiện", value: experience.audience },
    { label: "Cơ quan thực hiện", value: experience.authority, wide: true },
    { label: "Thời hạn giải quyết", value: experience.processingTime, wide: true },
  ];
}

function service(input: {
  id: string;
  title: string;
  authority: string;
  audience: string;
  fee: string;
}): readonly MarriageService[] {
  return [{ ...input, level: "Hỗ trợ chuẩn bị hồ sơ" }];
}

export const temporaryResidenceExperience: ProcedureExperience = {
  slug: "dang-ky-tam-tru",
  title: "Đăng ký tạm trú",
  shortTitle: "Đăng ký tạm trú",
  code: "1.004194",
  decision: "Data package v2",
  level: "Cấp xã",
  procedureType: "Thủ tục cư trú",
  field: "Đăng ký, quản lý cư trú",
  audience: "Công dân Việt Nam",
  competentAuthority: "Công an cấp xã",
  performingAgency: "Công an cấp xã",
  nationalProcedureId: "1.004194",
  justiceProcedureId: "1.004194",
  onlineServiceCode: "1.004194",
  services: service({
    id: "temporary-residence-guidance",
    title: "Đăng ký tạm trú",
    authority: "Công an cấp xã",
    audience: "Công dân Việt Nam",
    fee: "Cá nhân/hộ gia đình: trực tuyến 7.000 đồng, trực tiếp 15.000 đồng; có trường hợp được miễn.",
  }),
  metadata: metadata({
    title: "Đăng ký tạm trú",
    code: "1.004194",
    field: "Đăng ký, quản lý cư trú",
    authority: "Công an cấp xã",
    audience: "Công dân Việt Nam",
    processingTime: "03 ngày làm việc",
  }),
  steps: [
    "Xác định hình thức đăng ký cá nhân/hộ gia đình và trường hợp người chưa thành niên.",
    "Hoàn thành CT01 và khai địa chỉ, thời hạn tạm trú.",
    "Kiểm tra thông tin chỗ ở hợp pháp; chỉ bổ sung giấy tờ khi hệ thống không khai thác được.",
    "Kiểm tra ý kiến cha mẹ/người giám hộ và sự đồng ý của chủ hộ/chủ sở hữu khi áp dụng.",
    "Kiểm tra lệ phí theo kênh nộp rồi chuyển sang kênh chính thức để nộp.",
  ],
  methods: [
    {
      method: "Trực tuyến",
      duration: "03 ngày làm việc",
      fee: "7.000 đồng/lần",
      description: "Mức tham chiếu cho đăng ký cá nhân hoặc hộ gia đình, trừ trường hợp được miễn.",
    },
    {
      method: "Trực tiếp",
      duration: "03 ngày làm việc",
      fee: "15.000 đồng/lần",
      description: "Nộp tại Công an cấp xã; kiểm tra lại mức phí tại thời điểm nộp.",
    },
  ],
  nationalDossier: [
    { name: "Tờ khai thay đổi thông tin cư trú – Mẫu CT01", quantity: "01 bản chính" },
    {
      name: "Thông tin hoặc giấy tờ chứng minh chỗ ở hợp pháp khi cơ sở dữ liệu không khai thác được",
      quantity: "Theo trường hợp",
    },
    {
      name: "Ý kiến đồng ý của cha, mẹ hoặc người giám hộ đối với người chưa thành niên",
      quantity: "Theo trường hợp",
    },
  ],
  conditions: [
    "Luồng tự kiểm tra sâu áp dụng cho đăng ký cá nhân hoặc hộ gia đình.",
    "Đăng ký theo danh sách hoặc tại đơn vị lực lượng vũ trang cần cán bộ kiểm tra chính thức.",
  ],
  legalBases: [
    "SRC-DVC-1004194 — Đăng ký tạm trú",
    "SRC-LAW-154-2024 — Nghị định 154/2024/NĐ-CP",
    "SRC-CIRC-53-2025 — Thông tư 53/2025/TT-BCA",
    "SRC-FEE-75-2022 — Thông tư 75/2022/TT-BTC",
  ],
  result: {
    label: "Cập nhật thông tin cư trú và thông báo kết quả",
    code: "1.004194",
  },
  justiceDossier: [
    { id: "ct01", name: "Tờ khai thay đổi thông tin cư trú – Mẫu CT01", required: true, eForm: true },
    {
      id: "legal-dwelling",
      name: "Giấy tờ chứng minh chỗ ở hợp pháp khi dữ liệu không khai thác được",
      required: false,
      eForm: false,
    },
    {
      id: "minor-consent",
      name: "Ý kiến đồng ý của cha, mẹ hoặc người giám hộ",
      required: false,
      eForm: false,
    },
  ],
  formKind: "temporary-residence",
  routes: createRoutes("dang-ky-tam-tru"),
};

export const birthCertificateCopyExperience: ProcedureExperience = {
  slug: "cap-ban-sao-giay-khai-sinh",
  title: "Cấp bản sao Trích lục hộ tịch (bản sao Giấy khai sinh)",
  shortTitle: "Cấp bản sao Giấy khai sinh",
  code: "2.000635",
  decision: "Data package v2",
  level: "Cấp xã",
  procedureType: "Thủ tục hộ tịch",
  field: "Hộ tịch",
  audience: "Cá nhân, người được ủy quyền hoặc tổ chức",
  competentAuthority: "Cơ quan quản lý Cơ sở dữ liệu hộ tịch điện tử",
  performingAgency: "Trung tâm Phục vụ hành chính công có thẩm quyền",
  nationalProcedureId: "2.000635",
  justiceProcedureId: "2.000635",
  onlineServiceCode: "2.000635",
  services: service({
    id: "birth-copy-guidance",
    title: "Cấp bản sao Giấy khai sinh",
    authority: "Cơ quan quản lý Cơ sở dữ liệu hộ tịch điện tử",
    audience: "Cá nhân, người được ủy quyền hoặc tổ chức",
    fee: "8.000 đồng/bản tham chiếu; kiểm tra lại tại bước nộp.",
  }),
  metadata: metadata({
    title: "Cấp bản sao Trích lục hộ tịch (bản sao Giấy khai sinh)",
    code: "2.000635",
    field: "Hộ tịch",
    authority: "Cơ quan quản lý Cơ sở dữ liệu hộ tịch điện tử",
    audience: "Cá nhân, người được ủy quyền hoặc tổ chức",
    processingTime: "Theo phiếu hẹn",
  }),
  steps: [
    "Xác nhận đây là yêu cầu cấp bản sao Giấy khai sinh đã đăng ký trước đó.",
    "Chọn kênh nộp và kê khai người yêu cầu, người có sự kiện khai sinh.",
    "Chuẩn bị giấy tờ tùy thân và văn bản ủy quyền nếu thực hiện thay người khác.",
    "Kiểm tra thông tin tra cứu và yêu cầu riêng theo kênh nộp.",
    "Chuyển sang kênh chính thức để nộp hồ sơ.",
  ],
  methods: [
    { method: "Trực tuyến", duration: "Theo phiếu hẹn", fee: "8.000 đồng/bản", description: "Phí tham chiếu; kiểm tra lại tại bước nộp." },
    { method: "Trực tiếp", duration: "Theo phiếu hẹn", fee: "8.000 đồng/bản", description: "Xuất trình giấy tờ tùy thân còn giá trị." },
    { method: "Bưu chính", duration: "Theo phiếu hẹn", fee: "8.000 đồng/bản", description: "Chuẩn bị bản sao có chứng thực của giấy tờ phải xuất trình." },
  ],
  nationalDossier: [
    { name: "Mẫu điện tử tương tác hoặc Tờ khai đề nghị cấp bản sao Trích lục hộ tịch", quantity: "01 bản" },
    { name: "Thông tin giấy tờ tùy thân của người yêu cầu", quantity: "Theo trường hợp" },
    { name: "Thông tin sự kiện khai sinh đủ để tra cứu", quantity: "Theo trường hợp" },
    { name: "Văn bản ủy quyền", quantity: "Khi được ủy quyền" },
  ],
  conditions: ["Chỉ hỗ trợ bản sao Giấy khai sinh, không phải đăng ký khai sinh mới hoặc cải chính hộ tịch."],
  legalBases: ["SRC-DVC-2000635 — Cấp bản sao Trích lục hộ tịch, bản sao Giấy khai sinh"],
  result: { label: "Bản sao Giấy khai sinh", code: "2.000635" },
  justiceDossier: [
    { id: "birth-form", name: "Tờ khai đề nghị cấp bản sao Trích lục hộ tịch", required: true, eForm: true },
    { id: "identity", name: "Thông tin giấy tờ tùy thân", required: true, eForm: false },
    { id: "authorization", name: "Văn bản ủy quyền khi áp dụng", required: false, eForm: false },
  ],
  formKind: "guided",
  routes: createRoutes("cap-ban-sao-giay-khai-sinh"),
};

export const housingConfirmationExperience: ProcedureExperience = {
  slug: "xac-nhan-dieu-kien-nha-o",
  title: "Xác nhận điều kiện diện tích bình quân nhà ở",
  shortTitle: "Xác nhận điều kiện nhà ở",
  code: "1.013314",
  decision: "Data package v2",
  level: "Cấp xã",
  procedureType: "Thủ tục cư trú",
  field: "Đăng ký, quản lý cư trú",
  audience: "Công dân Việt Nam",
  competentAuthority: "Ủy ban nhân dân cấp xã nơi cư trú",
  performingAgency: "Ủy ban nhân dân cấp xã",
  nationalProcedureId: "1.013314",
  justiceProcedureId: "1.013314",
  onlineServiceCode: "1.013314",
  services: service({
    id: "housing-confirmation-guidance",
    title: "Xác nhận điều kiện diện tích bình quân nhà ở",
    authority: "Ủy ban nhân dân cấp xã nơi cư trú",
    audience: "Công dân Việt Nam",
    fee: "Không thu phí.",
  }),
  metadata: metadata({
    title: "Xác nhận điều kiện diện tích bình quân nhà ở",
    code: "1.013314",
    field: "Đăng ký, quản lý cư trú",
    authority: "Ủy ban nhân dân cấp xã nơi cư trú",
    audience: "Công dân Việt Nam",
    processingTime: "02 ngày làm việc",
  }),
  steps: [
    "Xác nhận nhu cầu là Mẫu số 02, không phải thủ tục đăng ký thường trú.",
    "Kê khai người đề nghị, địa chỉ chỗ ở và số liệu diện tích.",
    "Kiểm tra phép tính diện tích bình quân theo khu vực Hà Nội.",
    "Ghi rõ các nội dung phải do UBND cấp xã xác nhận.",
    "Nộp Mẫu số 02 tới UBND cấp xã hoặc cùng hồ sơ cư trú.",
  ],
  methods: [
    { method: "Trực tuyến", duration: "02 ngày làm việc", fee: "Không thu phí", description: "Nộp biểu mẫu điện tử tương tác." },
    { method: "Trực tiếp", duration: "02 ngày làm việc", fee: "Không thu phí", description: "Nộp Mẫu số 02 tại UBND cấp xã." },
    { method: "Bưu chính", duration: "02 ngày làm việc", fee: "Không thu phí", description: "Thời gian vận chuyển không nằm trong thời hạn xử lý." },
  ],
  nationalDossier: [{ name: "Mẫu số 02 – Tờ khai xác nhận tình trạng chỗ ở hợp pháp, diện tích nhà ở tối thiểu", quantity: "01 bản chính" }],
  conditions: ["VNeGuide chỉ kiểm tra tờ khai và phép tính; UBND cấp xã xác nhận tình trạng chỗ ở."],
  legalBases: [
    "SRC-DVC-1013314 — Thông tin thủ tục trên Cổng Dịch vụ công Quốc gia",
    "SRC-FORM-M02 — Mẫu số 02",
    "SRC-HN-AREA-2023 — Nghị quyết 10/2023/NQ-HĐND Hà Nội",
  ],
  result: { label: "Xác nhận tình trạng chỗ ở và diện tích nhà ở", code: "1.013314" },
  justiceDossier: [{ id: "m02", name: "Mẫu số 02", required: true, eForm: true }],
  formKind: "guided",
  routes: createRoutes("xac-nhan-dieu-kien-nha-o"),
};

export const procedureExperiences = [
  temporaryResidenceExperience,
  birthCertificateCopyExperience,
  housingConfirmationExperience,
] as const satisfies readonly ProcedureExperience[];

// Compatibility aliases for the existing shared route components. They are not
// separate supported procedures.
export const standardMarriageExperience = temporaryResidenceExperience;
export const additionalProcedureExperiences = procedureExperiences;

export function getProcedureExperience(slug: string): ProcedureExperience | undefined {
  return procedureExperiences.find((experience) => experience.slug === slug);
}

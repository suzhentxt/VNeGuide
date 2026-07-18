import {
  dossierItems,
  implementationMethods,
  legalBases as marriageLegalBases,
  marriageConditions,
  marriageRoutes,
  marriageServices,
  procedureMetadata,
  procedureSteps,
  type DossierItem,
  type ImplementationMethod,
  type MarriageService,
  type MetadataField,
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
  result: {
    label: string;
    code: string;
  };
  justiceDossier: readonly OnlineDossierRow[];
  formKind: "marriage" | "civil-record";
  routes: ProcedureRoutes;
}

const NO_INFORMATION = "Không có thông tin";

const localFeeDescription =
  "Mức lệ phí cụ thể do Hội đồng nhân dân tỉnh, thành phố trực thuộc Trung ương quyết định. Miễn lệ phí cho người thuộc gia đình có công với cách mạng, người thuộc hộ nghèo và người khuyết tật; phí cấp bản sao thực hiện theo quy định hiện hành.";

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

function createMethods(duration: "01 ngày" | "05 ngày"): readonly ImplementationMethod[] {
  return ["Trực tuyến", "Dịch vụ bưu chính", "Trực tiếp"].map((method) => ({
    method,
    duration,
    fee: "Miễn phí",
    description: localFeeDescription,
  }));
}

function createMetadata({
  audience,
  code,
  procedureType,
  title,
}: {
  audience: string;
  code: string;
  procedureType: string;
  title: string;
}): readonly MetadataField[] {
  return [
    { label: "Tên thủ tục", value: title, wide: true },
    { label: "Mã thủ tục", value: code },
    { label: "Số quyết định", value: "163/QĐ-BTP" },
    { label: "Cấp thực hiện", value: "Cấp xã" },
    { label: "Loại thủ tục", value: procedureType },
    { label: "Lĩnh vực", value: "Hộ tịch" },
    { label: "Đối tượng thực hiện", value: audience },
    {
      label: "Cơ quan có thẩm quyền",
      value: NO_INFORMATION,
      wide: true,
    },
    { label: "Địa chỉ tiếp nhận hồ sơ", value: NO_INFORMATION, wide: true },
    { label: "Cơ quan được ủy quyền", value: NO_INFORMATION },
    { label: "Cơ quan phối hợp", value: NO_INFORMATION },
    {
      label: "Thủ tục hành chính liên quan",
      value: NO_INFORMATION,
      wide: true,
    },
  ];
}

const standardMarriageJusticeDossier: readonly OnlineDossierRow[] = [
  {
    id: "electronic-form",
    name: "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn (kê khai theo hướng dẫn trên Cổng dịch vụ công)",
    required: true,
    eForm: true,
  },
  {
    id: "identity-documents",
    name: "Giấy tờ tùy thân còn giá trị sử dụng của hai bên yêu cầu đăng ký kết hôn",
    required: true,
    eForm: false,
  },
  {
    id: "residence-documents",
    name: "Giấy tờ chứng minh thông tin cư trú khi cơ quan đăng ký hộ tịch chưa khai thác được dữ liệu cư trú",
    required: false,
    eForm: false,
  },
];

export const standardMarriageExperience: ProcedureExperience = {
  slug: "dang-ky-ket-hon",
  title: "Thủ tục đăng ký kết hôn",
  shortTitle: "Đăng ký kết hôn",
  code: "1.000894",
  decision: "163/QĐ-BTP",
  level: "Cấp xã",
  procedureType: "TTHC được luật giao quy định chi tiết",
  field: "Hộ tịch",
  audience: "Công dân Việt Nam",
  competentAuthority: "UBND phường Cầu Giấy, Thành phố Hà Nội",
  performingAgency: "Ủy ban Nhân dân xã, phường, thị trấn",
  nationalProcedureId: "019d2bfd-3fac-7489-b53b-a15eb239a6fe",
  justiceProcedureId: "144405",
  onlineServiceCode: "1.000894.01",
  services: marriageServices,
  metadata: procedureMetadata,
  steps: procedureSteps,
  methods: implementationMethods,
  nationalDossier: dossierItems,
  conditions: marriageConditions,
  legalBases: marriageLegalBases,
  result: {
    label: "Giấy chứng nhận kết hôn",
    code: "KQ.G15.000032",
  },
  justiceDossier: standardMarriageJusticeDossier,
  formKind: "marriage",
  routes: {
    detail: marriageRoutes.detail,
    services: `${marriageRoutes.detail}/dich-vu-cong`,
    apply: marriageRoutes.apply,
    submission: marriageRoutes.submission,
    eForm: marriageRoutes.eForm,
  },
};

const foreignMarriageTitle =
  "Thủ tục đăng ký kết hôn có yếu tố nước ngoài";

const foreignMarriageServices: readonly MarriageService[] = [
  {
    id: "foreign-marriage-ubnd-phuong-cau-giay",
    title: foreignMarriageTitle,
    level: "DVCTT toàn trình",
    authority: "UBND phường Cầu Giấy",
    audience: "Công dân Việt Nam, Người Việt Nam định cư ở nước ngoài",
    fee: localFeeDescription,
  },
  {
    id: "foreign-marriage-phong-kinh-te-ha-tang-do-thi-cau-giay",
    title: foreignMarriageTitle,
    level: "DVCTT toàn trình",
    authority: "Phòng Kinh tế, Hạ tầng và Đô thị phường Cầu Giấy",
    audience: "Công dân Việt Nam, Người Việt Nam định cư ở nước ngoài",
    fee: localFeeDescription,
  },
];

const foreignMarriageSteps = [
  "Người yêu cầu nộp hồ sơ trực tiếp tại Trung tâm Phục vụ hành chính công có thẩm quyền hoặc nộp trực tuyến trên Cổng Dịch vụ công quốc gia hay Ứng dụng định danh quốc gia; kê khai mẫu hộ tịch điện tử, đính kèm tài liệu và nộp phí, lệ phí theo quy định.",
  "Cán bộ tiếp nhận kiểm tra tính chính xác, đầy đủ, thống nhất và hợp lệ của hồ sơ; hồ sơ hợp lệ được tiếp nhận, hẹn trả kết quả và chuyển công chức tư pháp - hộ tịch, hồ sơ thiếu được hướng dẫn bổ sung, hồ sơ không thể hoàn thiện bị từ chối.",
  "Công chức tư pháp - hộ tịch thẩm tra hồ sơ, kiểm tra nhân thân, sự tự nguyện và mục đích kết hôn; phối hợp xác minh khi có khiếu nại, tố cáo hoặc nội dung cần làm rõ và lập phiếu xin lỗi, hẹn lại nếu không thể trả đúng hạn.",
  "Nếu hồ sơ đầy đủ, hợp lệ và hai bên đủ điều kiện kết hôn, công chức tư pháp - hộ tịch ghi Sổ đăng ký kết hôn, cập nhật Phần mềm hộ tịch; với hồ sơ trực tuyến, biểu mẫu Giấy chứng nhận kết hôn điện tử được gửi để người yêu cầu xác nhận tối đa một ngày.",
  "Công chức tư pháp - hộ tịch in Giấy chứng nhận kết hôn, trình lãnh đạo Ủy ban nhân dân cấp xã ký và chuyển tới Trung tâm Phục vụ hành chính công để trả kết quả.",
  "Hai bên nam, nữ phải có mặt, xuất trình giấy tờ tùy thân, kiểm tra thông tin, xác nhận sự tự nguyện và ký vào Sổ, Giấy chứng nhận kết hôn; thời gian trao giấy có thể được gia hạn theo đề nghị bằng văn bản nhưng không quá 60 ngày.",
] as const;

const foreignMarriageNationalDossier: readonly DossierItem[] = [
  {
    name: "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn khi nộp hồ sơ trực tuyến hoặc Tờ khai đăng ký kết hôn theo mẫu khi nộp trực tiếp",
    quantity: "01 bản chính",
  },
  {
    name: "Bản sao hộ chiếu hoặc giấy tờ có giá trị thay thế hộ chiếu của người nước ngoài, công dân Việt Nam định cư ở nước ngoài",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ chứng minh tình trạng hôn nhân của người nước ngoài do cơ quan có thẩm quyền nước ngoài cấp, còn giá trị sử dụng",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy xác nhận của tổ chức y tế có thẩm quyền xác nhận các bên không mắc bệnh làm mất khả năng nhận thức, làm chủ hành vi",
    quantity: "01 bản chính",
  },
  {
    name: "Văn bản của cơ quan, đơn vị quản lý xác nhận việc kết hôn với người nước ngoài không trái quy định của ngành đối với công chức, viên chức hoặc người phục vụ trong lực lượng vũ trang",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy xác nhận tình trạng hôn nhân do Cơ quan đại diện ngoại giao hoặc Cơ quan đại diện lãnh sự Việt Nam ở nước ngoài cấp đối với người đang công tác, học tập, lao động có thời hạn ở nước ngoài",
    quantity: "01 bản chính",
  },
  {
    name: "Trích lục ghi chú ly hôn đối với công dân Việt Nam đã ly hôn hoặc hủy việc kết hôn tại cơ quan có thẩm quyền nước ngoài",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ tùy thân còn giá trị sử dụng để chứng minh nhân thân khi thực hiện thủ tục trực tiếp",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ chứng minh thông tin cư trú khi cơ quan đăng ký hộ tịch không khai thác được dữ liệu cư trú",
    quantity: "01 bản chính",
  },
];

const foreignMarriageJusticeDossier: readonly OnlineDossierRow[] = [
  {
    id: "foreign-marriage-electronic-form",
    name: "Mẫu hộ tịch điện tử tương tác đăng ký kết hôn (do người yêu cầu cung cấp thông tin theo hướng dẫn trên Cổng dịch vụ công)",
    required: true,
    eForm: true,
  },
  {
    id: "foreign-marriage-medical-certificate",
    name: "Giấy xác nhận của tổ chức y tế có thẩm quyền xác nhận các bên kết hôn không mắc bệnh làm mất khả năng nhận thức, làm chủ hành vi",
    required: false,
    eForm: false,
  },
  {
    id: "foreign-marriage-status-certificate",
    name: "Giấy tờ chứng minh tình trạng hôn nhân của người nước ngoài do cơ quan có thẩm quyền cấp, còn giá trị sử dụng",
    required: false,
    eForm: false,
  },
  {
    id: "foreign-marriage-passport",
    name: "Bản sao hộ chiếu hoặc giấy tờ có giá trị thay thế hộ chiếu của người nước ngoài, công dân Việt Nam định cư ở nước ngoài",
    required: false,
    eForm: false,
  },
  {
    id: "foreign-marriage-employer-confirmation",
    name: "Văn bản của cơ quan, đơn vị quản lý xác nhận việc kết hôn với người nước ngoài không trái quy định của ngành đối với công chức, viên chức hoặc lực lượng vũ trang",
    required: false,
    eForm: false,
  },
  {
    id: "foreign-marriage-consular-status-certificate",
    name: "Giấy xác nhận tình trạng hôn nhân do Cơ quan đại diện ngoại giao hoặc Cơ quan đại diện lãnh sự Việt Nam ở nước ngoài cấp",
    required: false,
    eForm: false,
  },
];

export const foreignMarriageExperience: ProcedureExperience = {
  slug: "dang-ky-ket-hon-co-yeu-to-nuoc-ngoai",
  title: foreignMarriageTitle,
  shortTitle: "Đăng ký kết hôn có yếu tố nước ngoài",
  code: "2.000806",
  decision: "163/QĐ-BTP",
  level: "Cấp xã",
  procedureType: "TTHC không được luật giao cho địa phương quy định",
  field: "Hộ tịch",
  audience: "Công dân Việt Nam, Người Việt Nam định cư ở nước ngoài",
  competentAuthority: "UBND phường Cầu Giấy, Thành phố Hà Nội",
  performingAgency: NO_INFORMATION,
  nationalProcedureId: "019d2bfd-8e13-728a-a0cd-635811d8432e",
  justiceProcedureId: "144406",
  onlineServiceCode: "2.000806.01",
  services: foreignMarriageServices,
  metadata: createMetadata({
    audience: "Công dân Việt Nam, Người Việt Nam định cư ở nước ngoài",
    code: "2.000806",
    procedureType: "TTHC không được luật giao cho địa phương quy định",
    title: foreignMarriageTitle,
  }),
  steps: foreignMarriageSteps,
  methods: createMethods("05 ngày"),
  nationalDossier: foreignMarriageNationalDossier,
  conditions: [NO_INFORMATION],
  legalBases: marriageLegalBases,
  result: {
    label: "Giấy chứng nhận kết hôn",
    code: "KQ.G15.000032",
  },
  justiceDossier: foreignMarriageJusticeDossier,
  formKind: "marriage",
  routes: createRoutes("dang-ky-ket-hon-co-yeu-to-nuoc-ngoai"),
};

const domesticCivilRecordTitle =
  "Thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc";

const foreignCivilRecordTitle =
  "Thủ tục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc có yếu tố nước ngoài";

const civilRecordResult = {
  label:
    "Trích lục thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
  code: "KQ.G15.000037",
} as const;

const domesticCivilRecordServices: readonly MarriageService[] = [
  {
    id: "domestic-civil-record-ubnd-phuong-cau-giay",
    title: domesticCivilRecordTitle,
    level: "DVCTT toàn trình",
    authority: "UBND phường Cầu Giấy",
    audience: "Công dân Việt Nam",
    fee: localFeeDescription,
  },
];

const foreignCivilRecordServices: readonly MarriageService[] = [
  {
    id: "foreign-civil-record-ubnd-phuong-cau-giay",
    title: foreignCivilRecordTitle,
    level: "DVCTT toàn trình",
    authority: "UBND phường Cầu Giấy",
    audience: "Công dân Việt Nam",
    fee: localFeeDescription,
  },
  {
    id: "foreign-civil-record-phong-kinh-te-ha-tang-do-thi-cau-giay",
    title: foreignCivilRecordTitle,
    level: "DVCTT toàn trình",
    authority: "Phòng Kinh tế, Hạ tầng và Đô thị phường Cầu Giấy",
    audience: "Công dân Việt Nam",
    fee: localFeeDescription,
  },
];

const domesticCivilRecordSteps = [
  "Người yêu cầu nộp hồ sơ trực tiếp tại Trung tâm Phục vụ hành chính công có thẩm quyền hoặc nộp trực tuyến qua Cổng Dịch vụ công quốc gia hay Ứng dụng định danh; kê khai mẫu tương tác, đính kèm tài liệu và nộp phí, lệ phí.",
  "Cán bộ tiếp nhận kiểm tra tính chính xác, đầy đủ và hợp lệ; hồ sơ hợp lệ được tiếp nhận, hẹn trả và chuyển công chức tư pháp - hộ tịch, hồ sơ thiếu được hướng dẫn bổ sung, hồ sơ không thể hoàn thiện bị từ chối.",
  "Công chức tư pháp - hộ tịch thẩm tra; yêu cầu bổ sung hoặc từ chối nếu không đủ điều kiện, lập phiếu xin lỗi và hẹn lại khi cần kiểm tra, xác minh.",
  "Nếu có cơ sở và hồ sơ hợp lệ, công chức tư pháp - hộ tịch ghi Sổ, cập nhật Phần mềm hộ tịch; với hồ sơ trực tuyến, biểu mẫu Trích lục điện tử được gửi để người yêu cầu kiểm tra và xác nhận tối đa một ngày.",
  "Sau khi người yêu cầu xác nhận hoặc hết thời hạn một ngày mà không phản hồi, công chức tư pháp - hộ tịch hoàn tất việc ghi nội dung và cập nhật dữ liệu.",
  "Công chức tư pháp - hộ tịch in Trích lục tương ứng, trình lãnh đạo Ủy ban nhân dân cấp xã ký và chuyển Trung tâm Phục vụ hành chính công trả kết quả.",
] as const;

const foreignCivilRecordSteps = [
  domesticCivilRecordSteps[0],
  domesticCivilRecordSteps[1],
  domesticCivilRecordSteps[2],
  domesticCivilRecordSteps[3],
  "Công chức tư pháp - hộ tịch in Trích lục, trình lãnh đạo Ủy ban nhân dân cấp xã ký và chuyển trả kết quả; nếu nội dung liên quan Giấy khai sinh hoặc Giấy chứng nhận kết hôn thì ghi và đóng dấu nội dung thay đổi, bổ sung.",
  "Nếu thủ tục không được thực hiện tại nơi đã đăng ký hộ tịch trước đây, Ủy ban nhân dân cấp xã gửi trích lục về nơi đăng ký cũ; nếu nơi cũ là Cơ quan đại diện thì gửi Bộ Ngoại giao để chuyển Cơ quan đại diện ghi Sổ.",
] as const;

const domesticCivilRecordNationalDossier: readonly DossierItem[] = [
  {
    name: "Mẫu hộ tịch điện tử tương tác thực hiện đăng ký thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc khi nộp trực tuyến",
    quantity: "01 bản chính, 01 bản sao",
  },
  {
    name: "Tờ khai đăng ký thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc khi nộp trực tiếp",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ làm căn cứ cho việc thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
    quantity: "01 bản chính",
  },
  {
    name: "Văn bản ủy quyền theo quy định trong trường hợp ủy quyền thực hiện thủ tục",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ tùy thân còn giá trị sử dụng để chứng minh nhân thân khi thực hiện thủ tục trực tiếp",
    quantity: "01 bản chính",
  },
  {
    name: "Giấy tờ chứng minh thông tin cư trú khi cơ quan đăng ký hộ tịch không khai thác được dữ liệu cư trú",
    quantity: "01 bản chính",
  },
];

const foreignCivilRecordNationalDossier: readonly DossierItem[] = [
  {
    name: "Mẫu hộ tịch điện tử tương tác thực hiện đăng ký thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc khi nộp trực tuyến",
    quantity: "01 bản chính",
  },
  {
    name: "Tờ khai đăng ký thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc khi nộp trực tiếp",
    quantity: "01 bản chính",
  },
  ...domesticCivilRecordNationalDossier.slice(2),
];

const civilRecordJusticeDossier: readonly OnlineDossierRow[] = [
  {
    id: "civil-record-electronic-form",
    name: "Mẫu hộ tịch điện tử tương tác thực hiện đăng ký thay đổi, cải chính, bổ sung thông tin hộ tịch, xác định lại dân tộc",
    required: true,
    eForm: true,
  },
  {
    id: "civil-record-supporting-documents",
    name: "Giấy tờ làm căn cứ thay đổi, cải chính, bổ sung thông tin hộ tịch",
    required: false,
    eForm: false,
  },
  {
    id: "civil-record-authorization",
    name: "Văn bản ủy quyền theo quy định; trường hợp người được ủy quyền là ông, bà, cha, mẹ, con, vợ, chồng, anh, chị hoặc em ruột thì văn bản ủy quyền không phải chứng thực",
    required: false,
    eForm: false,
  },
];

const domesticCivilRecordLegalBases = [
  "03/2023/TT-BTP",
  "87/2020/NĐ-CP",
  "01/2022/TT-BTP",
  "04/2020/TT-BTP",
  "07/2025/NĐ-CP",
  "120/2025/NĐ-CP",
  "66.7/2025/NQ-CP",
  "60/2014/QH13",
  "85/2019/TT-BTC",
  "104/2022/NĐ-CP",
  "123/2015/NĐ-CP",
  "91/2015/QH13",
  "08/2025/TT-BTP",
  "18/2026/NĐ-CP",
  "04/2024/TT-BTP",
  "106/2021/TT-BTC",
] as const;

const foreignCivilRecordLegalBases = [
  "04/2024/TT-BTP",
  "03/2023/TT-BTP",
  "106/2021/TT-BTC",
  "04/2020/TT-BTP",
  "07/2025/NĐ-CP",
  "120/2025/NĐ-CP",
  "66.7/2025/NQ-CP",
  "60/2014/QH13",
  "01/2022/TT-BTP",
  "85/2019/TT-BTC",
  "104/2022/NĐ-CP",
  "123/2015/NĐ-CP",
  "08/2025/TT-BTP",
  "18/2026/NĐ-CP",
  "87/2020/NĐ-CP",
] as const;

export const domesticCivilRecordExperience: ProcedureExperience = {
  slug: "thay-doi-cai-chinh-ho-tich",
  title: domesticCivilRecordTitle,
  shortTitle: "Thay đổi, cải chính thông tin hộ tịch",
  code: "1.004859",
  decision: "163/QĐ-BTP",
  level: "Cấp xã",
  procedureType: "TTHC được luật giao quy định chi tiết",
  field: "Hộ tịch",
  audience: "Công dân Việt Nam",
  competentAuthority: "UBND phường Cầu Giấy, Thành phố Hà Nội",
  performingAgency: NO_INFORMATION,
  nationalProcedureId: "019d2bfd-671e-714b-8fd6-8230c82f7867",
  justiceProcedureId: "144381",
  onlineServiceCode: "1.004859.01",
  services: domesticCivilRecordServices,
  metadata: createMetadata({
    audience: "Công dân Việt Nam",
    code: "1.004859",
    procedureType: "TTHC được luật giao quy định chi tiết",
    title: domesticCivilRecordTitle,
  }),
  steps: domesticCivilRecordSteps,
  methods: createMethods("01 ngày"),
  nationalDossier: domesticCivilRecordNationalDossier,
  conditions: [NO_INFORMATION],
  legalBases: domesticCivilRecordLegalBases,
  result: civilRecordResult,
  justiceDossier: civilRecordJusticeDossier,
  formKind: "civil-record",
  routes: createRoutes("thay-doi-cai-chinh-ho-tich"),
};

export const foreignCivilRecordExperience: ProcedureExperience = {
  slug: "thay-doi-cai-chinh-ho-tich-co-yeu-to-nuoc-ngoai",
  title: foreignCivilRecordTitle,
  shortTitle: "Thay đổi, cải chính hộ tịch có yếu tố nước ngoài",
  code: "2.000748",
  decision: "163/QĐ-BTP",
  level: "Cấp xã",
  procedureType: "TTHC không được luật giao cho địa phương quy định",
  field: "Hộ tịch",
  audience: "Công dân Việt Nam",
  competentAuthority: "UBND phường Cầu Giấy, Thành phố Hà Nội",
  performingAgency: NO_INFORMATION,
  nationalProcedureId: "019d2bfd-8e02-7590-b74b-fb572a57eda2",
  justiceProcedureId: "144382",
  onlineServiceCode: "2.000748.01",
  services: foreignCivilRecordServices,
  metadata: createMetadata({
    audience: "Công dân Việt Nam",
    code: "2.000748",
    procedureType: "TTHC không được luật giao cho địa phương quy định",
    title: foreignCivilRecordTitle,
  }),
  steps: foreignCivilRecordSteps,
  methods: createMethods("01 ngày"),
  nationalDossier: foreignCivilRecordNationalDossier,
  conditions: [NO_INFORMATION],
  legalBases: foreignCivilRecordLegalBases,
  result: civilRecordResult,
  justiceDossier: civilRecordJusticeDossier,
  formKind: "civil-record",
  routes: createRoutes("thay-doi-cai-chinh-ho-tich-co-yeu-to-nuoc-ngoai"),
};

export const additionalProcedureExperiences = [
  foreignMarriageExperience,
  domesticCivilRecordExperience,
  foreignCivilRecordExperience,
] as const satisfies readonly ProcedureExperience[];

export const procedureExperiences = [
  standardMarriageExperience,
  ...additionalProcedureExperiences,
] as const satisfies readonly ProcedureExperience[];

export function getProcedureExperience(
  slug: string,
): ProcedureExperience | undefined {
  return procedureExperiences.find((experience) => experience.slug === slug);
}

export const marriageRoutes = {
  category: "/hon-nhan-va-gia-dinh",
  services: "/hon-nhan-va-gia-dinh/dich-vu-cong",
  detail: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru",
  apply: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru/truc-tuyen",
  submission: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru/nop-ho-so",
  eForm: "/hon-nhan-va-gia-dinh/dang-ky-tam-tru/to-khai",
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
    title: "Ba thủ tục VNeGuide hỗ trợ",
    procedures: [
      "Đăng ký tạm trú",
      "Cấp bản sao Trích lục hộ tịch (bản sao Giấy khai sinh)",
      "Xác nhận điều kiện diện tích bình quân nhà ở",
    ],
  },
] as const;

export const popularProcedures = [
  "Đăng ký tạm trú",
  "Cấp bản sao Giấy khai sinh",
  "Xác nhận điều kiện diện tích bình quân nhà ở",
] as const;

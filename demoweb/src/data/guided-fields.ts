export interface GuidedFieldDefinition {
  procedure_code?: string;
  field_id: string;
  label: string;
  type: "string" | "date" | "integer" | "number" | "boolean" | "enum";
  requirement: string;
  values?: string[];
  minimum?: number;
  pattern?: string;
  hint?: string;
}

const enumLabels: Record<string, string> = {
  self: "Tự mình yêu cầu",
  authorized_person: "Người được ủy quyền",
  organization: "Cơ quan hoặc tổ chức",
  citizen_id: "Căn cước công dân",
  identity_card: "Chứng minh nhân dân",
  passport: "Hộ chiếu",
  identity_certificate: "Giấy chứng nhận căn cước",
  electronic_identity: "Định danh điện tử",
  online: "Nộp trực tuyến",
  direct: "Nộp trực tiếp",
  postal: "Nộp qua bưu chính",
  grandparent: "Ông hoặc bà",
  parent: "Cha hoặc mẹ",
  child: "Con",
  spouse: "Vợ hoặc chồng",
  sibling: "Anh, chị hoặc em ruột",
  other: "Khác",
  inner_city: "Khu vực nội thành Hà Nội",
  suburban: "Khu vực ngoại thành Hà Nội",
  individual_or_household: "Cá nhân hoặc hộ gia đình",
  by_list: "Đăng ký theo danh sách",
  armed_forces: "Đơn vị lực lượng vũ trang",
  owned: "Nhà ở thuộc sở hữu",
  rented: "Nhà thuê",
  borrowed: "Nhà mượn",
  accommodated: "Ở nhờ",
  join_family_household: "Về ở cùng hộ gia đình",
};

export function getEnumLabel(value: string) {
  return enumLabels[value] ?? value.replaceAll("_", " ");
}

export function isBlockingRequirement(requirement: string) {
  return requirement === "required" || requirement.startsWith("required_for_") || requirement === "required_declaration";
}

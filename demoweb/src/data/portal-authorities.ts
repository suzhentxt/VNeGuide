export interface PortalOption {
  id: string;
  label: string;
}

export const MAX_PORTAL_OPTIONS = 500;

export function parsePortalOptionsPayload(value: unknown): PortalOption[] | null {
  if (typeof value !== "object" || value === null || !("options" in value)) {
    return null;
  }

  const rawOptions = (value as { options?: unknown }).options;
  if (!Array.isArray(rawOptions) || rawOptions.length > MAX_PORTAL_OPTIONS) {
    return null;
  }

  const seenIds = new Set<string>();
  const options: PortalOption[] = [];

  for (const option of rawOptions) {
    if (
      typeof option !== "object" ||
      option === null ||
      !("id" in option) ||
      !("label" in option)
    ) {
      return null;
    }

    const id = (option as { id?: unknown }).id;
    const label = (option as { label?: unknown }).label;
    if (
      typeof id !== "string" ||
      id.length === 0 ||
      id.length > 64 ||
      !/^\d+$/.test(id) ||
      typeof label !== "string" ||
      label.length === 0 ||
      label.length > 200 ||
      label.trim() !== label
    ) {
      return null;
    }

    if (!seenIds.has(id)) {
      seenIds.add(id);
      options.push({ id, label });
    }
  }

  return options;
}

// Snapshot of the public portal's top-level authority IDs on 2026-07-17.
// Dependent Phường/Xã and Sở options stay live through /api/portal-options.
export const provinceOptions = [
  { id: "13465", label: "Thành phố Cần Thơ" },
  { id: "13453", label: "Thành phố Đà Nẵng" },
  { id: "13459", label: "Thành phố Đồng Nai" },
  { id: "13433", label: "Thành phố Hà Nội" },
  { id: "13445", label: "Thành phố Hải Phòng" },
  { id: "13460", label: "Thành phố Hồ Chí Minh" },
  { id: "13452", label: "Thành phố Huế" },
  { id: "13464", label: "Tỉnh An Giang" },
  { id: "13443", label: "Tỉnh Bắc Ninh" },
  { id: "13466", label: "Tỉnh Cà Mau" },
  { id: "13434", label: "Tỉnh Cao Bằng" },
  { id: "13457", label: "Tỉnh Đắk Lắk" },
  { id: "13436", label: "Tỉnh Điện Biên" },
  { id: "13462", label: "Tỉnh Đồng Tháp" },
  { id: "13455", label: "Tỉnh Gia Lai" },
  { id: "13450", label: "Tỉnh Hà Tĩnh" },
  { id: "13446", label: "Tỉnh Hưng Yên" },
  { id: "13456", label: "Tỉnh Khánh Hòa" },
  { id: "13437", label: "Tỉnh Lai Châu" },
  { id: "13441", label: "Tỉnh Lạng Sơn" },
  { id: "13439", label: "Tỉnh Lào Cai" },
  { id: "13458", label: "Tỉnh Lâm Đồng" },
  { id: "13449", label: "Tỉnh Nghệ An" },
  { id: "13447", label: "Tỉnh Ninh Bình" },
  { id: "13444", label: "Tỉnh Phú Thọ" },
  { id: "13454", label: "Tỉnh Quảng Ngãi" },
  { id: "13442", label: "Tỉnh Quảng Ninh" },
  { id: "13451", label: "Tỉnh Quảng Trị" },
  { id: "13438", label: "Tỉnh Sơn La" },
  { id: "13461", label: "Tỉnh Tây Ninh" },
  { id: "13440", label: "Tỉnh Thái Nguyên" },
  { id: "13448", label: "Tỉnh Thanh Hóa" },
  { id: "13435", label: "Tỉnh Tuyên Quang" },
  { id: "13463", label: "Tỉnh Vĩnh Long" },
] as const satisfies readonly PortalOption[];

export const ministryOptions = [
  { id: "484302", label: "Ban Tổ chức Trung ương" },
  { id: "6369", label: "Bộ Công an" },
  { id: "94", label: "Bộ Công thương" },
  { id: "5096", label: "Bộ Dân tộc và Tôn giáo" },
  { id: "2", label: "Bộ Giáo dục và Đào tạo" },
  { id: "734", label: "Bộ Khoa học  và  Công nghệ" },
  { id: "857", label: "Bộ Ngoại giao" },
  { id: "924", label: "Bộ Nội vụ" },
  { id: "1053", label: "Bộ Nông nghiệp và Môi trường" },
  { id: "6407", label: "Bộ Quốc phòng" },
  { id: "1301", label: "Bộ Tài chính" },
  { id: "4019", label: "Bộ Tư pháp" },
  { id: "5119", label: "Bộ Văn hóa, Thể thao và Du lịch" },
  { id: "4851", label: "Bộ Xây dựng" },
  { id: "4881", label: "Bộ Y tế" },
  { id: "80463832", label: "Đảng" },
  { id: "363963", label: "Ngân hàng Chính sách xã hội" },
  { id: "4983", label: "Ngân hàng Nhà nước Việt Nam" },
  { id: "363973", label: "Ngân hàng phát triển Việt Nam" },
  { id: "364400", label: "Tập đoàn Điện lực Việt Nam" },
  { id: "6468", label: "Thanh tra Chính phủ" },
  { id: "431093", label: "Tòa án nhân dân" },
  { id: "456442", label: "Văn phòng Chính phủ" },
  { id: "463832", label: "Văn phòng Trung ương Đảng" },
] as const satisfies readonly PortalOption[];

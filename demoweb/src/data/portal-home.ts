const portalOrigin = "https://dichvucong.gov.vn";
const portalIconBase = "/target/dichvucong/service-groups";

export type PortalAudienceType = "CITIZEN" | "CORPORATE";
export type PortalServiceGroupState = "ACTIVE";

export interface PortalServiceGroup {
  id: string;
  code: string;
  type: PortalAudienceType;
  order: number;
  state: PortalServiceGroupState;
  name: string;
  icon: string;
  href: string;
}

export interface PortalNewsItem {
  id: string;
  title: string;
  shortDescription?: string;
  href: string;
}

function serviceGroupHref(type: PortalAudienceType, id: string) {
  const segment =
    type === "CITIZEN"
      ? "dvc-chi-tiet-nhom-su-kien-cho-cong-dan"
      : "dvc-chi-tiet-nhom-su-kien-cho-doanh-nghiep";

  return `${portalOrigin}/${segment}/${id}`;
}

export const PORTAL_SERVICE_GROUPS = [
  {
    id: "019b694a-3c88-759a-8c84-1e02eb92a91b",
    code: "COCONNHO",
    type: "CITIZEN",
    order: 1,
    state: "ACTIVE",
    name: "Có con nhỏ",
    icon: `${portalIconBase}/co-con-nho.png`,
    href: serviceGroupHref("CITIZEN", "019b694a-3c88-759a-8c84-1e02eb92a91b"),
  },
  {
    id: "019b6e01-a0e9-75f9-b0a5-edac82b03d78",
    code: "HOCTAP",
    type: "CITIZEN",
    order: 2,
    state: "ACTIVE",
    name: "Học tập",
    icon: `${portalIconBase}/hoc-tap.png`,
    href: serviceGroupHref("CITIZEN", "019b6e01-a0e9-75f9-b0a5-edac82b03d78"),
  },
  {
    id: "019b6e11-d140-759c-a0b9-0bb7efd3fc4a",
    code: "VIECLAM",
    type: "CITIZEN",
    order: 3,
    state: "ACTIVE",
    name: "Việc làm",
    icon: `${portalIconBase}/viec-lam.png`,
    href: serviceGroupHref("CITIZEN", "019b6e11-d140-759c-a0b9-0bb7efd3fc4a"),
  },
  {
    id: "019b6e13-0cf4-70b7-b443-45281c901b6e",
    code: "CUTRUVAGIAYTOTUYTHAN",
    type: "CITIZEN",
    order: 4,
    state: "ACTIVE",
    name: "Cư trú và giấy tờ tùy thân",
    icon: `${portalIconBase}/cu-tru-va-giay-to-tuy-than.png`,
    href: serviceGroupHref("CITIZEN", "019b6e13-0cf4-70b7-b443-45281c901b6e"),
  },
  {
    id: "019b6e14-5b92-776a-ab2b-af9f0c261d97",
    code: "HONNHANVAGIADINH",
    type: "CITIZEN",
    order: 5,
    state: "ACTIVE",
    name: "VNeGuide: 3 thủ tục đã xác minh",
    icon: `${portalIconBase}/hon-nhan-va-gia-dinh.png`,
    href: "/hon-nhan-va-gia-dinh",
  },
  {
    id: "019b6e1a-3e04-7798-b659-49a14d3d2e58",
    code: "DIENLUCNHAODATDAI",
    type: "CITIZEN",
    order: 6,
    state: "ACTIVE",
    name: "Điện lực, nhà ở, đất đai",
    icon: `${portalIconBase}/dien-luc-nha-o-dat-dai.png`,
    href: serviceGroupHref("CITIZEN", "019b6e1a-3e04-7798-b659-49a14d3d2e58"),
  },
  {
    id: "019b6e22-16dd-70db-ac65-d3fe6b69906c",
    code: "SUCKHOEVAYTE",
    type: "CITIZEN",
    order: 7,
    state: "ACTIVE",
    name: "Sức khỏe và y tế",
    icon: `${portalIconBase}/suc-khoe-va-y-te.png`,
    href: serviceGroupHref("CITIZEN", "019b6e22-16dd-70db-ac65-d3fe6b69906c"),
  },
  {
    id: "019b6e26-4c8c-74a8-8467-9edb2713d23e",
    code: "PHUONGTIENVANGUOILAI",
    type: "CITIZEN",
    order: 8,
    state: "ACTIVE",
    name: "Phương tiện và người lái",
    icon: `${portalIconBase}/phuong-tien-va-nguoi-lai.png`,
    href: serviceGroupHref("CITIZEN", "019b6e26-4c8c-74a8-8467-9edb2713d23e"),
  },
  {
    id: "019b6e27-7642-76e5-8f29-649db67dd5e4",
    code: "HUUTRI",
    type: "CITIZEN",
    order: 9,
    state: "ACTIVE",
    name: "Hưu trí",
    icon: `${portalIconBase}/huu-tri.png`,
    href: serviceGroupHref("CITIZEN", "019b6e27-7642-76e5-8f29-649db67dd5e4"),
  },
  {
    id: "019b6e29-6dd5-7456-8d3e-a91feaae9f04",
    code: "NGUOITHANQUADOI",
    type: "CITIZEN",
    order: 10,
    state: "ACTIVE",
    name: "Người thân qua đời",
    icon: `${portalIconBase}/nguoi-than-qua-doi.png`,
    href: serviceGroupHref("CITIZEN", "019b6e29-6dd5-7456-8d3e-a91feaae9f04"),
  },
  {
    id: "019b6e31-866e-71ce-959b-af9f0836a7a2",
    code: "GIAIQUYETKHIEUKIEN",
    type: "CITIZEN",
    order: 110,
    state: "ACTIVE",
    name: "Giải quyết khiếu kiện",
    icon: `${portalIconBase}/giai-quyet-khieu-kien.png`,
    href: serviceGroupHref("CITIZEN", "019b6e31-866e-71ce-959b-af9f0836a7a2"),
  },
  {
    id: "019b6e0e-a904-742a-8407-d48b3d8c4730",
    code: "KHOISUKINHDOANH",
    type: "CORPORATE",
    order: 1,
    state: "ACTIVE",
    name: "Khởi sự kinh doanh",
    icon: `${portalIconBase}/khoi-su-kinh-doanh.png`,
    href: serviceGroupHref("CORPORATE", "019b6e0e-a904-742a-8407-d48b3d8c4730"),
  },
  {
    id: "019b6e0f-ad98-712e-96e6-5eea147fa53e",
    code: "LAODONGVABAOHIEMXAHOI",
    type: "CORPORATE",
    order: 2,
    state: "ACTIVE",
    name: "Lao động và bảo hiểm xã hội",
    icon: `${portalIconBase}/lao-dong-va-bao-hiem-xa-hoi.png`,
    href: serviceGroupHref("CORPORATE", "019b6e0f-ad98-712e-96e6-5eea147fa53e"),
  },
  {
    id: "019b6e12-4c57-72fa-86a4-d3e76970213e",
    code: "TAICHINHDOANHNGHIEP",
    type: "CORPORATE",
    order: 3,
    state: "ACTIVE",
    name: "Tài chính doanh nghiệp",
    icon: `${portalIconBase}/tai-chinh-doanh-nghiep.png`,
    href: serviceGroupHref("CORPORATE", "019b6e12-4c57-72fa-86a4-d3e76970213e"),
  },
  {
    id: "019b6e13-ad15-70ba-9889-126bb7521276",
    code: "DIENLUCDATDAIXAYDUNG",
    type: "CORPORATE",
    order: 4,
    state: "ACTIVE",
    name: "Điện lực, đất đai, xây dựng",
    icon: `${portalIconBase}/dien-luc-dat-dai-xay-dung.png`,
    href: serviceGroupHref("CORPORATE", "019b6e13-ad15-70ba-9889-126bb7521276"),
  },
  {
    id: "019b6e15-e590-71ed-9d9f-ce979fcdd9b2",
    code: "THUONGMAIQUANGCAO",
    type: "CORPORATE",
    order: 5,
    state: "ACTIVE",
    name: "Thương mại, quảng cáo",
    icon: `${portalIconBase}/thuong-mai-quang-cao.png`,
    href: serviceGroupHref("CORPORATE", "019b6e15-e590-71ed-9d9f-ce979fcdd9b2"),
  },
  {
    id: "019b6e21-735f-75c6-82d2-cfc723b40a47",
    code: "SOHUUTRITUEDANGKYSTAISAN",
    type: "CORPORATE",
    order: 6,
    state: "ACTIVE",
    name: "Sở hữu trí tuệ, đăng ký tài sản",
    icon: `${portalIconBase}/so-huu-tri-tue-dang-ky-tai-san.png`,
    href: serviceGroupHref("CORPORATE", "019b6e21-735f-75c6-82d2-cfc723b40a47"),
  },
  {
    id: "019b6e25-92b4-72d4-aae2-bae2eecf448b",
    code: "THANHLAPCHINHANHVANPHONGDAIDIEN",
    type: "CORPORATE",
    order: 7,
    state: "ACTIVE",
    name: "Thành lập chi nhánh, văn phòng đại diện",
    icon: `${portalIconBase}/thanh-lap-chi-nhanh-van-phong-dai-dien.png`,
    href: serviceGroupHref("CORPORATE", "019b6e25-92b4-72d4-aae2-bae2eecf448b"),
  },
  {
    id: "019b6e26-f7a1-702f-9ace-47f15cca232b",
    code: "DAUTHAUMUASAMCONG",
    type: "CORPORATE",
    order: 8,
    state: "ACTIVE",
    name: "Đấu thầu, mua sắm công",
    icon: `${portalIconBase}/dau-thau-mua-sam-cong.png`,
    href: serviceGroupHref("CORPORATE", "019b6e26-f7a1-702f-9ace-47f15cca232b"),
  },
  {
    id: "019b6e27-e274-7534-afba-98c2f732d180",
    code: "TAICAUTRUCDOANHNGHIEP",
    type: "CORPORATE",
    order: 9,
    state: "ACTIVE",
    name: "Tái cấu trúc doanh nghiệp",
    icon: `${portalIconBase}/tai-cau-truc-doanh-nghiep.png`,
    href: serviceGroupHref("CORPORATE", "019b6e27-e274-7534-afba-98c2f732d180"),
  },
  {
    id: "019b6e30-48a2-732a-8f83-b24540fddb77",
    code: "GIAIQUYETTRANHCHAPHOPDONG",
    type: "CORPORATE",
    order: 10,
    state: "ACTIVE",
    name: "Giải quyết tranh chấp hợp đồng",
    icon: `${portalIconBase}/giai-quyet-tranh-chap-hop-dong.png`,
    href: serviceGroupHref("CORPORATE", "019b6e30-48a2-732a-8f83-b24540fddb77"),
  },
  {
    id: "019b6e32-be21-756c-a306-06cf253a0b6f",
    code: "TAMDUNGCHAMDUTHOATDONG",
    type: "CORPORATE",
    order: 11,
    state: "ACTIVE",
    name: "Tạm dừng, chấm dứt hoạt động",
    icon: `${portalIconBase}/tam-dung-cham-dut-hoat-dong.png`,
    href: serviceGroupHref("CORPORATE", "019b6e32-be21-756c-a306-06cf253a0b6f"),
  },
] as const satisfies readonly PortalServiceGroup[];

export const PORTAL_SERVICE_GROUPS_BY_TYPE: Readonly<
  Record<PortalAudienceType, readonly PortalServiceGroup[]>
> = {
  CITIZEN: PORTAL_SERVICE_GROUPS.filter(
    (group) => group.type === "CITIZEN" && group.state === "ACTIVE",
  ).sort((left, right) => left.order - right.order),
  CORPORATE: PORTAL_SERVICE_GROUPS.filter(
    (group) => group.type === "CORPORATE" && group.state === "ACTIVE",
  ).sort((left, right) => left.order - right.order),
};

export const PORTAL_NEWS: readonly PortalNewsItem[] = [
  {
    id: "019e01c7-fa15-716b-89e4-ef8f57c8e1e8",
    title:
      "Công bố dữ liệu, hướng dẫn khai thác, sử dụng dữ liệu sổ sức khoẻ điện tử tích hợp trên VNeID thay thế sổ giấy trong giải quyết thủ tục hành chính",
    shortDescription:
      "Công bố dữ liệu, hướng dẫn khai thác, sử dụng dữ liệu sổ sức khoẻ điện tử tích hợp trên VNeID thay thế sổ giấy trong giải quyết thủ tục hành chính",
    href: `${portalOrigin}/tin-tuc/019e01c7-fa15-716b-89e4-ef8f57c8e1e8`,
  },
  {
    id: "019e01b1-a116-765c-b82a-2b88556aab84",
    title:
      "Công bố dữ liệu và hướng dẫn kết nối, khai thác sử dụng dữ liệu đăng ký doanh nghiệp, hợp tác xã, hộ kinh doanh thay thế giấy tờ trong giải quyết thủ tục hành chính",
    shortDescription:
      "Công bố dữ liệu và hướng dẫn kết nối, khai thác sử dụng dữ liệu đăng ký doanh nghiệp, hợp tác xã, hộ kinh doanh thay thế giấy tờ trong giải quyết thủ tục hành chính",
    href: `${portalOrigin}/tin-tuc/019e01b1-a116-765c-b82a-2b88556aab84`,
  },
  {
    id: "019e01a1-862e-76a3-b10a-0e46d78bb2f0",
    title:
      "Công bố dữ liệu hộ tịch và hướng dẫn kết nối, khai thác sử dụng dữ liệu hộ tịch thay thế giấy tờ trong giải quyết thủ tục hành chính",
    shortDescription:
      "Việc công bố dữ liệu hộ tịch và hướng dẫn kết nối, khai thác sử dụng dữ liệu hộ tịch thay thế giấy tờ trong giải quyết thủ tục hành chính",
    href: `${portalOrigin}/tin-tuc/019e01a1-862e-76a3-b10a-0e46d78bb2f0`,
  },
];

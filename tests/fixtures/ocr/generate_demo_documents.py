"""Generate synthetic PNG documents for manual OCR testing."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUTPUT = Path(__file__).with_name("demo_documents")
FONT_PATH = Path(r"C:\Windows\Fonts\arial.ttf")
FONT_BOLD_PATH = Path(r"C:\Windows\Fonts\arialbd.ttf")


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD_PATH if bold else FONT_PATH), size)


def render(
    name: str,
    title: str,
    lines: list[str],
    *,
    title_size: int = 46,
    content_y: int = 390,
) -> None:
    image = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((55, 55, 1345, 1745), outline="#333333", width=4)
    draw.text(
        (110, 105),
        "TÀI LIỆU TỔNG HỢP DÙNG KIỂM THỬ OCR",
        fill="#a00000",
        font=font(32, bold=True),
    )
    draw.multiline_text(
        (110, 220),
        title,
        fill="#111111",
        font=font(title_size, bold=True),
        spacing=12,
        align="center",
    )
    y = content_y
    for line in lines:
        draw.text((120, y), line, fill="#202020", font=font(30))
        y += 82
    draw.line((120, 1470, 1280, 1470), fill="#777777", width=2)
    draw.text(
        (120, 1515),
        "Chữ ký minh họa: NGƯỜI LẬP TÀI LIỆU DEMO",
        fill="#333333",
        font=font(28),
    )
    draw.text(
        (120, 1635),
        "KHÔNG CÓ GIÁ TRỊ PHÁP LÝ — KHÔNG CHỨA DỮ LIỆU THẬT",
        fill="#a00000",
        font=font(27, bold=True),
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT / name, format="PNG", optimize=True)


def main() -> None:
    render(
        "legal_dwelling_demo.png",
        "HỢP ĐỒNG CHO THUÊ CHỖ Ở\n(BẢN DEMO)",
        [
            "Bên cho thuê: NGUYỄN VĂN DEMO",
            "Bên thuê: TRẦN THỊ THỬ NGHIỆM",
            "Địa điểm chỗ ở: Số 123 Đường Mẫu, Phường Thử, Hà Nội",
            "Mục đích: sử dụng địa điểm trên làm nơi ở hợp pháp.",
            "Bên cho thuê đồng ý cho bên thuê sử dụng chỗ ở nêu trên.",
            "Thời hạn minh họa: từ 01/01/2026 đến 31/12/2026.",
            "Các thông tin trong tài liệu này hoàn toàn là dữ liệu tổng hợp.",
        ],
    )
    render(
        "minor_consent_demo.png",
        "VĂN BẢN ĐỒNG Ý\nCỦA CHA, MẸ HOẶC NGƯỜI GIÁM HỘ\n(BẢN DEMO)",
        [
            "Người đồng ý: PHẠM VĂN GIÁM HỘ DEMO",
            "Vai trò: Người giám hộ của người chưa thành niên.",
            "Người chưa thành niên: LÊ THỊ DỮ LIỆU MẪU",
            "Tôi đồng ý cho người chưa thành niên nêu trên đăng ký tạm trú",
            "tại Số 123 Đường Mẫu, Phường Thử, Hà Nội.",
            "Ý kiến này được lập tự nguyện để phục vụ hồ sơ minh họa.",
            "Tất cả họ tên và địa chỉ đều là dữ liệu tổng hợp.",
        ],
        title_size=38,
        content_y=500,
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

from typing import Any

import pytest

from vneguide.ocr import CT01TemplateMapper, OcrBlock


def _blocks(lines: list[tuple[str, int | None]]) -> tuple[OcrBlock, ...]:
    return tuple(
        OcrBlock(
            block_type="text",
            bbox=(0.05, index * 0.1, 0.95, index * 0.1 + 0.05),
            angle=angle,
            content=text,
        )
        for index, (text, angle) in enumerate(lines)
    )


def _accept(_field_id: str, _value: Any) -> None:
    return None


def test_maps_only_visible_ct01_fields_as_pending_candidates() -> None:
    result = CT01TemplateMapper().map(
        _blocks(
            [
                ("TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", 0),
                ("Mẫu CT01", 0),
                ("Họ, chữ đệm và tên: NGƯỜI DÙNG THỬ NGHIỆM", 0),
                ("Ngày, tháng, năm sinh: 01/01/2000", 0),
                ("Số định danh cá nhân: 000000000000", 0),
                ("Đăng ký tạm trú tại: Số 00 đường Kiểm Thử, Hà Nội", 0),
            ]
        ),
        validate_value=_accept,
    )

    assert result.document_type == "CT01"
    values = {candidate.field_id: candidate.suggested_value for candidate in result.candidates}
    assert values == {
        "applicant_full_name": "NGƯỜI DÙNG THỬ NGHIỆM",
        "applicant_date_of_birth": "2000-01-01",
        "applicant_personal_id": "000000000000",
        "temporary_address": "Số 00 đường Kiểm Thử, Hà Nội",
    }
    assert all(candidate.source == "USER_UPLOAD" for candidate in result.candidates)


def test_rotated_values_require_confirmation() -> None:
    result = CT01TemplateMapper().map(
        _blocks(
            [
                ("TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", 90),
                ("Mẫu CT01", 90),
                ("Họ và tên: NGƯỜI DÙNG THỬ NGHIỆM", 90),
            ]
        ),
        validate_value=_accept,
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].confidence < 0.85
    assert result.warnings == ("low_confidence:applicant_full_name",)


def test_wrong_document_never_emits_candidates() -> None:
    result = CT01TemplateMapper().map(
        _blocks([("BIÊN NHẬN HỒ SƠ THỬ NGHIỆM", 0)]),
        validate_value=_accept,
    )

    assert result.document_type == "other"
    assert result.candidates == ()


def test_catalog_validation_can_reject_visible_value() -> None:
    def reject_identity(field_id: str, _value: Any) -> None:
        if field_id == "applicant_personal_id":
            raise ValueError("invalid synthetic identity")

    result = CT01TemplateMapper().map(
        _blocks(
            [
                ("TỜ KHAI THAY ĐỔI THÔNG TIN CƯ TRÚ", 0),
                ("Mẫu CT01", 0),
                ("Số định danh cá nhân: 000000000000", 0),
            ]
        ),
        validate_value=reject_identity,
    )

    assert result.candidates == ()


def test_ocr_block_rejects_untrusted_geometry() -> None:
    with pytest.raises(ValueError, match="normalized"):
        OcrBlock("text", (-1.0, 0.0, 1.0, 1.0), 0, "unsafe")

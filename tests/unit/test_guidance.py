from __future__ import annotations

from pathlib import Path

import pytest

from vneguide.ai import InformationRequest
from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode, QATopic, SourceStatus
from vneguide.rules import ProcedureQAResponder

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def repository() -> ProcedureRepository:
    return ProcedureRepository.discover(ROOT)


@pytest.fixture(scope="module")
def responder(repository: ProcedureRepository) -> ProcedureQAResponder:
    return ProcedureQAResponder(repository)


_FIELD_HELP_TARGETS = {
    ProcedureCode.BIRTH_CERTIFICATE_COPY: "requester_type",
    ProcedureCode.HOUSING_CONDITION_CONFIRMATION: "hanoi_zone",
    ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION: "registration_mode",
}


@pytest.mark.parametrize("code", tuple(ProcedureCode))
@pytest.mark.parametrize("topic", tuple(QATopic))
def test_every_topic_for_every_procedure_is_grounded(
    repository: ProcedureRepository,
    responder: ProcedureQAResponder,
    code: ProcedureCode,
    topic: QATopic,
) -> None:
    target = _FIELD_HELP_TARGETS[code] if topic is QATopic.FIELD_HELP else None
    answer = responder.answer(code, InformationRequest((topic,), target_field_id=target))

    assert answer.text.startswith("Dạ,")
    assert answer.source_ids
    for source_id in answer.source_ids:
        source = repository.get_source(source_id)
        assert source.status is SourceStatus.APPROVED
        assert source.procedure_code in (None, code.value)


def test_temporary_residence_fee_uses_read_only_references(
    responder: ProcedureQAResponder,
) -> None:
    request = InformationRequest(
        (QATopic.FEE,),
        reference_fields={
            "registration_mode": "by_list",
            "submission_channel": "online",
        },
        evidence={
            "registration_mode": "theo danh sách",
            "submission_channel": "trực tuyến",
        },
    )

    answer = responder.answer(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        request,
        draft_values={"registration_mode": "individual_or_household"},
    )

    assert "5.000 đồng/người" in answer.text
    assert "7.000 đồng" not in answer.text
    assert "kiểm tra mức thu chính thức" in answer.text


def test_temporary_residence_fee_lists_options_without_guessing(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        InformationRequest((QATopic.FEE,)),
    )

    assert "7.000 đồng" in answer.text
    assert "15.000 đồng" in answer.text
    assert "5.000 đồng/người" in answer.text
    assert "10.000 đồng/người" in answer.text
    assert "chưa có mức phí riêng" in answer.text


def test_birth_copy_fee_is_not_multiplied_by_copy_count(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.BIRTH_CERTIFICATE_COPY,
        InformationRequest((QATopic.FEE,)),
        draft_values={"copies_requested": 20},
    )

    assert "8.000 đồng" in answer.text
    assert "không tự nhân" in answer.text
    assert "160.000" not in answer.text


def test_housing_fee_and_conditions_keep_official_boundary(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.HOUSING_CONDITION_CONFIRMATION,
        InformationRequest((QATopic.FEE, QATopic.CONDITIONS_LIMITED)),
    )

    assert "không thu phí" in answer.text
    assert "không kết luận anh/chị đủ điều kiện" in answer.text
    assert "không thay cơ quan có thẩm quyền" in answer.text


def test_documents_are_separated_from_required_form_information(
    responder: ProcedureQAResponder,
) -> None:
    documents = responder.answer(
        ProcedureCode.BIRTH_CERTIFICATE_COPY,
        InformationRequest((QATopic.DOCUMENTS,)),
    )
    fields = responder.answer(
        ProcedureCode.BIRTH_CERTIFICATE_COPY,
        InformationRequest((QATopic.REQUIRED_INFORMATION,)),
    )

    assert "Theo kênh nộp" in documents.text
    assert "Tùy trường hợp" in documents.text
    assert "Thông tin sự kiện khai sinh đủ để tra cứu" not in documents.text
    assert "không phải danh sách giấy tờ" in fields.text


def test_registration_mode_field_help_explains_selected_choice(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        InformationRequest(
            (QATopic.FIELD_HELP,),
            target_field_id="registration_mode",
            reference_fields={"registration_mode": "by_list"},
            evidence={"registration_mode": "theo danh sách"},
        ),
    )

    assert "Tờ khai CT01 của từng người" in answer.text
    assert "cần cơ quan có thẩm quyền kiểm tra chính thức" in answer.text
    assert "by_list" not in answer.text


def test_missing_reviewed_field_help_uses_authority_fallback(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.TEMPORARY_RESIDENCE_REGISTRATION,
        InformationRequest(
            (QATopic.FIELD_HELP,),
            target_field_id="applicant_full_name",
        ),
    )

    assert (
        "dữ liệu đã duyệt của VNeGuide chưa có thông tin này. Anh/chị vui lòng liên hệ "
        "Công an cấp xã hoặc xem nguồn chính thức ạ."
    ) in answer.text


def test_birth_legal_basis_states_package_limit(
    responder: ProcedureQAResponder,
) -> None:
    answer = responder.answer(
        ProcedureCode.BIRTH_CERTIFICATE_COPY,
        InformationRequest((QATopic.LEGAL_BASIS,)),
    )

    assert "chưa có văn bản pháp luật riêng" in answer.text
    assert answer.source_ids == ("SRC-DVC-2000635",)

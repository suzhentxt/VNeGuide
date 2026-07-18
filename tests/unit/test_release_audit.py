from deployment.scripts.release_audit import contains_possible_personal_identifier


def test_personal_id_pattern_detects_standalone_twelve_digit_value() -> None:
    assert contains_possible_personal_identifier('"citizen_id": "001234567890"')
    assert contains_possible_personal_identifier("CCCD:001234567890")


def test_personal_id_pattern_ignores_machine_identifiers() -> None:
    assert not contains_possible_personal_identifier("019d2bfd-00f6-700a-86bc-657210103554")
    assert not contains_possible_personal_identifier(
        "c4cc0f984013798641f301da97e35b000b16dec3ee060bdebc0e84ee1a2a0be7"
    )
    assert not contains_possible_personal_identifier("record_001234567890")
    assert not contains_possible_personal_identifier('"code": "TP-G12.000111111110"')
    assert not contains_possible_personal_identifier('"code": "999999999999"')

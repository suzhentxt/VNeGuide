from __future__ import annotations

from pathlib import Path

from vneguide.language import LanguageNormalizer, evaluate_normalizer, load_dialect_samples

ROOT = Path(__file__).resolve().parents[2]


def _fixed_intent_classifier(text: str) -> str:
    normalized = text.casefold()
    if "giấy nhà" in normalized:
        return "ambiguous"
    if "đăng ký tạm trú" in normalized:
        return "1.004194"
    if "bản sao giấy khai sinh" in normalized or "bản sao khai sinh" in normalized:
        return "2.000635"
    if "bản sao sổ hộ khẩu" in normalized:
        return "document_question"
    if normalized.startswith("tôi tên"):
        return "identity_statement"
    return "unknown"


def test_dialect_dataset_meets_safety_and_accuracy_gates() -> None:
    samples = load_dialect_samples(ROOT / "data" / "evaluation" / "dialect")

    metrics = evaluate_normalizer(LanguageNormalizer(), samples, _fixed_intent_classifier)

    assert metrics.sample_count == 16
    assert metrics.exact_normalization_rate == 1.0
    assert metrics.intent_accuracy_non_decreasing
    assert metrics.normalized_intent_accuracy == 1.0
    assert metrics.protected_spans_all_preserved
    assert metrics.unsafe_inference_count == 0


def test_every_declared_protected_value_is_detected_as_a_protected_span() -> None:
    normalizer = LanguageNormalizer()
    samples = load_dialect_samples(ROOT / "data" / "evaluation" / "dialect")

    for sample in samples:
        result = normalizer.normalize(sample.raw_text, source=sample.input_source)
        detected = {span.value for span in result.protected_spans}
        assert set(sample.protected_values) <= detected

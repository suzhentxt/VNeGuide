"""Grounded conversational replies rendered from reviewed procedure packs."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, TypeGuard

from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode, ProcedurePack


class GuidanceTopic(StrEnum):
    """Allowlisted procedural topics that the guided core can answer."""

    FEE = "fee"
    PROCESSING_TIME = "processing_time"
    CHECKLIST = "checklist"
    STEPS = "steps"
    AUTHORITY = "authority"
    CHANNELS = "channels"
    RESULT = "result"


@dataclass(frozen=True, slots=True)
class GroundedReply:
    """A deterministic reply plus the reviewed sources that support it."""

    text: str
    topic: GuidanceTopic
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("grounded reply text must not be empty")
        if not self.source_ids or any(not source_id.strip() for source_id in self.source_ids):
            raise ValueError("grounded reply must reference reviewed sources")


class ReplyComposer(Protocol):
    """Optional post-extraction reply layer used by the conversation core."""

    def compose(
        self,
        *,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None: ...


class CatalogReplyComposer:
    """Answer bounded Vietnamese guidance questions without calling a model.

    Topic selection is lexical and local. Every rendered fact comes from the
    reviewed ``ProcedurePack`` selected by the structured extraction layer.
    """

    _TOPIC_PATTERNS: tuple[tuple[GuidanceTopic, tuple[str, ...]], ...] = (
        (
            GuidanceTopic.FEE,
            (
                r"\ble phi\b",
                r"\bphi bao nhieu\b",
                r"\bbao nhieu tien\b",
                r"\bco mat phi\b",
                r"\bmien phi\b",
                r"\bchi phi\b",
            ),
        ),
        (
            GuidanceTopic.PROCESSING_TIME,
            (
                r"\bbao lau\b",
                r"\bmay ngay\b",
                r"\bthoi gian giai quyet\b",
                r"\bthoi han giai quyet\b",
                r"\bkhi nao co ket qua\b",
            ),
        ),
        (
            GuidanceTopic.CHECKLIST,
            (
                r"\bho so\b",
                r"\bgiay to\b",
                r"\bcan chuan bi\b",
                r"\bcan nop nhung gi\b",
                r"\bcan nhung gi\b",
                r"\btai lieu nao\b",
            ),
        ),
        (
            GuidanceTopic.STEPS,
            (
                r"\bcac buoc\b",
                r"\bquy trinh\b",
                r"\bhuong dan\b",
                r"\blam thu tuc the nao\b",
                r"\bbat dau tu dau\b",
            ),
        ),
        (
            GuidanceTopic.AUTHORITY,
            (
                r"\bco quan nao\b",
                r"\bdon vi nao\b",
                r"\bai giai quyet\b",
                r"\bnop o dau\b",
                r"\bnoi giai quyet\b",
            ),
        ),
        (
            GuidanceTopic.CHANNELS,
            (
                r"\bkenh nop\b",
                r"\bcach nop\b",
                r"\bnop bang cach nao\b",
                r"\bco nop online\b",
                r"\bnop truc tuyen duoc khong\b",
                r"\bco gui buu (?:dien|chinh)\b",
            ),
        ),
        (
            GuidanceTopic.RESULT,
            (
                r"\bket qua la gi\b",
                r"\bnhan duoc gi\b",
                r"\bduoc cap gi\b",
                r"\btra ket qua\b",
            ),
        ),
    )

    _CHANNEL_LABELS: Mapping[str, str] = {
        "online": "trực tuyến",
        "direct": "trực tiếp",
        "postal": "qua bưu chính",
    }

    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository

    def compose(
        self,
        *,
        procedure_code: ProcedureCode,
        message: str,
    ) -> GroundedReply | None:
        if not isinstance(message, str) or not message.strip():
            return None
        topic = self._select_topic(_normalize_vietnamese(message))
        if topic is None:
            return None
        pack = self._repository.get_by_code(procedure_code)
        text, source_ids = self._render(topic, pack)
        return GroundedReply(text=text, topic=topic, source_ids=source_ids)

    @classmethod
    def _select_topic(cls, normalized_message: str) -> GuidanceTopic | None:
        for topic, patterns in cls._TOPIC_PATTERNS:
            if any(re.search(pattern, normalized_message) for pattern in patterns):
                return topic
        return None

    def _render(
        self,
        topic: GuidanceTopic,
        pack: ProcedurePack,
    ) -> tuple[str, tuple[str, ...]]:
        if topic is GuidanceTopic.FEE:
            return self._render_fee(pack), pack.source_ids
        if topic is GuidanceTopic.PROCESSING_TIME:
            value = _required_text(pack.service_info, "processing_time_display")
            return f"Thời gian giải quyết: {value}.", pack.source_ids
        if topic is GuidanceTopic.CHECKLIST:
            lines = [
                f"- {item.name}: {item.condition}" if item.condition else f"- {item.name}"
                for item in pack.checklist
            ]
            sources = _unique(source_id for item in pack.checklist for source_id in item.source_ids)
            return "Hồ sơ cần chuẩn bị:\n" + "\n".join(lines), sources
        if topic is GuidanceTopic.STEPS:
            lines = [f"{step.step}. {step.text}" for step in pack.guidance_steps]
            sources = _unique(
                source_id for step in pack.guidance_steps for source_id in step.source_ids
            )
            return "Các bước thực hiện:\n" + "\n".join(lines), sources
        if topic is GuidanceTopic.AUTHORITY:
            value = _required_text(pack.service_info, "authority")
            return f"Cơ quan giải quyết: {value}.", pack.source_ids
        if topic is GuidanceTopic.CHANNELS:
            raw_channels = pack.service_info.get("channels")
            if not isinstance(raw_channels, tuple):
                raise ValueError("reviewed channels must be an immutable sequence")
            channels = [
                self._CHANNEL_LABELS.get(channel, channel)
                for channel in raw_channels
                if isinstance(channel, str) and channel.strip()
            ]
            if not channels:
                raise ValueError("reviewed channels must not be empty")
            return f"Có thể nộp hồ sơ theo các kênh: {', '.join(channels)}.", pack.source_ids
        if topic is GuidanceTopic.RESULT:
            value = _required_text(pack.service_info, "result")
            return f"Kết quả của thủ tục: {value}.", pack.source_ids
        raise AssertionError(f"unsupported guidance topic: {topic}")

    @staticmethod
    def _render_fee(pack: ProcedurePack) -> str:
        raw_fee = pack.service_info.get("fee")
        if not isinstance(raw_fee, Mapping):
            raise ValueError("reviewed fee must be an object")

        display = raw_fee.get("display")
        if isinstance(display, str) and display.strip():
            return f"Lệ phí: {display}."

        individual = raw_fee.get("individual_or_household")
        if isinstance(individual, Mapping):
            online = individual.get("online_vnd")
            direct = individual.get("direct_vnd")
            if not _is_non_negative_int(online) or not _is_non_negative_int(direct):
                raise ValueError("reviewed individual fee is invalid")
            text = (
                "Lệ phí cho cá nhân hoặc hộ gia đình: "
                f"{_format_vnd(online)} khi nộp trực tuyến; "
                f"{_format_vnd(direct)} khi nộp trực tiếp."
            )
            exemption = raw_fee.get("exemption")
            if isinstance(exemption, str) and exemption.strip():
                text = f"{text} {exemption}."
            return text

        amount = raw_fee.get("amount_vnd")
        if _is_non_negative_int(amount):
            return f"Lệ phí: {_format_vnd(amount)}."
        raise ValueError("reviewed fee does not contain a supported display value")


def _normalize_vietnamese(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    without_marks = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(re.sub(r"[^a-z0-9]+", " ", without_marks).split())


def _required_text(values: Mapping[str, object], key: str) -> str:
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"reviewed service_info.{key} must be non-empty text")
    return value


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    if not ordered:
        raise ValueError("grounded guidance has no reviewed sources")
    return tuple(ordered)


def _is_non_negative_int(value: object) -> TypeGuard[int]:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _format_vnd(value: int) -> str:
    return f"{value:,}".replace(",", ".") + " đồng"


__all__ = [
    "CatalogReplyComposer",
    "GroundedReply",
    "GuidanceTopic",
    "ReplyComposer",
]

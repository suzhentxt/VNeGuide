"""Small reviewed lexicon for administrative Vietnamese normalization.

The source workbook and public dialect page are research inputs only.  This
module intentionally keeps a narrow, auditable subset relevant to the three
supported procedures instead of copying a general-purpose dialect dictionary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GlossaryEntry:
    source: str
    target: str | None
    rule_id: str
    category: str
    regions: tuple[str, ...] = ()
    ambiguity_options: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source.strip() or not self.rule_id.strip() or not self.category.strip():
            raise ValueError("glossary entries require source, rule_id, and category")
        if self.target is None and len(self.ambiguity_options) < 2:
            raise ValueError("entries without a target must describe an ambiguity")
        if self.target is not None and self.ambiguity_options:
            raise ValueError("a deterministic entry cannot also be ambiguous")

    @property
    def pattern(self) -> re.Pattern[str]:
        return re.compile(rf"(?<!\w){re.escape(self.source)}(?!\w)", re.IGNORECASE)


class Glossary:
    def __init__(self, entries: tuple[GlossaryEntry, ...]) -> None:
        folded: set[str] = set()
        for entry in entries:
            key = entry.source.casefold()
            if key in folded:
                raise ValueError(f"duplicate glossary source: {entry.source}")
            folded.add(key)
        self._entries = tuple(sorted(entries, key=lambda item: len(item.source), reverse=True))

    @property
    def entries(self) -> tuple[GlossaryEntry, ...]:
        return self._entries


DEFAULT_ENTRIES = (
    # Administrative phrases and common speech-recognition errors.
    GlossaryEntry(
        "hộ khẩu photo",
        "bản sao sổ hộ khẩu",
        "admin.household_copy",
        "administrative",
    ),
    GlossaryEntry(
        "làm tạm chú",
        "đăng ký tạm trú",
        "asr.temporary_residence_action",
        "asr",
    ),
    GlossaryEntry(
        "làm tạm chủ",
        "đăng ký tạm trú",
        "asr.temporary_residence_action_owner",
        "asr",
    ),
    GlossaryEntry(
        "làm tạm trú",
        "đăng ký tạm trú",
        "admin.temporary_residence_action",
        "administrative",
    ),
    GlossaryEntry(
        "mần tạm trú",
        "đăng ký tạm trú",
        "dialect.temporary_residence_action",
        "dialect",
        ("central", "south"),
    ),
    GlossaryEntry(
        "thường chú",
        "thường trú",
        "asr.permanent_residence",
        "asr",
    ),
    GlossaryEntry("tạm chú", "tạm trú", "asr.temporary_residence", "asr"),
    GlossaryEntry("tạm chủ", "tạm trú", "asr.temporary_residence_owner", "asr"),
    GlossaryEntry("trích lụt", "trích lục", "asr.civil_extract", "asr"),
    GlossaryEntry("bảo sao", "bản sao", "asr.certified_copy", "asr"),
    GlossaryEntry("khai sanh", "khai sinh", "dialect.birth", "dialect", ("south",)),
    GlossaryEntry("nhập khẩu", "đăng ký thường trú", "admin.permanent_residence", "dialect"),
    GlossaryEntry("đk tạm trú", "đăng ký tạm trú", "abbr.temp_residence", "abbreviation"),
    GlossaryEntry("đăng kí", "đăng ký", "orthography.register", "spelling"),
    GlossaryEntry(
        "đk thường trú",
        "đăng ký thường trú",
        "abbr.permanent_residence",
        "abbreviation",
    ),
    GlossaryEntry("dvc", "dịch vụ công", "abbr.public_service", "abbreviation"),
    GlossaryEntry("ubnd", "Ủy ban nhân dân", "abbr.authority", "abbreviation"),
    # Central variants selected from the user-provided grouped workbook.
    GlossaryEntry("mần chi", "làm gì", "central.do_what", "dialect", ("central",)),
    GlossaryEntry("ở mô", "ở đâu", "central.where", "dialect", ("central",)),
    GlossaryEntry("khi mô", "khi nào", "central.when", "dialect", ("central",)),
    GlossaryEntry("như rứa", "như vậy", "central.like_that", "dialect", ("central",)),
    GlossaryEntry("răng rứa", "sao vậy", "central.how_so", "dialect", ("central",)),
    GlossaryEntry("nỏ", "không", "central.negation", "dialect", ("central",)),
    GlossaryEntry("chừ", "bây giờ", "central.now", "dialect", ("central",)),
    # Southern variants supported by both research inputs.
    GlossaryEntry("tụi tui", "chúng tôi", "south.we", "dialect", ("south",)),
    GlossaryEntry("hổng", "không", "south.negation_hong", "dialect", ("south",)),
    GlossaryEntry("hông", "không", "south.negation_hong_short", "dialect", ("south",)),
    GlossaryEntry("hong", "không", "south.negation_unaccented", "dialect", ("south",)),
    GlossaryEntry("tui", "tôi", "south.pronoun", "dialect", ("south",)),
    GlossaryEntry("ưng", "muốn", "central.want", "dialect", ("central",)),
    GlossaryEntry("mần", "làm", "central.do", "dialect", ("central", "south")),
    GlossaryEntry("ổng", "ông ấy", "south.he_older", "dialect", ("south",)),
    GlossaryEntry("bả", "bà ấy", "south.she_older", "dialect", ("south",)),
    GlossaryEntry("ảnh", "anh ấy", "south.he", "dialect", ("south",)),
    GlossaryEntry("bển", "bên đó", "south.there", "dialect", ("south",)),
    GlossaryEntry("vầy", "vậy", "south.this_way", "dialect", ("south",)),
    GlossaryEntry("nhen", "nhé", "south.particle", "dialect", ("south",)),
    GlossaryEntry("nhể", "nhỉ", "north.particle", "dialect", ("north",)),
    GlossaryEntry("photo", "bản sao", "loanword.copy", "loanword"),
    # Known administrative ambiguity: never rewrite or infer a field/service.
    GlossaryEntry(
        "giấy nhà",
        None,
        "ambiguous.house_document",
        "ambiguity",
        ambiguity_options=(
            "Giấy chứng nhận quyền sử dụng đất",
            "Giấy xác nhận chỗ ở",
            "Khác",
        ),
    ),
)


def default_glossary() -> Glossary:
    return Glossary(DEFAULT_ENTRIES)


__all__ = ["DEFAULT_ENTRIES", "Glossary", "GlossaryEntry", "default_glossary"]

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEXT_TARGETS = [
    ROOT / ".env.example",
    ROOT / "README.md",
    ROOT / "pyproject.toml",
    *sorted((ROOT / "src").rglob("*.py")),
]

SECRET_PATTERNS = {
    "OpenAI key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "GitHub token": re.compile(r"gh[oprsu]_[A-Za-z0-9]{20,}"),
    "assigned API key": re.compile(r"(?im)^[ \t]*VNEGUIDE_API_KEY[ \t]*=[ \t]*(?![<\s#])\S+"),
}


class RepositorySafetyTest(unittest.TestCase):
    def test_owned_text_files_do_not_contain_obvious_secrets(self) -> None:
        findings: list[str] = []
        for path in TEXT_TARGETS:
            content = path.read_text(encoding="utf-8")
            for label, pattern in SECRET_PATTERNS.items():
                if pattern.search(content):
                    findings.append(f"{path.relative_to(ROOT)}: {label}")

        message = "Phát hiện secret có thể đã bị commit: " + ", ".join(findings)
        self.assertEqual(findings, [], message)


if __name__ == "__main__":
    unittest.main()

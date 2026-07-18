#!/usr/bin/env python3
"""Fail a release when tracked files contain common secret, PII, or merge artifacts."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAX_TEXT_BYTES = 2_000_000
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".mjs",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}
ALLOWED_ENV_FILES = {".env.example", ".env.local.example"}
SYNTHETIC_DATA_PREFIXES = ("data/evaluation/", "tests/")

CONFLICT_PATTERN = re.compile(r"(?m)^(?:<{7} |={7}$|>{7} )")
PERSONAL_ID_PATTERN = re.compile(r"(?<!\d)\d{12}(?!\d)")
SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "aws_access_key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "google_api_key": re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def indexed_files() -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return tuple(raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw)


def read_index_text(relative: str) -> str | None:
    if Path(relative).suffix.lower() not in TEXT_SUFFIXES:
        return None
    result = subprocess.run(
        ["git", "show", "--no-textconv", f":{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    if len(result.stdout) > MAX_TEXT_BYTES:
        return None
    try:
        return result.stdout.decode("utf-8")
    except UnicodeError:
        return None


def main() -> int:
    findings: list[str] = []
    scanned = 0
    files = indexed_files()

    for relative in files:
        path = Path(relative)
        name = path.name
        if (name == ".env" or name.startswith(".env.")) and name not in ALLOWED_ENV_FILES:
            findings.append(f"tracked sensitive environment file: {relative}")
        if path.suffix.lower() in {".key", ".log", ".pem", ".p12", ".pfx"}:
            findings.append(f"tracked sensitive artifact: {relative}")

        text = read_index_text(relative)
        if text is None:
            continue
        scanned += 1
        if CONFLICT_PATTERN.search(text):
            findings.append(f"merge conflict marker: {relative}")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {relative}")
        if not relative.startswith(SYNTHETIC_DATA_PREFIXES) and PERSONAL_ID_PATTERN.search(text):
            findings.append(f"possible 12-digit personal identifier outside fixtures: {relative}")

    if findings:
        print("RELEASE_AUDIT_FAILED")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1

    print(f"RELEASE_AUDIT_OK index_files={len(files)} text_files={scanned}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

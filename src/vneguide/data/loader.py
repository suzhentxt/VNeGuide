"""Filesystem access for the repository-owned VNeGuide data package."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

from .errors import DataFormatError, DataPackageNotFoundError


def _reject_non_standard_number(value: str) -> NoReturn:
    raise ValueError(f"non-standard JSON number {value}")


@dataclass(frozen=True, slots=True)
class DataPackagePaths:
    root: Path
    catalog: Path
    contracts: Path
    evaluation: Path
    references: Path
    qa: Path

    @classmethod
    def from_root(cls, root: str | Path) -> DataPackagePaths:
        resolved = Path(root).expanduser().resolve()
        required = ("catalog", "contracts", "evaluation", "references", "qa")
        missing = [name for name in required if not (resolved / name).is_dir()]
        if missing:
            raise DataPackageNotFoundError(
                f"{resolved} is not a VNeGuide data package; missing: {', '.join(missing)}"
            )
        return cls(
            root=resolved,
            catalog=resolved / "catalog",
            contracts=resolved / "contracts",
            evaluation=resolved / "evaluation",
            references=resolved / "references",
            qa=resolved / "qa",
        )

    @classmethod
    def discover(cls, start: str | Path | None = None) -> DataPackagePaths:
        configured = os.getenv("VNEGUIDE_DATA_DIR")
        if configured:
            return cls.from_root(configured)

        starting_points: list[Path] = []
        if start is not None:
            starting_points.append(Path(start).expanduser().resolve())
        else:
            starting_points.extend((Path.cwd().resolve(), Path(__file__).resolve()))

        visited: set[Path] = set()
        for starting_point in starting_points:
            base = starting_point if starting_point.is_dir() else starting_point.parent
            for candidate in (base, *base.parents):
                if candidate in visited:
                    continue
                visited.add(candidate)
                for data_root in (candidate, candidate / "data"):
                    if (data_root / "catalog").is_dir() and (data_root / "contracts").is_dir():
                        return cls.from_root(data_root)

        raise DataPackageNotFoundError(
            "cannot find VNeGuide data package; set VNEGUIDE_DATA_DIR explicitly"
        )


def load_json(path: str | Path) -> Any:
    resolved = Path(path)
    try:
        with resolved.open("r", encoding="utf-8") as handle:
            return json.load(handle, parse_constant=_reject_non_standard_number)
    except FileNotFoundError as exc:
        raise DataFormatError(f"data file not found: {resolved}") from exc
    except json.JSONDecodeError as exc:
        raise DataFormatError(
            f"invalid JSON in {resolved} at line {exc.lineno}, column {exc.colno}"
        ) from exc
    except ValueError as exc:
        raise DataFormatError(f"invalid JSON in {resolved}: {exc}") from exc


def load_json_object(path: str | Path) -> dict[str, Any]:
    value = load_json(path)
    if not isinstance(value, dict):
        raise DataFormatError(f"expected a JSON object in {path}")
    return value


def load_json_array(path: str | Path) -> list[dict[str, Any]]:
    value = load_json(path)
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise DataFormatError(f"expected an array of JSON objects in {path}")
    return value


def load_jsonl(path: str | Path) -> tuple[dict[str, Any], ...]:
    resolved = Path(path)
    records: list[dict[str, Any]] = []
    try:
        with resolved.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line, parse_constant=_reject_non_standard_number)
                except json.JSONDecodeError as exc:
                    raise DataFormatError(
                        f"invalid JSONL in {resolved} at line {line_number}"
                    ) from exc
                except ValueError as exc:
                    raise DataFormatError(
                        f"invalid JSONL in {resolved} at line {line_number}: {exc}"
                    ) from exc
                if not isinstance(record, dict):
                    raise DataFormatError(
                        f"expected a JSON object in {resolved} at line {line_number}"
                    )
                records.append(record)
    except FileNotFoundError as exc:
        raise DataFormatError(f"data file not found: {resolved}") from exc
    return tuple(records)

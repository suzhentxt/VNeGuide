#!/usr/bin/env python3
"""Probe public/local VNeGuide URLs and emit reproducible JSON metrics."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

MAX_RESPONSE_BYTES = 1_000_000
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WEB_MARKER = "Bản mô phỏng Hackathon"


class SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[no-untyped-def]
        self,
        request,
        file_pointer,
        code,
        message,
        headers,
        new_url,
    ):
        target = urllib.parse.urljoin(request.full_url, new_url)
        current_origin = urllib.parse.urlsplit(request.full_url)
        target_origin = urllib.parse.urlsplit(target)
        if (current_origin.scheme, current_origin.netloc) != (
            target_origin.scheme,
            target_origin.netloc,
        ):
            raise urllib.error.HTTPError(
                target,
                code,
                "cross-origin redirect refused",
                headers,
                file_pointer,
            )
        return super().redirect_request(
            request,
            file_pointer,
            code,
            message,
            headers,
            target,
        )


HTTP_OPENER = urllib.request.build_opener(SameOriginRedirectHandler())


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def http_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError("must be an absolute HTTP(S) URL")
    if parsed.username or parsed.password:
        raise argparse.ArgumentTypeError("URL must not contain credentials")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise argparse.ArgumentTypeError("URL must be an origin without path, query, or fragment")
    return value.rstrip("/")


def git_metadata() -> dict[str, str | bool | None]:
    revision_result = subprocess.run(
        ["git", "rev-parse", "--short=12", "HEAD"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    status_result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    diff_result = subprocess.run(
        ["git", "diff", "--cached", "--binary"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    staged_digest = hashlib.sha256(diff_result.stdout).hexdigest() if diff_result.stdout else None
    return {
        "base_revision": revision_result.stdout.strip() or "unknown",
        "tracked_dirty": bool(status_result.stdout),
        "staged_diff_sha256": staged_digest,
    }


def package_version() -> str:
    try:
        return version("vneguide")
    except PackageNotFoundError:
        return "unknown"


def probe(
    url: str,
    *,
    samples: int,
    timeout: float,
    expect_health: bool,
    expected_marker: str | None = None,
) -> dict[str, Any]:
    latencies: list[float] = []
    statuses: list[int] = []
    failures: list[str] = []

    for _ in range(samples):
        started = time.perf_counter()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "VNeGuideReleaseSmoke/1"})
            with HTTP_OPENER.open(request, timeout=timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds safety limit")
                status = response.status
                content_type = response.headers.get_content_type()
                charset = response.headers.get_content_charset() or "utf-8"
            statuses.append(status)
            if not 200 <= status < 300:
                raise ValueError(f"unexpected HTTP status {status}")
            if expect_health:
                payload = json.loads(body)
                if payload != {"status": "ok"}:
                    raise ValueError("health payload is not {'status': 'ok'}")
            elif expected_marker is not None:
                if content_type != "text/html":
                    raise ValueError("web response is not HTML")
                if expected_marker not in body.decode(charset):
                    raise ValueError("web response does not contain the expected marker")
        except (OSError, ValueError, json.JSONDecodeError, urllib.error.HTTPError) as exc:
            failures.append(type(exc).__name__)
        finally:
            latencies.append(round((time.perf_counter() - started) * 1_000, 2))

    ordered = sorted(latencies)
    p95_index = max(0, min(len(ordered) - 1, (95 * len(ordered) + 99) // 100 - 1))
    return {
        "url": url,
        "samples": samples,
        "successes": samples - len(failures),
        "statuses": statuses,
        "failures": failures,
        "latency_ms": {
            "min": min(ordered),
            "median": round(statistics.median(ordered), 2),
            "p95": ordered[p95_index],
            "max": max(ordered),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", required=True, type=http_url)
    parser.add_argument("--web-url", required=True, type=http_url)
    parser.add_argument("--samples", type=positive_int, default=5)
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--web-marker", default=DEFAULT_WEB_MARKER)
    parser.add_argument("--provider", default=os.environ.get("VNEGUIDE_LLM_PROVIDER", "mock"))
    parser.add_argument(
        "--model",
        default=os.environ.get("VNEGUIDE_MODEL", "mock-scripted"),
        help="model/version label only; never pass a secret",
    )
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    report = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "git": git_metadata(),
        "package_version": package_version(),
        "provider_label": args.provider,
        "model_label": args.model,
        "model_call_verified": False,
        "api": probe(
            f"{args.api_url}/health",
            samples=args.samples,
            timeout=args.timeout,
            expect_health=True,
        ),
        "web": probe(
            args.web_url,
            samples=args.samples,
            timeout=args.timeout,
            expect_health=False,
            expected_marker=args.web_marker,
        ),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    api_ok = report["api"]["successes"] == args.samples
    web_ok = report["web"]["successes"] == args.samples
    return 0 if api_ok and web_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

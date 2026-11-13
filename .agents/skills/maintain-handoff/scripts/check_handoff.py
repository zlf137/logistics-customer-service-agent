"""Validate the workspace handoff's compactness invariants."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

MAX_LINES = 120
MAX_NON_WHITESPACE_CHARS = 6000
MAX_RECENT_VERIFICATION_ITEMS = 5
MAX_NEXT_STEPS = 5


def _section_lines(lines: list[str], heading: str) -> list[str]:
    try:
        start = lines.index(heading) + 1
    except ValueError:
        return []

    end = next(
        (index for index in range(start, len(lines)) if lines[index].startswith("## ")),
        len(lines),
    )
    return lines[start:end]


def validate(path: Path) -> tuple[list[str], int, int]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    non_whitespace_chars = len(re.sub(r"\s", "", text))
    errors: list[str] = []

    if len(lines) > MAX_LINES:
        errors.append(f"line count {len(lines)} exceeds {MAX_LINES}")
    if non_whitespace_chars > MAX_NON_WHITESPACE_CHARS:
        errors.append(
            "non-whitespace character count "
            f"{non_whitespace_chars} exceeds {MAX_NON_WHITESPACE_CHARS}"
        )

    verification_items = sum(
        line.startswith("- ") for line in _section_lines(lines, "## 最近验证")
    )
    if verification_items > MAX_RECENT_VERIFICATION_ITEMS:
        errors.append(
            f"recent verification has {verification_items} items; "
            f"maximum is {MAX_RECENT_VERIFICATION_ITEMS}"
        )

    next_steps = sum(
        re.match(r"^\d+\. ", line) is not None
        for line in _section_lines(lines, "## 下一步")
    )
    if next_steps > MAX_NEXT_STEPS:
        errors.append(f"next steps has {next_steps} items; maximum is {MAX_NEXT_STEPS}")

    return errors, len(lines), non_whitespace_chars


def main() -> int:
    default_path = Path(__file__).resolve().parents[5] / "HANDOFF.md"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=default_path)
    args = parser.parse_args()

    path = args.path.resolve()
    if not path.is_file():
        parser.error(f"handoff file not found: {path}")

    errors, line_count, non_whitespace_chars = validate(path)
    print(f"HANDOFF_LINES={line_count}")
    print(f"HANDOFF_NONWHITESPACE_CHARS={non_whitespace_chars}")
    for error in errors:
        print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())

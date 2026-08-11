from __future__ import annotations

import os
import re
from pathlib import Path

from .model import Device
from .safety import SafetyError, fsync_directory, fsync_file, under


READER_CONFIG = ".kobo/Kobo/Kobo eReader.conf"
ANALYTICS_CONFIG = ".kobo/Kobo/Analytics.conf"
_SECTION = re.compile(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$")
_KEY = re.compile(r"^(\s*)([^=]+?)(\s*=\s*)(.*?)(\r?\n)?$")
_COMMENTS = ("#", ";")


def _read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines(keepends=True)
    except (OSError, UnicodeError) as error:
        raise SafetyError(f"cannot read Nickel configuration {path}: {error}") from error


def _validate_lines(path: Path, lines: list[str]) -> None:
    section: str | None = None
    for line in lines:
        content = line.rstrip("\r\n")
        stripped = content.strip()
        if not stripped or stripped.startswith(_COMMENTS):
            continue
        section_match = _SECTION.match(line)
        if section_match is not None:
            section = section_match.group(1)
            continue
        if section is None or "=" not in content:
            raise SafetyError(f"malformed Nickel configuration: {path}")


def _newline(lines: list[str]) -> str:
    return "\r\n" if any(line.endswith("\r\n") for line in lines) else "\n"


def _set_values(
    path: Path,
    updates: dict[str, dict[str, str]],
) -> None:
    lines = _read_lines(path) if path.is_file() else []
    _validate_lines(path, lines)
    newline = _newline(lines)
    output: list[str] = []
    section: str | None = None
    seen: dict[str, set[str]] = {name: set() for name in updates}

    for line in lines:
        section_match = _SECTION.match(line)
        if section_match is not None:
            section = section_match.group(1)
            output.append(line)
            continue
        if section not in updates:
            output.append(line)
            continue
        key_match = _KEY.match(line)
        if key_match is None or key_match.group(2).strip() not in updates[section]:
            output.append(line)
            continue
        key = key_match.group(2).strip()
        output.append(
            f"{key_match.group(1)}{key_match.group(2)}{key_match.group(3)}"
            f"{updates[section][key]}{key_match.group(5) or newline}"
        )
        seen[section].add(key)

    for section_name, values in updates.items():
        missing = [key for key in values if key not in seen[section_name]]
        if not missing:
            continue
        header = f"[{section_name}]"
        start = next(
            (index for index, line in enumerate(output) if line.rstrip("\r\n").strip() == header),
            None,
        )
        if start is None:
            if output and output[-1].rstrip("\r\n"):
                output.append(newline)
            output.append(header + newline)
            output.extend(f"{key}={values[key]}{newline}" for key in missing)
            continue
        end = next(
            (
                index
                for index in range(start + 1, len(output))
                if _SECTION.match(output[index])
            ),
            len(output),
        )
        output[end:end] = [f"{key}={values[key]}{newline}" for key in missing]

    updated = "".join(output)
    original = "".join(lines)
    if updated != original:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".new")
        temporary.write_text(updated, encoding="utf-8")
        fsync_file(temporary)
        os.replace(temporary, path)
        fsync_directory(path.parent)


def apply_privacy(mount: Path, device: Device) -> None:
    if device.platform != "kobo":
        return
    _set_values(
        under(mount, READER_CONFIG),
        {
            "ApplicationPreferences": {
                "AIRPLANE_MODE": "true",
                "SideloadedMode": "true",
            }
        },
    )
    # Blackholed endpoints cannot drain this queue; clearing it avoids
    # repeatedly rewriting an ever-growing telemetry file in flash.
    analytics = under(mount, ANALYTICS_CONFIG)
    if analytics.is_file():
        section = _section_for_key(analytics, "GAQueue", "General")
        _set_values(analytics, {section: {"GAQueue": "@Invalid()"}})


def privacy_is_current(mount: Path, device: Device) -> bool:
    if device.platform != "kobo":
        return True
    values = _values(under(mount, READER_CONFIG))
    return (
        values.get(("ApplicationPreferences", "AIRPLANE_MODE")) == "true"
        and values.get(("ApplicationPreferences", "SideloadedMode")) == "true"
    )


def _values(path: Path) -> dict[tuple[str, str], str]:
    lines = _read_lines(path) if path.is_file() else []
    _validate_lines(path, lines)
    section: str | None = None
    values: dict[tuple[str, str], str] = {}
    for line in lines:
        section_match = _SECTION.match(line)
        if section_match is not None:
            section = section_match.group(1)
            continue
        if section is None:
            continue
        key_match = _KEY.match(line)
        if key_match is not None:
            values[(section, key_match.group(2).strip())] = key_match.group(4).strip()
    return values


def _section_for_key(path: Path, key: str, fallback: str) -> str:
    if not path.is_file():
        return fallback
    lines = _read_lines(path)
    _validate_lines(path, lines)
    section: str | None = None
    for line in lines:
        section_match = _SECTION.match(line)
        if section_match is not None:
            section = section_match.group(1)
            continue
        key_match = _KEY.match(line)
        if section is not None and key_match is not None:
            if key_match.group(2).strip() == key:
                return section
    return fallback

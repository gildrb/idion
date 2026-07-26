from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import tempfile

from .safety import SafetyError


MANGA_VALUES: dict[str, str] = {
    "flipping_scroll_mode": "false",
    "flipping_zoom_mode": '"page"',
    "kopt_max_columns": "1",
    "kopt_page_scroll": "0",
    "kopt_text_wrap": "0",
    "kopt_zoom_mode_genus": "4",
    "kopt_zoom_mode_type": "2",
    "normal_zoom_mode": '"page"',
    "panel_zoom_enabled": "false",
    "zoom_mode": '"page"',
}


def apply_manga_profile(sidecar: Path, *, crop: bool = False) -> Path:
    sidecar = sidecar.expanduser().resolve()
    if not sidecar.is_file() or sidecar.name != "metadata.pdf.lua":
        raise SafetyError(
            f"expected a KOReader PDF sidecar named metadata.pdf.lua: {sidecar}"
        )

    original = sidecar.read_text(encoding="utf-8")
    if not original.lstrip().startswith("return {"):
        raise SafetyError(f"sidecar is not a recognized Lua settings table: {sidecar}")

    values = dict(MANGA_VALUES)
    values["kopt_trim_page"] = "3" if crop else "0"
    updated = original
    missing: list[tuple[str, str]] = []
    for key, value in values.items():
        pattern = re.compile(rf'(?m)^(\s*)\["{re.escape(key)}"\]\s*=\s*[^,\n]+,')
        replacement = rf'\1["{key}"] = {value},'
        updated, count = pattern.subn(replacement, updated, count=1)
        if count == 0:
            missing.append((key, value))

    if missing:
        insertion = "".join(f'    ["{key}"] = {value},\n' for key, value in missing)
        updated = updated.replace("return {\n", "return {\n" + insertion, 1)

    backup = sidecar.with_suffix(sidecar.suffix + ".before-manga-profile")
    if backup.exists():
        raise SafetyError(f"profile backup already exists: {backup}")
    shutil.copy2(sidecar, backup)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=sidecar.name + ".", dir=sidecar.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(updated)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, sidecar.stat().st_mode)
        os.replace(temporary_name, sidecar)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
    return backup

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "seo"
SCRIPT_DIR = ROOT / "scripts" / "seo"
DOCS_DIR = ROOT / "docs" / "seo"
REPORTS_DIR = ROOT / "reports" / "seo"
PREVIEW_DIR = REPORTS_DIR / "generated-preview"
CACHE_DIR = REPORTS_DIR / ".cache"
BENCHMARK_TEMP_DIR = REPORTS_DIR / ".benchmark-temp"
FORBIDDEN_CACHE_DIR = ROOT / ".seo-cache"
ALLOWED_ROOTS = (DATA_DIR, SCRIPT_DIR, DOCS_DIR, REPORTS_DIR)
GENERATOR_VERSION = "1.1.0"
DATA_CONTRACT_VERSION = "1.0.0"


class FoundationError(RuntimeError):
    """Raised when isolation, validation, or generation cannot continue."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _reject_reparse_escape(path: Path) -> None:
    cursor = path.parent
    while _is_relative_to(cursor, ROOT) and cursor != ROOT:
        if cursor.exists():
            is_junction = bool(getattr(cursor, "is_junction", lambda: False)())
            if cursor.is_symlink() or is_junction:
                raise FoundationError(f"Reparse-point output path is prohibited: {cursor}")
        cursor = cursor.parent


def ensure_allowed_output(path: Path | str) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = ROOT / candidate
    resolved = candidate.resolve(strict=False)
    forbidden = FORBIDDEN_CACHE_DIR.resolve(strict=False)
    if resolved == forbidden or _is_relative_to(resolved, forbidden):
        raise FoundationError(f"Root .seo-cache is prohibited: {resolved}")
    if not any(resolved == root.resolve(strict=False) or _is_relative_to(resolved, root.resolve(strict=False)) for root in ALLOWED_ROOTS):
        raise FoundationError(f"Output path is outside approved isolated roots: {resolved}")
    _reject_reparse_escape(resolved)
    return resolved


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def stable_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def atomic_write_bytes(
    path: Path | str,
    payload: bytes,
    validator: Callable[[bytes], None] | None = None,
) -> dict[str, Any]:
    target = ensure_allowed_output(path)
    if validator is not None:
        validator(payload)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.read_bytes() == payload:
        return {"path": target.relative_to(ROOT).as_posix(), "status": "UNCHANGED", "sha256": sha256_bytes(payload), "bytes": len(payload)}

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if validator is not None:
            validator(temp_path.read_bytes())
        expected_hash = sha256_bytes(payload)
        if sha256_file(temp_path) != expected_hash:
            raise FoundationError(f"Temporary output hash mismatch: {temp_path}")
        os.replace(temp_path, target)
        temp_path = None
        if sha256_file(target) != expected_hash:
            raise FoundationError(f"Destination hash mismatch after atomic replace: {target}")
        return {"path": target.relative_to(ROOT).as_posix(), "status": "WRITTEN", "sha256": expected_hash, "bytes": len(payload)}
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def atomic_write_text(path: Path | str, text: str) -> dict[str, Any]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return atomic_write_bytes(path, normalized.encode("utf-8"))


def atomic_write_json(path: Path | str, value: Any) -> dict[str, Any]:
    def validate(payload: bytes) -> None:
        json.loads(payload.decode("utf-8"))

    return atomic_write_bytes(path, stable_json_bytes(value), validate)


def read_json(path: Path | str) -> Any:
    target = Path(path)
    if not target.is_absolute():
        target = ROOT / target
    with target.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def hash_inputs(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.as_posix().casefold()):
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(path).encode("ascii"))
        digest.update(b"\0")
    digest.update(GENERATOR_VERSION.encode("ascii"))
    digest.update(DATA_CONTRACT_VERSION.encode("ascii"))
    return digest.hexdigest()


def field_value(business: dict[str, Any], name: str, require_verified: bool = True) -> Any:
    field = business["fields"][name]
    if require_verified and field.get("verificationStatus") != "VERIFIED":
        return None
    return field.get("value")


def print_result(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))

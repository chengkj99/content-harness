import contextlib
import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


class HarnessError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)


def require(condition, code, message):
    if not condition:
        raise HarnessError(code, message)


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value: str):
    require(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{0,100}", value)), "INVALID_ID", value)
    return value


def digest(data: bytes):
    return "sha256:" + hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def yaml_bytes(value):
    return yaml.safe_dump(value, allow_unicode=True, sort_keys=False).encode()


def read_yaml(path):
    try:
        return yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise HarnessError("INVALID_YAML", f"{path}: {exc}") from exc


def safe_path(root: Path, relative: str):
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts, "UNSAFE_PATH", relative)
    root = root.resolve()
    current = root
    for part in path.parts:
        current = current / part
        require(not current.is_symlink(), "UNSAFE_PATH", f"symlink: {current}")
    result = (root / path).resolve()
    require(result.is_relative_to(root) and result != root, "UNSAFE_PATH", relative)
    return result


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), "UNSAFE_PATH", str(path))
    fd, name = tempfile.mkstemp(prefix=".harness-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(name):
            os.unlink(name)


@contextlib.contextmanager
def lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    path = safe_path(root, ".lock")
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HarnessError("RUN_LOCKED", f"Another writer holds {path}") from exc
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def files(path: Path):
    require(not path.is_symlink(), "UNSAFE_PATH", str(path))
    if path.is_file():
        return {"content": path.read_bytes()}
    if not path.exists():
        return {}
    result = {}
    for entry in sorted(path.rglob("*")):
        require(not entry.is_symlink(), "UNSAFE_PATH", str(entry))
        if entry.is_file():
            result[entry.relative_to(path).as_posix()] = entry.read_bytes()
    return result


def tree_hash(contents):
    if not contents:
        return None
    return digest(json_bytes({name: digest(data) for name, data in sorted(contents.items())}))

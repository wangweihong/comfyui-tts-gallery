"""Built-in catalog and atomic, process-safe user voice library."""
import copy
try:
    import fcntl
except ImportError:  # Windows ComfyUI portable installs
    fcntl = None
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .audio import MAX_BYTES, inspect

BASE = Path(__file__).parent
ID_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}\Z")


class LibraryError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_file(root, relative):
    root = Path(root).absolute()
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise LibraryError("无效音频路径 / Invalid audio path")
    p = root / relative
    for item in [p, *p.parents]:
        if item == root:
            break
        if item.is_symlink():
            raise LibraryError("不允许符号链接 / Symbolic links are not allowed")
    if not p.is_file() or not p.resolve().is_relative_to(root.resolve()):
        raise LibraryError("音频文件缺失 / Audio file is missing", 404)
    return p


def localized(row, field, language):
    return row.get(f"{field}_{language}") or row.get(f"{field}_zh") or row.get(f"{field}_en") or ""


def language(value):
    if value not in ("zh", "en"):
        raise LibraryError("无效界面语言 / Invalid interface language")
    return value


def default_user_root():
    configured = os.environ.get("COMFYUI_TTS_GALLERY_USER_LIBRARY")
    if configured:
        return Path(configured)
    import folder_paths
    return Path(folder_paths.get_user_directory()) / "tts_gallery"


class Library:
    def __init__(self, builtin=None, user=None):
        self.builtin = Path(builtin) if builtin else BASE / "library"
        self._user = Path(user) if user else None
        self.lock = threading.RLock()

    @property
    def user(self):
        return self._user if self._user is not None else default_user_root()

    def _builtin(self):
        try:
            data = json.loads((self.builtin / "catalog.json").read_text("utf-8"))
        except FileNotFoundError:
            return []
        return data["records"]

    def _index(self):
        path = self.user / "data" / "custom.json"
        if path.is_symlink():
            raise LibraryError("用户索引不能为符号链接 / Invalid user index")
        try:
            return json.loads(path.read_text("utf-8"))
        except FileNotFoundError:
            return {"version": 1, "revision": 0, "records": []}
        except (ValueError, OSError) as exc:
            raise LibraryError("用户索引无法读取，请从备份恢复 / Cannot read user catalog", 500) from exc

    @contextmanager
    def _write(self):
        with self.lock:
            self.user.mkdir(parents=True, exist_ok=True)
            for name in ("data", "audio", "preview"):
                p = self.user / name
                if p.is_symlink():
                    raise LibraryError("用户目录不能含符号链接 / Invalid user directory")
                p.mkdir(exist_ok=True)
            lock_path = self.user / ".lock"
            if lock_path.is_symlink():
                raise LibraryError("锁文件不能为符号链接 / Invalid lock file")
            descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(descriptor, "a+") as lock_file:
                if fcntl:
                    fcntl.flock(lock_file, fcntl.LOCK_EX)
                else:
                    import msvcrt
                    if lock_file.seek(0, 2) == 0:
                        lock_file.write("0")
                        lock_file.flush()
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield self._index()
                finally:
                    if fcntl:
                        fcntl.flock(lock_file, fcntl.LOCK_UN)
                    else:
                        lock_file.seek(0)
                        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

    def _save(self, index):
        index["revision"] += 1
        fd, name = tempfile.mkstemp(prefix=".index-", dir=self.user / "data")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as out:
                json.dump(index, out, ensure_ascii=False, indent=2)
                out.flush()
                os.fsync(out.fileno())
            os.replace(name, self.user / "data" / "custom.json")
        finally:
            Path(name).unlink(missing_ok=True)

    def record(self, identifier, kind=None):
        if not isinstance(identifier, str) or not ID_PATTERN.fullmatch(identifier):
            raise LibraryError("无效参考编号 / Invalid reference ID")
        # Copy so callers cannot change either catalog in memory.
        rows = self._builtin() + self._index()["records"]
        row = next((r for r in rows if r["id"] == identifier), None)
        if not row or kind and row["kind"] != kind:
            raise LibraryError("参考编号不存在或类型不匹配 / Reference not found or wrong type", 404)
        return copy.deepcopy(row)

    def asset(self, identifier, role="original", kind=None):
        row = self.record(identifier, kind)
        if role not in ("original", "preview"):
            raise LibraryError("无效音频类型 / Invalid audio role")
        key = "audio" if role == "original" else "preview"
        return checked_file(self.user if row["origin"] == "user" else self.builtin, row[key])

    def fingerprint(self, identifier, kind=None):
        row = self.record(identifier, kind)
        # The digest includes content and metadata, so edits invalidate Comfy caches.
        return hashlib.sha256((json.dumps(row, sort_keys=True, ensure_ascii=False) + sha256(self.asset(identifier, kind=kind))).encode()).hexdigest()

    def catalog(self):
        index = self._index()
        rows = self._builtin() + index["records"]
        for row in rows:
            try:
                root = self.user if row["origin"] == "user" else self.builtin
                checked_file(root, row["audio"])
                checked_file(root, row["preview"])
                row["available"] = True
            except (ValueError, OSError):
                row["available"] = False
        return {"version": 1, "revision": index["revision"], "records": rows}

    @staticmethod
    def metadata(data):
        if not isinstance(data, dict):
            raise LibraryError("元数据必须是对象 / Metadata must be an object")
        out = {}
        for key, maximum in (("name_zh", 120), ("name_en", 120), ("description_zh", 2000),
                             ("description_en", 2000), ("reference_text", 8000)):
            value = data.get(key, "")
            if not isinstance(value, str) or len(value) > maximum:
                raise LibraryError(f"字段过长或类型错误 / Invalid field: {key}")
            out[key] = value.strip()
        if not (out["name_zh"] or out["name_en"]) or not out["reference_text"]:
            raise LibraryError("请填写名称和准确逐字稿 / Name and exact transcript are required")
        lang = data.get("language", "zh")
        if lang not in ("zh", "en", "other"):
            raise LibraryError("无效音频语言 / Invalid audio language")
        tags = data.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 20 or any(not isinstance(t, str) or not t.strip() or len(t) > 40 for t in tags):
            raise LibraryError("标签最多20个，每个最多40字 / Invalid tags")
        out.update(language=lang, tags=list(dict.fromkeys(t.strip() for t in tags)))
        return out

    def add(self, source, filename, metadata):
        info = self.metadata(metadata)
        source = Path(source)
        if source.stat().st_size > MAX_BYTES:
            raise LibraryError("音频最大25 MiB / Audio exceeds 25 MiB", 413)
        suffix = Path(filename).suffix.lower()
        if suffix not in (".wav", ".flac", ".mp3"):
            raise LibraryError("仅支持 WAV、FLAC、MP3 / Unsupported file extension")
        properties, preview = inspect(source)
        identifier = "u-" + uuid.uuid4().hex
        row = {"id": identifier, "kind": "voice", "origin": "user", **info, **properties,
               "audio": f"audio/{identifier}{suffix}", "preview": f"preview/{identifier}.wav",
               "sha256": sha256(source), "original_filename": Path(filename).name,
               "source": "User import", "created_at": datetime.now(timezone.utc).isoformat(),
               "revision": 1, "validation": {"execution": "decoded", "transcript": "user_supplied", "listening": "unreviewed"}}
        with self._write() as index:
            original = self.user / row["audio"]
            preview_path = self.user / row["preview"]
            try:
                shutil.copyfile(source, original)
                preview_path.write_bytes(preview)
                index["records"].append(row)
                self._save(index)
            except BaseException:
                original.unlink(missing_ok=True)
                preview_path.unlink(missing_ok=True)
                raise
        return row

    def update(self, identifier, data):
        info = self.metadata(data)
        with self._write() as index:
            row = next((r for r in index["records"] if r["id"] == identifier), None)
            if row is None:
                raise LibraryError("只能编辑自定义音色 / Only custom voices can be edited", 404)
            if data.get("revision") != row["revision"]:
                raise LibraryError("条目已更新，请刷新后重试 / Stale edit; refresh and retry", 409)
            row.update(info)
            row["revision"] += 1
            self._save(index)
            return copy.deepcopy(row)

    def delete(self, identifier, revision):
        with self._write() as index:
            row = next((r for r in index["records"] if r["id"] == identifier), None)
            if row is None:
                raise LibraryError("只能删除自定义音色 / Only custom voices can be deleted", 404)
            if revision != row["revision"]:
                raise LibraryError("条目已更新，请刷新后重试 / Stale delete; refresh and retry", 409)
            paths = [checked_file(self.user, row[k]) for k in ("audio", "preview") if (self.user / row[k]).exists()]
            index["records"].remove(row)
            self._save(index)
            for path in paths:
                path.unlink(missing_ok=True)


library = Library()

"""Gallery HTTP endpoints; no route can enqueue or load a generation model."""
import asyncio
import json
import tempfile
from functools import wraps
from pathlib import Path

from aiohttp import web

from .audio import MAX_BYTES
from .catalog import BASE, LibraryError, language, library
from . import workflows


def register_routes(routes, lib=None):
    lib = lib or library

    def endpoint(method, path):
        def wrap(fn):
            @wraps(fn)
            async def handler(request):
                try:
                    return await fn(request)
                except LibraryError as exc:
                    return web.json_response({"error": str(exc)}, status=exc.status)
                except (ValueError, json.JSONDecodeError) as exc:
                    return web.json_response({"error": str(exc)}, status=400)
            getattr(routes, method.lower())("/tts_gallery" + path)(handler)
            return handler
        return wrap

    def same_origin(request):
        origin = request.headers.get("Origin")
        if origin and origin != f"{request.scheme}://{request.host}":
            raise LibraryError("拒绝跨来源操作 / Cross-origin writes are rejected", 403)
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise LibraryError("拒绝跨来源操作 / Cross-origin writes are rejected", 403)

    async def body(request):
        same_origin(request)
        if request.content_type != "application/json":
            raise LibraryError("必须使用JSON / Expected application/json")
        raw = bytearray()
        async for chunk in request.content.iter_chunked(8192):
            raw.extend(chunk)
            if len(raw) > 65536:
                raise LibraryError("元数据过大 / Metadata too large", 413)
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise LibraryError("JSON必须是对象 / Expected a JSON object")
        return data

    @endpoint("GET", "/gallery")
    async def gallery(request):
        return web.FileResponse(BASE / "web" / "gallery.html", headers={"Cache-Control": "no-cache"})

    @endpoint("GET", "/static/{name}")
    async def static(request):
        name = request.match_info["name"]
        if name not in ("gallery.css", "gallery.mjs", "core.mjs"):
            raise web.HTTPNotFound()
        return web.FileResponse(BASE / "web" / name, headers={"Cache-Control": "no-cache"})

    @endpoint("GET", "/catalog")
    async def catalog(request):
        return web.json_response(await asyncio.to_thread(lib.catalog), headers={"Cache-Control": "no-store"})

    @endpoint("GET", "/audio/{id}/{role}")
    async def audio(request):
        path = await asyncio.to_thread(lib.asset, request.match_info["id"], request.match_info["role"])
        return web.FileResponse(path, headers={"Cache-Control": "no-cache", "X-Content-Type-Options": "nosniff"})

    @endpoint("GET", "/workflow/{id}")
    async def workflow(request):
        identifier = request.match_info["id"]
        lang = language(request.query.get("lang", "zh"))
        result = await asyncio.to_thread(workflows.export, identifier, request.query.get("model"), request.query.get("format", "ui"), lang, lib)
        headers = {"Cache-Control": "no-store"}
        if request.query.get("download") == "1":
            headers["Content-Disposition"] = f'attachment; filename="tts-gallery-{identifier}.json"'
        return web.json_response(result, headers=headers)

    @endpoint("POST", "/voices")
    async def upload(request):
        same_origin(request)
        if request.content_type != "multipart/form-data":
            raise LibraryError("上传需要multipart/form-data / Expected multipart upload")
        reader = await request.multipart()
        # Temporary inputs disappear even when validation or decoding fails.
        with tempfile.TemporaryDirectory(prefix="tts-gallery-upload-") as directory:
            path = Path(directory) / "upload"
            filename, metadata, size = None, None, 0
            while True:
                part = await reader.next()
                if part is None:
                    break
                if part.name == "audio" and filename is None:
                    filename = part.filename or ""
                    with path.open("wb") as out:
                        while chunk := await part.read_chunk():
                            size += len(chunk)
                            if size > MAX_BYTES:
                                raise LibraryError("音频最大25 MiB / Audio exceeds 25 MiB", 413)
                            out.write(chunk)
                elif part.name == "metadata" and metadata is None:
                    raw = bytearray()
                    while chunk := await part.read_chunk():
                        raw.extend(chunk)
                        if len(raw) > 65536:
                            raise LibraryError("元数据过大 / Metadata too large", 413)
                    metadata = json.loads(raw)
                else:
                    raise LibraryError("重复或未知上传字段 / Duplicate or unknown upload field")
            if not filename or metadata is None or not size:
                raise LibraryError("请提供音频和元数据 / Audio and metadata are required")
            row = await asyncio.to_thread(lib.add, path, filename, metadata)
        return web.json_response({"record": row}, status=201)

    @endpoint("PATCH", "/voices/{id}")
    async def update(request):
        data = await body(request)
        return web.json_response({"record": await asyncio.to_thread(lib.update, request.match_info["id"], data)})

    @endpoint("DELETE", "/voices/{id}")
    async def delete(request):
        data = await body(request)
        await asyncio.to_thread(lib.delete, request.match_info["id"], data.get("revision"))
        return web.json_response({"ok": True})

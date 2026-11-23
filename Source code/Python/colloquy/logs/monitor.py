"""A bounded, read-only view of the files written by Logger, including worker paths."""
import json
import re
from hashlib import blake2s
from urllib.parse import parse_qs

from colloquy.base import Base
from colloquy.logger import Logger


TAIL_BYTES = 16 * 1024
MAX_EVENTS = 100
RECENT_FILES = 12
STAMP = re.compile(r"^(\d+(?::\d+){0,2}\.\d{2}s?):?(?: (.*))?$")


def tail(path):
    with path.open("rb") as stream:
        size = stream.seek(0, 2)
        stream.seek(max(0, size - TAIL_BYTES))
        data = stream.read(TAIL_BYTES)
    if size > TAIL_BYTES and b"\n" in data:
        data = data.partition(b"\n")[2]
    return data.decode("utf-8", errors="replace")


def events(source, content):
    elapsed, stamp = 0.0, ""
    for line in content.splitlines():
        match = STAMP.fullmatch(line)
        if match:
            stamp, message = match.groups()
            elapsed = 0.0
            for part in stamp.rstrip("s").split(":"):
                elapsed = elapsed * 60 + float(part)
        else:
            message = line
        yield elapsed, [stamp, source, message or ""]


def active_thread_count():
    # Base.all_threads also removes stopped threads. Observers only need a count.
    return sum(node.is_started for node in Base._all_threads.copy())


def log_files(folder):
    root = folder.resolve()
    files = {}
    for path in folder.rglob("*.log"):
        try:
            if path.is_file() and path.resolve().is_relative_to(root):
                name = path.relative_to(folder).with_suffix("").as_posix()
                files[name] = (path, path.stat())
        except FileNotFoundError:
            continue

    return files


def snapshot(folder, source, previous=None):
    files = log_files(folder)
    if source:
        selected = [source] if source in files else []
    else:
        recent = sorted(files, key=lambda name: files[name][1].st_mtime_ns, reverse=True)
        selected = recent[:RECENT_FILES]
    names = sorted(files)
    threads = active_thread_count()
    revisions = [(name, files[name][1].st_mtime_ns, files[name][1].st_size) for name in selected]
    signature = json.dumps([names, source, threads, revisions]).encode()
    etag = '"' + blake2s(signature, digest_size=16).hexdigest() + '"'
    if etag == previous:
        return etag, None

    entries = []
    for name in selected:
        try:
            entries.extend(events(name, tail(files[name][0])))
        except FileNotFoundError:
            continue
    entries.sort(key=lambda row: row[0])
    return etag, {
        "sources": names,
        "events": [row for _, row in entries[-MAX_EVENTS:]],
        "threads": threads,
    }


def response(environ):
    source = parse_qs(environ.get("QUERY_STRING", "")).get("source", [""])[0]
    headers = [("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")]
    try:
        etag, data = snapshot(Logger.folder(), source, environ.get("HTTP_IF_NONE_MATCH"))
    except OSError:
        return "503 Service Unavailable", headers, b'{"error":"Log files unavailable"}'
    headers.append(("ETag", etag))
    if data is None:
        return "304 Not Modified", headers, b""
    return "200 OK", headers, json.dumps(data, ensure_ascii=False).encode()

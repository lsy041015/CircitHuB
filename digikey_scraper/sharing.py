import json
import os
import re
import socket
from datetime import datetime
from pathlib import Path

from .constants import SHARE_DIR

MAX_SHARE_BYTES = 5 * 1024 * 1024
MAX_METADATA_BYTES = 64 * 1024
DEFAULT_SHARE_BIND_HOST = os.environ.get("DIGIKEY_SHARE_BIND_HOST", "127.0.0.1")


def safe_filename(filename: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
    filename = re.sub(r"\s+", "_", filename).strip("._")
    return filename or "digikey_specs.txt"


def unique_path(directory: Path, filename: str) -> Path:
    base = directory / safe_filename(filename)
    if not base.exists():
        return base
    stem = base.stem or "digikey_specs"
    suffix = base.suffix
    for index in range(1, 1000):
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return directory / f"{stem}_{timestamp}{suffix}"


def recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ConnectionError("연결이 중간에 끊겼습니다.")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def save_shared_text(filename: str, text: str) -> Path:
    SHARE_DIR.mkdir(parents=True, exist_ok=True)
    path = unique_path(SHARE_DIR, filename)
    path.write_text(text, encoding="utf-8")
    return path


def send_shared_text(peer_ip: str, port: int, filename: str, text: str) -> None:
    payload = text.encode("utf-8")
    if len(payload) > MAX_SHARE_BYTES:
        raise ValueError("공유 파일 크기가 허용 범위를 초과했습니다.")

    metadata = json.dumps(
        {
            "filename": filename,
            "size": len(payload),
        },
        ensure_ascii=False,
    ).encode("utf-8")

    if len(metadata) > MAX_METADATA_BYTES:
        raise ValueError("공유 메타데이터 크기가 허용 범위를 초과했습니다.")

    with socket.create_connection((peer_ip, port), timeout=10) as connection:
        connection.sendall(len(metadata).to_bytes(4, "big"))
        connection.sendall(metadata)
        connection.sendall(payload)
        connection.settimeout(10)
        ack = connection.recv(2)
        if ack != b"OK":
            raise ConnectionError("공유 수신 확인에 실패했습니다.")


def receive_shared_text(connection: socket.socket) -> tuple[str, str]:
    metadata_size = int.from_bytes(recv_exact(connection, 4), "big")
    if metadata_size <= 0 or metadata_size > MAX_METADATA_BYTES:
        raise ValueError("공유 메타데이터 크기가 올바르지 않습니다.")

    metadata = json.loads(recv_exact(connection, metadata_size).decode("utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("공유 메타데이터 형식이 올바르지 않습니다.")
    payload_size = int(metadata["size"])
    if payload_size < 0 or payload_size > MAX_SHARE_BYTES:
        raise ValueError("공유 파일 크기가 허용 범위를 초과했습니다.")

    payload = recv_exact(connection, payload_size)
    connection.sendall(b"OK")
    filename = str(metadata.get("filename") or "digikey_specs.txt")
    return safe_filename(filename), payload.decode("utf-8")


def build_share_filename() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"digikey_specs_{timestamp}.txt"

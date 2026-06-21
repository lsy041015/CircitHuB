import ipaddress
import json
import socket
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

MAX_CHAT_BYTES = 64 * 1024


class ChatConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


def is_loopback_host(host: str) -> bool:
    host = (host or "").strip()
    if not host:
        return False
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


def peer_allowed(host: str, allowed_hosts: set[str] | None) -> bool:
    if not allowed_hosts:
        return True
    return host in allowed_hosts


@dataclass
class ChatMessage:
    kind: str
    room: str
    sender: str
    text: str
    timestamp: float
    message_id: str = ""
    payload: dict = field(default_factory=dict)
    mentions: list[str] = field(default_factory=list)
    parent_id: str = ""
    reactions: dict = field(default_factory=dict)
    read_by: list[str] = field(default_factory=list)


def _recv_exact(connection: socket.socket, size: int) -> bytes:
    chunks = []
    remaining = size
    while remaining > 0:
        chunk = connection.recv(remaining)
        if not chunk:
            raise ConnectionError("chat connection closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_frame(connection: socket.socket, payload: dict) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    if len(data) > MAX_CHAT_BYTES:
        raise ValueError("chat message is too large")
    connection.sendall(len(data).to_bytes(4, "big"))
    connection.sendall(data)


def receive_frame(connection: socket.socket) -> dict:
    size = int.from_bytes(_recv_exact(connection, 4), "big")
    if size <= 0 or size > MAX_CHAT_BYTES:
        raise ValueError("invalid chat frame size")
    return json.loads(_recv_exact(connection, size).decode("utf-8"))


def _string_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def build_message(
    kind: str,
    room: str,
    sender: str,
    text: str,
    token: str = "",
    *,
    message_id: str = "",
    payload: dict | None = None,
    mentions: list[str] | None = None,
    parent_id: str = "",
    reactions: dict | None = None,
    read_by: list[str] | None = None,
) -> dict:
    return {
        "kind": kind,
        "room": room.strip() or "general",
        "sender": sender.strip() or "anonymous",
        "text": text,
        "token": token,
        "timestamp": time.time(),
        "message_id": message_id.strip() or f"msg-{uuid4().hex}",
        "payload": payload if isinstance(payload, dict) else {},
        "mentions": _string_list(mentions),
        "parent_id": parent_id.strip(),
        "reactions": reactions if isinstance(reactions, dict) else {},
        "read_by": _string_list(read_by),
    }


def parse_message(payload: dict) -> ChatMessage:
    extra_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    return ChatMessage(
        kind=str(payload.get("kind", "message")),
        room=str(payload.get("room", "general")),
        sender=str(payload.get("sender", "anonymous")),
        text=str(payload.get("text", "")),
        timestamp=float(payload.get("timestamp", time.time())),
        message_id=str(payload.get("message_id", "")),
        payload=extra_payload,
        mentions=_string_list(payload.get("mentions")),
        parent_id=str(payload.get("parent_id", "")),
        reactions=payload.get("reactions") if isinstance(payload.get("reactions"), dict) else {},
        read_by=_string_list(payload.get("read_by")),
    )


class ChatServer:
    def __init__(
        self,
        host: str,
        port: int,
        status_callback: Callable[[str], None] | None = None,
        token: str = "",
        allowed_hosts: set[str] | None = None,
        require_token: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.status_callback = status_callback
        self.token = token.strip()
        self.allowed_hosts = {item.strip() for item in allowed_hosts or set() if item.strip()}
        self.require_token = require_token
        self._socket: socket.socket | None = None
        self._running = False
        self._clients: dict[socket.socket, tuple[str, str]] = {}
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running:
            return
        if self.require_token and not self.token:
            raise ValueError("chat token is required")
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen()
        server.settimeout(1)
        self._socket = server
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True, name="digikey-chat-server")
        self._thread.start()
        self._emit_status(f"chat server listening on {self.host or '0.0.0.0'}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None
        with self._lock:
            clients = list(self._clients)
            self._clients.clear()
        for client in clients:
            try:
                client.close()
            except OSError:
                pass

    def _serve(self) -> None:
        while self._running and self._socket is not None:
            try:
                connection, addr = self._socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            peer_ip = str(addr[0])
            if not peer_allowed(peer_ip, self.allowed_hosts):
                self._emit_status(f"chat rejected peer: {peer_ip}")
                try:
                    connection.close()
                except OSError:
                    pass
                continue
            threading.Thread(target=self._handle_client, args=(connection,), daemon=True).start()

    def _handle_client(self, connection: socket.socket) -> None:
        nickname = "anonymous"
        room = "general"
        try:
            join = receive_frame(connection)
            if join.get("kind") != "join":
                raise ValueError("first chat frame must be join")
            if (self.token or self.require_token) and str(join.get("token", "")) != self.token:
                raise PermissionError("invalid chat token")
            nickname = str(join.get("sender") or "anonymous").strip() or "anonymous"
            room = str(join.get("room") or "general").strip() or "general"
            with self._lock:
                self._clients[connection] = (nickname, room)
            self._broadcast(build_message("system", room, "server", f"{nickname} joined"), room)

            while self._running:
                payload = receive_frame(connection)
                kind = payload.get("kind")
                if kind == "room_switch":
                    next_room = str(payload.get("room") or "general").strip() or "general"
                    if next_room != room:
                        old_room = room
                        room = next_room
                        with self._lock:
                            self._clients[connection] = (nickname, room)
                        self._broadcast(build_message("system", old_room, "server", f"{nickname} left"), old_room)
                        self._broadcast(build_message("system", room, "server", f"{nickname} joined"), room)
                    continue
                if kind != "message":
                    continue
                text = str(payload.get("text", "")).strip()
                extra_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
                if text or extra_payload:
                    self._broadcast(
                        build_message(
                            "message",
                            room,
                            nickname,
                            text,
                            message_id=str(payload.get("message_id", "")),
                            payload=extra_payload,
                            mentions=_string_list(payload.get("mentions")),
                            parent_id=str(payload.get("parent_id", "")),
                            reactions=payload.get("reactions") if isinstance(payload.get("reactions"), dict) else {},
                            read_by=_string_list(payload.get("read_by")),
                        ),
                        room,
                    )
        except Exception as exc:
            self._emit_status(f"chat client disconnected: {exc}")
        finally:
            with self._lock:
                known = self._clients.pop(connection, None)
            try:
                connection.close()
            except OSError:
                pass
            if known is not None:
                self._broadcast(build_message("system", room, "server", f"{nickname} left"), room)

    def _broadcast(self, payload: dict, room: str) -> None:
        stale = []
        with self._lock:
            targets = [(client, info) for client, info in self._clients.items() if info[1] == room]
        for client, _info in targets:
            try:
                send_frame(client, payload)
            except OSError:
                stale.append(client)
        if stale:
            with self._lock:
                for client in stale:
                    self._clients.pop(client, None)

    def _emit_status(self, message: str) -> None:
        if self.status_callback is not None:
            self.status_callback(message)


class ChatClient:
    def __init__(
        self,
        host: str,
        port: int,
        nickname: str,
        room: str,
        message_callback: Callable[[ChatMessage], None],
        status_callback: Callable[[str], None] | None = None,
        token: str = "",
    ) -> None:
        self.host = host
        self.port = port
        self.nickname = nickname.strip() or "anonymous"
        self.room = room.strip() or "general"
        self.message_callback = message_callback
        self.status_callback = status_callback
        self.token = token.strip()
        self._socket: socket.socket | None = None
        self._running = False
        self._thread: threading.Thread | None = None

    def connect(self) -> None:
        if self._running:
            return
        connection = socket.create_connection((self.host, self.port), timeout=10)
        # create_connection leaves a 10s timeout on the socket; without clearing
        # it the receive loop raises "timed out" whenever no message arrives for
        # 10 seconds. Restore blocking mode so the connection stays open while idle.
        connection.settimeout(None)
        send_frame(connection, build_message("join", self.room, self.nickname, "", self.token))
        self._socket = connection
        self._running = True
        self._thread = threading.Thread(target=self._receive_loop, daemon=True, name="digikey-chat-client")
        self._thread.start()
        self._emit_status(f"chat connected to {self.host}:{self.port}")

    def send(
        self,
        text: str,
        *,
        payload: dict | None = None,
        mentions: list[str] | None = None,
        parent_id: str = "",
    ) -> None:
        if self._socket is None:
            raise ConnectionError("chat client is not connected")
        text = text.strip()
        has_payload = isinstance(payload, dict) and bool(payload)
        if text or has_payload:
            send_frame(
                self._socket,
                build_message(
                    "message",
                    self.room,
                    self.nickname,
                    text,
                    payload=payload,
                    mentions=mentions,
                    parent_id=parent_id,
                ),
            )
            self._running = True

    def switch_room(self, room: str) -> None:
        if self._socket is None:
            raise ConnectionError("chat client is not connected")
        next_room = room.strip() or "general"
        if next_room == self.room:
            return
        send_frame(self._socket, build_message("room_switch", next_room, self.nickname, ""))
        self.room = next_room

    def close(self) -> None:
        self._running = False
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass
            self._socket = None

    def _receive_loop(self) -> None:
        try:
            while self._running and self._socket is not None:
                self.message_callback(parse_message(receive_frame(self._socket)))
        except Exception as exc:
            if self._running:
                self._emit_status(f"chat disconnected: {exc}")
        finally:
            self._running = False

    def _emit_status(self, message: str) -> None:
        if self.status_callback is not None:
            self.status_callback(message)

"""Local-network spec sharing (TCP send/receive) for MainWindow, as a mixin.

Extracted from _main_window. Methods rely on MainWindow attributes
(receiver_socket, ui_signals, peer_ip, share_port, ...) and helpers
(_tr, set_status, get_share_port, get_result_text, switch_tab).
"""

from __future__ import annotations

import socket
import threading
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from .constants import DEFAULT_SHARE_PORT
from .sharing import (
    DEFAULT_SHARE_BIND_HOST,
    build_share_filename,
    receive_shared_text,
    save_shared_text,
    send_shared_text,
)


class SharingMixin:
    def start_receiver(self):
        if self.receiver_running:
            return
        try:
            port = self.get_share_port()
        except ValueError:
            port = DEFAULT_SHARE_PORT
            self.share_port.setText(str(DEFAULT_SHARE_PORT))
        srv = None
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((DEFAULT_SHARE_BIND_HOST, port))
            srv.listen()
            srv.settimeout(1)
        except OSError as exc:
            if srv is not None:
                try:
                    srv.close()
                except OSError:
                    pass
            self.set_status(self._tr("receiver_start_failed", error=exc))
            return
        self.receiver_socket = srv
        self.receiver_running = True
        threading.Thread(target=self.receiver_loop, daemon=True).start()
        self.set_status(self._tr("receiver_waiting", port=port))

    def restart_receiver(self):
        self.stop_receiver()
        self.start_receiver()

    def stop_receiver(self):
        self.receiver_running = False
        if self.receiver_socket:
            try:
                self.receiver_socket.close()
            except OSError:
                pass
            self.receiver_socket = None

    def receiver_loop(self):
        while self.receiver_running and self.receiver_socket:
            try:
                conn, addr = self.receiver_socket.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle_recv, args=(conn, addr), daemon=True).start()

    def _handle_recv(self, conn, addr):
        with conn:
            try:
                filename, text = receive_shared_text(conn)
                saved = save_shared_text(filename, text)
            except Exception as exc:
                self.ui_signals.status_key.emit("receiver_failed", {"error": str(exc)})
                return
        self.ui_signals.received_share.emit(addr[0], str(saved), text)

    def show_received_share(self, ip: str, saved_path: str, text: str):
        self.latest_share_text = text
        self.results = []
        self.text_result.setPlainText(text)
        self.switch_tab("text")
        self.set_status(self._tr("receiver_done", ip=ip, name=Path(saved_path).name))

    def start_send_share(self):
        peer = self.peer_ip.text().strip()
        if not peer:
            QMessageBox.warning(
                self, self._tr("peer_required_title"), self._tr("peer_required_message")
            )
            return
        text = self.get_result_text()
        if not text:
            QMessageBox.warning(self, self._tr("no_share_title"), self._tr("no_share_message"))
            return
        try:
            port = self.get_share_port()
        except ValueError as exc:
            QMessageBox.warning(self, self._tr("input_error_title"), str(exc))
            return
        self.set_status(self._tr("send_in_progress", peer=peer, port=port))
        threading.Thread(target=self._send_worker, args=(peer, port, text), daemon=True).start()

    def _send_worker(self, peer: str, port: int, text: str):
        fn = build_share_filename()
        try:
            save_shared_text(fn, text)
            send_shared_text(peer, port, fn, text)
        except Exception as exc:
            self.ui_signals.status_key.emit("send_failed", {"error": str(exc)})
            return
        self.ui_signals.status_key.emit("send_done", {"peer": peer, "port": port})

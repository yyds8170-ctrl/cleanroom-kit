"""最小 WebSocket 客户端（仅标准库：socket/base64/hashlib/struct/os）。
足以连接 Chrome DevTools Protocol 并收发文本帧。
"""
import base64
import hashlib
import os
import socket
import struct


class WebSocket:
    def __init__(self, url, timeout=15):
        self.url = url
        assert url.startswith("ws://"), "仅支持 ws://（本地调试端口）"
        rest = url[5:]
        host_port, _, path = rest.partition("/")
        self.path = "/" + path
        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host, port = host_port, 80
        self.sock = socket.create_connection((host, port), timeout=timeout)

        key = base64.b64encode(os.urandom(16)).decode()
        handshake = (
            f"GET {self.path} HTTP/1.1\r\nHost: {host_port}\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            resp += self.sock.recv(4096)
        if b" 101 " not in resp.split(b"\r\n")[0]:
            raise ConnectionError("WebSocket 握手失败：" + resp.split(b"\r\n")[0].decode())
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()
        ).decode()
        if expected.encode() not in resp:
            raise ConnectionError("WebSocket 接受校验失败")
        self._buf = b""

    def _recv_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("连接已关闭")
            data += chunk
        return data

    def send_text(self, text):
        payload = text.encode("utf-8")
        header = bytearray([0x81])  # FIN + text
        mask_key = os.urandom(4)
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", length)
        header += mask_key
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def recv_text(self):
        buf = b""
        while True:
            b1, b2 = self._recv_exact(2)
            opcode = b1 & 0x0F
            fin = b1 & 0x80
            length = b2 & 0x7F
            if length == 126:
                length = struct.unpack(">H", self._recv_exact(2))[0]
            elif length == 127:
                length = struct.unpack(">Q", self._recv_exact(8))[0]
            payload = self._recv_exact(length) if length else b""

            if opcode == 0x9:  # ping -> pong
                self._send_pong(payload)
                continue
            if opcode == 0xA:  # pong
                continue
            if opcode == 0x8:  # close
                raise ConnectionError("对端关闭连接")
            if opcode == 0x2:  # 二进制帧
                raise ConnectionError("收到二进制帧（opcode 0x2），当前 WebSocket 客户端仅支持文本帧")
            if opcode == 0x1:  # 文本首帧
                buf = payload
            elif opcode == 0x0:  # 续帧
                buf += payload
            else:
                raise ConnectionError(f"不支持的帧 opcode {opcode}")
            if fin:
                return buf.decode("utf-8", errors="replace")

    def _send_pong(self, payload):
        mask_key = os.urandom(4)
        header = bytearray([0x8A, 0x80 | len(payload)]) + mask_key
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + masked)

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass

"""Limite de corpo antes dos middlewares que leem JSON ou assinam escritas."""

import json

from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestBodyLimitMiddleware:
    """Buffer limitado para escritas; rejeita excesso com 413 e fecha a conexão."""

    def __init__(self, app: ASGIApp, max_bytes: int = 1024 * 1024):
        if max_bytes <= 0:
            raise ValueError("max_bytes deve ser positivo")
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") not in {
            "POST", "PUT", "PATCH", "DELETE"
        }:
            await self.app(scope, receive, send)
            return

        content_length = Headers(scope=scope).get("content-length")
        if content_length is not None:
            try:
                declarado = int(content_length)
            except ValueError:
                await self._responder(send, 400, "Content-Length inválido")
                return
            if declarado < 0:
                await self._responder(send, 400, "Content-Length inválido")
                return
            if declarado > self.max_bytes:
                await self._responder(
                    send, 413, f"Corpo da requisição excede {self.max_bytes} bytes"
                )
                return

        partes: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            corpo = message.get("body", b"")
            total += len(corpo)
            if total > self.max_bytes:
                await self._responder(
                    send, 413, f"Corpo da requisição excede {self.max_bytes} bytes"
                )
                return
            partes.append(corpo)
            if not message.get("more_body", False):
                break

        corpo_completo = b"".join(partes)
        enviado = False

        async def replay() -> Message:
            nonlocal enviado
            if not enviado:
                enviado = True
                return {"type": "http.request", "body": corpo_completo, "more_body": False}
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, replay, send)

    async def _responder(self, send: Send, status: int, detail: str) -> None:
        corpo = json.dumps({"detail": detail}).encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(corpo)).encode()),
                (b"cache-control", b"no-store"),
                (b"x-content-type-options", b"nosniff"),
                (b"x-frame-options", b"DENY"),
                (b"connection", b"close"),
            ],
        })
        await send({"type": "http.response.body", "body": corpo})

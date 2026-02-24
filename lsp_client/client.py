import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from .protocol import BaseRequest
from .utils import (
    DEFAULT_ENCODING,
    DEFAULT_CONTENT_MIME_TYPE,
    EncodingError,
    parse_content_type,
)

DEFAULT_CONTENT_TYPE = DEFAULT_CONTENT_MIME_TYPE

SEPARATOR = "\r\n"

# Next request ID — managed here rather than in BaseRequest to keep protocol
# objects pure data and avoid global mutable state in protocol.py.
_next_request_id: int = 0


def _allocate_request_id() -> int:
    global _next_request_id
    _next_request_id += 1
    return _next_request_id


class LSPClient(object):
    """
    An asynchronous client implementation for the Language Server Protocol.
    """

    stdin: asyncio.StreamWriter | None
    stdout: asyncio.StreamReader | None
    response_handler: Callable[[dict[Any, Any]], Coroutine[Any, Any, None]]

    def __init__(
        self,
        stdin: asyncio.StreamWriter | None,
        stdout: asyncio.StreamReader | None,
        response_handler: Callable[[dict[Any, Any]], Coroutine[Any, Any, None]],
        logger: logging.Logger | None = None,
    ) -> None:
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.response_handler = response_handler
        self.stdin = stdin
        self.stdout = stdout

    async def send_request(self, request: BaseRequest) -> None:
        """
        Send a request to the LSP server.

        Args:
            request: A BaseRequest object representing the request.
        """
        await self._send_request(request.model_dump())

    def build_request(
        self, request_cls: type[BaseRequest], **kwargs: Any
    ) -> BaseRequest:
        """
        Construct a request with a server-assigned ID.

        Prefer this over constructing requests directly so that ID management
        stays centralised in LSPClient.
        """
        return request_cls(id=_allocate_request_id(), **kwargs)

    async def _send_request(self, request: dict) -> None:
        """
        Serialise and write a request to the LSP server.

        Args:
            request: A dictionary representing the request.
        """
        request_string = json.dumps(request)
        request_bytes = request_string.encode(DEFAULT_ENCODING)
        header_string = f"Content-Length: {len(request_bytes)}{SEPARATOR}"
        # Use the shared constant from utils rather than a local copy
        header_string += (
            f"Content-Type: {DEFAULT_CONTENT_MIME_TYPE}; charset={DEFAULT_ENCODING}"
        )
        header_string += f"{SEPARATOR}{SEPARATOR}"
        header_bytes = header_string.encode(DEFAULT_ENCODING)

        await self._async_write_request(header_bytes, request_bytes)

    async def listen(self) -> None:
        """
        Continuously read and dispatch responses from the LSP server until the
        connection is closed or the task is cancelled.
        """
        try:
            while True:
                await self.read_response()
        except asyncio.CancelledError:
            self.logger.debug("LSPClient.listen() cancelled — shutting down.")
            raise

    async def read_response(self) -> None:
        """
        Read a single response from the LSP server and dispatch it.
        """
        content_length = 0
        content_type = None

        # Read headers until the blank separator line.
        while True:
            line = await self._async_read_line()
            # Strip \r\n / \n so header parsing is not sensitive to line endings.
            decoded_line = line.decode(DEFAULT_ENCODING).rstrip("\r\n")
            if decoded_line.startswith("Content-Length:"):
                content_length = int(decoded_line.split(":", 1)[1].strip())
            elif decoded_line.startswith("Content-Type:"):
                content_type = decoded_line.split(":", 1)[1].strip()
            elif decoded_line == "":
                break

        try:
            content_type, encoding = parse_content_type(content_type)
        except EncodingError as e:
            self.logger.warning("Unrecognised encoding, skipping message: %s", e)
            return
        except ValueError as e:
            self.logger.warning("Unsupported content type, skipping message: %s", e)
            return

        response = await self._async_read(content_length)
        decoded_response = response.decode(encoding)
        response = json.loads(decoded_response)
        await self._handle_response(response)

    async def _async_write_request(
        self, header_bytes: bytes, request_bytes: bytes
    ) -> None:
        """
        Write header and body bytes to the LSP server subprocess.
        """
        assert self.stdin is not None
        self.stdin.write(header_bytes)
        self.stdin.write(request_bytes)
        await self.stdin.drain()

    async def _async_read(self, content_length: int) -> bytes:
        """
        Read exactly `content_length` bytes from the server, handling partial
        reads caused by system buffer limits.
        """
        assert self.stdout is not None
        response = await self.stdout.read(content_length)
        while len(response) < content_length:
            remaining_length = content_length - len(response)
            response += await self.stdout.read(remaining_length)
        return response

    async def _async_read_line(self) -> bytes:
        """
        Read one line (up to and including the newline) from the server.
        """
        assert self.stdout is not None
        return await self.stdout.readline()

    async def _handle_response(self, response: dict) -> None:
        """
        Delegate a parsed response to the registered response handler.
        """
        await self.response_handler(response)

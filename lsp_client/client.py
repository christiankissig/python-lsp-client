import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from .protocol import BaseNotification, BaseRequest
from .utils import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_ENCODING,
    EncodingError,
    parse_content_type,
)

SEPARATOR = "\r\n"


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
        self._next_request_id: int = 0

    def _allocate_request_id(self) -> int:
        self._next_request_id += 1
        return self._next_request_id

    async def send_request(self, request: BaseRequest) -> None:
        """
        Send a request to the LSP server.

        Args:
            request: A BaseRequest object representing the request.
        """
        if request.id is None:
            request.id = self._allocate_request_id()
        await self._send_request(request.model_dump())

    async def send_notification(self, notification: BaseNotification) -> None:
        """
        Send a notification to the LSP server.

        Notifications have no id and expect no response.

        Args:
            notification: A BaseNotification object representing the notification.
        """
        await self._send_request(notification.model_dump(exclude_none=True))

    def build_request(
        self, request_cls: type[BaseRequest], **kwargs: Any
    ) -> BaseRequest:
        """
        Construct a request with a server-assigned ID.

        Prefer this over constructing requests directly so that ID management
        stays centralised in LSPClient.
        """
        return request_cls(id=self._allocate_request_id(), **kwargs)

    async def _send_request(self, request: dict) -> None:
        """
        Serialise and write a request to the LSP server.

        Args:
            request: A dictionary representing the request.
        """
        request_string = json.dumps(request)
        request_bytes = request_string.encode(DEFAULT_ENCODING)
        header_string = f"Content-Length: {len(request_bytes)}{SEPARATOR}"
        header_string += f"Content-Type: {DEFAULT_CONTENT_TYPE}"
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
        except EOFError:
            self.logger.info("LSPClient.listen() — server closed the connection.")
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
            if line == b"":
                raise EOFError("LSP server closed its stdout")
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
            chunk = await self.stdout.read(content_length - len(response))
            if chunk == b"":
                raise EOFError("LSP server closed its stdout mid-message")
            response += chunk
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

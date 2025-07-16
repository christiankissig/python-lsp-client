import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from .protocol import BaseRequest
from .utils import EncodingError, parse_content_type

DEFAULT_ENCODING = "utf-8"
DEFAULT_CONTENT_TYPE = "application/vscode-jsonrpc"
SEPARATOR = "\r\n"


class LSPClient(object):
    """
    An asynchronous client implementation for the Language Server Protocol.
    """

    request_id: int
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
        self.request_id = 0
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

    async def _send_request(self, request: dict) -> None:
        """
        Send a request to the LSP server.

        Args:
            request: A dictionary representing the request.
        """
        request_string = json.dumps(request)
        request_bytes = request_string.encode(DEFAULT_ENCODING)
        header_string = f"Content-Length: {len(request_bytes)}{SEPARATOR}"
        header_string += f"Content-Type: {DEFAULT_CONTENT_TYPE}"
        if DEFAULT_ENCODING:
            header_string += f"; charset={DEFAULT_ENCODING}"
        header_string += f"{SEPARATOR}{SEPARATOR}"
        header_bytes = header_string.encode(DEFAULT_ENCODING)

        await self._async_write_request(header_bytes, request_bytes)

    async def read_response(self) -> None:
        """
        Read response asynchronously and handle methods.
        """
        content_length = 0
        content_type = None
        # read headers
        while True:
            line = await self._async_read_line()
            decoded_line = line.decode(DEFAULT_ENCODING)
            if decoded_line.startswith("Content-Length:"):
                content_length = int(decoded_line.split(":")[1].strip())
            elif decoded_line.startswith("Content-Type:"):
                content_type = decoded_line.split(":")[1].strip()
            elif decoded_line.strip() == "":
                break

        try:
            content_type, encoding = parse_content_type(content_type)
        except EncodingError as e:
            self.logger.warn(e)
            return

        response = await self._async_read(content_length)
        decoded_response = response.decode(encoding)
        response = json.loads(decoded_response)
        await self._handle_response(response)

    async def _async_write_request(
        self, header_bytes: bytes, request_bytes: bytes
    ) -> None:
        """
        Implements asynchronous writing to the LSP server subprocess.
        """
        assert self.stdin is not None
        self.stdin.write(header_bytes)
        self.stdin.write(request_bytes)
        await self.stdin.drain()

    async def _async_read(self, content_length: int) -> bytes:
        """
        Implements asynchronous reading from STDIN of the subprocess.

        Accounts for system buffer.
        """
        assert self.stdout is not None
        response = await self.stdout.read(content_length)
        while len(response) < content_length:
            remaining_length = content_length - len(response)
            response += await self.stdout.read(remaining_length)
        return response

    async def _async_read_line(self) -> bytes:
        """
        Implements asynchronous reading of a line from STDIN of the subprocess.
        """
        assert self.stdout is not None
        return await self.stdout.readline()

    async def _handle_response(self, response: dict) -> None:
        """
        Delegate response to method handlers from the LSP server.
        """
        await self.response_handler(response)

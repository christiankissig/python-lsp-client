import asyncio
import json
import subprocess
import logging

from .protocol import BaseRequest
from .utils import parse_content_type, EncodingError

DEFAULT_ENCODING = "utf-8"
DEFAULT_CONTENT_TYPE = "application/vscode-jsonrpc"
SEPARATOR = "\r\n"


class BaseLSPClient:
    """
    A base class for LSP clients.
    """

    def __init__(
        self,
        executable: str,
        server_args: list[str] = [],
        method_handlers: dict[str, callable] = {},
        logger: logging.Logger | None = None
    ):
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.executable = executable
        self.server_args = server_args
        self.method_handlers = method_handlers
        self.id = 0
        self.process = None

    def _send_request(self, request: dict):
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

        payload = header_string + request_string
        if len(payload) > 100:
            message = f"sending: {payload[:100]}..."
        else:
            message = f"sending: {payload}"
        self.logger.info(message)

        self._write_request(header_bytes, request_bytes)

    def send_request(self, request: BaseRequest) -> None:
        """
        Send a request to the LSP server.

        Args:
            request: A request object.
        """
        self._send_request(request.to_dict())

    async def _async_read_response(self):
        """
        Read response asynchronously and handle methods.
        """
        content_length = 0
        content_type = None
        # read headers
        while True:
            line = await self._async_read_line()
            decoded_line = line.decode(DEFAULT_ENCODING)
            if decoded_line.startswith('Content-Length:'):
                content_length = int(decoded_line.split(':')[1].strip())
            elif decoded_line.startswith('Content-Type:'):
                content_type = decoded_line.split(':')[1].strip()
            elif decoded_line.strip() == '':
                break

        try:
            content_type, encoding = parse_content_type(content_type)
        except EncodingError as e:
            self.logger.warn(e)
            return

        response = await self._async_read(content_length)
        decoded_response = response.decode(encoding)
        response = json.loads(decoded_response)
        self._handle_response(response)

    def _handle_response(self, response: dict):
        """
        Delegate response to method handlers from the LSP server.
        """
        if "method" in response and response["method"] in self.method_handlers:
            method = response["method"]
            self.method_handlers[method](response)
        else:
            if "method" in response:
                message = f"Unhandled response for method {response['method']}"
            else:
                message = f"Unhandled response: {response}"
            self.logger.info(message)

    async def _read_response(self):
        """
        Read response and handle methods.

        Currently shadows _async_read_response.
        """
        await self._async_read_response()

    def _write_request(self, header_bytes, request_bytes) -> None:
        """
        Writes a request to the LSP server.

        Implemented by concrete client implementation.
        """
        raise NotImplementedError

    async def _async_read_line(self):
        """
        Reads a line asynchronously from the LSP server.

        Implemented by concrete client implementation.
        """
        raise NotImplementedError

    async def _async_read(self, content_length: int) -> bytes:
        """
        Reads asynchronously from the LSP server.

        Implemented by concrete client implementation.
        """
        raise NotImplementedError


class STDIOLSPClient(BaseLSPClient):
    """
    A client implementation for Language Server Protocol over std I/O.
    """

    def __init__(
        self,
        executable: str,
        server_args: list[str] = [],
        callbacks: dict[str, callable] = {}
    ):
        super().__init__(executable, server_args, callbacks)

    async def start(self):
        """
        Start the LSP server as a subprocess.
        """
        program = [self.executable] + self.server_args
        self.logger.info("Starting " + " ".join(program))
        self.process = await asyncio.create_subprocess_exec(
            *program,
            stdin=subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            bufsize=0
        )

    def _write_request(self, header_bytes, request_bytes):
        """
        Implements synchronous writing to the LSP server subprocess.
        """
        self.process.stdin.write(header_bytes)
        self.process.stdin.write(request_bytes)

    async def _async_read(self, content_length: int) -> bytes:
        """
        Implements asynchronous reading from STDIN of the subprocess.

        Accounts for system buffer.
        """
        response = await self.process.stdout.read(content_length)
        while len(response) < content_length:
            remaining_length = content_length - len(response)
            response += await self.process.stdout.read(remaining_length)
        return response

    async def _async_read_line(self):
        """
        Implements asynchronous reading of a line from STDIN of the subprocess.
        """
        return await self.process.stdout.readline()

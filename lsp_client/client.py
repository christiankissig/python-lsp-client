import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from .protocol import (
    BaseNotification,
    BaseRequest,
    CancelRequest,
    LSPError,
    ResponseError,
)
from .utils import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_ENCODING,
    EncodingError,
    parse_content_type,
)

SEPARATOR = "\r\n"

#: Sentinel marking "no explicit timeout argument" so ``None`` can mean "wait
#: forever" distinctly from "fall back to the client default".
_UNSET: Any = object()


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
        request_timeout: float | None = None,
    ) -> None:
        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger
        self.response_handler = response_handler
        self.stdin = stdin
        self.stdout = stdout
        self._next_request_id: int = 0
        #: Default timeout (seconds) applied to ``request()`` when the caller
        #: does not pass one. ``None`` means wait indefinitely.
        self.request_timeout = request_timeout
        #: In-flight requests awaiting a response, keyed by request id.
        self._pending_requests: dict[int | str, asyncio.Future[Any]] = {}

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

    async def request(
        self,
        request: BaseRequest,
        timeout: float | None = _UNSET,
    ) -> Any:
        """
        Send a request and await its result.

        Unlike :meth:`send_request` (fire-and-forget), this correlates the
        response by id and returns the response ``result``. On a
        ``ResponseError`` it raises :class:`LSPError`. If no response arrives
        within ``timeout`` seconds a ``$/cancelRequest`` is sent to the server
        and ``asyncio.TimeoutError`` is raised.

        Args:
            request: The request to send. An id is assigned if it has none.
            timeout: Seconds to wait for a response. Omit to use the client's
                ``request_timeout``; pass ``None`` to wait indefinitely.

        Returns:
            The response ``result`` (which may be ``None``).
        """
        if request.id is None:
            request.id = self._allocate_request_id()
        if timeout is _UNSET:
            timeout = self.request_timeout

        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending_requests[request.id] = future

        try:
            await self._send_request(request.model_dump(exclude_none=True))
            if timeout is None:
                return await future
            return await asyncio.wait_for(future, timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            # The caller will no longer consume the result; tell the server to
            # stop computing it. Best-effort — ignore send failures.
            await self._safe_cancel(request.id)
            raise
        finally:
            self._pending_requests.pop(request.id, None)

    async def cancel_request(self, request_id: int | str) -> None:
        """
        Send a ``$/cancelRequest`` notification for an in-flight request.

        ``$/cancelRequest`` is a notification, so it carries no id of its own;
        ``exclude_none`` drops the unset id from the serialised message.
        """
        cancel = CancelRequest(params={"id": request_id})
        await self._send_request(cancel.model_dump(exclude_none=True))

    async def _safe_cancel(self, request_id: int | str) -> None:
        """Send a cancellation, swallowing any error (e.g. closed transport)."""
        try:
            await self.cancel_request(request_id)
        except Exception as e:  # pragma: no cover - best-effort cleanup
            self.logger.debug("Failed to send $/cancelRequest: %s", e)

    async def send_notification(self, notification: BaseNotification) -> None:
        """
        Send a notification to the LSP server.

        Notifications have no id and expect no response.

        Args:
            notification: A BaseNotification object representing the notification.
        """
        await self._send_request(notification.model_dump(exclude_none=True))

    @classmethod
    async def from_command(
        cls,
        *cmd: str,
        response_handler: Callable[[dict[Any, Any]], Coroutine[Any, Any, None]],
        logger: logging.Logger | None = None,
        request_timeout: float | None = None,
    ) -> tuple["LSPClient", asyncio.subprocess.Process]:
        """
        Spawn an LSP server subprocess and return a ready-to-use client.

        Args:
            *cmd: The command and arguments to launch the LSP server.
            response_handler: Async callable that receives each parsed response.
            logger: Optional logger; defaults to the module logger.
            request_timeout: Default timeout (seconds) for awaited requests.
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        return (
            cls(
                proc.stdin,
                proc.stdout,
                response_handler,
                logger,
                request_timeout,
            ),
            proc,
        )

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
        Dispatch a parsed message.

        Responses to requests issued via :meth:`request` are correlated by id
        and used to resolve (or reject) the awaiting future. Everything else —
        server-initiated requests, notifications, and responses with no pending
        future — is forwarded to the registered ``response_handler``.
        """
        message_id: int | str | None = response.get("id")
        if message_id is not None:
            future = self._pending_requests.get(message_id)
            if future is not None and ("result" in response or "error" in response):
                del self._pending_requests[message_id]
                if not future.done():
                    error = response.get("error")
                    if error is not None:
                        future.set_exception(LSPError(ResponseError(**error)))
                    else:
                        future.set_result(response.get("result"))
                return

        await self.response_handler(response)

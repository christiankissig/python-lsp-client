import asyncio
import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lsp_client.client import (
    DEFAULT_ENCODING,
    SEPARATOR,
    LSPClient,
)
from lsp_client.utils import DEFAULT_CONTENT_TYPE
from lsp_client.protocol import (
    HoverRequest,
    InitializedNotification,
    InitializeRequest,
    LSPError,
)


@pytest.mark.asyncio
async def test_send_request_headers():
    client = LSPClient(sys.stdin, sys.stdout, dict())
    test_request = InitializeRequest(id=0)

    with patch.object(client, "_async_write_request") as mock_write_request:
        await client.send_request(test_request)

        # Capture the header and request bytes passed to _async_write_request
        mock_write_request.assert_called_once()
        args, kwargs = mock_write_request.call_args

        header_bytes, request_bytes = args
        header_string = header_bytes.decode(DEFAULT_ENCODING)
        request_string = request_bytes.decode(DEFAULT_ENCODING)

        # Check the Content-Length header
        expected_content_length = f"Content-Length: {len(request_bytes)}{SEPARATOR}"
        assert expected_content_length in header_string
        expected_content_type = f"Content-Type: {DEFAULT_CONTENT_TYPE}{SEPARATOR}"
        assert expected_content_type in header_string

        actual_request = json.loads(request_string)
        assert actual_request == test_request.model_dump()


@pytest.mark.asyncio
async def test_send_notification_no_id():
    client = LSPClient(sys.stdin, sys.stdout, dict())
    notification = InitializedNotification()

    with patch.object(client, "_async_write_request") as mock_write_request:
        await client.send_notification(notification)

        mock_write_request.assert_called_once()
        args, _ = mock_write_request.call_args
        _, request_bytes = args
        actual = json.loads(request_bytes.decode(DEFAULT_ENCODING))

        assert actual["method"] == "initialized"
        assert actual["jsonrpc"] == "2.0"
        assert "id" not in actual


def test_request_id_per_instance():
    client_a = LSPClient(None, None, dict())
    client_b = LSPClient(None, None, dict())

    assert client_a._allocate_request_id() == 1
    assert client_a._allocate_request_id() == 2
    assert client_b._allocate_request_id() == 1  # independent counter


@pytest.mark.asyncio
async def test_listen_exits_cleanly_on_eof():
    reader = asyncio.StreamReader()
    reader.feed_eof()

    client = LSPClient(None, reader, dict())
    await client.listen()  # must return without raising


@pytest.mark.asyncio
async def test_from_command_wires_streams():
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock(spec=asyncio.StreamWriter)
    mock_proc.stdout = MagicMock(spec=asyncio.StreamReader)

    async def handler(response: dict) -> None:
        pass

    with patch(
        "asyncio.create_subprocess_exec", new=AsyncMock(return_value=mock_proc)
    ) as mock_exec:
        client, proc = await LSPClient.from_command("pylsp", response_handler=handler)

        mock_exec.assert_called_once_with(
            "pylsp",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert client.stdin is mock_proc.stdin
        assert client.stdout is mock_proc.stdout
        assert proc is mock_proc


async def _noop_handler(response: dict) -> None:
    pass


@pytest.mark.asyncio
async def test_request_resolves_by_id():
    client = LSPClient(None, None, _noop_handler)

    with patch.object(client, "_send_request", new=AsyncMock()):
        task = asyncio.ensure_future(client.request(HoverRequest()))
        await asyncio.sleep(0)  # let request register its future

        # Server replies with the result for the allocated id.
        [(request_id, _)] = client._pending_requests.items()
        await client._handle_response(
            {"jsonrpc": "2.0", "id": request_id, "result": {"contents": "hi"}}
        )

        result = await task
        assert result == {"contents": "hi"}
        # Pending entry is cleaned up.
        assert client._pending_requests == {}


@pytest.mark.asyncio
async def test_request_propagates_response_error():
    client = LSPClient(None, None, _noop_handler)

    with patch.object(client, "_send_request", new=AsyncMock()):
        task = asyncio.ensure_future(client.request(HoverRequest()))
        await asyncio.sleep(0)
        [request_id] = list(client._pending_requests)

        await client._handle_response(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "method not found"},
            }
        )

        with pytest.raises(LSPError) as exc:
            await task
        assert exc.value.code == -32601
        assert exc.value.message == "method not found"


@pytest.mark.asyncio
async def test_request_times_out_and_cancels():
    client = LSPClient(None, None, _noop_handler)

    with patch.object(client, "_send_request", new=AsyncMock()) as mock_send:
        with pytest.raises(asyncio.TimeoutError):
            await client.request(HoverRequest(), timeout=0.01)

        # A $/cancelRequest was sent for the timed-out request.
        sent_methods = [call.args[0]["method"] for call in mock_send.call_args_list]
        assert "$/cancelRequest" in sent_methods
        # No leaked pending future.
        assert client._pending_requests == {}


@pytest.mark.asyncio
async def test_default_request_timeout_used():
    client = LSPClient(None, None, _noop_handler, request_timeout=0.01)

    with patch.object(client, "_send_request", new=AsyncMock()):
        with pytest.raises(asyncio.TimeoutError):
            await client.request(HoverRequest())


@pytest.mark.asyncio
async def test_unmatched_response_forwarded_to_handler():
    received = []

    async def handler(response: dict) -> None:
        received.append(response)

    client = LSPClient(None, None, handler)

    # A server-initiated request (no pending future) goes to the handler.
    message = {"jsonrpc": "2.0", "id": 99, "method": "window/showMessageRequest"}
    await client._handle_response(message)
    assert received == [message]

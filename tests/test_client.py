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
from lsp_client.protocol import InitializeRequest, InitializedNotification


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

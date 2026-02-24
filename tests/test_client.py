import json
import sys
from unittest.mock import patch

import pytest

from lsp_client.client import (
    DEFAULT_CONTENT_TYPE,
    DEFAULT_ENCODING,
    SEPARATOR,
    LSPClient,
)
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
        expected_content_type = f"Content-Type: {DEFAULT_CONTENT_TYPE}; charset={DEFAULT_ENCODING}{SEPARATOR}"
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

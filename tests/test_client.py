import json

from lsp_client.client import BaseLSPClient, DEFAULT_ENCODING, SEPARATOR, DEFAULT_CONTENT_TYPE
from unittest.mock import patch


def test_send_request_headers():
    client = BaseLSPClient("")
    test_request = {'jsonrpc': '2.0', 'method': 'initialize', 'params': {}, 'id': 1}

    with patch.object(client, '_write_request') as mock_write_request:
        client._send_request(test_request)

        # Capture the header and request bytes passed to _write_request
        mock_write_request.assert_called_once()
        args, kwargs = mock_write_request.call_args

        header_bytes, request_bytes = args
        header_string = header_bytes.decode(DEFAULT_ENCODING)
        request_string = request_bytes.decode(DEFAULT_ENCODING)

        # Check the Content-Length header
        expected_content_length = f'Content-Length: {len(request_bytes)}{SEPARATOR}'
        assert expected_content_length in header_string
        expected_content_type = f'Content-Type: {DEFAULT_CONTENT_TYPE}; charset={DEFAULT_ENCODING}{SEPARATOR}'
        assert expected_content_type in header_string

        actual_request = json.loads(request_string)
        assert actual_request == test_request

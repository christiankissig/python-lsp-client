from lsp_client.protocol import (
    CancelRequest,
)


def test_cancel_request_todict():
    cancel_request = CancelRequest(language="python", id=1)

    assert cancel_request.model_dump(exclude_none=True) == {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "python/cancelRequest",
        }

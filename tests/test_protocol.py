from lsp_client.protocol import (
    CancelRequest,
)


def test_cancel_request_todict():
    cancel_request = CancelRequest(language="python", id=1)
    assert cancel_request.to_dict()["method"] == "python/cancelRequest"
    assert cancel_request.to_dict()["params"]["id"] == 1

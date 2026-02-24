from lsp_client.protocol import CancelRequest, InitializedNotification


def test_cancel_request_todict():
    cancel_request = CancelRequest(language="python", id=1)

    assert cancel_request.model_dump(exclude_none=True) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "python/cancelRequest",
    }


def test_initialized_notification_no_id():
    notification = InitializedNotification()

    data = notification.model_dump(exclude_none=True)
    assert data == {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    assert "id" not in data


def test_initialized_notification_method():
    notification = InitializedNotification()
    assert notification.method == "initialized"

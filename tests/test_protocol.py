from lsp_client.protocol import (
    CancelRequest,
    ClientInfo,
    CompletionRequest,
    ContentChange,
    DefinitionRequest,
    ExitNotification,
    HoverRequest,
    InitializeParams,
    InitializeRequest,
    InitializedNotification,
    Position,
    ProgressNotification,
    Range,
    ShutdownRequest,
    TextDocumentDidChangeNotification,
    TextDocumentDidCloseNotification,
    TextDocumentDidOpenNotification,
    TextDocumentIdentifier,
    TextDocumentPositionParams,
)


def test_cancel_request_todict():
    cancel_request = CancelRequest(id=1)

    assert cancel_request.model_dump(exclude_none=True) == {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "$/cancelRequest",
    }


def test_initialized_notification_no_id():
    notification = InitializedNotification()

    data = notification.model_dump(exclude_none=True)
    assert data == {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    assert "id" not in data


def test_initialized_notification_method():
    notification = InitializedNotification()
    assert notification.method == "initialized"


def test_did_open_notification_no_id():
    notification = TextDocumentDidOpenNotification()
    data = notification.model_dump(exclude_none=True)
    assert "id" not in data
    assert data["method"] == "textDocument/didOpen"


def test_did_change_notification_no_id():
    change = ContentChange(
        text="hello",
        range=Range(
            start=Position(line=0, character=0), end=Position(line=0, character=5)
        ),
    )
    notification = TextDocumentDidChangeNotification(
        uri="file:///tmp/test.py", version=1, contentChanges=[change]
    )
    data = notification.model_dump(exclude_none=True)
    assert "id" not in data
    assert data["method"] == "textDocument/didChange"


def test_progress_notification_no_id():
    notification = ProgressNotification()
    data = notification.model_dump(exclude_none=True)
    assert "id" not in data
    assert data["method"] == "$/progress"


def test_content_change_range_optional():
    change = ContentChange(text="hello world")
    data = change.model_dump(exclude_none=True)
    assert data == {"text": "hello world"}
    assert "range" not in data


def test_initialize_request_with_params():
    params = InitializeParams(
        processId=1234,
        clientInfo=ClientInfo(name="test-client"),
        rootUri="file:///tmp",
    )
    request = InitializeRequest(id=1, params=params)
    data = request.model_dump(exclude_none=True)

    assert data["method"] == "initialize"
    assert data["id"] == 1
    assert data["params"]["rootUri"] == "file:///tmp"
    assert data["params"]["clientInfo"] == {"name": "test-client"}
    # Optional fields with None values are excluded
    assert "rootPath" not in data["params"]
    assert "workspaceFolders" not in data["params"]


def test_shutdown_request():
    req = ShutdownRequest(id=1)
    data = req.model_dump(exclude_none=True)
    assert data["method"] == "shutdown"
    assert data["id"] == 1
    assert "params" not in data


def test_exit_notification():
    notif = ExitNotification()
    data = notif.model_dump(exclude_none=True)
    assert data["method"] == "exit"
    assert "id" not in data


def test_did_close_notification():
    notif = TextDocumentDidCloseNotification()
    data = notif.model_dump(exclude_none=True)
    assert data["method"] == "textDocument/didClose"
    assert "id" not in data


def _position_params() -> TextDocumentPositionParams:
    return TextDocumentPositionParams(
        textDocument=TextDocumentIdentifier(uri="file:///tmp/test.py"),
        position=Position(line=3, character=10),
    )


def test_hover_request():
    req = HoverRequest(id=1, params=_position_params().model_dump())
    data = req.model_dump(exclude_none=True)
    assert data["method"] == "textDocument/hover"
    assert data["params"]["textDocument"] == {"uri": "file:///tmp/test.py"}
    assert data["params"]["position"] == {"line": 3, "character": 10}


def test_completion_request():
    req = CompletionRequest(id=1, params=_position_params().model_dump())
    data = req.model_dump(exclude_none=True)
    assert data["method"] == "textDocument/completion"
    assert data["params"]["textDocument"]["uri"] == "file:///tmp/test.py"


def test_definition_request():
    req = DefinitionRequest(id=1, params=_position_params().model_dump())
    data = req.model_dump(exclude_none=True)
    assert data["method"] == "textDocument/definition"
    assert data["params"]["textDocument"]["uri"] == "file:///tmp/test.py"

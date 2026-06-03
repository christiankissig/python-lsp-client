from lsp_client.protocol import (
    BaseNotification,
    BaseRequest,
    CancelRequest,
    ClientCapabilities,
    ClientInfo,
    CompletionRequest,
    ContentChange,
    DefinitionRequest,
    ErrorCodes,
    ExitNotification,
    GeneralClientCapabilities,
    HoverRequest,
    InitializeParams,
    InitializeRequest,
    InitializedNotification,
    Message,
    NotificationMessage,
    Position,
    PositionEncodingKind,
    ProgressNotification,
    Range,
    RequestMessage,
    ResponseError,
    ResponseMessage,
    ServerCapabilities,
    ShutdownRequest,
    TextDocumentDidChangeNotification,
    TextDocumentDidCloseNotification,
    TextDocumentDidOpenNotification,
    TextDocumentIdentifier,
    TextDocumentPositionParams,
    WorkDoneProgressBegin,
    WorkDoneProgressCancelNotification,
    WorkDoneProgressCancelParams,
    WorkDoneProgressCreateParams,
    WorkDoneProgressCreateRequest,
    WorkDoneProgressEnd,
    WorkDoneProgressOptions,
    WorkDoneProgressReport,
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


def test_work_done_progress_begin():
    begin = WorkDoneProgressBegin(title="Indexing", percentage=0)
    data = begin.model_dump(exclude_none=True)
    assert data == {"kind": "begin", "title": "Indexing", "percentage": 0}
    # Optional fields with None values are excluded
    assert "message" not in data
    assert "cancellable" not in data


def test_work_done_progress_report():
    report = WorkDoneProgressReport(message="halfway", percentage=50)
    data = report.model_dump(exclude_none=True)
    assert data == {"kind": "report", "message": "halfway", "percentage": 50}


def test_work_done_progress_end():
    end = WorkDoneProgressEnd(message="done")
    data = end.model_dump(exclude_none=True)
    assert data == {"kind": "end", "message": "done"}


def test_work_done_progress_end_minimal():
    data = WorkDoneProgressEnd().model_dump(exclude_none=True)
    assert data == {"kind": "end"}


def test_work_done_progress_options():
    data = WorkDoneProgressOptions(workDoneProgress=True).model_dump(exclude_none=True)
    assert data == {"workDoneProgress": True}


def test_work_done_progress_create_request():
    req = WorkDoneProgressCreateRequest(
        id=1, params=WorkDoneProgressCreateParams(token="token-1")
    )
    data = req.model_dump(exclude_none=True)
    assert data["method"] == "window/workDoneProgress/create"
    assert data["id"] == 1
    assert data["params"] == {"token": "token-1"}


def test_work_done_progress_cancel_notification():
    notif = WorkDoneProgressCancelNotification(
        params=WorkDoneProgressCancelParams(token=42)
    )
    data = notif.model_dump(exclude_none=True)
    assert data["method"] == "window/workDoneProgress/cancel"
    assert "id" not in data
    assert data["params"] == {"token": 42}


def test_message_base_defaults():
    message = Message()
    assert message.jsonrpc == "2.0"
    assert message.model_dump() == {"jsonrpc": "2.0"}


def test_requests_and_notifications_are_messages():
    # The base protocol abstract Message is the root of every message type.
    assert issubclass(BaseRequest, Message)
    assert issubclass(BaseNotification, Message)
    assert RequestMessage is BaseRequest
    assert NotificationMessage is BaseNotification


def test_response_message_success():
    response = ResponseMessage(id=1, result={"capabilities": {}})
    data = response.model_dump(exclude_none=True)
    assert data == {"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}
    assert "error" not in data


def test_response_message_error():
    response = ResponseMessage(
        id=1,
        error=ResponseError(code=ErrorCodes.MethodNotFound, message="no such method"),
    )
    data = response.model_dump(exclude_none=True)
    assert data["error"] == {"code": -32601, "message": "no such method"}
    assert "result" not in data


def test_response_message_null_id():
    # id may be null when it cannot be determined (e.g. a parse error).
    response = ResponseMessage(
        id=None,
        error=ResponseError(code=ErrorCodes.ParseError, message="parse error"),
    )
    data = response.model_dump()
    assert data["id"] is None


def test_position_encoding_kind_values():
    assert PositionEncodingKind.UTF8 == "utf-8"
    assert PositionEncodingKind.UTF16 == "utf-16"
    assert PositionEncodingKind.UTF32 == "utf-32"


def test_general_client_capabilities_position_encodings():
    general = GeneralClientCapabilities(
        positionEncodings=[
            PositionEncodingKind.UTF8,
            PositionEncodingKind.UTF16,
        ]
    )
    data = general.model_dump(exclude_none=True)
    assert data == {"positionEncodings": ["utf-8", "utf-16"]}
    # Unset general sub-capabilities are excluded.
    assert "markdown" not in data


def test_client_capabilities_advertise_position_encodings():
    caps = ClientCapabilities(
        general=GeneralClientCapabilities(
            positionEncodings=[PositionEncodingKind.UTF32]
        )
    )
    data = caps.model_dump(exclude_none=True)
    assert data == {"general": {"positionEncodings": ["utf-32"]}}


def test_initialize_request_with_position_encodings():
    params = InitializeParams(
        rootUri="file:///tmp",
        capabilities=ClientCapabilities(
            general=GeneralClientCapabilities(
                positionEncodings=[
                    PositionEncodingKind.UTF8,
                    PositionEncodingKind.UTF16,
                ]
            )
        ),
    )
    request = InitializeRequest(id=1, params=params)
    data = request.model_dump(exclude_none=True)
    assert data["params"]["capabilities"]["general"]["positionEncodings"] == [
        "utf-8",
        "utf-16",
    ]


def test_server_capabilities_position_encoding():
    caps = ServerCapabilities(positionEncoding=PositionEncodingKind.UTF8)
    data = caps.model_dump(exclude_none=True)
    assert data == {"positionEncoding": "utf-8"}


def test_server_capabilities_position_encoding_optional():
    # Absent positionEncoding means utf-16 is assumed; nothing is serialised.
    assert ServerCapabilities().model_dump(exclude_none=True) == {}


def test_error_codes_values():
    assert ErrorCodes.ParseError == -32700
    assert ErrorCodes.InvalidRequest == -32600
    assert ErrorCodes.InternalError == -32603
    assert ErrorCodes.RequestCancelled == -32800
    assert ErrorCodes.ContentModified == -32801
    # Shared-value codes resolve to aliases of the canonical member.
    assert ErrorCodes.serverErrorStart is ErrorCodes.jsonrpcReservedErrorRangeStart

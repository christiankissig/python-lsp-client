import pytest
from pydantic import ValidationError

from lsp_client.protocol import (
    BaseNotification,
    BaseRequest,
    CancelRequest,
    ClientCapabilities,
    ClientInfo,
    CodeDescription,
    CompletionRequest,
    ContentChange,
    DefinitionRequest,
    Diagnostic,
    DiagnosticRelatedInformation,
    DiagnosticSeverity,
    DiagnosticTag,
    ErrorCodes,
    ExitNotification,
    GeneralClientCapabilities,
    HoverRequest,
    InitializeParams,
    InitializeRequest,
    InitializedNotification,
    LanguageKind,
    Location,
    LSPErrorCodes,
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
    TextDocumentItem,
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


def test_notification_message_with_object_params():
    notif = NotificationMessage(method="telemetry/event", params={"key": "value"})
    data = notif.model_dump(exclude_none=True)
    assert data == {
        "jsonrpc": "2.0",
        "method": "telemetry/event",
        "params": {"key": "value"},
    }
    assert "id" not in data


def test_notification_message_with_array_params():
    # Per the spec a notification's params may be an array, not just an object.
    notif = NotificationMessage(method="custom/event", params=[1, "two", {"k": 3}])
    data = notif.model_dump(exclude_none=True)
    assert data["params"] == [1, "two", {"k": 3}]


def test_notification_message_params_optional():
    notif = NotificationMessage(method="exit")
    data = notif.model_dump(exclude_none=True)
    assert data == {"jsonrpc": "2.0", "method": "exit"}
    assert "params" not in data


def test_notification_message_requires_method():
    with pytest.raises(ValidationError):
        NotificationMessage()


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


def test_language_kind_values():
    assert LanguageKind.Python == "python"
    assert LanguageKind.CPP == "cpp"
    assert LanguageKind.GitCommit == "git-commit"
    assert LanguageKind.TypeScriptReact == "typescriptreact"


def test_text_document_item_with_language_kind():
    item = TextDocumentItem(
        uri="file:///tmp/test.py",
        languageId=LanguageKind.Python,
        version=1,
        text="print(1)",
    )
    data = item.model_dump()
    assert data == {
        "uri": "file:///tmp/test.py",
        "languageId": "python",
        "version": 1,
        "text": "print(1)",
    }


def test_text_document_item_with_known_string():
    item = TextDocumentItem(
        uri="file:///tmp/a.rs", languageId="rust", version=2, text="fn main(){}"
    )
    assert item.model_dump()["languageId"] == "rust"


def test_text_document_item_allows_custom_language_id():
    # languageId is a free-form string; unlisted identifiers stay valid.
    item = TextDocumentItem(
        uri="file:///tmp/a.cob", languageId="cobol", version=1, text=""
    )
    assert item.model_dump()["languageId"] == "cobol"


def test_text_document_item_serialises_over_the_wire():
    import json

    item = TextDocumentItem(
        uri="file:///tmp/test.py",
        languageId=LanguageKind.Python,
        version=1,
        text="x = 1",
    )
    assert json.loads(json.dumps(item.model_dump()))["languageId"] == "python"


def test_position_serialises():
    pos = Position(line=3, character=10)
    assert pos.model_dump() == {"line": 3, "character": 10}


def test_position_allows_zero():
    # Positions are zero-based, so 0 is a valid offset.
    assert Position(line=0, character=0).model_dump() == {"line": 0, "character": 0}


def test_position_rejects_negative_line():
    with pytest.raises(ValidationError):
        Position(line=-1, character=0)


def test_position_rejects_negative_character():
    with pytest.raises(ValidationError):
        Position(line=0, character=-5)


def test_position_rejects_above_uinteger_max():
    # uinteger is bounded at 2^31 - 1 per the LSP spec.
    with pytest.raises(ValidationError):
        Position(line=2147483648, character=0)


def test_position_allows_uinteger_max():
    assert Position(line=2147483647, character=2147483647).line == 2147483647


def test_range_structure():
    rng = Range(
        start=Position(line=1, character=2),
        end=Position(line=3, character=4),
    )
    assert rng.model_dump() == {
        "start": {"line": 1, "character": 2},
        "end": {"line": 3, "character": 4},
    }


def test_range_rejects_negative_position():
    with pytest.raises(ValidationError):
        Range(
            start=Position(line=0, character=0),
            end=Position(line=-1, character=0),
        )


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


def _range() -> Range:
    return Range(start=Position(line=1, character=0), end=Position(line=1, character=8))


def test_diagnostic_severity_values():
    assert DiagnosticSeverity.Error == 1
    assert DiagnosticSeverity.Warning == 2
    assert DiagnosticSeverity.Information == 3
    assert DiagnosticSeverity.Hint == 4


def test_diagnostic_tag_values():
    assert DiagnosticTag.Unnecessary == 1
    assert DiagnosticTag.Deprecated == 2


def test_location_structure():
    loc = Location(uri="file:///tmp/a.py", range=_range())
    assert loc.model_dump() == {
        "uri": "file:///tmp/a.py",
        "range": {
            "start": {"line": 1, "character": 0},
            "end": {"line": 1, "character": 8},
        },
    }


def test_diagnostic_minimal():
    diag = Diagnostic(range=_range(), message="undefined name 'x'")
    data = diag.model_dump(exclude_none=True)
    # Only range and message are required; optional fields are omitted.
    assert set(data) == {"range", "message"}
    assert data["message"] == "undefined name 'x'"


def test_diagnostic_full():
    diag = Diagnostic(
        range=_range(),
        severity=DiagnosticSeverity.Warning,
        code="F821",
        codeDescription=CodeDescription(href="https://example.com/F821"),
        source="flake8",
        message="undefined name 'x'",
        tags=[DiagnosticTag.Unnecessary],
        relatedInformation=[
            DiagnosticRelatedInformation(
                location=Location(uri="file:///tmp/b.py", range=_range()),
                message="first defined here",
            )
        ],
        data={"fixable": True},
    )
    data = diag.model_dump(exclude_none=True)
    assert data["severity"] == 2
    assert data["code"] == "F821"
    assert data["codeDescription"] == {"href": "https://example.com/F821"}
    assert data["source"] == "flake8"
    assert data["tags"] == [1]
    assert data["relatedInformation"][0]["location"]["uri"] == "file:///tmp/b.py"
    assert data["relatedInformation"][0]["message"] == "first defined here"
    assert data["data"] == {"fixable": True}


def test_diagnostic_integer_code():
    diag = Diagnostic(range=_range(), message="boom", code=42)
    assert diag.model_dump(exclude_none=True)["code"] == 42


def test_diagnostic_rejects_invalid_severity():
    with pytest.raises(ValidationError):
        Diagnostic(range=_range(), message="boom", severity=5)


def test_error_codes_values():
    # ErrorCodes carries only the JSON-RPC defined codes and reserved markers.
    assert ErrorCodes.ParseError == -32700
    assert ErrorCodes.InvalidRequest == -32600
    assert ErrorCodes.MethodNotFound == -32601
    assert ErrorCodes.InvalidParams == -32602
    assert ErrorCodes.InternalError == -32603
    assert ErrorCodes.ServerNotInitialized == -32002
    assert ErrorCodes.UnknownErrorCode == -32001
    # Shared-value codes resolve to aliases of the canonical member.
    assert ErrorCodes.serverErrorStart is ErrorCodes.jsonrpcReservedErrorRangeStart
    assert ErrorCodes.serverErrorEnd is ErrorCodes.jsonrpcReservedErrorRangeEnd


def test_lsp_error_codes_values():
    # LSP-defined codes live in their own enum, separate from JSON-RPC codes.
    assert LSPErrorCodes.RequestFailed == -32803
    assert LSPErrorCodes.ServerCancelled == -32802
    assert LSPErrorCodes.ContentModified == -32801
    assert LSPErrorCodes.RequestCancelled == -32800
    assert LSPErrorCodes.lspReservedErrorRangeStart == -32899
    # The reserved range end aliases RequestCancelled (shared value).
    assert LSPErrorCodes.lspReservedErrorRangeEnd is LSPErrorCodes.RequestCancelled


def test_error_codes_namespaces_are_separate():
    # JSON-RPC and LSP codes are distinct enums per the spec.
    assert not hasattr(ErrorCodes, "RequestCancelled")
    assert not hasattr(LSPErrorCodes, "ParseError")


def test_response_error_with_lsp_code():
    err = ResponseError(
        code=LSPErrorCodes.RequestFailed, message="boom", data={"detail": 1}
    )
    assert err.model_dump() == {
        "code": -32803,
        "message": "boom",
        "data": {"detail": 1},
    }


def test_response_message_rejects_result_and_error():
    # The spec forbids carrying both a result and an error.
    with pytest.raises(ValidationError):
        ResponseMessage(
            id=1,
            result={"ok": True},
            error=ResponseError(code=ErrorCodes.InternalError, message="bad"),
        )

"""
Incomplete implementation of the Language Server Protocol (LSP).

See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
for reference, and what a correct and complete implementation should look like.
"""

from enum import Enum, IntEnum
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


# Position Encoding
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocuments  # noqa: E501


class PositionEncodingKind(str, Enum):
    """How positions are encoded — i.e. what column offsets mean.

    Prior to 3.17 offsets were always based on a UTF-16 string representation.
    Since 3.17 client and server can negotiate a different encoding via the
    ``general.positionEncodings`` client capability and the ``positionEncoding``
    server capability.

    @since 3.17.0
    """

    #: Character offsets count UTF-8 code units (e.g. bytes).
    UTF8 = "utf-8"
    #: Character offsets count UTF-16 code units. This is the default and must
    #: always be supported by servers.
    UTF16 = "utf-16"
    #: Character offsets count UTF-32 code units. These are the same as Unicode
    #: code points, so this may also be used for an encoding-agnostic offset.
    UTF32 = "utf-32"


# Base Protocol — abstract Message
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#abstractMessage  # noqa: E501


class Message(BaseModel):
    """Base of every LSP message; carries only the JSON-RPC version."""

    jsonrpc: str = Field(default="2.0")


class BaseNotification(Message):
    """LSP notification — like a request but without an id field."""

    method: str
    params: dict | None = Field(default=None)


class BaseRequest(Message):
    id: int | None = Field(default=None)
    method: str
    params: dict | None = Field(default=None)


class ResponseError(BaseModel):
    """The error object returned on a failed request."""

    code: int
    message: str
    data: Any | None = None


class ResponseMessage(Message):
    """A response to a request.

    ``id`` may be ``null`` when the request id could not be determined (e.g. a
    parse error). Exactly one of ``result`` / ``error`` is present per the spec.
    """

    id: int | str | None = None
    result: Any | None = None
    error: ResponseError | None = None


class ErrorCodes(IntEnum):
    """JSON-RPC and LSP-defined error codes.

    Codes that share a value (e.g. ``serverErrorStart`` /
    ``jsonrpcReservedErrorRangeStart``) resolve to enum aliases.
    """

    # Defined by JSON-RPC
    ParseError = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams = -32602
    InternalError = -32603

    jsonrpcReservedErrorRangeStart = -32099
    serverErrorStart = -32099

    ServerNotInitialized = -32002
    UnknownErrorCode = -32001

    jsonrpcReservedErrorRangeEnd = -32000
    serverErrorEnd = -32000

    # Defined by LSP
    lspReservedErrorRangeStart = -32899

    RequestFailed = -32803
    ServerCancelled = -32802
    ContentModified = -32801
    RequestCancelled = -32800

    lspReservedErrorRangeEnd = -32800


class ProtocolError(Exception):
    def __init__(self, message: str, errors: Optional[List[str]] = None) -> None:
        """
        Initialize the exception with an error message and optional errors.

        Args:
            message (str): The error message to be displayed.
            errors (optional): Additional details or nested errors.
        """
        super().__init__(message)
        self.errors = errors


# Server Lifecycle
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#lifeCycleMessages


class WorkDoneProgressParams(BaseModel):
    workDoneToken: int | str | None = None


class ClientInfo(BaseModel):
    name: str
    version: str | None = None


class GeneralClientCapabilities(BaseModel):
    """General client capabilities — capabilities not tied to a single feature.

    @since 3.16.0
    """

    staleRequestSupport: dict | None = None
    regularExpressions: dict | None = None
    markdown: dict | None = None
    #: The position encodings supported by the client, in order of decreasing
    #: preference. The server picks the first one it also supports; if none
    #: match it must default to ``utf-16``. @since 3.17.0
    positionEncodings: list[PositionEncodingKind] | None = None


class ClientCapabilities(BaseModel):
    workspace: dict | None = None
    textDocument: dict | None = None
    notebook: dict | None = None
    window: dict | None = None
    general: GeneralClientCapabilities | None = None
    experimental: dict | None = None


class ServerCapabilities(BaseModel):
    """Subset of server capabilities relevant to position encoding negotiation.

    Returned by the server in the ``InitializeResult``.
    """

    #: The position encoding the server picked from the client's advertised
    #: ``positionEncodings``. If absent, ``utf-16`` is assumed. @since 3.17.0
    positionEncoding: PositionEncodingKind | None = None


class TextDocumentClientCapabilities(BaseModel):
    synchronization: dict | None
    completion: dict | None
    hover: dict | None
    signatureHelp: dict | None
    declaration: dict | None
    definition: dict | None
    typeDefinition: dict | None
    implementation: dict | None
    references: dict | None
    documentHighlight: dict | None
    documentSymbol: dict | None
    codeAction: dict | None
    codeLens: dict | None
    documentLink: dict | None
    colorProvider: dict | None
    formatting: dict | None
    rangeFormatting: dict | None
    onTypeFormatting: dict | None
    rename: dict | None
    publishDiagnostics: dict | None
    foldingRange: dict | None
    selectionRange: dict | None
    linkedEditingRange: dict | None
    callHierarchy: dict | None
    semanticTokens: dict | None
    moniker: dict | None
    typeHierarchy: dict | None
    inlineValue: dict | None
    inlayHint: dict | None
    diagnostic: dict | None


class NotebookDocumentClientCapabilities(BaseModel):
    synchronization: dict | None


class WorkspaceClientCapabilities(BaseModel):
    applyEdit: dict | None
    workspaceEdit: dict | None
    didChangeConfiguration: dict | None
    didChangeWatchedFiles: dict | None
    symbol: dict | None
    executeCommand: dict | None
    workspaceFolders: dict | None
    configuration: dict | None
    semanticTokens: dict | None
    codeLens: dict | None
    fileOperations: dict | None
    inlineValue: dict | None
    inlayHint: dict | None
    diagnostics: dict | None


class FileOperationsClientCapabilities(BaseModel):
    didCreate: dict | None = None
    willCreate: dict | None = None
    didRename: dict | None = None
    willRename: dict | None = None
    didDelete: dict | None = None
    willDelete: dict | None = None


class InitializeParams(WorkDoneProgressParams):
    processId: int | None = None
    clientInfo: ClientInfo | None = None
    rootPath: str | None = None
    rootUri: str
    initializationOptions: dict | None = None
    capabilities: ClientCapabilities = Field(default_factory=ClientCapabilities)
    trace: str | None = None
    workspaceFolders: list[dict] | None = None


class InitializeRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "initialize"
        if isinstance(kwargs.get("params"), InitializeParams):
            kwargs["params"] = kwargs["params"].model_dump(exclude_none=True)
        super(InitializeRequest, self).__init__(**kwargs)


class InitializedNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "initialized"
        kwargs.setdefault("params", {})
        super(InitializedNotification, self).__init__(**kwargs)


# Text Document Synchronization
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_synchronization # noqa: E501


class TextDocumentItem(BaseModel):
    uri: str
    languageId: str
    version: int
    text: str


class TextDocumentDidOpenNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/didOpen"
        super(TextDocumentDidOpenNotification, self).__init__(**kwargs)


class Position(BaseModel):
    line: int
    character: int


class Range(BaseModel):
    start: Position
    end: Position


class ContentChange(BaseModel):
    text: str
    range: Optional[Range] = None
    # rangeLength is deprecated and optional per the LSP spec
    rangeLength: Optional[int] = None


class TextDocumentDidChangeNotification(BaseNotification):
    def __init__(
        self,
        uri: str,
        version: int,
        contentChanges: List[ContentChange],
        **kwargs: Any,
    ) -> None:
        kwargs["method"] = "textDocument/didChange"
        if "params" in kwargs:
            params = kwargs["params"]
        else:
            params = {}
        params["textDocument"] = {"uri": uri, "version": version}
        params["contentChanges"] = contentChanges
        kwargs["params"] = params
        super(TextDocumentDidChangeNotification, self).__init__(**kwargs)


# Server Lifecycle — shutdown / exit
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#shutdown


class ShutdownRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "shutdown"
        super(ShutdownRequest, self).__init__(**kwargs)


class ExitNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "exit"
        super(ExitNotification, self).__init__(**kwargs)


# Text Document — didClose, hover, completion, definition
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_synchronization # noqa: E501


class TextDocumentDidCloseNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/didClose"
        super(TextDocumentDidCloseNotification, self).__init__(**kwargs)


class TextDocumentIdentifier(BaseModel):
    uri: str


class TextDocumentPositionParams(BaseModel):
    textDocument: TextDocumentIdentifier
    position: Position


class HoverRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/hover"
        super(HoverRequest, self).__init__(**kwargs)


class CompletionRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/completion"
        super(CompletionRequest, self).__init__(**kwargs)


class DefinitionRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/definition"
        super(DefinitionRequest, self).__init__(**kwargs)


# $ Notifications and Requests
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#dollarRequests


class CancelRequest(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "$/cancelRequest"
        super(CancelRequest, self).__init__(**kwargs)


# A progress token is either an integer or a string, supplied by whichever
# side initiates the progress sequence.
ProgressToken = int | str


class ProgressParams(BaseModel):
    token: ProgressToken
    value: dict


class ProgressNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "$/progress"
        super(ProgressNotification, self).__init__(**kwargs)


# Work Done Progress
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#workDoneProgress  # noqa: E501


class WorkDoneProgressBegin(BaseModel):
    """Payload signalling the start of a work done progress sequence.

    Sent as the ``value`` of a ``$/progress`` notification.
    """

    kind: Literal["begin"] = "begin"
    title: str
    cancellable: bool | None = None
    message: str | None = None
    percentage: int | None = None


class WorkDoneProgressReport(BaseModel):
    """Payload reporting progress within an ongoing work done sequence."""

    kind: Literal["report"] = "report"
    cancellable: bool | None = None
    message: str | None = None
    percentage: int | None = None


class WorkDoneProgressEnd(BaseModel):
    """Payload signalling the end of a work done progress sequence."""

    kind: Literal["end"] = "end"
    message: str | None = None


class WorkDoneProgressOptions(BaseModel):
    """Server capability marker for features that support work done progress."""

    workDoneProgress: bool | None = None


class WorkDoneProgressCreateParams(BaseModel):
    token: ProgressToken


class WorkDoneProgressCreateRequest(BaseRequest):
    """Server -> client request asking the client to create a progress token."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "window/workDoneProgress/create"
        if isinstance(kwargs.get("params"), WorkDoneProgressCreateParams):
            kwargs["params"] = kwargs["params"].model_dump(exclude_none=True)
        super(WorkDoneProgressCreateRequest, self).__init__(**kwargs)


class WorkDoneProgressCancelParams(BaseModel):
    token: ProgressToken


class WorkDoneProgressCancelNotification(BaseNotification):
    """Client -> server notification cancelling a work done progress sequence."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "window/workDoneProgress/cancel"
        if isinstance(kwargs.get("params"), WorkDoneProgressCancelParams):
            kwargs["params"] = kwargs["params"].model_dump(exclude_none=True)
        super(WorkDoneProgressCancelNotification, self).__init__(**kwargs)


# Spec-named aliases for the base protocol message types.
RequestMessage = BaseRequest
NotificationMessage = BaseNotification

# Backwards-compatible aliases for renamed classes
TextDocumentDidOpenRequest = TextDocumentDidOpenNotification
TextDocumentDidChangeRequest = TextDocumentDidChangeNotification
TextDocument_DidOpen_Request = TextDocumentDidOpenNotification
TextDocument_DidChange_Request = TextDocumentDidChangeNotification

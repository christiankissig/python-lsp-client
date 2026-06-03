"""
Incomplete implementation of the Language Server Protocol (LSP).

See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
for reference, and what a correct and complete implementation should look like.
"""

from enum import Enum, IntEnum
from typing import Annotated, Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


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


# Notification Message
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#notificationMessage  # noqa: E501


class BaseNotification(Message):
    """A notification message — like a request but with no ``id``.

    A processed notification message must not send a response back; they work
    like events. Per the spec a notification carries a ``method`` and optional
    ``params`` which may be either an array or an object.
    """

    method: str
    params: list | dict | None = Field(default=None)


class BaseRequest(Message):
    id: int | None = Field(default=None)
    method: str
    params: dict | None = Field(default=None)


class ResponseError(BaseModel):
    """The error object returned on a failed request.

    ``code`` is a number indicating the error type (see :class:`ErrorCodes` and
    :class:`LSPErrorCodes`), ``message`` a short human-readable description, and
    ``data`` an optional primitive or structured value with extra detail.
    """

    code: int
    message: str
    data: Any | None = None


class ResponseMessage(Message):
    """A response to a request.

    ``id`` may be ``null`` when the request id could not be determined (e.g. a
    parse error). Per the spec ``result`` is required on success and must not be
    present on error, so a response carries at most one of ``result`` / ``error``.
    """

    id: int | str | None = None
    result: Any | None = None
    error: ResponseError | None = None

    @model_validator(mode="after")
    def _check_result_xor_error(self) -> "ResponseMessage":
        if self.result is not None and self.error is not None:
            raise ValueError(
                "a ResponseMessage must not carry both 'result' and 'error'"
            )
        return self


class ErrorCodes(IntEnum):
    """Error codes defined by JSON-RPC.

    Codes that share a value (e.g. ``serverErrorStart`` /
    ``jsonrpcReservedErrorRangeStart``) resolve to enum aliases. LSP-defined
    codes live in their own range; see :class:`LSPErrorCodes`.
    """

    ParseError = -32700
    InvalidRequest = -32600
    MethodNotFound = -32601
    InvalidParams = -32602
    InternalError = -32603

    # Start range of JSON-RPC reserved error codes. Does not denote a real
    # error code. ``ServerNotInitialized`` / ``UnknownErrorCode`` are kept in
    # this range for backwards compatibility. @since 3.16.0
    jsonrpcReservedErrorRangeStart = -32099
    #: @deprecated use ``jsonrpcReservedErrorRangeStart``
    serverErrorStart = -32099

    ServerNotInitialized = -32002
    UnknownErrorCode = -32001

    # End range of JSON-RPC reserved error codes. Does not denote a real error
    # code. @since 3.16.0
    jsonrpcReservedErrorRangeEnd = -32000
    #: @deprecated use ``jsonrpcReservedErrorRangeEnd``
    serverErrorEnd = -32000


class LSPErrorCodes(IntEnum):
    """Error codes defined by the Language Server Protocol itself."""

    # Start range of LSP reserved error codes. Does not denote a real error
    # code. @since 3.16.0
    lspReservedErrorRangeStart = -32899

    #: A request failed but was syntactically correct (known method, valid
    #: params); the message should explain why. @since 3.17.0
    RequestFailed = -32803
    #: The server cancelled the request; only for explicitly server-cancellable
    #: requests. @since 3.17.0
    ServerCancelled = -32802
    #: The document content was modified outside normal conditions, so the
    #: result may be stale.
    ContentModified = -32801
    #: The client cancelled a request and the server detected the cancellation.
    RequestCancelled = -32800

    # End range of LSP reserved error codes. Does not denote a real error code.
    # @since 3.16.0 (aliases ``RequestCancelled``)
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


class LanguageKind(str, Enum):
    """The recognised language identifiers for a :class:`TextDocumentItem`.

    The LSP types ``languageId`` simply as ``string`` and documents the set of
    identifiers below. These are provided for convenience; custom identifiers
    not listed here remain valid (``languageId`` accepts any string).

    See
    https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocumentItem
    """

    ABAP = "abap"
    WindowsBat = "bat"
    BibTeX = "bibtex"
    Clojure = "clojure"
    Coffeescript = "coffeescript"
    C = "c"
    CPP = "cpp"
    CSharp = "csharp"
    CSS = "css"
    Diff = "diff"
    Dart = "dart"
    Dockerfile = "dockerfile"
    Elixir = "elixir"
    Erlang = "erlang"
    FSharp = "fsharp"
    GitCommit = "git-commit"
    GitRebase = "git-rebase"
    Go = "go"
    Groovy = "groovy"
    Handlebars = "handlebars"
    HTML = "html"
    Ini = "ini"
    Java = "java"
    JavaScript = "javascript"
    JavaScriptReact = "javascriptreact"
    JSON = "json"
    LaTeX = "latex"
    Less = "less"
    Lua = "lua"
    Makefile = "makefile"
    Markdown = "markdown"
    ObjectiveC = "objective-c"
    ObjectiveCPP = "objective-cpp"
    Perl = "perl"
    Perl6 = "perl6"
    PHP = "php"
    Powershell = "powershell"
    Pug = "jade"
    Python = "python"
    R = "r"
    Razor = "razor"
    Ruby = "ruby"
    Rust = "rust"
    SCSS = "scss"
    Sass = "sass"
    Scala = "scala"
    ShaderLab = "shaderlab"
    ShellScript = "shellscript"
    SQL = "sql"
    Swift = "swift"
    TypeScript = "typescript"
    TypeScriptReact = "typescriptreact"
    TeX = "tex"
    VisualBasic = "vb"
    XML = "xml"
    XSL = "xsl"
    YAML = "yaml"


class TextDocumentItem(BaseModel):
    """An item to transfer a text document from the client to the server.

    ``languageId`` is a free-form string per the spec; :class:`LanguageKind`
    enumerates the documented identifiers for convenience.
    """

    uri: str
    languageId: LanguageKind | str
    version: int
    text: str


class TextDocumentDidOpenNotification(BaseNotification):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/didOpen"
        super(TextDocumentDidOpenNotification, self).__init__(**kwargs)


# Range
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#range  # noqa: E501

#: The LSP ``uinteger`` type: a non-negative integer in the range
#: ``[0, 2^31 - 1]``. Used for line and character offsets.
uinteger = Annotated[int, Field(ge=0, le=2147483647)]


class Position(BaseModel):
    """Position in a text document — a zero-based line and character offset.

    Both ``line`` and ``character`` are ``uinteger`` (non-negative). A position
    sits between two characters, like an insert cursor. The unit of
    ``character`` depends on the negotiated position encoding (UTF-16 code units
    by default); see :class:`PositionEncodingKind`.
    """

    line: uinteger
    character: uinteger


class Range(BaseModel):
    """A range in a text document — a start and an exclusive end position.

    A range is comparable to a selection in an editor. An empty range (where
    ``start`` equals ``end``) denotes a single position.
    """

    start: Position
    end: Position


# Location
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#location  # noqa: E501


class Location(BaseModel):
    """A range inside a text document, identified by its URI."""

    uri: str
    range: Range


# Diagnostic
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#diagnostic  # noqa: E501


class DiagnosticSeverity(IntEnum):
    """How severe a diagnostic is."""

    Error = 1
    Warning = 2
    Information = 3
    Hint = 4


class DiagnosticTag(IntEnum):
    """Additional metadata about a diagnostic. @since 3.15.0"""

    #: Unused or unnecessary code — clients may render this faded out.
    Unnecessary = 1
    #: Deprecated or obsolete code — clients may render this struck through.
    Deprecated = 2


class CodeDescription(BaseModel):
    """A structure describing a diagnostic's error code. @since 3.16.0"""

    #: A URI to open with more information about the diagnostic error.
    href: str


class DiagnosticRelatedInformation(BaseModel):
    """A related message and source location for a diagnostic.

    Used e.g. when symbol names within a scope collide, to point at every
    colliding definition.
    """

    location: Location
    message: str


class Diagnostic(BaseModel):
    """A diagnostic, such as a compiler error or warning.

    Diagnostic objects are only valid in the scope of a resource.
    """

    #: The range at which the message applies.
    range: Range
    #: The diagnostic's severity. If omitted the client interprets it.
    severity: DiagnosticSeverity | None = None
    #: The diagnostic's code, which may appear in the user interface.
    code: int | str | None = None
    #: An optional structure describing the error code. @since 3.16.0
    codeDescription: CodeDescription | None = None
    #: A human-readable description of the diagnostic's source, e.g.
    #: ``"typescript"`` or ``"super lint"``.
    source: str | None = None
    #: The diagnostic's message.
    message: str
    #: Additional metadata about the diagnostic. @since 3.15.0
    tags: list[DiagnosticTag] | None = None
    #: An array of related diagnostic information.
    relatedInformation: list[DiagnosticRelatedInformation] | None = None
    #: A data entry preserved between a ``textDocument/publishDiagnostics``
    #: notification and a ``textDocument/codeAction`` request. @since 3.16.0
    data: Any | None = None


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

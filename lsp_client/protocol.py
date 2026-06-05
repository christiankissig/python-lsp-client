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


class LSPError(Exception):
    """Raised when an awaited request resolves to a :class:`ResponseError`.

    Wraps the error object so callers can inspect ``code`` / ``message`` /
    ``data`` while still catching it as a regular exception.
    """

    def __init__(self, error: ResponseError) -> None:
        super().__init__(f"[{error.code}] {error.message}")
        self.error = error
        self.code = error.code
        self.message = error.message
        self.data = error.data


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


class TextDocumentSyncKind(IntEnum):
    """Defines how the host (editor) should sync document changes to the
    language server."""

    #: Documents should not be synced at all.
    None_ = 0
    #: Documents are synced by always sending the full content of the document.
    Full = 1
    #: Documents are synced by sending the full content on open, then
    #: incremental change notifications afterwards.
    Incremental = 2


class ServerCapabilities(BaseModel):
    """The capabilities a language server provides.

    Returned by the server in the :class:`InitializeResult`.

    Provider options that the spec models as dedicated ``XxxOptions`` /
    ``XxxRegistrationOptions`` objects are accepted here as ``dict`` (consistent
    with the rest of this module), while ``boolean | XxxOptions`` unions accept
    ``bool | dict``.
    """

    #: The position encoding the server picked from the client's advertised
    #: ``positionEncodings``. If absent, ``utf-16`` is assumed. @since 3.17.0
    positionEncoding: PositionEncodingKind | None = None
    #: Defines how text documents are synced.
    textDocumentSync: TextDocumentSyncKind | dict | None = None
    #: Defines how notebook documents are synced. @since 3.17.0
    notebookDocumentSync: dict | None = None
    #: The server provides completion support.
    completionProvider: dict | None = None
    #: The server provides hover support.
    hoverProvider: bool | dict | None = None
    #: The server provides signature help support.
    signatureHelpProvider: dict | None = None
    #: The server provides go to declaration support. @since 3.14.0
    declarationProvider: bool | dict | None = None
    #: The server provides goto definition support.
    definitionProvider: bool | dict | None = None
    #: The server provides goto type definition support. @since 3.6.0
    typeDefinitionProvider: bool | dict | None = None
    #: The server provides goto implementation support. @since 3.6.0
    implementationProvider: bool | dict | None = None
    #: The server provides find references support.
    referencesProvider: bool | dict | None = None
    #: The server provides document highlight support.
    documentHighlightProvider: bool | dict | None = None
    #: The server provides document symbol support.
    documentSymbolProvider: bool | dict | None = None
    #: The server provides code actions.
    codeActionProvider: bool | dict | None = None
    #: The server provides code lens.
    codeLensProvider: dict | None = None
    #: The server provides document link support.
    documentLinkProvider: dict | None = None
    #: The server provides color provider support. @since 3.6.0
    colorProvider: bool | dict | None = None
    #: The server provides document formatting.
    documentFormattingProvider: bool | dict | None = None
    #: The server provides document range formatting.
    documentRangeFormattingProvider: bool | dict | None = None
    #: The server provides document formatting on typing.
    documentOnTypeFormattingProvider: dict | None = None
    #: The server provides rename support.
    renameProvider: bool | dict | None = None
    #: The server provides folding provider support. @since 3.10.0
    foldingRangeProvider: bool | dict | None = None
    #: The server provides execute command support.
    executeCommandProvider: dict | None = None
    #: The server provides selection range support. @since 3.15.0
    selectionRangeProvider: bool | dict | None = None
    #: The server provides linked editing range support. @since 3.16.0
    linkedEditingRangeProvider: bool | dict | None = None
    #: The server provides call hierarchy support. @since 3.16.0
    callHierarchyProvider: bool | dict | None = None
    #: The server provides semantic tokens support. @since 3.16.0
    semanticTokensProvider: dict | None = None
    #: The server provides moniker support. @since 3.16.0
    monikerProvider: bool | dict | None = None
    #: The server provides type hierarchy support. @since 3.17.0
    typeHierarchyProvider: bool | dict | None = None
    #: The server provides inline values. @since 3.17.0
    inlineValueProvider: bool | dict | None = None
    #: The server provides inlay hints. @since 3.17.0
    inlayHintProvider: bool | dict | None = None
    #: The server has support for pull model diagnostics. @since 3.17.0
    diagnosticProvider: dict | None = None
    #: The server provides workspace symbol support.
    workspaceSymbolProvider: bool | dict | None = None
    #: Workspace-specific server capabilities.
    workspace: dict | None = None
    #: Experimental server capabilities.
    experimental: Any | None = None


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


class ServerInfo(BaseModel):
    """Information about the server. @since 3.15.0"""

    #: The name of the server as defined by the server.
    name: str
    #: The server's version as defined by the server.
    version: str | None = None


class InitializeResult(BaseModel):
    """The result returned from an ``initialize`` request."""

    #: The capabilities the language server provides.
    capabilities: ServerCapabilities
    #: Information about the server. @since 3.15.0
    serverInfo: ServerInfo | None = None


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


class DocumentSymbolParams(BaseModel):
    """Params for a ``textDocument/documentSymbol`` request."""

    textDocument: TextDocumentIdentifier


def _coerce_params(kwargs: dict[str, Any]) -> None:
    """Serialise a Pydantic ``params`` model into a plain dict in place.

    Lets the language-feature request constructors accept either a raw
    ``dict`` (as before) or a typed params model — mirroring
    :class:`InitializeRequest`.
    """
    params = kwargs.get("params")
    if isinstance(params, BaseModel):
        kwargs["params"] = params.model_dump(exclude_none=True)


# Hover
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_hover  # noqa: E501


class MarkupKind(str, Enum):
    """Describes the content type that a client supports in various result
    literals like ``Hover`` or ``CompletionItem``."""

    #: Plain text is supported as a content format.
    PlainText = "plaintext"
    #: Markdown is supported as a content format.
    Markdown = "markdown"


class MarkupContent(BaseModel):
    """A string value whose content is interpreted based on its ``kind``.

    @since 3.3.0
    """

    kind: MarkupKind
    value: str


class MarkedString(BaseModel):
    """A marked string with an explicit language for syntax highlighting.

    @deprecated use :class:`MarkupContent` instead. Kept because servers may
    still return the ``{ language, value }`` form in a hover result.
    """

    language: str
    value: str


class Hover(BaseModel):
    """The result of a ``textDocument/hover`` request."""

    #: The hover's content. Either a single :class:`MarkupContent`, a (possibly
    #: deprecated) marked string, or a list of marked strings.
    contents: MarkupContent | MarkedString | str | list[MarkedString | str]
    #: An optional range the hover applies to, used to visually highlight it.
    range: Range | None = None


# Completion
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_completion  # noqa: E501


class CompletionTriggerKind(IntEnum):
    """How a completion was triggered."""

    #: Completion was triggered by typing an identifier, manual invocation
    #: (e.g. Ctrl+Space) or via the API.
    Invoked = 1
    #: Completion was triggered by a trigger character specified by the
    #: ``completionProvider``'s ``triggerCharacters``.
    TriggerCharacter = 2
    #: Completion was re-triggered as the current completion list is incomplete.
    TriggerForIncompleteCompletions = 3


class CompletionContext(BaseModel):
    """Additional information about the context in which a completion request is
    triggered."""

    #: How the completion was triggered.
    triggerKind: CompletionTriggerKind
    #: The trigger character (single character) that triggered completion.
    #: Undefined if ``triggerKind`` is not ``TriggerCharacter``.
    triggerCharacter: str | None = None


class CompletionParams(TextDocumentPositionParams):
    """Params for a ``textDocument/completion`` request."""

    #: The completion context. Only present if the client specifies it can be
    #: filled in via the ``completionItem.contextSupport`` capability.
    context: CompletionContext | None = None


class CompletionItemKind(IntEnum):
    """The kind of a completion entry."""

    Text = 1
    Method = 2
    Function = 3
    Constructor = 4
    Field = 5
    Variable = 6
    Class = 7
    Interface = 8
    Module = 9
    Property = 10
    Unit = 11
    Value = 12
    Enum = 13
    Keyword = 14
    Snippet = 15
    Color = 16
    File = 17
    Reference = 18
    Folder = 19
    EnumMember = 20
    Constant = 21
    Struct = 22
    Event = 23
    Operator = 24
    TypeParameter = 25


class InsertTextFormat(IntEnum):
    """Defines whether the insert text in a completion item should be
    interpreted as plain text or a snippet."""

    #: The primary text to be inserted is treated as plain text.
    PlainText = 1
    #: The primary text to be inserted is treated as a snippet (with tab stops,
    #: placeholders etc.).
    Snippet = 2


class TextEdit(BaseModel):
    """A textual edit applicable to a text document."""

    #: The range of the text document to be manipulated.
    range: Range
    #: The string to be inserted. An empty string deletes the range.
    newText: str


class InsertReplaceEdit(BaseModel):
    """A special text edit offering an insert and a replace range.

    @since 3.16.0
    """

    #: The string to be inserted.
    newText: str
    #: The range if the insert is requested.
    insert: Range
    #: The range if the replace is requested.
    replace: Range


class CompletionItem(BaseModel):
    """A single completion entry. Only the commonly used fields are modelled;
    unmodelled fields are ignored."""

    #: The label of this completion item, shown in the UI.
    label: str
    #: The kind of this completion item, used to pick an icon.
    kind: CompletionItemKind | None = None
    #: A human-readable string with additional information, e.g. type/symbol.
    detail: str | None = None
    #: A human-readable string that represents a doc-comment.
    documentation: str | MarkupContent | None = None
    #: The string to insert when selecting this completion. When omitted the
    #: ``label`` is used.
    insertText: str | None = None
    #: An edit applied when selecting this completion; overrides ``insertText``.
    textEdit: TextEdit | InsertReplaceEdit | None = None
    #: How ``insertText`` / ``textEdit`` text is interpreted.
    insertTextFormat: InsertTextFormat | None = None


class CompletionList(BaseModel):
    """A collection of completion items to be presented in the editor."""

    #: ``True`` if this list is not complete; further typing should recompute it.
    isIncomplete: bool
    #: The completion items.
    items: list[CompletionItem]


# Definition
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_definition  # noqa: E501


class LocationLink(BaseModel):
    """A link between a source and a target location.

    Provides additional metadata over a plain :class:`Location`, including the
    span of the originating link and the precise target selection range.
    """

    #: Span of the origin of this link. Used as the underlined span for mouse
    #: navigation; defaults to the word range at the mouse position.
    originSelectionRange: Range | None = None
    #: The target resource identifier of this link.
    targetUri: str
    #: The full target range, e.g. the whole symbol including comments.
    targetRange: Range
    #: The precise range to select and reveal, e.g. just the symbol name. Must
    #: be contained within ``targetRange``.
    targetSelectionRange: Range


# Document Symbols
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_documentSymbol  # noqa: E501


class SymbolKind(IntEnum):
    """A symbol kind."""

    File = 1
    Module = 2
    Namespace = 3
    Package = 4
    Class = 5
    Method = 6
    Property = 7
    Field = 8
    Constructor = 9
    Enum = 10
    Interface = 11
    Function = 12
    Variable = 13
    Constant = 14
    String = 15
    Number = 16
    Boolean = 17
    Array = 18
    Object = 19
    Key = 20
    Null = 21
    EnumMember = 22
    Struct = 23
    Event = 24
    Operator = 25
    TypeParameter = 26


class SymbolTag(IntEnum):
    """Extra annotations that tweak the rendering of a symbol. @since 3.16.0"""

    #: Render a symbol as obsolete, usually using a strike-out.
    Deprecated = 1


class DocumentSymbol(BaseModel):
    """A hierarchical symbol — programming constructs like variables, classes,
    functions etc. — with two ranges and optional children."""

    #: The name of this symbol, displayed in the UI.
    name: str
    #: More detail for this symbol, e.g. the signature of a function.
    detail: str | None = None
    #: The kind of this symbol.
    kind: SymbolKind
    #: Tags for this symbol. @since 3.16.0
    tags: list[SymbolTag] | None = None
    #: Indicates the symbol is deprecated. @deprecated use ``tags`` instead.
    deprecated: bool | None = None
    #: The range enclosing this symbol, e.g. a function's whole body.
    range: Range
    #: The range to select when picking this symbol, e.g. the function name.
    #: Must be contained by ``range``.
    selectionRange: Range
    #: Children of this symbol, e.g. the methods of a class.
    children: list["DocumentSymbol"] | None = None


class SymbolInformation(BaseModel):
    """A flat representation of a symbol with its enclosing location.

    @deprecated by the LSP spec in favour of :class:`DocumentSymbol`; servers
    may still return it from ``textDocument/documentSymbol``.
    """

    #: The name of this symbol.
    name: str
    #: The kind of this symbol.
    kind: SymbolKind
    #: Tags for this symbol. @since 3.16.0
    tags: list[SymbolTag] | None = None
    #: Indicates the symbol is deprecated. @deprecated use ``tags`` instead.
    deprecated: bool | None = None
    #: The location of this symbol.
    location: Location
    #: The name of the symbol containing this symbol.
    containerName: str | None = None


# Document Highlights
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_documentHighlight  # noqa: E501


class DocumentHighlightKind(IntEnum):
    """A document highlight kind."""

    #: A textual occurrence.
    Text = 1
    #: Read access of a symbol, e.g. reading a variable.
    Read = 2
    #: Write access of a symbol, e.g. writing to a variable.
    Write = 3


class DocumentHighlight(BaseModel):
    """A range inside a text document that should be highlighted, e.g. all
    occurrences of a symbol."""

    #: The range this highlight applies to.
    range: Range
    #: The highlight kind, defaulting to :attr:`DocumentHighlightKind.Text`.
    kind: DocumentHighlightKind | None = None


# Language-feature requests
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#languageFeatures  # noqa: E501


class HoverRequest(BaseRequest):
    """``textDocument/hover`` — params are a :class:`TextDocumentPositionParams`."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/hover"
        _coerce_params(kwargs)
        super(HoverRequest, self).__init__(**kwargs)


class CompletionRequest(BaseRequest):
    """``textDocument/completion`` — params are :class:`CompletionParams`."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/completion"
        _coerce_params(kwargs)
        super(CompletionRequest, self).__init__(**kwargs)


class DefinitionRequest(BaseRequest):
    """``textDocument/definition`` — params are a :class:`TextDocumentPositionParams`."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/definition"
        _coerce_params(kwargs)
        super(DefinitionRequest, self).__init__(**kwargs)


class DocumentSymbolRequest(BaseRequest):
    """``textDocument/documentSymbol`` — params are :class:`DocumentSymbolParams`."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/documentSymbol"
        _coerce_params(kwargs)
        super(DocumentSymbolRequest, self).__init__(**kwargs)


class DocumentHighlightRequest(BaseRequest):
    """``textDocument/documentHighlight`` — params are a :class:`TextDocumentPositionParams`."""

    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/documentHighlight"
        _coerce_params(kwargs)
        super(DocumentHighlightRequest, self).__init__(**kwargs)


# Result-union parsing helpers
# Several language-feature requests return a union whose concrete shape is only
# discoverable at runtime. These helpers validate a raw JSON ``result`` into the
# appropriate typed model(s), returning ``None`` when the server returned null.


def parse_hover_result(result: Any) -> Hover | None:
    """Validate a ``textDocument/hover`` result into a :class:`Hover`."""
    if result is None:
        return None
    return Hover.model_validate(result)


def parse_completion_result(result: Any) -> CompletionList | None:
    """Validate a ``textDocument/completion`` result.

    Normalises the ``CompletionItem[] | CompletionList | null`` union: a bare
    array becomes a complete :class:`CompletionList`.
    """
    if result is None:
        return None
    if isinstance(result, list):
        items = [CompletionItem.model_validate(item) for item in result]
        return CompletionList(isIncomplete=False, items=items)
    return CompletionList.model_validate(result)


def parse_definition_result(
    result: Any,
) -> list[Location] | list[LocationLink] | None:
    """Validate a ``textDocument/definition`` result.

    Normalises the ``Location | Location[] | LocationLink[] | null`` union: a
    single ``Location`` becomes a one-element list. ``LocationLink`` entries are
    distinguished from ``Location`` entries by their ``targetUri`` field.
    """
    if result is None:
        return None
    if isinstance(result, dict):
        return [Location.model_validate(result)]
    if not result:
        return []
    if "targetUri" in result[0]:
        return [LocationLink.model_validate(item) for item in result]
    return [Location.model_validate(item) for item in result]


def parse_document_symbol_result(
    result: Any,
) -> list[DocumentSymbol] | list[SymbolInformation] | None:
    """Validate a ``textDocument/documentSymbol`` result.

    Parses the ``DocumentSymbol[] | SymbolInformation[] | null`` union;
    ``SymbolInformation`` entries are distinguished by their ``location`` field.
    """
    if result is None:
        return None
    if not result:
        return []
    if "location" in result[0]:
        return [SymbolInformation.model_validate(item) for item in result]
    return [DocumentSymbol.model_validate(item) for item in result]


def parse_document_highlight_result(
    result: Any,
) -> list[DocumentHighlight] | None:
    """Validate a ``textDocument/documentHighlight`` result into highlights."""
    if result is None:
        return None
    return [DocumentHighlight.model_validate(item) for item in result]


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

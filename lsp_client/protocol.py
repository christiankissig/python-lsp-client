"""
Incomplete implementation of the Language Server Protocol (LSP).

See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
for reference, and what a correct and complete implementation should look like.
"""

from typing import Any, List, Optional

from pydantic import BaseModel, Field

# global request ID
latest_request_id: int = 0


class BaseRequest(BaseModel):
    jsonrpc: str = Field(default="2.0")
    id: int
    method: str
    params: dict | None = Field(default=None)

    def __init__(self, **kwargs: Any) -> None:
        global latest_request_id
        latest_request_id += 1
        if "id" not in kwargs:
            kwargs["id"] = latest_request_id
        super(BaseRequest, self).__init__(**kwargs)


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
    workDoneToken: int | str


class ClientInfo(BaseModel):
    name: str
    version: str | None


class ClientCapabilities(BaseModel):
    workspace: dict | None
    textDocument: dict | None
    notebook: dict | None
    window: dict | None
    general: dict | None
    experimental: dict | None


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


class FileOperationsClientCapabilities:
    didCreate: dict | None
    willCreate: dict | None
    didRename: dict | None
    willRename: dict | None
    didDelete: dict | None
    willDelete: dict | None


class InitializeParams(WorkDoneProgressParams):
    processId: int
    clientInfo: ClientInfo
    rootPath: str | None
    rootUri: str
    initializationOptions: dict | None
    capabilities: ClientCapabilities
    trace: str | None
    workspaceFolders: list[dict] | None


class InitializeRequest(BaseRequest):
    method: str = "initialize"


# Text Document Synchronization
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_synchronization # noqa: E501


class TextDocumentItem(BaseModel):
    uri: str
    languageId: str
    version: int
    text: str


class TextDocument_DidOpen_Request(BaseRequest):
    def __init__(self, **kwargs: Any) -> None:
        kwargs["method"] = "textDocument/didOpen"
        super(TextDocument_DidOpen_Request, self).__init__(**kwargs)


class Position(BaseModel):
    line: int
    character: int


class Range(BaseModel):
    start: Position
    end: Position


class ContentChange(BaseModel):
    text: str
    range: Range
    rangeLength: int


class TextDocument_DidChange_Request(BaseRequest):
    def __init__(
        self, uri: str, version: str, contentChanges: List[ContentChange], **kwargs: Any
    ) -> None:
        kwargs["method"] = "textDocument/didChange"
        if "params" in kwargs:
            params = kwargs["params"]
        else:
            params = {}
        params["textDocument"] = {"uri": uri, "version": version}
        params["contentChanges"] = contentChanges
        kwargs["params"] = params
        super(TextDocument_DidChange_Request, self).__init__(**kwargs)


# $ Notifications and Requests
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#dollarRequests


class CancelRequest(BaseRequest):
    def __init__(self, language: str, **kwargs: Any) -> None:
        kwargs["method"] = f"{language}/cancelRequest"
        super(CancelRequest, self).__init__(**kwargs)


class ProgressParams(BaseModel):
    token: int | str
    value: dict


class ProgressNotification(BaseRequest):
    def __init__(self, language: str, **kwargs: Any) -> None:
        kwargs["method"] = f"{language}/progress"
        super(ProgressNotification, self).__init__(**kwargs)

"""
Incomplete implementation of the Language Server Protocol (LSP).

See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/
for reference, and what a correct and complete implementation should look like.
"""

# global request ID
id: int = 0


class BaseRequest:
    """
    Base class of a request object.
    """
    def __init__(self, method: str, params: dict):
        global id
        self.jsonrpc = "2.0"
        self.id = id
        self.method = method
        self.params = params
        id += 1

    def to_dict(self):
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.id,
            "method": self.method,
            "params": self.params
        }


class ProtocolError(Exception):
    """
    LSP Protocol related error.
    """

    def __init__(self, message, errors=None):
        """
        Initialize the exception with an error message and optional errors.

        Args:
            message (str): The error message to be displayed.
            errors (optional): Additional details or nested errors.
        """
        super().__init__(message)
        self.errors = errors

    def __str__(self):
        """
        Return a string representation of the error.

        Returns:
            str: The error message with additional details if available.
        """
        if self.errors:
            return f"{self.message} (Details: {self.errors})"
        return self.message


# Server Lifecycle
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#lifeCycleMessages

class WorkDoneProgressParams:
    """
    Work done progress parameters.
    """
    def __init__(self, workDoneToken: str | int):
        self.workDoneToken = workDoneToken

    def to_dict(self):
        return {
            "workDoneToken": self.workDoneToken
        }


class ClientInfo:
    """
    Client information.
    """
    def __init__(self, name: str, version: str | None):
        self.name = name
        self.version = version

    def to_dict(self):
        return {key: value for key, value in {
            "name": self.name,
            "version": self.version
        }.items() if value is not None}


class ClientCapabilities:
    def __init__(self,
                 workspace=None,
                 textDocument=None,
                 notebookDocument=None,
                 window=None,
                 general=None,
                 experimental=None,
                 ):
        self.workspace = workspace
        self.textDocument = textDocument
        self.notebookDocument = notebookDocument
        self.window = window
        self.general = general
        self.experimental = experimental

    def to_dict(self):
        return {key: value for key, value in {
            "workspace": self.workspace,
            "textDocument": self.textDocument,
            "notebookDocument": self.notebookDocument,
            "window": self.window,
            "general": self.general,
            "experimental": self.experimental
        }.items() if value is not None}


class TextDocumentClientCapabilities:
    def __init__(self,
                 synchronization=None,
                 completion=None,
                 hover=None,
                 signatureHelp=None,
                 declaration=None,
                 definition=None,
                 typeDefinition=None,
                 implementation=None,
                 references=None,
                 documentHighlight=None,
                 documentSymbol=None,
                 codeAction=None,
                 codeLens=None,
                 documentLink=None,
                 colorProvider=None,
                 formatting=None,
                 rangeFormatting=None,
                 onTypeFormatting=None,
                 rename=None,
                 publishDiagnostics=None,
                 foldingRange=None,
                 selectionRange=None,
                 linkedEditingRange=None,
                 callHierarchy=None,
                 semanticTokens=None,
                 moniker=None,
                 typeHierarchy=None,
                 inlineValue=None,
                 inlayHint=None,
                 diagnostic=None,
                 ):
        self.synchronization = synchronization
        self.completion = completion
        self.hover = hover
        self.signatureHelp = signatureHelp
        self.declaration = declaration
        self.definition = definition
        self.typeDefinition = typeDefinition
        self.implementation = implementation
        self.references = references
        self.documentHighlight = documentHighlight
        self.documentSymbol = documentSymbol
        self.codeAction = codeAction
        self.codeLens = codeLens
        self.documentLink = documentLink
        self.colorProvider = colorProvider
        self.formatting = formatting
        self.rangeFormatting = rangeFormatting
        self.onTypeFormatting = onTypeFormatting
        self.rename = rename
        self.publishDiagnostics = publishDiagnostics
        self.foldingRange = foldingRange
        self.selectionRange = selectionRange
        self.linkedEditingRange = linkedEditingRange
        self.callHierarchy = callHierarchy
        self.semanticTokens = semanticTokens
        self.moniker = moniker
        self.typeHierarchy = typeHierarchy
        self.inlineValue = inlineValue
        self.inlayHint = inlayHint
        self.diagnostic = diagnostic

    def to_dict(self):
        return {key: value for key, value in {
            "synchronization": self.synchronization,
            "completion": self.completion,
            "hover": self.hover,
            "signatureHelp": self.signatureHelp,
            "declaration": self.declaration,
            "definition": self.definition,
            "typeDefinition": self.typeDefinition,
            "implementation": self.implementation,
            "references": self.references,
            "documentHighlight": self.documentHighlight,
            "documentSymbol": self.documentSymbol,
            "codeAction": self.codeAction,
            "codeLens": self.codeLens,
            "documentLink": self.documentLink,
            "colorProvider": self.colorProvider,
            "formatting": self.formatting,
            "rangeFormatting": self.rangeFormatting,
            "onTypeFormatting": self.onTypeFormatting,
            "rename": self.rename,
            "publishDiagnostics": self.publishDiagnostics,
            "foldingRange": self.foldingRange,
            "selectionRange": self.selectionRange,
            "linkedEditingRange": self.linkedEditingRange,
            "callHierarchy": self.callHierarchy,
            "semanticTokens": self.semanticTokens,
            "moniker": self.moniker,
            "typeHierarchy": self.typeHierarchy,
            "inlineValue": self.inlineValue,
            "inlayHint": self.inlayHint,
            "diagnostic": self.diagnostic
        }.items() if value is not None}


class NotebookDocumentClientCapabilities:
    def __init__(self, synchronization):
        self.synchronization = synchronization

    def to_dict(self):
        return {
            "synchronization": self.synchronization
        }


class WorkspaceClientCapabilities:
    def __init__(self,
                 applyEdit=None,
                 workspaceEdit=None,
                 didChangeConfiguration=None,
                 didChangeWatchedFiles=None,
                 symbol=None,
                 executeCommand=None,
                 workspaceFolders=None,
                 configuration=None,
                 semanticTokens=None,
                 codeLens=None,
                 fileOperations=None,
                 inlineValue=None,
                 inlayHint=None,
                 diagnostics=None,
                 ):
        self.applyEdit = applyEdit
        self.workspaceEdit = workspaceEdit
        self.didChangeConfiguration = didChangeConfiguration
        self.didChangeWatchedFiles = didChangeWatchedFiles
        self.symbol = symbol
        self.executeCommand = executeCommand
        self.workspaceFolders = workspaceFolders
        self.configuration = configuration
        self.semanticTokens = semanticTokens
        self.codeLens = codeLens
        self.fileOperations = fileOperations
        self.inlineValue = inlineValue
        self.inlayHint = inlayHint
        self.diagnostics = diagnostics

    def to_dict(self):
        return {key: value for key, value in {
            "applyEdit": self.applyEdit,
            "workspaceEdit": self.workspaceEdit,
            "didChangeConfiguration": self.didChangeConfiguration,
            "didChangeWatchedFiles": self.didChangeWatchedFiles,
            "symbol": self.symbol,
            "executeCommand": self.executeCommand,
            "workspaceFolders": self.workspaceFolders,
            "configuration": self.configuration,
            "semanticTokens": self.semanticTokens,
            "codeLens": self.codeLens,
            "fileOperations": self.fileOperations,
            "inlineValue": self.inlineValue,
            "inlayHint": self.inlayHint,
            "diagnostics": self.diagnostics
        }.items() if value is not None}


class FileOperationsClientCapabilities:
    def __init__(self,
                 dynamicRegistration=None,
                 didCreate=None,
                 willCreate=None,
                 didRename=None,
                 willRename=None,
                 didDelete=None,
                 willDelete=None,
                 ):
        self.dynamicRegistration = dynamicRegistration
        self.didCreate = didCreate
        self.willCreate = willCreate
        self.didRename = didRename
        self.willRename = willRename
        self.didDelete = didDelete
        self.willDelete = willDelete

    def to_dict(self):
        return {key: value for key, value in {
            "dynamicRegistration": self.dynamicRegistration,
            "didCreate": self.didCreate,
            "willCreate": self.willCreate,
            "didRename": self.didRename,
            "willRename": self.willRename,
            "didDelete": self.didDelete,
            "willDelete": self.willDelete
        }.items() if value is not None}


class InitializeParams(WorkDoneProgressParams):
    """
    Initialize parameters.
    """
    def __init__(self,
                 workDoneToken: int | str,
                 processId: int,
                 clientInfo: ClientInfo,
                 rootPath: str | None,
                 rootUri: str,
                 initializationOptions: dict | None,
                 capabilities: ClientCapabilities,
                 trace: str | None,
                 workspaceFolders: list[dict] | None,
                 ):
        super().__init__(workDoneToken)
        self.processId = processId
        self.clientInfo = clientInfo
        self.rootPath = rootPath
        self.rootUri = rootUri
        self.initializationOptions = initializationOptions
        self.capabilities = capabilities
        self.trace = trace
        self.workspaceFolders = workspaceFolders

    def to_dict(self):
        return {key: value for key, value in {
            "workDoneToken": self.workDoneToken,
            "processId": self.processId,
            "clientInfo": self.clientInfo.to_dict(),
            "rootUri": self.rootUri,
            "initializationOptions": self.initializationOptions,
            "capabilities": self.capabilities.to_dict(),
            "trace": self.trace,
            "workspaceFolders": self.workspaceFolders
        }.items() if value is not None}


class InitializeRequest(BaseRequest):
    """
    "initialize" request.
    """
    def __init__(self, processId: str | None, params: dict):
        if processId is not None:
            params["processId"] = processId
        super().__init__("initialize", params)


# Text Document Synchronization
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#textDocument_synchronization # noqa: E501


class OpenTextDocumentRequest(BaseRequest):
    """
    "textDocument/didOpen" request.
    """
    def __init__(self, uri: str, text: str):
        method = "textDocument/didOpen"
        params = {
            "textDocument": {
                "uri": uri,
                "languageId": "isabelle",
                "version": 1,
                "text": text
            }
        }
        super().__init__(method, params)


class ContentChange:
    """
    Content change.

    Used for instance in "textDocument/didChange" requests.
    """
    def __init__(self,
                 text: str,
                 start_line: int,
                 start_character: int,
                 end_line: int,
                 end_character: int,
                 range_length: int):
        self.text = text
        self.start_line = start_line
        self.start_character = start_character
        self.end_line = end_line
        self.end_character = end_character
        self.range_length = range_length

    def to_dict(self):
        return {
            "range": {
                "start": {
                    "line": self.start_line,
                    "character": self.start_character
                },
                "end": {
                    "line": self.end_line,
                    "character": self.end_character
                }
            },
            "text": self.text,
            "rangeLength": self.range_length
        }


class TextDocument_DidChange_Request(BaseRequest):
    """
    "textDocument/didChange" request.
    """
    def __init__(
            self, uri: str,
            version: int,
            contentChanges: list[ContentChange]):
        method = "textDocument/didChange"
        params = {
            "textDocument": {
                "uri": uri,
                "version": version
            },
            "contentChanges": [
                change.to_dict() for change in contentChanges
            ]
        }
        super().__init__(method, params)


# $ Notifications and Requests
# See https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#dollarRequests

class CancelRequest(BaseRequest):
    """
    "$/cancelRequest" request.
    """
    def __init__(self, language: str, id: int | str):
        method = f"{language}/cancelRequest"
        params = {
            "id": id
        }
        super().__init__(method, params)


class ProgressParams:
    """
    Progress parameters.
    """
    def __init__(self, token: int | str, value: dict):
        self.token = token
        self.value = value

    def to_dict(self):
        return {
            "token": self.token,
            "value": self.value
        }

    @staticmethod
    def from_dict(dct: dict):
        try:
            return ProgressParams(
                    dct["token"],
                    dct["value"])
        except KeyError as e:
            raise ProtocolError("Invalid progress parameters.", e)


class ProgressNotification(BaseRequest):
    """
    "$/progress" request.
    """
    def __init__(self, language: str, progressParams: dict):
        method = f"{language}/progress"
        super().__init__(method, progressParams)

    @staticmethod
    def from_dict(dct: dict):
        try:
            return ProgressNotification(
                    dct["method"],
                    dct["params"])
        except KeyError as e:
            raise ProtocolError("Invalid progress notification.", e)

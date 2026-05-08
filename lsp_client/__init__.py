from .client import LSPClient
from .protocol import (
    BaseNotification,
    BaseRequest,
    CancelRequest,
    ContentChange,
    InitializeRequest,
    InitializedNotification,
    Position,
    ProgressNotification,
    ProgressParams,
    Range,
    TextDocumentDidChangeNotification,
    TextDocumentDidOpenNotification,
    TextDocumentItem,
    # Backwards-compatible aliases
    TextDocumentDidChangeRequest,
    TextDocumentDidOpenRequest,
    TextDocument_DidChange_Request,
    TextDocument_DidOpen_Request,
)

__all__ = [
    "Position",
    "Range",
    "BaseNotification",
    "BaseRequest",
    "CancelRequest",
    "ContentChange",
    "InitializeRequest",
    "InitializedNotification",
    "LSPClient",
    "ProgressNotification",
    "ProgressParams",
    "TextDocumentItem",
    "TextDocumentDidOpenNotification",
    "TextDocumentDidChangeNotification",
    # Backwards-compatible aliases
    "TextDocumentDidOpenRequest",
    "TextDocumentDidChangeRequest",
    "TextDocument_DidOpen_Request",
    "TextDocument_DidChange_Request",
]

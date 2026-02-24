from .client import LSPClient
from .protocol import (
    BaseRequest,
    CancelRequest,
    ContentChange,
    InitializeRequest,
    Position,
    ProgressNotification,
    ProgressParams,
    Range,
    TextDocumentDidChangeRequest,
    TextDocumentDidOpenRequest,
    TextDocumentItem,
    # Backwards-compatible aliases
    TextDocument_DidChange_Request,
    TextDocument_DidOpen_Request,
)

__all__ = [
    "Position",
    "Range",
    "BaseRequest",
    "CancelRequest",
    "ContentChange",
    "InitializeRequest",
    "LSPClient",
    "ProgressNotification",
    "ProgressParams",
    "TextDocumentItem",
    "TextDocumentDidOpenRequest",
    "TextDocumentDidChangeRequest",
    # Backwards-compatible aliases
    "TextDocument_DidOpen_Request",
    "TextDocument_DidChange_Request",
]

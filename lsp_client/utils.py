import codecs

DEFAULT_ENCODING = "utf-8"
DEFAULT_CONTENT_MIME_TYPE = "application/vscode-jsonrpc"
DEFAULT_CONTENT_TYPE = f"{DEFAULT_CONTENT_MIME_TYPE}; charset={DEFAULT_ENCODING}"


def is_valid_encoding(encoding: str) -> bool:
    try:
        encoding = codecs.lookup(encoding).name
    except LookupError:
        return False
    return True


def parse_content_type(content_type_string: str | None) -> tuple[str, str]:
    """
    Parses content type string and returns content type and encoding.

    Raises ValueError if content type is not supported.
    Raises EncodingError if the specified charset is invalid.
    """
    if content_type_string is not None:
        content_type_parts = content_type_string.split(";")
        content_type = content_type_parts[0].strip()
        # Compare against the bare MIME type, not the full header string
        if content_type != DEFAULT_CONTENT_MIME_TYPE:
            raise ValueError(f"Unsupported content type in {content_type_string}")
        if len(content_type_parts) > 1 and content_type_parts[1].strip().startswith(
            "charset="
        ):
            encoding = content_type_parts[1].split("=")[1].strip()
            if not is_valid_encoding(encoding):
                raise EncodingError(encoding)
        else:
            encoding = DEFAULT_ENCODING
        return (content_type, encoding)
    else:
        return (DEFAULT_CONTENT_MIME_TYPE, DEFAULT_ENCODING)


class EncodingError(Exception):
    def __init__(self, encoding: str):
        super().__init__(f"Invalid encoding: {encoding}")

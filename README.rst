Summary
=======

This repository contains a client implementation of the Language Server Protcol 
(LSP) in Python. The implementation aims to be correct with respect to the 
[https://github.com/microsoft/language-server-protocol](official specification).

Caveat
======

Until version 1, the implementation is incomplete and should not be used in
production environments.

Alternatives
============

Microsoft's 
[https://github.com/microsoft/monitors4codegen/tree/main/src/monitors4codegen/multilspy](monitors4codegen)
repository offers another implementation of LSP in Python, including a server
implementation for several popular languages.

Requirements
============

The implementation requires 
* Python 3.6 or later.

How to Build
============

Create a virtual environment

```
python3 -m venv python-lsp
source python-lsp/bin/activate
```

Build and install in virtual environment

```
pip install -e .
```


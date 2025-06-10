.. image:: https://github.com/christiankissig/python-lsp-client/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/christiankissig/python-lsp-client/actions/workflows/ci.yml
   :alt: CI/CD

Summary
=======

This repository contains a client implementation of the Language Server Protcol 
(LSP) in Python. The implementation aims to be correct with respect to the 
`official specification 
<https://github.com/microsoft/language-server-protocol>`_.

Caveat
======

Until version 1, the implementation is incomplete and should not be used in
production environments.

Alternatives
============

Microsoft's `multispy<https://github.com/microsoft/multilspy>`_
repository includes a server implementation of LSP in Python.

Yeger's python package `pyslpclient<https://github.com/yeger00/pylspclient>`_
offers a thread-safe client implementation of LSP in Python.

Requirements
============

The implementation requires 
* Python 3.6 or later.

How to Build
============

Create a virtual environment

::

  python3 -m venv python-lsp
  source python-lsp/bin/activate

Build and install in virtual environment

::

  pip install .



.. image:: https://github.com/christiankissig/python-lsp-client/actions/workflows/ci.yml/badge.svg
   :target: https://github.com/christiankissig/python-lsp-client/actions/workflows/ci.yml
   :alt: CI/CD

.. image:: https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue
   :target: https://www.python.org/
   :alt: Python versions

.. image:: https://img.shields.io/badge/license-MIT-green
   :target: https://github.com/christiankissig/python-lsp-client/blob/master/LICENSE
   :alt: License: MIT

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

yeger00's python package `pyslpclient<https://github.com/yeger00/pylspclient>`_
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

  poetry install

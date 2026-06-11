# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""genro-ws-web — WebSocket-driven reactive SPA framework in pure Python.

Describe a single-page application with the genro-builders HTML dialect
and pointer state; the framework renders it, tracks dependencies and
keeps the browser in sync over WebSocket.

Public surface:

- ``WsLiveApp`` — the ASGI application (startup page, WSX ``main`` and
  ``mutate``, server tickers).
- ``WsLivePage`` — the page base: subclass, override ``main(root)``.
- ``WsTargetWrapper`` — the connection-bound render destination.
- ``widgets`` — the effective widget kit (``HtmlComponentsBase``,
  ``HtmlContainersBase``).
"""

from __future__ import annotations

from .application import WsLiveApp
from .page import WsLivePage
from .target import WsTargetWrapper
from .widgets import DTYPE_KINDS, HtmlComponentsBase, HtmlContainersBase

__version__ = "0.1.0"

__all__ = [
    "DTYPE_KINDS",
    "HtmlComponentsBase",
    "HtmlContainersBase",
    "WsLiveApp",
    "WsLivePage",
    "WsTargetWrapper",
]

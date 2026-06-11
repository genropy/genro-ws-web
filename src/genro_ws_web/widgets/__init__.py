# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""The widget kit — collections to mix into an HtmlBuilder page.

``HtmlComponentsBase`` (closed input widgets, ``@component``) and
``HtmlContainersBase`` (fillable layout containers, ``@container``).
This is the EFFECTIVE kit of the SPA framework: the application
vocabulary (dtype write-back, client bindings, validation) grows here.
genro-builders keeps only a small didactic collection demonstrating
the component/container mechanics.
"""

from __future__ import annotations

from .components import DTYPE_KINDS, HtmlComponentsBase
from .containers import HtmlContainersBase

__all__ = ["DTYPE_KINDS", "HtmlComponentsBase", "HtmlContainersBase"]

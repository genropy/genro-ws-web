# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""colorpicker — the first web-component-backed collection (PoC).

The widget is a grammar ELEMENT, not a body component: the render
emits ONE tag (``<gnr-colorpicker>``, via ``_meta['render_tag']``)
and the internals live in the custom element next door
(``colorpicker.js``, declared in ``js_requires``): a shadow-DOM
``<input type=color>`` speaking the native input contract — a
``value`` property and composed bubbling ``input`` events — so the
kernel binds it like any input (value up by id, attribute patches
down). No body, no expansion, no server state: the machine is the
browser's.
"""
from __future__ import annotations

from genro_ws_web import webcomponent


class ColorPickerCollection:
    """Web-component widgets. Mix into a WsLivePage."""

    js_requires = ("colorpicker.js",)

    @webcomponent()
    def colorpicker(self):
        """A color picker custom element; ``value`` rides the pointer."""

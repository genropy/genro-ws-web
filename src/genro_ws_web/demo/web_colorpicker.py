# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Web-component colorpicker: the PoC of the element-backed widget.

Same two-way binding as the ``colorpicker`` demo, but the widget is
ONE grammar element rendered as ``<gnr-colorpicker>``: the custom
element (shadow DOM around a native color input) speaks the input
contract and the kernel binds it like any input — value up on
``input`` events, attribute patches down by id. The swatch and the
hex readout follow the same datum: pick a color, both react.
"""

from __future__ import annotations

from ..page import WsLivePage
from ..resources.components.colorpicker import ColorPickerCollection

PAGE_TITLE = "Colorpicker web component (PoC)"


class Page(WsLivePage, ColorPickerCollection):
    """A ``<gnr-colorpicker>`` whose value drives a swatch's border."""

    def setup(self, data):
        self.set_data("style.border", "#2c5f8a")

    def main(self, root):
        pane = root.div(datapath="style")
        pane.h1("Pick a border color — web component")
        pane.colorpicker(value="^.border")
        pane.div("Riquadro", class_="swatch", border_color="^.border")
        pane.div("^.border", font_family="monospace", margin_top="8px")

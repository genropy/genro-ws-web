# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component, single: one @component used several times.

``fieldRow`` is a closed component (CMP.1): the caller parameterizes
it, the expansion builds label + input. The reactive ``value`` pointer
passes through to the inner <input> (CMP.4) with its dtype on the
NODE: edit any field and the typed write lands at the pointer — the
summary recomputes server-side and comes back as a patch.
"""

from __future__ import annotations

from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Components 1 — single"


class Page(WsLivePage):
    @component
    def fieldRow(self, root, label="", value=None, dtype=None, **attrs):
        row = root.div(display="flex", gap="8px", align_items="center",
                       margin_bottom="6px")
        row.html_label(label, width="90px", color="#555555")
        kw = {"value": value, **attrs}
        if dtype:
            kw["dtype"] = dtype
        row.input(**kw)

    def setup(self, data):
        self.set_data("box.width", 30)
        self.set_data("box.height", 12)
        self.set_data("box.label", "Hello")

    def main(self, root):
        pane = root.div(datapath="box", max_width="420px")
        pane.h1("Single component")
        pane.p("One @component, used three times. Every input is an "
               "expansion node: the mutation travels by derived id, "
               "the node types it.")
        pane.fieldRow(label="Label", value="^.label")
        pane.fieldRow(label="Width", value="^.width", dtype="L",
                       html_type="number")
        pane.fieldRow(label="Height", value="^.height", dtype="L",
                       html_type="number")
        pane.dataFormula(destination=".area", func="box_area",
                          width="^.width", height="^.height",
                          _on_start=True)
        out = pane.p(padding="8px", background="#f0f4f8")
        out.span("${label}: ${width} x ${height} = area ${area}",
                 label="^.label", width="^.width", height="^.height",
                 area="^.area")

    @staticmethod
    def box_area(width, height):
        if not width or not height:
            return None
        return width * height

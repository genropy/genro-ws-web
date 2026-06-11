# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component, nested: a component that calls another component.

``titled_field`` builds a bordered box and calls ``field_row`` inside
its own expansion (CMP.8, fractal composability) — used several
times. The inner input's identity CHAINS through both expansions
(parent.child.grandchild): the mutation still resolves to the inner
node, where the dtype lives.
"""

from __future__ import annotations

from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Components 2 — nested"


class Page(WsLivePage):
    @component
    def field_row(self, root, label="", value=None, dtype=None, **attrs):
        row = root.div(display="flex", gap="8px", align_items="center")
        row.html_label(label, width="80px", color="#555555")
        kw = {"value": value, **attrs}
        if dtype:
            kw["dtype"] = dtype
        row.input(**kw)

    @component
    def titled_field(self, root, title="", value=None, dtype=None):
        box = root.div(border="1px solid #c8c8c8", border_radius="6px",
                       padding="8px", margin_bottom="8px")
        box.div(title, font_weight="600", margin_bottom="4px",
                color="#2c5f8a")
        box.field_row(label="value", value=value, dtype=dtype)

    def setup(self, data):
        self.set_data("trip.km", 420)
        self.set_data("trip.liters", 28)

    def main(self, root):
        pane = root.div(datapath="trip", max_width="420px")
        pane.h1("Nested components")
        pane.p("titled_field calls field_row inside its expansion: the "
               "input id chains through both levels.")
        pane.titled_field(title="Distance (km)", value="^.km", dtype="L")
        pane.titled_field(title="Fuel (liters)", value="^.liters",
                          dtype="N")
        pane.data_formula(destination=".consumption", func="consumption",
                          km="^.km", liters="^.liters", _on_start=True)
        out = pane.p(padding="8px", background="#f0f4f8")
        out.span("${km} km with ${liters} l = ${consumption} km/l",
                 km="^.km", liters="^.liters",
                 consumption="^.consumption")

    @staticmethod
    def consumption(km, liters):
        if not km or not liters:
            return None
        return round(float(km) / float(liters), 1)

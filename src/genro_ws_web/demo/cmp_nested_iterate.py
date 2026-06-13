# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Components, nested iterates: regions iterating their states.

``regionBlock`` iterates ``^regions`` and, INSIDE its expansion,
``stateLine`` iterates that region's ``^.states``: the id chain
crosses two stores (base.REGION.ord.STATE.ord). Edit any state — only
its datum moves, and the grand total recomputes.
"""

from __future__ import annotations

from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Components 4 — nested iterate"


class Page(WsLivePage):
    @component
    def stateLine(self, root, node_label=None):
        line = root.div(datapath="." + node_label, display="flex",
                        gap="8px", align_items="center",
                        margin="2px 0 2px 16px")
        line.html_label(node_label, width="48px", font_weight="600")
        line.input(value="^.name")
        line.input(value="^.population", dtype="L", html_type="number",
                   width="100px")

    @component
    def regionBlock(self, root, node_label=None):
        block = root.div(datapath="." + node_label,
                         border="1px solid #c8c8c8", border_radius="6px",
                         padding="8px", margin_bottom="8px")
        block.div("^.title", font_weight="600", color="#2c5f8a",
                  margin_bottom="4px")
        block.stateLine(iterate="^.states")

    def setup(self, data):
        seed = {
            "EAST": ("East coast", (("NSW", "New South Wales", 8166000),
                                    ("QLD", "Queensland", 5260000))),
            "SOUTH": ("South", (("VIC", "Victoria", 6681000),
                                ("TAS", "Tasmania", 572000))),
        }
        for region, (title, states) in seed.items():
            self.set_data(f"regions.{region}.title", title)
            for code, name, pop in states:
                self.set_data(f"regions.{region}.states.{code}.name", name)
                self.set_data(
                    f"regions.{region}.states.{code}.population", pop,
                )

    def main(self, root):
        pane = root.div(max_width="520px")
        pane.h1("Nested iterates")
        pane.p("Regions iterate their states: the id chain crosses two "
               "stores. Every input addresses its own row, two levels "
               "deep.")
        pane.regionBlock(iterate="^regions")
        pane.dataFormula(destination="total", func="grand_total",
                          regions="^regions", _on_start=True)
        out = pane.p(padding="8px", background="#f0f4f8")
        out.span("Grand total: ${total}", total="^total")

    @staticmethod
    def grand_total(regions):
        if regions is None:
            return 0
        total = 0
        for region in regions.values():
            states = region["states"]
            if states is None:
                continue
            total += sum(row["population"] or 0 for row in states.values())
        return total

# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component, iterated: one declaration, one expansion per store row.

``stateRow`` iterates the ``^states`` store: the row identity is the
bag LABEL (VIC, NSW, ...) and it enters the derived id chain — every
input is individually addressable. Edit a name or a population: only
THAT row's datum changes; the totals recompute server-side.
"""

from __future__ import annotations

from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Components 3 — iterate"


class Page(WsLivePage):
    @component
    def stateRow(self, root, node_label=None):
        row = root.tr(datapath="." + node_label)
        row.td(node_label, font_weight="600", padding="4px 10px")
        cell_name = row.td(padding="4px 10px")
        cell_name.input(value="^.name")
        cell_pop = row.td(padding="4px 10px")
        cell_pop.input(value="^.population", dtype="L",
                       html_type="number", width="110px")

    def setup(self, data):
        for code, name, pop in (
            ("NSW", "New South Wales", 8166000),
            ("QLD", "Queensland", 5260000),
            ("VIC", "Victoria", 6681000),
        ):
            self.set_data(f"states.{code}.name", name)
            self.set_data(f"states.{code}.population", pop)

    def main(self, root):
        pane = root.div(max_width="520px")
        pane.h1("Iterated component")
        pane.p("One source node, one expansion per row of the store: "
               "the row label (the bag label) is the row identity in "
               "the id chain.")
        table = pane.table(border_collapse="collapse")
        head = table.tr()
        for caption in ("Code", "Name", "Population"):
            head.th(caption, text_align="left", padding="4px 10px",
                    border_bottom="2px solid #c8c8c8")
        table.stateRow(iterate="^states")
        pane.dataFormula(destination="total", func="total_population",
                          states="^states", _on_start=True)
        out = pane.p(padding="8px", background="#f0f4f8")
        out.span("Total population: ${total}", total="^total")

    @staticmethod
    def total_population(states):
        if states is None:
            return 0
        return sum(row["population"] or 0 for row in states.values())

# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Scale demos, shared shape: one grid, N rows, the invoice row logic.

Three pages (``scale_30`` / ``scale_300`` / ``scale_3000``) subclass
this base declaring only ``rows_count``: same grid, same rules, three
orders of magnitude. The point is to FEEL what each mutation costs
while the patch unit for expansions is the whole enclosing grid
(CMP.7 "per ora"): a qty edit recomputes ONE row but re-renders and
ships ALL of them; the rate in the header recomputes every row by
design (shared binding). The per-row patches of the RX roadmap will
be measured against these same pages.

This module exposes no ``Page``: the auto-discovery skips it.
"""

from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder import component

from ..page import WsLivePage

_COLUMNS = (
    ("Row", "gnr-grid-cell"),
    ("Name", "gnr-grid-cell"),
    ("Qty", "gnr-grid-cell gnr-grid-num"),
    ("Price", "gnr-grid-cell gnr-grid-num"),
    ("Total", "gnr-grid-cell gnr-grid-num"),
    ("Converted", "gnr-grid-cell gnr-grid-num"),
    ("", "gnr-grid-cell"),
)


class ScaleGridPage(WsLivePage):
    """The shared scale grid; subclasses declare ``rows_count``."""

    rows_count = 0

    @component
    def scale_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label, class_="gnr-grid-row")
        row.div(node_label, class_="gnr-grid-cell", font_weight="600")
        row.div("^.name", class_="gnr-grid-cell")
        row.div(class_="gnr-grid-cell gnr-grid-num").input(
            value="^.qty", dtype="L", html_type="number")
        row.div(class_="gnr-grid-cell gnr-grid-num").input(
            value="^.price", dtype="N", html_type="number")
        row.div("^.total", class_="gnr-grid-cell gnr-grid-num")
        row.div("^.converted", class_="gnr-grid-cell gnr-grid-num",
                color="#2c5f8a")
        commands = row.div(class_="gnr-grid-cell")
        commands.button("+", class_="gnr-grid-ins",
                        title="insert a row above this one",
                        **{"data-fire-pointer": "commands.ins_row",
                           "data-fire-value": node_label})
        commands.button("−", class_="gnr-grid-del", title="remove this row",
                        **{"data-fire-pointer": "commands.del_row",
                           "data-fire-value": node_label})
        row.data_formula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.data_formula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        self.set_data("header.rate", 0.89)
        for n in range(1, self.rows_count + 1):
            qty = n % 9 + 1
            price = float(n % 50 + 1)
            total = round(qty * price, 2)
            row = Bag()
            row["name"] = f"Item {n}"
            row["qty"] = qty
            row["price"] = price
            row["total"] = total
            row["converted"] = round(total * 0.89, 2)
            data.set_item(f"rows.r{n}", row)

    def main(self, root):
        pane = root.div(max_width="820px")
        pane.h1(f"Scale — {self.rows_count} rows")
        header = pane.div(display="flex", gap="12px",
                          align_items="center", padding="8px",
                          background="#f0f4f8", margin_bottom="8px")
        header.html_label("Rate (recomputes EVERY row)", color="#555555")
        header.input(value="^header.rate", dtype="N",
                     html_type="number", step="0.01", width="80px")
        pane.button("+ add row", class_="gnr-grid-add",
                    **{"data-fire-pointer": "commands.add_row"})
        grid = pane.div(
            class_="gnr-grid gnr-grid-scroll gnr-grid-pin scale-grid")
        head = grid.div(class_="gnr-grid-row gnr-grid-head")
        for caption, klass in _COLUMNS:
            head.div(caption, class_=klass)
        grid.scale_row(iterate="^rows")
        # The grid footer: sticky with the scroll, the totals live in
        # their own columns.
        foot = grid.div(class_="gnr-grid-row gnr-grid-footrow")
        foot.div("Totals", class_="gnr-grid-cell")
        foot.div(class_="gnr-grid-cell")
        foot.div(class_="gnr-grid-cell")
        foot.div(class_="gnr-grid-cell")
        foot.div("^grand.total", class_="gnr-grid-cell gnr-grid-num")
        foot.div("^grand.converted", class_="gnr-grid-cell gnr-grid-num")
        foot.div(class_="gnr-grid-cell")
        pane.data_controller(func="add_row", trigger="^commands.add_row")
        pane.data_controller(func="ins_row", label="^commands.ins_row")
        pane.data_controller(func="del_row", label="^commands.del_row")
        pane.data_formula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)
        pane.data_formula(destination="grand.converted",
                          func="grand_converted", rows="^rows",
                          _on_start=True)

    @staticmethod
    def add_row(node, trigger=None):
        if not trigger:
            return
        rows = node.GET("rows")
        ordinal = 1 + max(
            (int(lbl[1:]) for lbl in rows.keys() if lbl[1:].isdigit()),
            default=0,
        )
        row = Bag()
        row["name"] = f"Item {ordinal}"
        row["qty"] = 1
        row["price"] = 0.0
        row["total"] = 0.0
        row["converted"] = 0.0
        node.SET(f"rows.r{ordinal}", row)

    @staticmethod
    def ins_row(node, label=None):
        """Insert a fresh row ABOVE the clicked one: the bag places by
        position (identity stays rN — identity is not position)."""
        if not label:
            return
        rows = node.GET("rows")
        ordinal = 1 + max(
            (int(lbl[1:]) for lbl in rows.keys() if lbl[1:].isdigit()),
            default=0,
        )
        row = Bag()
        row["name"] = f"Item {ordinal}"
        row["qty"] = 1
        row["price"] = 0.0
        row["total"] = 0.0
        row["converted"] = 0.0
        node.data_handler.data.set_item(
            node.abs_datapath(f"rows.r{ordinal}"), row,
            node_position=f"<{label}",
        )

    @staticmethod
    def del_row(node, label=None):
        if not label:
            return
        node.data_handler.data.pop(node.abs_datapath(f"rows.{label}"))

    @staticmethod
    def row_total(qty, price):
        if qty is None or price is None:
            return None
        return round(float(qty) * float(price), 2)

    @staticmethod
    def convert(total, rate):
        if total is None or rate is None:
            return None
        return round(float(total) * float(rate), 2)

    @staticmethod
    def grand_total(rows):
        if rows is None:
            return 0
        return round(sum(float(r["total"] or 0) for r in rows.values()), 2)

    @staticmethod
    def grand_converted(rows):
        if rows is None:
            return 0
        return round(
            sum(float(r["converted"] or 0) for r in rows.values()), 2,
        )

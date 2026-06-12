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
    ("Row", "gnr-grid-cell gnr-grid-pinned"),
    ("Name", "gnr-grid-cell gnr-grid-pinned"),
    ("Qty", "gnr-grid-cell gnr-grid-num"),
    ("Price", "gnr-grid-cell gnr-grid-num"),
    ("Total", "gnr-grid-cell gnr-grid-num"),
    ("Converted", "gnr-grid-cell gnr-grid-num"),
)


class ScaleGridPage(WsLivePage):
    """The shared scale grid; subclasses declare ``rows_count``."""

    rows_count = 0

    @component
    def scale_row(self, root, node_label=None):
        # The row IS a selector: the click writes its label into the
        # selection path (set-pointer lane, absolute by construction:
        # the segment is the page name). The visual state rides the
        # row's own _selected mark, moved by the select_row controller.
        row = root.div(
            datapath="." + node_label, class_="gnr-grid-row",
            **{"data-set-pointer": f"{self.name}.selection.row",
               "data-set-value": node_label,
               "data-selected-row": "^._selected"})
        row.div(node_label, class_="gnr-grid-cell gnr-grid-pinned",
                font_weight="600")
        row.div(class_="gnr-grid-cell gnr-grid-pinned").input(
            value="^.name")
        row.div(class_="gnr-grid-cell gnr-grid-num").input(
            value="^.qty", dtype="L", html_type="number")
        row.div(class_="gnr-grid-cell gnr-grid-num").input(
            value="^.price", dtype="N", html_type="number")
        row.div("^.total", class_="gnr-grid-cell gnr-grid-num")
        row.div("^.converted", class_="gnr-grid-cell gnr-grid-num",
                color="#2c5f8a")
        row.data_formula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.data_formula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        self.set_data("header.rate", 0.89)
        # The numeric data declares its own presentation (mask, fixed
        # decimals): every reader — full render, row replace, cell
        # patch — shows the datum the way the datum says.
        data.set_item("grand.total", 0.0, mask="%.2f")
        data.set_item("grand.converted", 0.0, mask="%.2f")
        for n in range(1, self.rows_count + 1):
            qty = n % 9 + 1
            price = float(n % 50 + 1)
            total = round(qty * price, 2)
            row = Bag()
            row["name"] = f"Item {n}"
            row["qty"] = qty
            row.set_item("price", price, mask="%.2f")
            row.set_item("total", total, mask="%.2f")
            row.set_item("converted", round(total * 0.89, 2), mask="%.2f")
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
        header.html_label("Selected", color="#555555", margin_left="16px")
        header.span("^selection.row", font_weight="600")
        pane.button("+ add row", class_="gnr-grid-add",
                    **{"data-fire-pointer": "commands.add_row"})
        # The legacy tris: a toolbar command with NO payload — the
        # controller reads the selection itself (passive binding).
        pane.button("− remove selected", class_="gnr-grid-add",
                    **{"data-fire-pointer": "commands.del_selected"})
        grid = pane.div(
            class_="gnr-grid gnr-grid-scroll scale-grid")
        # Three-box layout: header edge / scrolling body / footer edge.
        # The edges hide their overflow and mirror the body's
        # horizontal scroll (genro.js); the rows inside keep the
        # template min-width, so the tracks align by construction.
        head = grid.div(class_="gnr-grid-edge").div(
            class_="gnr-grid-row gnr-grid-head")
        for caption, klass in _COLUMNS:
            head.div(caption, class_=klass)
        # The data body is the ONLY scrolling box (both axes): the
        # scrollbars live between header and footer. Side benefit: it
        # is also the iterate's enclosing element — a coalesced
        # broadcast replaces the body, never header or footer.
        # Store-backed lazy: the collection lives in the store and
        # stays fully editable; the render pages with the scroll.
        grid.div(class_="gnr-grid-body").scale_row(
            iterate="^rows", lazy=True, id="rows")
        # The grid footer: the totals live in their own columns.
        foot = grid.div(class_="gnr-grid-edge").div(
            class_="gnr-grid-row gnr-grid-footrow")
        foot.div("Totals", class_="gnr-grid-cell gnr-grid-pinned")
        foot.div(class_="gnr-grid-cell gnr-grid-pinned")
        foot.div(class_="gnr-grid-cell")
        foot.div(class_="gnr-grid-cell")
        foot.div("^grand.total", class_="gnr-grid-cell gnr-grid-num")
        foot.div("^grand.converted", class_="gnr-grid-cell gnr-grid-num")
        pane.data_controller(func="add_row", trigger="^commands.add_row",
                             label="=selection.row")
        pane.data_controller(func="ins_row", label="^commands.ins_row")
        pane.data_controller(func="del_row", label="^commands.del_row")
        pane.data_controller(func="select_row", selected="^selection.row")
        pane.data_controller(func="del_selected",
                             trigger="^commands.del_selected",
                             label="=selection.row")
        pane.data_formula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)
        pane.data_formula(destination="grand.converted",
                          func="grand_converted", rows="^rows",
                          _on_start=True)

    @staticmethod
    def add_row(node, trigger=None, label=None):
        """The toolbar "+": a fresh row AFTER the selected one (the
        selection is a passive binding, read at compute time, like
        del_selected); with no selection the row appends at the end."""
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
        row.set_item("price", 0.0, mask="%.2f")
        row.set_item("total", 0.0, mask="%.2f")
        row.set_item("converted", 0.0, mask="%.2f")
        if label and node.GET(f"rows.{label}") is not None:
            node.data_handler.data.set_item(
                node.abs_datapath(f"rows.r{ordinal}"), row,
                node_position=f">{label}",
            )
        else:
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
        row.set_item("price", 0.0, mask="%.2f")
        row.set_item("total", 0.0, mask="%.2f")
        row.set_item("converted", 0.0, mask="%.2f")
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
    def select_row(node, selected=None):
        """Move the _selected mark to the new row: two writes, two
        per-row patches — the rest of the grid never travels."""
        previous = node.GET("selection.marked")
        if previous == selected:
            return
        if previous and node.GET(f"rows.{previous}") is not None:
            node.SET(f"rows.{previous}._selected", None)
        if selected and node.GET(f"rows.{selected}") is not None:
            node.SET(f"rows.{selected}._selected", True)
        node.PUT("selection.marked", selected)

    @staticmethod
    def del_selected(node, trigger=None, label=None):
        """The toolbar command carries no payload: the selection IS the
        argument (passive binding, read at compute time)."""
        if not trigger or not label:
            return
        node.data_handler.data.pop(node.abs_datapath(f"rows.{label}"))
        node.SET("selection.row", None)

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

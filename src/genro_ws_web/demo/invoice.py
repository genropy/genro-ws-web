# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Invoice page: header + rows, row logic and the page command.

The real-world shape: the document loads COMPLETE (totals already
right, trusted as-is — nothing recomputes at render). The row rules
are rules of MUTATION:

- edit qty or price -> THAT row recomputes total, then converted
  (the rule chain cascades inside the row);
- edit the exchange rate in the HEADER -> EVERY row recomputes its
  converted amount (a shared binding resolves to the same path for
  all rows: one event, N rows);
- the grand totals are canonical page-level formulas reading the
  store.

The +/− buttons are PAGE COMMANDS — the fire lane of the wire: the
click sends only the element id, the server node declares the fired
path (and, for the per-row "−", the message: the row label, baked at
expansion). A data_controller bound to the fired path performs the
STRUCTURAL store op; the iterate block re-renders because the store
changed. Layout: a CSS grid in the legacy-grid look (one column
template shared by header and rows — classes in ws_live.css).
"""

from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Invoice (row logic)"

_COLUMNS = (
    ("Row", "inv-cell"),
    ("Description", "inv-cell"),
    ("Price", "inv-cell inv-num"),
    ("Qty", "inv-cell inv-num"),
    ("Total", "inv-cell inv-num"),
    ("Converted", "inv-cell inv-num"),
    ("", "inv-cell"),
)


class Page(WsLivePage):
    @component
    def invoice_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label, class_="inv-row")
        row.div(node_label, class_="inv-cell", font_weight="600")
        row.div(class_="inv-cell").input(value="^.description")
        row.div(class_="inv-cell inv-num").input(value="^.price", dtype="N",
                                                 html_type="number")
        row.div(class_="inv-cell inv-num").input(value="^.qty", dtype="L",
                                                 html_type="number")
        row.div("^.total", class_="inv-cell inv-num")
        row.div("^.converted", class_="inv-cell inv-num", color="#2c5f8a")
        # The per-row command: the message (WHICH row) is the node's
        # own attribute, baked at expansion — the click is identity.
        row.button("−", class_="inv-del", title="remove this row",
                   **{"data-fire-pointer": "commands.del_row",
                      "data-fire-value": node_label})
        # Row rules: mutation-only (the loaded document is trusted).
        row.data_formula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.data_formula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        self.set_data("header.currency", "EUR -> USD")
        self.set_data("header.rate", 0.89)
        rows = (
            ("r1", "Keyboard", 2, 80.0),
            ("r2", "Monitor", 3, 240.0),
            ("r3", "Dock station", 20, 45.0),
        )
        for label, description, qty, price in rows:
            total = qty * price
            self.set_data(f"rows.{label}.description", description)
            self.set_data(f"rows.{label}.qty", qty)
            self.set_data(f"rows.{label}.price", price)
            self.set_data(f"rows.{label}.total", total)
            self.set_data(f"rows.{label}.converted",
                          round(total * 0.89, 2))

    def main(self, root):
        pane = root.div(max_width="720px")
        pane.h1("Invoice")
        header = pane.div(display="flex", gap="12px",
                          align_items="center", padding="8px",
                          background="#f0f4f8", margin_bottom="8px")
        header.html_label("Currency", color="#555555")
        header.span("^header.currency", font_weight="600")
        header.html_label("Rate", color="#555555", margin_left="16px")
        header.input(value="^header.rate", dtype="N",
                     html_type="number", step="0.01", width="80px")
        grid = pane.div(class_="inv-grid")
        head = grid.div(class_="inv-row inv-head")
        for caption, klass in _COLUMNS:
            head.div(caption, class_=klass)
        grid.invoice_row(iterate="^rows")
        # The page command, footer side: no declared message — the
        # fired value defaults to True (the command needs no payload).
        pane.button("+ add row", class_="inv-add",
                    **{"data-fire-pointer": "commands.add_row"})
        pane.data_controller(func="add_row", trigger="^commands.add_row")
        pane.data_controller(func="del_row", label="^commands.del_row")
        pane.data_formula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)
        pane.data_formula(destination="grand.converted",
                          func="grand_converted", rows="^rows",
                          _on_start=True)
        out = pane.p(class_="inv-foot")
        out.span("Grand total: ${total} — converted: ${converted}",
                 total="^grand.total", converted="^grand.converted")

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
        row["description"] = ""
        row["qty"] = 1
        row["price"] = 0.0
        row["total"] = 0.0
        row["converted"] = 0.0
        node.SET(f"rows.r{ordinal}", row)

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

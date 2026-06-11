# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Invoice page: header + rows, with per-row logic on the store.

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
"""

from __future__ import annotations

from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Invoice (row logic)"

_CELL = {"padding": "4px 10px"}


class Page(WsLivePage):
    @component
    def invoice_row(self, root, node_label=None):
        row = root.tr(datapath="." + node_label)
        row.td(node_label, font_weight="600", **_CELL)
        row.td(**_CELL).input(value="^.description", width="160px")
        row.td(**_CELL).input(value="^.price", dtype="N",
                              html_type="number", width="80px")
        row.td(**_CELL).input(value="^.qty", dtype="L",
                              html_type="number", width="60px")
        row.td("^.total", text_align="right", **_CELL)
        row.td("^.converted", text_align="right", color="#2c5f8a",
               **_CELL)
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
        pane = root.div(max_width="640px")
        pane.h1("Invoice")
        header = pane.div(display="flex", gap="12px",
                          align_items="center", padding="8px",
                          background="#f0f4f8", margin_bottom="8px")
        header.html_label("Currency", color="#555555")
        header.span("^header.currency", font_weight="600")
        header.html_label("Rate", color="#555555", margin_left="16px")
        header.input(value="^header.rate", dtype="N",
                     html_type="number", step="0.01", width="80px")
        table = pane.table(border_collapse="collapse")
        head = table.tr()
        for caption in ("Row", "Description", "Price", "Qty", "Total",
                        "Converted"):
            head.th(caption, text_align="left", padding="4px 10px",
                    border_bottom="2px solid #c8c8c8")
        table.invoice_row(iterate="^rows")
        pane.data_formula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)
        pane.data_formula(destination="grand.converted",
                          func="grand_converted", rows="^rows",
                          _on_start=True)
        out = pane.p(padding="8px", background="#f0f4f8",
                     text_align="right")
        out.span("Grand total: ${total} — converted: ${converted}",
                 total="^grand.total", converted="^grand.converted")

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

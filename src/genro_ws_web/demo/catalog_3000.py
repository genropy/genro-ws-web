# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Catalog demo, 3000 rows: the lazy iterate end to end.

The anchor holds a ``read_only`` resolver (the query — the freezed
selection) and the iterate opts in with ``lazy=True``: the first paint
ships page 0 plus the marker, genro.js fabricates the placeholders
(min-height = the measured average of the real page-0 rows) and asks a
page when an empty one enters the viewport — the marker fired with the
page number, on the one mutation road; the ``page`` op comes back with
the rendered blocks. Immutable rows: no writeback, no rules — the row
click is a selection (set-pointer lane), shown in the header.
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver
from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "Catalog — 3000 rows, lazy"

_COLUMNS = (
    ("Code", "gnr-grid-cell"),
    ("Name", "gnr-grid-cell"),
    ("Price", "gnr-grid-cell gnr-grid-num"),
)


class Page(WsLivePage):
    rows_count = 3000

    @component
    def catalogRow(self, root, node_label=None):
        row = root.div(datapath="." + node_label, class_="gnr-grid-row",
                       **{"data-set-pointer": f"{self.name}.selection.row",
                          "data-set-value": node_label})
        row.div(node_label, class_="gnr-grid-cell", font_weight="600")
        row.div("^.name", class_="gnr-grid-cell")
        row.div("^.price", class_="gnr-grid-cell gnr-grid-num")

    def setup(self, data):
        # ALL the author writes for lazy: the query on the anchor...
        data.set_item(
            "catalog", BagCbResolver(self.load_catalog, read_only=True),
        )

    def main(self, root):
        pane = root.div(max_width="720px")
        pane.h1(f"Catalog — {self.rows_count} rows, lazy")
        header = pane.div(display="flex", gap="12px",
                          align_items="center", padding="8px",
                          background="#f0f4f8", margin_bottom="8px")
        header.html_label("Selected", color="#555555")
        header.span("^selection.row", font_weight="600")
        grid = pane.div(class_="gnr-grid gnr-grid-scroll catalog-grid")
        head = grid.div(class_="gnr-grid-edge").div(
            class_="gnr-grid-row gnr-grid-head")
        for caption, klass in _COLUMNS:
            head.div(caption, class_=klass)
        # ...and lazy=True on the iterate. The rest is machinery.
        grid.div(class_="gnr-grid-body").catalogRow(
            iterate="^catalog", lazy=True, id="catalog")

    def load_catalog(self):
        """The query, run ONCE at first render (the freezed selection)."""
        rows = Bag()
        for i in range(1, self.rows_count + 1):
            rows[f"p{i:04d}.name"] = f"Product {i}"
            rows.set_item(f"p{i:04d}.price",
                          round((i % 90) + i / 100, 2), mask="%.2f")
        return rows

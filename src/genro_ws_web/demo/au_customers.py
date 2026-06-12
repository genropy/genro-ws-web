# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""AU customers: the read_only lazy iterate on a REAL query.

The anchor holds a ``read_only`` resolver wrapping a legacy-instance
query (``invc.customer`` — the Australian invoicing world); ``state``
is a resolver PARAMETER carried as a node attribute: genro-bag merges
``node.attr`` into the resolver kwargs, so re-parameterizing is one
attribute write. The state bar writes the selection, a controller
copies it onto the anchor attribute — the component re-renders: fresh
query, fresh parking (the freezed selection), fresh marker, and the
client rebuilds its placeholders. Pages follow the scroll as in the
catalog demo. Immutable rows: no writeback, no rules; the row click
picks a customer (set-pointer lane).
"""

from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver
from genro_builders.builder import component

from ..page import WsLivePage

PAGE_TITLE = "AU customers (lazy, by state)"

_COLUMNS = (
    ("Account", "gnr-grid-cell"),
    ("Suburb", "gnr-grid-cell"),
    ("State", "gnr-grid-cell"),
    ("Postcode", "gnr-grid-cell"),
)


class Page(WsLivePage):
    requires_db = True

    @component
    def customer_row(self, root, node_label=None):
        row = root.div(
            datapath="." + node_label, class_="gnr-grid-row",
            **{"data-set-pointer": f"{self.name}.selection.customer",
               "data-set-value": node_label})
        row.div("^.account_name", class_="gnr-grid-cell")
        row.div("^.suburb", class_="gnr-grid-cell")
        row.div("^.state", class_="gnr-grid-cell")
        row.div("^.postcode", class_="gnr-grid-cell")

    def setup(self, data):
        # The query lives on the anchor. ``state`` is declared as a
        # RESOLVER parameter (construction default None = no filter):
        # only declared parameters pick up their node-attribute
        # override — that is the re-parameterization lane the state
        # bar writes on.
        data.set_item(
            "customers",
            BagCbResolver(self.load_customers, read_only=True, state=None),
        )

    def main(self, root):
        with self.db_access() as db:
            states = [dict(r) for r in db.table("invc.state").query(
                columns="code,name", order_by="$code",
            ).fetch()]
        pane = root.div(max_width="820px")
        pane.h1("Australian customers — lazy, by state")
        bar = pane.div(display="flex", gap="8px", align_items="center",
                       padding="8px", background="#f0f4f8",
                       margin_bottom="8px", flex_wrap="wrap")
        # The state bar: every button writes the same selection path;
        # "All" declares no value (writes None = no filter).
        bar.button("All", class_="gnr-grid-add",
                   **{"data-set-pointer": f"{self.name}.selection.state"})
        for state in states:
            bar.button(state["code"], class_="gnr-grid-add",
                       title=state["name"],
                       **{"data-set-pointer":
                          f"{self.name}.selection.state",
                          "data-set-value": state["code"]})
        info = pane.div(display="flex", gap="12px", padding="4px 8px",
                        margin_bottom="8px")
        info.html_label("State", color="#555555")
        info.span("^selection.state", font_weight="600")
        info.html_label("Picked", color="#555555", margin_left="16px")
        info.span("^selection.customer", font_weight="600")
        grid = pane.div(class_="gnr-grid gnr-grid-scroll au-grid")
        head = grid.div(class_="gnr-grid-edge").div(
            class_="gnr-grid-row gnr-grid-head")
        for caption, klass in _COLUMNS:
            head.div(caption, class_=klass)
        grid.div(class_="gnr-grid-body").customer_row(
            iterate="^customers", lazy=True, id="customers")
        # The state click re-parameterizes the anchor: one attribute
        # write, and the lazy component re-renders — re-query included.
        pane.data_controller(func="set_state", state="^selection.state")

    @staticmethod
    def set_state(node, state=None):
        # "All" writes the EMPTY string, not None: a None attribute is
        # removed, and the resolver would fall back to its LAST params
        # (genro-bag: changed arguments become the new state). The
        # empty string is a real attribute and a falsy filter.
        node.SET("customers?state", state or "")

    def load_customers(self, state=None):
        """The query — run ONCE per (re)render of the lazy component."""
        with self.db_access() as db:
            fetched = db.table("invc.customer").query(
                columns="account_name,suburb,state,postcode",
                where="$state = :st" if state else None,
                st=state, order_by="$account_name",
            ).fetch()
            rows = Bag()
            for i, record in enumerate(fetched, start=1):
                row = Bag()
                row["account_name"] = record["account_name"]
                row["suburb"] = record["suburb"]
                row["state"] = record["state"]
                row["postcode"] = record["postcode"]
                rows[f"r{i:04d}"] = row
        return rows

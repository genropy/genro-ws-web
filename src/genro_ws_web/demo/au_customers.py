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
    ("Inv.", "gnr-grid-cell gnr-grid-num"),
    ("Invoiced", "gnr-grid-cell gnr-grid-num"),
)

#: the editable customer fields, dialog and save share the list
_FIELDS = ("account_name", "street_address", "suburb", "postcode",
           "email", "phone")


class Page(WsLivePage):
    requires_db = True

    @component
    def customerRow(self, root, node_label=None):
        # The row label IS the record pkey: the identity baked on the
        # row is directly the key of any per-record command.
        row = root.div(
            datapath="." + node_label, class_="gnr-grid-row",
            **{"data-set-pointer": f"{self.name}.selection.customer",
               "data-set-value": node_label})
        # One node, one verb: the row keeps the single-click selection,
        # the first cell carries the DOUBLE-click command (data-fire-on
        # is client guidance — the wire stays an ordinary {id, value}).
        row.div("^.account_name", class_="gnr-grid-cell",
                **{"data-fire-pointer": "commands.edit_customer",
                   "data-fire-value": node_label,
                   "data-fire-on": "dblclick"})
        row.div("^.suburb", class_="gnr-grid-cell")
        row.div("^.state", class_="gnr-grid-cell")
        row.div("^.postcode", class_="gnr-grid-cell")
        row.div("^.n_invoices", class_="gnr-grid-cell gnr-grid-num")
        row.div("^.invoiced_total",
                class_="gnr-grid-cell gnr-grid-num")

    @component
    def invoiceRow(self, root, node_label=None):
        # The customer's invoices, display-only: store-backed EAGER
        # iterate (a handful of rows — laziness would be ceremony).
        row = root.div(datapath="." + node_label, class_="gnr-grid-row")
        row.div("^.inv_number", class_="gnr-grid-cell")
        row.div("^.date", class_="gnr-grid-cell")
        row.div("^.total", class_="gnr-grid-cell gnr-grid-num")
        row.div("^.gross_total", class_="gnr-grid-cell gnr-grid-num")

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
        data.set_item("dialog.display", "none")

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
        grid.div(class_="gnr-grid-body").customerRow(
            iterate="^customers", lazy=True, id="customers")
        # The customer dialog: a fixed overlay, shown and hidden by a
        # DATUM. Its fields live in the store (dialog.customer.*) —
        # mutable data, ordinary inputs: writeback for free. The grid
        # stays throwaway; the record under edit is store-backed.
        dialog = pane.div(class_="gnr-dialog", display="^dialog.display")
        box = dialog.div(class_="gnr-dialog-box")
        box.h2("Customer")
        for field in _FIELDS:
            frow = box.div(class_="gnr-dialog-row")
            frow.html_label(field.replace("_", " "), color="#555555")
            frow.input(value=f"^dialog.customer.{field}")
        box.h3("Invoices", margin_bottom="4px")
        inv = box.div(class_="gnr-grid gnr-grid-scroll "
                             "dialog-invoices-grid")
        inv_head = inv.div(class_="gnr-grid-edge").div(
            class_="gnr-grid-row gnr-grid-head")
        for caption, klass in (
            ("Number", "gnr-grid-cell"), ("Date", "gnr-grid-cell"),
            ("Total", "gnr-grid-cell gnr-grid-num"),
            ("Gross", "gnr-grid-cell gnr-grid-num"),
        ):
            inv_head.div(caption, class_=klass)
        inv.div(class_="gnr-grid-body").invoiceRow(
            iterate="^dialog.invoices", id="dialog_invoices")
        buttons = box.div(class_="gnr-dialog-buttons")
        buttons.button("Save", class_="gnr-grid-add",
                       **{"data-fire-pointer": "commands.save_customer"})
        buttons.button("Cancel", class_="gnr-grid-add",
                       **{"data-fire-pointer": "commands.cancel_customer"})
        # The state click re-parameterizes the anchor: one attribute
        # write, and the lazy component re-renders — re-query included.
        pane.dataController(func="set_state", state="^selection.state")
        pane.dataController(func="edit_customer",
                             pkey="^commands.edit_customer")
        pane.dataController(
            func="save_customer", trigger="^commands.save_customer",
            pkey="=dialog.pkey",
            **{field: f"=dialog.customer.{field}" for field in _FIELDS})
        pane.dataController(func="cancel_customer",
                             trigger="^commands.cancel_customer")

    @staticmethod
    def set_state(node, state=None):
        # "All" writes the EMPTY string, not None: a None attribute is
        # removed, and the resolver would fall back to its LAST params
        # (genro-bag: changed arguments become the new state). The
        # empty string is a real attribute and a falsy filter.
        node.SET("customers?state", state or "")

    def load_customers(self, state=None):
        """The query — run ONCE per (re)render of the lazy component.
        Row labels are the record pkeys (base62, dot-free): identity.
        """
        with self.db_access() as db:
            fetched = db.table("invc.customer").query(
                columns=("$id,$account_name,$suburb,$state,$postcode,"
                         "$n_invoices,$invoiced_total"),
                where="$state = :st" if state else None,
                st=state, order_by="$account_name",
            ).fetch()
            rows = Bag()
            for record in fetched:
                row = Bag()
                row["account_name"] = record["account_name"]
                row["suburb"] = record["suburb"]
                row["state"] = record["state"]
                row["postcode"] = record["postcode"]
                # virtual columns of the legacy model: the customer
                # already KNOWS its invoice count and turnover
                row["n_invoices"] = record["n_invoices"] or None
                if record["invoiced_total"]:
                    row.set_item("invoiced_total",
                                 record["invoiced_total"], mask="%.2f")
                rows[record["id"]] = row
        return rows

    @staticmethod
    def edit_customer(node, pkey=None):
        """Double click: load the WHOLE record and open the dialog.
        Data-logic funcs are static: the PAGE arrives through the node
        (``node.builder``), and with it the db unit of work.
        """
        if not pkey:
            return
        page = node.builder
        with page.db_access() as db:
            record = db.table("invc.customer").query(
                columns=",".join(f"${f}" for f in ("id", *_FIELDS)),
                where="$id = :pk", pk=pkey, addPkeyColumn=False,
            ).fetch()[0]
            fetched = db.table("invc.invoice").query(
                columns="$id,$inv_number,$date,$total,$gross_total",
                where="$customer_id = :pk", pk=pkey,
                order_by="$date desc",
            ).fetch()
        invoices = Bag()
        for inv in fetched:
            row = Bag()
            row["inv_number"] = inv["inv_number"]
            row["date"] = str(inv["date"] or "")
            row.set_item("total", inv["total"], mask="%.2f")
            row.set_item("gross_total", inv["gross_total"], mask="%.2f")
            invoices[inv["id"]] = row
        node.SET("dialog.pkey", record["id"])
        for field in _FIELDS:
            node.SET(f"dialog.customer.{field}", record[field])
        node.SET("dialog.invoices", invoices)
        node.SET("dialog.display", "flex")

    @staticmethod
    def save_customer(node, trigger=None, pkey=None, **fields):
        """Save: diff-update on the legacy table, commit (the author's
        duty), close — and bump the anchor so the grid re-queries."""
        if not trigger or not pkey:
            return
        page = node.builder
        with page.db_access() as db:
            tbl = db.table("invc.customer")
            current = dict(tbl.query(
                columns=",".join(f"${f}" for f in ("id", *_FIELDS)),
                where="$id = :pk", pk=pkey, addPkeyColumn=False,
            ).fetch()[0])
            fresh = dict(current)
            fresh.update(fields)
            tbl.update(fresh, current)
            db.commit()
        page._close_dialog(node)
        # Any anchor-attribute write re-renders the lazy component:
        # fresh query, fresh marker, the client rebuilds and refills.
        node.SET("customers?v", (node.GET("customers?v") or 0) + 1)

    @staticmethod
    def cancel_customer(node, trigger=None):
        """Cancel: close and clear. The database never hears of it."""
        if not trigger:
            return
        node.builder._close_dialog(node)

    def _close_dialog(self, node):
        node.SET("dialog.display", "none")
        node.SET("dialog.pkey", None)
        node.SET("dialog.invoices", None)
        for field in _FIELDS:
            node.SET(f"dialog.customer.{field}", None)

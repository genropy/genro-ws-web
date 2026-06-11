# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Australian states page: a domain table read through the page cycle.

``invc.state`` of the wired instance, fetched inside the page's own
``db_access()`` block: the env comes from the page's connection, the
exit guards watch the block, the connection closes on the way out.
Pure read — no commit involved.
"""

from __future__ import annotations

from ..page import WsLivePage

PAGE_TITLE = "Australian states (invc.state)"


class Page(WsLivePage):
    """The invc.state table rendered as a plain HTML table."""

    requires_db = True

    def main(self, root):
        with self.db_access() as db:
            rows = db.table("invc.state").query(
                columns="code,name,region_code", order_by="$code",
            ).fetch()
            states = [dict(r) for r in rows]
        pane = root.div()
        pane.h1("Australian states")
        listing = pane.table(border_collapse="collapse")
        head = listing.tr()
        for caption in ("Code", "Name", "Region"):
            head.th(caption, text_align="left", padding="4px 12px",
                    border_bottom="2px solid #c8c8c8")
        for state in states:
            row = listing.tr()
            row.td(state["code"], padding="4px 12px", font_weight="600")
            row.td(state["name"], padding="4px 12px")
            row.td(state["region_code"], padding="4px 12px")
        pane.p(f"{len(states)} rows from invc.state of "
               f"'{self.application.instance_name}'.")

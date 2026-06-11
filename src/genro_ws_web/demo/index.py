# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Index page: the live demos, listed from the application registry.

The menu is true by construction: it iterates ``application.pages`` —
the registry built by the demo auto-discovery and filtered by
``requires_db`` — so a new demo file appears by itself and the db
pages vanish when the server runs without ``--instance``. A plain
loop for now; the tree widget (legacy-alignment §5) will be its
natural upgrade.
"""

from __future__ import annotations

from ..page import WsLivePage

PAGE_TITLE = "genro-ws-web demos"


class Page(WsLivePage):
    """The registered demo pages as a list of links."""

    def main(self, root):
        pane = root.div(max_width="480px")
        pane.h1("genro-ws-web demos")
        pane.p("Server-driven live pages over one websocket. "
               "Every entry below is a module in demo/: drop a new "
               "file there and it appears here.")
        listing = pane.ul(class_="feed")
        for key, (title, _page_class) in self.application.pages.items():
            if key == "index":
                continue
            item = listing.li()
            item.a(title, href=key)
            item.span(f" — /{key}", color="#888888", font_size="0.85em")
        if self.application.db is not None:
            pane.p(f"Legacy instance wired: "
                   f"'{self.application.instance_name}'.",
                   font_size="0.9em", color="#666666")

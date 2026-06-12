# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Index: the demo DESKTOP — the drawer technique applied to itself.

The page registry (auto-discovery, filtered by ``requires_db``)
becomes a TREE on the left: one branch per family (live / db), one
leaf per page. A double click plants a LIVE tab in the container on
the right — an iframe per page, each with its own websocket
connection, never reloaded on tab switch (attribute-only morph).
Drop a new module in demo/ and it appears in the tree by itself.
"""

from __future__ import annotations

from genro_bag import Bag

from ..page import WsLivePage
from ..resources.components.tree import TreeCollection
from ..widgets import HtmlContainersBase

PAGE_TITLE = "genro-ws-web demos"

GROUPS = {"live": "Live pages", "db": "Database pages"}


class Page(WsLivePage, TreeCollection, HtmlContainersBase):
    """Pages tree on the left, live page tabs on the right."""

    def setup(self, data):
        store = Bag()
        for group, caption in GROUPS.items():
            store.set_item(group, None, caption=caption,
                           file_ext="directory")
        for key, (title, page_class) in self.application.pages.items():
            if key == "index":
                continue
            group = "db" if page_class.requires_db else "live"
            store.set_item(f"{group}.{key}", None,
                           caption=title, page=key)
        self.set_data("shell.pages", store)

    def main(self, root):
        bc = root.border_container(height="calc(100vh - 80px)")
        left = bc.div(region="left", width="320px", splitter=True,
                      overflow="auto", padding="8px",
                      border_right="1px solid #c8c8c8",
                      background="#fafbfc")
        pane = left.div(datapath="shell")
        pane.h1("genro-ws-web", font_size="1.1em", margin="4px 0 8px 0")
        pane.tree(wid="shell", store="^.pages",
                  label_attribute="caption",
                  dblclick_fire="shell.open_page")
        pane.p("double click opens a page", font_size="0.8em",
               color="#888888")
        pane.data_controller(func="open_page", trigger="^.open_page")

        center = bc.div(region="center", overflow="auto", padding="8px")
        shell = center.div(datapath="shell", height="100%")
        self._shell_tabs = shell.tab_container(selected_page="^.current")

    # -------------------------------------------------------- data logic
    @staticmethod
    def open_page(node, trigger=None):
        """A dblclick fired a tree row: PAGE rows open a live tab.

        One live iframe per page (key = the page key: reopening just
        refocuses); group rows carry no ``page`` attr and fall through.
        """
        if not trigger:
            return
        page_key = node.GET(f"{trigger}?page")
        if not page_key:
            return
        shell = node.builder
        token = shell._shell_tabs.attr.get("node_id")
        if page_key not in shell.tab_keys(token):
            pane = shell.tab(shell._shell_tabs,
                             node.GET(f"{trigger}?caption"), key=page_key,
                             closable=True)
            pane.iframe(src=page_key, width="100%",
                        height="calc(100vh - 160px)", border="0")
        node.SET("shell.current", page_key)

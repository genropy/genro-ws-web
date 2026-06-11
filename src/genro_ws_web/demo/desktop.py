# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Desktop page: the shell preview — page titles left, live pages right.

The left strip is the application registry itself (a new demo file
appears by itself); the right panes host the pages in iframes. The
selected key lives in data; the click is a mutation; switching is an
attribute-only morph: the iframes are never touched, a background
page keeps living (the clock keeps ticking) and switching back finds
it exactly where it was.

Pages load LAZILY: every iframe is born on ``about:blank`` and a
``data_controller`` writes the real src on FIRST selection — the
legacy desktop stack, in data terms. The src write replaces that one
iframe (its first real load); from then on selection never touches it.
"""

from __future__ import annotations

from ..page import WsLivePage
from ..widgets import HtmlContainersBase

PAGE_TITLE = "Desktop (sidebar + live pages)"

_NOT_HOSTED = ("index", "desktop")


class Page(WsLivePage, HtmlContainersBase):
    """A miniature desktop: the registry on the left, live pages right."""

    def page_keys(self):
        """The hosted pages: the registry minus index and ourselves."""
        return [key for key in self.application.pages
                if key not in _NOT_HOSTED]

    def setup(self, data):
        keys = self.page_keys()
        self.set_data("ui.page", keys[0] if keys else "")
        for key in keys:
            self.set_data(f"ui.src.{key}", "about:blank")

    def main(self, root):
        bc = root.border_container(height="calc(100vh - 40px)")
        bc.zone("top", height="44px", padding="8px 12px",
                background="#f0f4f8").h2("Desktop", margin="0")
        center = bc.zone("center")
        tc = center.tab_container(selected="^ui.page",
                                  tabs_position="left")
        for key in self.page_keys():
            title, _page_class = self.application.pages[key]
            tc.tab(title, key=key).iframe(
                src=f"^ui.src.{key}", width="100%",
                height="calc(100vh - 120px)", border="none",
            )
        center.data_controller(func="open_page", selected="^ui.page",
                               _on_start=True)

    @staticmethod
    def open_page(node, selected=None):
        """First selection of a page turns its blank iframe into the
        page URL; later selections find the src already set and leave
        the living iframe alone."""
        if not selected:
            return
        if node.GET(f"ui.src.{selected}") == "about:blank":
            node.SET(f"ui.src.{selected}", selected)

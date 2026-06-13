# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Nested border containers, splitters everywhere (legacy parity).

A tab container up front, one tab per LEGACY DESIGN: the same nested
frame built with the outer ``design="headline"`` (top/bottom span the
full width) and ``design="sidebar"`` (left/right span the full
height). Inside each: three levels of border containers — every
region is a CHILD declaring ``region=`` (a nested
``borderContainer(region=...)`` included, the legacy gesture
verbatim) and ``splitter=True`` plants the drag bar on the region's
inner edge. Sizes are client UI state.
"""

from __future__ import annotations

from ..page import WsLivePage
from ..widgets import HtmlContainersBase

PAGE_TITLE = "Nested border containers"


class Page(WsLivePage, HtmlContainersBase):
    """Two designs side by side, bc in bc in bc with splitters."""

    def setup(self, data):
        self.set_data("ui.design", "headline")
        self.set_data("ui.inner_headline", "uno")
        self.set_data("ui.inner_sidebar", "uno")

    def main(self, root):
        tc = root.tabContainer(selected_page="^ui.design")
        self._frame(tc.tab("Headline", key="headline"), "headline")
        self._frame(tc.tab("Sidebar", key="sidebar"), "sidebar")

    def _frame(self, pane, design):
        """The same nested structure, outer design as asked."""
        bc = pane.borderContainer(design=design,
                                   height="calc(100vh - 140px)")
        bc.div(region="top", height="56px", splitter=True,
               background="#2c5f8a", color="#ffffff", padding="8px",
               ).span(f"L1 top ({design})")
        # A borderContainer nested in a SIDE region (any region works:
        # the css child selector scopes each grid to its own children).
        side = bc.borderContainer(region="left", width="200px",
                                   splitter=True, min_width="0")
        side.div(region="top", height="40px", splitter=True,
                 background="#cfe0ef", padding="8px",
                 ).span("L1 left · top")
        side.div(region="center", background="#e8eef4", padding="8px",
                 ).span("L1 left · center")
        bc.div(region="right", width="160px", splitter=True,
               background="#fdf3e3", padding="8px",
               ).span("L1 right")
        bc.div(region="bottom", height="48px", splitter=True,
               background="#e6e6e6", padding="8px",
               ).span("L1 bottom")

        # The oracle's gesture: a borderContainer IS the region child;
        # the inner frame shows the OTHER design than the outer one.
        inner_design = "sidebar" if design == "headline" else "headline"
        inner = bc.borderContainer(region="center", design=inner_design,
                                    min_height="0")
        inner.div(region="left", width="180px", splitter=True,
                  background="#dcebdc", padding="8px",
                  ).span(f"L2 left ({inner_design})")
        inner.div(region="bottom", height="64px", splitter=True,
                  background="#f3e3f3", padding="8px",
                  ).span("L2 bottom")

        third = inner.borderContainer(region="center", min_height="0")
        third.div(region="top", height="48px", splitter=True,
                  background="#fbe9d0", padding="8px",
                  ).span("L3 top")
        center = third.div(region="center", padding="12px",
                           background="#ffffff", overflow="auto")
        center.h2(f"L3 center — outer {design}", margin="0 0 8px 0")
        center.p("Every colored band is a regioned child with "
                 "splitter=True: drag the inner edges. The inner "
                 "frames are border_containers sitting directly in a "
                 "region; the level-2 frame uses the opposite design.")
        # Tabs INSIDE borders inside tabs: closable pages (the ✕ pops
        # them from the structure) and the legacy selected pair —
        # selected_page (key) plus selected (index), both on display.
        itc = center.tabContainer(
            selected_page=f"^ui.inner_{design}",
            selected=f"^ui.inner_idx_{design}")
        itc.tab("Uno", key="uno", closable=True,
                ).p("first inner page — close me")
        due = itc.tab("Due", key="due", closable=True)
        ibc = due.borderContainer(height="160px")
        ibc.div(region="left", width="120px", splitter=True,
                background="#e8eef4", padding="6px",
                ).span("bc in tab")
        ibc.div(region="center", padding="6px",
                ).span("borders inside tabs inside borders inside tabs")
        itc.tab("Tre", key="tre", closable=True,
                ).p("third inner page")
        status = center.div(margin_top="8px", font_size="0.85em",
                            color="#555555")
        status.span("selected_page: ")
        status.span(f"^ui.inner_{design}", font_weight="600")
        status.span("  ·  selected (index): ", margin_left="8px")
        status.span(f"^ui.inner_idx_{design}", font_weight="600")

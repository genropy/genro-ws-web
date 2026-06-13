# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Inspector: the legacy Developer Tools refounded server-side.

The legacy palette (genro_dev.js) put two paletteTrees on the CLIENT
bags (``*D`` data, ``*S`` source). Here the bags live on the SERVER,
so the inspector is an ordinary page that looks at the OTHER live
pages — every connection, every iframe (more than the legacy could
see). Pick a page in the left tree: its SOURCE and DATA bags are
snapshotted into this page's store and rendered by the same tree
widget; selecting a node fills the detail pane FOR FREE — the
selection write carries the row attributes (``#datapath``), and the
``<pre>`` reads the formatted ``?_insp_attrs`` off the selection
node. Snapshots refresh on demand (live following is the bag-sync
chapter).
"""

from __future__ import annotations

from genro_bag import Bag

from ..page import WsLivePage
from ..resources.components.tree import TreeCollection
from ..widgets import HtmlContainersBase

PAGE_TITLE = "Inspector (dev tools)"

#: children shown per level — an inspector survives a 3000-row store
MAX_CHILDREN = 100


class Page(WsLivePage, TreeCollection, HtmlContainersBase):
    """Live pages on the left, Source/Data trees plus detail center."""

    def setup(self, data):
        self.set_data("insp.pages", self._pages_store())
        self.set_data("insp.tab", "source")

    # ---------------------------------------------------------- snapshots
    def _pages_store(self):
        """The live pages registry as a tree store (group per
        connection, one leaf per mounted page)."""
        store = Bag()
        for ckey, builder in self.application.live_pages.items():
            conn, _, page_key = ckey.partition(":")
            if builder is self:
                continue
            if store.get_node(conn) is None:
                store.set_item(conn, None, caption=f"connection {conn}",
                               file_ext="directory")
            store.set_item(f"{conn}.{page_key}", None,
                           caption=page_key, ckey=ckey)
        return store

    @classmethod
    def _snapshot(cls, bag):
        """Materialize a foreign bag for the tree: per node, the
        caption (``label [tag]``), the formatted original attributes
        (the detail pane datum) and the children, capped."""
        out = Bag()
        if bag is None:
            return out
        for n, node in enumerate(bag.nodes):
            if n >= MAX_CHILDREN:
                out.set_item("_more", None,
                             _insp_caption=f"… +{len(bag) - n} more")
                break
            value = node.value
            tag = getattr(node, "node_tag", None)
            caption = f"{node.label} [{tag}]" if tag else node.label
            lines = [f"label: {node.label}"]
            if tag:
                lines.append(f"tag: {tag}")
            if not isinstance(value, Bag):
                lines.append(f"value: {value!r}")
            lines += [
                f"{key}: {val!r}" for key, val in node.attr.items()
            ]
            out.set_item(
                node.label,
                cls._snapshot(value) if isinstance(value, Bag) else None,
                _insp_caption=caption,
                _insp_attrs="\n".join(lines),
            )
        return out

    # ----------------------------------------------------------- the page
    def main(self, root):
        bc = root.borderContainer(height="calc(100vh - 80px)")
        left = bc.div(region="left", width="280px", splitter=True,
                      overflow="auto", padding="8px",
                      border_right="1px solid #c8c8c8",
                      background="#fafbfc")
        pane = left.div(datapath="insp")
        head = pane.div(display="flex", align_items="center", gap="8px",
                        margin_bottom="6px")
        head.h1("Inspector", font_size="1.1em", margin="0")
        head.button("refresh", font_size="0.8em",
                    **{"data-fire-pointer": "insp.refresh"})
        pane.tree(wid="insp_pages", store="^.pages",
                  label_attribute="caption",
                  selected_path="insp.page_sel")
        pane.data_controller(func="insp_refresh", trigger="^.refresh")
        pane.data_controller(func="insp_load", trigger="^.page_sel")

        center = bc.div(region="center", overflow="auto", padding="8px")
        insp = center.div(datapath="insp", height="100%")
        tc = insp.tabContainer(selected_page="^.tab")

        src = tc.tab("Source", key="source")
        sbc = src.borderContainer(height="calc(100vh - 190px)",
                                   design="sidebar")
        sleft = sbc.div(region="left", width="50%", splitter=True,
                        overflow="auto", padding="4px")
        sleft.div(datapath="insp").tree(
            wid="insp_src", store="^.source_store",
            label_attribute="_insp_caption",
            selected_path="insp.src_current")
        sbc.div(region="center", overflow="auto", padding="8px",
                ).pre("^insp.src_current?_insp_attrs",
                      font_size="0.85em", margin="0")

        dat = tc.tab("Data", key="data")
        dbc = dat.borderContainer(height="calc(100vh - 190px)",
                                   design="sidebar")
        dleft = dbc.div(region="left", width="50%", splitter=True,
                        overflow="auto", padding="4px")
        dleft.div(datapath="insp").tree(
            wid="insp_data", store="^.data_store",
            label_attribute="_insp_caption",
            selected_path="insp.data_current")
        dbc.div(region="center", overflow="auto", padding="8px",
                ).pre("^insp.data_current?_insp_attrs",
                      font_size="0.85em", margin="0")

    # -------------------------------------------------------- data logic
    @staticmethod
    def insp_refresh(node, trigger=None):
        """Rebuild the live pages tree (and forget stale sockets)."""
        if not trigger:
            return
        node.SET("insp.pages", node.builder._pages_store())

    @staticmethod
    def insp_load(node, trigger=None):
        """A page was picked: snapshot its SOURCE and its DATA segment
        into this page's store — the trees re-render from there."""
        if not trigger:
            return
        ckey = node.GET(f"{trigger}?ckey")
        if not ckey:
            return                     # a connection group row
        page = node.builder
        target = page.application.live_pages.get(ckey)
        if target is None:
            return
        node.SET("insp.source_store", page._snapshot(target.source))
        node.SET("insp.data_store", page._snapshot(
            target.handler.data.get_item(target.name)))
        node.SET("insp.src_current", None)
        node.SET("insp.data_current", None)

# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""File drawer: the legacy gnride drawer refounded — tree v1 + editor.

A ``DirectoryResolver`` mounts this very package as a Bag; the
``tree`` widget (TreeCollection) renders it with the LEGACY API:
``store`` anchors the bag, ``selected_path`` receives the picked
row's path (attributes riding), ``dblclick_fire`` is the gnride verb
— a double click on a FILE opens an editor tab: the controller reads
the row by the fired path, registers the tab, and the single iframe
(CodeMirror via the ``codefile`` route, mode by extension) follows
``editor.src`` through a data_formula. The tab strip is a store-backed
iterate; the active tab highlight rides ``data-selectable``.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from genro_bag import Bag
from genro_bag.resolvers.directory_resolver import DirectoryResolver

from ..page import WsLivePage
from ..resources.components.tree import TreeCollection
from ..widgets import HtmlContainersBase

PAGE_TITLE = "File drawer (tree v1, gnride parity)"

#: the mounted folder: this very package — small, real, source-only
PACKAGE_DIR = Path(__file__).resolve().parent.parent


class Page(WsLivePage, TreeCollection, HtmlContainersBase):
    """The gnride drawer pattern: tree, info pane, editor tabs."""

    @staticmethod
    def _stamp_caption(nodeattr):
        """Caption per node via callback (NB: the ``caption=True``
        resolver option is shadowed below level 2 — the generated
        ``caption`` NODE attr wins over the kwarg in the ``__call__``
        merge, genro-bag namespace collision; the callback never lands
        on nodes, so it survives the inheritance chain). A file shows
        its real name WITH extension; a directory its bare name."""
        name = nodeattr["file_name"]
        ext = nodeattr["file_ext"]
        nodeattr["caption"] = name if ext == "directory" else f"{name}.{ext}"

    @classmethod
    def _materialize(cls, bag):
        """Deep-resolve the directory bag into PLAIN data (v1 boundary).

        A read_only resolver re-resolves on every access: a row-relative
        write (the ``.pick`` fire) would land on a transient bag no
        later walk can reach. The eager tree wants REAL rows; the tree
        over a LIVE resolver store is the v2 step (the lazy-iterate
        parking mechanics)."""
        out = Bag()
        for node in bag.nodes:
            value = node.value
            out.set_item(
                node.label,
                cls._materialize(value) if isinstance(value, Bag) else None,
                **dict(node.attr),
            )
        return out

    def setup(self, data):
        store = Bag()
        store.set_item(
            "root",
            self._materialize(DirectoryResolver(
                str(PACKAGE_DIR),
                include="*.py,*.js,*.css",
                exclude="_*,.*",
                callback=self._stamp_caption,
            )()),
            caption="genro_ws_web",
            file_ext="directory",
        )
        self.set_data("drawer.directories", store)

    # ----------------------------------------------------------- the page
    def main(self, root):
        # The gnride frame: drawer on the LEFT, editor stack CENTER.
        bc = root.border_container(height="calc(100vh - 80px)")
        left = bc.div(region="left", width="320px", splitter=True,
                      overflow="auto", padding="8px",
                      border_right="1px solid #c8c8c8",
                      background="#fafbfc")
        pane = left.div(datapath="drawer")
        pane.h1("File drawer", font_size="1.1em", margin="4px 0 8px 0")
        pane.tree(wid="drawer", store="^.directories",
                  label_attribute="caption",
                  selected_path="drawer.current.path",
                  dblclick_fire="drawer.open_file")
        info = pane.div(padding="6px 2px", margin_top="8px",
                        font_size="0.85em")
        info.span("^.current.path?rel_path", color="#2c5f8a",
                  font_family="monospace")
        pane.data_controller(func="open_file", trigger="^.open_file")

        center = bc.div(region="center", overflow="auto", padding="8px")
        editor = center.div(datapath="editor", height="100%")
        # The editor stack: a REAL tab_container (panes are live source
        # nodes; switching tabs is an attribute-only morph — iframes
        # never reload). The handle parks on the instance: the rule
        # plants the runtime tabs there.
        self._editor_tabs = editor.tab_container(selected_page="^.current")

    # -------------------------------------------------------- data logic
    @staticmethod
    def open_file(node, trigger=None):
        """A dblclick fired a row path: FILES open an editor tab.

        ONE live pane per file (the gnride editor stack): the first
        open PLANTS a tab in the container — runtime structure, the
        insert rides the source lanes — with its own CodeMirror
        iframe; reopening just refocuses (key = sanitized path)."""
        if not trigger:
            return
        if node.GET(f"{trigger}?file_ext") == "directory":
            return
        abs_path = node.GET(f"{trigger}?abs_path")
        if not abs_path:
            return
        key = trigger.replace(".", "_")
        page = node.builder
        token = page._editor_tabs.attr.get("node_id")
        if key not in page.tab_keys(token):
            pane = page.tab(page._editor_tabs,
                            node.GET(f"{trigger}?caption"), key=key,
                            closable=True)
            pane.iframe(src=f"../codefile?path={quote(abs_path)}",
                        width="100%", height="calc(100vh - 170px)",
                        border="0")
        node.SET("editor.current", key)

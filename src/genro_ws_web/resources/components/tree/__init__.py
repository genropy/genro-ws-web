# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""tree — the legacy tree widget, all-python v1 (gnride parity).

The legacy ``pane.tree(storepath=...)`` refounded on the existing
lanes, no client code: the structure renders from the store Bag, one
``treeBranch`` expansion per node, RECURSIVE (a directory row plants
another ``treeBranch`` over its own value — nested iterate, the
``cmp_nested_iterate`` mechanics applied to itself).

- expansion/collapse is ``<details>/<summary>``: BROWSER state, no
  datum, no patch, no js;
- the row CAPTION comes from ``label_attribute`` (legacy default
  ``caption``);
- SELECTION is the legacy ``selectedPath`` contract, one ordinary
  SET: the summary carries ``data-set-pointer`` (the declared target)
  and ``data-set-value="#datapath"`` — the click writes the row's own
  path, the row attributes riding as the write's attributes
  (``itemFullPath + item.attr`` parity). Companions need no
  machinery: ``^sel.path?file_ext`` reads them off the selection
  node. NOTHING is ever written into the store: the tree READS it.
- v1 boundary: the store renders eagerly (resolver bags resolve on
  walk — size it with include/exclude); resolve-on-expand is the v2
  step.
"""
from __future__ import annotations

from genro_builders.builder import component, container

#: tree config by wid, stamped by the @container on the page instance:
#: iterate bodies receive only the row label, so the branch recovers
#: caption attribute and selection target from here.
TREE_CFG_ATTR = "_tree_cfg"


class TreeCollection:
    """The tree widget. Mix into a WsLivePage."""

    css_requires = ("tree.css",)

    @container("tree")
    def tree(self, pane, wid=None, store=None, label_attribute="caption",
             selected_path=None, dblclick_fire=None):
        """The legacy tree: ``store`` anchors the Bag,
        ``selected_path`` (segment-relative) names where a click
        writes the selected row's path — attributes included;
        ``dblclick_fire`` names the controller path a double click
        FIRES with the row's path as the message (the gnride
        ``connect_ondblclick`` verb, on the data-fire-on lane)."""
        cfg = {
            "wid": wid,
            "label_attribute": label_attribute or "caption",
            "selected_path": (
                f"{self.name}.{selected_path.lstrip('^=')}"
                if selected_path else None
            ),
            "dblclick_fire": (
                dblclick_fire.lstrip("^=") if dblclick_fire else None
            ),
        }
        registry = getattr(self, TREE_CFG_ATTR, None)
        if registry is None:
            registry = {}
            setattr(self, TREE_CFG_ATTR, registry)
        box = pane.div(class_="gnr-tree")
        # The registry key is the STORE ROOT (segmentless): branch
        # bodies resolve their tree by the expansion anchor — every
        # row anchor lives UNDER its store root, whatever the depth.
        store_key = box.abs_datapath(store).split(".", 1)[1]
        registry[store_key] = cfg
        box.treeBranch(iterate=store, id=f"tree_{wid}")
        return box

    @component
    def treeBranch(self, root, node_label=None):
        """ONE row of the tree, recursive: a Bag-valued row plants the
        next level over its own value (``iterate="^."``); a leaf row
        iterates None and closes the recursion."""
        # The expansion anchor (the row's store path) sits on the
        # wrapper node: it names which tree this branch belongs to.
        cfg = self._tree_cfg_for(root.parent_node.attr.get("datapath"))
        # The row KIND rides the datum: ``file_ext`` becomes a class
        # (gnr-ext-directory, gnr-ext-py, ...) via the template idiom —
        # folders and leaves style apart semantically, no DOM probing.
        # Born CLOSED: the user opens what he wants to see (and the v2
        # lazy step will resolve-on-open along the same gesture).
        row = root.details(datapath="." + node_label,
                           class_="gnr-tree-row gnr-ext-${ext}",
                           ext="^.?file_ext")
        label_kw = {"data-selectable": f"tree_{cfg['wid']}"}
        if cfg["selected_path"]:
            label_kw.update({"data-set-pointer": cfg["selected_path"],
                             "data-set-value": "#datapath"})
        summary = row.summary(class_="gnr-tree-label", **label_kw)
        caption_kw = {}
        if cfg["dblclick_fire"]:
            # One node one verb (the invoice pattern): the summary
            # keeps the selection SET, the caption carries the
            # dblclick FIRE — the message is the row's own path.
            caption_kw = {"data-fire-pointer": cfg["dblclick_fire"],
                          "data-fire-value": "#datapath",
                          "data-fire-on": "dblclick"}
        summary.span(f"^.?{cfg['label_attribute']}",
                     class_="gnr-tree-caption", **caption_kw)
        row.treeBranch(iterate="^.")

    def _tree_cfg_for(self, anchor: str) -> dict:
        """The tree config owning ``anchor``: the longest registered
        store root the anchor lives under. N trees per page, each
        branch finds its own."""
        registry = getattr(self, TREE_CFG_ATTR, {})
        best = None
        for store_key, cfg in registry.items():
            if anchor == store_key or anchor.startswith(store_key + "."):
                if best is None or len(store_key) > len(best[0]):
                    best = (store_key, cfg)
        if best is not None:
            return best[1]
        raise KeyError(f"no tree registered for anchor {anchor!r}")

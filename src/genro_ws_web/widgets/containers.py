# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlContainersBase — fillable containers (the @container citizen).

The OTHER half of the collection (CMP.9): pieces that generate REAL
source nodes at call time, which the caller fills. Real nodes mean
real identity (``target_id``): every zone and pane is individually
patchable, and an <iframe> hosted inside survives the updates around
it (the client morph never disconnects matched elements).

- ``borderContainer``: a CSS grid with named areas (top /
  left-center-right / bottom), the LEGACY contract: any CHILD
  declares its region as an attribute — ``bc.div(region="left",
  width="320px", splitter=True)``, a nested
  ``borderContainer(region="center")`` included — and the shared css
  places it. Sizes live ON the regioned child; an absent region
  collapses by itself (auto tracks); ``splitter=True`` gets the
  draggable bar (client guidance, the kernel plants it).
- ``tabContainer`` / ``tab``: the selected key lives in DATA
  (``selected="^ui.tab"``), the click IS a mutation (the tab strip
  carries ``data-set-pointer``/``data-set-value``, the client
  translates the click into ``setData``). Visibility is pure CSS: a
  per-instance ``<style>`` accumulates one rule per key (keys are
  known at build time), keyed on the container's ``data-selected``
  attribute — which is a pointer, so switching tabs is an
  attribute-only morph: the panes are never touched, iframes inside
  never reload.

Usage::

    class Page(HtmlBuilder, HtmlContainersBase):
        def main(self, root):
            bc = root.borderContainer(height="100vh")
            bc.div(region="top", height="48px").h1("Header")
            tc = bc.div(region="center").tabContainer(
                selected_page="^ui.tab")
            tc.tab("First", key="one").div("...")
            tc.tab("Second", key="two", closable=True).iframe(src="widgets")
"""
from __future__ import annotations

from genro_builders.builder import container

_TAB_POSITIONS = {
    "top": "column", "bottom": "column-reverse",
    "left": "row", "right": "row-reverse",
}

#: the two legacy designs (dijit BorderContainer): headline = top and
#: bottom span the full width; sidebar = left and right span the full
#: height.
_BC_DESIGNS = {
    "headline": '"top top top" "left center right" "bottom bottom bottom"',
    "sidebar": '"left top right" "left center right" "left bottom right"',
}


class HtmlContainersBase:
    """Fillable layout containers. Mix into an HtmlBuilder."""

    #: per-instance progressive for unique tab-container tokens
    #: (class default; the first increment shadows it on the instance).
    _gnr_tabs_serial = 0

    # ------------------------------------------------------------------
    # border container — grid with named areas, regions on the children
    # ------------------------------------------------------------------

    # Explicit dispatch name: the legacy prefix-strip rule would turn
    # the compound name into "container" (a collision).
    @container("borderContainer")
    def borderContainer(self, pane, design="headline", **attrs):
        """``design`` is the legacy pair: ``headline`` (top/bottom span
        the full width) or ``sidebar`` (left/right span the full
        height)."""
        if design not in _BC_DESIGNS:
            raise ValueError(
                f"unknown design {design!r}: one of {tuple(_BC_DESIGNS)}",
            )
        return pane.div(
            class_="gnr-bordercontainer",
            display="grid",
            grid_template_areas=_BC_DESIGNS[design],
            grid_template_rows="auto 1fr auto",
            grid_template_columns="auto 1fr auto",
            **attrs,
        )

    # ------------------------------------------------------------------
    # tab container — selected in data, click is a mutation, CSS shows
    # ------------------------------------------------------------------

    @container("tabContainer")
    def tabContainer(self, pane, selected=None, selected_page=None,
                      tabs_position="top", **attrs):
        """The shell: tab strip + panes. The LEGACY pair:
        ``selected_page`` is the reactive pointer to the selected page
        KEY (drives the css visibility — required); ``selected`` is the
        optional pointer receiving the selected page INDEX (kept by a
        planted controller, recomputed when tabs close).
        ``tabs_position`` puts the strip on one of the four sides."""
        if selected_page is None:
            raise ValueError(
                "tabContainer() requires a selected_page pointer",
            )
        if tabs_position not in _TAB_POSITIONS:
            raise ValueError(
                f"unknown tabs_position {tabs_position!r}: "
                f"one of {tuple(_TAB_POSITIONS)}",
            )
        self._gnr_tabs_serial = self._gnr_tabs_serial + 1
        token = f"gnr-tabs-{self._gnr_tabs_serial}"
        outer = pane.div(
            class_=f"gnr-tabs {token}", node_id=token,
            display="flex", flex_direction=_TAB_POSITIONS[tabs_position],
            **{"data-selected": selected_page}, **attrs,
        )
        # The per-instance rules: one base rule now, one per key as the
        # tabs are added (build time — the keys are the author's). A
        # <style> inside the container keeps it self-contained.
        outer.style(
            f".{token} > .gnr-tab-panes > .gnr-tab-pane "
            "{ display: none; }\n",
            node_id=f"{token}-style",
        )
        bar_direction = (
            "row" if tabs_position in ("top", "bottom") else "column"
        )
        outer.div(
            class_="gnr-tab-bar", node_id=f"{token}-bar",
            display="flex", flex_direction=bar_direction, gap="2px",
        )
        outer.div(
            class_="gnr-tab-panes", node_id=f"{token}-panes", flex="1",
        )
        page_key_path = outer.abs_datapath(selected_page).split(".", 1)[1]
        # The close lane: one controller per container, fired by the
        # tab ✕ with the page key as the message.
        outer.data_controller(
            func="gnr_tab_close", trigger=f"^_tabs.{token}.close",
            token=token, page_key_path=page_key_path,
        )
        if selected is not None:
            # Legacy ``selected``: the INDEX of the selected page,
            # derived from the key (and re-derived when tabs close).
            outer.data_controller(
                func="gnr_tab_index", trigger=selected_page,
                token=token,
                dest=outer.abs_datapath(selected).split(".", 1)[1],
            )
        return outer

    @container
    def tab(self, tabs, label, key=None, closable=False, **attrs):
        """One tab: the strip gets the clickable label (plus the close
        ✕ when ``closable`` — the legacy pane verb: it pops the tab
        from the STRUCTURE), the panes get the (returned) fillable
        pane, the instance style gets the per-key visibility and
        active-strip rules."""
        if key is None:
            raise ValueError("tab() requires a key")
        token = tabs.attr.get("node_id")
        selected_abs = tabs.abs_datapath(tabs.attr.get("data-selected"))
        bar = self.node_by_id(f"{token}-bar")
        panes = self.node_by_id(f"{token}-panes")
        styles = self.node_by_id(f"{token}-style")
        btn = bar.div(class_="gnr-tab", **{
            "data-set-pointer": selected_abs, "data-set-value": key,
        })
        btn.span(label)
        if closable:
            btn.span("✕", class_="gnr-tab-close",
                     **{"data-fire-pointer": f"_tabs.{token}.close",
                        "data-fire-value": key})
        styles.set_value(
            styles.value
            + f'.{token}[data-selected="{key}"] > .gnr-tab-panes > '
              f'[data-key="{key}"] {{ display: block; }}\n'
            + f'.{token}[data-selected="{key}"] > .gnr-tab-bar > '
              f'[data-set-value="{key}"] '
              "{ background: #ffffff; border-color: #c8c8c8; "
              "font-weight: 600; }\n",
        )
        return panes.div(
            class_="gnr-tab-pane", **{"data-key": key}, **attrs,
        )

    def tab_keys(self, token):
        """The CURRENT page keys of a tab container, in strip order."""
        panes = self.node_by_id(f"{token}-panes")
        if panes.value is None:
            return []
        return [n.attr.get("data-key") for n in panes.value.nodes]

    # -------------------------------------------------- tab data logic
    @staticmethod
    def gnr_tab_close(node, trigger=None, token=None, page_key_path=None):
        """The ✕ fired a page key: pop button and pane from the
        structure (the legacy ``deletePage``), then fix the selection —
        the neighbour takes over, the last close clears it (legacy
        nulls on empty)."""
        if not trigger:
            return
        page = node.builder
        keys = page.tab_keys(token)
        if trigger not in keys:
            return
        idx = keys.index(trigger)
        bar = page.node_by_id(f"{token}-bar")
        panes = page.node_by_id(f"{token}-panes")
        for parent, attr_name in (
            (bar, "data-set-value"), (panes, "data-key"),
        ):
            for child in list(parent.value.nodes):
                if child.attr.get(attr_name) == trigger:
                    parent.value.pop_node(child.label)
                    break
        if node.GET(page_key_path) == trigger:
            remaining = [k for k in keys if k != trigger]
            node.SET(
                page_key_path,
                remaining[min(idx, len(remaining) - 1)]
                if remaining else None,
            )

    @staticmethod
    def gnr_tab_index(node, trigger=None, token=None, dest=None):
        """Legacy ``selected``: the key became an index."""
        keys = node.builder.tab_keys(token)
        node.SET(dest, keys.index(trigger) if trigger in keys else None)

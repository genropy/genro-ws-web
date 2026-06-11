# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLivePage — HtmlBuilder base for the live pages.

A live page builds CONTENT only: the shell (resource links, the
``mainWindow`` div, the GenroClient bootstrap) is the fixed startup
page the HTTP route serves, the same for every page. The page's
``main(root)`` populates the source that the ``main`` WSX call renders
into the main div; later mutations travel as patches.
"""

from __future__ import annotations

from typing import Any

from genro_builders.contrib.html import HtmlBuilder


class _NodeAccessor:
    """Subscript access to source nodes by id: ``page.node["page"]``."""

    def __init__(self, builder: WsLivePage) -> None:
        self.builder = builder

    def __getitem__(self, node_id: str) -> Any:
        return self.builder.node_by_id(node_id)


class WsLivePage(HtmlBuilder):
    """HtmlBuilder for live content. Subclass and override ``main``."""

    #: a page that needs the legacy db declares it: the app drops it
    #: from the registry when no instance is configured.
    requires_db = False

    #: the WsConnection this live page belongs to (identity chain:
    #: page -> connection -> avatar). None on headless renders.
    connection = None

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    @property
    def application(self) -> Any:
        """The application this page's handler is mounted on."""
        return self.handler.application

    def db_access(self) -> Any:
        """The page's db unit of work: ``with self.db_access() as db:``.

        Rides the application's command cycle with THIS page's
        connection: env from the avatar in, exit guards and close out.
        Commit is the author's duty — end your writes with
        ``db.commit()``.
        """
        return self.application.db_access(connection=self.connection)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["page"]`` -> source node by id."""
        return _NodeAccessor(self)

# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DB users page: a legacy instance queried from a live page.

The first DB inclusion (legacy-alignment §7): the app wires a legacy
GenroPy instance once per process (``--instance <name>``); the page
reaches the shared db via ``self.application`` and queries the
``adm.user`` table (it exists in every instance). The access rides
``db_access()``: serialized (the legacy connection is unique and not
thread-safe) and closed on every exit path.

The page registers only when the app HAS an instance
(``requires_db``).
"""

from __future__ import annotations

from ..page import WsLivePage

PAGE_TITLE = "DB users (legacy instance)"


class Page(WsLivePage):
    """The adm.user table of the wired legacy instance, rendered live."""

    requires_db = True

    def main(self, root):
        with self.application.db_access() as db:
            rows = db.table("adm.user").query(
                columns="username,email", order_by="$username", limit=20,
            ).fetch()
            users = [dict(r) for r in rows]
        pane = root.div()
        pane.h1(f"Users of '{self.application.instance_name}'")
        listing = pane.ul(class_="feed")
        for user in users:
            email = user.get("email") or "no email"
            listing.li(f"{user['username']} — {email}")
        pane.p(f"{len(users)} rows from adm.user, over the shared "
               "legacy connection.")

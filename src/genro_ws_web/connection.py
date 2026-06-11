# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsConnection — the server-side identity of one websocket connection.

Born at the first WSX call of a connection, dies with it. Owns the
live-pages registry and the avatar slot. Authentication, session and
disconnection are the transport layer's business (genro-asgi and its
middleware): the avatar ARRIVES from there — this object only carries
it. No middleware yet = no avatar = anonymous connection: reads pass,
writes hit the application's exit guard.
"""

from __future__ import annotations

from typing import Any


class WsConnection:
    """One websocket connection: its live pages and its identity."""

    def __init__(self, ws: Any, application: Any) -> None:
        self.ws = ws
        self.application = application
        self.pages: dict[str, Any] = {}    # page key -> live builder
        self.avatar: Any = None            # set by the asgi auth middleware

    def db_env(self) -> dict[str, Any]:
        """The db environment carried by this connection's identity.

        Empty while anonymous. When the auth slice lands, the avatar's
        fields map to the legacy env the audit triggers read
        (``setCurrentUser``, the ``userTags`` protection check).
        """
        if self.avatar is None:
            return {}
        return {"user": self.avatar.user, "userTags": self.avatar.user_tags}

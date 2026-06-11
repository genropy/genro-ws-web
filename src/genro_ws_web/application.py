# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLiveApp — server-side reactive SPA on the legacy page cycle.

The cycle (the GenroPy one, refounded — see the application-registry
design in the genro-builders roadmap):

1. HTTP serves the SAME startup page for every page key: resource
   links, an empty ``mainWindow``, the inline GenroClient.
2. The client connects the websocket and calls ``main``: the server
   prepares the live page (one builder + handler per connection, the
   ``WsTargetWrapper`` bound to the connection) and returns the
   rendered HTML of the main div — the content's first paint.
3. Patches travel ONE road: every ``live()`` flush — a client mutate,
   a server timer, anything — is PUSHED over the websocket by the
   wrapper. ``mutate`` responds only the outcome.

The sync world (builders, handlers, live sections) runs in worker
threads (``asyncio.to_thread``); the async routes capture the event
loop and the connection so the wrapper can bridge back
(``run_coroutine_threadsafe``). A page declaring ``live_interval``
gets a server-side ticker: its ``tick()`` runs inside ``live()`` and
the resulting patches reach the browser with no client request —
server-initiated reactivity end to end.
"""

from __future__ import annotations

import asyncio
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_asgi.request import get_current_request
from genro_asgi.websocket import WebSocketState
from genro_routes import route
from genro_tytx.utils import raw_decode

from genro_builders.builder import BuilderHandler

from . import demo
from .connection import WsConnection
from .startup_page import STARTUP_HTML
from .target import WsTargetWrapper

try:
    from gnr.app.gnrapp import GnrApp
except ImportError:
    GnrApp = None

_PACKAGE_DIR = Path(__file__).parent


class WsLiveApp(AsgiApplication):
    """Server-side reactive SPA over WSX, one HtmlBuilder per page."""

    def __init__(self, **kwargs: Any) -> None:
        """Wire ``base_dir`` to the package directory by default.

        ``instance`` names a legacy GenroPy instance: the app loads it
        once per process and shares its db with the pages (§7 of the
        legacy-alignment track).
        """
        self.instance_name: str = kwargs.pop("instance", "")
        kwargs.setdefault("base_dir", _PACKAGE_DIR)
        super().__init__(**kwargs)

    def on_init(self, **kwargs: Any) -> None:
        """Wire the legacy instance (if any) and discover the pages.

        ``GnrApp`` is instantiated ONCE here — it loads the instance's
        whole model and owns the single shared db connection. Pages
        that declare ``requires_db`` are dropped when no instance is
        configured.
        """
        self.gnrapp: Any = None
        self.db: Any = None
        if self.instance_name:
            if GnrApp is None:
                raise RuntimeError(
                    "an instance was requested but the legacy genropy "
                    "package is not installed",
                )
            self.gnrapp = GnrApp(self.instance_name)
            self.db = self.gnrapp.db
            if self.db.implementation != "postgres":
                raise NotImplementedError(
                    "the db exit guard probes postgres for assigned "
                    f"xids; implementation {self.db.implementation!r} "
                    "is not supported yet",
                )
        pages = demo.discover()
        if self.db is None:
            pages = {
                key: entry for key, entry in pages.items()
                if not getattr(entry[1], "requires_db", False)
            }
        self.pages = pages
        self.loop: asyncio.AbstractEventLoop | None = None

    @contextmanager
    def db_access(self, connection: Any = None) -> Any:
        """One unit of db work — the db leg of a page command.

        The legacy layer pools connections PER THREAD and keys
        ``currentEnv`` by thread id; our commands run on recycled
        worker threads. So the env belongs to the BLOCK, not the
        thread: written on entry from the connection's identity,
        cleared on exit — an env left behind would sign one user's
        write with another user's name.

        COMMIT IS THE AUTHOR'S DUTY (the legacy contract: the command
        ends with ``db.commit()``). The exit guards only make the
        violations loud, one by one — writes on an anonymous
        connection, writes left uncommitted — and the close rolls
        back whatever was not committed. Side writes ride
        ``deferToCommit``, never a direct ``commit()``.
        """
        if self.db is None:
            raise RuntimeError("db_access() without a legacy instance")
        if connection is not None:
            self.db.updateEnv(**connection.db_env())
        try:
            yield self.db
            self._db_exit_guards(connection)
        finally:
            self.db.closeConnection()
            self.db.clearCurrentEnv()

    def _db_exit_guards(self, connection: Any) -> None:
        """Loud seams at block exit: each violation fails alone.

        The write signal comes from postgres itself: a transaction is
        assigned a xid ONLY when it writes
        (``pg_current_xact_id_if_assigned``), reads never trip the
        guard. The probe runs on every still-uncommitted connection of
        this thread (``commit()`` marks the committed ones) — so a
        write left pending is caught whoever made it.

        Backstop, not the gate: a write the author DID commit on an
        anonymous connection is beyond reach here (its transaction is
        gone) — gating anonymous connections upstream is the asgi auth
        middleware's job.
        """
        thread_connections = self.db._connections.get(
            threading.get_ident(), {},
        )
        dirty = [
            c.storename for c in thread_connections.values()
            if not c.committed and self._transaction_wrote(c)
        ]
        if not dirty:
            return
        if connection is None or connection.avatar is None:
            raise RuntimeError(
                "db writes on an anonymous connection (no avatar): "
                "authentication has not landed on this connection; "
                "the close is rolling them back",
            )
        raise RuntimeError(
            "db writes left uncommitted (the command must end with "
            f"db.commit()): stores {dirty}; the close is rolling "
            "them back",
        )

    def _transaction_wrote(self, conn: Any) -> bool:
        """True if ``conn``'s open transaction performed writes."""
        cursor = self.db.adapter.cursor(conn)
        cursor.execute("SELECT pg_current_xact_id_if_assigned()")
        return cursor.fetchone()[0] is not None

    def on_startup(self) -> None:
        """Capture the server's event loop (lifespan runs inside it).

        The sync world — routes in worker threads, live() flushes —
        bridges back to the connection through this reference
        (``run_coroutine_threadsafe`` in the wrapper and for the
        tickers).
        """
        self.loop = asyncio.get_running_loop()

    # ------------------------------------------------------------------
    # HTTP — the startup page (one fixed skeleton for every page)
    # ------------------------------------------------------------------

    @route(meta_mime_type="text/html")
    def page(self, *args: str) -> str:
        """Serve the startup skeleton. ``/<app>/page/<key>``.

        Always the same document: the page key only parameterizes the
        client bootstrap; the content arrives later over the websocket.
        """
        key = args[0] if args else next(iter(self.pages))
        title, _ = self.pages[key]
        return STARTUP_HTML % {"page": key, "title": title}

    @route()
    def static(self, file: str = "") -> Path:
        """Serve a static resource (JS, CSS) from ``resources/``.

        Returns a ``Path``; ``set_result`` detects the mime type from the
        suffix. Raises on missing file or empty parameter.
        """
        if not file:
            raise ValueError("file parameter required")
        resource_path = _PACKAGE_DIR / "resources" / file
        if not resource_path.is_file():
            raise FileNotFoundError(f"resource not found: {file}")
        return resource_path

    # ------------------------------------------------------------------
    # WSX — the live page (per-connection, prepared on ``main``)
    # ------------------------------------------------------------------

    def _connection(self, ws: Any) -> WsConnection:
        """The ``WsConnection`` of this websocket (born on first call)."""
        if "connection" not in ws.state:
            ws.state.connection = WsConnection(ws, self)
        return ws.state.connection

    def _prepare(self, key: str, connection: WsConnection) -> Any:
        """Instantiate and mount the page ``key`` on its own handler.

        One builder per page per connection; the page carries its
        ``connection`` (identity chain: page -> connection -> avatar).
        The ``WsTargetWrapper`` (riding on the builder as ``ws_target``)
        is bound to the connection so every flush pushes its patches.
        ``activate`` renders once — the full content lands in the
        wrapper — and arms the data subscribe.
        """
        title, page_class = self.pages[key]
        builder = page_class()
        builder.connection = connection
        builder.ws_target = WsTargetWrapper(page_key=key)
        builder.ws_target.bind(connection.ws, self.loop)
        builder.set_render_target(builder.ws_target)
        handler = BuilderHandler(application=self)
        handler.add_builder(builder)
        handler.activate()
        return builder

    def _live_builder(self, key: str, ws: Any) -> Any:
        """Return the connection's live builder for ``key`` (lazy)."""
        connection = self._connection(ws)
        builder = connection.pages.get(key)
        if builder is None:
            builder = self._prepare(key, connection)
            connection.pages[key] = builder
            interval = getattr(builder, "live_interval", None)
            if interval:
                builder._ticker_future = asyncio.run_coroutine_threadsafe(
                    self._ticker(ws, builder, interval), self.loop,
                )
        return builder

    @route()
    def main(self, page: str = "") -> dict[str, Any]:
        """First client call: the rendered HTML of the main div."""
        key = page or next(iter(self.pages))
        ws = get_current_request().websocket
        builder = self._live_builder(key, ws)
        return {"html": builder.ws_target.last_full}

    @route()
    def mutate(
        self, page: str = "", path: str = "", value: Any = None,
        dtype: str = "",
    ) -> dict[str, Any]:
        """Apply a data mutation to the live page.

        ``dtype`` is the widget's declared type (legacy TYTX codes): the
        write is converted before it lands, so the datastore holds the
        DATUM, not its text. It travels as a separate parameter — an
        in-band ``value::dtype`` suffix would be injectable from any
        textbox. The write runs inside ``handler.live()``; the flush
        pushes the patches over the connection (single road), so the
        response carries only the outcome.
        """
        if dtype:
            value = self._typed_value(value, dtype)
        builder = self._live_builder(page, get_current_request().websocket)
        handler = builder.handler
        with handler.live():
            handler.data.set_item(path, value)
        return {"ok": True}

    def _typed_value(self, value: Any, dtype: str) -> Any:
        """Convert a client string to its declared dtype (TYTX codes).

        ``None`` passes through (an emptied field means "no datum");
        non-strings are already typed by JSON (checkbox booleans). An
        unknown dtype raises: the widget declared something the catalog
        does not know.
        """
        if value is None or not isinstance(value, str):
            return value
        decoded, typed = raw_decode(f"{value}::{dtype}")
        if not decoded:
            raise ValueError(f"unknown dtype {dtype!r}")
        return typed

    # ------------------------------------------------------------------
    # Server-initiated reactivity — the ticker
    # ------------------------------------------------------------------

    async def _ticker(self, ws: Any, builder: Any, interval: float) -> None:
        """Run the page's ``tick()`` inside ``live()`` every ``interval``.

        The patches reach the browser through the wrapper push — no
        client request involved. The ticker dies with the connection.
        """
        while ws.connection_state == WebSocketState.CONNECTED:
            await asyncio.sleep(interval)
            if ws.connection_state != WebSocketState.CONNECTED:
                break
            await asyncio.to_thread(self._tick, builder)

    def _tick(self, builder: Any) -> None:
        with builder.handler.live():
            builder.tick()


if __name__ == "__main__":
    app = WsLiveApp()
    key = next(iter(app.pages))
    print(app.page(key))

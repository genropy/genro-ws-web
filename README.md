# genro-ws-web

WebSocket-driven reactive SPA framework, in **pure Python**.

Describe a single-page application with the [genro-builders](https://github.com/genropy/genro-builders)
HTML dialect and pointer-bound state. The framework renders it, tracks which
nodes depend on which data, and keeps the browser in sync over a WebSocket —
no hand-written HTML/CSS/JS, no client-side Python. The application logic runs
on the server; the browser holds a fixed JS client that owns the DOM and
applies the patches the server sends.

## Status

**Development Status: Pre-Alpha** — documentation and architecture only, no
implementation code yet. See `roadmap/VISION.md` for the design.

## Where it sits

| Project | Role |
| --- | --- |
| `genro-builders` | HTML dialect (bag → markup) + reactivity level 0 (`pointer_map`, pull) |
| `genro-asgi` | web server: routing, HTTP/WS dispatch, session |
| **`genro-ws-web`** | SPA framework: Python pages, fixed client, partial re-render, events, widgets |

`genro-ws-web` does **not** reimplement routing (that is genro-asgi's job) or
the HTML dialect (that is genro-builders'). It is the reactive layer on top.

## Why a separate repo

The reactivity work beyond level 0 — partial re-render, generic events,
server push — is an open-ended effort. Kept inside genro-builders it would
hold that core open indefinitely. As a separate repo, genro-builders can
close as a core and `genro-ws-web` evolves on its own.

## Phase 1

A pure-Python, server-driven prototype to evaluate **speed and efficacy** of
the WebSocket model. A later phase will add a JS version (as in classic
GenroPy). Phase 1 is the measurement, not the destination.

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l. See `LICENSE` and `NOTICE`.

# Claude Code Instructions - genro-ws-web

**Parent Document**: This project follows all policies from the central [meta-genro-modules CLAUDE.md](https://github.com/softwellsrl/meta-genro-modules/blob/main/CLAUDE.md)

## Project-Specific Context

### Current Status
- Development Status: Pre-Alpha
- Has Implementation: No (documentation and architecture only)

### Project Description
WebSocket-driven reactive SPA framework, in pure Python. Lets you describe
a single-page application with the genro-builders HTML dialect and pointer
state; the framework renders it, tracks dependencies, and keeps the browser
in sync over WebSocket — no hand-written HTML/CSS/JS, no client-side Python.

Sits on two existing projects:
- **genro-builders** — the HTML dialect (bag → markup) and reactivity level 0
  (`pointer_map`, pull pointers).
- **genro-asgi** — routing, HTTP/WS dispatch, session.

This is the home of the reactivity "levels beyond 0" that the genro-builders
contract parks under area `RX` (partial re-render, generic events, server
push). It is born as a separate repo so genro-builders can close as a core
without being held open by the SPA effort.

Phase 1 is a pure-Python, server-driven prototype to evaluate speed and
efficacy of the WS model before a future JS version.

The authoritative document is `roadmap/VISION.md`.

---

**All general policies are inherited from the parent document.**

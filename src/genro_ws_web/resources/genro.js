// Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
//
// GenroClient — the ws_live client, on the legacy page cycle refounded:
// the startup page is the same for every page; the client connects the
// websocket, asks `main` for the rendered HTML of the main div, then
// keeps the DOM live by applying the patch batches the server sends
// ({id, op, ...} — id is the node's target_id serial).
//
// The op vocabulary is open: `replace` (outer fragment) is the workhorse,
// `insert`/`remove` are the structural pair (a node attached to or
// dropped from the source); finer ops (set_attrs, set_text) will ride
// the same envelope.

class GenroClient {
  constructor(kw) {
    this.page = kw.page;
    this.pending = {};
    this.nextId = 1;
    this.ws = null;
    this.lazyStates = {};
    // Served at /<mount>/page/<key>: the WSX prefix is everything
    // before the last "/page" segment — the key may be absent
    // (/<mount>/page/ serves the default page).
    var m = location.pathname.match(/^(.*)\/page(?:\/.*)?$/);
    this.wsPrefix = (m ? m[1] : "") + "/";
    this.ops = {
      // Replace applies BY DIFFERENCE (morph): the existing DOM is
      // updated in place, matched elements survive as objects — an
      // engaged input is never disconnected (the native color picker
      // panel closes on disconnection, transplanting back does not
      // reopen it), an iframe never reloads while its block updates.
      replace: (patch) => {
        var el = document.getElementById(patch.id);
        if (!el) return;
        var tpl = document.createElement("template");
        tpl.innerHTML = patch.html;
        var fresh = tpl.content.firstElementChild;
        if (fresh) this.morph(el, fresh);
      },
      // The new fragment lands before its anchor sibling (`before`),
      // or appended to the container (`id`; null = the main div).
      insert: (patch) => {
        if (patch.before) {
          var ref = document.getElementById(patch.before);
          if (ref) ref.insertAdjacentHTML("beforebegin", patch.html);
          return;
        }
        var container = patch.id
          ? document.getElementById(patch.id) : this.mainWindow();
        if (container) container.insertAdjacentHTML("beforeend", patch.html);
      },
      remove: (patch) => {
        var el = document.getElementById(patch.id);
        if (el) el.remove();
      },
      // Value-only cell patches: the wire carries {id, value}
      // downstream too. `text` sets the element's text content,
      // `attr` an attribute — on form controls the live property,
      // unless the control is sovereign (focused: its edits are
      // already the truth).
      text: (patch) => {
        var el = document.getElementById(patch.id);
        if (el) el.textContent = patch.value;
      },
      attr: (patch) => {
        var el = document.getElementById(patch.id);
        if (!el) return;
        var sovereign = el === document.activeElement
          && el.matches("input, select, textarea");
        if (patch.name === "value"
            && el.matches("input, select, textarea")) {
          if (!sovereign) el.value = patch.value;
          return;
        }
        el.setAttribute(patch.name, patch.value);
      },
      // Lazy iterate: ONE op per page — the html carries the page's
      // blocks in order, the client owns the placeholders and fills
      // the ones of that page (index arithmetic, no DOM anchor).
      page: (patch) => {
        var state = this.lazyStates[patch.id];
        if (!state) return;
        var tpl = document.createElement("template");
        tpl.innerHTML = patch.html;
        var start = patch.page * state.pageSize;
        Array.from(tpl.content.children).forEach((block, i) => {
          var ph = state.placeholders[start + i];
          if (!ph) return;
          delete state.placeholders[start + i];
          state.observer.unobserve(ph);
          ph.replaceWith(block);
        });
      },
    };
    this._onReady(() => this.connect());
  }

  _onReady(cb) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", cb);
    } else {
      cb();
    }
  }

  // ---------------------------------------------------------------- dom
  mainWindow() {
    return document.getElementById("mainWindow");
  }

  setStatus(t) {
    document.body.setAttribute("data-gnr-status", t);
  }

  // Apply a patch batch. Replaces are morphed (see ops.replace): the
  // element the user is interacting with is never disconnected, so
  // focus, caret and the native picker panel survive every round-trip
  // and intermediate drag events keep flowing by default.
  applyPatches(patches) {
    patches.forEach((patch) => {
      var op = this.ops[patch.op];
      if (op) op(patch);
    });
    this.bindInputs();
    this.bindGridSync();
    this.bindLazy();
  }

  // Lazy iterate, client half. The marker announces total and page
  // size; page 0 is already inline (the marker's previous siblings).
  // The client measures their REAL average height, fabricates the
  // missing rows as placeholders — same tag, min-height = average, so
  // the scrollbar is honest from the start and free to breathe as
  // rows inflate — and asks a page when an empty placeholder enters
  // the viewport: the marker fired with the page number, on the one
  // mutation road. A re-rendered marker loses the wired mark (morph
  // syncs attributes), so a container replace re-wires from scratch:
  // re-render = re-query, the placeholders rebuild.
  bindLazy() {
    document.querySelectorAll("[data-lazy-total]").forEach((marker) => {
      if (!marker.id || marker.hasAttribute("data-gnr-wired")) return;
      marker.setAttribute("data-gnr-wired", "1");
      var total = parseInt(marker.getAttribute("data-lazy-total"), 10);
      var pageSize = parseInt(marker.getAttribute("data-lazy-page"), 10);
      var baseId = marker.id.replace(/\.lazy$/, "");
      var old = this.lazyStates[baseId];
      if (old && old.observer) old.observer.disconnect();
      var rows = [];
      for (var el = marker.previousElementSibling;
           el && rows.length < pageSize; el = el.previousElementSibling) {
        rows.push(el);
      }
      var delivered = rows.length;
      var avg = delivered
        ? rows.reduce(
            (s, r) => s + r.getBoundingClientRect().height, 0) / delivered
        : 24;
      var state = {
        pageSize: pageSize,
        requested: { 0: true },
        placeholders: {},
        observer: null,
      };
      this.lazyStates[baseId] = state;
      var rowClass = delivered ? rows[0].className : "";
      var frag = document.createDocumentFragment();
      for (var i = delivered; i < total; i++) {
        var ph = document.createElement(marker.tagName);
        if (rowClass) ph.className = rowClass + " gnr-lazy-ph";
        ph.style.minHeight = avg + "px";
        ph.setAttribute("data-lazy-index", i);
        state.placeholders[i] = ph;
        frag.appendChild(ph);
      }
      marker.after(frag);
      state.observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          var idx = parseInt(
            entry.target.getAttribute("data-lazy-index"), 10);
          var page = Math.floor(idx / state.pageSize);
          if (state.requested[page]) return;
          state.requested[page] = true;
          this.mutate(marker.id, page);
        });
      }, { rootMargin: "200px" });
      Object.keys(state.placeholders).forEach((k) => {
        state.observer.observe(state.placeholders[k]);
      });
    });
  }

  // Three-box grids: header and footer mirror the data body's
  // horizontal scroll (separate scrollers cannot be coupled in CSS).
  bindGridSync() {
    document.querySelectorAll(".gnr-grid-body").forEach((body) => {
      body.onscroll = () => {
        body.parentElement
          .querySelectorAll(":scope > .gnr-grid-edge")
          .forEach((row) => { row.scrollLeft = body.scrollLeft; });
      };
    });
  }

  // ---------------------------------------------------------------- morph
  // In-place DOM update: el is mutated to match `fresh`, preserving
  // every element object it can. Children are matched by id — the
  // reactive render puts a target_id serial on EVERY element, so the
  // match is identity-driven, not heuristic. The focused form control
  // is SOVEREIGN: its value/checked are never touched (its own edits
  // are already the truth; everything else around it updates).
  morph(el, fresh) {
    if (el.tagName !== fresh.tagName) {
      el.replaceWith(fresh);
      return;
    }
    var sovereign = el === document.activeElement
      && el.matches("input, select, textarea");
    this.syncAttrs(el, fresh, sovereign);
    if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
      if (!sovereign) {
        el.value = fresh.value;
        if (el.type === "checkbox") el.checked = fresh.checked;
      }
      return;
    }
    this.morphChildren(el, fresh);
    if (el.tagName === "SELECT" && !sovereign) el.value = fresh.value;
  }

  syncAttrs(el, fresh, sovereign) {
    var skip = (name) =>
      sovereign && (name === "value" || name === "checked");
    Array.from(el.attributes).forEach((attr) => {
      if (!fresh.hasAttribute(attr.name) && !skip(attr.name)) {
        el.removeAttribute(attr.name);
      }
    });
    Array.from(fresh.attributes).forEach((attr) => {
      if (skip(attr.name)) return;
      if (el.getAttribute(attr.name) !== attr.value) {
        el.setAttribute(attr.name, attr.value);
      }
    });
  }

  morphChildren(el, fresh) {
    var oldById = {};
    for (var c = el.firstElementChild; c; c = c.nextElementSibling) {
      if (c.id) oldById[c.id] = c;
    }
    var current = el.firstChild;
    var target = fresh.firstChild;
    while (target) {
      var next = target.nextSibling;
      var matched = null;
      if (target.nodeType === 1 && target.id && oldById[target.id]) {
        matched = oldById[target.id];
      } else if (
        current && current.nodeType === target.nodeType
        && (target.nodeType !== 1
            || (!target.id && !current.id
                && current.tagName === target.tagName))
      ) {
        matched = current;
      }
      if (matched) {
        if (matched === current) {
          current = current.nextSibling;
        } else {
          el.insertBefore(matched, current);   // pulled into position
        }
        if (matched.nodeType === 1) {
          this.morph(matched, target);
        } else if (matched.nodeValue !== target.nodeValue) {
          matched.nodeValue = target.nodeValue;
        }
      } else {
        el.insertBefore(target, current);      // adopt the fresh node
      }
      target = next;
    }
    while (current) {                          // leftovers: server truth
      var nextOld = current.nextSibling;
      el.removeChild(current);
      current = nextOld;
    }
  }

  // An input change writes its value back to the bound data path: the
  // render emits `data-value-pointer` (absolute datapath) on bound
  // inputs. Debounced by 10ms so a fast drag sends only the last value
  // of each window.
  bindInputs() {
    var main = this.mainWindow();
    if (!main) return;
    if (!this._inputHandler) {
      this._inputHandler = (e) => this.onInput(e);
    }
    if (!this._clickHandler) {
      this._clickHandler = (e) => this.onClick(e);
    }
    if (!this._dblHandler) {
      this._dblHandler = (e) => this.onDblClick(e);
    }
    main.removeEventListener("input", this._inputHandler);
    main.addEventListener("input", this._inputHandler);
    main.removeEventListener("click", this._clickHandler);
    main.addEventListener("click", this._clickHandler);
    main.removeEventListener("dblclick", this._dblHandler);
    main.addEventListener("dblclick", this._dblHandler);
  }

  // A click on an element carrying `data-set-pointer` (write a
  // declared value) or `data-fire-pointer` (the page command: an
  // event message) IS a mutation, riding the same single road as the
  // inputs (tab strips, menus, buttons). The wire carries only the
  // element's identity: pointer and value are the SERVER node's
  // attributes.
  onClick(e) {
    var el = e.target.closest
      ? e.target.closest("[data-set-pointer], [data-fire-pointer]")
      : null;
    // A dblclick-only carrier never fires on a single click: walk
    // past it (the row behind keeps its single-click verb).
    while (el && el.getAttribute("data-fire-on") === "dblclick") {
      el = el.parentElement && el.parentElement.closest(
        "[data-set-pointer], [data-fire-pointer]");
    }
    if (!el || !el.id) return;
    this.mutate(el.id);
  }

  // The double click fires the nodes that declared it. Same fire
  // lane, same {id} on the wire — ``data-fire-on`` is CLIENT
  // guidance only: the gesture decides WHEN, the node decides WHAT.
  onDblClick(e) {
    var el = e.target.closest
      ? e.target.closest('[data-fire-on="dblclick"]') : null;
    if (!el || !el.id) return;
    this.mutate(el.id);
  }

  onInput(e) {
    var el = e.target;
    if (!el || !el.matches("input, select, textarea")) return;
    if (!el.id) return;
    // The wire carries WHO (the element id — a serial, or the derived
    // chain inside an expansion) and WHAT (the raw value). Path and
    // dtype never travel: the server resolves the node by identity
    // and reads them THERE (typing, retention, validation).
    var value;
    if (el.type === "checkbox") {
      value = el.checked;                  // already typed (boolean)
    } else {
      value = el.value;
      // Text trims by default (legacy TextBox trim=true); data-trim
      // ="false" opts out, passwords never trim.
      if (el.type !== "password"
          && el.getAttribute("data-trim") !== "false") {
        value = value.trim();
      }
    }
    if (this._inputTimer) clearTimeout(this._inputTimer);
    this._inputTimer = setTimeout(() => {
      this._inputTimer = null;
      this.mutate(el.id, value);
    }, 10);
  }

  // ---------------------------------------------------------------- wsk
  connect() {
    var proto = location.protocol === "https:" ? "wss:" : "ws:";
    this.setStatus("connecting");
    this.ws = new WebSocket(proto + "//" + location.host + this.wsPrefix);
    this.ws.onopen = () => {
      this.setStatus("connected");
      this.main();
    };
    this.ws.onclose = () => {
      this.setStatus("disconnected");
      setTimeout(() => this.connect(), 2000);
    };
    this.ws.onerror = () => this.setStatus("error");
    this.ws.onmessage = (event) => this.onMessage(event);
  }

  call(method, params, cb) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    var id = String(this.nextId++);
    if (cb) this.pending[id] = cb;
    this.ws.send("WSX://" + JSON.stringify({
      id: id,
      method: "POST",
      path: this.wsPrefix + method,
      query: params,
    }));
  }

  onMessage(event) {
    var raw = event.data;
    if (typeof raw !== "string") return;
    if (raw.indexOf("WSX://") === 0) raw = raw.slice(6);
    var msg;
    try { msg = JSON.parse(raw); } catch (err) { return; }
    if (msg.status && msg.status !== 200) {
      this.setStatus("error");
      return;
    }
    var data = msg.data || {};
    var cb = msg.id && this.pending[msg.id];
    if (cb) {
      delete this.pending[msg.id];
      cb(data);
    }
    // Patches apply whatever the message: a mutate response today, a
    // server-initiated push tomorrow — same envelope, same road.
    if (Array.isArray(data.patches)) this.applyPatches(data.patches);
  }

  // ----------------------------------------------------------- lifecycle
  main() {
    this.call("main", { page: this.page }, (data) => {
      var main = this.mainWindow();
      main.innerHTML = data.html || "";
      main.classList.remove("waiting");
      this.bindInputs();
      this.bindGridSync();
      this.bindLazy();
      this.setStatus("ready");
    });
  }

  mutate(id, value) {
    var params = { page: this.page, id: id };
    if (value !== undefined) params.value = value;
    this.call("mutate", params);
  }
}

window.GenroClient = GenroClient;

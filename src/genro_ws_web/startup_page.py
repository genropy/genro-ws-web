# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""The startup page — one fixed skeleton for EVERY page (legacy model).

The HTTP route serves this same document whatever the page: resource
links, the shell tab strip (the live page / its Python source), an
empty ``mainWindow`` and the inline instantiation of the GenroClient.
The page CONTENT never travels over HTTP: the client opens the
websocket and asks ``main`` for the rendered HTML of the main div.
The Source tab is an iframe on the ``source`` route, loaded lazily on
first activation.

``SOURCE_HTML`` is the document that route serves: the page module's
Python, escaped, in a read-only CodeMirror (CDN); the bare textarea
is the graceful degradation when the CDN is unreachable.
"""
from __future__ import annotations

STARTUP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>%(title)s</title>
<link rel="stylesheet" href="../static?file=ws_live.css&v=%(v)s">
<script src="../static?file=genro.js&v=%(v)s"></script>
<script>var genro = new GenroClient({page: "%(page)s"});</script>
</head>
<body data-gnr-status="loading">
<div class="shell-tabs">
<span class="shell-tab active" data-pane="mainWindow">Page</span>
<span class="shell-tab" data-pane="sourceFrame">Source</span>
</div>
<div id="mainWindow" class="waiting"></div>
<iframe id="sourceFrame" class="hidden" data-src="../source?page=%(page)s"></iframe>
<script>
(function () {
  var tabs = document.querySelectorAll(".shell-tab");
  var main = document.getElementById("mainWindow");
  var frame = document.getElementById("sourceFrame");
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      tabs.forEach(function (t) { t.classList.remove("active"); });
      tab.classList.add("active");
      var showSource = tab.dataset.pane === "sourceFrame";
      main.classList.toggle("hidden", showSource);
      frame.classList.toggle("hidden", !showSource);
      if (showSource && !frame.getAttribute("src")) {
        frame.src = frame.dataset.src;
      }
    });
  });
})();
</script>
</body>
</html>
"""

SOURCE_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>%(title)s — source</title>
<link rel="stylesheet" href="static?file=ws_live.css&v=%(v)s">
<link rel="stylesheet"
 href="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.css">
<script
 src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/codemirror.min.js"></script>
<script
 src="https://cdnjs.cloudflare.com/ajax/libs/codemirror/5.65.16/mode/python/python.min.js"></script>
</head>
<body class="source-view">
<textarea id="code" readonly>%(code)s</textarea>
<script>
if (window.CodeMirror) {
  CodeMirror.fromTextArea(document.getElementById("code"), {
    mode: "python",
    readOnly: true,
    lineNumbers: true,
    viewportMargin: Infinity,
  });
}
</script>
</body>
</html>
"""

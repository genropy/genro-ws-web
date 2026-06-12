/* Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0 */
// <gnr-colorpicker> — the PoC web component. It speaks the NATIVE
// input contract: a `value` property and composed bubbling `input`
// events. Shadow retargeting makes the HOST the event target, so the
// kernel's delegated listener sees one element carrying the id and
// the value — the wire stays {id, value}, as for any input.
// Downstream needs no lane either: a value patch on a non-input does
// setAttribute, and `observedAttributes` forwards it to the inner
// input.
class GnrColorpicker extends HTMLElement {
  static get observedAttributes() { return ["value"]; }

  constructor() {
    super();
    var root = this.attachShadow({ mode: "open" });
    var style = document.createElement("style");
    style.textContent = ":host { display: inline-block; }";
    root.appendChild(style);
    this._input = document.createElement("input");
    this._input.type = "color";
    root.appendChild(this._input);
  }

  connectedCallback() {
    if (this.hasAttribute("value")) {
      this._input.value = this.getAttribute("value");
    }
  }

  attributeChangedCallback(name, _old, fresh) {
    if (name === "value") this._input.value = fresh;
  }

  get value() { return this._input.value; }
  set value(v) { this._input.value = v; }
}

customElements.define("gnr-colorpicker", GnrColorpicker);

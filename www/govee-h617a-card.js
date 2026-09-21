/* Govee H617A companion card — no external libraries or network resources. */
const EFFECTS = {
  clockwise: "Clockwise", counter_clockwise: "Counter clockwise",
  cycle: "Cycle", gradient: "Gradient", twinkle: "Twinkle", breathe: "Breathe",
};
const rgb = hex => hex.slice(1).match(/../g).map(v => parseInt(v, 16));
const hex = values => "#" + values.map(v => v.toString(16).padStart(2, "0")).join("");

class GoveeH617ACard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode: "open"});
    this.segments = Array(15).fill(null);
    this.animation = "clockwise";
    this.paint = "#ff0000";
    this.erase = false;
    this.dirty = false;
    this.busy = false;
    this.history = [];
  }
  setConfig(config) {
    if (!config.entity?.startsWith("light.")) throw new Error("Choose a light entity");
    if (this.config && this.config.entity !== config.entity) {
      this.segments = Array(15).fill(null);
      this.history = [];
      this.dirty = false;
    }
    this.config = config;
    this.render();
    this.updateState();
  }
  set hass(hass) { this._hass = hass; this.updateState(); }
  getCardSize() { return 2; }
  getGridOptions() { return {columns: 12, rows: 2, min_columns: 6}; }
  static getStubConfig(hass) {
    return {entity: Object.keys(hass.states).find(id => id.startsWith("light.") && hass.states[id].attributes.effect_list?.includes("Starry Sky")) || "light.your_h617a"};
  }
  $(selector) { return this.shadowRoot.querySelector(selector); }
  updateState() {
    if (!this.config || !this.$("#title")) return;
    const state = this._hass?.states[this.config.entity];
    this.$("#title").textContent = this.config.name || state?.attributes.friendly_name || this.config.entity;
    this.$("#state").textContent = state ? state.state + (state.attributes.effect ? " · " + state.attributes.effect : "") : "Entity not found";
    this.$("#power").textContent = state?.state === "on" ? "Turn off" : "Turn on";
    this.$("#power").disabled = !state || ["unavailable", "unknown"].includes(state.state) || this.busy;
    this.updateCapacity();
  }
  groups() {
    const grouped = new Map();
    this.segments.forEach((colour, index) => {
      if (colour) {
        if (!grouped.has(colour)) grouped.set(colour, {rgb: rgb(colour), segments: []});
        grouped.get(colour).segments.push(index);
      }
    });
    return [...grouped.values()];
  }
  updateCapacity() {
    if (!this.$("#apply")) return;
    const groups = this.groups();
    const available = this._hass?.services?.govee_h617a_ble?.apply_diy;
    const state = this._hass?.states[this.config.entity]?.state;
    this.$("#limit").textContent = !groups.length ? "Paint at least one segment to apply." : "";
    this.$("#apply").disabled = this.busy || !groups.length || !available || !state || ["unavailable", "unknown"].includes(state);
    this.$("#connection").textContent = !available ? "Install the DIY integration update to enable Apply." :
      state === "unavailable" ? "The strip is unavailable. Disconnect the Govee app and wait for recovery." : "";
  }
  draw() {
    const background = this.$("#none").checked ? null : this.$("#background").value;
    const opacity = Number(this.$("#background-level").value) / 100;
    this.shadowRoot.querySelectorAll(".segment").forEach((button, i) => {
      const colour = this.segments[i];
      button.style.background = colour || background || "repeating-conic-gradient(#555 0% 25%,#333 0% 50%) 0 / 10px 10px";
      button.style.opacity = colour || !background ? "1" : String(Math.max(0.15, opacity));
      button.setAttribute("aria-label", "Segment " + (i + 1) + (colour ? ", painted " + colour : ", background"));
      button.title = "Segment " + (i + 1);
    });
    this.$("#undo").disabled = !this.history.length || this.busy;
    this.$("#draft").textContent = this.dirty ? "Unsaved draft · press Apply to send" : "Draft preview · not live device readback";
    this.updateCapacity();
  }
  paintSegment(index) {
    if (this.busy) return;
    const colour = this.erase ? null : this.paint;
    if (this.segments[index] === colour) return;
    this.segments[index] = colour;
    this.dirty = true;
    this.draw();
  }
  snapshot() { this.history.push([...this.segments]); if (this.history.length > 40) this.history.shift(); }
  openEditor() {
    const saved = this._hass?.states[this.config.entity]?.attributes.diy_pattern;
    if (!this.dirty && saved) {
      this.segments = Array(15).fill(null);
      saved.groups.forEach(group => group.segments.forEach(i => this.segments[i] = hex(group.rgb)));
      this.animation = saved.animation;
      this.$("#none").checked = saved.background_rgb === null;
      if (saved.background_rgb) this.$("#background").value = hex(saved.background_rgb);
      this.$("#background-level").value = saved.background_brightness;
      this.$("#speed").value = saved.speed;
    }
    this.refreshControls();
    this.draw();
    this.$("dialog").showModal();
  }
  refreshControls() {
    this.$("#background").disabled = this.$("#none").checked;
    ["speed", "background-level"].forEach(id => this.$("#" + id + "-value").textContent = this.$("#" + id).value + "%");
    this.shadowRoot.querySelectorAll("[data-effect]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.effect === this.animation)));
    this.$("#pencil").setAttribute("aria-pressed", String(!this.erase));
    this.$("#eraser").setAttribute("aria-pressed", String(this.erase));
  }
  async apply() {
    const pattern = {
      animation: this.animation, speed: Number(this.$("#speed").value),
      background_brightness: Number(this.$("#background-level").value),
      background_rgb: this.$("#none").checked ? null : rgb(this.$("#background").value),
      groups: this.groups(),
    };
    this.busy = true;
    this.$("#editor-fields").disabled = true;
    this.$("#message").textContent = "Applying pattern…";
    this.updateCapacity();
    try {
      await this._hass.callService("govee_h617a_ble", "apply_diy", {entity_id: this.config.entity, ...pattern});
      this.dirty = false;
      this.$("#message").textContent = "Pattern sent. Check the strip matches your design.";
    } catch (error) {
      this.$("#message").textContent = error.message || String(error);
    } finally {
      this.busy = false;
      this.$("#editor-fields").disabled = false;
      this.draw();
      this.updateState();
    }
  }
  render() {
    this.shadowRoot.innerHTML = `
      <style>
        :host {display:block;color:var(--primary-text-color,#eee);font-family:var(--paper-font-body1_-_font-family,system-ui)}
        ha-card {display:block;padding:20px;border-radius:var(--ha-card-border-radius,16px);background:var(--ha-card-background,var(--card-background-color,#202124))}
        h2,h3,p {margin:0} h2 {font-size:19px} h3 {font-size:16px}
        .row {display:flex;align-items:center;gap:12px;flex-wrap:wrap}
        .spread {justify-content:space-between} .muted,small {color:var(--secondary-text-color,#aaa)}
        .actions {margin-top:16px} button,input,select {font:inherit}
        button {cursor:pointer;border:1px solid var(--divider-color,#555);border-radius:12px;padding:11px 14px;color:inherit;background:transparent;min-height:44px}
        button[aria-pressed=true],.primary {border-color:var(--primary-color,#03a9f4);background:var(--primary-color,#03a9f4);color:var(--text-primary-color,#fff)}
        button:disabled {opacity:.45;cursor:default} button:focus-visible,input:focus-visible {outline:3px solid var(--primary-color,#03a9f4);outline-offset:3px}
        dialog {box-sizing:border-box;width:min(560px,calc(100vw - 24px));max-height:90dvh;overflow:auto;border:1px solid var(--divider-color,#555);border-radius:22px;padding:24px;color:var(--primary-text-color,#eee);background:var(--card-background-color,#202124)}
        dialog::backdrop {background:#0009} fieldset {border:0;padding:0;margin:0;min-width:0}
        section {margin-top:24px} label {display:block;margin-bottom:10px}
        input[type=color] {width:48px;height:44px;padding:2px;border:0;background:transparent}
        input[type=range] {flex:1;min-width:120px;accent-color:var(--primary-color,#03a9f4)}
        input[type=checkbox] {accent-color:var(--primary-color,#03a9f4)}
        .strip {display:grid;grid-template-columns:repeat(15,minmax(0,1fr));gap:3px;touch-action:none;margin:14px 0 6px}
        .segment {padding:0;min-width:0;height:62px;border-radius:5px;border:1px solid #ffffff55}
        .effects {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
        .effects button {padding:12px 4px;font-size:13px}
        .note {font-size:13px;line-height:1.5;margin-top:12px} #limit,#connection {color:var(--warning-color,#ffc66d)}
        #message {min-height:20px} .bottom {margin-top:22px} output {min-width:3em}
        @media(max-width:420px) {dialog {padding:18px} .effects {grid-template-columns:repeat(2,minmax(0,1fr))}}
      </style>
      <ha-card>
        <div class="row spread"><h2 id="title"></h2><span aria-hidden="true">✦</span></div>
        <p id="state" class="muted"></p>
        <div class="row actions"><button id="power">Power</button><button id="controls">Light controls</button><button id="diy" class="primary">DIY</button></div>
        <p id="card-message" class="note" role="status"></p>
      </ha-card>
      <dialog aria-labelledby="editor-title">
        <div class="row spread"><div><small>GOVEE H617A · EXPERIMENTAL</small><h2 id="editor-title">Finger Sketch</h2></div><button id="close" aria-label="Close editor">✕</button></div>
        <p id="draft" class="note muted"></p>
        <fieldset id="editor-fields">
          <section><label for="background">Background colour</label><div class="row">
            <input type="color" id="background" value="#ff0000">
            <label class="row"><input id="none" type="checkbox" checked>No background</label>
          </div><label for="background-level">Background brightness</label><div class="row">
            <input id="background-level" type="range" min="1" max="100" value="100"><output id="background-level-value">100%</output>
          </div></section>
          <section><label for="fill">Paint colour</label><div class="row">
            <input type="color" id="fill" value="#ff0000"><button id="pencil" aria-pressed="true">Pencil</button><button id="eraser" aria-pressed="false">Eraser</button>
            <button id="undo">Undo</button><button id="clear">Clear</button>
          </div><p class="note muted">Tap or drag across the 15 segments.</p>
          <div class="strip">${Array.from({length:15},(_,i)=>'<button class="segment" data-index="'+i+'" aria-label="Segment '+(i+1)+'"></button>').join("")}</div>
          <div class="row spread muted"><small>Left · 1</small><small>15 · Right</small></div></section>
          <section><h3>Animation</h3><div class="effects actions">${Object.entries(EFFECTS).map(([id,label])=>'<button data-effect="'+id+'" aria-pressed="false">'+label+'</button>').join("")}</div></section>
          <section><label for="speed">Speed</label><div class="row"><input id="speed" type="range" min="0" max="100" value="0"><output id="speed-value">0%</output></div></section>
        </fieldset>
        <p id="limit" class="note"></p><p id="connection" class="note"></p>
        <div class="row spread bottom"><small>Changes send only when you apply.</small><button id="apply" class="primary">Apply to strip</button></div>
        <p id="message" class="note" role="status" aria-live="polite"></p>
      </dialog>`;
    this.$("#diy").onclick = () => this.openEditor();
    this.$("#close").onclick = () => this.$("dialog").close();
    this.$("#controls").onclick = () => this.dispatchEvent(new CustomEvent("hass-more-info", {bubbles:true,composed:true,detail:{entityId:this.config.entity}}));
    this.$("#power").onclick = async () => {
      try { await this._hass.callService("light", "toggle", {entity_id:this.config.entity}); }
      catch(error) { this.$("#card-message").textContent = error.message || String(error); }
    };
    this.$("#apply").onclick = () => this.apply();
    this.$("#fill").oninput = event => this.paint = event.target.value;
    this.$("#pencil").onclick = () => { this.erase = false; this.refreshControls(); };
    this.$("#eraser").onclick = () => { this.erase = true; this.refreshControls(); };
    this.$("#undo").onclick = () => { if (this.history.length) this.segments = this.history.pop(); this.dirty = true; this.draw(); };
    this.$("#clear").onclick = () => { this.snapshot(); this.segments.fill(null); this.dirty = true; this.draw(); };
    ["background", "none", "background-level", "speed"].forEach(id => this.$("#"+id).oninput = () => { this.dirty = true; this.refreshControls(); this.draw(); });
    this.shadowRoot.querySelectorAll("[data-effect]").forEach(button => button.onclick = () => { this.animation = button.dataset.effect; this.dirty = true; this.refreshControls(); });
    const strip = this.$(".strip");
    strip.onpointerdown = event => {
      const target = event.target.closest(".segment");
      if (!target || this.busy) return;
      this.snapshot(); this.drawing = true; strip.setPointerCapture(event.pointerId);
      this.paintSegment(Number(target.dataset.index));
    };
    strip.onpointermove = event => {
      if (!this.drawing) return;
      const target = this.shadowRoot.elementFromPoint(event.clientX,event.clientY)?.closest(".segment");
      if (target) this.paintSegment(Number(target.dataset.index));
    };
    strip.onpointerup = strip.onpointercancel = strip.onlostpointercapture = () => this.drawing = false;
    strip.onclick = event => {
      if (event.detail !== 0 || !event.target.matches(".segment")) return;
      this.snapshot(); this.paintSegment(Number(event.target.dataset.index));
    };
    this.refreshControls(); this.draw();
  }
}
if (!customElements.get("govee-h617a-card")) customElements.define("govee-h617a-card", GoveeH617ACard);
window.customCards = window.customCards || [];
window.customCards.push({type:"govee-h617a-card",name:"Govee H617A",description:"Light controls and an experimental Finger Sketch editor."});

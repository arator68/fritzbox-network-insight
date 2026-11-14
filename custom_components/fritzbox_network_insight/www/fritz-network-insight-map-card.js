/* FRITZ!Box Network Insight – standalone topology card.
 * Read-only adapter for the existing topology_view service. No topology inference.
 */
class FritzNetworkInsightMapCard extends HTMLElement {
  static getStubConfig() { return { design: "lcars", height: 620 }; }
  setConfig(config) {
    this.config = { design: "lcars", height: 620, refresh_seconds: 60, ...config };
    this._data = null;
    this._error = "";
    this._selected = null;
  }
  connectedCallback() {
    this._active = true;
    this._load();
    this._timer = setInterval(() => this._load(), Math.max(15, Number(this.config?.refresh_seconds) || 60) * 1000);
  }
  disconnectedCallback() {
    this._active = false;
    clearInterval(this._timer);
  }
  set hass(hass) {
    this._hass = hass;
    if (this._active && !this._data && !this._loading) this._load();
  }
  getCardSize() { return 8; }
  getGridOptions() { return { columns: "full", rows: "auto" }; }
  async _load() {
    if (!this._hass || this._loading || !this._active) return;
    this._loading = true;
    try {
      const response = await this._hass.callWS({
        type: "call_service", domain: "fritzbox_network_insight",
        service: "topology_view",
        service_data: this.config.entry_id ? { entry_id: this.config.entry_id } : {},
        return_response: true
      });
      const data = response?.response ?? response?.service_response ?? response;
      if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) {
        throw new Error(data?.error || "Keine gültigen Topologiedaten erhalten");
      }
      this._data = data;
      this._error = "";
    } catch (error) {
      this._error = String(error?.message || error);
    } finally {
      this._loading = false;
      if (this._active) this.render();
    }
  }
  _esc(value) {
    return String(value ?? "").replace(/[&<>"']/g, c => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[c]);
  }
  _kind(node) {
    const kind = String(node.device_type || "").toLowerCase();
    const role = String(node.mesh_role || "").toLowerCase();
    if (kind.includes("router") || role.includes("router") || role.includes("master")) return "router";
    if (kind.includes("switch")) return "switch";
    if (kind.includes("repeater") || role.includes("repeater")) return "repeater";
    return "device";
  }
  _layout(nodes) {
    // Presentation-only layout: no graph traversal or relationship inference.
    // The integration alone decides which edges are present.
    const map = new Map(nodes.map(n => [String(n.id || n.mac), n]));
    const components = nodes.filter(n => this._kind(n) !== "device");
    const groups = ["router", "switch", "repeater"];
    const layers = groups.map(kind => components.filter(n => this._kind(n) === kind))
      .filter(layer => layer.length);
    const positions = new Map();
    const width = Math.max(680, ...layers.map(layer => layer.length * 240 + 40));
    layers.forEach((layer, depth) => {
      layer.sort((a,b) => String(a.name).localeCompare(String(b.name)));
      layer.forEach((n,i) => positions.set(String(n.id || n.mac), {
        x: width * (i + 1) / (layer.length + 1), y: 65 + depth * 160
      }));
    });
    return { positions, width, height: Math.max(240, 160 * layers.length + 35), map };
  }
  _deviceConnection(node) {
    // The exact entity IDs and evidence are already produced by the integration.
    // Read them, do not infer a physical cable from a switch forwarding table.
    const compact = String(node.mac || node.id || "").replace(/:/g, "").toLowerCase();
    const peer = this._hass?.states?.[`sensor.fritzbox_network_insight_${compact}_connection_peer`];
    if (!peer || ["unknown", "unavailable", "none", ""].includes(String(peer.state).toLowerCase())) return null;
    const evidence = String(peer.attributes?.evidence || "");
    return {
      name: peer.state,
      mac: peer.attributes?.connected_to_mac || "",
      evidence,
      confirmed: peer.attributes?.direct_connection === "confirmed" ||
        evidence === "lldp_last_observed"
    };
  }
  render() {
    if (!this.config) return;
    const esc = v => this._esc(v);
    const data = this._data;
    // Only current FRITZ!Box hosts, never stale LLDP/FDB/Mesh-only identities.
    const nodes = (data?.nodes || []).filter(n => n.known_host === true);
    const currentIds = new Set(nodes.map(n => String(n.id || n.mac)));
    const edges = (data?.edges || []).filter(e =>
      currentIds.has(String(e.source)) && currentIds.has(String(e.target)) &&
      ((e.kind === "confirmed_lan" && e.physical_link_confirmed === true) ||
       (e.kind === "mesh_wlan" && e.evidence === "avm_mesh"))
    );
    const {positions, width, height, map} = this._layout(nodes);
    const kindLabel = { router: "Router", switch: "Switch", repeater: "Repeater", device: "Gerät" };
    const kindIcon = { router: "◉", switch: "▦", repeater: "⌁", device: "●" };
    const design = ["lcars","cyber","modern-dark","modern-light"].includes(this.config.design)
      ? this.config.design : "lcars";
    const selected = map.get(this._selected);
    const details = selected ? edges.filter(e => e.source === this._selected || e.target === this._selected) : [];\n    const selectedConnection = selected ? this._deviceConnection(selected) : null;
    const nodeButtons = [...positions.entries()].map(([id,p]) => {
      const n = map.get(id);
      const kind = this._kind(n);
      const count = edges.filter(e => e.source === id || e.target === id).length;
      return `<button class="fnm-node ${kind}" data-node="${esc(id)}" style="left:${p.x-95}px;top:${p.y}px">
        <span class="fnm-symbol">${kindIcon[kind]}</span>
        <span class="fnm-name"><strong>${esc(n.name || n.mac)}</strong><small>${kindLabel[kind]} · ${esc(n.ip_address || "")}</small></span>
        <span class="fnm-count">${count}</span>
      </button>`;
    }).join("");
    const lines = edges.filter(e => positions.has(e.source) && positions.has(e.target)).map(e => {
      const a = positions.get(e.source), b = positions.get(e.target);
      const dashed = e.kind === "mesh_wlan";
      return `<path d="M ${a.x} ${a.y+72} C ${a.x} ${(a.y+b.y)/2+45}, ${b.x} ${(a.y+b.y)/2+45}, ${b.x} ${b.y}" class="${dashed?"wlan":"lan"}"><title>${esc(e.evidence)}${e.port ? " · "+esc(e.port):""}</title></path>`;
    }).join("");
    const endDevices = nodes.filter(n => !positions.has(String(n.id || n.mac)));
    const linkedDevices = endDevices.filter(n => this._deviceConnection(n) ||
      edges.some(e => e.source === (n.id || n.mac) || e.target === (n.id || n.mac)));
    const unassigned = endDevices.filter(n => !linkedDevices.includes(n));
    const deviceItems = arr => arr.map(n => {
      const connection = this._deviceConnection(n);
      const relation = connection
        ? `<small title="${esc(connection.evidence)}">${connection.confirmed ? "Direkt: " : "Über Switch: "}${esc(connection.name)}</small>`
        : "";
      return `<button class="fnm-device" data-node="${esc(n.id || n.mac)}"><span>●</span>${esc(n.name || n.mac)}${relation}<small>${esc(n.ip_address || "")}</small></button>`;
    }).join("");
    const status = this._error ? `<div class="fnm-error">${esc(this._error)}</div>`
      : !data ? '<div class="fnm-info">Topologiedaten werden geladen …</div>' : "";
    this.innerHTML = `
      <ha-card class="fnm-card ${design}">
        <div class="fnm-wrap">
          <header class="fnm-toolbar"><strong>NETZWERKÜBERSICHT</strong>
            <span>${nodes.length} Geräte · ${edges.length} bestätigte Verbindungen</span>
            <button class="fnm-refresh" title="Aktualisieren">↻</button>
          </header>
          ${status}
          ${data ? `
          <div class="fnm-graph-scroll" style="max-height:${Math.max(250, Number(this.config.height) || 620)}px">
            <div class="fnm-graph" style="width:${width}px;height:${height}px">
              <svg class="fnm-lines" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none">${lines}</svg>
              ${nodeButtons}
            </div>
          </div>
          <div class="fnm-legend"><span>━ LLDP (direkt)</span><span>┄ Mesh-WLAN</span><span>Keine Verbindungen werden in der Karte berechnet</span></div>
          ${selected ? `<section class="fnm-detail"><button class="fnm-close">×</button><strong>${esc(selected.name || selected.mac)}</strong>
             <div>${esc(selected.mac)} · ${esc(selected.ip_address || "")}</div>
             <div>${details.map(e => `${esc(map.get(e.source === this._selected ? e.target : e.source)?.name || (e.source === this._selected ? e.target : e.source))} · ${esc(e.evidence)}${e.port ? " · "+esc(e.port) : ""}`).join("<hr>") || (selectedConnection ? `${esc(selectedConnection.confirmed ? "Direkt verbunden mit" : "Erreichbar über")} ${esc(selectedConnection.name)} (${esc(selectedConnection.evidence)})` : "Keine Zuordnung vorhanden")}</div>
           </section>` : ""}
          <details class="fnm-devices"><summary>Endgeräte mit vorhandener Zuordnung (${linkedDevices.length})</summary><div class="fnm-grid">${deviceItems(linkedDevices)}</div></details>
          <details class="fnm-devices"><summary>Ohne vorhandene Zuordnung (${unassigned.length})</summary><div class="fnm-grid">${deviceItems(unassigned)}</div></details>
          ` : ""}
        </div>
      </ha-card>
      <style>
        :host{display:block;width:100%;min-width:0}
        .fnm-card{--bg:#101827;--fg:#f5f7fa;--line:#b5c0cf;--router:#ffae00;--switch:#cc6666;--repeater:#9999ff;--tile:#202b3b}
        .fnm-card.cyber{--bg:#080d18;--fg:#e6fbff;--line:#00a9c7;--router:#00f0ff;--switch:#00bfa5;--repeater:#9b6bff;--tile:#101a2b}
        .fnm-card.modern-dark{--bg:#171b22;--fg:#f1f5f9;--line:#64748b;--router:#2563eb;--switch:#0f766e;--repeater:#7c3aed;--tile:#222a35}
        .fnm-card.modern-light{--bg:#fff;--fg:#1f2937;--line:#94a3b8;--router:#2563eb;--switch:#0f766e;--repeater:#7c3aed;--tile:#f1f5f9}
        .fnm-wrap{background:var(--bg);color:var(--fg);padding:12px;border:1px solid var(--line);border-radius:12px}
        .fnm-toolbar{display:flex;align-items:center;gap:16px;flex-wrap:wrap;font-size:12px;padding:4px 2px 14px}
        .fnm-toolbar strong{font-size:15px;letter-spacing:.06em}.fnm-toolbar span{opacity:.75}
        .fnm-refresh,.fnm-close{margin-left:auto;border:1px solid var(--line);border-radius:7px;background:var(--tile);color:var(--fg);padding:5px 11px;cursor:pointer}
        .fnm-graph-scroll{overflow:auto;border:1px solid var(--line);border-radius:10px;background:var(--bg)}
        .fnm-graph{position:relative;margin:auto;min-width:100%}
        .fnm-lines{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;overflow:visible}
        .fnm-lines path{fill:none;stroke:var(--line);stroke-width:2.5;opacity:.85}
        .fnm-lines .wlan{stroke-dasharray:8 7;stroke:var(--repeater)}
        .fnm-node{position:absolute;display:flex;align-items:center;gap:8px;width:190px;min-height:73px;box-sizing:border-box;padding:10px;border:1px solid var(--line);border-top:4px solid var(--switch);border-radius:10px;background:var(--tile);color:var(--fg);cursor:pointer;text-align:left}
        .fnm-node.router{border-top-color:var(--router)}.fnm-node.repeater{border-top-color:var(--repeater)}
        .fnm-node:hover,.fnm-device:hover{filter:brightness(1.2)}
        .fnm-symbol{font-size:23px}.fnm-name{min-width:0;flex:1}.fnm-name strong{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px}.fnm-name small{display:block;opacity:.7;font-size:10px;margin-top:5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .fnm-count{opacity:.7;font-size:11px}.fnm-legend{display:flex;gap:18px;flex-wrap:wrap;font-size:11px;opacity:.75;padding:10px 2px}
        .fnm-detail{position:relative;border:1px solid var(--line);border-radius:9px;background:var(--tile);padding:14px;font-size:12px}
        .fnm-detail strong{font-size:15px}.fnm-detail>div{margin-top:9px}.fnm-close{float:right}
        .fnm-devices{margin-top:10px;border:1px solid var(--line);border-radius:9px;padding:10px;font-size:12px}
        .fnm-devices summary{cursor:pointer}.fnm-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:8px;margin-top:12px}
        .fnm-device{display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:7px;background:var(--tile);color:var(--fg);padding:10px;text-align:left;cursor:pointer;min-width:0}
        .fnm-device small{margin-left:auto;opacity:.6}.fnm-error{color:#ff9a9a;padding:12px}.fnm-info{padding:12px}
      </style>`;
    this.querySelector(".fnm-refresh")?.addEventListener("click", () => this._load());
    this.querySelector(".fnm-close")?.addEventListener("click", () => { this._selected = null; this.render(); });
    this.querySelectorAll("[data-node]").forEach(button => button.addEventListener("click", () => {
      this._selected = button.dataset.node; this.render();
    }));
  }
}
if (!customElements.get("fritz-network-insight-map-card")) {
  customElements.define("fritz-network-insight-map-card", FritzNetworkInsightMapCard);
}
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === "fritz-network-insight-map-card")) {
  window.customCards.push({
    type: "fritz-network-insight-map-card",
    name: "FRITZ!Box Network Insight Map",
    description: "Read-only topology map with verified LLDP and AVM Mesh connections"
  });
}

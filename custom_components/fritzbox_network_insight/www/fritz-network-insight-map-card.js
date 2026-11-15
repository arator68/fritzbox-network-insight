import "./fritz-network-insight-topology-dialog.js";
/* All user-facing frontend text is loaded from the language files. */
import deFrontend from "./translations/de.js";
import enFrontend from "./translations/en.js";

const FNM_TRANSLATIONS = { de: deFrontend, en: enFrontend };
const fnmText = (hass, key) => {
  const language = String(hass?.locale?.language || hass?.language || document.documentElement.lang || "en").toLowerCase();
  const dictionary = language.startsWith("de") ? FNM_TRANSLATIONS.de : FNM_TRANSLATIONS.en;
  return dictionary[key] ?? FNM_TRANSLATIONS.en[key] ?? key;
};

/* FRITZ!Box Network Map Card - renderer only */
class FritzNetworkMapCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("fritz-network-map-card-editor");
  }
  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(id => id === "sensor.netzwerk_topologie")
      || Object.keys(hass?.states || {}).find(id => id.startsWith("sensor.") && id.includes("topologie"))
      || "";
    return { entity, theme: "auto", design: "cyber" };
  }
  connectedCallback() {
    // Home Assistant can attach the card before its final layout width is known.
    // Observe the host and redraw once its real width is available or changes.
    if (typeof ResizeObserver !== "undefined" && !this._layoutObserver) {
      this._layoutObserver = new ResizeObserver(entries => {
        const width = Math.round(entries[0]?.contentRect?.width || this.clientWidth || 0);
        if (!width || Math.abs(width - (this._observedWidth || 0)) < 8) return;
        this._observedWidth = width;
        if (this._layoutFrame) cancelAnimationFrame(this._layoutFrame);
        this._layoutFrame = requestAnimationFrame(() => {
          this._layoutFrame = null;
          if (this.isConnected && this._hass && this.config) this.render();
        });
      });
      this._layoutObserver.observe(this);
    }
  }
  disconnectedCallback() {
    if (this._layoutObserver) {
      this._layoutObserver.disconnect();
      this._layoutObserver = null;
    }
    if (this._layoutFrame) {
      cancelAnimationFrame(this._layoutFrame);
      this._layoutFrame = null;
    }
  }
  setConfig(config) {
    if (!config) throw new Error("Missing card configuration");
    this.config = { colors: {}, entity: "Network Insight", ...config };
    this._signature = null;
    if (this._selectedComponent === undefined) this._selectedComponent = null;
    if (!Array.isArray(this._componentHistory)) this._componentHistory = [];
    this._restoreViewState();
  }
  _viewStorageKey() {
    // Each browser/device keeps its own navigation state.
    return `fritz-network-map:view:${this.config?.entity || "default"}`;
  }
  _restoreViewState() {
    try {
      const raw = window.localStorage.getItem(this._viewStorageKey());
      if (!raw) return;
      const state = JSON.parse(raw);
      this._selectedComponent = typeof state.selectedComponent === "string"
        ? state.selectedComponent : null;
      this._componentHistory = Array.isArray(state.componentHistory)
        ? state.componentHistory.filter(id => typeof id === "string")
        : [];
    } catch (err) {
      // Storage may be unavailable in private browsing; the card still works.
    }
  }
  _saveViewState() {
    try {
      window.localStorage.setItem(this._viewStorageKey(), JSON.stringify({
        selectedComponent: this._selectedComponent,
        componentHistory: this._componentHistory
      }));
    } catch (err) {
      // Storage restrictions must not affect normal card operation.
    }
  }
  set topologyData(data) {
    const next = JSON.stringify([data?.nodes || [], data?.edges || []]);
    if (next === this._topologySignature) return;
    this._topology = data;
    this._topologySignature = next;
    this._signature = null;
    if (this._hass && this.config) this.render();
  }
  set hass(hass) {
    this._hass = hass;
    if (!this.config) return;
    const signature = JSON.stringify([this._topology?.nodes || [], this._topology?.edges || []]);
    if (signature === this._signature && this.querySelector(".fnm-wrap")) return;
    this._signature = signature;
    this.render();
  }
  // Native Home Assistant Sections sizing: always occupy the complete
  // width of the section (including sections with column_span > 1).
  // This is layout metadata only; it does not depend on the active theme.
  getGridOptions() {
    return { columns: "full", rows: "auto" };
  }
  getCardSize() { return 7; }
  render() {
    if (!this._hass || !this.config) return;
    // Read Network Insight topology_view directly; do not synthesize topology links.
    const nodes = (this._topology?.nodes || []).filter(n => n.known_host === true).map(n => {
      const mac = String(n.mac || n.id || "");
      const key = mac.replace(/:/g, "").toLowerCase();
      const state = this._hass.states?.[`sensor.fritzbox_network_insight_${key}_status`];
      const role = String(state?.attributes?.device_type || n.device_type || "").toLowerCase();
      const kind = role === "access_point" ? "repeater" : ["router", "switch", "repeater"].includes(role) ? role : "device";
      return { ...n, id: String(n.id || n.mac).toUpperCase(), kind,
        ipv4: state?.attributes?.ip_address || n.ip_address || "",
        active: state?.state === "online" || n.online === true,
        status: state?.state || (n.online === true ? "online" : n.online === false ? "offline" : "unknown") };
    });
    const edges = (this._topology?.edges || []).filter(e =>
      (e.kind === "mesh_wlan" && e.evidence === "avm_mesh") ||
      (e.kind === "confirmed_lan" && e.physical_link_confirmed === true)
    ).map(e => ({...e, source: String(e.source || "").toUpperCase(), target: String(e.target || "").toUpperCase()}));
    const theme = ["light", "dark"].includes(this.config.theme) ? this.config.theme : "auto";
    const design = ["modern-dark", "modern-light", "lcars", "cyber", "custom"].includes(this.config.design)
      ? this.config.design : "cyber";
    const designPalettes = {
      "modern-dark": { background:"#171b22", text:"#f1f5f9", line:"#64748b", router:"#2563eb", switch:"#0f766e", repeater:"#7c3aed", device:"#222a35" },
      "modern-light": { background:"#ffffff", text:"#1f2937", line:"#94a3b8", router:"#2563eb", switch:"#0f766e", repeater:"#7c3aed", device:"#f1f5f9" },
      "lcars": { background:"#101827", text:"#f5f7fa", line:"#b5c0cf", router:"#ffae00", switch:"#cc6666", repeater:"#9999ff", device:"#202b3b" },
      "cyber": { background:"#080d18", text:"#e6fbff", line:"#00a9c7", router:"#00f0ff", switch:"#00bfa5", repeater:"#9b6bff", device:"#101a2b" },
      "custom": { background:"#111827", text:"#f3f4f6", line:"#64748b", router:"#2563eb", switch:"#0f766e", repeater:"#7c3aed", device:"#263445" }
    };
    const prefersLight = theme === "light" || (theme === "auto" && window.matchMedia?.("(prefers-color-scheme: light)").matches);
    const palette = designPalettes[design];
    const colors = {
      ...palette,
      ...(design === "modern-dark" && prefersLight ? designPalettes["modern-light"] : {}),
      ...this.config.colors
    };
    const animateConnections = this.config.animate_connections !== false;
    const svgPath = (d, index = 0) => {
      const delay = (index * 0.19).toFixed(2);
      return `<path d="${d}" />${animateConnections ? `<path class="fnm-graph-pulse" d="${d}" style="animation-delay:${-(index * 0.19).toFixed(2)}s" />` : ""}`;
    };
    this.style.cssText += ";display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box";
    const esc = v => String(v ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const byId = new Map(nodes.map(n => [String(n.id), n]));
    const component = n => ["router","switch","repeater"].includes(String(n?.kind || "").toLowerCase());
    const children = new Map(nodes.map(n => [String(n.id), []]));
    const parents = new Map();
    edges.forEach(e => {
      const a=String(e.source || ""), b=String(e.target || "");
      if (!byId.has(a) || !byId.has(b) || a===b) return;
      if (!children.has(a)) children.set(a,[]);
      if (!children.get(a).includes(b)) children.get(a).push(b);
      if (!parents.has(b)) parents.set(b,[]);
      parents.get(b).push(a);
    });
    const kindLabel = k => ({router:fnmText(this._hass,"ui.router"),switch:fnmText(this._hass,"ui.switch"),repeater:fnmText(this._hass,"ui.repeater"),device:fnmText(this._hass, "ui.end_device")})[String(k||"").toLowerCase()] || fnmText(this._hass, "ui.device");
    const kindIcon = k => ({router:"◉",switch:"▦",repeater:"⌁",device:"●"})[String(k||"").toLowerCase()] || "●";
    const online = n => n.active === true || ["online","connected","verbunden","aktiv"].includes(String(n.status||"").toLowerCase());
    const components = nodes.filter(component);
    const componentChildren = n => (children.get(String(n.id))||[]).map(id=>byId.get(id)).filter(Boolean);
    const directDevices = n => componentChildren(n).filter(x=>!component(x));
    const directComponents = n => componentChildren(n).filter(component);
    const parentNames = n => (parents.get(String(n.id))||[]).map(id=>byId.get(id)).filter(Boolean).map(p=>p.name||kindLabel(p.kind));
    const assigned = new Set();
    edges.forEach(e=>{if(e.target)assigned.add(String(e.target));});
    const unassigned = nodes.filter(n=>!component(n)&&!assigned.has(String(n.id)));
    const selected = this._selectedComponent === "__unassigned__"
      ? null : byId.get(String(this._selectedComponent));
    if (this._selectedComponent && this._selectedComponent !== "__unassigned__" && (!selected || !component(selected))) {
      this._selectedComponent = null;
      this._componentHistory = [];
      this._saveViewState();
    }
    const current = this._selectedComponent === "__unassigned__" ? null : (this._selectedComponent ? byId.get(String(this._selectedComponent)) : null);
    // Display-only hierarchy: choose one parent per component by walking outward
    // from the router. This resolves reciprocal/cyclic raw edges for navigation
    // without changing the sensor data, edge list, or topology calculation.
    const canonicalParent = new Map();
    const hierarchyRoot = components.find(n => String(n.kind).toLowerCase() === "router")
      || components.find(n => !(parents.get(String(n.id)) || []).some(id => component(byId.get(id))))
      || components[0];
    if (hierarchyRoot) {
      const visited = new Set([String(hierarchyRoot.id)]);
      const pending = [String(hierarchyRoot.id)];
      while (pending.length) {
        const parentId = pending.shift();
        (children.get(parentId) || []).forEach(childId => {
          if (!byId.has(childId) || !component(byId.get(childId)) || visited.has(childId)) return;
          visited.add(childId);
          canonicalParent.set(childId, parentId);
          pending.push(childId);
        });
      }
    }
    const totalOnline = nodes.filter(online).length;
    const totalOffline = nodes.length-totalOnline;

    const deviceChip = n => `<button class="fnm-device-chip ${online(n)?"is-online":"is-offline"}" data-node="${esc(n.id)}" title="${esc(n.name||n.mac||fnmText(this._hass, "ui.device"))} · ${esc(n.ipv4||n.mac||"")}"><i></i><span>${esc(n.name||n.mac||fnmText(this._hass, "ui.device"))}</span><small>${esc(n.ipv4||"")}</small></button>`;
    const componentCard = n => {
      const devs=directDevices(n), nested=directComponents(n);
      const all=componentChildren(n);
      const on=all.filter(online).length;
      return `<button class="fnm-overview-card ${esc(n.kind)}" data-open-component="${esc(n.id)}">
        <div class="fnm-overview-icon">${kindIcon(n.kind)}</div>
        <div class="fnm-overview-main"><strong>${esc(n.name||kindLabel(n.kind))}</strong><small>${kindLabel(n.kind)}${n.ipv4?" · "+esc(n.ipv4):""}</small></div>
        <span class="fnm-overview-arrow">›</span>
        <div class="fnm-overview-stats"><b>${all.length}</b><span>${fnmText(this._hass, "ui.direct_devices_components")}</span><i class="fnm-status-dot"></i><span>${on} online · ${all.length-on} ${fnmText(this._hass, "ui.offline")}</span></div>
        ${nested.length?`<div class="fnm-overview-nested">${nested.map(x=>`${kindIcon(x.kind)} ${esc(x.name||kindLabel(x.kind))}`).join(" · ")}</div>`:""}
      </button>`;
    };
    const selectedTitle = this._selectedComponent === "__unassigned__" ? fnmText(this._hass, "ui.unassigned_devices") : (current?.name || fnmText(this._hass, "ui.component_details"));
    let content;
    if (this._selectedComponent === "__unassigned__") {
      content = `<div class="fnm-detail-toolbar"><button class="fnm-back">← ${fnmText(this._hass, "ui.overview")}</button><div><strong>${esc(selectedTitle)}</strong><small>${unassigned.length} ${fnmText(this._hass, "ui.devices_without_a_recognized_direct_connection")}</small></div></div><div class="fnm-device-grid fnm-detail-devices">${unassigned.map(deviceChip).join("") || `<div class="fnm-empty">${fnmText(this._hass, "ui.no_unassigned_devices")}</div>`}</div>`;
    } else if (current) {
      const devs=directDevices(current), canonicalParentId=canonicalParent.get(String(current.id));
      const parentComponents=canonicalParentId && byId.has(canonicalParentId) ? [byId.get(canonicalParentId)] : [];
      const parentIds=new Set(parentComponents.map(n=>String(n.id)));
      // A parent can also appear in the raw child list when the source reports
      // reciprocal records. Never render that parent as a child of the selected node.
      const nested=directComponents(current).filter(n=>!parentIds.has(String(n.id)));
      const total=componentChildren(current);
      const subNodeW=190, subNodeH=94, subRootW=220, subRootH=94;
      const subAvailable=Math.max(0,(this._observedWidth||this.clientWidth||0)-64);
      const siblingCount=Math.max(1,parentComponents.length,nested.length);
      const subGap=Math.max(210,Math.min(300,(subAvailable-56)/siblingCount));
      const subWidth=Math.max(920,subAvailable,56+Math.max(parentComponents.length,nested.length,1)*subGap);
      const subCenter=subWidth/2, parentY=22, currentY=174, childY=342;
      const spreadCenters=count=>Array.from({length:count},(_,i)=>subWidth/2+(i-(count-1)/2)*subGap);
      const parentCenters=spreadCenters(parentComponents.length);
      const childCenters=spreadCenters(nested.length);
      const subHeight=nested.length?450:300;
      const subLines=[];
      parentComponents.forEach((p,i)=>{
        const x=parentCenters[i], startY=parentY+subNodeH, endY=currentY;
        const bend=Math.max(28,(endY-startY)*0.48);
        // One independent curved connector for each actual parent -> selected-node edge.
        subLines.push(svgPath(`M ${x} ${startY} C ${x} ${startY+bend}, ${subCenter} ${endY-bend}, ${subCenter} ${endY}`,i));
      });
      nested.forEach((n,i)=>{
        const x=childCenters[i], startY=currentY+subRootH, endY=childY;
        const bend=Math.max(28,(endY-startY)*0.48);
        // One independent curved connector for each actual selected-node -> child edge.
        subLines.push(svgPath(`M ${subCenter} ${startY} C ${subCenter} ${startY+bend}, ${x} ${endY-bend}, ${x} ${endY}`,parentComponents.length+i));
      });
      const parentCards=parentComponents.map((p,i)=>{
        const x=parentCenters[i];
        return `<button class="fnm-graph-node ${esc(p.kind)}" style="left:${x-subNodeW/2}px;top:${parentY}px;width:${subNodeW}px;height:${subNodeH}px" data-open-component="${esc(p.id)}"><span class="fnm-graph-icon">${kindIcon(p.kind)}</span><span class="fnm-graph-label"><strong>${esc(p.name||kindLabel(p.kind))}</strong><small>${kindLabel(p.kind)}${p.ipv4?" · "+esc(p.ipv4):""}</small><em>${fnmText(this._hass, "ui.parent_component")}</em></span><span class="fnm-graph-arrow">›</span></button>`;
      }).join("");
      const currentOnline=devs.filter(online).length;
      const selectedCard=`<div class="fnm-graph-node ${esc(current.kind)} fnm-graph-root fnm-graph-selected" style="left:${subCenter-subRootW/2}px;top:${currentY}px;width:${subRootW}px;height:${subRootH}px"><span class="fnm-graph-icon">${kindIcon(current.kind)}</span><span class="fnm-graph-label"><strong>${esc(current.name||kindLabel(current.kind))}</strong><small>${kindLabel(current.kind)}${current.ipv4?" · "+esc(current.ipv4):""}</small><em>${devs.length} ${fnmText(this._hass, "ui.end_devices")} · ${nested.length} ${fnmText(this._hass, "ui.components")}</em></span><span class="fnm-graph-status"><i></i>${currentOnline} ${fnmText(this._hass, "ui.online")} · ${devs.length-currentOnline} ${fnmText(this._hass, "ui.offline")}</span></div>`;
      const childCards=nested.map((n,i)=>{
        const x=childCenters[i], childDevices=directDevices(n), on=childDevices.filter(online).length;
        return `<button class="fnm-graph-node ${esc(n.kind)}" style="left:${x-subNodeW/2}px;top:${childY}px;width:${subNodeW}px;height:${subNodeH}px" data-open-component="${esc(n.id)}"><span class="fnm-graph-icon">${kindIcon(n.kind)}</span><span class="fnm-graph-label"><strong>${esc(n.name||kindLabel(n.kind))}</strong><small>${kindLabel(n.kind)}${n.ipv4?" · "+esc(n.ipv4):""}</small><em>${childDevices.length} ${fnmText(this._hass, "ui.end_devices")} · ${directComponents(n).length} ${fnmText(this._hass, "ui.components")}</em></span><span class="fnm-graph-arrow">›</span><span class="fnm-graph-status"><i></i>${on} ${fnmText(this._hass, "ui.online")} · ${childDevices.length-on} ${fnmText(this._hass, "ui.offline")}</span></button>`;
      }).join("");
      const subSvg=`<svg class="fnm-graph-lines ${animateConnections?"is-animated":""}" viewBox="0 0 ${subWidth} ${subHeight}" width="${subWidth}" height="${subHeight}" aria-hidden="true">${subLines.join("")}</svg>`;
      const subGraph=`<div class="fnm-graph-scroll"><div class="fnm-graph-canvas" style="width:${subWidth}px;height:${subHeight}px">${subSvg}${parentCards}${selectedCard}${childCards}</div></div>`;
      content = `<div class="fnm-detail-toolbar"><button class="fnm-back">← ${this._componentHistory.length ? fnmText(this._hass, "ui.parent_level") : fnmText(this._hass, "ui.overview")}</button><div class="fnm-detail-heading"><strong>${esc(current.name||kindLabel(current.kind))}</strong><small>${kindLabel(current.kind)}${current.ipv4?" · "+esc(current.ipv4):""} · ${fnmText(this._hass, "ui.parent")}${esc(parentComponents.map(p=>p.name||kindLabel(p.kind)).join(", ")||fnmText(this._hass, "ui.no_recognized_parent_component"))}</small></div><span class="fnm-detail-count">${total.length} ${fnmText(this._hass, "ui.direct_connections")}</span></div>
        <div class="fnm-section-heading">${fnmText(this._hass, "ui.network_hierarchy_parent_component_selection_and_child_component")}</div>
        ${subGraph}
        <div class="fnm-section-heading">${fnmText(this._hass, "ui.connected_devices")}</div><div class="fnm-device-grid fnm-detail-devices">${devs.map(deviceChip).join("") || `<div class="fnm-empty">${fnmText(this._hass, "ui.no_directly_connected_end_devices")}</div>`}</div>`;

    } else {
      // Hierarchical layout: positions follow the actual component-to-component
      // edges. Device clusters are attached only to their reported direct parent.
      const root = components.find(n => String(n.kind).toLowerCase() === "router")
        || components.find(n => !(parents.get(String(n.id)) || []).some(id => component(byId.get(id))))
        || components[0];
      const rootId = root ? String(root.id) : "";
      const componentIds = new Set(components.map(n => String(n.id)));
      const treeChildren = new Map(components.map(n => [String(n.id), []]));
      const treeParent = new Map();
      const seen = new Set(root ? [rootId] : []);
      const queue = root ? [rootId] : [];
      // Breadth-first traversal assigns each component one layout parent.
      while ( (queue.length) ) {
        const parentId = queue.shift();
        const reportedChildren = (children.get(parentId) || []).filter(id => componentIds.has(id));
        reportedChildren.forEach(childId => {
          if (seen.has(childId)) return;
          seen.add(childId);
          treeParent.set(childId, parentId);
          treeChildren.get(parentId).push(childId);
          queue.push(childId);
        });
      }
      // Keep disconnected components visible without fabricating a connection.
      const disconnected = components.map(n => String(n.id)).filter(id => id !== rootId && !seen.has(id));
      disconnected.forEach(id => { seen.add(id); treeParent.set(id, null); });
      const treeRoots = [rootId, ...disconnected].filter(Boolean);
      const nodeW = 190, nodeH = 94, rootW = 220, rootH = 94;
      const leftPad = 28, topPad = 22, levelGap = 188, minLeafGap = 210;
      const xById = new Map(), depthById = new Map(), leafIndex = new Map();
      let leafCursor = 0;
      // First pass: determine tree depth and stable left-to-right leaf order.
      const collectLeaves = (id, depth) => {
        depthById.set(id, depth);
        const kids = treeChildren.get(id) || [];
        if (!kids.length) {
          leafIndex.set(id, leafCursor++);
          return;
        }
        kids.forEach(child => collectLeaves(child, depth + 1));
      };
      treeRoots.forEach(id => collectLeaves(id, 0));
      const leafCount = Math.max(1, leafCursor);
      // Use the available card width, but retain a minimum spacing so large
      // topologies scroll horizontally instead of compressing nodes together.
      const availableWidth = Math.max(0, (this._observedWidth || this.clientWidth || 0) - 64);
      const graphWidth = Math.max(920, availableWidth, leftPad * 2 + leafCount * minLeafGap);
      const usableWidth = graphWidth - leftPad * 2;
      const leafX = index => leftPad + usableWidth * ((index + 0.5) / leafCount);
      // Second pass: place parents at the midpoint of their visible children.
      const placeTree = id => {
        const kids = treeChildren.get(id) || [];
        if (!kids.length) {
          const x = leafX(leafIndex.get(id) ?? 0);
          xById.set(id, x);
          return x;
        }
        const childXs = kids.map(placeTree);
        const x = childXs.reduce((sum,value)=>sum+value,0) / childXs.length;
        xById.set(id, x);
        return x;
      };
      treeRoots.forEach(placeTree);
      // Center a single isolated root or any component with no descendants.
      if (root && !xById.has(rootId)) xById.set(rootId, graphWidth / 2);
      const maxDepth = Math.max(0, ...Array.from(depthById.values()));
      const graphHeight = topPad + (maxDepth + 1) * levelGap + 20;
      const nodeTop = id => topPad + (depthById.get(id) || 0) * levelGap;
      const nodeBottomY = id => nodeTop(id) + (id === rootId ? rootH : nodeH);

      const nodeMarkup = n => {
        const id=String(n.id), isRoot=id===rootId, x=xById.get(id) ?? graphWidth/2;
        const y=nodeTop(id), w=isRoot?rootW:nodeW, h=isRoot?rootH:nodeH;
        const devs=directDevices(n), nested=directComponents(n), on=devs.filter(online).length;
        const detailText = `${devs.length} ${fnmText(this._hass, "ui.end_devices")} · ${nested.length} ${fnmText(this._hass, "ui.components")}`;
        return `<button class="fnm-graph-node ${esc(n.kind)} ${isRoot?"fnm-graph-root":""}" style="left:${x-w/2}px;top:${y}px;width:${w}px;height:${h}px" data-open-component="${esc(id)}"><span class="fnm-graph-icon">${kindIcon(n.kind)}</span><span class="fnm-graph-label"><strong>${esc(n.name||kindLabel(n.kind))}</strong><small>${kindLabel(n.kind)}${n.ipv4?" · "+esc(n.ipv4):""}</small><em>${detailText}</em></span><span class="fnm-graph-arrow">›</span><span class="fnm-graph-status"><i></i>${on} ${fnmText(this._hass, "ui.online")} · ${devs.length-on} ${fnmText(this._hass, "ui.offline")}</span></button>`;
      };
      const graphEdges = [];
      // Draw every reported component edge. The tree controls placement only;
      // additional/multiple reported edges remain visible as real cross-links.
      const renderedComponentLinks = new Set();
      edges.forEach((e,index) => {
        const a=String(e.source||""), b=String(e.target||"");
        if (!componentIds.has(a) || !componentIds.has(b) || !xById.has(a) || !xById.has(b) || a===b) return;
        // Some topology sources expose the same physical link in both directions.
        // Treat the link as undirected for drawing and render it only once.
        const linkKey = [a,b].sort().join("|");
        if (renderedComponentLinks.has(linkKey)) return;
        renderedComponentLinks.add(linkKey);
        // Route from the visually upper component to the lower one, regardless
        // of the source/target direction in the raw edge record.
        const aTop=nodeTop(a), bTop=nodeTop(b);
        const upper=aTop<=bTop?a:b, lower=upper===a?b:a;
        const ax=xById.get(upper), bx=xById.get(lower);
        const ay=nodeBottomY(upper), by=nodeTop(lower);
        const bend=Math.max(30,(by-ay)*0.48);
        graphEdges.push(svgPath(`M ${ax} ${ay} C ${ax} ${ay+bend}, ${bx} ${by-bend}, ${bx} ${by}`,graphEdges.length));
      });
      const svg = `<svg class="fnm-graph-lines ${animateConnections?"is-animated":""}" viewBox="0 0 ${graphWidth} ${graphHeight}" width="${graphWidth}" height="${graphHeight}" aria-hidden="true">${graphEdges.join("")}</svg>`;
      const graphNodes = [...components].sort((a,b)=>(depthById.get(String(a.id))||0)-(depthById.get(String(b.id))||0)).map(nodeMarkup).join("");
      const graph = `<div class="fnm-graph-scroll"><div class="fnm-graph-canvas" style="width:${graphWidth}px;height:${graphHeight}px">${svg}${graphNodes}</div></div>`;
      content = `<div class="fnm-overview-statsbar"><div><b>${nodes.length}</b><span>${fnmText(this._hass, "ui.total_devices")}</span></div><div><b>${components.length}</b><span>${fnmText(this._hass, "ui.network_components")}</span></div><div><b>${totalOnline}</b><span>${fnmText(this._hass, "ui.online_2")}</span></div><div><b>${totalOffline}</b><span>${fnmText(this._hass, "ui.offline_2")}</span></div></div>
        <div class="fnm-section-heading">${fnmText(this._hass, "ui.network_topology_select_a_node_for_details")}</div>
        ${graph || `<div class="fnm-empty">${fnmText(this._hass, "ui.no_network_components_detected")}</div>`}
        <button class="fnm-unassigned-entry" data-open-component="__unassigned__"><span>${fnmText(this._hass, "ui.other_unassigned_devices")}</span><b>${unassigned.length}</b><span>${fnmText(this._hass, "ui.show_devices")}</span></button>`;
    }
    this.innerHTML=`<ha-card><div class="fnm-wrap">
      <div class="fnm-toolbar"><div class="fnm-summary">${this._selectedComponent ? fnmText(this._hass, "ui.network_details") : fnmText(this._hass, "ui.network_overview")} <span>·</span> ${fnmText(this._hass, "ui.data_source")}${esc(this.config.entity)}</div><div class="fnm-controls"><button class="fnm-fit">${this._selectedComponent?fnmText(this._hass, "ui.overview_2"):fnmText(this._hass, "ui.overview")}</button></div></div>
      <div class="fnm-overview">${content}</div>
      <div class="fnm-detail" hidden></div>
      <div class="fnm-note">${fnmText(this._hass, "ui.this_view_uses_only_the_direct_connections_reported_by_the_topol")}</div>
    </div></ha-card>`;
    const style=document.createElement("style");
    style.textContent=`:host{display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box}fritz-network-map-card > ha-card{width:100%;max-width:100%;box-sizing:border-box}.fnm-wrap{background:${colors.background};color:${colors.text};padding:0 14px 14px;box-sizing:border-box}.fnm-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px}.fnm-summary{font-size:12px;opacity:.76}.fnm-controls button,.fnm-back{border:1px solid ${colors.line};border-radius:7px;padding:7px 11px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-overview{display:flex;flex-direction:column;gap:13px}.fnm-overview-statsbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.fnm-overview-statsbar>div{border:1px solid ${colors.line};border-radius:9px;padding:11px;background:${colors.device};display:flex;flex-direction:column;gap:3px}.fnm-overview-statsbar b{font-size:23px;color:${colors.text}}.fnm-overview-statsbar span{font-size:10px;opacity:.7}.fnm-section-heading{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.72;margin:3px 0 -3px}.fnm-overview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:10px;align-items:stretch}.fnm-overview-card{position:relative;display:grid;grid-template-columns:38px minmax(0,1fr) 20px;gap:8px;align-items:center;text-align:left;min-width:0;padding:12px;border:1px solid ${colors.line};border-top:3px solid ${colors.switch};border-radius:10px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-overview-card.repeater{border-top-color:${colors.repeater}}.fnm-overview-card.router{border-top-color:${colors.router}}.fnm-overview-card:hover,.fnm-unassigned-entry:hover{filter:brightness(1.12);border-color:${colors.text}}.fnm-overview-icon{width:34px;height:34px;border-radius:9px;background:${colors.background};display:grid;place-items:center;font-size:20px}.fnm-overview-main{min-width:0}.fnm-overview-main strong{display:block;font-size:14px;overflow-wrap:anywhere}.fnm-overview-main small{display:block;font-size:10px;opacity:.7;margin-top:4px}.fnm-overview-arrow{font-size:25px;opacity:.7;text-align:center}.fnm-overview-stats{grid-column:2/-1;display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:10px;opacity:.78}.fnm-overview-stats b{font-size:18px;color:${colors.text}}.fnm-status-dot{width:7px;height:7px;border-radius:50%;background:#27ae60;display:inline-block}.fnm-overview-nested{grid-column:2/-1;font-size:10px;opacity:.65;border-top:1px solid ${colors.line}66;padding-top:7px}.fnm-graph-scroll{width:100%;overflow-x:auto;overflow-y:hidden;scrollbar-width:none;-ms-overflow-style:none;border:1px solid ${colors.line}88;border-radius:10px;background:linear-gradient(180deg,${colors.background},${colors.device}55);padding:8px;box-sizing:border-box}.fnm-graph-scroll::-webkit-scrollbar{display:none;width:0;height:0}.fnm-graph-canvas{position:relative;margin:0 auto;min-width:100%;}.fnm-graph-lines{position:absolute;inset:0;overflow:visible;pointer-events:none}.fnm-graph-lines path{fill:none;stroke:${colors.line};stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.78}.fnm-graph-lines .fnm-graph-pulse{display:none}.fnm-graph-lines.is-animated .fnm-graph-pulse{display:block;fill:none;stroke:#39e8ff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:9 25;stroke-dashoffset:0;opacity:.98;filter:none;animation:fnm-connection-flow 3.2s linear infinite}@keyframes fnm-connection-flow{to{stroke-dashoffset:-40}}@media(prefers-reduced-motion:reduce){.fnm-graph-lines.is-animated .fnm-graph-pulse{animation:none;stroke-dasharray:9 25;opacity:.45}}.fnm-graph-node{position:absolute;z-index:2;display:grid;grid-template-columns:34px minmax(0,1fr) 15px;gap:7px;align-items:center;text-align:left;padding:9px;border:1px solid ${colors.line};border-top:3px solid ${colors.switch};border-radius:10px;background:${colors.device};color:${colors.text};cursor:pointer;box-sizing:border-box}.fnm-graph-node.router{border-top-color:${colors.router}}.fnm-graph-node.repeater{border-top-color:${colors.repeater}}.fnm-graph-node:hover{filter:brightness(1.14);border-color:${colors.text}}.fnm-graph-root{border-width:1px;border-top-width:4px}.fnm-graph-selected{border:2px solid ${colors.text};box-shadow:0 0 0 2px ${colors.line}55}.fnm-graph-icon{width:32px;height:32px;border-radius:8px;background:${colors.background};display:grid;place-items:center;font-size:19px}.fnm-graph-label{min-width:0}.fnm-graph-label strong{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.fnm-graph-label small{display:block;font-size:9px;opacity:.7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}.fnm-graph-label em{display:block;font-size:9px;font-style:normal;opacity:.75;margin-top:5px}.fnm-graph-arrow{font-size:22px;opacity:.7}.fnm-graph-status{grid-column:2/-1;display:flex;align-items:center;gap:6px;font-size:9px;opacity:.78}.fnm-graph-status i,.fnm-graph-dots i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#89919d}.fnm-graph-status i{background:#27ae60}.fnm-graph-device-cluster{position:absolute;z-index:1;min-height:54px;box-sizing:border-box;border:1px dashed ${colors.line};border-radius:8px;padding:6px 8px;background:${colors.background};display:flex;flex-direction:column;gap:5px}.fnm-graph-cluster-title{font-size:8px;letter-spacing:.06em;opacity:.65}.fnm-graph-dots{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.fnm-graph-dots i.on{background:#27ae60;box-shadow:0 0 5px #27ae6080}.fnm-graph-dots i.off{background:#d97706}.fnm-graph-dots b{font-size:9px;opacity:.75}.fnm-graph-device-cluster small{font-size:9px;opacity:.65}.fnm-graph-root-devices{position:absolute;z-index:2;display:flex;align-items:center;gap:7px;padding:5px 8px;border:1px dashed ${colors.line};border-radius:7px;background:${colors.background};font-size:9px;white-space:nowrap}.fnm-unassigned-entry{appearance:none!important;width:100%;box-sizing:border-box;background:${colors.background}!important;color:${colors.text}!important;border:1px dashed ${colors.line}!important;display:flex;align-items:center;gap:12px;text-align:left;border:1px dashed ${colors.line};border-radius:9px;padding:12px;background:${colors.background};color:${colors.text};cursor:pointer}.fnm-unassigned-entry b{font-size:18px}.fnm-unassigned-entry span:last-child{margin-left:auto;font-size:11px;opacity:.7}.fnm-detail-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:3px 0 12px;border-bottom:1px solid ${colors.line}66}.fnm-detail-heading{min-width:0;flex:1}.fnm-detail-heading strong,.fnm-detail-toolbar>div>strong{display:block;font-size:16px}.fnm-detail-heading small,.fnm-detail-toolbar>div>small{display:block;font-size:10px;opacity:.7;margin-top:4px}.fnm-detail-count{font-size:11px;opacity:.7}.fnm-detail-components{margin-top:9px}.fnm-device-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,205px),1fr));gap:7px;margin-top:9px}.fnm-device-chip{min-width:0;display:flex;align-items:center;gap:7px;text-align:left;border:1px solid ${colors.line}88;border-radius:7px;padding:9px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-device-chip span{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}.fnm-device-chip small{font-size:9px;opacity:.62;white-space:nowrap}.fnm-device-chip i{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:#7b8490}.fnm-device-chip.is-online i{background:#27ae60;box-shadow:0 0 6px #27ae6080}.fnm-device-chip:hover{border-color:${colors.text}}.fnm-detail{margin-top:12px;padding:12px;border:1px solid ${colors.line};border-radius:8px;line-height:1.5;background:${colors.device};font-size:12px}.fnm-detail[hidden]{display:none}.fnm-empty{padding:16px;border:1px dashed ${colors.line};border-radius:9px;opacity:.7;font-size:12px}.fnm-note{font-size:10px;opacity:.58;margin-top:12px}@media(max-width:700px){.fnm-wrap{padding:9px}.fnm-overview-statsbar{grid-template-columns:repeat(2,minmax(0,1fr))}.fnm-overview-grid{grid-template-columns:1fr}.fnm-device-grid{grid-template-columns:1fr}.fnm-device-chip small{display:none}}`;
    this.append(style);
    this.querySelectorAll("[data-open-component]").forEach(el=>el.addEventListener("click",()=>{
      const next=String(el.dataset.openComponent);
      if (this._selectedComponent && this._selectedComponent !== "__unassigned__" && next !== "__unassigned__") {
        this._componentHistory.push(this._selectedComponent);
      } else if (next === "__unassigned__") {
        this._componentHistory = [];
      }
      this._selectedComponent=next;
      this._saveViewState();
      this.render();
    }));
    this.querySelector(".fnm-back")?.addEventListener("click",()=>{
      this._selectedComponent=this._componentHistory.length ? this._componentHistory.pop() : null;
      this._saveViewState();
      this.render();
    });
    this.querySelector(".fnm-fit")?.addEventListener("click",()=>{
      this._componentHistory=[];
      this._selectedComponent=null;
      this._saveViewState();
      this.render();
    });
    this.querySelectorAll(".fnm-device-chip").forEach(el=>{
      el.addEventListener("click",()=>{
        const n=byId.get(String(el.dataset.node)); const box=this.querySelector(".fnm-detail");
        if(!n||!box)return;
        box.hidden=false;
        // Find the existing per-device rate entities by their registered
        // friendly_name. Entity IDs are generated by Home Assistant from the
        // device registry name and must not be guessed from the topology name.
        const deviceFriendlyName = String(n.name || "").trim();
        const rateDefinitions = [
          { suffix: " Datenrate", label: fnmText(this._hass, "ui.lan_data_rate") },
          { suffix: " WLAN 2,4 GHz Datenrate", label: fnmText(this._hass, "ui.wi_fi_2_4_ghz") },
          { suffix: " WLAN 5 GHz Datenrate", label: fnmText(this._hass, "ui.wi_fi_5_ghz") }
        ];
        const normalizeFriendlyName = value => String(value || "").trim().toLocaleLowerCase();
        const rateStates = Object.entries(this._hass?.states || {}).map(([entityId, state]) => ({
          entityId,
          state,
          friendlyName: normalizeFriendlyName(state?.attributes?.friendly_name)
        }));
        const activeRate = rateDefinitions
          .map(definition => {
            const expectedName = normalizeFriendlyName(deviceFriendlyName + definition.suffix);
            const match = rateStates.find(candidate => candidate.friendlyName === expectedName);
            return match ? { ...definition, ...match } : null;
          })
          .filter(Boolean)
          .find(entity => {
            const raw = entity.state?.state;
            if (raw === undefined || raw === null || raw === "" || ["unknown", "unavailable", "none"].includes(String(raw).toLowerCase())) return false;
            const numeric = Number(raw);
            return Number.isFinite(numeric) && numeric > 0;
          });
        const speedValue = activeRate ? Number(activeRate.state.state) : null;
        const speedText = activeRate
          ? `${activeRate.label}: ${speedValue.toLocaleString(this._hass?.locale?.language || "de-DE",{maximumFractionDigits:1})} ${activeRate.state.attributes?.unit_of_measurement || "Mbit/s"}`
          : fnmText(this._hass, "ui.not_available");
        box.innerHTML=`<strong>${esc(n.name||n.mac||n.id)}</strong><br>${fnmText(this._hass, "ui.type")}${esc(kindLabel(n.kind))}<br>IPv4: ${esc(n.ipv4||"-")}<br>MAC: ${esc(n.mac||"-")}<br>${fnmText(this._hass, "ui.status")}${esc(n.status|| (online(n)?"Online":"Offline"))}<br>${fnmText(this._hass, "ui.connected_via")}${esc(n.switch_name||parentNames(n).join(", ")||"-")}<br>Port: ${esc(n.switch_port||"-")}<br>${fnmText(this._hass, "ui.connection_speed")}${esc(speedText)}`;
        // Keep the popup/card viewport at its current position. scrollIntoView()
        // would scroll every ancestor (including the dialog) when details expand.
      });
    });
  }
}



// Additional compact Network Center card. It consumes the same sensor payload
// as the topology map and never calculates or changes network relationships.
class FritzNetworkCenterCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement("fritz-network-center-card-editor");
  }
  static getStubConfig(hass) {
    const entity = Object.keys(hass?.states || {}).find(id => id === "sensor.netzwerk_topologie")
      || Object.keys(hass?.states || {}).find(id => id.startsWith("sensor.") && id.includes("topologie"))
      || "";
    return { entity, title: fnmText(hass,"ui.network_center"), theme: "auto" };
  }
  setConfig(config) {
    if (!config) throw new Error("Missing card configuration");
    this.config = { title: fnmText(this._hass,"ui.network_center"), entity: "Network Insight", refresh_seconds: 60, ...config };
    this._signature = null;
    this._filter = "all";
    this._query = "";
    this._expanded = new Set();
    if (this._mapOpen === undefined) this._mapOpen = false;
  }
  connectedCallback() {
    this._active = true;
    this._load();
    this._refreshTimer = setInterval(() => this._load(), Math.max(15, Number(this.config?.refresh_seconds) || 60) * 1000);
  }
  disconnectedCallback() {
    this._active = false;
    clearInterval(this._refreshTimer);
    document.removeEventListener("keydown", this._mapEscapeHandler);
  }
  set hass(hass) {
    this._hass = hass;
    if (this._active && !this._data && !this._loading) this._load();
    if (this._data && !this._mapOpen) this.render();
    if (this._mapOpen) this.querySelector("fritz-network-insight-topology-dialog")?.setAttribute("data-live", "true");
  }
  async _load() {
    if (!this._hass || !this._active || this._loading) return;
    this._loading = true;
    try {
      const result = await this._hass.callWS({type:"call_service", domain:"fritzbox_network_insight", service:"topology_view", service_data:this.config?.entry_id?{entry_id:this.config.entry_id}:{}, return_response:true});
      const data = result?.response ?? result?.service_response ?? result;
      if (!Array.isArray(data?.nodes) || !Array.isArray(data?.edges)) throw Error(data?.error || "Invalid Network Insight topology");
      const signature = JSON.stringify([data.nodes, data.edges]);
      this._data = data;
      this._error = "";
      if (signature !== this._signature) {
        this._signature = signature;
        this.render();
      }
    } catch(e) {
      this._error = String(e?.message || e);
      this.render();
    } finally { this._loading = false; }
  }
  getCardSize() { return 6; }
  getGridOptions() { return { columns: "full", rows: "auto" }; }
  render() {
    if (!this._hass || !this.config) return;
    // Preserve the live popup DOM while the center card's summary is refreshed.
    const preservedBackdrop = this._mapOpen ? this.querySelector(".fnc-map-backdrop") : null;
    if (preservedBackdrop) preservedBackdrop.remove();
    // Render groups from the existing Network Insight peer/edge observations.
    const nodes = (this._data?.nodes || []).filter(n => n.known_host === true).map(n => {
      const mac = String(n.mac || n.id || "");
      const key = mac.replace(/:/g, "").toLowerCase();
      const state = this._hass.states?.[`sensor.fritzbox_network_insight_${key}_status`];
      const role = String(state?.attributes?.device_type || n.device_type || "").toLowerCase();
      return {...n, id: String(n.id || n.mac).toUpperCase(),
        kind: role === "access_point" ? "repeater" : ["router","switch","repeater"].includes(role) ? role : "device",
        ipv4: state?.attributes?.ip_address || n.ip_address || "",
        active: state?.state === "online" || n.online === true,
        status: state?.state || (n.online === true ? "online" : n.online === false ? "offline" : "unknown")};
    });
    const edges = (this._data?.edges || []).filter(e =>
      (e.kind === "mesh_wlan" && e.evidence === "avm_mesh") ||
      (e.kind === "confirmed_lan" && e.physical_link_confirmed === true)
    ).map(e => ({...e, source: String(e.source || "").toUpperCase(), target: String(e.target || "").toUpperCase()}));
    const groups = nodes.filter(n => ["router","switch","repeater"].includes(n.kind)).map(n => ({
      parent_id: n.id,
      member_ids: edges.filter(e => e.source === n.id).map(e => e.target)
    }));
    const selectedTheme = ["light", "dark"].includes(this.config.theme) ? this.config.theme : "auto";
    this.setAttribute("data-fnc-theme", selectedTheme);
    const design = ["modern-dark", "modern-light", "lcars", "cyber", "custom"].includes(this.config.design)
      ? this.config.design : "modern-dark";
    this.setAttribute("data-fnc-design", design);
    const designPalettes = {
      "modern-dark": { accent: "#03a9f4", heading: "#f1f5f9", background: "#171b22", panel: "#222a35", border: "#394454", text: "#f1f5f9", muted: "#aab6c5", success: "#2eaf62" },
      "modern-light": { accent: "#0284c7", heading: "#1f2937", background: "#ffffff", panel: "#f1f5f9", border: "#d8dee8", text: "#1f2937", muted: "#64748b", success: "#16a34a" },
      "lcars": { accent: "#ffae00", heading: "#ffae00", background: "#101827", panel: "#202b3b", border: "#52657d", text: "#f5f7fa", muted: "#b5c0cf", success: "#27d99a" },
      "cyber": { accent: "#00f0ff", heading: "#00f0ff", background: "#080d18", panel: "#101a2b", border: "#174b68", text: "#e6fbff", muted: "#86a9bd", success: "#31f7a2" },
      "custom": { accent: "#03a9f4", heading: "#f1f5f9", background: "#171b22", panel: "#222a35", border: "#394454", text: "#f1f5f9", muted: "#aab6c5", success: "#2eaf62" }
    };
    const palette = designPalettes[design];
    for (const [key, value] of Object.entries({
      "--fnc-accent": palette.accent,
      "--fnc-heading-color": palette.heading,
      "--fnc-background-color": palette.background,
      "--fnc-panel-color": palette.panel,
      "--fnc-border-color": palette.border,
      "--fnc-text-color": palette.text,
      "--fnc-muted-color": palette.muted,
      "--fnc-success-color": palette.success
    })) this.style.setProperty(key, value);
    // User-configurable heading and overall card background colors override preset defaults.
    const parseSafeColor = value => {
      const candidate = String(value || "").trim();
      return /^(#[0-9a-fA-F]{3,8}|rgba?\\([\\d\\s.,%]+\\)|hsla?\\([\\d\\s.,%deg]+\\)|[a-zA-Z]{1,24})$/.test(candidate)
        ? candidate : "";
    };
    const headingColor = parseSafeColor(this.config.heading_color);
    const backgroundColor = parseSafeColor(this.config.background_color);
    if (headingColor) this.style.setProperty("--fnc-heading-color", headingColor);
    if (backgroundColor) this.style.setProperty("--fnc-background-color", backgroundColor);
    const byId = new Map(nodes.map(n => [String(n.id), n]));
    const esc = v => String(v ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
    const isOnline = n => n.active === true || ["online","connected","active","aktiv","verbunden"].includes(String(n.status || "").toLowerCase());
    const kindLabel = k => ({router:fnmText(this._hass,"ui.router"),switch:fnmText(this._hass,"ui.switch"),repeater:fnmText(this._hass,"ui.repeater"),device:fnmText(this._hass, "ui.end_device")}[k] || fnmText(this._hass, "ui.device"));
    const groupedIds = new Set(groups.flatMap(g => (g.member_ids || []).map(String)));
    // Group parents are already represented by their expandable group cards.
    // Exclude them from "Weitere Geräte" to avoid showing routers/switches twice.
    const groupParentIds = new Set(groups.map(g => String(g.parent_id || "")).filter(Boolean));
    const online = nodes.filter(isOnline).length;
    const offline = nodes.filter(n => n.active === false || ["offline","disconnected","inactive","inaktiv","nicht verbunden"].includes(String(n.status || "").toLowerCase())).length;
    const typeCounts = ["router","switch","repeater"].map(k => ({kind:k,count:nodes.filter(n=>n.kind===k).length})).filter(x=>x.count);
    const nodeRow = n => `<div class="fnc-device"><span class="fnc-dot ${isOnline(n)?"on":""}"></span><span class="fnc-device-main"><strong>${esc(n.name || n.mac || n.id)}</strong><small>${esc(kindLabel(n.kind))}${n.ipv4 ? " · "+esc(n.ipv4):""}${n.switch_port ? " · "+esc(n.switch_port):""}</small></span><span class="fnc-state">${esc(n.status || (n.active === true ? fnmText(this._hass, "ui.online_2") : n.active === false ? fnmText(this._hass, "ui.offline_2") : fnmText(this._hass, "ui.status_unknown")))}</span></div>`;
    const filterNode=n => {
      const q=this._query.trim().toLowerCase();
      const matches=!q || [n.name,n.ipv4,n.mac,n.switch_name,n.switch_port].some(v=>String(v||"").toLowerCase().includes(q));
      const offlineOnly=this._filter==="offline";
      const typeOk=this._filter==="all" || offlineOnly || n.kind===this._filter;
      const offlineOk=!offlineOnly || n.active===false || ["offline","disconnected","inactive","inaktiv","nicht verbunden"].includes(String(n.status||"").toLowerCase());
      return matches && typeOk && offlineOk;
    };
    const groupHtml = groups.map((g,i) => {
      const id=String(g.id || g.parent_id || i), parent=byId.get(String(g.parent_id));
      const allMembers=(g.member_ids||[]).map(x=>byId.get(String(x))).filter(Boolean);
      const members=allMembers.filter(filterNode);
      const parentMatches=parent && filterNode(parent);
      if ((this._query.trim() || this._filter!=="all") && !parentMatches && members.length===0) return "";
      const opened=this._expanded.has(id);
      return `<section class="fnc-group"><button class="fnc-group-head" data-group="${esc(id)}" aria-expanded="${opened}"><span><b>${esc(g.parent_name || parent?.name || g.title || fnmText(this._hass, "ui.network_component"))}</b><small>${members.length} ${this._query.trim() || this._filter!=="all" ? fnmText(this._hass, "ui.matches") : fnmText(this._hass, "ui.directly_connected_devices")}</small></span><span class="fnc-chevron">${opened?"−":"+"}</span></button>${opened?`<div class="fnc-members">${members.map(nodeRow).join("") || `<div class="fnc-empty">${fnmText(this._hass, "ui.no_matching_devices")}</div>`}</div>`:""}</section>`;
    }).join("");
    const standalone=nodes.filter(n=>!groupedIds.has(String(n.id)) && !groupParentIds.has(String(n.id)));
    const visibleStandalone=standalone.filter(filterNode);
    this.innerHTML=`<ha-card header="${esc(this.config.title)}"><div class="fnc-root">
      <div class="fnc-summary">
        <div class="fnc-stat"><strong>${nodes.length}</strong><span>${fnmText(this._hass, "ui.total_devices")}</span></div>
        <div class="fnc-stat"><strong>${edges.length}</strong><span>${fnmText(this._hass, "ui.connections")}</span></div>
        <div class="fnc-stat"><strong>${online}</strong><span>${fnmText(this._hass, "ui.online_2")}</span></div>
        <div class="fnc-stat"><strong>${offline}</strong><span>${fnmText(this._hass, "ui.offline_2")}</span></div>
      </div>
      <div class="fnc-types">${typeCounts.map(x=>`<span>${esc(kindLabel(x.kind))}: <b>${x.count}</b></span>`).join("")}</div>
      <div class="fnc-actions"><button class="fnc-open-map" type="button">⌁ ${fnmText(this._hass, "ui.open_network_map")}</button></div>
      <div class="fnc-tools"><input class="fnc-search" type="search" placeholder="${fnmText(this._hass, "ui.search_device_ip_or_mac")}" value="${esc(this._query)}" aria-label="${fnmText(this._hass, "ui.search_devices")}"><select class="fnc-filter" aria-label="${fnmText(this._hass, "ui.filter_devices")}"><option value="all">${fnmText(this._hass, "ui.all_devices")}</option><option value="router">Router</option><option value="switch">${fnmText(this._hass, "ui.switches")}</option><option value="repeater">Repeater</option><option value="device">${fnmText(this._hass, "ui.end_devices")}</option><option value="offline">${fnmText(this._hass, "ui.offline_2")}</option></select></div>
      <div class="fnc-section-title">${fnmText(this._hass, "ui.network_components_and_directly_connected_devices")}</div>
      <div class="fnc-groups">${groupHtml || `<div class="fnc-empty">${this._query.trim() || this._filter!=="all" ? fnmText(this._hass, "ui.no_matching_network_components_or_devices_found") : fnmText(this._hass, "ui.no_device_groups_available")}</div>`}</div>
      <div class="fnc-section-title">${fnmText(this._hass, "ui.other_devices")}</div>
      <div class="fnc-standalone">${visibleStandalone.map(nodeRow).join("") || `<div class="fnc-empty">${fnmText(this._hass, "ui.no_matching_devices")}</div>`}</div>
      <div class="fnc-foot">${fnmText(this._hass, "ui.data_source")}${esc(this.config.entity)} · ${fnmText(this._hass, "ui.relationships_are_taken_exclusively_from_sensor_attributes")}</div>
      <div class="fnc-map-backdrop" hidden><section class="fnc-map-dialog" role="dialog" aria-modal="true" aria-label="${fnmText(this._hass, "ui.network_map")}"><header class="fnc-map-dialog-head"><strong>${fnmText(this._hass, "ui.network_map")}</strong><button class="fnc-close-map" type="button" aria-label="${fnmText(this._hass, "ui.close_popup")}">×</button></header><div class="fnc-map-dialog-body"><div class="fnc-map-mount"></div></div></section></div>
    </div></ha-card>`;
    const style=document.createElement("style");
    style.textContent=`fritz-network-center-card{display:block;width:100%;max-width:100%;min-width:0;box-sizing:border-box}fritz-network-center-card[data-fnc-theme="dark"]{--primary-text-color:#f1f5f9;--secondary-text-color:#aab6c5;--card-background-color:#171b22;--ha-card-background:#171b22;--secondary-background-color:#222a35;--input-fill-color:#222a35;--divider-color:#394454;--primary-color:#03a9f4;--disabled-text-color:#77808c;--text-primary-color:#ffffff;--success-color:#2eaf62}fritz-network-center-card[data-fnc-theme="light"]{--primary-text-color:#1f2937;--secondary-text-color:#64748b;--card-background-color:#ffffff;--ha-card-background:#ffffff;--secondary-background-color:#f1f5f9;--input-fill-color:#f8fafc;--divider-color:#d8dee8;--primary-color:#0284c7;--disabled-text-color:#9ca3af;--text-primary-color:#ffffff;--success-color:#16a34a}fritz-network-center-card > ha-card{width:100%;max-width:100%;box-sizing:border-box;background:var(--fnc-background-color,var(--fnc-background-color,var(--ha-card-background,var(--card-background-color))));--ha-card-background:var(--fnc-background-color,var(--card-background-color));--ha-card-header-color:var(--fnc-heading-color,var(--fnc-text-color,var(--primary-text-color)))}.fnc-root{padding:14px;box-sizing:border-box;color:var(--fnc-text-color,var(--primary-text-color));background:var(--fnc-background-color,transparent);border-radius:var(--ha-card-border-radius,12px)}.fnc-summary{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.fnc-stat{background:var(--fnc-background-color,var(--ha-card-background,var(--card-background-color)));border:1px solid var(--fnc-border-color,var(--divider-color));border-radius:10px;padding:12px;min-width:0}.fnc-stat strong{display:block;font-size:25px;line-height:1.2;color:var(--fnc-accent,var(--primary-color))}.fnc-stat span,.fnc-types,.fnc-device small,.fnc-group-head small,.fnc-foot{font-size:12px;color:var(--fnc-muted-color,var(--secondary-text-color))}.fnc-types{display:flex;gap:16px;flex-wrap:wrap;padding:12px 2px}.fnc-tools{display:flex;gap:9px;margin:4px 0 16px}.fnc-search,.fnc-filter{font:inherit;color:var(--fnc-text-color,var(--primary-text-color));background:var(--fnc-panel-color,var(--input-fill-color,var(--secondary-background-color)));border:1px solid var(--fnc-border-color,var(--divider-color));border-radius:8px;padding:10px;min-width:0}.fnc-search{flex:1}.fnc-section-title{font-size:13px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--fnc-heading-color,var(--fnc-muted-color,var(--secondary-text-color)));margin:14px 0 8px}.fnc-groups{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));gap:9px}.fnc-group{border:1px solid var(--fnc-border-color,var(--divider-color));border-radius:10px;overflow:hidden;min-width:0}.fnc-group-head{display:flex;align-items:center;justify-content:space-between;width:100%;padding:13px;background:var(--fnc-panel-color,var(--secondary-background-color));color:var(--fnc-text-color,var(--primary-text-color));border:0;text-align:left;cursor:pointer;font:inherit}.fnc-group-head b,.fnc-group-head small{display:block}.fnc-group-head small{margin-top:4px}.fnc-chevron{font-size:22px;color:var(--fnc-accent,var(--primary-color));padding-left:8px}.fnc-members{padding:4px 12px}.fnc-device{display:flex;align-items:center;gap:9px;padding:9px 2px;border-bottom:1px solid var(--fnc-border-color,var(--divider-color));min-width:0}.fnc-device:last-child{border-bottom:0}.fnc-dot{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:var(--disabled-text-color)}.fnc-dot.on{background:var(--fnc-success-color,var(--success-color,#2eaf62))}.fnc-device-main{display:block;min-width:0;flex:1}.fnc-device-main strong,.fnc-device-main small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fnc-device-main strong{font-size:13px}.fnc-device small{margin-top:3px}.fnc-state{font-size:11px;color:var(--fnc-muted-color,var(--secondary-text-color));white-space:nowrap}.fnc-standalone{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:8px;border:0;border-radius:0;padding:0}.fnc-standalone .fnc-device{box-sizing:border-box;min-width:0;min-height:54px;padding:9px 11px;gap:9px;border:1px solid var(--fnc-border-color,var(--divider-color));border-radius:9px;background:var(--fnc-panel-color,var(--secondary-background-color));align-items:center}.fnc-standalone .fnc-device-main strong{font-size:12px;line-height:1.25}.fnc-standalone .fnc-device small{font-size:10px;line-height:1.2;margin-top:3px}.fnc-standalone .fnc-state{display:none}.fnc-standalone .fnc-dot{width:8px;height:8px;flex:0 0 8px}.fnc-empty{padding:14px;color:var(--fnc-muted-color,var(--secondary-text-color));font-size:13px}.fnc-foot{margin-top:14px}.fnc-actions{display:flex;justify-content:flex-end;margin:0 0 12px}.fnc-open-map{border:1px solid var(--fnc-accent,var(--primary-color));border-radius:8px;padding:9px 14px;background:var(--fnc-accent,var(--primary-color));color:var(--text-primary-color,#fff);font:inherit;font-weight:600;cursor:pointer}.fnc-map-backdrop{position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:3vh 3vw;box-sizing:border-box}.fnc-map-backdrop[hidden]{display:none}.fnc-map-dialog{display:flex;flex-direction:column;width:min(94vw,1800px);height:90vh;max-height:90vh;background:var(--card-background-color,#1c1c1c);color:var(--fnc-text-color,var(--primary-text-color));border:1px solid var(--fnc-border-color,var(--divider-color));border-radius:14px;box-shadow:0 18px 60px rgba(0,0,0,.5);overflow:hidden}.fnc-map-dialog-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;border-bottom:1px solid var(--fnc-border-color,var(--divider-color));flex:0 0 auto}.fnc-map-dialog-head strong{font-size:16px}.fnc-close-map{border:0;background:transparent;color:var(--fnc-text-color,var(--primary-text-color));font-size:30px;line-height:1;cursor:pointer;padding:0 5px}.fnc-map-dialog-body{flex:1;min-height:0;overflow-y:auto;overflow-x:hidden;scrollbar-width:none;-ms-overflow-style:none;padding:10px;box-sizing:border-box;overscroll-behavior:contain}.fnc-map-dialog-body::-webkit-scrollbar{display:none;width:0;height:0}.fnc-map-mount{display:block;width:100%;min-height:0}.fnc-map-mount fritz-network-insight-topology-dialog{display:block;width:100%;height:auto;min-height:calc(90vh - 125px);--ha-card-border-radius:10px}.fnc-map-mount .fnm-wrap{min-height:calc(90vh - 125px);height:auto;overflow:visible}@media(max-width:600px){.fnc-map-dialog{width:98vw;height:94vh;max-height:94vh}.fnc-map-dialog-body{padding:5px}.fnc-map-mount fritz-network-insight-topology-dialog{min-height:calc(94vh - 120px)}.fnc-map-mount .fnm-wrap{min-height:calc(94vh - 120px)}}@media(max-width:600px){.fnc-summary{grid-template-columns:repeat(2,minmax(0,1fr))}.fnc-tools{flex-direction:column}.fnc-filter{width:100%}}`;
    this.append(style);
    const search=this.querySelector(".fnc-search"), select=this.querySelector(".fnc-filter");
    search.addEventListener("input",ev=>{
      this._query=ev.target.value;
      const selectionStart=ev.target.selectionStart ?? this._query.length;
      const selectionEnd=ev.target.selectionEnd ?? selectionStart;
      const selectionDirection=ev.target.selectionDirection || "none";
      this.render();
      requestAnimationFrame(()=>{
        const el=this.querySelector(".fnc-search");
        if(!el) return;
        el.focus({preventScroll:true});
        el.setSelectionRange(selectionStart,selectionEnd,selectionDirection);
      });
    });
    select.value=this._filter;
    select.addEventListener("change",ev=>{this._filter=ev.target.value;this.render();});
    this.querySelectorAll(".fnc-group-head").forEach(btn=>btn.addEventListener("click",()=>{const id=btn.dataset.group;this._expanded.has(id)?this._expanded.delete(id):this._expanded.add(id);this.render();}));
    const generatedBackdrop=this.querySelector(".fnc-map-backdrop");
    const backdrop=preservedBackdrop || generatedBackdrop;
    if (preservedBackdrop && generatedBackdrop) generatedBackdrop.replaceWith(preservedBackdrop);
    const closeMap=()=>{this._mapOpen=false;backdrop.hidden=true;};
    this.querySelector(".fnc-open-map").addEventListener("click",()=>{
      this._mapOpen=true;
      this._renderPopupMap(backdrop);
      backdrop.hidden=false;
    });
    if (!backdrop._fncEventsBound) {
      backdrop.querySelector(".fnc-close-map").addEventListener("click",closeMap);
      backdrop.addEventListener("click",ev=>{if(ev.target===backdrop)closeMap();});
      backdrop._fncEventsBound=true;
    }
    if (!this._mapEscapeHandler) {
      this._mapEscapeHandler=ev=>{
        if(ev.key==="Escape" && this._mapOpen){
          this._mapOpen=false;
          const active=this.querySelector(".fnc-map-backdrop");
          if(active) active.hidden=true;
        }
      };
      document.addEventListener("keydown",this._mapEscapeHandler);
    }
    // Update the existing map instance; do not replace the open dialog.
    if (this._mapOpen) {
      this._renderPopupMap(backdrop);
      backdrop.hidden=false;
    }
  }
  _renderPopupMap(backdrop) {
    const mount=backdrop?.querySelector(".fnc-map-mount");
    if (!mount) return;
    let mapCard=mount.querySelector("fritz-network-insight-topology-dialog");
    if (!mapCard) {
      mapCard=document.createElement("fritz-network-insight-topology-dialog");
      mapCard.setConfig({
      entry_id:this.config.entry_id,
      title:"Netzwerkübersicht",
      theme:this.config.theme || "auto",
      height:"calc(90vh - 125px)",
      min_height:"400px",
      popup_mode:true,
      animate_connections: this.config.animate_connections,
      colors: this.config.theme === "light"
        ? { background: "#f8fafc", text: "#1f2937", line: "#64748b", router: "#2563eb", switch: "#0f766e", repeater: "#7c3aed", device: "#e2e8f0" }
        : { background: "#111827", text: "#f3f4f6", line: "#64748b", router: "#2563eb", switch: "#0f766e", repeater: "#7c3aed", device: "#263445" },
      ...(this.config.map_options || {})
      });
      mount.appendChild(mapCard);
    }
    // Refresh data on the same map-card instance, preserving its UI state.
    mapCard.hass=this._hass;
    mapCard.topology=this._data;
  }
}

if (!customElements.get("fritz-network-insight-map-card")) customElements.define("fritz-network-insight-map-card", FritzNetworkCenterCard);
window.customCards = window.customCards || [];
if (!window.customCards.some(c => c.type === "fritz-network-insight-map-card")) window.customCards.push({type:"fritz-network-insight-map-card",name:"FRITZ!Box Network Insight Map",description:"Network Center with original v0.7.29 map layout"});

class FritzNetworkMapCardEditor extends HTMLElement { setConfig(config){this._config=config;} set hass(hass){this._hass=hass;} }
if (!customElements.get("fritz-network-map-card-editor")) customElements.define("fritz-network-map-card-editor", FritzNetworkMapCardEditor);
class FritzNetworkCenterCardEditor extends HTMLElement { setConfig(config){this._config=config;} set hass(hass){this._hass=hass;} }
if (!customElements.get("fritz-network-center-card-editor")) customElements.define("fritz-network-center-card-editor", FritzNetworkCenterCardEditor);

/* All user-facing frontend text is loaded from the language files. */
const deFrontend = {
  "ui.please_select_a_network_topology_entity": "Bitte eine Netzwerk-Topologie-Entität angeben.",
  "ui.end_device": "Endgerät",
  "ui.device": "Gerät",
  "ui.direct_devices_components": "direkte Geräte/Komponenten",
  "ui.offline": "offline",
  "ui.unassigned_devices": "Nicht zugeordnete Geräte",
  "ui.component_details": "Komponentendetails",
  "ui.overview": "Gesamtübersicht",
  "ui.devices_without_a_recognized_direct_connection": "Geräte ohne erkannte direkte Zuordnung",
  "ui.no_unassigned_devices": "Keine nicht zugeordneten Geräte.",
  "ui.parent_component": "Übergeordnete Komponente",
  "ui.end_devices": "Endgeräte",
  "ui.components": "Komponenten",
  "ui.online": "online",
  "ui.parent_level": "Übergeordnete Ebene",
  "ui.parent": "Übergeordnet: ",
  "ui.no_recognized_parent_component": "Keine erkannte übergeordnete Komponente",
  "ui.direct_connections": "direkte Verbindungen",
  "ui.network_hierarchy_parent_component_selection_and_child_component": "Netzwerkhierarchie – übergeordnete Komponente, Auswahl und Unterkomponenten",
  "ui.connected_devices": "Angeschlossene Geräte",
  "ui.no_directly_connected_end_devices": "Keine direkt angeschlossenen Endgeräte.",
  "ui.total_devices": "Geräte gesamt",
  "ui.network_components": "Netzwerkkomponenten",
  "ui.online_2": "Online",
  "ui.offline_2": "Offline",
  "ui.network_topology_select_a_node_for_details": "Grafische Netzwerktopologie – Knoten auswählen für Details",
  "ui.no_network_components_detected": "Keine Netzwerkkomponenten erkannt.",
  "ui.other_unassigned_devices": "Weitere / nicht zugeordnete Geräte",
  "ui.show_devices": "Geräte anzeigen →",
  "ui.network_details": "Netzwerkdetails",
  "ui.network_overview": "Netzwerk-Gesamtübersicht",
  "ui.data_source": "Datenquelle: ",
  "ui.overview_2": "Zur Übersicht",
  "ui.this_view_uses_only_the_direct_connections_reported_by_the_topol": "Die Anzeige verwendet ausschließlich die vom Topologie-Sensor gelieferten Direktverbindungen. Es werden keine zusätzlichen Verbindungen abgeleitet.",
  "ui.lan_data_rate": "LAN / Datenrate",
  "ui.wi_fi_2_4_ghz": "WLAN 2,4 GHz",
  "ui.wi_fi_5_ghz": "WLAN 5 GHz",
  "ui.not_available": "Nicht verfügbar",
  "ui.type": "Typ: ",
  "ui.status": "Status: ",
  "ui.connected_via": "Verbunden über: ",
  "ui.connection_speed": "Verbindungsgeschwindigkeit: ",
  "ui.entity": "Entität",
  "ui.theme": "Darstellung",
  "ui.design": "Design",
  "ui.animate_connection_lines": "Verbindungslinien animieren",
  "ui.the_topology_uses_the_same_device_and_connection_data_as_the_net": "Die Topologie verwendet dieselbe Geräte- und Verbindungsdatenbasis wie das Network Center.",
  "ui.automatic": "Automatisch",
  "ui.light": "Hell",
  "ui.dark": "Dunkel",
  "ui.status_unknown": "Status unbekannt",
  "ui.network_component": "Netzwerkkomponente",
  "ui.matches": "Treffer",
  "ui.directly_connected_devices": "direkt verbundene Geräte",
  "ui.no_matching_devices": "Keine passenden Geräte.",
  "ui.connections": "Verbindungen",
  "ui.open_network_map": "Netzwerk-Map öffnen",
  "ui.search_device_ip_or_mac": "Gerät, IP oder MAC suchen …",
  "ui.search_devices": "Geräte suchen",
  "ui.filter_devices": "Geräte filtern",
  "ui.all_devices": "Alle Geräte",
  "ui.switches": "Switches",
  "ui.network_components_and_directly_connected_devices": "Netzwerkkomponenten und direkt verbundene Geräte",
  "ui.no_matching_network_components_or_devices_found": "Keine passenden Netzwerkkomponenten oder Geräte gefunden.",
  "ui.no_device_groups_available": "Keine Gerätegruppen vorhanden.",
  "ui.other_devices": "Weitere Geräte",
  "ui.relationships_are_taken_exclusively_from_sensor_attributes": "Beziehungen werden ausschließlich aus den Sensorattributen übernommen.",
  "ui.network_map": "Netzwerk-Map",
  "ui.close_popup": "Popup schließen",
  "ui.this_card_uses_the_same_topology_sensor_as_the_network_map_the_p": "Die Karte verwendet denselben Topologie-Sensor wie die Netzwerk-Map. Die Popup-Map benötigt keine zusätzliche Entität.",
  "ui.title": "Titel",
  "ui.heading_color": "Überschriftenfarbe",
  "ui.e_g_00bfff_blank_design_color": "z. B. #00BFFF (leer = Designfarbe)",
  "ui.background_color": "Hintergrundfarbe",
  "ui.e_g_111827_blank_design_color": "z. B. #111827 (leer = Designfarbe)",
  "ui.router": "Router",
  "ui.switch": "Switch",
  "ui.repeater": "Repeater",
  "ui.modern_dark": "Modern Dark",
  "ui.modern_light": "Modern Light",
  "ui.lcars": "LCARS",
  "ui.cyber": "Cyber",
  "ui.custom": "Benutzerdefiniert",
  "ui.network_center": "Network Center",
  "ui.network_map_name": "FRITZ!Box Network Map",
  "ui.network_map_description": "Renderer für sensorbasierte Netzwerkverbindungen",
  "ui.network_center_name": "FRITZ!Box Network Center",
  "ui.network_center_description": "Kompakte, filterbare Geräteübersicht auf Basis derselben Netzwerktopologie"
};
const enFrontend = {
  "ui.please_select_a_network_topology_entity": "Please select a network topology entity.",
  "ui.end_device": "End device",
  "ui.device": "Device",
  "ui.direct_devices_components": "direct devices/components",
  "ui.offline": "offline",
  "ui.unassigned_devices": "Unassigned devices",
  "ui.component_details": "Component details",
  "ui.overview": "Overview",
  "ui.devices_without_a_recognized_direct_connection": "Devices without a recognized direct connection",
  "ui.no_unassigned_devices": "No unassigned devices.",
  "ui.parent_component": "Parent component",
  "ui.end_devices": "End devices",
  "ui.components": "components",
  "ui.online": "online",
  "ui.parent_level": "Parent level",
  "ui.parent": "Parent: ",
  "ui.no_recognized_parent_component": "No recognized parent component",
  "ui.direct_connections": "direct connections",
  "ui.network_hierarchy_parent_component_selection_and_child_component": "Network hierarchy – parent component, selection and child components",
  "ui.connected_devices": "Connected devices",
  "ui.no_directly_connected_end_devices": "No directly connected end devices.",
  "ui.total_devices": "Total devices",
  "ui.network_components": "Network components",
  "ui.online_2": "Online",
  "ui.offline_2": "Offline",
  "ui.network_topology_select_a_node_for_details": "Network topology – select a node for details",
  "ui.no_network_components_detected": "No network components detected.",
  "ui.other_unassigned_devices": "Other / unassigned devices",
  "ui.show_devices": "Show devices →",
  "ui.network_details": "Network details",
  "ui.network_overview": "Network overview",
  "ui.data_source": "Data source: ",
  "ui.overview_2": "Overview",
  "ui.this_view_uses_only_the_direct_connections_reported_by_the_topol": "This view uses only the direct connections reported by the topology sensor. No additional connections are inferred.",
  "ui.lan_data_rate": "LAN / data rate",
  "ui.wi_fi_2_4_ghz": "Wi-Fi 2.4 GHz",
  "ui.wi_fi_5_ghz": "Wi-Fi 5 GHz",
  "ui.not_available": "Not available",
  "ui.type": "Type: ",
  "ui.status": "Status: ",
  "ui.connected_via": "Connected via: ",
  "ui.connection_speed": "Connection speed: ",
  "ui.entity": "Entity",
  "ui.theme": "Theme",
  "ui.design": "Design",
  "ui.animate_connection_lines": "Animate connection lines",
  "ui.the_topology_uses_the_same_device_and_connection_data_as_the_net": "The topology uses the same device and connection data as the Network Center.",
  "ui.automatic": "Automatic",
  "ui.light": "Light",
  "ui.dark": "Dark",
  "ui.status_unknown": "Status unknown",
  "ui.network_component": "Network component",
  "ui.matches": "matches",
  "ui.directly_connected_devices": "directly connected devices",
  "ui.no_matching_devices": "No matching devices.",
  "ui.connections": "Connections",
  "ui.open_network_map": "Open network map",
  "ui.search_device_ip_or_mac": "Search device, IP or MAC …",
  "ui.search_devices": "Search devices",
  "ui.filter_devices": "Filter devices",
  "ui.all_devices": "All devices",
  "ui.switches": "Switches",
  "ui.network_components_and_directly_connected_devices": "Network components and directly connected devices",
  "ui.no_matching_network_components_or_devices_found": "No matching network components or devices found.",
  "ui.no_device_groups_available": "No device groups available.",
  "ui.other_devices": "Other devices",
  "ui.relationships_are_taken_exclusively_from_sensor_attributes": "Relationships are taken exclusively from sensor attributes.",
  "ui.network_map": "Network map",
  "ui.close_popup": "Close popup",
  "ui.this_card_uses_the_same_topology_sensor_as_the_network_map_the_p": "This card uses the same topology sensor as the Network Map. The popup map does not require an additional entity.",
  "ui.title": "Title",
  "ui.heading_color": "Heading color",
  "ui.e_g_00bfff_blank_design_color": "e.g. #00BFFF (blank = design color)",
  "ui.background_color": "Background color",
  "ui.e_g_111827_blank_design_color": "e.g. #111827 (blank = design color)",
  "ui.router": "Router",
  "ui.switch": "Switch",
  "ui.repeater": "Repeater",
  "ui.modern_dark": "Modern Dark",
  "ui.modern_light": "Modern Light",
  "ui.lcars": "LCARS",
  "ui.cyber": "Cyber",
  "ui.custom": "Custom",
  "ui.network_center": "Network Center",
  "ui.network_map_name": "FRITZ!Box Network Map",
  "ui.network_map_description": "Renderer for sensor-based network connections",
  "ui.network_center_name": "FRITZ!Box Network Center",
  "ui.network_center_description": "Compact, filterable device overview based on the same network topology"
};

const FNM_TRANSLATIONS = { de: deFrontend, en: enFrontend };
const fnmText = (hass, key) => {
  const language = String(hass?.locale?.language || hass?.language || document.documentElement.lang || "en").toLowerCase();
  const dictionary = language.startsWith("de") ? FNM_TRANSLATIONS.de : FNM_TRANSLATIONS.en;
  return dictionary[key] ?? FNM_TRANSLATIONS.en[key] ?? key;
};

/* FRITZ!Box Network Map Card - renderer only */
class FritzNetworkInsightTopologyDialog extends HTMLElement {
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
    if (!config) throw new Error("Map configuration missing");
    this.config = { colors: {}, ...config };
    this._signature = null;
    if (this._selectedComponent === undefined) this._selectedComponent = null;
    if (!Array.isArray(this._componentHistory)) this._componentHistory = [];
    this._restoreViewState();
  }
  _viewStorageKey() {
    // Each browser/device keeps its own navigation state.
    return `fritz-network-insight:view:${this.config?.entry_id || "default"}`;
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
  set hass(hass) { this._hass=hass; if(this.config && this._topology) this.render(); }
  set topology(data) {
    if (!data || !Array.isArray(data.nodes) || !Array.isArray(data.edges)) return;
    const signature=JSON.stringify(data);
    if(signature===this._signature && this.querySelector('.fnm-wrap')) return;
    this._topology=data; this._signature=signature;
    if(this._hass && this.config) this.render();
  }
  _kind(n) {
    const t=String(n.device_type||n.kind||'').toLowerCase();
    return t==='router'?'router':t==='switch'?'switch':t==='repeater'||t==='access_point'?'repeater':'device';
  }
  _online(n) {
    if(typeof n.online==='boolean')return n.online;
    if(typeof n.is_online==='boolean')return n.is_online;
    const key=String(n.mac||n.id||'').replace(/:/g,'').toLowerCase();
    return ['online','on','connected','verbunden'].includes(String(this._hass?.states?.['sensor.fritzbox_network_insight_'+key+'_status']?.state||'').toLowerCase());
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
    // Directly consume Network Insight topology_view; only presentation fields are read here.
    const nodes=(this._topology?.nodes||[]).filter(n=>n.known_host===true).map(n=>{
      const id=String(n.mac||n.id||'').toUpperCase();
      const key=id.replace(/:/g,'').toLowerCase();
      const a=this._hass?.states?.['sensor.fritzbox_network_insight_'+key+'_status']?.attributes||{};
      return {...n,id,mac:n.mac||id,kind:this._kind({...n,device_type:a.device_type||n.device_type}),name:a.dns_name||n.name,ipv4:a.ip_address||n.ip_address,active:this._online(n),status:this._online(n)?'online':'offline'};
    });
    const byMac=new Set(nodes.map(n=>String(n.id)));
    const edges=(this._topology?.edges||[]).filter(e=>{
      if(!byMac.has(String(e.source).toUpperCase())||!byMac.has(String(e.target).toUpperCase()))return false;
      return (e.kind==='mesh_wlan'&&e.evidence==='avm_mesh') || (e.kind==='confirmed_lan'&&e.physical_link_confirmed===true);
    }).map(e=>({source_id:String(e.source).toUpperCase(),target_id:String(e.target).toUpperCase()}));
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
      const a=String(e.source_id || ""), b=String(e.target_id || "");
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
    edges.forEach(e=>{if(e.target_id)assigned.add(String(e.target_id));});
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
        const a=String(e.source_id||""), b=String(e.target_id||"");
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
      <div class="fnm-toolbar"><div class="fnm-summary">${this._selectedComponent ? fnmText(this._hass, "ui.network_details") : fnmText(this._hass, "ui.network_overview")} <span>·</span> ${fnmText(this._hass, "ui.data_source")}${"Network Insight"}</div><div class="fnm-controls"><button class="fnm-fit">${this._selectedComponent?fnmText(this._hass, "ui.overview_2"):fnmText(this._hass, "ui.overview")}</button></div></div>
      <div class="fnm-overview">${content}</div>
      <div class="fnm-detail" hidden></div>
      <div class="fnm-note">${fnmText(this._hass, "ui.this_view_uses_only_the_direct_connections_reported_by_the_topol")}</div>
    </div></ha-card>`;
    const style=document.createElement("style");
    style.textContent=`:host{display:block;width:100%;min-width:0;max-width:100%;box-sizing:border-box}fritz-network-insight-topology-dialog > ha-card{width:100%;max-width:100%;box-sizing:border-box}.fnm-wrap{background:${colors.background};color:${colors.text};padding:0 14px 14px;box-sizing:border-box}.fnm-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:14px}.fnm-summary{font-size:12px;opacity:.76}.fnm-controls button,.fnm-back{border:1px solid ${colors.line};border-radius:7px;padding:7px 11px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-overview{display:flex;flex-direction:column;gap:13px}.fnm-overview-statsbar{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}.fnm-overview-statsbar>div{border:1px solid ${colors.line};border-radius:9px;padding:11px;background:${colors.device};display:flex;flex-direction:column;gap:3px}.fnm-overview-statsbar b{font-size:23px;color:${colors.text}}.fnm-overview-statsbar span{font-size:10px;opacity:.7}.fnm-section-heading{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.72;margin:3px 0 -3px}.fnm-overview-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,260px),1fr));gap:10px;align-items:stretch}.fnm-overview-card{position:relative;display:grid;grid-template-columns:38px minmax(0,1fr) 20px;gap:8px;align-items:center;text-align:left;min-width:0;padding:12px;border:1px solid ${colors.line};border-top:3px solid ${colors.switch};border-radius:10px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-overview-card.repeater{border-top-color:${colors.repeater}}.fnm-overview-card.router{border-top-color:${colors.router}}.fnm-overview-card:hover,.fnm-unassigned-entry:hover{filter:brightness(1.12);border-color:${colors.text}}.fnm-overview-icon{width:34px;height:34px;border-radius:9px;background:${colors.background};display:grid;place-items:center;font-size:20px}.fnm-overview-main{min-width:0}.fnm-overview-main strong{display:block;font-size:14px;overflow-wrap:anywhere}.fnm-overview-main small{display:block;font-size:10px;opacity:.7;margin-top:4px}.fnm-overview-arrow{font-size:25px;opacity:.7;text-align:center}.fnm-overview-stats{grid-column:2/-1;display:flex;align-items:center;gap:7px;flex-wrap:wrap;font-size:10px;opacity:.78}.fnm-overview-stats b{font-size:18px;color:${colors.text}}.fnm-status-dot{width:7px;height:7px;border-radius:50%;background:#27ae60;display:inline-block}.fnm-overview-nested{grid-column:2/-1;font-size:10px;opacity:.65;border-top:1px solid ${colors.line}66;padding-top:7px}.fnm-graph-scroll{width:100%;overflow-x:auto;overflow-y:hidden;scrollbar-width:none;-ms-overflow-style:none;border:1px solid ${colors.line}88;border-radius:10px;background:linear-gradient(180deg,${colors.background},${colors.device}55);padding:8px;box-sizing:border-box}.fnm-graph-scroll::-webkit-scrollbar{display:none;width:0;height:0}.fnm-graph-canvas{position:relative;margin:0 auto;min-width:100%;}.fnm-graph-lines{position:absolute;inset:0;overflow:visible;pointer-events:none}.fnm-graph-lines path{fill:none;stroke:${colors.line};stroke-width:2;stroke-linecap:round;stroke-linejoin:round;opacity:.78}.fnm-graph-lines .fnm-graph-pulse{display:none}.fnm-graph-lines.is-animated .fnm-graph-pulse{display:block;fill:none;stroke:#39e8ff;stroke-width:3;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:9 25;stroke-dashoffset:0;opacity:.98;filter:none;animation:fnm-connection-flow 3.2s linear infinite}@keyframes fnm-connection-flow{to{stroke-dashoffset:-40}}@media(prefers-reduced-motion:reduce){.fnm-graph-lines.is-animated .fnm-graph-pulse{animation:none;stroke-dasharray:9 25;opacity:.45}}.fnm-graph-node{position:absolute;z-index:2;display:grid;grid-template-columns:34px minmax(0,1fr) 15px;gap:7px;align-items:center;text-align:left;padding:9px;border:1px solid ${colors.line};border-top:3px solid ${colors.switch};border-radius:10px;background:${colors.device};color:${colors.text};cursor:pointer;box-sizing:border-box}.fnm-graph-node.router{border-top-color:${colors.router}}.fnm-graph-node.repeater{border-top-color:${colors.repeater}}.fnm-graph-node:hover{filter:brightness(1.14);border-color:${colors.text}}.fnm-graph-root{border-width:1px;border-top-width:4px}.fnm-graph-selected{border:2px solid ${colors.text};box-shadow:0 0 0 2px ${colors.line}55}.fnm-graph-icon{width:32px;height:32px;border-radius:8px;background:${colors.background};display:grid;place-items:center;font-size:19px}.fnm-graph-label{min-width:0}.fnm-graph-label strong{display:block;font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.fnm-graph-label small{display:block;font-size:9px;opacity:.7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:3px}.fnm-graph-label em{display:block;font-size:9px;font-style:normal;opacity:.75;margin-top:5px}.fnm-graph-arrow{font-size:22px;opacity:.7}.fnm-graph-status{grid-column:2/-1;display:flex;align-items:center;gap:6px;font-size:9px;opacity:.78}.fnm-graph-status i,.fnm-graph-dots i{display:inline-block;width:7px;height:7px;border-radius:50%;background:#89919d}.fnm-graph-status i{background:#27ae60}.fnm-graph-device-cluster{position:absolute;z-index:1;min-height:54px;box-sizing:border-box;border:1px dashed ${colors.line};border-radius:8px;padding:6px 8px;background:${colors.background};display:flex;flex-direction:column;gap:5px}.fnm-graph-cluster-title{font-size:8px;letter-spacing:.06em;opacity:.65}.fnm-graph-dots{display:flex;align-items:center;gap:5px;flex-wrap:wrap}.fnm-graph-dots i.on{background:#27ae60;box-shadow:0 0 5px #27ae6080}.fnm-graph-dots i.off{background:#d97706}.fnm-graph-dots b{font-size:9px;opacity:.75}.fnm-graph-device-cluster small{font-size:9px;opacity:.65}.fnm-graph-root-devices{position:absolute;z-index:2;display:flex;align-items:center;gap:7px;padding:5px 8px;border:1px dashed ${colors.line};border-radius:7px;background:${colors.background};font-size:9px;white-space:nowrap}.fnm-unassigned-entry{appearance:none!important;width:100%;box-sizing:border-box;background:${colors.background}!important;color:${colors.text}!important;border:1px dashed ${colors.line}!important;display:flex;align-items:center;gap:12px;text-align:left;border:1px dashed ${colors.line};border-radius:9px;padding:12px;background:${colors.background};color:${colors.text};cursor:pointer}.fnm-unassigned-entry b{font-size:18px}.fnm-unassigned-entry span:last-child{margin-left:auto;font-size:11px;opacity:.7}.fnm-detail-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:3px 0 12px;border-bottom:1px solid ${colors.line}66}.fnm-detail-heading{min-width:0;flex:1}.fnm-detail-heading strong,.fnm-detail-toolbar>div>strong{display:block;font-size:16px}.fnm-detail-heading small,.fnm-detail-toolbar>div>small{display:block;font-size:10px;opacity:.7;margin-top:4px}.fnm-detail-count{font-size:11px;opacity:.7}.fnm-detail-components{margin-top:9px}.fnm-device-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,205px),1fr));gap:7px;margin-top:9px}.fnm-device-chip{min-width:0;display:flex;align-items:center;gap:7px;text-align:left;border:1px solid ${colors.line}88;border-radius:7px;padding:9px;background:${colors.device};color:${colors.text};cursor:pointer}.fnm-device-chip span{font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}.fnm-device-chip small{font-size:9px;opacity:.62;white-space:nowrap}.fnm-device-chip i{width:8px;height:8px;flex:0 0 8px;border-radius:50%;background:#7b8490}.fnm-device-chip.is-online i{background:#27ae60;box-shadow:0 0 6px #27ae6080}.fnm-device-chip:hover{border-color:${colors.text}}.fnm-detail{margin-top:12px;padding:12px;border:1px solid ${colors.line};border-radius:8px;line-height:1.5;background:${colors.device};font-size:12px}.fnm-detail[hidden]{display:none}.fnm-empty{padding:16px;border:1px dashed ${colors.line};border-radius:9px;opacity:.7;font-size:12px}.fnm-note{font-size:10px;opacity:.58;margin-top:12px}@media(max-width:700px){.fnm-wrap{padding:9px}.fnm-overview-statsbar{grid-template-columns:repeat(2,minmax(0,1fr))}.fnm-overview-grid{grid-template-columns:1fr}.fnm-device-grid{grid-template-columns:1fr}.fnm-device-chip small{display:none}}`;
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
    this.querySelectorAll('.fnm-device-chip').forEach(el=>el.addEventListener('click',()=>{
      const n=byId.get(String(el.dataset.node));if(!n)return;
      this.dispatchEvent(new CustomEvent('hass-more-info',{bubbles:true,composed:true,detail:{entityId:'sensor.fritzbox_network_insight_'+String(n.mac||n.id).replace(/:/g,'').toLowerCase()+'_status'}}));
    }));
  }
}


if (!customElements.get('fritz-network-insight-topology-dialog')) customElements.define('fritz-network-insight-topology-dialog', FritzNetworkInsightTopologyDialog);

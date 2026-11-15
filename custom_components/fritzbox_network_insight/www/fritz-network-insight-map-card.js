/* Network Insight – Network Center view. Read-only; no topology inference. */
class FritzNetworkInsightMapCard extends HTMLElement {
  static getStubConfig(){return {design:"lcars",height:620,refresh_seconds:60};}
  setConfig(config){this.config={design:"lcars",height:620,refresh_seconds:60,...config};this._data=null;this._error="";this._search="";this._filter="all";this._expanded=new Set();this._showMap=false;}
  connectedCallback(){this._active=true;this._load();this._timer=setInterval(()=>this._load(),Math.max(15,Number(this.config?.refresh_seconds)||60)*1000);}
  disconnectedCallback(){this._active=false;clearInterval(this._timer);}
  set hass(hass){this._hass=hass;if(this._active&&!this._data&&!this._loading)this._load();}
  getCardSize(){return 8;}
  getGridOptions(){return {columns:"full",rows:"auto"};}
  async _load(){
    if(!this._hass||this._loading||!this._active)return;
    this._loading=true;
    try{
      const response=await this._hass.callWS({type:"call_service",domain:"fritzbox_network_insight",service:"topology_view",service_data:this.config.entry_id?{entry_id:this.config.entry_id}:{},return_response:true});
      const data=response?.response??response?.service_response??response;
      if(!Array.isArray(data?.nodes)||!Array.isArray(data?.edges))throw Error(data?.error||"Keine gültigen Topologiedaten erhalten");
      this._data=data;this._error="";
    }catch(e){this._error=String(e?.message||e);}finally{this._loading=false;if(this._active)this.render();}
  }
  _esc(v){return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
  _id(n){return String(n.id||n.mac||"").toUpperCase();}
  _kind(n){
    const type=String(n.device_type||"").toLowerCase(),role=String(n.mesh_role||"").toLowerCase();
    if(type.includes("router")||role.includes("router")||role.includes("master"))return "router";
    if(type.includes("switch"))return "switch";
    if(type.includes("repeater")||role.includes("repeater"))return "repeater";
    return "device";
  }
  _connection(n){
    const compact=String(n.mac||n.id||"").replace(/:/g,"").toLowerCase();
    const s=this._hass?.states?.["sensor.fritzbox_network_insight_"+compact+"_connection_peer"];
    if(!s||["unknown","unavailable","none",""].includes(String(s.state).toLowerCase()))return null;
    return {name:String(s.state),mac:String(s.attributes?.connected_to_mac||"").toUpperCase()};
  }
  _online(n){
    if(typeof n.online==="boolean")return n.online;
    if(typeof n.is_online==="boolean")return n.is_online;
    const compact=String(n.mac||n.id||"").replace(/:/g,"").toLowerCase();
    const s=this._hass?.states?.["sensor.fritzbox_network_insight_"+compact+"_status"];
    if(!s)return null;
    const v=String(s.state).toLowerCase();
    if(["online","on","connected","verbunden"].includes(v))return true;
    if(["offline","off","disconnected","getrennt"].includes(v))return false;
    return null;
  }
  _view(){
    const nodes=(this._data?.nodes||[]).filter(n=>n.known_host===true);
    const byId=new Map(nodes.map(n=>[this._id(n),n]));
    const byName=new Map(nodes.map(n=>[String(n.name||"").trim().toLowerCase(),n]));
    const groups=new Map(),assigned=new Set();
    const components=nodes.filter(n=>this._kind(n)!=="device");
    for(const c of components)groups.set(this._id(c),[]);
    for(const n of nodes){
      if(this._kind(n)!=="device")continue;
      const rel=this._connection(n);
      let parent=rel&&(byId.get(rel.mac)||byName.get(rel.name.trim().toLowerCase()));
      if(!parent){
        const edge=(this._data.edges||[]).find(e=>e.target===this._id(n)&&groups.has(String(e.source).toUpperCase())&&(e.kind==="mesh_wlan"&&e.evidence==="avm_mesh"||e.kind==="confirmed_lan"&&e.physical_link_confirmed===true));
        if(edge)parent=byId.get(String(edge.source).toUpperCase());
      }
      if(parent&&groups.has(this._id(parent))){groups.get(this._id(parent)).push(n);assigned.add(this._id(n));}
    }
    return {nodes,components,groups,other:nodes.filter(n=>this._kind(n)==="device"&&!assigned.has(this._id(n)))};
  }
  render(){
    if(!this.config)return;
    const esc=v=>this._esc(v),data=this._data,view=this._view();
    const {nodes,components,groups,other}=view;
    const search=this._search.trim().toLowerCase();
    const matches=n=>!search||[n.name,n.mac,n.ip_address].some(v=>String(v||"").toLowerCase().includes(search));
    const filter=n=>this._filter==="all"||this._filter===this._kind(n);
    const shown=n=>matches(n)&&filter(n);
    const online=nodes.filter(n=>this._online(n)===true).length;
    const offline=nodes.filter(n=>this._online(n)===false).length;
    const connectionCount=[...groups.values()].reduce((sum,a)=>sum+a.length,0);
    const item=n=>'<button class="fnc-device" data-device="'+esc(this._id(n))+'"><span class="fnc-dot '+(this._online(n)===true?"on":"")+'"></span><span class="fnc-device-text"><strong>'+esc(n.name||n.mac)+'</strong><small>'+esc(this._kind(n)==="device"?"Endgerät":this._kind(n))+' · '+esc(n.ip_address||"")+'</small></span></button>';
    const tiles=components.filter(c=>filter(c)||this._filter==="device").map(c=>{
      const devices=groups.get(this._id(c))||[];
      const visible=devices.filter(shown);
      if(search&&!matches(c)&&!visible.length)return "";
      if(this._filter==="device"&&!visible.length)return "";
      const id=this._id(c),expanded=this._expanded.has(id);
      return '<section class="fnc-group"><button class="fnc-group-head" data-group="'+esc(id)+'"><span><strong>'+esc(c.name||c.mac)+'</strong><small>'+devices.length+' direkt verbundene Geräte</small></span><b>'+(expanded?"−":"+")+'</b></button>'+(expanded?'<div class="fnc-group-items">'+(visible.map(item).join("")||'<span class="fnc-empty">Keine passenden Geräte</span>')+'</div>':"")+'</section>';
    }).join("");
    const otherVisible=other.filter(shown);
    const allCount=nodes.length;
    const stats=[["Geräte gesamt",allCount],["Verbindungen",connectionCount],["Online",online],["Offline",offline]];
    this.innerHTML='<ha-card class="fnc-card"><div class="fnc-wrap"><h2>Network Center</h2>'+
      '<div class="fnc-stats">'+stats.map(([label,value])=>'<div class="fnc-stat"><strong>'+value+'</strong><small>'+label+'</small></div>').join("")+'</div>'+
      '<div class="fnc-meta"><span>Router: '+components.filter(n=>this._kind(n)==="router").length+'</span><span>Switch: '+components.filter(n=>this._kind(n)==="switch").length+'</span><span>Repeater: '+components.filter(n=>this._kind(n)==="repeater").length+'</span></div>'+
      '<div class="fnc-actions"><button class="fnc-map-toggle">'+(this._showMap?"← Network Center":"→ Netzwerk-Map öffnen")+'</button></div>'+
      (this._error?'<p class="fnc-error">'+esc(this._error)+'</p>':"")+
      (!data?'<p>Topologiedaten werden geladen …</p>':
      '<div class="fnc-controls"><input class="fnc-search" type="search" placeholder="Gerät, IP oder MAC suchen ..." value="'+esc(this._search)+'"><select class="fnc-filter"><option value="all">Alle Geräte</option><option value="router">Router</option><option value="switch">Switches</option><option value="repeater">Repeater</option><option value="device">Endgeräte</option></select></div>'+
      (this._showMap?'<p class="fnc-info">Die grafische Netzwerk-Map wird in einem späteren Schritt angepasst. Die Network-Center-Ansicht bleibt unverändert verfügbar.</p>':
      '<h3>NETZWERKKOMPONENTEN UND DIREKT VERBUNDENE GERÄTE</h3><div class="fnc-groups">'+tiles+'</div><h3>WEITERE GERÄTE</h3><div class="fnc-other">'+otherVisible.map(item).join("")+'</div>')+
      '<footer>Datenquelle: sensor.netzwerk_topologie · Beziehungen werden ausschließlich aus den Sensorattributen übernommen.</footer>')+
      '</div></ha-card><style>'+
      ':host{display:block;width:100%;min-width:0}.fnc-card{background:#161a20;color:#e7eaf0;border-radius:30px;overflow:hidden}.fnc-wrap{padding:14px;box-sizing:border-box;font-family:inherit}.fnc-wrap h2{font-size:22px;font-weight:500;margin:0 0 32px}.fnc-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.fnc-stat{border:1px solid #344052;border-radius:10px;padding:12px;min-height:75px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}.fnc-stat strong{font-size:26px;color:#03a9f4;line-height:1.1}.fnc-stat small{font-size:12px;color:#b8c8e0}.fnc-meta{display:flex;gap:12px;margin-top:12px;font-size:12px;color:#a8bde0}.fnc-actions{display:flex;justify-content:flex-end;margin:12px 0 10px}.fnc-map-toggle{background:#03a9f4;color:#071522;border:0;border-radius:9px;padding:12px 18px;cursor:pointer;font-weight:600}.fnc-controls{display:flex;gap:8px;margin:8px 0 16px}.fnc-search,.fnc-filter{background:#222c3a;border:1px solid #354357;border-radius:9px;color:#e7eaf0;padding:12px;font:inherit;box-sizing:border-box}.fnc-search{flex:1;min-width:0}.fnc-filter{width:135px}.fnc-wrap h3{font-size:12px;margin:16px 0 10px;font-weight:700}.fnc-groups{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}.fnc-group{min-width:0}.fnc-group-head{width:100%;min-height:72px;display:flex;align-items:center;justify-content:space-between;text-align:left;gap:10px;border:1px solid #344052;background:#222c3a;color:#e7eaf0;border-radius:10px;padding:12px;cursor:pointer}.fnc-group-head strong,.fnc-device strong{display:block;font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fnc-group-head small,.fnc-device small{display:block;font-size:11px;color:#a6bce1;margin-top:5px}.fnc-group-head b{color:#03a9f4}.fnc-group-items{display:grid;gap:5px;padding-top:6px}.fnc-other{display:flex;flex-wrap:wrap;gap:8px}.fnc-device{display:flex;align-items:center;gap:8px;min-width:190px;max-width:100%;border:1px solid #344052;border-radius:9px;background:#222c3a;color:#e7eaf0;text-align:left;padding:10px;cursor:pointer}.fnc-group-items .fnc-device{width:100%;min-width:0}.fnc-device-text{min-width:0}.fnc-dot{width:8px;height:8px;flex:none;background:#697383;border-radius:50%}.fnc-dot.on{background:#31cb8b}.fnc-wrap footer{font-size:11px;color:#a6bce1;margin-top:14px}.fnc-error{color:#ff9999}.fnc-info{padding:24px;border:1px solid #344052;border-radius:10px}@media(max-width:850px){.fnc-groups{grid-template-columns:repeat(2,minmax(0,1fr))}.fnc-stats{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:520px){.fnc-groups{grid-template-columns:1fr}.fnc-controls{flex-wrap:wrap}.fnc-filter{width:100%}}'+
      '</style>';
    const input=this.querySelector(".fnc-search");
    if(input){input.addEventListener("input",e=>{const pos=e.target.selectionStart;this._search=e.target.value;this.render();const next=this.querySelector(".fnc-search");next?.focus();try{next?.setSelectionRange(pos,pos);}catch(_){}});}
    const select=this.querySelector(".fnc-filter");
    if(select){select.value=this._filter;select.addEventListener("change",e=>{this._filter=e.target.value;this.render();});}
    this.querySelector(".fnc-map-toggle")?.addEventListener("click",()=>{this._showMap=!this._showMap;this.render();});
    this.querySelectorAll("[data-group]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.group;if(this._expanded.has(id))this._expanded.delete(id);else this._expanded.add(id);this.render();}));
    this.querySelectorAll("[data-device]").forEach(b=>b.addEventListener("click",()=>{const id=b.dataset.device;const n=nodes.find(x=>this._id(x)===id);if(n){const event=new CustomEvent("hass-more-info",{bubbles:true,composed:true,detail:{entityId:"sensor.fritzbox_network_insight_"+String(n.mac||"").replace(/:/g,"").toLowerCase()+"_status"}});this.dispatchEvent(event);}}));
  }
}
if(!customElements.get("fritz-network-insight-map-card"))customElements.define("fritz-network-insight-map-card",FritzNetworkInsightMapCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==="fritz-network-insight-map-card"))window.customCards.push({type:"fritz-network-insight-map-card",name:"FRITZ!Box Network Insight Map",description:"Network Center using existing integration data"});

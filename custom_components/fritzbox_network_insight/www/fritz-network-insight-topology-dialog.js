/* Read-only topology dialog renderer; uses supplied topology_view data. */
class FritzNetworkInsightTopologyDialog extends HTMLElement {
  setConfig(config) { this.config={...config}; this.render(); }
  set hass(hass) { this._hass=hass; this.render(); }
  set topology(data) { this._topology=data; this.render(); }
  _esc(v) { return String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c])); }
  render() {
    if (!this.isConnected || !this._topology || !this.config) return;
    const nodes=(this._topology.nodes||[]).filter(n=>n.known_host===true);
    const id=n=>String(n.mac||n.id||"").toUpperCase();
    const kind=n=>String(n.device_type||"device").toLowerCase();
    const infrastructure=nodes.filter(n=>["router","switch","repeater","access_point"].includes(kind(n)));
    const infraIds=new Set(infrastructure.map(id));
    const validEdges=(this._topology.edges||[]).filter(e=>infraIds.has(String(e.source).toUpperCase())&&infraIds.has(String(e.target).toUpperCase())&&((e.kind==="mesh_wlan"&&e.evidence==="avm_mesh")||(e.kind==="confirmed_lan"&&e.physical_link_confirmed===true)));
    const children=new Map(infrastructure.map(n=>[id(n),[]])),parent=new Map();
    for(const e of validEdges){const a=String(e.source).toUpperCase(),b=String(e.target).toUpperCase();if(a!==b&&!parent.has(b)){parent.set(b,a);children.get(a).push(b);}}
    const roots=infrastructure.filter(n=>!parent.has(id(n))),byId=new Map(infrastructure.map(n=>[id(n),n]));
    const depths=new Map(),columns=new Map();let next=0;
    const visiting=new Set();
    const layout=(key,d)=>{if(visiting.has(key))return next++;visiting.add(key);depths.set(key,d);const kids=(children.get(key)||[]).filter(k=>!visiting.has(k));const x=kids.length?kids.map(k=>layout(k,d+1)).reduce((a,b)=>a+b,0)/kids.length:next++;columns.set(key,x);return x;};
    roots.forEach(n=>layout(id(n),0));infrastructure.forEach(n=>{if(!columns.has(id(n)))layout(id(n),0);});
    const width=Math.max(850,next*220+100),height=Math.max(400,...Array.from(depths.values()).map(d=>d*160+180));
    const pos=key=>({x:100+(columns.get(key)||0)*220,y:30+(depths.get(key)||0)*160});
    const lines=validEdges.map(e=>{const a=String(e.source).toUpperCase(),b=String(e.target).toUpperCase();if(parent.get(b)!==a)return "";const p=pos(a),q=pos(b);return '<path d="M '+p.x+' '+(p.y+95)+' C '+p.x+' '+(p.y+130)+' '+q.x+' '+(q.y-35)+' '+q.x+' '+q.y+'"/>';}).join("");
    const cards=infrastructure.map(n=>{const p=pos(id(n));return '<button class="fnit-node" data-node="'+this._esc(id(n))+'" style="left:'+(p.x-95)+'px;top:'+p.y+'px"><strong>'+this._esc(n.name||n.mac)+'</strong><small>'+this._esc(kind(n))+'</small><small>'+this._esc(n.ip_address||"")+'</small></button>';}).join("");
    const details=nodes.filter(n=>!infraIds.has(id(n))).map(n=>'<button class="fnit-device" data-node="'+this._esc(id(n))+'">'+this._esc(n.name||n.mac)+'</button>').join("");
    this.innerHTML='<style>:host{display:block;color:#e7f5ff;font-family:inherit}.fnit-canvas{position:relative;min-height:400px}.fnit-canvas svg{position:absolute;inset:0;width:100%;height:100%;fill:none;stroke:#0b7896;stroke-width:2}.fnit-scroll{overflow:auto;max-width:100%}.fnit-node{position:absolute;box-sizing:border-box;width:190px;height:95px;border:1px solid #0b7896;border-radius:12px;background:#102b3c;color:#e7f5ff;text-align:left;padding:12px;cursor:pointer}.fnit-node strong,.fnit-node small{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.fnit-node small{font-size:11px;margin-top:6px}.fnit-devices{display:flex;flex-wrap:wrap;gap:6px}.fnit-device{border:1px solid #0b7896;border-radius:8px;padding:9px;background:#102b3c;color:#e7f5ff;cursor:pointer}</style><h3>Netzwerktopologie</h3><div class="fnit-scroll"><div class="fnit-canvas" style="width:'+width+'px;height:'+height+'px"><svg viewBox="0 0 '+width+' '+height+'">'+lines+'</svg>'+cards+'</div></div><h3>Endgeräte ('+(nodes.length-infrastructure.length)+')</h3><div class="fnit-devices">'+details+'</div>';
    this.querySelectorAll("[data-node]").forEach(el=>el.addEventListener("click",()=>{const n=nodes.find(x=>id(x)===el.dataset.node);if(!n)return;this.dispatchEvent(new CustomEvent("hass-more-info",{bubbles:true,composed:true,detail:{entityId:"sensor.fritzbox_network_insight_"+String(n.mac||n.id).replace(/:/g,"").toLowerCase()+"_status"}}));}));
  }
}
if(!customElements.get("fritz-network-insight-topology-dialog"))customElements.define("fritz-network-insight-topology-dialog",FritzNetworkInsightTopologyDialog);

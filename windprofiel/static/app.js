"use strict";
const $ = (id) => document.getElementById(id);
const ids = ["fryslan", "beabuorren"];
const format = (v, digits = 1) => new Intl.NumberFormat("nl-NL", {maximumFractionDigits: digits}).format(v);
let current = null;
let sequence = 0;
let busy = false;
const svgNS = "http://www.w3.org/2000/svg";
function svgElement(tag, attrs = {}, text) {
  const el = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  if (text !== undefined) el.textContent = text;
  return el;
}
function chart(container, values, stamps, unit, emptyMessage, colour = "#32876c", points = []) {
  container.replaceChildren();
  const valid = values.filter(v => v !== null);
  if (!valid.length) {
    const text = document.createElement("div"); text.className = "empty";
    text.textContent = emptyMessage; container.append(text); return;
  }
  const W = 1000, H = 230, left = 53, right = 14, top = 22, bottom = 30;
  const max = Math.max(1, ...valid) * 1.12;
  const x = i => left + i * (W - left - right) / Math.max(1, values.length - 1);
  const y = v => H - bottom - v * (H - top - bottom) / max;
  const svg = svgElement("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Dagprofiel in ${unit}`});
  for (let i = 0; i <= 4; i++) {
    const v = max * i / 4;
    svg.append(svgElement("line", {x1:left, y1:y(v), x2:W-right, y2:y(v), stroke:"#e9eee8"}));
    svg.append(svgElement("text", {x:left-8, y:y(v)+4, "text-anchor":"end"}, format(v)));
  }
  svg.append(svgElement("text", {x:left, y:13}, unit));
  for (let i = 0; i <= 6; i++) {
    const index = Math.round((values.length-1)*i/6);
    svg.append(svgElement("text", {x:x(index), y:H-7, "text-anchor":i===0?"start":i===6?"end":"middle"}, stamps[index].slice(11,16)));
  }
  let path = "", connected = false;
  values.forEach((v,i) => {
    if (v === null) {connected=false; return;}
    path += `${connected ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)} `; connected=true;
  });
  svg.append(svgElement("path", {d:path, fill:"none", stroke:colour, "stroke-width":2, "stroke-linejoin":"round"}));
  const start = Date.parse(stamps[0]);
  points.forEach(point => {
    const index = (Date.parse(point.timestamp) - start) / 60000;
    if(point.value === null || index < 0 || index > values.length-1) return;
    const dot = svgElement("circle", {class:"reference-point", cx:x(index), cy:y(point.value), r:2.6, fill:"white", stroke:colour, "stroke-width":1.5});
    dot.append(svgElement("title", {}, `${point.timestamp} · ${format(point.value,3)} ${unit} · ${unit==="MW"?"berekend uit KNMI-tienminutengemiddelde":"KNMI-tienminutengemiddelde"}`));
    svg.append(dot);
  });
  const cursor = svgElement("line", {y1:top, y2:H-bottom, stroke:colour, visibility:"hidden"});
  const marker = svgElement("circle", {r:4, fill:colour, visibility:"hidden"});
  const label = svgElement("text", {x:W-right, y:13, "text-anchor":"end"});
  svg.append(cursor, marker, label);
  svg.addEventListener("pointermove", event => {
    const position = (event.clientX - svg.getBoundingClientRect().left) / svg.getBoundingClientRect().width * W;
    const index = Math.max(0, Math.min(values.length-1, Math.round((position-left)/(W-left-right)*(values.length-1))));
    cursor.setAttribute("x1",x(index)); cursor.setAttribute("x2",x(index)); cursor.setAttribute("visibility","visible");
    const value=values[index]; marker.setAttribute("visibility",value===null?"hidden":"visible");
    if(value!==null){marker.setAttribute("cx",x(index));marker.setAttribute("cy",y(value));}
    label.textContent=`${stamps[index].slice(11)} · ${value===null?"ontbreekt":`${format(value,3)} ${unit}`}`;
  });
  svg.addEventListener("pointerleave",() => {cursor.setAttribute("visibility","hidden");marker.setAttribute("visibility","hidden");label.textContent="";});
  container.append(svg);
}
function controls() {
  $("previous").disabled = busy || $("date").value <= "2025-01-01";
  $("next").disabled = busy || $("date").value >= "2025-12-31";
  $("export").disabled = busy || !current;
  $("refresh").disabled = busy;
}
async function request(url, options = {}) {
  const preview = window.WINDPROFIEL_PREVIEW;
  if(preview) {
    if(options.method && options.method !== "GET") throw new Error("Een voorbeeldpagina kan geen curves opslaan. Gebruik daarvoor de Python-webserver.");
    const target = new URL(url, "http://example.invalid");
    const first = Object.values(preview.profiles)[0];
    if(target.pathname === "/api/stations") return {stations:ids.map(id=>first.parks[id].station), parks:Object.fromEntries(ids.map(id=>[id,{station:first.parks[id].station.id}]))};
    const data = preview.profiles[target.searchParams.get("date")];
    if(!data) throw new Error(`Deze zelfstandige voorbeeldpagina bevat ${Object.keys(preview.profiles).join(", ")}. Start de Python-server om andere dagen uit KNMI op te halen.`);
    return data;
  }
  const controller = new AbortController();
  const timer = setTimeout(()=>controller.abort(), 25000);
  try {
    // Relatieve paden werken ook wanneer de app onder een URL-prefix staat.
    const response = await fetch(url.replace(/^\//,""), {...options, signal:controller.signal});
    if (!response.headers.get("Content-Type")?.includes("application/json")) {
      throw new Error("Deze pagina bereikt de Python-API niet. Start python3 -m windprofiel.server vanuit de checkout. Een losse HTML-pagina of GitHub Pages voert de KNMI-server niet uit.");
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ophalen mislukt.");
    return data;
  } catch(error) {
    if(error.name === "AbortError") throw new Error("Ophalen duurt langer dan 25 seconden. Controleer de server en KNMI-toegang en probeer opnieuw.");
    if(error instanceof TypeError) throw new Error("De webserver is niet bereikbaar. Start python3 -m windprofiel.server en open de app via die server.");
    throw error;
  } finally {clearTimeout(timer);}
}
function parameters() {
  const params = new URLSearchParams({date: $("date").value});
  ids.forEach(id => params.set(id, $("station-"+id).value));
  params.set("wake", $("wake").checked ? "1" : "0");
  return params;
}
async function load() {
  if (!$("date").checkValidity() || !$("date").value) {$("status").textContent="Kies een geldige datum in 2025.";return;}
  const call = ++sequence;
  busy = true; current = null; controls();
  $("status").textContent="KNMI-metingen ophalen en minuutprofiel berekenen…";
  try {
    const data = await request("/api/profile?"+parameters());
    if (call !== sequence) return;
    current = data;
    ids.forEach(id => {
      const p = data.parks[id], card=$(id);
      const energy = card.querySelector(".energy"); energy.replaceChildren();
      energy.append(document.createTextNode(p.energy_mwh===null?"—":`${format(p.energy_mwh)} MWh`));
      const small=document.createElement("small");small.textContent="GESCHATTE DAGOPBRENGST";energy.append(small);
      chart(card.querySelector(".plot"), p.power_mw, data.timestamps, "MW", p.curve?"Vermogen niet beschikbaar: geen bruikbare windmetingen.":"Vermogen nog niet beschikbaar: voeg een curve voor de juiste turbine-uitvoering toe.", "#32876c", p.reference_points.map(point=>({timestamp:point.timestamp,value:point.power_mw})));
      chart(card.querySelector(".windplot"), p.wind_ms, data.timestamps, "m/s op 10 m", "Geen bruikbare windmetingen.","#749caf", p.reference_points.map(point=>({timestamp:point.timestamp,value:point.wind_ms})));
      card.querySelector(".source").textContent=`KNMI ${p.station.properties.name} · ${p.missing_wind_minutes} ontbrekende windminuten`;
      card.querySelector(".assumptions").textContent=`${p.assumptions} ${data.wake?`Zogverlies: wind ${format(p.wake_deficit*100,0)} % lager voor alle turbines (scenario-aanname).`:"Zogverlies uitgeschakeld."}`;
      const source=card.querySelector(".curve-source");source.replaceChildren();
      if(p.curve){source.append(document.createTextNode(p.curve.status+" "));const link=document.createElement("a");link.href=p.curve.source;link.textContent=p.curve.kind==="cubic_scenario"?"Natuurkundige achtergrond ↗":"Curvebron ↗";link.target="_blank";link.rel="noopener";source.append(link);} else source.textContent="Vermogenscurve ontbreekt; windmetingen zijn wel beschikbaar.";
    });
    const combined=$("combined");combined.querySelector(".energy").textContent=data.combined_energy_mwh===null?"—":`${format(data.combined_energy_mwh)} MWh`;
    chart(combined.querySelector(".plot"),data.combined_mw,data.timestamps,"MW","Gecombineerd vermogen vereist een beschikbare curve én winddata voor beide parken.","#32876c",data.combined_reference_points.map(point=>({timestamp:point.timestamp,value:point.power_mw})));
    $("method").textContent=data.method;
    const missing=ids.filter(id=>!data.parks[id].curve);
    $("status").textContent=`${data.date} · ${format(data.minutes,0)} minuten · Europe/Amsterdam. ${missing.length?"Wind opgehaald; vermogen nog onvolledig door ontbrekende curve.":"Profielen berekend."}${window.WINDPROFIEL_PREVIEW?" Opgeslagen KNMI-voorbeeld; geen live aanvraag.":""}`;
  } catch(error) {
    if(call===sequence){$("status").textContent=error.message;$("charts").querySelectorAll(".plot,.windplot").forEach(el=>el.replaceChildren());$("charts").querySelectorAll(".energy").forEach(el=>el.textContent="—");}
  } finally {if(call===sequence){busy=false;controls();}}
}
function moveDay(delta){const d=new Date($("date").value+"T12:00:00Z");d.setUTCDate(d.getUTCDate()+delta);$("date").value=d.toISOString().slice(0,10);load();}
$("previous").addEventListener("click",()=>moveDay(-1));$("next").addEventListener("click",()=>moveDay(1));
$("date").addEventListener("change",load);$("refresh").addEventListener("click",load);
$("export").addEventListener("click",async()=>{
  if(!current)return;
  // Download de getoonde reeksen, zonder opnieuw de API te raadplegen.
  const a=current.parks.fryslan,b=current.parks.beabuorren;
  const rows=[["tijd_Europe_Amsterdam","fryslan_wind_10m_ms","beabuorren_wind_10m_ms","fryslan_wind_ashoogte_ms","beabuorren_wind_ashoogte_ms","fryslan_geschat_MW","beabuorren_geschat_MW","gecombineerd_geschat_MW"]];
  current.timestamps.forEach((t,i)=>rows.push([t,a.wind_ms[i],b.wind_ms[i],a.hub_wind_ms[i],b.hub_wind_ms[i],a.power_mw[i],b.power_mw[i],current.combined_mw[i]]));
  const blob=new Blob([rows.map(row=>row.map(v=>v===null?"":v).join(",")).join("\r\n")],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=`windprofiel-${current.date}.csv`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
ids.forEach(id=>{
  $("station-"+id).addEventListener("change",load);
  $("curve-"+id).addEventListener("change",async event=>{
    const file=event.target.files[0];if(!file)return;
    try{
      if(file.size>100000)throw new Error("Curve is groter dan 100 kB.");
      await request("/api/curves/"+id,{method:"POST",headers:{"Content-Type":"application/json"},body:await file.text()});
      await load();
    }catch(error){$("status").textContent=error.message;}
    event.target.value="";
  });
});
async function init(){
  busy=true;controls();
  $("status").textContent="KNMI-stations laden…";
  try{
    if(location.protocol === "file:" && !window.WINDPROFIEL_PREVIEW) throw new Error("Open de zelfstandige index.html in de hoofdmap voor voorbeelden, of start python3 -m windprofiel.server voor elke dag in 2025.");
    if(window.WINDPROFIEL_PREVIEW){
      $("preview-notice").hidden=false;
      ids.forEach(id=>{$("station-"+id).disabled=true;$("curve-"+id).disabled=true;});
      Object.keys(window.WINDPROFIEL_PREVIEW.profiles).forEach(day=>{
        const button=document.createElement("button");button.textContent=day;
        button.addEventListener("click",()=>{$("date").value=day;load();});
        $("preview-days").append(button);
      });
    }
    const data=await request("/api/stations");
    const stations=data.stations.filter(s=>s.geometry?.coordinates?.[1]>50).sort((a,b)=>a.properties.name.localeCompare(b.properties.name));
    ids.forEach(id=>{const select=$("station-"+id);stations.forEach(s=>{const option=document.createElement("option");option.value=s.id;option.textContent=`${s.properties.name} (${s.properties.wmoId})`;select.append(option);});select.value=data.parks[id].station;});
    await load();
  }catch(error){$("status").textContent=error.message;}
  finally{busy=false;controls();}
}
controls();init();
$("wake").addEventListener("change",load);
$("show-points").addEventListener("change",event=>$("charts").classList.toggle("hide-points",!event.target.checked));

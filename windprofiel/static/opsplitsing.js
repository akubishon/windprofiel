"use strict";
// Elektrolyser opsplitsen: formulier, aanvragen en grafieken zonder externe bibliotheken.

const $ = id => document.getElementById(id);
const SVG = "http://www.w3.org/2000/svg";
const STORE = "opsplitsing-v2";   // v2: technologiekeuze en EU-standaardwaarden
const COLORS = {one: "#22528F", many: "#0094C6", wash: "#C3E4F2", ink: "#0C2340", muted: "#465970"};
const nf = (value, digits = 1) => value == null || !isFinite(value) ? "–"
  : new Intl.NumberFormat("nl-NL", {minimumFractionDigits: digits, maximumFractionDigits: digits}).format(value);
const pct = (value, digits = 1) => (value > 0 ? "+" : "") + nf(value * 100, digits) + " %";
const label = n => `${n} module${n === 1 ? "" : "s"}`;

let meta = null;
let tech = "pem";
const standard = key => meta.technologieen[tech].waarden[key];
const show = value => nf(value, decimals(value)).replace(/\s|\./g, "");
const SOURCE_CLASS = {"EU LCOH-tool": "eu", "mijnwindpark.nl": "site", "plaatshouder": "placeholder"};
let lastResult = null;
let running = false;

function el(tag, attrs = {}, children = []) {
  const node = document.createElementNS(SVG, tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  for (const child of [].concat(children)) node.append(child);
  return node;
}

function text(x, y, content, attrs = {}) {
  return el("text", {x, y, ...attrs}, [document.createTextNode(content)]);
}

function load() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch { return {}; }
}

function save(state) {
  try { localStorage.setItem(STORE, JSON.stringify(state)); } catch { /* opslag niet beschikbaar */ }
}

// ---------------------------------------------------------------- tooltip

const tooltip = $("tooltip");
function showTip(event, html) {
  tooltip.innerHTML = html;
  tooltip.hidden = false;
  const box = tooltip.getBoundingClientRect();
  let x = event.clientX + 14, y = event.clientY + 14;
  if (x + box.width > innerWidth - 8) x = event.clientX - box.width - 14;
  if (y + box.height > innerHeight - 8) y = event.clientY - box.height - 14;
  tooltip.style.left = Math.max(8, x) + "px";
  tooltip.style.top = Math.max(8, y) + "px";
}
const hideTip = () => { tooltip.hidden = true; };
const swatch = color => `<span class="key ${color === COLORS.one ? "one" : "many"}"></span>`;

// ---------------------------------------------------------------- formulier

function field(item, value) {
  const wrap = document.createElement("div");
  wrap.className = "field";
  const id = "f-" + item.key;
  const base = standard(item.key);
  const hint = `${item.uitleg ? item.uitleg + " " : ""}Standaard ${meta.technologieen[tech].naam}: ${nf(base, decimals(base))}.`;
  wrap.innerHTML = `<label for="${id}">${item.label}${item.eenheid ? ` <span class="unit">(${item.eenheid})</span>` : ""}</label>
    <input id="${id}" inputmode="decimal" autocomplete="off" data-key="${item.key}">
    <div class="field-meta"><span class="source ${SOURCE_CLASS[item.bron]}">${item.bron}</span>
      <details class="hint"><summary aria-label="Uitleg bij ${item.label}">ⓘ</summary><p>${hint}</p></details></div>`;
  const input = wrap.querySelector("input");
  input.value = show(value);
  input.addEventListener("input", () => { validate(input); remember(); drawExplainers(); summarise(); });
  validate(input);
  return wrap;
}

function decimals(value) {
  const text = String(value);
  return text.includes(".") ? Math.min(3, text.split(".")[1].length) : 0;
}

function parse(text) {
  const clean = text.trim().replace(/\s/g, "").replace(",", ".");
  return clean === "" || !/^-?\d*\.?\d+$/.test(clean) ? NaN : Number(clean);
}

function item(key) {
  for (const group of meta.groepen) for (const entry of group.velden) if (entry.key === key) return entry;
  return null;
}

function validate(input) {
  const entry = item(input.dataset.key);
  const value = parse(input.value);
  const ok = isFinite(value) && value >= entry.min && value <= entry.max;
  input.setAttribute("aria-invalid", String(!ok));
  input.title = ok ? "" : `Kies ${nf(entry.min, decimals(entry.min))} tot ${nf(entry.max, decimals(entry.max))}`;
  input.classList.toggle("changed", ok && Math.abs(value - standard(entry.key)) > 1e-9);
  return ok;
}

function values() {
  const out = {};
  for (const input of document.querySelectorAll(".field input")) out[input.dataset.key] = parse(input.value);
  return out;
}

function selection() {
  return {
    strategie: document.querySelector("input[name=strategie]:checked")?.value || "verdelen",
    jaren: [...document.querySelectorAll("input[name=jaar]:checked")].map(i => Number(i.value)),
    modules: [...document.querySelectorAll("input[name=modules]:checked")].map(i => Number(i.value)),
  };
}

function remember() {
  const changed = {};
  const current = values();
  for (const [key, value] of Object.entries(current)) {
    if (isFinite(value) && Math.abs(value - standard(key)) > 1e-9) changed[key] = value;
  }
  save({technologie: tech, aannames: changed, ...selection()});
}

function buildForm(state) {
  tech = meta.technologieen[state.technologie] ? state.technologie : "pem";
  $("technologies").replaceChildren(...Object.entries(meta.technologieen).map(([key, entry]) => {
    const labelNode = document.createElement("label");
    labelNode.innerHTML = `<input type="radio" name="technologie" value="${key}"><span><b>${entry.naam}</b></span>`;
    const input = labelNode.querySelector("input");
    input.checked = key === tech;
    input.addEventListener("change", () => switchTechnology(key));
    return labelNode;
  }));
  $("strategies").replaceChildren(...Object.entries(meta.strategieen).map(([key, description]) => {
    const labelNode = document.createElement("label");
    labelNode.innerHTML = `<input type="radio" name="strategie" value="${key}"><span><b>${key[0].toUpperCase() + key.slice(1)}</b><small>${description}</small></span>`;
    labelNode.querySelector("input").checked = key === (state.strategie || "verdelen");
    return labelNode;
  }));
  const checks = (target, name, list, chosen, format) => $(target).replaceChildren(...list.map(value => {
    const labelNode = document.createElement("label");
    labelNode.innerHTML = `<input type="checkbox" name="${name}" value="${value}"> ${format(value)}`;
    labelNode.querySelector("input").checked = chosen.includes(value);
    return labelNode;
  }));
  checks("years", "jaar", meta.jaren, state.jaren?.length ? state.jaren : meta.jaren, String);
  checks("counts", "modules", meta.modules, state.modules?.length ? state.modules : meta.modules, String);
  const opened = loadOpen();
  $("groups").replaceChildren(...meta.groepen.map(group => {
    const set = document.createElement("details");
    set.className = "group";
    set.dataset.group = group.naam;
    set.open = opened.includes(group.naam);
    set.innerHTML = `<summary><span class="group-name">${group.naam}</span><span class="group-summary"></span></summary>`;
    set.addEventListener("toggle", rememberOpen);
    const reset = document.createElement("button");
    reset.type = "button";
    reset.className = "text-button";
    reset.textContent = "Standaard";
    reset.addEventListener("click", () => {
      for (const entry of group.velden) {
        const input = $("f-" + entry.key);
        input.value = show(standard(entry.key));
        validate(input);
      }
      remember(); drawExplainers(); summarise();
    });
    const body = document.createElement("div");
    body.className = "group-body";
    body.append(reset);
    for (const entry of group.velden) body.append(field(entry, state.aannames?.[entry.key] ?? standard(entry.key)));
    set.append(body);
    return set;
  }));
  summarise();
}

// Korte samenvatting per dichte categorie: de belangrijkste waarden en hoeveel er is aangepast.
const SUMMARIES = {
  "Installatie": v => [`${nf(v.capaciteit_mw, 0)} MW`],
  "Rendement per module": v => [`minimumlast ${nf(v.minimumlast, 0)} %`, `${nf(v.systeemverbruik_vol)} kWh/kg`, `${nf(v.degradatie_1000h, 2)} %/1000 h`],
  "Bedrijfsvoering": v => [`aan ≥ ${nf(v.min_aan_min, 0)} min`, `startvertraging ${nf(v.startvertraging_min, 0)} min`, `koude start ${nf(v.opstart_koud_min, 0)} min`],
  "Beschikbaarheid": v => [`${nf(v.onderhoud_dagen, 0)} dagen onderhoud`, `${nf(v.storingen_per_jaar, 0)} storingen per jaar`],
  "Slijtage": v => [`stack ${nf(v.stack_levensduur_uur, 0)} h`],
  "Kosten": v => [`${nf(v.capex_eur_kw, 0)} €/kW`, `stroom ${nf(v.stroomprijs_eur_mwh + v.netkosten_eur_mwh + v.belasting_eur_mwh, 2)} €/MWh`, `rente ${nf(v.rente, 1)} %`],
  "Subsidies en opbrengsten": v => {
    const parts = [];
    if (v.capex_subsidie_eur_kw) parts.push(`subsidie ${nf(v.capex_subsidie_eur_kw, 0)} €/kW`);
    if (v.waterstofpremie_eur_kg) parts.push(`premie ${nf(v.waterstofpremie_eur_kg, 2)} €/kg`);
    if (v.korting_net_belasting_eur_mwh) parts.push(`korting ${nf(v.korting_net_belasting_eur_mwh, 2)} €/MWh`);
    if (v.zuurstofprijs_eur_t) parts.push(`zuurstof ${nf(v.zuurstofprijs_eur_t, 0)} €/t`);
    return parts.length ? parts : ["geen"];
  },
};

function summarise() {
  const v = values();
  for (const set of document.querySelectorAll("details.group")) {
    const inputs = [...set.querySelectorAll(".field input")];
    const changed = inputs.filter(i => i.classList.contains("changed")).length;
    const bad = inputs.filter(i => i.getAttribute("aria-invalid") === "true").length;
    const parts = (SUMMARIES[set.dataset.group] || (() => []))(v).filter(p => !p.includes("–"));
    if (changed) parts.push(`${changed} aangepast`);
    if (bad) parts.push(`${bad} ongeldig`);
    set.querySelector(".group-summary").textContent = parts.join(" · ");
    set.classList.toggle("has-changes", changed > 0);
    set.classList.toggle("has-errors", bad > 0);
  }
}

function loadOpen() {
  try { return JSON.parse(localStorage.getItem(STORE + "-open")) || []; } catch { return []; }
}

function rememberOpen() {
  const open = [...document.querySelectorAll("details.group[open]")].map(d => d.dataset.group);
  try { localStorage.setItem(STORE + "-open", JSON.stringify(open)); } catch { /* opslag niet beschikbaar */ }
}

// ---------------------------------------------------------------- uitleg

// Wisselen zet alle velden op de standaard van die technologie; eigen wijzigingen vervallen.
function switchTechnology(key) {
  const changed = document.querySelectorAll(".field input.changed").length;
  if (changed && !confirm(`Alle velden op de standaardwaarden voor ${meta.technologieen[key].naam} zetten? ${changed} eigen ${changed === 1 ? "wijziging vervalt" : "wijzigingen vervallen"}.`)) {
    document.querySelector(`input[name=technologie][value=${tech}]`).checked = true;
    return;
  }
  buildForm({...selection(), technologie: key, aannames: {}});
  remember();
  drawExplainers();
}

// Spiegelt stack_sec_full, stack_kg_h en draw_mw in opsplitsing.py; v in getoonde eenheden.
function kgPerMWh(x, v, ageing = true) {
  if (x <= 0 || x < v.minimumlast / 100 - 1e-9) return 0;
  const faraday = Math.max(0, 1 - (v.faradayverlies_10 / 100) * 0.1 / x);
  const full = v.systeemverbruik_vol * (1 - v.faradayverlies_10 / 100 * 0.1) / (1 + v.bop_variabel / 100 + v.bop_vast / 100);
  const wear = ageing ? v.degradatie_1000h / 100 * v.stack_levensduur_uur / 1000 / 2 : 0;
  const sec = full * (1 - v.deellastvoordeel / 100 * (1 - x)) * (1 + wear);
  const draw = x * (1 + v.bop_variabel / 100) + v.bop_vast / 100;
  return x * 1000 / sec * faraday / draw;
}

function threshold(size, v) {
  return size * (v.minimumlast / 100 * (1 + v.bop_variabel / 100) + v.bop_vast / 100);
}

function drawExplainers() {
  const v = values();
  if (Object.values(v).some(x => !isFinite(x))) return;
  drawThresholdArt(v);
  drawEfficiency(v);
}

function drawThresholdArt(v) {
  const svg = $("threshold-art");
  const title = svg.querySelector("title");
  const W = 440, H = 220, L = 34, R = 150, T = 14, B = 196;
  const big = threshold(v.capaciteit_mw, v), small = threshold(v.capaciteit_mw / 4, v);
  const top = Math.max(big * 1.8, 4);
  const xs = Array.from({length: 121}, (_, i) => i / 120);
  const wave = x => top * (0.42 + 0.3 * Math.sin(x * 9.5) + 0.18 * Math.sin(x * 23 + 1) + 0.08 * Math.sin(x * 51));
  const px = x => L + x * (W - L - R);
  const py = value => B - Math.max(0, Math.min(top, value)) / top * (B - T);
  const area = cut => {
    const points = xs.map(x => [px(x), py(wave(x) >= cut ? wave(x) : 0)]);
    return `M${px(0)},${B} ` + points.map(p => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" ") + ` L${px(1)},${B} Z`;
  };
  svg.replaceChildren(title,
    el("line", {x1: L, x2: px(1), y1: B, y2: B, class: "axis", stroke: "#bcc8d2"}),
    el("path", {d: area(small), fill: COLORS.many, "fill-opacity": .25}),
    el("path", {d: area(big), fill: COLORS.one, "fill-opacity": .35}),
    el("polyline", {points: xs.map(x => `${px(x).toFixed(1)},${py(wave(x)).toFixed(1)}`).join(" "), fill: "none", stroke: COLORS.ink, "stroke-width": 2, "stroke-linejoin": "round"}),
    el("line", {x1: L, x2: px(1), y1: py(big), y2: py(big), stroke: COLORS.one, "stroke-width": 1.5, "stroke-dasharray": "6 4"}),
    el("line", {x1: L, x2: px(1), y1: py(small), y2: py(small), stroke: COLORS.many, "stroke-width": 1.5, "stroke-dasharray": "6 4"}),
    text(px(1) + 8, py(big) + 4, `1 × ${nf(v.capaciteit_mw, 0)} MW: vanaf ${nf(big)} MW`, {fill: COLORS.ink, "font-size": 11}),
    text(px(1) + 8, py(small) + 4, `4 × ${nf(v.capaciteit_mw / 4)} MW: vanaf ${nf(small)} MW`, {fill: COLORS.ink, "font-size": 11}),
    text(px(1) + 8, py(wave(1)) + 4, "windaanbod", {fill: COLORS.muted, "font-size": 11}),
    text(L, B + 18, "tijd →", {fill: COLORS.muted, "font-size": 11}),
    text(L - 6, T + 4, "MW", {fill: COLORS.muted, "font-size": 11, "text-anchor": "end"}));
}

function drawEfficiency(v) {
  const W = 440, H = 220, L = 44, R = 16, T = 30, B = 184;
  const xs = Array.from({length: 101}, (_, i) => i / 100);
  const ys = xs.map(x => kgPerMWh(x, v));
  const top = niceTop(Math.max(...ys, 1) * 1.1);
  const px = x => L + x * (W - L - R), py = y => B - y / top * (B - T);
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true"});
  for (let y = 0; y <= top; y += top / 4) {
    svg.append(el("line", {x1: L, x2: W - R, y1: py(y), y2: py(y), class: y ? "grid" : "axis"}),
      text(L - 6, py(y) + 4, nf(y, 0), {"text-anchor": "end"}));
  }
  for (const x of [0, .25, .5, .75, 1]) svg.append(text(px(x), B + 16, nf(x * 100, 0) + " %", {"text-anchor": "middle"}));
  svg.append(text(L - 40, T - 16, "kg per MWh", {}), text(W - R, B + 32, "last van de module", {"text-anchor": "end"}));
  const live = xs.map((x, i) => [x, ys[i]]).filter(([, y]) => y > 0);
  const minLoad = v.minimumlast / 100;
  svg.append(el("rect", {x: L, y: T, width: px(minLoad) - L, height: B - T, fill: COLORS.wash, "fill-opacity": .6}),
    text(L + 6, T + 14, "onder minimumlast", {fill: COLORS.ink}));
  if (live.length) {
    svg.append(el("polyline", {points: live.map(([x, y]) => `${px(x).toFixed(1)},${py(y).toFixed(1)}`).join(" "),
      fill: "none", stroke: COLORS.one, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round"}));
    const best = live.reduce((a, b) => b[1] > a[1] ? b : a);
    svg.append(el("circle", {cx: px(best[0]), cy: py(best[1]), r: 4.5, fill: COLORS.one, stroke: "#fff", "stroke-width": 2}),
      text(px(best[0]), py(best[1]) - 10, `${nf(best[1])} kg/MWh bij ${nf(best[0] * 100, 0)} %`, {"text-anchor": best[0] > .7 ? "end" : "middle", class: "label"}));
    const hit = el("rect", {x: L, y: T, width: W - L - R, height: B - T, class: "hit"});
    hit.addEventListener("mousemove", event => {
      const box = hit.getBoundingClientRect();
      const x = Math.max(0, Math.min(1, (event.clientX - box.left) / box.width));
      const y = kgPerMWh(x, v);
      showTip(event, `<b>Last ${nf(x * 100, 0)} %</b><br>${y ? nf(y) + " kg per MWh stroom<br>" + nf(1000 / y) + " kWh per kg" : "Onder de minimumlast: geen productie"}`);
    });
    hit.addEventListener("mouseleave", hideTip);
    svg.append(hit);
  }
  $("efficiency-chart").replaceChildren(svg);
  $("efficiency-caption").textContent = `Gemiddeld over het stackleven. Op vollast ${nf(1000 / kgPerMWh(1, v))} kWh/kg; een nieuwe stack ${nf(1000 / kgPerMWh(1, v, false))} kWh/kg. Volgt de aannames uit stap 2.`;
}

// ---------------------------------------------------------------- grafieken per aantal modules

function frame(rows, top, {bottom = 0, unit = ""} = {}) {
  const format = v => nf(v, digitsFor((top - bottom) / 4));
  const W = 520, H = 260, L = 52, R = 14, T = 22, B = 214;
  const band = (W - L - R) / rows.length;
  const cx = i => L + band * (i + .5);
  const py = y => B - (y - bottom) / (top - bottom) * (B - T);
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true"});
  for (let i = 0; i <= 4; i++) {
    const y = bottom + (top - bottom) * i / 4;
    svg.append(el("line", {x1: L, x2: W - R, y1: py(y), y2: py(y), class: i ? "grid" : "axis"}),
      text(L - 6, py(y) + 4, format(y), {"text-anchor": "end"}));
  }
  rows.forEach((row, i) => svg.append(text(cx(i), B + 16, String(row.modules), {"text-anchor": "middle"})));
  svg.append(text(W - R, B + 34, "aantal modules", {"text-anchor": "end"}), text(L, T - 8, unit));
  return {svg, cx, py, band, L, R, T, B, W};
}

function hover(f, rows, html) {
  rows.forEach((row, i) => {
    const band = el("rect", {x: f.cx(i) - f.band / 2, y: f.T, width: f.band, height: f.B - f.T, class: "hit"});
    band.addEventListener("mousemove", event => showTip(event, html(row, i)));
    band.addEventListener("mouseleave", hideTip);
    f.svg.append(band);
  });
}

// Ronde as met vier gelijke stappen van 1, 2, 2,5 of 5 × 10^n.
function niceScale(low, high) {
  const raw = Math.max(high - low, 1e-9) / 4;
  const power = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map(m => m * power).find(m => m >= raw);
  let bottom = Math.floor(low / step) * step;
  while (bottom + 4 * step < high) bottom += step;
  return {bottom, top: bottom + 4 * step, step};
}
const niceTop = value => niceScale(0, value).top;
const digitsFor = step => step >= 1 ? 0 : step >= .1 ? 1 : 2;

function lineWithRange(target, rows, key, unit, digits) {
  const lows = rows.map(r => Math.min(...Object.values(r.jaren).map(y => y[key])));
  const highs = rows.map(r => Math.max(...Object.values(r.jaren).map(y => y[key])));
  const min = Math.min(...lows), max = Math.max(...highs);
  // Een lijn mag boven nul beginnen; de as maakt dat zichtbaar.
  const scale = niceScale(min - (max - min) * .25, max + (max - min) * .25);
  const f = frame(rows, scale.top, {bottom: scale.bottom, unit});
  rows.forEach((row, i) => f.svg.append(el("line", {x1: f.cx(i), x2: f.cx(i), y1: f.py(lows[i]), y2: f.py(highs[i]), stroke: COLORS.one, "stroke-opacity": .35, "stroke-width": 6, "stroke-linecap": "round"})));
  f.svg.append(el("polyline", {points: rows.map((r, i) => `${f.cx(i)},${f.py(r[key])}`).join(" "), fill: "none", stroke: COLORS.one, "stroke-width": 2, "stroke-linejoin": "round"}));
  const best = key === "lcoh_eur_kg" ? rows.reduce((a, b) => b[key] < a[key] ? b : a) : rows[rows.length - 1];
  rows.forEach((row, i) => {
    f.svg.append(el("circle", {cx: f.cx(i), cy: f.py(row[key]), r: 4.5, fill: COLORS.one, stroke: "#fff", "stroke-width": 2}));
    if (row === best || i === 0) f.svg.append(text(f.cx(i), f.py(highs[i]) - 9, nf(row[key], digits), {"text-anchor": "middle", class: "label"}));
  });
  hover(f, rows, (row, i) => `<b>${label(row.modules)} van ${nf(row.module_mw)} MW</b><br>Gemiddeld ${nf(row[key], digits)} ${unit}<br>Windjaren ${nf(lows[i], digits)} tot ${nf(highs[i], digits)}<br>Benutting aanbod ${nf(row.benutting * 100)} %`);
  $(target).replaceChildren(f.svg);
}

function capexChart(rows) {
  const top = niceTop(Math.max(...rows.flatMap(r => [r.capex_meur, r.capex_break_even_meur])) * 1.05);
  const f = frame(rows, top, {unit: "M€"});
  const width = Math.min(22, (f.band - 14) / 2);
  rows.forEach((row, i) => {
    [[row.capex_meur, COLORS.one, -1], [row.capex_break_even_meur, COLORS.many, 1]].forEach(([value, color, side]) => {
      const x = side < 0 ? f.cx(i) - width - 1 : f.cx(i) + 1;
      const y = f.py(Math.max(0, value)), h = f.B - y;
      const r = Math.min(4, h, width / 2);
      f.svg.append(el("path", {d: `M${x},${f.B} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${f.B} Z`, fill: color}));
    });
  });
  hover(f, rows, row => {
    const room = row.capex_break_even_meur / row.capex_meur - 1;
    return `<b>${label(row.modules)} van ${nf(row.module_mw)} MW</b>
      <div class="row">${swatch(COLORS.one)} Aangenomen CAPEX ${nf(row.capex_meur)} M€</div>
      <div class="row">${swatch(COLORS.many)} Maximaal ${nf(row.capex_break_even_meur)} M€</div>
      ${room >= 0 ? "Ruimte " + nf(room * 100) + " %" : "Aanname ligt " + nf(-room * 100) + " % boven het maximum"}`;
  });
  const legend = document.createElement("div");
  legend.className = "legend";
  legend.innerHTML = `<span>${swatch(COLORS.one)} Aangenomen CAPEX</span><span>${swatch(COLORS.many)} Maximaal om ${label(rows[0].modules)} te verslaan</span>`;
  $("capex-chart").replaceChildren(legend, f.svg);
}

function stepChart(rows) {
  const steps = rows.slice(1);
  if (!steps.length) { $("step-chart").textContent = "Kies minstens twee moduleaantallen."; return; }
  const top = niceTop(Math.max(...steps.map(r => Math.abs(r.extra_waterstof_t)), 1) * 1.15);
  const f = frame(steps, top, {unit: "ton per jaar"});
  const width = Math.min(24, f.band - 12);
  const biggest = steps.reduce((a, b) => b.extra_waterstof_t > a.extra_waterstof_t ? b : a);
  steps.forEach((row, i) => {
    const value = Math.max(0, row.extra_waterstof_t);
    const x = f.cx(i) - width / 2, y = f.py(value), h = f.B - y, r = Math.min(4, h, width / 2);
    f.svg.append(el("path", {d: `M${x},${f.B} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${f.B} Z`, fill: COLORS.one}));
    if (row === biggest || i === steps.length - 1) f.svg.append(text(f.cx(i), y - 7, nf(row.extra_waterstof_t, 0) + " t", {"text-anchor": "middle", class: "label"}));
  });
  hover(f, steps, (row, i) => {
    const before = rows[i];
    return `<b>${before.modules} → ${row.modules} modules</b><br>${nf(row.extra_waterstof_t, 1)} ton extra (${pct(row.extra_waterstof_t / before.waterstof_t)})<br>Kosten ${row.extra_kosten_meur_jaar >= 0 ? "+" : ""}${nf(row.extra_kosten_meur_jaar, 2)} M€ per jaar`;
  });
  $("step-chart").replaceChildren(f.svg);
}

// Opbrengst per kilo (premie en zuurstof) uit de aannames van de uitkomst, in opgeslagen eenheden.
const revenuePerKg = result => result.aannames.waterstofpremie_eur_kg + result.aannames.zuurstofprijs_eur_t * 8 / 1000;

function table(rows, net) {
  const columns = [
    ["Modules", r => `${r.modules} × ${nf(r.module_mw)} MW`],
    ["Waterstof (t/jaar)", r => nf(r.waterstof_t, 0)],
    ["Benutting aanbod", r => nf(r.benutting * 100) + " %"],
    ["Bedrijfsuren per module", r => nf(r.bedrijfsuren_gem, 0)],
    ["Starts per module (warm / koud)", r => `${nf(r.starts_warm_per_module, 0)} / ${nf(r.starts_koud_per_module, 0)}`],
    ["Stackwissel na (jaar)", r => nf(r.jaren_tot_stackwissel)],
    ["CAPEX (M€)", r => nf(r.capex_meur)],
    ["Maximale CAPEX (M€)", r => nf(r.capex_break_even_meur)],
    ["Stroom (M€/jaar)", r => nf(r.stroom_meur_jaar, 2)],
    ["Stack (M€/jaar)", r => nf(r.stack_meur_jaar, 2)],
    ["Kosten (M€/jaar)", r => nf(r.kosten_meur_jaar, 2)],
    ["LCOH (€/kg)", r => nf(r.lcoh_eur_kg, 2)],
    ...(net ? [["Netto (€/kg)", r => nf(r.netto_eur_kg, 2)]] : []),
  ];
  const best = rows.reduce((a, b) => (b.lcoh_eur_kg ?? Infinity) < (a.lcoh_eur_kg ?? Infinity) ? b : a);
  const head = `<caption class="note">Gemiddelden over de gekozen windjaren. De vetgedrukte rij heeft de laagste LCOH.</caption><thead><tr>${columns.map(c => `<th scope="col">${c[0]}</th>`).join("")}</tr></thead>`;
  const body = rows.map(r => `<tr${r === best ? ' class="best"' : ""}>${columns.map(c => `<td>${c[1](r)}</td>`).join("")}</tr>`).join("");
  $("table").innerHTML = head + `<tbody>${body}</tbody>`;
}

function headline(rows, result) {
  const base = rows[0];
  // Knikpunt: het eerste aantal waarna een extra stap minder dan 1 % waterstof oplevert.
  let knee = base;
  for (let i = 1; i < rows.length; i++) {
    if (rows[i].extra_waterstof_t / rows[i - 1].waterstof_t < 0.01) break;
    knee = rows[i];
  }
  const gain = knee.waterstof_t / base.waterstof_t - 1;
  const room = knee.capex_break_even_meur / base.capex_meur - 1;
  $("headline").innerHTML = `
    <div><span>Knikpunt</span><strong>${label(knee.modules)}</strong><p>Daarna levert een extra module minder dan 1 % waterstof op.</p></div>
    <div><span>Meer waterstof</span><strong>${pct(gain)}</strong><p>${label(knee.modules)} ten opzichte van ${label(base.modules)}: ${nf(knee.waterstof_t - base.waterstof_t, 0)} ton per jaar.</p></div>
    <div><span>Mag duurder zijn</span><strong>${pct(room)}</strong><p>Hoogste CAPEX voor ${label(knee.modules)} waarbij de kilo niet duurder wordt dan met ${label(base.modules)}: ${nf(knee.capex_break_even_meur)} M€.</p></div>`;
  const years = result.jaren.join(", ");
  $("result-sub").textContent = `Besturing ‘${result.strategie}’, windjaren ${years}. Aanbod gemiddeld ${nf(Object.values(result.aanbod).reduce((s, a) => s + a.mwh, 0) / result.jaren.length / 1000, 0)} GWh per jaar.`;
}

function render(result) {
  lastResult = result;
  const rows = result.rijen;
  $("results").hidden = false;
  headline(rows, result);
  lineWithRange("h2-chart", rows, "waterstof_t", "ton", 0);
  capexChart(rows);
  const net = revenuePerKg(result) > 0;
  $("lcoh-title").textContent = net ? "Netto kosten per kilo" : "Kosten per kilo (LCOH)";
  $("lcoh-note").textContent = net
    ? `LCOH min premie en zuurstofverkoop (${nf(revenuePerKg(result), 2)} €/kg); de streep toont de spreiding tussen windjaren.`
    : "Met de aangenomen CAPEX en schaalfactor; de streep toont de spreiding tussen windjaren.";
  lineWithRange("lcoh-chart", rows, net ? "netto_eur_kg" : "lcoh_eur_kg", "€/kg", 2);
  stepChart(rows);
  table(rows, net);
  renderSpeed(result);
  const others = rows.slice(1).map(r => r.modules);
  $("day-panel").hidden = !others.length;
  if (others.length) {
    const prefer = others.includes(4) ? 4 : others[0];
    $("day-count").replaceChildren(...others.map(n => new Option(label(n), n, false, n === prefer)));
    const day = $("day");
    day.min = `${Math.min(...result.jaren)}-01-01`;
    day.max = `${Math.max(...result.jaren)}-12-31`;
    if (!day.value || day.value < day.min || day.value > day.max) day.value = result.voorbeelddag || day.min;
    runDay();
  }
}

// ---------------------------------------------------------------- dag van dichtbij

const day = {data: null, n: 0, v: null, index: 0, marker: null};

function dayChart(data, n, v) {
  const one = data.configuraties[1] || data.configuraties["1"];
  const many = data.configuraties[n] || data.configuraties[String(n)];
  const steps = one.stappen;
  const W = 1000, H = 300, L = 48, R = 16, T = 16, B = 260;
  const start = steps[0].t, span = steps[steps.length - 1].t + 600 - start;
  const px = t => L + (t - start) / span * (W - L - R);
  const top = niceTop(Math.max(...steps.map(s => s.aanbod), threshold(v.capaciteit_mw, v)));
  const py = y => B - y / top * (B - T);
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, "aria-hidden": "true"});
  for (let i = 0; i <= 4; i++) {
    const y = top * i / 4;
    svg.append(el("line", {x1: L, x2: W - R, y1: py(y), y2: py(y), class: i ? "grid" : "axis"}), text(L - 6, py(y) + 4, nf(y, 0), {"text-anchor": "end"}));
  }
  for (let h = 0; h * 3600 <= span; h += 3) svg.append(text(px(start + h * 3600), B + 18, String(h).padStart(2, "0") + ":00", {"text-anchor": "middle"}));
  svg.append(text(L, T - 4, "MW"));
  const stepLine = (list, value) => list.map(s => `${px(s.t).toFixed(1)},${py(value(s)).toFixed(1)} ${px(s.t + 600).toFixed(1)},${py(value(s)).toFixed(1)}`).join(" ");
  svg.append(el("path", {d: `M${px(start)},${B} L` + stepLine(steps, s => s.aanbod).replace(/ /g, " L") + ` L${px(steps[steps.length - 1].t + 600)},${B} Z`, fill: COLORS.wash, "fill-opacity": .7}));
  const big = threshold(v.capaciteit_mw, v), small = threshold(v.capaciteit_mw / n, v);
  svg.append(el("line", {x1: L, x2: W - R, y1: py(big), y2: py(big), stroke: COLORS.one, "stroke-dasharray": "6 4", "stroke-width": 1.2}),
    el("line", {x1: L, x2: W - R, y1: py(small), y2: py(small), stroke: COLORS.many, "stroke-dasharray": "6 4", "stroke-width": 1.2}));
  svg.append(el("polyline", {points: stepLine(one.stappen, s => s.verbruik), fill: "none", stroke: COLORS.one, "stroke-width": 2, "stroke-linejoin": "round"}),
    el("polyline", {points: stepLine(many.stappen, s => s.verbruik), fill: "none", stroke: COLORS.many, "stroke-width": 2, "stroke-linejoin": "round"}));
  const cursor = el("line", {x1: 0, x2: 0, y1: T, y2: B, stroke: COLORS.ink, "stroke-width": 1, visibility: "hidden"});
  // Gekozen moment voor het rekenvoorbeeld: band over de tien minuten plus stippen op beide lijnen.
  const pick = el("g", {class: "pick"});
  const hit = el("rect", {x: L, y: T, width: W - L - R, height: B - T, class: "hit"});
  const indexAt = event => {
    const box = hit.getBoundingClientRect();
    const t = start + (event.clientX - box.left) / box.width * span;
    const found = steps.findIndex(s => s.t + 600 > t);
    return found < 0 ? steps.length - 1 : found;
  };
  let dragging = false;
  hit.addEventListener("pointerdown", event => { dragging = true; hit.setPointerCapture(event.pointerId); selectStep(indexAt(event)); });
  hit.addEventListener("pointerup", () => { dragging = false; });
  hit.addEventListener("mousemove", event => {
    const i = indexAt(event);
    if (dragging) selectStep(i);
    const a = one.stappen[i], b = many.stappen[i];
    if (!a || !b) return;
    cursor.setAttribute("x1", px(a.t + 300)); cursor.setAttribute("x2", px(a.t + 300)); cursor.setAttribute("visibility", "visible");
    const clock = new Date(a.t * 1000).toLocaleTimeString("nl-NL", {hour: "2-digit", minute: "2-digit", timeZone: "Europe/Amsterdam"});
    const active = s => s.stack.filter(x => x > 0).length, down = s => s.uit.filter(Boolean).length;
    showTip(event, `<b>${clock}</b> · aanbod ${nf(a.aanbod)} MW
      <div class="row">${swatch(COLORS.one)} 1 module: ${nf(a.verbruik)} MW, ${active(a) ? "aan" : "uit"}${down(a) ? " (onderhoud of storing)" : ""}</div>
      <div class="row">${swatch(COLORS.many)} ${n} modules: ${nf(b.verbruik)} MW, ${active(b)} aan${down(b) ? `, ${down(b)} in onderhoud of storing` : ""}</div>`);
  });
  hit.addEventListener("mouseleave", () => { hideTip(); cursor.setAttribute("visibility", "hidden"); });
  const dots = el("g", {class: "pick-dots"});
  svg.insertBefore(pick, svg.querySelector("polyline"));
  svg.append(dots, cursor, hit);
  $("day-chart").replaceChildren(svg);
  day.marker = i => {
    const a = one.stappen[i], b = many.stappen[i];
    pick.replaceChildren(el("rect", {x: px(a.t), y: T, width: Math.max(2, px(a.t + 600) - px(a.t)), height: B - T, class: "pick-band"}));
    dots.replaceChildren(
      el("circle", {cx: px(a.t + 300), cy: py(a.verbruik), r: 5, fill: COLORS.one, stroke: "#fff", "stroke-width": 2}),
      el("circle", {cx: px(b.t + 300), cy: py(b.verbruik), r: 5, fill: COLORS.many, stroke: "#fff", "stroke-width": 2}));
  };
  $("day-legend").innerHTML = `<span><span class="key wash"></span> Windaanbod</span>
    <span>${swatch(COLORS.one)} Verbruik met 1 module</span><span>${swatch(COLORS.many)} Verbruik met ${n} modules</span>
    <span><span class="key dash"></span> Startdrempel: ${nf(big)} MW voor 1 module, ${nf(small)} MW per module bij ${n}</span>`;
  const used = cfg => cfg.stappen.reduce((s, x) => s + x.verbruik / 6, 0);
  const supply = steps.reduce((s, x) => s + x.aanbod / 6, 0);
  $("day-summary").textContent = `${new Date(data.datum + "T12:00:00").toLocaleDateString("nl-NL", {weekday: "long", day: "numeric", month: "long", year: "numeric"})}: `
    + `aanbod ${nf(supply, 0)} MWh. Met 1 module ${nf(used(one), 0)} MWh benut en ${nf(one.waterstof_kg / 1000)} ton waterstof; `
    + `met ${n} modules ${nf(used(many), 0)} MWh en ${nf(many.waterstof_kg / 1000)} ton.`;
}

async function post(url, body) {
  const response = await fetch(url, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)});
  const data = await response.json().catch(() => ({error: "Onverwacht antwoord van de server."}));
  if (!response.ok) throw new Error(data.error || "Aanvraag mislukt.");
  return data;
}

async function runDay() {
  const n = Number($("day-count").value);
  const v = values();
  $("day-status").innerHTML = '<span class="spinner"></span>Dag berekenen…';
  $("day-status").classList.remove("error");
  try {
    const data = await post("/api/opsplitsing/dag", {aannames: v, strategie: selection().strategie, datum: $("day").value, modules: [1, n]});
    dayChart(data, n, v);
    Object.assign(day, {data, n, v});
    const slider = $("step");
    slider.max = String(data.wind.length - 1);
    selectStep(interestingStep(data, n));
    $("day-status").textContent = "";
  } catch (error) {
    $("day-status").textContent = error.message;
    $("day-status").classList.add("error");
  }
}

async function submit(event) {
  event.preventDefault();
  if (running) return;
  const inputs = [...document.querySelectorAll(".field input")];
  const bad = inputs.filter(input => !validate(input));
  const pick = selection();
  const status = $("status");
  status.classList.remove("error");
  if (bad.length) {
    status.textContent = `Controleer ${bad.length === 1 ? "het rood gemarkeerde veld" : bad.length + " rood gemarkeerde velden"}.`;
    status.classList.add("error");
    // Een dichte categorie verbergt het rode veld; open die eerst.
    for (const input of bad) input.closest("details.group").open = true;
    summarise();
    bad[0].focus();
    return;
  }
  if (!pick.jaren.length || !pick.modules.length) {
    status.textContent = "Kies minstens één windjaar en één moduleaantal.";
    status.classList.add("error");
    return;
  }
  running = true;
  $("run").disabled = true;
  const began = performance.now();
  status.innerHTML = '<span class="spinner"></span>Rekenen… De eerste keer haalt de server de windjaren bij KNMI op; daarna komen ze uit de lokale opslag.';
  try {
    const result = await post("/api/opsplitsing", {aannames: values(), ...pick});
    render(result);
    status.textContent = `Klaar in ${nf((performance.now() - began) / 1000)} s.`;
    $("results").scrollIntoView({behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
  } catch (error) {
    status.textContent = error.message;
    status.classList.add("error");
  } finally {
    running = false;
    $("run").disabled = false;
  }
}

async function start() {
  try {
    const response = await fetch("/api/opsplitsing/aannames");
    if (!response.ok) throw new Error();
    meta = await response.json();
  } catch {
    $("status").textContent = "Start de Python-server (python3 -m windprofiel.server) en open deze pagina via http://127.0.0.1:8000/opsplitsing.";
    $("status").classList.add("error");
    return;
  }
  buildForm(load());
  drawExplainers();
  renderSpeed(null);
  $("form").addEventListener("submit", submit);
  $("form").addEventListener("change", remember);
  $("reset").addEventListener("click", () => {
    buildForm({...selection(), technologie: tech, aannames: {}});
    remember();
    drawExplainers();
  });
  $("day-run").addEventListener("click", runDay);
  $("step").addEventListener("input", event => selectStep(Number(event.target.value)));
  $("day-count").addEventListener("change", runDay);
  addEventListener("scroll", hideTip, {passive: true});
}

start();

// ---------------------------------------------------------------- rekenvoorbeeld van één moment

const clockOf = t => new Date(t * 1000).toLocaleTimeString("nl-NL", {hour: "2-digit", minute: "2-digit", timeZone: "Europe/Amsterdam"});
const cfg = (data, n) => data.configuraties[n] || data.configuraties[String(n)];

// Begin bij een moment waarop één module stilstaat en meerdere modules wel draaien: daar zit het verschil.
function interestingStep(data, n) {
  const one = cfg(data, 1).stappen, many = cfg(data, n).stappen;
  const gaps = one.map((s, i) => ({i, gap: many[i].kg.reduce((a, b) => a + b, 0) - s.kg.reduce((a, b) => a + b, 0)}));
  const off = gaps.filter(g => one[g.i].verbruik === 0 && g.gap > 0);
  return (off.length ? off[Math.floor(off.length / 2)] : gaps.reduce((a, b) => b.gap > a.gap ? b : a)).i;
}

function selectStep(i) {
  if (!day.data) return;
  day.index = Math.max(0, Math.min(day.data.wind.length - 1, i));
  $("step").value = String(day.index);
  $("step-time").textContent = `${clockOf(cfg(day.data, 1).stappen[day.index].t)}–${clockOf(cfg(day.data, 1).stappen[day.index].t + 600)}`;
  day.marker?.(day.index);
  renderWalk();
}

function moduleBars(step, size, color) {
  const n = step.stack.length, W = 260, gap = 4, w = Math.min(40, (W - gap * (n - 1)) / n), H = 46;
  const svg = el("svg", {viewBox: `0 0 ${W} ${H + 14}`, class: "module-bars", "aria-hidden": "true"});
  step.stack.forEach((x, i) => {
    const left = i * (w + gap), fill = x / size;
    svg.append(el("rect", {x: left, y: 0, width: w, height: H, fill: step.uit[i] ? "#EFECE6" : "#fff", stroke: "#bcc8d2"}));
    if (step.uit[i]) svg.append(el("line", {x1: left, y1: H, x2: left + w, y2: 0, stroke: COLORS.muted}));
    if (fill > 0) svg.append(el("rect", {x: left + 1, y: H - fill * (H - 2) - 1, width: w - 2, height: fill * (H - 2), fill: color, "fill-opacity": step.opstart_min[i] ? .45 : 1}));
    if (n <= 16) svg.append(text(left + w / 2, H + 12, step.uit[i] ? "uit" : nf(fill * 100, 0) + "%", {"text-anchor": "middle", "font-size": 9}));
  });
  return svg;
}

function windSpark(data, index) {
  const W = 260, H = 70, T = 6, B = 62;
  const series = Object.keys(data.stations);
  const top = niceTop(Math.max(...data.wind.flatMap(w => series.map(p => w[p].v10)), 1));
  const px = i => i / (data.wind.length - 1) * W, py = v => B - v / top * (B - T);
  const svg = el("svg", {viewBox: `0 0 ${W} ${H}`, class: "spark", "aria-hidden": "true"});
  svg.append(el("line", {x1: 0, x2: W, y1: B, y2: B, class: "axis"}));
  series.forEach((park, k) => {
    const color = k ? COLORS.many : COLORS.one;
    svg.append(el("polyline", {points: data.wind.map((w, i) => `${px(i).toFixed(1)},${py(w[park].v10).toFixed(1)}`).join(" "), fill: "none", stroke: color, "stroke-width": 2, "stroke-linejoin": "round"}),
      el("circle", {cx: px(index), cy: py(data.wind[index][park].v10), r: 4.5, fill: color, stroke: "#fff", "stroke-width": 2}));
  });
  svg.append(el("line", {x1: px(index), x2: px(index), y1: T, y2: B, stroke: COLORS.ink, "stroke-width": 1}));
  return svg;
}

function renderWalk() {
  const {data, n, v, index} = day;
  const wind = data.wind[index];
  const one = cfg(data, 1), many = cfg(data, n);
  const a = one.stappen[index], b = many.stappen[index];
  const share = data.aandeel_fryslan;
  const parks = Object.keys(data.stations);
  const sumKg = s => s.kg.reduce((x, y) => x + y, 0);
  const kWh = (x, size) => x > 0 ? (x * (1 + v.bop_variabel / 100) + v.bop_vast / 100 * size) * 1000 / 6 : 0;

  const card = (letter, title, body) => {
    const li = document.createElement("li");
    li.innerHTML = `<span class="flow-n">${letter}</span><h4>${title}</h4>`;
    for (const part of [].concat(body)) typeof part === "string" ? li.insertAdjacentHTML("beforeend", part) : li.append(part);
    return li;
  };
  const windLine = park => {
    const w = wind[park];
    return `<p class="calc"><b>${data.parken[park]}</b><br>${nf(w.v10)} × (${w.ashoogte}/10)<sup>${nf(w.alpha, 3)}</sup> = <b>${nf(w.v_as)} m/s</b> op ${w.ashoogte} m<br>
      − ${nf(w.zog * 100, 0)} % zog = ${nf(w.v_turbine)} m/s → ${nf(w.turbine_kw, 0)} kW per turbine<br>
      × ${w.turbines} turbines = <b>${nf(w.mw)} MW</b></p>`;
  };
  const deploy = (config, step, color, count) => {
    const size = config.module_mw;
    const active = step.stack.filter(x => x > 0).length;
    const reason = step.redenen.length ? `<br><span class="why">${step.redenen.join("; ")}</span>` : "";
    const verdict = active ? `${active} van ${count} ${active === 1 ? "draait" : "draaien"} op ${nf(step.stack.find(x => x > 0) / size * 100, 0)} % last` : "Staat stil";
    const box = document.createElement("div");
    box.className = "deploy";
    box.innerHTML = `<p class="calc"><b>${label(count)} van ${nf(size)} MW</b><br>Startdrempel ${nf(config.drempel_mw)} MW per module
      (${nf(v.minimumlast, 0)} % last + BoP). Er passen er ${step.passen}; de besturing kiest ${step.gewenst}${step.gewenst < step.passen && selection().strategie === "verdelen" ? ", omdat dat de meeste waterstof geeft" : ""}. ${verdict}.${reason}</p>`;
    box.append(moduleBars(step, size, color));
    return box;
  };
  const produce = (config, step, count) => {
    const size = config.module_mw;
    const lines = step.stack.map((x, i) => ({x, kg: step.kg[i], start: step.opstart_min[i]})).filter(m => m.x > 0);
    if (!lines.length) return `<p class="calc"><b>${label(count)}</b>: geen productie.</p>`;
    const m = lines[0];
    const spec = m.kg ? kWh(m.x, size) / m.kg : null;
    const startNote = lines.some(l => l.start) ? ` Opstarten kost ${nf(Math.max(...lines.map(l => l.start)), 0)} min productie.` : "";
    const many = lines.length > 1;
    return `<p class="calc"><b>${label(count)}</b>${many ? `, per module` : ""}<br>${nf(m.x)} MW stack + BoP, 10 min = ${nf(kWh(m.x, size), 0)} kWh
      ${spec ? `<br>÷ ${nf(spec, 1)} kWh/kg bij ${nf(m.x / size * 100, 0)} % last = <b>${nf(m.kg)} kg</b>` : "<br>Nog aan het opstarten: 0 kg"}${many ? `<br>× ${lines.length} modules = <b>${nf(sumKg(step))} kg</b>` : ""}.${startNote}</p>`;
  };
  const year = lastResult && (() => {
    const rowOf = k => lastResult.rijen.find(r => r.modules === k);
    const r1 = rowOf(1), rn = rowOf(n);
    return r1 && rn ? `<p class="calc">Een jaar heeft ${nf(52560, 0)} van zulke stappen. Gemiddeld over de windjaren:
      <b>${nf(r1.waterstof_t, 0)} t</b> met 1 module, <b>${nf(rn.waterstof_t, 0)} t</b> met ${n}. Kosten per kilo
      ${nf(r1.lcoh_eur_kg, 2)} en ${nf(rn.lcoh_eur_kg, 2)} € (stap 3).</p>` : "";
  })();

  const legend = `<p class="legend small">${parks.map((p, k) => `<span>${swatch(k ? COLORS.many : COLORS.one)} ${data.stations[p]}</span>`).join("")}</p>`;
  $("walk").replaceChildren(
    card("A", "KNMI-wind op 10 m", [legend, windSpark(data, index),
      `<p class="calc">${parks.map(p => `${data.stations[p]} <b>${nf(wind[p].v10)} m/s</b>`).join(" · ")}<br>Tienminutengemiddelde van het KNMI.</p>`]),
    card("B", "Wind op ashoogte en parkvermogen", parks.map(windLine)),
    card("C", "Aanbod voor de elektrolyser", `<p class="calc">${nf(share, 1)} × ${nf(wind.fryslan.mw)} + ${nf(wind.beabuorren.mw)}<br><b class="big">= ${nf(a.aanbod)} MW</b></p>
      <p class="note">10 % van Windpark Fryslân plus heel Beabuorren, zoals op mijnwindpark.nl.</p>`),
    card("D", "Modules inzetten", [deploy(one, a, COLORS.one, 1), deploy(many, b, COLORS.many, n)]),
    card("E", "Waterstof in deze tien minuten", [produce(one, a, 1), produce(many, b, n)]),
    card("F", "Optellen", `<p class="calc">Dit moment: <b>${nf(sumKg(a))} kg</b> met 1 module, <b>${nf(sumKg(b))} kg</b> met ${n}.</p>
      <p class="calc">De hele dag, ${nf(data.wind.length, 0)} stappen: <b>${nf(one.waterstof_kg / 1000, 2)} t</b> en <b>${nf(many.waterstof_kg / 1000, 2)} t</b>.</p>${year}`),
  );
}

// ---------------------------------------------------------------- hoe kan dit zo snel?

function renderSpeed(result) {
  const years = result ? result.jaren.length : selection().jaren.length || meta.jaren.length;
  const counts = result ? result.rijen.map(r => r.modules) : (selection().modules.length ? selection().modules : meta.modules);
  const steps = result?.omvang?.tijdstappen ?? years * 52560;
  const modules = counts.reduce((a, b) => a + b, 0);
  const total = steps * modules;
  const cores = result?.omvang?.processen;
  const timing = !result ? "Nog niet berekend."
    : result.uit_cache ? `Laatste berekening: ${nf(result.rekentijd_s, 2)} s, uit de cache. De eerste keer kostte ${nf(result.eerste_rekentijd_s, 1)} s.`
    : `Laatste berekening: ${nf(result.rekentijd_s, 1)} s, nieuw uitgerekend.`;
  $("speed-body").innerHTML = `
    <div class="sum">
      <div><strong>${nf(years, 0)}</strong><span>windjaren</span></div><i>×</i>
      <div><strong>${nf(steps / years, 0)}</strong><span>tijdstappen van 10 min per jaar, met meting</span></div><i>×</i>
      <div><strong>${nf(modules, 0)}</strong><span>modules in ${counts.length} configuraties</span></div><i>=</i>
      <div class="total"><strong>${nf(total / 1e6, 1)} mln</strong><span>keer: één module, één moment</span></div>
    </div>
    <p>Per module en per moment is het rekenwerk klein: aanbod verdelen, minimumlast controleren, kilo's uitrekenen en
      slijtage optellen. Dat zijn een paar tientallen rekenstappen; een computer doet er honderden miljoenen per seconde.</p>
    <ul class="reasons">
      <li><b>Wind één keer ophalen.</b> Elk windjaar komt in één KNMI-aanvraag binnen en wordt als aanbod bewaard.</li>
      <li><b>Keuzes onthouden.</b> Hoeveel modules het beste draaien bij een bepaald aanbod, wordt één keer uitgerekend en daarna opgezocht.</li>
      <li><b>Werk verdelen.</b> Elke combinatie van windjaar en configuratie is een losse taak, verdeeld over ${cores ? cores : "alle"} processorkernen.</li>
      <li><b>Uitkomsten bewaren.</b> Dezelfde aannames nog eens? Dan komt de uitkomst direct uit de cache.</li>
    </ul>
    <p class="note">${timing}</p>`;
}

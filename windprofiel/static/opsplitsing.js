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
  wrap.innerHTML = `<label for="${id}">${item.label}${item.eenheid ? ` <span class="unit">(${item.eenheid})</span>` : ""}</label>
    <input id="${id}" inputmode="decimal" autocomplete="off" data-key="${item.key}">
    <small><span class="source ${SOURCE_CLASS[item.bron]}">${item.bron}</span> ${item.uitleg ? item.uitleg + " " : ""}<span class="default">Standaard ${meta.technologieen[tech].naam}: ${nf(base, decimals(base))}.</span></small>`;
  const input = wrap.querySelector("input");
  input.value = show(value);
  input.addEventListener("input", () => { validate(input); remember(); drawExplainers(); });
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
  $("groups").replaceChildren(...meta.groepen.map(group => {
    const set = document.createElement("fieldset");
    set.innerHTML = `<legend>${group.naam}</legend>`;
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
      remember(); drawExplainers();
    });
    set.append(reset);
    for (const entry of group.velden) set.append(field(entry, state.aannames?.[entry.key] ?? standard(entry.key)));
    return set;
  }));
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

function table(rows) {
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
  lineWithRange("lcoh-chart", rows, "lcoh_eur_kg", "€/kg", 2);
  stepChart(rows);
  table(rows);
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
  const hit = el("rect", {x: L, y: T, width: W - L - R, height: B - T, class: "hit"});
  hit.addEventListener("mousemove", event => {
    const box = hit.getBoundingClientRect();
    const t = start + (event.clientX - box.left) / box.width * span;
    const found = steps.findIndex(s => s.t + 600 > t);
    const i = found < 0 ? steps.length - 1 : found;
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
  svg.append(cursor, hit);
  $("day-chart").replaceChildren(svg);
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
  $("form").addEventListener("submit", submit);
  $("form").addEventListener("change", remember);
  $("reset").addEventListener("click", () => {
    buildForm({...selection(), technologie: tech, aannames: {}});
    remember();
    drawExplainers();
  });
  $("day-run").addEventListener("click", runDay);
  $("day-count").addEventListener("change", runDay);
  addEventListener("scroll", hideTip, {passive: true});
}

start();

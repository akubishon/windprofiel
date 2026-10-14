"use strict";

// ---------------------------------------------------------------------------
// Algemene hulpmiddelen
// ---------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);
const ids = ["fryslan", "beabuorren"];
const preview = window.WINDPROFIEL_PREVIEW;
const format = (v, digits = 1) => new Intl.NumberFormat("nl-NL", {maximumFractionDigits: digits}).format(v);

let current = null;   // laatst geladen profiel
let sequence = 0;     // voorkomt dat een trager, ouder antwoord een nieuwer overschrijft
let busy = false;
// Gekozen tijdvak als minuutindexen (inclusief), gedeeld door alle vermogensgrafieken.
let selection = null;
let bands = [];

// Nederlandse notatie in beeld (dd-mm-jjjj); intern blijft de datum ISO (jjjj-mm-dd).
function nlDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-");
  return `${d}-${m}-${y}`;
}

function nlMoment(timestamp) {
  return `${nlDate(timestamp)} ${timestamp.slice(11, 16)}`;
}

function parseNlDate(text) {
  const match = text.trim().match(/^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$/);
  if (!match) return null;
  const iso = `${match[3]}-${match[2].padStart(2, "0")}-${match[1].padStart(2, "0")}`;
  const check = new Date(iso + "T12:00:00Z");
  return !isNaN(check) && check.toISOString().slice(0, 10) === iso ? iso : null;
}

function today() {
  return new Intl.DateTimeFormat("sv-SE", {timeZone: "Europe/Amsterdam"}).format(new Date());
}

function invalidDateMessage() {
  return `Kies een geldige datum (dd-mm-jjjj) van 01-11-2021 tot en met ${nlDate(today())}.`;
}

// ---------------------------------------------------------------------------
// Grafieken
// ---------------------------------------------------------------------------

const svgNS = "http://www.w3.org/2000/svg";

function svgElement(tag, attrs = {}, text) {
  const el = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
  if (text !== undefined) el.textContent = text;
  return el;
}

function chart(container, values, stamps, unit, emptyMessage, colour = "#32876c", points = [], selectable = false) {
  container.replaceChildren();
  const valid = values.filter(v => v !== null);
  if (!valid.length) {
    const text = document.createElement("div");
    text.className = "empty";
    text.textContent = emptyMessage;
    container.append(text);
    return;
  }

  const W = 1000, H = 230, left = 53, right = 14, top = 22, bottom = 30;
  const max = Math.max(1, ...valid) * 1.12;
  const x = i => left + i * (W - left - right) / Math.max(1, values.length - 1);
  const y = v => H - bottom - v * (H - top - bottom) / max;
  const svg = svgElement("svg", {viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": `Dagprofiel in ${unit}`});

  // Assen: vijf horizontale lijnen en zeven tijdlabels.
  for (let i = 0; i <= 4; i++) {
    const v = max * i / 4;
    svg.append(svgElement("line", {x1: left, y1: y(v), x2: W - right, y2: y(v), stroke: "#e9eee8"}));
    svg.append(svgElement("text", {x: left - 8, y: y(v) + 4, "text-anchor": "end"}, format(v)));
  }
  svg.append(svgElement("text", {x: left, y: 13}, unit));
  for (let i = 0; i <= 6; i++) {
    const index = Math.round((values.length - 1) * i / 6);
    const anchor = i === 0 ? "start" : i === 6 ? "end" : "middle";
    svg.append(svgElement("text", {x: x(index), y: H - 7, "text-anchor": anchor}, stamps[index].slice(11, 16)));
  }

  if (selectable) {
    const band = svgElement("rect", {y: top, height: H - top - bottom, fill: colour, opacity: 0.13, visibility: "hidden"});
    svg.append(band);
    bands.push({band, x});
  }

  // Lijn per minuut; een gat in de data onderbreekt de lijn.
  let path = "", connected = false;
  values.forEach((v, i) => {
    if (v === null) {
      connected = false;
      return;
    }
    path += `${connected ? "L" : "M"}${x(i).toFixed(2)},${y(v).toFixed(2)} `;
    connected = true;
  });
  svg.append(svgElement("path", {d: path, fill: "none", stroke: colour, "stroke-width": 2, "stroke-linejoin": "round"}));

  // Stippen op de oorspronkelijke tienminutenwaarden.
  const start = Date.parse(stamps[0]);
  const pointLabel = unit === "MW" ? "berekend uit KNMI-tienminutengemiddelde" : "KNMI-tienminutengemiddelde";
  points.forEach(point => {
    const index = (Date.parse(point.timestamp) - start) / 60000;
    if (point.value === null || index < 0 || index > values.length - 1) return;
    const dot = svgElement("circle", {class: "reference-point", cx: x(index), cy: y(point.value), r: 2.6,
                                      fill: "white", stroke: colour, "stroke-width": 1.5});
    dot.append(svgElement("title", {}, `${nlMoment(point.timestamp)} · ${format(point.value, 3)} ${unit} · ${pointLabel}`));
    svg.append(dot);
  });

  // Hover: verticale lijn, stip en waarde rechtsboven.
  const cursor = svgElement("line", {y1: top, y2: H - bottom, stroke: colour, visibility: "hidden"});
  const marker = svgElement("circle", {r: 4, fill: colour, visibility: "hidden"});
  const label = svgElement("text", {x: W - right, y: 13, "text-anchor": "end"});
  svg.append(cursor, marker, label);
  const indexAt = event => {
    const box = svg.getBoundingClientRect();
    const position = (event.clientX - box.left) / box.width * W;
    return Math.max(0, Math.min(values.length - 1, Math.round((position - left) / (W - left - right) * (values.length - 1))));
  };

  // Slepen selecteert een tijdvak; een klik zonder slepen wist de selectie.
  let dragStart = null;
  const range = (a, b) => ({a: Math.min(a, b), b: Math.max(a, b)});
  if (selectable) {
    svg.classList.add("selectable");
    svg.addEventListener("pointerdown", event => {
      if (event.button !== 0) return;
      dragStart = indexAt(event);
      svg.setPointerCapture(event.pointerId);
      setSelection({a: dragStart, b: dragStart});
    });
    svg.addEventListener("pointerup", event => {
      if (dragStart === null) return;
      const index = indexAt(event);
      setSelection(index === dragStart ? null : range(dragStart, index));
      dragStart = null;
    });
    svg.addEventListener("pointercancel", () => {
      dragStart = null;
      setSelection(null);
    });
  }

  svg.addEventListener("pointermove", event => {
    const index = indexAt(event);
    if (dragStart !== null) setSelection(range(dragStart, index));
    cursor.setAttribute("x1", x(index));
    cursor.setAttribute("x2", x(index));
    cursor.setAttribute("visibility", "visible");
    const value = values[index];
    marker.setAttribute("visibility", value === null ? "hidden" : "visible");
    if (value !== null) {
      marker.setAttribute("cx", x(index));
      marker.setAttribute("cy", y(value));
    }
    label.textContent = `${stamps[index].slice(11)} · ${value === null ? "ontbreekt" : `${format(value, 3)} ${unit}`}`;
  });
  svg.addEventListener("pointerleave", () => {
    cursor.setAttribute("visibility", "hidden");
    marker.setAttribute("visibility", "hidden");
    label.textContent = "";
  });
  container.append(svg);
}

// ---------------------------------------------------------------------------
// Opbrengst en selectie
// ---------------------------------------------------------------------------

function ratedMW(id) {
  if (id === "combined") return ratedMW("fryslan") + ratedMW("beabuorren");
  const park = current.parks[id];
  return park.count * park.rated_kw / 1000;
}

function seriesFor(id) {
  return id === "combined" ? current.combined_mw : current.parks[id].power_mw;
}

function setSelection(range) {
  selection = range;
  bands.forEach(({band, x}) => {
    band.setAttribute("visibility", range ? "visible" : "hidden");
    if (range) {
      band.setAttribute("x", x(range.a));
      band.setAttribute("width", Math.max(1, x(range.b) - x(range.a)));
    }
  });
  if (!current) return;
  updateDashboard(range);

  [...ids, "combined"].forEach(id => {
    const box = $(id).querySelector(".range");
    const text = box.querySelector("span");
    box.querySelector("button").hidden = !range;
    if (!range) {
      text.textContent = "Sleep in de grafiek om een tijdvak te selecteren.";
      return;
    }
    const values = seriesFor(id).slice(range.a, range.b + 1);
    // Eindtijd in Nederlandse tijd: begin van de minuut na de selectie, of middernacht.
    const end = current.timestamps[range.b + 1]?.slice(11, 16) ?? "24:00";
    const label = `${current.timestamps[range.a].slice(11, 16)}–${end} (${format(values.length / 60, 2)} u)`;
    if (values.includes(null)) {
      text.textContent = `Selectie ${label}: opbrengst onbekend door ontbrekende data.`;
      return;
    }
    const energy = values.reduce((sum, v) => sum + v, 0) / 60;
    text.textContent = `Selectie ${label}: ${format(energy)} MWh · ${format(energy / ratedMW(id), 2)} vollasturen`
      + ` · gemiddeld ${format(energy / (values.length / 60))} MW`;
  });
}

// ---------------------------------------------------------------------------
// Productieoverzicht: dag (of vandaag tot nu) of de gekozen selectie
// ---------------------------------------------------------------------------

function energyText(mwh) {
  return mwh >= 1000 ? `${format(mwh / 1000, 2)} GWh` : `${format(mwh)} MWh`;
}

// Opbrengst, gemiddeld vermogen en piek over een tijdvak; ontbrekende data maakt de opbrengst onbekend.
function periodStats(id, range) {
  const series = seriesFor(id);
  let first = 0, last = series.length - 1, energy;
  if (range) {
    [first, last] = [range.a, range.b];
    const values = series.slice(first, last + 1);
    energy = values.includes(null) ? null : values.reduce((sum, v) => sum + v, 0) / 60;
  } else {
    const source = id === "combined" ? current : current.parks[id];
    energy = id === "combined" ? current.combined_energy_mwh : source.energy_mwh;
    const until = id === "combined" ? current.combined_energy_until : source.energy_until;
    if (until) last = current.timestamps.indexOf(until);
  }
  let peak = null, peakAt = null;
  for (let i = first; i <= last; i++) {
    if (series[i] !== null && (peak === null || series[i] > peak)) {
      peak = series[i];
      peakAt = current.timestamps[i];
    }
  }
  const hours = (last - first + 1) / 60;
  const mean = energy === null ? null : energy / hours;
  return {energy, hours, mean, peak, peakAt, factor: mean === null ? null : mean / ratedMW(id)};
}

function periodLabel(range) {
  if (range) {
    const end = current.timestamps[range.b + 1]?.slice(11, 16) ?? "24:00";
    return `Selectie ${current.timestamps[range.a].slice(11, 16)}–${end} · ${nlDate(current.date)}`;
  }
  const until = current.combined_energy_until;
  return until ? `Vandaag tot ${until.slice(11, 16)}` : `Hele dag · ${nlDate(current.date)}`;
}

function updateDashboard(range) {
  const tiles = $("dashboard").querySelectorAll(".tile");
  if (!current) {
    $("dashboard-period").textContent = "";
    tiles.forEach(tile => {
      tile.querySelector(".tile-value").textContent = "—";
      tile.querySelector(".meter span").style.width = "0";
      tile.querySelectorAll("dd").forEach(dd => dd.textContent = "—");
    });
    return;
  }
  $("dashboard-period").textContent = periodLabel(range);
  tiles.forEach(tile => {
    const id = tile.dataset.park;
    const stats = periodStats(id, range);
    const facts = Object.fromEntries([...tile.querySelectorAll("dd")].map(dd => [dd.dataset.fact, dd]));
    tile.querySelector(".tile-value").textContent = stats.energy === null ? "onbekend" : energyText(stats.energy);
    tile.querySelector(".meter span").style.width = `${Math.min(100, (stats.factor ?? 0) * 100)}%`;
    facts.hours.textContent = stats.energy === null ? "—" : format(stats.energy / ratedMW(id), 1);
    facts.mean.textContent = stats.mean === null ? "—" : `${format(stats.mean)} MW`;
    facts.peak.textContent = stats.peak === null ? "—" : `${format(stats.peak)} MW om ${stats.peakAt.slice(11, 16)}`;
    facts.factor.textContent = stats.factor === null ? "—" : `${format(stats.factor * 100, 0)} %`;
  });
}

function showEnergy(element, energy, id, until = null) {
  element.replaceChildren(document.createTextNode(energy === null ? "—" : `${format(energy)} MWh`));
  const small = document.createElement("small");
  const label = until ? `GESCHATTE OPBRENGST TOT ${until.slice(11, 16)}` : "GESCHATTE DAGOPBRENGST";
  small.textContent = energy === null ? label : `${format(energy / ratedMW(id), 1)} VOLLASTUREN · ${label}`;
  element.append(small);
}

// ---------------------------------------------------------------------------
// Gegevens ophalen (Python-server of opgeslagen voorbeeldpagina)
// ---------------------------------------------------------------------------

function controls() {
  $("previous").disabled = busy || $("date").value <= $("date").min;
  $("next").disabled = busy || $("date").value >= $("date").max;
  $("export").disabled = busy || !current;
  $("refresh").disabled = busy;
}

function previewRequest(url, options) {
  if (options.method && options.method !== "GET") {
    throw new Error("Een voorbeeldpagina kan geen curves opslaan. Gebruik daarvoor de Python-webserver.");
  }
  const target = new URL(url, "http://example.invalid");
  const first = Object.values(preview.profiles)[0];
  if (target.pathname === "/api/stations") {
    return {
      stations: ids.map(id => first.parks[id].station),
      parks: Object.fromEntries(ids.map(id => [id, {station: first.parks[id].station.id}])),
    };
  }
  const data = preview.profiles[target.searchParams.get("date")];
  if (!data) {
    const days = Object.keys(preview.profiles).map(nlDate).join(", ");
    throw new Error(`Deze zelfstandige voorbeeldpagina bevat ${days}. Start de Python-server om andere dagen uit KNMI op te halen.`);
  }
  return data;
}

async function request(url, options = {}) {
  if (preview) return previewRequest(url, options);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 25000);
  try {
    // Relatieve paden werken ook wanneer de app onder een URL-prefix staat.
    const response = await fetch(url.replace(/^\//, ""), {...options, signal: controller.signal});
    if (!response.headers.get("Content-Type")?.includes("application/json")) {
      throw new Error("Deze pagina bereikt de Python-API niet. Start python3 -m windprofiel.server vanuit de checkout. "
        + "Een losse HTML-pagina of GitHub Pages voert de KNMI-server niet uit.");
    }
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Ophalen mislukt.");
    return data;
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error("Ophalen duurt langer dan 25 seconden. Controleer de server en KNMI-toegang en probeer opnieuw.");
    }
    if (error instanceof TypeError) {
      throw new Error("De webserver is niet bereikbaar. Start python3 -m windprofiel.server en open de app via die server.");
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

// Eigen hoogte-exponent: leeg = standaard; komma of punt; null bij een ongeldige waarde.
function alphaInput(id) {
  const text = $("alpha-" + id).value.trim();
  if (!text) return "";
  const value = Number(text.replace(",", "."));
  return Number.isFinite(value) && value >= 0 && value <= 0.6 ? String(value) : null;
}

function parameters() {
  const params = new URLSearchParams({date: $("date").value});
  ids.forEach(id => params.set(id, $("station-" + id).value));
  params.set("wake", $("wake").checked ? "1" : "0");
  ids.forEach(id => {
    if (alphaInput(id)) params.set("alpha_" + id, alphaInput(id));
  });
  return params;
}

// ---------------------------------------------------------------------------
// Pagina vullen
// ---------------------------------------------------------------------------

const referencePoints = (points, key) => points.map(point => ({timestamp: point.timestamp, value: point[key]}));

function showPark(id, data) {
  const park = data.parks[id];
  const card = $(id);
  showEnergy(card.querySelector(".energy"), park.energy_mwh, id, park.energy_until);
  const noPower = park.curve
    ? "Vermogen niet beschikbaar: geen bruikbare windmetingen."
    : "Vermogen nog niet beschikbaar: voeg een curve voor de juiste turbine-uitvoering toe.";
  chart(card.querySelector(".plot"), park.power_mw, data.timestamps, "MW", noPower, "#32876c",
        referencePoints(park.reference_points, "power_mw"), true);
  chart(card.querySelector(".windplot"), park.wind_ms, data.timestamps, "m/s op 10 m", "Geen bruikbare windmetingen.", "#749caf",
        referencePoints(park.reference_points, "wind_ms"));
  card.querySelector(".source").textContent =
    `KNMI ${park.station.properties.name} · ${park.missing_wind_minutes} ontbrekende windminuten`;

  const wake = data.wake
    ? `Zogverlies: wind ${format(park.wake_deficit * 100, 0)} % lager voor alle turbines (scenario-aanname).`
    : "Zogverlies uitgeschakeld.";
  const alpha = park.alpha_custom
    ? `Hoogte-exponent: α = ${format(park.alpha, 3)} (eigen waarde; standaard deze dag ${format(park.alpha_default, 3)}).`
    : `Hoogte-exponent deze dag: α = ${format(park.alpha, 3)}.`;
  card.querySelector(".assumptions").textContent = `${park.assumptions} ${alpha} ${wake}`;
  // De standaardwaarde van deze dag staat grijs in het lege veld.
  $("alpha-" + id).placeholder = format(park.alpha_default, 3);
  $("alpha-" + id).classList.toggle("custom", Boolean(park.alpha_custom));

  const source = card.querySelector(".curve-source");
  source.replaceChildren();
  if (!park.curve) {
    source.textContent = "Vermogenscurve ontbreekt; windmetingen zijn wel beschikbaar.";
    return;
  }
  const link = document.createElement("a");
  link.href = park.curve.source;
  link.textContent = park.curve.kind === "cubic_scenario" ? "Natuurkundige achtergrond ↗" : "Curvebron ↗";
  link.target = "_blank";
  link.rel = "noopener";
  source.append(document.createTextNode(park.curve.status + " "), link);
}

function statusText(data) {
  const missing = ids.filter(id => !data.parks[id].curve);
  let text = `${nlDate(data.date)} · ${format(data.minutes, 0)} minuten · Europe/Amsterdam. `;
  text += missing.length ? "Wind opgehaald; vermogen nog onvolledig door ontbrekende curve." : "Profielen berekend.";
  if (preview) text += " Opgeslagen KNMI-voorbeeld; geen live aanvraag.";
  else if (data.date === today()) text += " Vandaag: metingen tot nu; klik Profiel ophalen voor nieuwe metingen.";
  return text;
}

function clearCharts() {
  const charts = $("charts");
  charts.querySelectorAll(".range span").forEach(el => el.textContent = "");
  charts.querySelectorAll(".range button").forEach(el => el.hidden = true);
  charts.querySelectorAll(".plot,.windplot").forEach(el => el.replaceChildren());
  charts.querySelectorAll(".energy").forEach(el => el.textContent = "—");
  updateDashboard(null);
}

async function load() {
  $("date-text").value = $("date").value ? nlDate($("date").value) : "";
  if (!$("date").checkValidity() || !$("date").value) {
    $("status").textContent = invalidDateMessage();
    return;
  }
  if (ids.some(id => alphaInput(id) === null)) {
    $("status").textContent = "Kies een hoogte-exponent α tussen 0 en 0,6 (bijvoorbeeld 0,15), of laat het veld leeg voor de standaard.";
    return;
  }
  const call = ++sequence;
  busy = true;
  current = null;
  controls();
  updateDashboard(null);
  $("status").textContent = "KNMI-metingen ophalen en minuutprofiel berekenen…";
  try {
    const data = await request("/api/profile?" + parameters());
    if (call !== sequence) return;
    current = data;
    bands = [];
    selection = null;
    // Opgeslagen voorbeeldprofielen liggen vast; het vinkje toont hun instelling.
    if (preview) $("wake").checked = Boolean(data.wake);
    ids.forEach(id => showPark(id, data));

    const combined = $("combined");
    showEnergy(combined.querySelector(".energy"), data.combined_energy_mwh, "combined", data.combined_energy_until);
    chart(combined.querySelector(".plot"), data.combined_mw, data.timestamps, "MW",
          "Gecombineerd vermogen vereist een beschikbare curve én winddata voor beide parken.", "#32876c",
          referencePoints(data.combined_reference_points, "power_mw"), true);
    setSelection(null);
    $("method").textContent = data.method;
    $("status").textContent = statusText(data);
  } catch (error) {
    if (call === sequence) {
      $("status").textContent = error.message;
      clearCharts();
    }
  } finally {
    if (call === sequence) {
      busy = false;
      controls();
    }
  }
}

// ---------------------------------------------------------------------------
// CSV-export
// ---------------------------------------------------------------------------

// Zelfde Nederlandse notatie als csv_rows in application.py: dd-mm-jjjj, decimale komma, puntkomma.
function downloadCsv() {
  if (!current) return;
  // Download de getoonde reeksen, zonder opnieuw de API te raadplegen.
  const a = current.parks.fryslan, b = current.parks.beabuorren;
  const repeated = current.minutes > 1440;
  const time = t => nlMoment(t)
    + (repeated && t.slice(11, 13) === "02" ? (t.endsWith("+02:00") ? " zomertijd" : " wintertijd") : "");
  const number = v => v === null ? "" : (v.toFixed(6).replace(/\.?0+$/, "") || "0").replace(".", ",");
  const rows = [["tijd_Europe_Amsterdam", "fryslan_wind_10m_ms", "beabuorren_wind_10m_ms",
                 "fryslan_wind_ashoogte_ms", "beabuorren_wind_ashoogte_ms",
                 "fryslan_geschat_MW", "beabuorren_geschat_MW", "gecombineerd_geschat_MW"]];
  current.timestamps.forEach((t, i) => {
    const values = [a.wind_ms[i], b.wind_ms[i], a.hub_wind_ms[i], b.hub_wind_ms[i],
                    a.power_mw[i], b.power_mw[i], current.combined_mw[i]];
    rows.push([time(t), ...values.map(number)]);
  });
  const blob = new Blob(["﻿" + rows.map(row => row.join(";") + "\r\n").join("")], {type: "text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `windprofiel-${nlDate(current.date)}.csv`;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// ---------------------------------------------------------------------------
// Bediening
// ---------------------------------------------------------------------------

function moveDay(delta) {
  const day = new Date($("date").value + "T12:00:00Z");
  day.setUTCDate(day.getUTCDate() + delta);
  $("date").value = day.toISOString().slice(0, 10);
  load();
}

function typedDate() {
  const iso = parseNlDate($("date-text").value);
  if (!iso || iso < $("date").min || iso > $("date").max) {
    $("status").textContent = invalidDateMessage();
    return;
  }
  $("date").value = iso;
  load();
}

async function uploadCurve(id, event) {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 100000) throw new Error("Curve is groter dan 100 kB.");
    await request("/api/curves/" + id, {method: "POST", headers: {"Content-Type": "application/json"}, body: await file.text()});
    await load();
  } catch (error) {
    $("status").textContent = error.message;
  }
  event.target.value = "";
}

function showPreviewDays() {
  $("preview-notice").hidden = false;
  ids.forEach(id => {
    $("station-" + id).disabled = true;
    $("curve-" + id).disabled = true;
  });
  $("wake").disabled = true;
  ["alpha-fryslan", "alpha-beabuorren", "alpha-reset"].forEach(name => $(name).disabled = true);
  Object.keys(preview.profiles).forEach(day => {
    const button = document.createElement("button");
    button.textContent = nlDate(day);
    button.addEventListener("click", () => {
      $("date").value = day;
      load();
    });
    $("preview-days").append(button);
  });
}

function fillStations(data) {
  const stations = data.stations
    .filter(s => s.geometry?.coordinates?.[1] > 50)
    .sort((a, b) => a.properties.name.localeCompare(b.properties.name));
  ids.forEach(id => {
    const select = $("station-" + id);
    stations.forEach(s => {
      const option = document.createElement("option");
      option.value = s.id;
      option.textContent = `${s.properties.name} (${s.properties.wmoId})`;
      select.append(option);
    });
    select.value = data.parks[id].station;
  });
}

async function init() {
  busy = true;
  controls();
  $("status").textContent = "KNMI-stations laden…";
  try {
    if (location.protocol === "file:" && !preview) {
      throw new Error("Open de zelfstandige index.html in de hoofdmap voor voorbeelden, "
        + "of start python3 -m windprofiel.server voor elke dag vanaf 01-11-2021 tot en met vandaag.");
    }
    if (preview) showPreviewDays();
    fillStations(await request("/api/stations"));
    await load();
  } catch (error) {
    $("status").textContent = error.message;
  } finally {
    busy = false;
    controls();
  }
}

$("date").max = today();
// De webapp opent op vandaag; de zelfstandige voorbeeldpagina op haar eerste opgeslagen dag.
if (!preview) $("date").value = today();

$("previous").addEventListener("click", () => moveDay(-1));
$("next").addEventListener("click", () => moveDay(1));
$("date").addEventListener("change", load);
$("date-text").addEventListener("change", typedDate);
$("calendar").addEventListener("click", () => {
  try {
    $("date").showPicker();
  } catch {
    $("date").focus();
  }
});
$("refresh").addEventListener("click", load);
$("export").addEventListener("click", downloadCsv);
$("wake").addEventListener("change", load);
ids.forEach(id => $("alpha-" + id).addEventListener("change", load));
$("alpha-reset").addEventListener("click", () => {
  ids.forEach(id => $("alpha-" + id).value = "");
  load();
});
$("show-points").addEventListener("change", event => $("charts").classList.toggle("hide-points", !event.target.checked));
$("charts").querySelectorAll(".range button").forEach(button => button.addEventListener("click", () => setSelection(null)));
ids.forEach(id => {
  $("station-" + id).addEventListener("change", load);
  $("curve-" + id).addEventListener("change", event => uploadCurve(id, event));
});

controls();
init();

"""Elektrolyser opsplitsen in modules: simulatie op het eigen windprofiel.

Vraag: levert een 44 MW-elektrolyser in N modules meer waterstof en een lagere
LCOH op dan in minder, grotere modules? De voeding is hetzelfde aandeel als op
mijnwindpark.nl: 10 % van Windpark Fryslân plus Wynpark Beabuorren, uit
KNMI-tienminutenwaarden met het rekenmodel van deze app.

Alle elektrolyser- en kostengetallen in `Aannames` zijn plaatshouders, geen
leveranciers- of literatuurwaarden. Vervang ze door datasheets en offertes;
pas dan zegt de uitkomst iets over jouw installatie.
"""

import argparse
import csv
import json
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from math import floor
from pathlib import Path

from .application import PARKS, ROOT, load_curve, park_power_mw, parse_wind, shear_exponent
from .knmi import KNMIClient, KNMIError, load_env_file

STEP_H = 1 / 6
FRYSLAN_SHARE = 0.10
STRATEGIES = {
    "samen": "Alle modules tegelijk aan of uit, last gelijk verdeeld.",
    "bijschakelen": "Modules één voor één bijschakelen; hooguit één module in deellast.",
    "verdelen": "Per tijdstap het aantal actieve modules dat de meeste waterstof geeft, last gelijk verdeeld.",
}


@dataclass(frozen=True)
class Aannames:
    capaciteit_mw: float = 44.0
    # Elektrolyser per module (plaatshouders; vervang door datasheet)
    minimumlast: float = 0.20          # fractie van modulevermogen
    sec_laag: float = 44.0             # kWh/kg van de stack bij lage last
    sec_vol: float = 50.0              # kWh/kg van de stack bij vollast
    hulpvermogen: float = 0.03         # vaste BoP-last als fractie van modulevermogen, zolang aan
    standby: float = 0.01              # warmhouden als fractie van modulevermogen
    koud_na_uur: float = 4.0           # na zoveel uur uit is een start koud
    opstart_warm_min: float = 5.0      # minuten zonder productie
    opstart_koud_min: float = 45.0
    # Degradatie als equivalente bedrijfsuren (plaatshouders; vervang door leverancier of literatuur)
    eq_uur_warme_start: float = 1.0
    eq_uur_koude_start: float = 5.0
    eq_uur_per_lastcyclus: float = 0.0  # per volledige 0→1→0-lastzwaai
    stack_levensduur_uur: float = 60000.0
    # Kosten (plaatshouders; vervang door offertes per configuratie)
    capex_eur_kw: float = 2000.0       # systeem-CAPEX bij de referentiemodule
    capex_ref_mw: float = 11.0
    capex_schaal: float = 0.85         # kosten ∝ grootte^schaal; < 1 maakt kleine modules duurder per kW
    stack_aandeel: float = 0.35        # stackvervanging als fractie van module-CAPEX
    opex_aandeel: float = 0.02         # vaste OPEX per jaar als fractie van CAPEX
    stroomprijs_eur_mwh: float = 50.0
    rente: float = 0.07
    looptijd_jaar: int = 20


def supply_year(year: int, client: KNMIClient) -> list[float]:
    """Bruto toegewezen windvermogen (MW) per tien minuten; meetgaten vallen weg."""
    start = datetime(year, 1, 1, tzinfo=timezone.utc)
    end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    series = {}
    for park_id, park in PARKS.items():
        samples = parse_wind(client.observations_range(park["station"], start, end), park["station"])
        curve = load_curve(park_id)
        power = {}
        for moment, speed in samples:
            if speed is None or not start <= moment < end:
                continue
            alpha = shear_exponent(park, moment.date())
            power[moment] = park_power_mw(speed * (park["hub_height"] / 10) ** alpha, park_id, curve, wake=True)
        series[park_id] = power
    shared = sorted(series["fryslan"].keys() & series["beabuorren"].keys())
    return [FRYSLAN_SHARE * series["fryslan"][t] + series["beabuorren"][t] for t in shared]


def module_kg_h(x: float, size_mw: float, a: Aannames) -> float:
    """Waterstof per uur van één module bij lastfractie x, inclusief vaste hulplast."""
    if x < a.minimumlast or x <= a.hulpvermogen:
        return 0.0
    return (x - a.hulpvermogen) * size_mw * 1000 / (a.sec_laag + (a.sec_vol - a.sec_laag) * x)


def dispatch(power: float, n: int, size: float, a: Aannames, strategy: str, memo: dict) -> list[float]:
    """Lastfracties voor de actieve modules, hoogste last eerst."""
    minimum = a.minimumlast * size
    if strategy == "samen":
        return [min(1.0, power / (n * size))] * n if power >= n * minimum else []
    if strategy == "bijschakelen":
        full = min(n, floor(power / size))
        rest = power - full * size
        return [1.0] * full + ([rest / size] if full < n and rest >= minimum else [])
    key = round(power, 2)
    if key not in memo:
        best, best_k = 0.0, 0
        for k in range(1, min(n, floor(key / minimum)) + 1 if minimum > 0 else n + 1):
            x = min(1.0, key / (k * size))
            kg = k * module_kg_h(x, size, a)
            if kg > best + 1e-9:
                best, best_k = kg, k
        memo[key] = [min(1.0, key / (best_k * size))] * best_k if best_k else []
    return memo[key]


def simulate(supply: list[float], n: int, a: Aannames, strategy: str) -> dict:
    size = a.capaciteit_mw / n
    off_h = [a.koud_na_uur] * n          # start koud
    startup = [0.0] * n
    load = [0.0] * n
    eq = [0.0] * n
    hours = [0.0] * n
    warm = [0] * n
    cold = [0] * n
    kg = used = standby = 0.0
    memo = {}
    for power in supply:
        targets = dispatch(power, n, size, a, strategy, memo)
        # Draaiende modules eerst, daarna de minst versleten: minder starts en gelijkmatige slijtage.
        order = sorted(range(n), key=lambda i: (load[i] == 0, eq[i]))
        new = [0.0] * n
        for i, x in zip(order, targets):
            new[i] = x
        for i in range(n):
            x = new[i]
            if x > 0:
                if load[i] == 0:
                    if off_h[i] >= a.koud_na_uur:
                        cold[i] += 1; eq[i] += a.eq_uur_koude_start; startup[i] = a.opstart_koud_min
                    else:
                        warm[i] += 1; eq[i] += a.eq_uur_warme_start; startup[i] = a.opstart_warm_min
                productive = max(0.0, 10 - startup[i]) / 10
                startup[i] = max(0.0, startup[i] - 10)
                kg += module_kg_h(x, size, a) * STEP_H * productive
                used += x * size * STEP_H
                eq[i] += STEP_H + abs(x - load[i]) / 2 * a.eq_uur_per_lastcyclus
                hours[i] += STEP_H
                off_h[i] = 0.0
            else:
                if off_h[i] < a.koud_na_uur:
                    standby += a.standby * size * STEP_H
                off_h[i] += STEP_H
            load[i] = x
    scale = 8760 / (len(supply) * STEP_H)   # meetgaten: herschalen naar een vol jaar
    supply_mwh = sum(supply) * STEP_H
    return {
        "modules": n, "module_mw": size, "strategie": strategy,
        "waterstof_t": kg * scale / 1000, "verbruik_mwh": used * scale, "standby_mwh": standby * scale,
        "benutting": used / supply_mwh if supply_mwh else 0.0,
        "bedrijfsuren_gem": sum(hours) / n * scale,
        "starts_warm_per_module": sum(warm) / n * scale, "starts_koud_per_module": sum(cold) / n * scale,
        "eq_uren_per_module": [e * scale for e in eq],
        "dekking_uur": len(supply) * STEP_H,
    }


def economics(result: dict, a: Aannames) -> dict:
    n, size = result["modules"], result["module_mw"]
    module_capex = a.capex_eur_kw * a.capex_ref_mw * 1000 * (size / a.capex_ref_mw) ** a.capex_schaal
    capex = n * module_capex
    crf = a.rente / (1 - (1 + a.rente) ** -a.looptijd_jaar)
    # Continue benadering: elk bedrijfsuur verbruikt een deel van een stack.
    stack = sum(a.stack_aandeel * module_capex * e / a.stack_levensduur_uur for e in result["eq_uren_per_module"])
    power = (result["verbruik_mwh"] + result["standby_mwh"]) * a.stroomprijs_eur_mwh
    annual = capex * crf + a.opex_aandeel * capex + stack + power
    kg = result["waterstof_t"] * 1000
    return {"capex_meur": capex / 1e6, "stack_meur_jaar": stack / 1e6, "kosten_meur_jaar": annual / 1e6,
            "lcoh_eur_kg": annual / kg if kg else None,
            "jaren_tot_stackwissel": min(a.stack_levensduur_uur / e for e in result["eq_uren_per_module"] if e) if any(result["eq_uren_per_module"]) else None}


def average(runs: list[dict]) -> dict:
    """Gemiddelde over windjaren; per jaar is al naar een vol jaar herschaald."""
    out = dict(runs[0])
    for key, value in runs[0].items():
        if key == "eq_uren_per_module":
            out[key] = [sum(r[key][i] for r in runs) / len(runs) for i in range(len(value))]
        elif isinstance(value, float):
            out[key] = sum(r[key] for r in runs) / len(runs)
    return out


def table(supplies: dict[int, list[float]], counts: list[int], a: Aannames, strategy: str) -> list[dict]:
    rows = []
    for n in counts:
        result = average([simulate(s, n, a, strategy) for s in supplies.values()])
        rows.append({**result, **economics(result, a)})
    crf = a.rente / (1 - (1 + a.rente) ** -a.looptijd_jaar)
    single = rows[0]
    previous = None
    for row in rows:
        # Hoogste CAPEX waarbij deze configuratie dezelfde LCOH haalt als de eerste (meestal één module):
        # het getal waaraan offertes te toetsen zijn, los van de aangenomen kostenschaal.
        wear = sum(row["eq_uren_per_module"]) / row["modules"] / a.stack_levensduur_uur
        power = (row["verbruik_mwh"] + row["standby_mwh"]) * a.stroomprijs_eur_mwh
        target = single["lcoh_eur_kg"] * row["waterstof_t"] * 1000
        row["capex_break_even_meur"] = (target - power) / (crf + a.opex_aandeel + a.stack_aandeel * wear) / 1e6
        # Marginaal: wat de stap naar meer modules extra kost en oplevert.
        if previous:
            row["extra_waterstof_t"] = row["waterstof_t"] - previous["waterstof_t"]
            row["extra_kosten_meur_jaar"] = row["kosten_meur_jaar"] - previous["kosten_meur_jaar"]
        previous = row
    return rows


CSV_FIELDS = ["scenario", "strategie", "modules", "module_mw", "waterstof_t", "benutting", "bedrijfsuren_gem",
              "starts_warm_per_module", "starts_koud_per_module", "jaren_tot_stackwissel", "capex_meur",
              "stack_meur_jaar", "kosten_meur_jaar", "lcoh_eur_kg", "capex_break_even_meur", "extra_waterstof_t",
              "extra_kosten_meur_jaar"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Simuleer een elektrolyser in N modules op het windprofiel.")
    parser.add_argument("--jaren", type=int, nargs="+", default=[2022, 2023, 2024, 2025])
    parser.add_argument("--modules", type=int, nargs="+", default=[1, 2, 4, 6, 8, 11, 16])
    parser.add_argument("--uit", type=Path, default=ROOT / "uitvoer" / "opsplitsing")
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    try:
        client = KNMIClient(ROOT / ".cache" / "knmi")
        supplies = {year: supply_year(year, client) for year in args.jaren}
    except KNMIError as exc:
        print(str(exc))
        return 1
    base = Aannames()
    scenarios = {"basis": ({}, list(STRATEGIES)),
                 "minimumlast 10 %": ({"minimumlast": 0.10}, ["verdelen"]),
                 "minimumlast 40 %": ({"minimumlast": 0.40}, ["verdelen"]),
                 "CAPEX -25 %": ({"capex_eur_kw": base.capex_eur_kw * 0.75}, ["verdelen"]),
                 "CAPEX +25 %": ({"capex_eur_kw": base.capex_eur_kw * 1.25}, ["verdelen"])}
    scenarios.update({f"windjaar {y}": ({}, ["verdelen"]) for y in args.jaren})
    rows = []
    for name, (changes, strategies) in scenarios.items():
        a = replace(base, **changes)
        data = {int(name[-4:]): supplies[int(name[-4:])]} if name.startswith("windjaar") else supplies
        for strategy in strategies:
            for row in table(data, args.modules, a, strategy):
                rows.append({"scenario": name, **row})
    args.uit.mkdir(parents=True, exist_ok=True)
    with (args.uit / "resultaten.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    meta = {"jaren": args.jaren, "dekking_uur": {y: len(s) * STEP_H for y, s in supplies.items()},
            "aanbod_mwh_per_jaar": {y: sum(s) * STEP_H * 8760 / (len(s) * STEP_H) for y, s in supplies.items()},
            "aannames": asdict(base), "strategieen": STRATEGIES}
    (args.uit / "resultaten.json").write_text(json.dumps({"meta": meta, "rijen": rows}, indent=1), encoding="utf-8")
    for row in rows:
        if row["scenario"] == "basis" or row["modules"] in (1, 4, 11):
            print(f'{row["scenario"]:18} {row["strategie"]:12} N={row["modules"]:2} '
                  f'H2 {row["waterstof_t"]:7.1f} t  LCOH {row["lcoh_eur_kg"]:5.2f} €/kg  '
                  f'starts/mod {row["starts_warm_per_module"] + row["starts_koud_per_module"]:5.0f}  '
                  f'CAPEX {row["capex_meur"]:5.1f} (max {row["capex_break_even_meur"]:5.1f}) M€  '
                  f'stackwissel {row["jaren_tot_stackwissel"]:4.1f} j')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

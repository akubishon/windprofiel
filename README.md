# Windprofiel

Lokale webapp die per dag het geschatte vermogen toont van **Windpark Fryslân**,
**Wynpark Beabuorren** en beide samen, berekend uit KNMI-windmetingen. Kies een
dag van 1 november 2021 (Windpark Fryslân volledig in bedrijf) tot en met
vandaag. Het is een indicatief model, geen gemeten productie.

## Snel bekijken

Open [index.html](index.html) in de hoofdmap. Dat is een zelfstandige pagina met
drie opgeslagen KNMI-dagen (15-01-2025, 30-03-2025 en 26-10-2025); er is geen
server of API-sleutel nodig. Voor andere dagen, stations of curves start je de
webapp hieronder. (`windprofiel/static/index.html` is alleen de template van de server.)

## Webapp starten

Vereist Python 3.12 of nieuwer; er zijn geen externe pakketten nodig.

1. Zet je KNMI EDR API-sleutel in de omgeving als `KNMI_EDR_API_KEY`, of lokaal in
   `.env`: `cp .env.example .env` en vul de sleutel in. `.env` staat in `.gitignore`;
   een ingestelde omgevingsvariabele gaat voor.
2. Start de server:

   ```sh
   python3 -m windprofiel.server --port 8000
   ```

3. Open <http://127.0.0.1:8000>. De server luistert alleen lokaal en houdt de
   sleutel buiten de browser.

## Gebruik

- De app opent op vandaag. Datums staan als dd-mm-jjjj; typ bijvoorbeeld
  `11-10-2026`, gebruik ← en → of de kalenderknop.
- **Vandaag** toont de metingen tot nu (KNMI loopt ongeveer een kwartier achter);
  de opbrengst geldt dan tot het laatste meetmoment. **Profiel ophalen** haalt
  nieuwe metingen op.
- **Geschatte productie** bovenaan toont per park en samen de opbrengst,
  vollasturen, gemiddeld vermogen, piek en benutting (gemiddeld vermogen gedeeld
  door het nominale vermogen), voor de hele dag of voor de gekozen selectie.
- Per park staan dagopbrengst en vollasturen. **Sleep** in een vermogensgrafiek
  om een tijdvak te selecteren; klik zonder slepen of op **Wis selectie** om terug te gaan.
- **Hoogte-exponent α**: vul per park een eigen α in (0 tot 0,6, komma of punt)
  om te zien wat dat met wind en vermogen doet; leeg laten of **Standaard** geeft
  de geijkte waarde, die grijs in het veld staat. Ook via de API: `alpha_fryslan=0.25`.
- Onder **Meetstations en vermogenscurves** kies je een ander KNMI-station of
  upload je een eigen curve (zie [Curve-formaat](#curve-formaat)).
- **Download CSV** geeft de minuutreeksen in Nederlandse notatie voor Excel:
  puntkomma, decimale komma en tijden als `11-10-2026 13:05`. In het dubbele uur
  bij de wintertijdwissel staat `zomertijd` of `wintertijd` erachter. Ontbrekend
  vermogen blijft leeg.

## Model in het kort

| | Windpark Fryslân | Wynpark Beabuorren |
| --- | --- | --- |
| Turbines | 89 × 4,3 MW (382,7 MW) | 8 × 1,3 MW (10,4 MW) |
| KNMI-station | Houtribdijk | Stavoren |
| Ashoogte | 115 m | 60 m |
| Hoogte-exponent α | 0,18 (winter) tot 0,05 (zomer), geijkt op productie | 0,20 (aanname) |
| Vermogenscurve | kubisch scenario: 3 / 11,5 / 25 m/s | secundaire gepubliceerde curve |
| Zogverlies | 5 % minder wind | 2 % minder wind |

Wind op ashoogte: `v_h = v_10 × (h / 10)^α`. De tienminutengemiddelden van KNMI
worden lineair naar minuten geïnterpoleerd; meetgaten blijven leeg. Zogverlies
staat standaard aan en is uit te zetten met het vinkje (of `wake=0` in de API).

Meer uitleg:

- [Formules en ijking](docs/rekenmodel.md): rekenwijze, aannames en de vergelijking met productiedata.
- [Databronnen](docs/databronnen.md): KNMI-dataset, stations, parkgegevens en hun bronnen.

## Elektrolyser opsplitsen

Open <http://127.0.0.1:8000/opsplitsing> (of de link bovenaan de startpagina). De
pagina rekent door of een elektrolyser van 44 MW beter in één module of in 2 tot 16
gelijke modules kan, op vier volledige windjaren (2022–2025). De voeding is dezelfde
als op mijnwindpark.nl: 10 % van Windpark Fryslân plus heel Wynpark Beabuorren. Windpark
Fryslân krijgt hier per tien minuten de hoogste KNMI-wind van Houtribdijk en Stavoren; die
lijn past beter bij wat het park zelf levert dan één station. Beabuorren houdt Stavoren.

- **Zo werkt de analyse** laat in zes stappen zien hoe de berekening loopt, met een
  schets van de startdrempels, de rendementscurve per module en een uitleg waarom een
  heel jaar per tien minuten in seconden is doorgerekend.
- **Aannames**: kies **PEM** of **Alkaline** voor de standaardwaarden uit de EU
  LCOH-tool (Clean Hydrogen Partnership): CAPEX, energieverbruik, stacklevensduur en
  -degradatie, stackvervanging, OPEX, stroomprijs, netkosten, belasting, rente en
  looptijd. Wat die tool niet geeft, zoals minimumlast (PEM 10 %, alkaline 20 %) en
  opstarttijden, is een plaatshouder. Elk veld toont zijn bron. Alles is aan te passen;
  je wijzigingen blijven in je browser bewaard. De categorieën staan dicht, met een
  samenvatting; de uitleg per veld zit achter ⓘ. Subsidies en opbrengsten (CAPEX-subsidie,
  waterstofpremie, korting op netkosten en belasting, zuurstofverkoop) geven ook de
  netto kosten per kilo.
- **Uitkomst**: knikpunt, extra waterstof en de *maximale CAPEX*: hoeveel een
  configuratie hooguit mag kosten om per kilo niet duurder te zijn dan één module.
  Dat getal hangt niet af van de aangenomen kostenschaal en is het getal om offertes
  aan te toetsen.
- **Een dag van dichtbij** vergelijkt het verbruik van 1 module en N modules per tien minuten.
  Kies een moment in de grafiek: zes kaarten rekenen dat moment met de echte getallen door,
  van KNMI-wind tot kilo's waterstof.

De eerste berekening haalt de vier windjaren één keer bij KNMI op (een paar seconden
per jaar). Het aanbod per jaar en elke uitkomst worden in `.cache/opsplitsing/`
bewaard; daarna komt dezelfde berekening direct uit de cache en kost een nieuwe set
aannames ongeveer tien seconden.

Zonder webpagina, met gevoeligheden voor minimumlast, CAPEX en windjaar:

```sh
python3 -m windprofiel.opsplitsing                              # schrijft uitvoer/opsplitsing/resultaten.csv
python3 -m windprofiel.opsplitsing --technologie alkaline       # standaard: pem
python3 -m windprofiel.opsplitsing --aannames mijn-offerte.json # bijvoorbeeld {"minimumlast": 10, "capex_eur_kw": 1700}
```

Beperkingen: tienminutengemiddelden verbergen kortere schommelingen; de rendementscurve
is lineair met een Faradayterm; degradatie telt starts en lastwisselingen als extra
bedrijfsuren, niet als functie van de last; stackvervanging is een continue benadering.

## Curve-formaat

Een eigen curve is een JSON-bestand met:

- `model`: exact de getoonde turbinenaam;
- `source`: HTTPS-bron-URL;
- `cut_out`: uitschakelsnelheid in m/s;
- `points`: oplopende paren `[m/s, kW]`, beginnend bij nul vermogen, met het
  nominale vermogen en eindigend onder `cut_out`;
- optioneel `status`: tekst over bron en beperkingen.

Een geüploade curve gaat voor op het standaardmodel. De controle van het formaat
is geen certificering van de bron.

## Projectindeling

| Pad | Inhoud |
| --- | --- |
| `windprofiel/knmi.py` | KNMI EDR-client met cache |
| `windprofiel/profile.py` | dagminuten, curves en kubisch model |
| `windprofiel/application.py` | parkgegevens, profielberekening en CSV |
| `windprofiel/server.py` | lokale webserver en API |
| `windprofiel/opsplitsing.py` | simulatie elektrolyser in N modules, met cache |
| `windprofiel/preview.py` | maakt de zelfstandige `index.html` |
| `windprofiel/static/` | pagina's, JavaScript, CSS en lettertype (TASA Orbiter, SIL OFL) |
| `windprofiel/data/` | curve van Beabuorren |
| `tests/` | unit-tests zonder netwerk |
| `docs/` | rekenmodel en databronnen |

Lokale bestanden onder `.cache/` (KNMI-antwoorden, geüploade curves, windaanbod en
uitkomsten van de opsplitsing) en `.env`
gaan niet mee in Git. Dagen van de laatste 24 uur worden niet gecachet, zodat
ze nieuwe metingen krijgen.

## Controle en onderhoud

```sh
python3 -m unittest discover -s tests -v   # unit-tests, zonder netwerk of sleutel
python3 -m windprofiel.knmi                # controleert echte KNMI-toegang
node --check windprofiel/static/app.js     # JavaScript-syntax
node --check windprofiel/static/opsplitsing.js
```

Na wijzigingen aan de webapp maak je de zelfstandige pagina opnieuw (met
KNMI-toegang):

```sh
python3 -m windprofiel.preview
python3 -m windprofiel.preview --dates 2025-06-01 2025-06-02 --output voorbeeld.html
```

De HTML bevat winddata en modeluitkomsten, nooit de API-sleutel.

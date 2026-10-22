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
- **Kosten**: de CAPEX volgt uit een referentieofferte (standaard 60 M€ voor 50 MW in
  10 units van 5 MW) als prijs per kW plus vaste kosten per module (gelijkrichter,
  transformator, besturing). Stackwissels kosten stilstand (standaard 4 weken per wissel).
- **Uitkomst**: knikpunt, extra waterstof en per aantal modules de *maximale vaste kosten
  per module*: tot welk bedrag per unit opsplitsen per kilo goedkoper blijft dan één
  module. Dat is het getal om offertes aan te toetsen.
- **Waarom wint of verliest N modules?** Kies een aantal modules: het verschil in kosten per
  kilo met één module wordt exact uitgesplitst in meer waterstof, duurdere installatie,
  stroom per kilo en stackvervanging. Een tornadografiek toont welke aanname dat verschil
  het sterkst verschuift (elke aanname 25 % lager en hoger). Loont opsplitsen ook gratis
  niet, dan staat er "loont niet" in plaats van een negatief bedrag.
- **Laagste berekende kostprijs, stap voor stap**: per volgende gekozen configuratie wat de extra kilo's kosten,
  naast de gemiddelde kosten per kilo ervoor. De stapgrafiek blijft zichtbaar, met daarnaast de
  LCOH op drie decimalen, de verandering in cent/kg en het verschil met de laagste doorgerekende kostprijs.
  Een daling tegenover de vorige configuratie betekent niet automatisch de laagste totale kostprijs.
  De open stappentabel behoudt extra tonnen, productie-uren, jaarkosten en LCOH vóór en na elke stap.
  De **omslagkaart** toont het goedkoopste aantal bij elke combinatie van minimumlast
  (10–50 %) en vaste kosten per module (0–1,5 M€).
- **Scenario "Hoge minimumlast en lage modulekosten"**: alkaline met 40 % minimumlast en 0,3 M€ vaste
  kosten per module. Met de standaardwaarden wint bijna altijd 2: bij 10–20 % minimumlast
  vangt één grote module de zwakke wind al grotendeels, en 1 M€ per extra unit is veel.
  Met een hoge minimumlast staat één module van 44 MW onder ~18 MW stil, terwijl een
  module van 11 MW al vanaf ~4,5 MW draait. Windjaar 2025, `verdelen`:

  | Scenario | Goedkoopst | LCOH 1 module → goedkoopst |
  |---|---|---|
  | PEM standaard | 2 modules | 8,11 → 8,07 €/kg |
  | Alkaline standaard (20 %) | 2 modules | 8,01 → 7,95 €/kg |
  | Alkaline, 40 % minimumlast | 3 modules | 8,39 → 8,07 €/kg |
  | Alkaline, 40 %, 0,3 M€ per module | **4 modules** | 8,65 → 8,21 €/kg |

  In het laatste scenario wordt met 4 modules 6255 uur per jaar waterstof gemaakt, tegen
  3468 uur met 1 module.
- **Een dag van dichtbij** vergelijkt het verbruik van 1 module en N modules per tien minuten.
  Kies een moment in de grafiek of met de tijdschuif en vorige/volgende. De productie van beide
  configuraties staat bij de grafiek. Daarnaast tonen zes compacte rekenstappen hun kernwaarden;
  alle formules blijven per stap en via ‘Alle rekenstappen tonen’ beschikbaar. De geopende stappen
  blijven open wanneer het tijdstip verandert. De gewone tekst en tabellen zijn groter en er staan
  maximaal twee grote resultaatgrafieken per rij.

De eerste berekening haalt de vier windjaren één keer bij KNMI op (een paar seconden
per jaar). Het aanbod per jaar en elke uitkomst worden in `.cache/opsplitsing/`
bewaard; daarna komt dezelfde berekening direct uit de cache en kost een nieuwe set
aannames ongeveer tien seconden.

Zonder webpagina, met gevoeligheden voor minimumlast, CAPEX en windjaar:

```sh
python3 -m windprofiel.opsplitsing                              # schrijft uitvoer/opsplitsing/resultaten.csv
python3 -m windprofiel.opsplitsing --technologie alkaline       # standaard: pem
python3 -m windprofiel.opsplitsing --aannames mijn-offerte.json # bijvoorbeeld {"minimumlast": 10, "vaste_kosten_module_meur": 0.5}
```

### Berekeningsbasis en controleerbare export

De uitkomst toont de gebruikte aannames en hun herkomst, windjaren, gelijk totaalvermogen en één vaste, herhaalbare storingstrekking per module en windjaar. Jaarspreiding is geen betrouwbaarheidsinterval; meerdere storingstrekkingen zijn niet als onzekerheidsband berekend. De markering ‘laagste berekend’ geldt binnen de getoonde instellingen en geselecteerde configuraties.

De CSV-download bewaart alle oorspronkelijke rijvelden, ongeronde stapverschillen en aannames in rekeneenheden (puntkomma's en kommawaarden). Contextkolommen beginnen met `berekening.`, verschillen met `stap.` en aannames met `aanname.`. JSON bevat ook de volledige jaaruitkomsten en veldmetadata. Geen of negatieve extra productie krijgt geen misleidende prijs per extra kilo; negatieve kosten en productieverschillen blijven zichtbaar. Extra decimalen zijn voor controle, niet een maat voor voorspellingszekerheid.

Vervolgdiagrammen, gevoeligheid en dagvoorbeelden gebruiken de aannames van de getoonde berekening, ook na wijzigingen in het formulier. Een melding geeft aan wanneer de invoer nog niet is herberekend. De Pythonberekeningen en standaardwaarden blijven gelijk.

### Alle moduleaantallen in bulk doorrekenen en op de pagina tonen

`windprofiel.scenarios` rekent elk moduleaantal in een bereik door en bewaart de uitkomst als
JSON in `scenarios/`, plus alles onder elkaar in `scenarios/overzicht.csv`. Op de
opsplitsingspagina staan ze onder **Opgeslagen scenario's**; **Toon** laat de volledige
uitkomst zien zonder opnieuw te rekenen en zet de aannames in het formulier.

```sh
python3 -m windprofiel.scenarios                    # 3 technologieën × 3 besturingen, 1–16 modules, alle windjaren
python3 -m windprofiel.scenarios --technologie alkaline_hoog --strategie verdelen --jaren 2025 --modules 1-44
python3 -m windprofiel.scenarios --modules 1-6,8,10,12 --aannames mijn-offerte.json --naam "Offerte X"
python3 -m windprofiel.scenarios --lijst            # wat er is opgeslagen
python3 -m windprofiel.scenarios --verwijder offerte-x-pem-verdelen
```

Dezelfde naam opnieuw draaien overschrijft het scenario. Een rekening die al in
`.cache/opsplitsing/` staat, komt direct uit de cache. Met 4 processen duurt 1–16 modules voor
één windjaar ongeveer 13 s; grote aantallen duren langer, omdat elke module per tien minuten
wordt gevolgd (44 modules: ongeveer 10 s per windjaar voor die ene configuratie). `scenarios/` staat in `.gitignore`; haal die
regel weg als je de uitkomsten wilt meecommitten.

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
| `windprofiel/ijking.py` | toetst de hoogte-exponent van Fryslân op opgeslagen productiedata |
| `windprofiel/preview.py` | maakt de zelfstandige `index.html` |
| `windprofiel/static/` | pagina's, JavaScript, CSS en lettertype (TASA Orbiter, SIL OFL) |
| `windprofiel/data/` | curve van Beabuorren, dagproductie Windpark Fryslân 2022–2025 |
| `tests/` | unit-tests zonder netwerk |
| `docs/` | rekenmodel en databronnen |

Lokale bestanden onder `.cache/` (KNMI-antwoorden, geüploade curves, windaanbod en
uitkomsten van de opsplitsing) en `.env`
gaan niet mee in Git. Dagen van de laatste 24 uur worden niet gecachet, zodat
ze nieuwe metingen krijgen.

## Controle en onderhoud

```sh
python3 -m unittest discover -s tests -v   # unit-tests, zonder netwerk of sleutel
node --test tests/opsplitsing-presentation.test.mjs  # presentatie en exports (Node.js 18+)
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

## Website (Fryslân production explorer)

De broncode van de gehoste website staat in `src/`, `worker/`, `scripts/` en
`package.json` (Node.js 22+). Zie [README-website.md](README-website.md) voor
starten, bouwen en configuratie; de Node-tests draaien met `npm test`.

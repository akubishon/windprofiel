# Databronnen

Waar de gegevens vandaan komen en hoe betrouwbaar ze zijn. De rekenwijze staat in
[rekenmodel.md](rekenmodel.md); welke keuzes vroeger op productie waren afgesteld in
[afhankelijkheden.md](afhankelijkheden.md).

Drie soorten gegevens blijven gescheiden:

| Soort | Bron | Gebruik |
| --- | --- | --- |
| Waarneming | KNMI-stations, tienminutengemiddelden | Wind op 10 m, de invoer van beide rekenroutes |
| Model | KNMI WINS50 (HARMONIE-heranalyse), KNMI HARMONIE-voorspellingen | Hoogtevertaling (WINS50); voorspellingen alleen op de website |
| Gemeten productie | App van Windpark Fryslân, dagtotalen | Alleen vergelijking en weergave, nooit invoer |

## KNMI-windmetingen

| | |
| --- | --- |
| Dataset | `10-minute-in-situ-meteorological-observations`, versie 1.0 |
| Toegang | KNMI EDR API, `https://api.dataplatform.knmi.nl/edr/v1/collections/10-minute-in-situ-meteorological-observations` |
| Variabele | `ff`: tienminutengemiddelde windsnelheid in m/s, volgens KNMI ‘representatief voor 10 meter’ (`dd` is de windrichting) |
| Archief | vanaf 2012; vandaag tot ongeveer een kwartier geleden |

Primaire bronnen:
[dataset en metadata](https://dataplatform.knmi.nl/dataset/10-minute-in-situ-meteorological-observations-1-0),
[technische documentatie](https://dataplatform.knmi.nl/dataset/docs/10-minute-in-situ-meteorological-observations-1-0),
[API-toegang](https://dataplatform.knmi.nl/dataset/access/10-minute-in-situ-meteorological-observations-1-0),
[EDR-gebruik en sleutelaanvraag](https://developer.dataplatform.knmi.nl/edr-api) en de
[OpenAPI-specificatie](https://tyk-cdn.dataplatform.knmi.nl/edr/v1/openapi.json).

De EDR API is gekozen omdat die per station, variabele en tijdvak gericht kan
opvragen, zonder honderden bestanden per dag te downloaden. Stations komen uit
`/locations`; metingen uit `/locations/{id}` met `datetime` en `parameter-name`.

**Hoogte van de meting.** KNMI levert naast `ff` ook `ffs`, de wind op sensorhoogte. `ff` is
door KNMI omgerekend naar een hoogte van 10 m (EDR-metadata: `eumetnet:level` 10). Het model
gebruikt `ff`. Houtribdijk staat op de dijk, 7,25 m boven zeeniveau (EDR `/locations`); de
10 m van dat station ligt dus hoger boven het water dan 10 m boven het IJsselmeer. Dat
verschil zit in de vertaalfactor F, die stationswind rechtstreeks koppelt aan de modelwind
op ashoogte boven het park (zie [rekenmodel](rekenmodel.md#1-wind-op-ashoogte)).

**Verwerking:**

- De tijdstempel markeert het **einde** van het tienminuteninterval (UTC). Elk gemiddelde
  staat op het intervalmidden (vijf minuten eerder). De dagopbrengst telt de intervallen met
  hun midden in de Nederlandse kalenderdag op; de minuutlijn in de grafiek is lineair
  geïnterpoleerd. Aan beide kanten van de dag wordt tien minuten extra opgevraagd.
- Negatieve, niet-eindige en ontbrekende waarden tellen als ontbrekend. Er is geen
  extrapolatie, geen interpolatie over gaten en geen invulling met een ander station.
- Een ontbrekend tienminuteninterval maakt de dagopbrengst onbekend. Alleen voor vandaag
  telt de opbrengst tot het laatste meetmoment; een gat eerder op de dag maakt ook die onbekend.
- Windstoten (`fx`, `gff`) worden niet gebruikt.
- Een Nederlandse kalenderdag heeft 144 tienminutenintervallen, of 138 en 150 bij de klokwissel.

**Sleutel, quotum en cache:** de client leest `KNMI_EDR_API_KEY` uit de omgeving (of `.env`),
stuurt die alleen naar `api.dataplatform.knmi.nl` en volgt geen redirects. Een eigen sleutel
vraag je aan via de [KNMI API Catalog](https://developer.dataplatform.knmi.nl/apis/). De sleutel
heeft een quotum van [1.000 aanvragen per uur](https://developer.dataplatform.knmi.nl/edr-api);
daarboven antwoordt KNMI met HTTP 403 ‘Quota exceeded’. Antwoorden worden bewaard onder `.cache/knmi` en `.cache/wins50`, zonder
sleutel; HTTP-fouten en dagen van de laatste 24 uur worden niet gecachet. Controleer de
toegang met `python3 -m windprofiel.knmi`.

## WINS50: HARMONIE-wind op hoogte (2019–2021)

| | |
| --- | --- |
| Dataset | KNMI WINS50, EDR-collectie `wins50` (dataset [`wins50_ctl_nl_daily_3d`](https://dataplatform.knmi.nl/dataset/wins50-ctl-nl-daily-3d-2)) |
| Model | HARMONIE-AROME Cy43, 2,5 km, genest in ERA5; run **zonder windparken** (ongestoorde wind) |
| Hoogtes | 10, 20, 40, 60, 80, 100, 120, 140, 150, 160, 180, 200, 220, 250, 300, 500 en 600 m boven het oppervlak |
| Tijd | uurwaarden, 1 januari 2019 tot en met 31 december 2021 |
| Gebruikt | `wspeed` op 10, 60, 100 en 120 m, in `windprofiel/data/wins50_punten.csv.gz` |

[WINS50](https://www.wins50.nl/data/) is een modelheranalyse, geen meting. Het is de enige
HARMONIE-bron met wind op hoogte over een periode van jaren; daarom bepaalt die bron de
hoogtevertaling (`python3 -m windprofiel.wins50`, daarna `python3 -m windprofiel.ashoogte`).
De EDR-cube staat per aanvraag hooguit 100 hoogte × uur-waarden toe; vier hoogtes × 24 uur is één
aanvraag per dag, 1.096 voor de drie jaren. Locaties in het bestand:

| Locatie | Roosterpunten |
| --- | --- |
| Windpark Fryslân | Alle punten binnen 4 km van 53,010° N 5,290° E (zeven punten), gemiddeld |
| Wynpark Beabuorren | Dichtstbijzijnde punt bij 53,052° N 5,493° E |
| Houtribdijk, Stavoren | Dichtstbijzijnde punt bij het station |

## HARMONIE-voorspellingen

De HARMONIE-voorspellingen waar de website mee werkt, staan in de websitecode
(`src/harmonie.mjs`, `scripts/update-harmonie.mjs`), niet in het Python-pakket.

| | P1 (deterministisch) | P2b (ensemble) |
| --- | --- | --- |
| Bron | KNMI Open Data, `harmonie_arome_cy43_p1` 1.0 | KNMI Open Data, `harmonie_arome_cy43_p2b` |
| Bestanden | `HARM43_V1_P1_JJJJMMDDUU.tar`, elk uur een run, ca. 0,9–1,0 GB, 61 uur vooruit | idem met `_P2B_` |
| Archief bij KNMI | Eerste run 7 januari 2026 22 UTC (gecontroleerd 22 oktober 2026) | Runs ouder dan 72 uur worden door de website geweigerd |
| Wind in de bestanden | u en v op 10, 50, 100, 200 en 300 m boven het oppervlak (GRIB1 tabel 253, parameters 33/34, niveautype 105); ook temperatuur op 2, 50, 100, 200 en 300 m | niet apart gecontroleerd |
| Opslag website | R2: `harmonie/v1/{model}/{run}.json`, twee roosterpunten, alleen 10 m | idem |
| Sleutel | `KNMI_OPEN_DATA_API_KEY` (niet de EDR-sleutel) | idem |

De website haalt alleen wind op **10 m** uit de bestanden en past daarop de oude, op productie
geijkte seizoens-α toe. De hogere niveaus (100 en 200 m omsluiten 115 m) worden niet bewaard.
Het roosterpunt voor Fryslân ligt op 53,017° N 5,367° E, ongeveer 5 km oostelijker dan het
geschatte midden van het park (zie [Locatie](#locatie-van-het-park)).

### Overlap met de productiegegevens

| Bron | Periode | Overlap met dagproductie 2022–2025 |
| --- | --- | --- |
| KNMI-stations | 2012 – nu | volledig |
| WINS50 | 2019 – 2021 | geen |
| HARMONIE P1-archief | 7 januari 2026 – nu | geen |
| HARMONIE-snapshots website | oktober 2026 – nu | geen |
| Dagproductie (`productie_fryslan.csv`) | 2022 – 2025 | — |

Er is dus geen HARMONIE-profiel voor de dagen waarvan productie is opgeslagen. Voor de
vergelijking met productie komt de wind daarom altijd van de KNMI-stations; HARMONIE (WINS50)
bepaalt alleen de vertaling naar ashoogte. Voorspellingen worden in geen enkele rekenroute als
waarneming gebruikt. Vanaf 2026 overlappen het P1-archief en de uurproductie in de app van
Windpark Fryslân wel; daar zou een volgende controle kunnen beginnen.

## Locatie van het park

Het inpassingsplan beschrijft het park als ‘in het IJsselmeer nabij de Afsluitdijk op een
afstand van circa 6,5 kilometer van de Friese kust … en reikt vanaf de Afsluitdijk circa 7,7
kilometer het IJsselmeer in’, tussen Breezanddijk en Kornwerderzand. Wikipedia geeft
53°00′ N 5°16′ E. Het midden voor WINS50 is daarom geschat op 53,010° N 5,290° E, met een
onzekerheid van enkele kilometers; boven open water verandert de modelwind over die afstand
weinig. Turbineposities zijn niet opgehaald (OpenStreetMap was vanuit deze omgeving niet bereikbaar).

## Ashoogte en verticale referentie

| Bron | Gegeven | Ashoogte |
| --- | --- | --- |
| [Windpark Fryslân, windturbines](https://www.windparkfryslan.nl/onderwerpen/windturbines/) | ‘De hoogte van een windturbine boven water is 180 meter.’ | 180 − 130/2 = **115 m boven water** |
| [Factsheet](https://www.windparkfryslan.nl/wp-content/uploads/2020/05/Factsheet-Windpark-Fryslan.pdf) (2020) | Tekening: 180 m, 130 m rotor, 65 m blad, 28 m onder de bodem | 115 m (de ‘115 meter’ in de factsheet is de Achmeatoren) |
| [Rijksinpassingsplan](https://www.ruimtelijkeplannen.nl/documents/NL.IMRO.0000.EZip15wpfryslan-3000/t_NL.IMRO.0000.EZip15wpfryslan-3000.pdf) (2016) | Ashoogte 95–120 m en tip ≤ 182,8 m, ‘gemeten vanaf N.A.P.’; IJsselmeerpeil −0,2 m (zomer) en −0,4 m (winter) | binnen de bandbreedte |
| [NS Energy](https://www.nsenergybusiness.com/projects/fryslan-wind-farm-friesland-netherlands) (2018, vóór de bouw) | 109 m ashoogte, 174 m tiphoogte, waterdiepte 3–6 m | 109 m |

115 m is de ashoogte boven het wateroppervlak; NAP en waterpeil verschillen hooguit 0,4 m.
WINS50-hoogtes zijn hoogtes boven het oppervlak, boven het park dus boven water: dezelfde
referentie. De 109 m uit 2018 is een eerdere, geplande waarde; die zit in de gevoeligheidsanalyse.

## Stations

Standaard krijgen beide parken per tien minuten het **gemiddelde van Houtribdijk en Stavoren**,
alleen als beide meten. De regel is vooraf gesteld: stations op het IJsselmeer zelf, hetzelfde
wateroppervlak als Windpark Fryslân. De vergelijking met WINS50 (2019–2021, uurwaarden,
kruisvalidatie per jaar, maandfactor) ondersteunt die keuze:

<!-- STATIONSTABEL -->

| Station | Coördinaten | Hoogte (EDR) | Afstand tot Fryslân | Ligging |
| --- | --- | ---: | ---: | --- |
| Houtribdijk (`0-20000-0-06258`) | 52,648° N 5,401° E | 7,25 m | 41 km | Dijk midden in IJsselmeer en Markermeer: vrijwel alle richtingen open water |
| Stavoren (`0-20000-0-06267`) | 52,897° N 5,383° E | −1,3 m | 13 km | Friese IJsselmeerkust: west en zuid water, oost land |

Meer stations tegelijk verlagen de fout tegenover WINS50 verder, ook met stations aan de Noordzee
of Waddenzee. Een deel daarvan is middeling: een gemiddelde van verre stations is gladder, net als
een modelveld van 2,5 km en net als de totale opbrengst van een park van 35 km². Stations buiten
het IJsselmeer vallen buiten de regel en zijn niet gebruikt. Stavoren alleen en Houtribdijk alleen
staan in de [gevoeligheidsanalyse](vergelijking.md).

De oude keuzes (Houtribdijk voor het dagprofiel, de hoogste van beide voor de opsplitsing) waren
gemaakt door te vergelijken met productie; zie [afhankelijkheden](afhankelijkheden.md). In de
webapp is per park één ander station te kiezen; dan geldt dat station alleen, met zijn eigen
WINS50-factor als die bekend is en anders alleen de hoogtetoename op de parklocatie.

## Productiedata Windpark Fryslân

`windprofiel/data/productie_fryslan.csv` bevat de dagproductie van Windpark Fryslân van
1 januari 2022 tot en met 31 december 2025 (1.461 dagen, kolommen `datum` en `productie_kwh`).
De waarden komen uit de app van Windpark Fryslân, opgehaald in oktober 2026 met
`scripts/fetch-graph.cjs` uit de repository `windpark-fryslan` (één aanvraag per maand). Het is
gemeten productie; waarden zijn afgerond op hele MWh. Zes dagen staan op 0 (21 september 2022,
17 tot en met 20 augustus 2024 en 19 januari 2025); de oorzaak is niet bekend.

**Tijdzone.** De datums zijn Nederlandse kalenderdagen. Gecontroleerd door de modelenergie per dag
op vier manieren in te delen en te correleren met de productie: Europe/Amsterdam geeft de hoogste
correlatie, UTC-dagen iets lager, een dag verschoven veel lager (zie [vergelijking](vergelijking.md)).
Uit dagtotalen wordt geen tienminutenproductie afgeleid.

Gebruik: alleen `productie.py` leest dit bestand, voor de dagvergelijking (`vergelijking.py`),
de weergave naast het dagprofiel en de oude ijking (`ijking.py`). Wind en modelopbrengst hangen
er niet van af; `tests/test_productie_onafhankelijk.py` controleert dat.

## Windpark Fryslân

- **89 turbines van 4,3 MW, 382,7 MW**: [exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/).
- **Ashoogte 115 m boven water**: zie [Ashoogte en verticale referentie](#ashoogte-en-verticale-referentie).
- **Turbinetype Siemens Gamesa SWT-DD-130**: volgens [Wikipedia](https://en.wikipedia.org/wiki/Windpark_Frysl%C3%A2n);
  de daar gelinkte fabrikantpagina werkt niet meer.
- **Geen gepubliceerde vermogenscurve**: de [turbinedatabase](https://en.wind-turbine-models.com/turbines/1898-siemens-gamesa-swt-dd-130)
  heeft er geen. Daarom gebruikt het model een kubisch scenario met gekozen
  grenzen (3 / 11,5 / 25 m/s); een curve van een ander 130-metermodel is bewust
  niet gebruikt.

## Wynpark Beabuorren

- **8 turbines, 10,4 MW sinds 2007**: [Rengineers](https://rengineers.eu/nieuw/wynpark-beaborren-25-jaar/).
- **Siemens SWT-1.3-62, locatie 53,052° N, 5,493° E** (Wûnseradiel, nauwkeurig
  gelokaliseerd): [The Wind Power](https://www.thewindpower.net/windfarm_en_6263_beabuorren.php).
  Het eerdere deel met een Bonus B44/600 bij Tjerkwerd is ontmanteld.
- **Ashoogte 60 m**: uit [lokaal nieuws van januari 2007](https://tsjerkwert.nl/start-opschaling-van-het-wynpark/),
  over de toenmalige bouwfase; nog niet bevestigd voor alle acht turbines.
- **Vermogenscurve**: grafiekpunten van [Wind-Turbine-Models](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62),
  met bronvermelding in `windprofiel/data/beabuorren.json`. Dit is een secundaire
  bron; luchtdichtheid en herkomst zijn onbekend. Het punt bij 25 m/s is
  weggelaten, omdat de datasheet daar cut-out noemt.

## Controle

`python3 -m unittest discover -s tests -v` draait de unit-tests met nagebootste
KNMI-antwoorden en synthetische testcurves, zonder netwerk.

<!-- DAGPROFIELEN -->

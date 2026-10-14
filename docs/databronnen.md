# Databronnen

Waar de gegevens vandaan komen en hoe betrouwbaar ze zijn. De rekenwijze en de
ijking op productiedata staan in [rekenmodel.md](rekenmodel.md).

## KNMI-windmetingen

| | |
| --- | --- |
| Dataset | `10-minute-in-situ-meteorological-observations`, versie 1.0 |
| Toegang | KNMI EDR API, `https://api.dataplatform.knmi.nl/edr/v1/collections/10-minute-in-situ-meteorological-observations` |
| Variabele | `ff`: tienminutengemiddelde windsnelheid in m/s, representatief voor 10 m (`dd` is de windrichting) |
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

**Verwerking:**

- De tijdstempel markeert het **einde** van het tienminuteninterval (UTC). De app
  plaatst elk gemiddelde op het intervalmidden (vijf minuten eerder) en
  interpoleert lineair naar minuten. Aan beide kanten van de dag wordt tien
  minuten extra opgevraagd.
- Negatieve, niet-eindige en ontbrekende waarden tellen als ontbrekend. Er is geen
  extrapolatie en geen interpolatie over gaten of intervallen langer dan tien minuten.
- Een ontbrekende minuut maakt de dagopbrengst onbekend. Alleen voor vandaag
  telt de opbrengst tot het laatste meetmoment; een gat eerder op de dag maakt
  ook die onbekend.
- Windstoten (`fx`, `gff`) worden niet gebruikt.
- Een Nederlandse kalenderdag heeft 1.440 minuten, of 1.380 en 1.500 bij de klokwissel.

Het archief is niet handmatig op volledigheid gecontroleerd; elke gekozen dag
wordt afzonderlijk op ontbrekende metingen gecontroleerd.

**Sleutel en cache:** de client leest `KNMI_EDR_API_KEY` uit de omgeving (of
`.env`), stuurt die alleen naar `api.dataplatform.knmi.nl` en volgt geen redirects.
Een eigen sleutel vraag je aan via de [KNMI API Catalog](https://developer.dataplatform.knmi.nl/apis/).
Antwoorden worden bewaard onder `.cache/knmi`, zonder sleutel; HTTP-fouten en dagen
van de laatste 24 uur worden niet gecachet. Controleer de toegang met
`python3 -m windprofiel.knmi`.

WINS50 heeft wind op meerdere hoogtes, maar de versie
[`wins50_ctl_nl_daily_3d/2`](https://dataplatform.knmi.nl/dataset/wins50-ctl-nl-daily-3d-2)
dekt alleen 2019–2021.

## Stations

| Park | Standaardstation | Coördinaten | Afstand | Waarom |
| --- | --- | --- | ---: | --- |
| Fryslân | Houtribdijk (`0-20000-0-06258`) | 52,648° N, 5,401° E | 43 km | Beste aansluiting op productiedata ([rekenmodel, sectie 7](rekenmodel.md#7-ijking-op-productiedata-fryslân)) |
| Beabuorren | Stavoren (`0-20000-0-06267`) | 52,897° N, 5,383° E | 19 km | Dichtstbijzijnde KNMI-station; niet geijkt op productie |

Stavoren ligt dichter bij Windpark Fryslân (17 km), maar meet structureel minder
wind dan het park krijgt. Leeuwarden Airport (`0-20000-0-06270`) ligt op 26 km
van Beabuorren. Er zijn geen metingen in de turbinegondels gebruikt; in de webapp
is per park een ander station te kiezen. Afstand, windrichting en omgeving
bepalen hoe representatief een station is.

## Windpark Fryslân

- **89 turbines van 4,3 MW, 382,7 MW**: [exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/).
- **Ashoogte circa 115 m**: afgeleid uit de [factsheet](https://www.windparkfryslan.nl/wp-content/uploads/2020/05/Factsheet-Windpark-Fryslan.pdf),
  180 m tiphoogte min de helft van 130 m rotordiameter. Nog niet gecontroleerd
  tegen een technische specificatie.
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

Echte EDR-dagprofielen met de standaardstations en zogverlies (modeluitkomsten,
geen gemeten productie):

| Datum | Minuten | Ontbrekende windminuten | Fryslân | Beabuorren | Samen |
| --- | ---: | ---: | ---: | ---: | ---: |
| 15-01-2025 | 1.440 | 0 | 271,0 MWh | 6,0 MWh | 277,0 MWh |
| 30-03-2025 | 1.380 | 0 | 8.802,1 MWh | 238,7 MWh | 9.040,7 MWh |
| 26-10-2025 | 1.500 | 0 | 9.440,3 MWh | 255,2 MWh | 9.695,5 MWh |

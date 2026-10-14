# Databronnen en verificatie

Doel: een kiesbare Nederlandse kalenderdag in 2025, met drie grafieken van
geschat vermogen in MW: Windpark Fryslân, Wynpark Beabuorren en de som.
Op gewone dagen zijn er 1.440 minuutwaarden; tijdens de klokwissel 1.380 of 1.500.

## Wat werkt en wat nog onzeker is

De geregistreerde EDR-sleutel werkt via de beveiligde netwerkbinding. Historische
CoverageJSON-antwoorden, eenheden en stations zijn live gecontroleerd. De webapp
heeft datumkeuze, stationkeuze, caching, interactieve grafieken en CSV-download.

Fryslân gebruikt nu het afgesproken benaderde kubische scenario. Zijn vermogen
en de som worden berekend zodra bruikbare winddata aanwezig is. De exacte
fabrikantcurve ontbreekt nog, maar is niet meer vereist voor dit indicatieve model.
Beabuorren gebruikt een secundaire gepubliceerde curve. De ashoogte voor alle
turbines, ruimtelijke representativiteit, hoogtecorrectie en referentieluchtdichtheid
blijven modelonzekerheden. [Formules en bronnen](rekenmodel.md) onderscheiden
gepubliceerde gegevens van onze expliciete scenario-keuzes.

Data met grovere tijdstappen blijven als zodanig herkenbaar:
interpolatie levert geen echte minuutmetingen. Lange meetgaten mogen niet stilzwijgend
worden gevuld. De modeluitkomst is geen gemeten productie van de parkbeheerder.

## Geverifieerde KNMI-bron (14 oktober 2026)

De netwerkblokkade voor KNMI is opgelost. Primaire bronnen:

- [Dataset en metadata](https://dataplatform.knmi.nl/dataset/10-minute-in-situ-meteorological-observations-1-0).
- [Technische documentatie](https://dataplatform.knmi.nl/dataset/docs/10-minute-in-situ-meteorological-observations-1-0).
- [API-toegang voor deze dataset](https://dataplatform.knmi.nl/dataset/access/10-minute-in-situ-meteorological-observations-1-0).
- [EDR-gebruik en sleutelaanvraag](https://developer.dataplatform.knmi.nl/edr-api).
- [OpenAPI-specificatie](https://tyk-cdn.dataplatform.knmi.nl/edr/v1/openapi.json).

Dataset: `10-minute-in-situ-meteorological-observations`, versie `1.0`.
KNMI beschrijft een historisch archief vanaf 2012-01-01. Dit dekt volgens de
documentatie 2025, maar is niet handmatig gevalideerd en kan onvolledig zijn.
Elke gekozen dag wordt afzonderlijk gecontroleerd op ontbrekende waarnemingen.
De hele jaarreeks is niet in één keer gedownload of op volledigheid getoetst.

Gekozen aansluiting: de **EDR API**, omdat deze stations, variabelen en een
datuminterval gericht kan opvragen zonder honderden bestanden per dag te downloaden.
Basisadres:
`https://api.dataplatform.knmi.nl/edr/v1/collections/10-minute-in-situ-meteorological-observations`.
Met `/locations` worden stations ontdekt; met `/locations/{location_id}` en
`datetime` en `parameter-name` worden hun gegevens opgehaald.
Gebruik station-ID's uit de actuele metadata, geen gegokte identifiers.

Variabele `ff`: tienminutengemiddelde windsnelheid, representatief voor 10 meter,
in **m/s**. `dd`: gemiddelde windrichting, volgens de live metadata op sensorhoogte.
Gebruik geen windstoten (`fx`, `gff`) als gemiddelde windsnelheid.
De tijdstempel in de gegevens markeert het **einde** van het voorafgaande
meetinterval in UTC. De bestandsnaam kan een ander tijdstip gebruiken; interpreteer
de daadwerkelijke gegevenstijdstempels. De applicatie plaatst tienminutengemiddelden
op het intervalmidden (gegevenstijdstempel minus vijf minuten), en interpoleert
lineair tussen die middelpunten. Aan elke dagzijde wordt tien minuten extra
opgevraagd. Negatieve, niet-eindige en ontbrekende windsnelheden worden ontbrekend.
Er is geen extrapolatie en er wordt niet over ontbrekende samples of intervallen
langer dan tien minuten geïnterpoleerd. Een ontbrekende minuut maakt de volledige
dagopbrengst onbekend; er wordt geen gedeeltelijke som als volledige dag getoond.

WINS50 heeft wind op meerdere hoogtes, maar de gecontroleerde versie
`wins50_ctl_nl_daily_3d/2` dekt 2019–2021 en is daarom ongeschikt voor dit projectjaar.
Bron: https://dataplatform.knmi.nl/dataset/wins50-ctl-nl-daily-3d-2.

## Toegang

`KNMI_EDR_API_KEY` is ingesteld als beveiligde netwerkbinding, uitsluitend voor
`api.dataplatform.knmi.nl`, en de daadwerkelijke EDR-aanvragen slagen.
Het metadata-endpoint gaf een archief vanaf 2012 en 77 stations bij deze controle.
Sleutels worden nooit in de repository opgeslagen. Voor een andere omgeving is
een eigen **EDR API**-sleutel nodig, aangevraagd via het
[KNMI API Catalog](https://developer.dataplatform.knmi.nl/apis/).
De eerdere openbare Open Data-sleutel gaf HTTP 429 en is niet in de app opgenomen.
Voor de HARMONIE-test (`windprofiel/harmonie.py`) is een eigen Open Data API-sleutel
`KNMI_OPEN_DATA_API_KEY` gebruikt; die gaat alleen naar de KNMI-API, niet naar de
vooraf ondertekende S3-downloadadressen.

Controleer metadata en stations met:

```sh
cd /workspace/windprofiel
python3 -m windprofiel.knmi
```

De client leest de sleutel uit de omgeving, verstuurt die alleen naar de vaste
KNMI-host en volgt geen redirects. Historische antwoorden kunnen lokaal worden
gecached; HTTP-fouten worden niet gecached. Ruwe antwoorden staan onder `.cache/knmi`
en bevatten geen Authorization-header of sleutel. Cachebestanden zijn niet tracked.

## Stations en hoogtecorrectie

Standaard gebruikt Fryslân **Houtribdijk** (`0-20000-0-06258`, 5.4006° E, 52.6481° N)
als IJsselmeerproxy; dit station sloot het best aan op productiedata (zie
[rekenmodel, sectie 7](rekenmodel.md#7-ijking-op-productiedata-fryslân)). Stavoren
(`0-20000-0-06267`) is dichterbij maar gaf structureel te weinig wind. Beabuorren gebruikt **Leeuwarden Airport** (`0-20000-0-06270`,
5.7517° E, 53.2231° N) als regionale landproxy. Beide identifiers zijn afkomstig
uit de actuele EDR-stationslijst en zijn voor de gecontroleerde dagen bruikbaar.
Er zijn geen KNMI-metingen in de turbinegondels gebruikt. Een andere stationkeuze
is mogelijk in de webapp; afstand, windrichting en lokale omgeving beïnvloeden
de representativiteit. Een geografisch dichtbij station garandeert geen parkmeting.

Aswind wordt geschat met `v_h = v_10 * (h / 10)^alpha`. De exponent voor
Fryslân volgt een seizoensformule (0,18 in de winter, 0,05 in de zomer), geijkt
op zes productiedagen; 0,20 voor land is een scenario-aanname. Geen van beide is een door KNMI gemeten lokaal verticaal profiel. De UI toont deze aannames. De
vermogensberekening interpoleert de curve op de geschatte aswind, vermenigvuldigt
met het turbinaantal en rekent kW om naar MW. Zogverlies is standaard benaderd
met een vaste snelheidsverlaging per park (zie [rekenmodel](rekenmodel.md#5-zogverlies));
beschikbaarheid, afregeling, stormhysterese en luchtdichtheidcorrectie zijn niet gemodelleerd.

## Windparken

**Windpark Fryslân:** de exploitant bevestigt 89 turbines van 4,3 MW, samen
382,7 MW. Bron: https://www.windparkfryslan.nl/onderwerpen/windturbines/.
De genoemde hoogte van 180 meter is de tiphoogte en mag niet als ashoogte
worden gebruikt. De [factsheet van de exploitant](https://www.windparkfryslan.nl/wp-content/uploads/2020/05/Factsheet-Windpark-Fryslan.pdf)
toont een rotordiameter van 130 meter; dit impliceert ongeveer 115 meter ashoogte
boven water (180 minus 65), nog te controleren tegen de technische specificatie.
[Wikipedia](https://en.wikipedia.org/wiki/Windpark_Frysl%C3%A2n) koppelt het park aan
**Siemens Gamesa SWT-DD-130**. De daar gelinkte fabrikantpagina uit 2021 geeft
nu algemene website-inhoud en is daarom niet als primaire bevestiging gebruikt.
De [turbinedatabase](https://en.wind-turbine-models.com/turbines/1898-siemens-gamesa-swt-dd-130)
heeft voor dit model geen vermogenscurve. Een curve voor een ander 130-metermodel
mag niet stilzwijgend worden gebruikt als curve voor deze 4,3 MW-uitvoering.

**Wynpark Beabuorren (Tjerkwerd):** onderhoudsbedrijf Rengineers bevestigt acht
turbines en 10,4 MW sinds 2007:
https://rengineers.eu/nieuw/wynpark-beaborren-25-jaar/.
The Wind Power specificeert acht **Siemens SWT-1.3-62**:
https://www.thewindpower.net/windfarm_en_6263_beabuorren.php.
Een lokaal nieuwsbericht van januari 2007 noemt aanvankelijk zes nieuwe
Siemens 1.3-turbines en 60 meter hoogte:
https://tsjerkwert.nl/start-opschaling-van-het-wynpark/.
Dat is een beschrijving van de toenmalige bouwfase; gebruik deze niet als
actueel turbinaantal. De ashoogte voor alle acht en de curve blijven te bevestigen.
De eerder voorgestelde parkdomeinen zijn niet als officiële bron vastgesteld.

Een [secundaire curve voor SWT-1.3-62](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62)
is gevonden als numerieke gegevens bij de grafiek. Dit is geen officiële
fabrikantcurve; luchtdichtheid en herkomst zijn daar niet voldoende vastgelegd.
De pagina noemt bovendien generieke torenhoogtes van 68/90 meter, die niet
zomaar op Beabuorren mogen worden toegepast. De gepubliceerde grafiekpunten staan
met bronvermelding onder `windprofiel/data/beabuorren.json`. Het curvepunt bij
25 m/s is verwijderd: de datasheet noemt cut-out bij 25 m/s, zodat het vermogen
vanaf die snelheid nul is in dit eenvoudige model. Er wordt nog geen
gecertificeerde of gemeten productie geclaimd.

De rekenbasis heeft geen externe pakketten nodig en gebruikt Python 3.12.
Controle vanuit `/workspace/windprofiel`:

```sh
python3 -m unittest discover -s tests -v
```

Achttien lokale tests slagen. De unit-tests gebruiken nagebootste antwoorden
en synthetische testcurves; die testcurves staan niet in de applicatiedata.
Daarnaast zijn daadwerkelijke EDR-dagprofielen voor beide stations gecontroleerd:

| Datum | Minuten | Ontbrekende windminuten per station | Fryslân (scenario) | Beabuorren (secundaire curve) | Samen |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025-01-15 | 1.440 | 0 | 135,103 MWh | 3,026 MWh | 138,129 MWh |
| 2025-03-30 | 1.380 | 0 | 8.802,100 MWh | 232,728 MWh | 9.034,828 MWh |
| 2025-10-26 | 1.500 | 0 | 9.391,474 MWh | 241,546 MWh | 9.633,020 MWh |

Dit zijn modeluitkomsten, geen bevestigde parkproductie. De eerdere ontbrekende
Fryslân-curve wordt nu vervangen door het expliciet gekozen scenario. Er is geen
curve van een ander turbinemodel gebruikt.

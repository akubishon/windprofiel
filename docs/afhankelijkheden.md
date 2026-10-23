# Afhankelijkheid van productiegegevens

Inventaris van oktober 2026: welke parameters, stationskeuzes en selectieregels in de
rekenroutes zijn afgeleid van gemeten productie van Windpark Fryslân. Een modelwind die
op productie is afgesteld, kan daarna niet meer onafhankelijk met diezelfde productie
worden vergeleken: het verschil tussen model en gemeten productie is dan deels
weggepoetst door de keuze zelf. De vervangende, productie-onafhankelijke methode staat
in [rekenmodel.md](rekenmodel.md#1-wind-op-ashoogte); de vergelijking van oud en nieuw in
[vergelijking.md](vergelijking.md).

## Wat uit productie kwam

| Plaats | Keuze | Waarde | Hoe uit productie | Status nu |
| --- | --- | --- | --- | --- |
| `application.py`, `PARKS["fryslan"]["station"]` | KNMI-station Fryslân (dagprofiel) | Houtribdijk (`06258`) | Kleinste RMS-afwijking tussen modelenergie en dagproductie van acht stations binnen 45 km (tien dagen in 2025–2026) | Vervangen: gemiddelde van Houtribdijk en Stavoren, gekozen op ligging en WINS50 |
| `application.py`, `alpha` + `alpha_seasonal` | Hoogte-exponent Fryslân | 0,115 + 0,065 cos(2π(n−1)/365): 0,18 winter, 0,05 zomer | Gefit op dagproductie (tien dagen), daarna bevestigd met `ijking.py` op 2022–2025 bij een grens van 85 % | Vervangen door WINS50-hoogtevertaling; alleen nog in de oude methode |
| `opsplitsing.py`, `STATIONS` + `combine_wind` | Windbron Fryslân (opsplitsing) | Per tien minuten de hoogste van Houtribdijk en Stavoren; ontbreekt er één, dan de ander | `ijking.py`: RMS 0,77 GWh tegen 0,82 GWh voor Houtribdijk alleen | Vervangen: dezelfde bron als het dagprofiel, zonder terugval op één station |
| `opsplitsing.py`, `park_mw` | Hoogtecorrectie in het aanbod | Zelfde seizoens-α als hierboven | Overgenomen uit de ijking | Vervangen |
| `ijking.py`, `prepare` | Dagselectie | Alleen dagen met ≥ 138 tienminutenwaarden **en productie > 0** | Selectie op de gemeten productie zelf | Alleen in de oude methode |
| `ijking.py`, `robust_fit` | ‘Verdachte dagen’ weglaten | Productie < grens × model én ≥ 0,5 GWh lager; herhaald tot stabiel | Selectie op productie; alleen dagen waarop het model hoger is vallen weg, nooit dagen waarop het lager is | Alleen in de oude methode; heet nu ‘dagen met groot verschil (model hoger)’ |
| `ijking.py`, `--grenzen` | Keuze van de grens | 85 % | Gekozen omdat de fit dan samenvalt met de al gebruikte formule (kringredenering) | Alleen in de oude methode |
| `docs/rekenmodel.md`, sectie 7 | Weggelaten ijkdagen | 1 januari 2026, 7 juli 2025, 5 en 13 oktober 2026 | Weggelaten omdat de productie lager was dan het model, toegeschreven aan afregeling of stilstand zonder aanvullende gegevens | Beschrijving aangepast: verschil, geen vastgestelde oorzaak |
| Website, `src/knmi.mjs` en `src/wind-potential.mjs` | Parkpagina’s | Standaard Stavoren, met de op Houtribdijk geijkte seizoens-α | Combinatie van een productie-geijkte α met een ander station dan waarop geijkt is | Niet gewijzigd (andere toepassing); zie [Website](#website) |
| Website, `src/opsplitsing/data/*.json` | Meegeleverde jaarreeksen | Aanbod met de oude opsplitsingsmethode | Zie de rij `STATIONS` + `combine_wind` | Opnieuw berekend met de nieuwe methode |

## Wat niet uit productie kwam

| Keuze | Waarde | Herkomst |
| --- | --- | --- |
| Ashoogte Fryslân | 115 m boven water | Exploitant: ‘hoogte van een windturbine boven water is 180 meter’, min de helft van 130 m rotordiameter. Gecontroleerd in oktober 2026, zie [databronnen](databronnen.md#ashoogte-en-verticale-referentie) |
| Turbinecurve Fryslân | gedigitaliseerde SWT-DD-130, 4,3 MW / 107 dB | Fabrikantpresentatie; modelgrens 28,01 m/s is een technische aanname |
| Zogverlies | 5 % Fryslân, 2 % Beabuorren minder wind | Scenario-aanname, niet gekalibreerd |
| Beabuorren | 60 m, curve SWT-1.3-62 | Lokaal nieuws, secundaire curve |
| Beabuorren, oud | Stavoren, α 0,20 | Dichtstbijzijnde station en land-aanname, niet op productie afgesteld; vervangen door dezelfde bron als Fryslân met een eigen WINS50-factor, zodat beide parken en beide routes één methode volgen |
| Aandeel voor waterstof | 10 % Fryslân + 100 % Beabuorren | mijnwindpark.nl |

De huidige curve en het zogverlies zijn niet op productie afgesteld. De oude `α` is wél
gefit met de vorige kubische curve en dit zogverlies. Fouten in curve en zog zijn daardoor deels in
de oude `α` terechtgekomen; met een onafhankelijke hoogtevertaling worden ze zichtbaar
als verschil tussen model en gemeten productie.

## De oude methode blijft reproduceerbaar

`windprofiel/windbron.py` bevat drie methoden:

| Methode | Fryslân | Beabuorren | Gebruikt door |
| --- | --- | --- | --- |
| `onafhankelijk` (standaard) | Gemiddelde van Houtribdijk en Stavoren (beide moeten meten), WINS50-maandfactor | Idem, eigen maandfactor | Dagprofiel en opsplitsing |
| `productie_houtribdijk` | Houtribdijk, seizoens-α | Stavoren, α 0,20 | Oude dagprofiel |
| `productie_hoogste` | Hoogste van Houtribdijk en Stavoren, seizoens-α | Stavoren, α 0,20 | Oude opsplitsing en `ijking.py` |

```sh
python3 -m windprofiel.vergelijking                               # nieuw en beide oude methoden, 2022–2025
python3 -m windprofiel.opsplitsing --windmethode productie_hoogste # oude opsplitsing
python3 -m windprofiel.ijking                                     # oude ijking, ongewijzigde uitkomst
```

`ijking.py` rekent bewust nog met `productie_hoogste`, zodat de tabel in
[rekenmodel.md](rekenmodel.md#oude-ijking-op-vier-jaar-dagproductie-20222025) te herhalen is.
De uitkomst van die ijking wordt nergens meer als standaard gebruikt.

## Website

De parkpagina’s van de website (`src/knmi.mjs`, `src/wind-potential.mjs`) zijn een eigen
JavaScript-route met instelbare parameters. Ze gebruiken standaard Stavoren met de
seizoens-α die op Houtribdijk is geijkt, en halen HARMONIE-wind op 10 m op bij
53,017° N 5,367° E. Dat punt ligt ongeveer 5 km oostelijker dan het geschatte midden van het park (zie
[databronnen](databronnen.md#locatie-van-het-park)). Die route is in deze wijziging niet
aangepast; de opsplitsingskopie in `src/opsplitsing/` wel.

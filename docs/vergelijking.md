# Model en gemeten productie: oud en nieuw

Vergelijking van de gemodelleerde mogelijke opbrengst van Windpark Fryslân met de gemeten
dagproductie, voor de oude, op productie afgestelde methoden en de nieuwe, productie-onafhankelijke
methode. Opnieuw te maken met `python3 -m windprofiel.vergelijking --waterstof` (uitvoer in
`uitvoer/vergelijking/`: `dagen.csv`, `gevoeligheid.csv`, `samenvatting.json`).

## Vooraf vastgelegd

- **Periode**: 1 januari 2022 tot en met 31 december 2025, de jaren met opgeslagen dagproductie.
- **Dagen**: elke dag met gemeten productie en volledige wind (alle tienminutenintervallen) in
  álle varianten hieronder. Zo worden oud, nieuw en de gevoeligheden op precies dezelfde dagen
  vergeleken. Geen enkele dag valt weg op grond van het verschil met de productie; dagen waarop het
  model lager uitkomt dan gemeten, tellen gewoon mee. De zes dagen met gemeten productie 0 tellen mee
  als 0.
- **Tijdschaal**: het model rekent per oorspronkelijk KNMI-tienminuteninterval (vermogen × 1/6 uur)
  en telt op naar Nederlandse kalenderdagen (Europe/Amsterdam), dezelfde dagen als de productie.
  Er wordt geen tienminutenproductie uit dagtotalen gemaakt.
- **Maat**: gemeten ÷ model over alle vergelijkingsdagen, gemiddeld en RMS-verschil per dag,
  correlatie van de dagwaarden, aantal dagen met het model lager en hoger dan gemeten.
- **Woorden**: het verschil heet *verschil tussen model en gemeten productie*. Het model rekent met
  100 % beschikbaarheid, zonder afregeling, stilstand, netbeperking of elektrische verliezen tot de
  meter. Dat maakt een lager gemeten productie verwacht, maar verklaart geen individueel verschil;
  er zijn geen gegevens over afregeling of storingen gebruikt.

## Tijdas, dekking en ontbrekende gegevens

<!-- T:DAGINDELING -->

<!-- T:DEKKING -->

## Oud en nieuw op dezelfde dagen

<!-- T:VERGELIJKING -->

<!-- T:JAAR -->

<!-- T:MAAND -->

### Dagen waarop het model lager uitkomt dan gemeten

<!-- T:LAGER -->

## Gevoeligheid voor onzekere aannames

Alle varianten op dezelfde vergelijkingsdagen. Alleen de genoemde aanname verandert; de rest is
de nieuwe standaard.

<!-- T:GEVOELIGHEID -->

### Verschuiving van Houtribdijk tegenover andere stations

<!-- T:DRIFT -->

## Gevolgen voor de waterstofuitkomsten

<!-- T:WATERSTOF -->

## Wat dit wel en niet laat zien

- **Niveau.** De nieuwe methode berekent minder mogelijke opbrengst dan beide oude methoden; de gemeten
  productie ligt dichter bij het model, maar nog steeds lager. Dat het oude niveau hoger lag, past bij
  de oude selectieregel: alleen dagen waarop het model hóger was dan gemeten werden weggelaten, wat de
  afgestelde α omhoog trok ([rekenmodel, sectie 7](rekenmodel.md#7-oude-ijking-op-productiedata-fryslân-niet-meer-in-gebruik)).
- **Dagpatroon.** De correlatie per dag is met de nieuwe methode hoger dan met beide oude methoden.
  Dat is een toets buiten de afleiding: station en factor zijn zonder productie gekozen.
- **Wat het verschil is.** Gemeten ÷ model onder 1 betekent dat het park minder leverde dan het model
  als mogelijk berekent. Het model kent geen beschikbaarheid onder 100 %, geen afregeling, geen
  netbeperking en geen elektrische verliezen tot de meter; ook de curve en het zog zijn aannames. Welk
  deel van het verschil waar vandaan komt, is met dagtotalen niet te scheiden. Het seizoenspatroon
  (in de zomer een groter verschil dan in de winter) is beschreven, niet verklaard.
- **Grootste onzekerheden.** De turbinecurve (nominale wind ±1 m/s) en het zogverlies (0–10 %) verschuiven
  de modelenergie meer dan de keuzes in de hoogtevertaling. Binnen de hoogtevertaling geven de spreiding
  tussen de WINS50-jaren, de verschuiving van Houtribdijk en de stationskeuze elk enkele procenten;
  de ashoogte (109 of 115 m) ongeveer een procent. In de kruisvalidatie op WINS50 zelf geeft F × ff
  enkele procenten minder energie dan de modelwind op ashoogte (zie [databronnen](databronnen.md#stations)).
- **Geen validatie op ashoogte.** Er is geen windmeting op 115 m bij het park gebruikt; WINS50 is een model.
  De hoogtevertaling blijft daarom een onderbouwde aanname, met de gevoeligheid hierboven.
- **Niet gedaan.** Er is niets afgesteld op de productie, er zijn geen dagen weggelaten om het verschil,
  en er is geen tienminuten- of uurproductie afgeleid uit de dagtotalen.


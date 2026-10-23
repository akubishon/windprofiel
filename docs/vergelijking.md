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
  meter. Daardoor is een lagere gemeten productie te verwachten, maar dat verklaart geen individueel
  verschil; er zijn geen gegevens over afregeling of storingen gebruikt.

## Tijdas, dekking en ontbrekende gegevens

De datums in de productie zijn Nederlandse kalenderdagen. Controle: de modelenergie per tien minuten (nieuwe methode) op vier manieren in dagen ingedeeld en gecorreleerd met de gemeten dagproductie. Er wordt niets op afgesteld; het gaat alleen om de tijdas.

| Dagindeling | Correlatie met gemeten dagproductie |
| --- | ---: |
| Europe/Amsterdam | 0,904 |
| UTC | 0,902 |
| Europe/Amsterdam, dag later | 0,521 |
| Europe/Amsterdam, dag eerder | 0,524 |

Europe/Amsterdam past het best; UTC-dagen liggen daar vlak onder (één à twee uur verschuiving), een dag verschuiven geeft een veel lagere correlatie.

Een dag telt alleen mee als alle tienminutenintervallen wind hebben; er wordt niets ingevuld en geen ander station gebruikt. Klokwisseldagen tellen met 138 of 150 intervallen.

| Jaar | Dagen | Volledige wind (Houtribdijk én Stavoren) | Onvolledig | Klokwisseldagen | Gemeten productie 0 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022 | 365 | 325 | 40 | 2 | 1 |
| 2023 | 365 | 329 | 36 | 2 | 0 |
| 2024 | 366 | 335 | 31 | 2 | 4 |
| 2025 | 365 | 342 | 23 | 2 | 1 |

Vergelijkingsdagen (volledig in álle varianten en met gemeten productie): **1.331** van de 1.461.

## Oud en nieuw op dezelfde dagen

Over 1.331 dezelfde dagen. ‘Verschil’ is model min gemeten.

| Methode | Model | Gemeten | Gemeten ÷ model | Gemiddeld verschil per dag | RMS-verschil per dag | Correlatie | Dagen model lager | Dagen model hoger |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oud dagprofiel (Houtribdijk, seizoens-α) | 5.484 GWh | 4.574 GWh | 0,834 | +683 MWh | 1.536 MWh | 0,873 | 384 | 947 |
| Oude opsplitsing (hoogste van twee, seizoens-α) | 5.724 GWh | 4.574 GWh | 0,799 | +864 MWh | 1.577 MWh | 0,885 | 289 | 1042 |
| **Nieuw** (gemiddelde Houtribdijk + Stavoren, WINS50-factor) | 5.145 GWh | 4.574 GWh | 0,889 | +429 MWh | 1.271 MWh | 0,906 | 475 | 856 |

Per jaar:

| Jaar | Dagen | Oud dagprofiel (Houtribdijk, seizoens-α): gemeten ÷ model | Oude opsplitsing (hoogste van twee, seizoens-α): gemeten ÷ model | Nieuw (gemiddelde Houtribdijk + Stavoren, WINS50-factor): gemeten ÷ model |
| --- | ---: | ---: | ---: | ---: |
| 2022 | 325 | 0,847 | 0,814 | 0,914 |
| 2023 | 329 | 0,778 | 0,752 | 0,833 |
| 2024 | 335 | 0,874 | 0,833 | 0,918 |
| 2025 | 342 | 0,843 | 0,801 | 0,896 |

Per kalendermaand, over alle jaren samen:

| Gemeten ÷ model | jan | feb | mrt | apr | mei | jun | jul | aug | sep | okt | nov | dec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Oud dagprofiel (Houtribdijk, seizoens-α) | 0,89 | 0,92 | 0,81 | 0,81 | 0,77 | 0,79 | 0,81 | 0,70 | 0,87 | 0,92 | 0,78 | 0,84 |
| Oude opsplitsing (hoogste van twee, seizoens-α) | 0,86 | 0,90 | 0,77 | 0,78 | 0,73 | 0,76 | 0,77 | 0,66 | 0,82 | 0,87 | 0,75 | 0,82 |
| Nieuw (gemiddelde Houtribdijk + Stavoren, WINS50-factor) | 0,95 | 0,97 | 0,96 | 0,91 | 0,89 | 0,80 | 0,83 | 0,74 | 0,88 | 0,91 | 0,83 | 0,89 |

### Dagen waarop het model lager uitkomt dan gemeten

Op **475** van de 1.331 vergelijkingsdagen (36 %) berekent het nieuwe model minder energie dan er gemeten is; op 212 daarvan minstens 500 MWh minder. Die dagen tellen volledig mee en staan allemaal in `uitvoer/vergelijking/dagen.csv` (kolom `model_lager_dan_gemeten`). De tien grootste:

| Datum | Wind op ashoogte (daggemiddelde) | Model | Gemeten | Verschil (model − gemeten) |
| --- | ---: | ---: | ---: | ---: |
| 2024-01-28 | 8,6 m/s | 3.416 MWh | 6.586 MWh | −3.170 MWh |
| 2022-03-13 | 8,0 m/s | 2.625 MWh | 5.516 MWh | −2.891 MWh |
| 2022-03-12 | 8,9 m/s | 4.039 MWh | 6.853 MWh | −2.814 MWh |
| 2025-12-27 | 6,3 m/s | 1.624 MWh | 4.381 MWh | −2.757 MWh |
| 2025-11-05 | 9,3 m/s | 4.274 MWh | 6.942 MWh | −2.668 MWh |
| 2022-01-21 | 9,1 m/s | 3.982 MWh | 6.414 MWh | −2.432 MWh |
| 2025-12-29 | 7,3 m/s | 2.104 MWh | 4.495 MWh | −2.391 MWh |
| 2025-12-30 | 7,9 m/s | 2.648 MWh | 4.964 MWh | −2.316 MWh |
| 2025-02-20 | 9,9 m/s | 5.152 MWh | 7.438 MWh | −2.286 MWh |
| 2023-01-26 | 8,7 m/s | 3.689 MWh | 5.967 MWh | −2.278 MWh |

Ook hier geen oorzaak: het kan aan de stationswind, de hoogtevertaling, de turbinecurve of het zog liggen; daar zijn geen aanvullende gegevens over.

## Gevoeligheid voor onzekere aannames

Alle varianten op dezelfde vergelijkingsdagen. Alleen de genoemde aanname verandert; de rest is
de nieuwe standaard.

| Variant | Model | Verandering model | Gemeten ÷ model | RMS-verschil per dag | Correlatie | Dagen model lager |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Productie-onafhankelijk: Houtribdijk + Stavoren, WINS50-maandfactor | 5.145 GWh | +0,0 % | 0,889 | 1.271 MWh | 0,906 | 475 |
| F per maand van het laagste WINS50-jaar (2019–2021) | 4.898 GWh | −4,8 % | 0,934 | 1.224 MWh | 0,903 | 575 |
| F per maand van het hoogste WINS50-jaar (2019–2021) | 5.389 GWh | +4,7 % | 0,849 | 1.366 MWh | 0,903 | 360 |
| Ashoogte 109 m (persbericht 2018) in plaats van 115 m | 5.097 GWh | −0,9 % | 0,897 | 1.259 MWh | 0,905 | 491 |
| Ontleding: alleen de WINS50-hoogtetoename op de parklocatie, zonder correctie voor de stationsligging | 3.934 GWh | −23,5 % | 1,163 | 1.375 MWh | 0,874 | 956 |
| Houtribdijk per jaar gecorrigeerd naar zijn verhouding met Stavoren in 2019–2021 | 5.319 GWh | +3,4 % | 0,860 | 1.331 MWh | 0,905 | 401 |
| Geen zogverlies | 5.598 GWh | +8,8 % | 0,817 | 1.443 MWh | 0,905 | 310 |
| Zogverlies 10 % minder wind | 4.675 GWh | −9,1 % | 0,978 | 1.190 MWh | 0,902 | 673 |
| Kubische curve met nominale wind 10,5 m/s | 5.917 GWh | +15,0 % | 0,773 | 1.610 MWh | 0,902 | 215 |
| Kubische curve met nominale wind 12,5 m/s | 4.454 GWh | −13,4 % | 1,027 | 1.191 MWh | 0,899 | 753 |
| Alleen station Houtribdijk, met eigen WINS50-maandfactor | 5.070 GWh | −1,5 % | 0,902 | 1.404 MWh | 0,873 | 509 |
| Alleen station Stavoren, met eigen WINS50-maandfactor | 5.240 GWh | +1,8 % | 0,873 | 1.309 MWh | 0,900 | 444 |

### Verschuiving van Houtribdijk tegenover andere stations

Verhouding van de jaargemiddelde `ff`, over momenten waarop alle vier stations meten. Alleen stationsdata.

| Jaar | Houtribdijk/Stavoren | Houtribdijk/Vlieland | Stavoren/Vlieland | Stavoren/Leeuwarden |
| --- | ---: | ---: | ---: | ---: |
| 2019 | 1,307 | 0,967 | 0,739 | 1,208 |
| 2020 | 1,283 | 0,940 | 0,732 | 1,182 |
| 2021 | 1,266 | 0,945 | 0,746 | 1,211 |
| 2022 | 1,248 | 0,911 | 0,730 | 1,180 |
| 2023 | 1,256 | 0,930 | 0,740 | 1,194 |
| 2024 | 1,227 | 0,896 | 0,730 | 1,173 |
| 2025 | 1,228 | 0,899 | 0,732 | 1,178 |

Houtribdijk meet in 2022–2025 gemiddeld ongeveer 4 % minder wind ten opzichte van Stavoren en Vlieland
dan in 2019–2021, de jaren waarop de factor F is afgeleid (Houtribdijk/Stavoren 1,285 → 1,240;
Houtribdijk/Vlieland 0,951 → 0,909). Stavoren blijft ten opzichte van Vlieland en Leeuwarden binnen
1–2 % gelijk. De oorzaak is niet vastgesteld; de EDR-metadata bevat geen stationsgeschiedenis. Omdat F
op 2019–2021 rust, valt de wind in 2022–2025 met het gemiddelde van beide stations daardoor iets lager uit.
De variant ‘Houtribdijk per jaar gecorrigeerd’ in de tabel hierboven laat zien hoeveel: ongeveer 3 % meer
modelenergie. Die correctie is niet in de standaardmethode opgenomen, omdat ze op de aanname rust dat
Stavoren stabiel is; ze staat hier als gevoeligheid.

## Gevolgen voor de waterstofuitkomsten

De opsplitsing rekent met de nieuwe wind (`MODEL_VERSION` 11). Aannames van de elektrolyser zijn
gelijk gehouden; alleen het windaanbod verschilt. Het aanbod daalt met ongeveer 13 %, de waterstof
met 13 tot 17 % en de kostprijs per kilo stijgt met ongeveer 0,25 tot 0,45 €. Het goedkoopste aantal
modules verandert in deze twee scenario's niet. Bij één grote module met een hoge minimumlast daalt
de productie het sterkst, omdat meer tijdstappen onder de startdrempel vallen.

**PEM, standaard**, besturing `verdelen`, windjaren 2022–2025. Aanbod naar de elektrolyser: 190 GWh per jaar oud, 165 GWh nieuw (−13,3 %).

| Modules | Waterstof oud | Waterstof nieuw | Verandering | LCOH oud | LCOH nieuw | Productie-uren oud | nieuw |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 3.119 t | 2.681 t | −14,0 % | 8,05 €/kg | 8,33 €/kg | 5.977 | 5.447 |
| 2 | 3.266 t | 2.833 t | −13,2 % | 8,00 €/kg | 8,25 €/kg | 7.088 | 6.646 |
| 3 | 3.297 t | 2.867 t | −13,0 % | 8,02 €/kg | 8,27 €/kg | 7.464 | 7.065 |
| 4 | 3.311 t | 2.882 t | −13,0 % | 8,05 €/kg | 8,30 €/kg | 7.661 | 7.292 |
| 6 | 3.323 t | 2.891 t | −13,0 % | 8,12 €/kg | 8,38 €/kg | 7.865 | 7.536 |
| 8 | 3.330 t | 2.897 t | −13,0 % | 8,20 €/kg | 8,46 €/kg | 7.979 | 7.672 |

Laagste berekende kostprijs: oud 2 modules (8,00 €/kg), nieuw 2 modules (8,25 €/kg).

**Alkaline, 40 % minimumlast, 0,3 M€ per module**, besturing `verdelen`, windjaren 2022–2025. Aanbod naar de elektrolyser: 190 GWh per jaar oud, 165 GWh nieuw (−13,3 %).

| Modules | Waterstof oud | Waterstof nieuw | Verandering | LCOH oud | LCOH nieuw | Productie-uren oud | nieuw |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2.577 t | 2.134 t | −17,2 % | 8,53 €/kg | 8,98 €/kg | 3.572 | 2.996 |
| 2 | 3.054 t | 2.602 t | −14,8 % | 8,20 €/kg | 8,53 €/kg | 5.171 | 4.590 |
| 3 | 3.186 t | 2.734 t | −14,2 % | 8,14 €/kg | 8,46 €/kg | 5.889 | 5.319 |
| 4 | 3.252 t | 2.796 t | −14,0 % | 8,11 €/kg | 8,44 €/kg | 6.335 | 5.766 |
| 6 | 3.295 t | 2.843 t | −13,7 % | 8,12 €/kg | 8,44 €/kg | 6.835 | 6.336 |
| 8 | 3.318 t | 2.866 t | −13,6 % | 8,13 €/kg | 8,45 €/kg | 7.129 | 6.677 |

Laagste berekende kostprijs: oud 4 modules (8,11 €/kg), nieuw 4 modules (8,44 €/kg).


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


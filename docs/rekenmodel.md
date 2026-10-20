# Formules, werking en aannames

Het doel is een eenvoudig, indicatief beeld van vermogensschommelingen over
tientallen minuten en uren. De app berekent geen gemeten elektriciteitsproductie
en reconstrueert geen werkelijke windvlagen per minuut. Alle formules staan ook
in de webapp onder **Formules, werking en bronnen**.

## 1. Wind op ashoogte

\[
v_h=v_{10}\left(\frac{h}{10}\right)^\alpha
\]

`v₁₀` is KNMI-variabele `ff`: windsnelheid in m/s, representatief voor 10 meter.
`h` is de ashoogte in meters. `α` bepaalt de toename met de hoogte. Fryslân
gebruikt `h = 115 m` en een exponent die met het seizoen meebeweegt;
Beabuorren `h = 60 m, α = 0,20`:

\[
\alpha_\mathrm{Fryslân}(n)=0{,}115+0{,}065\cos\left(\frac{2\pi(n-1)}{365}\right)
\]

`n` is het dagnummer in het jaar (1 = 1 januari). Begin januari is `α` 0,18,
begin juli 0,05, in april en oktober circa 0,115.
In de webapp is per park een eigen `α` in te vullen (0 tot 0,6); die geldt dan
voor de hele gekozen dag, ook voor de CSV-export.
Deze correctie verandert het niveau van de hele reeks en daarmee, via de
vermogenscurve, ook de grootte van de schommelingen.

De [wind profile power law](https://en.wikipedia.org/wiki/Wind_profile_power_law)
beschrijft de empirische formule en de afhankelijkheid van terrein en
atmosferische stabiliteit. De bron noemt circa 0,11 boven open water in neutrale
omstandigheden. Op de onderzochte dagen nam de wind in de winter veel sterker
met de hoogte toe dan in de zomer. **De Fryslân-seizoensformule is geijkt op
productiedata (sectie 7); 0,20 voor land is een modelkeuze, geen gemeten
exponent voor Beabuorren.** Een vaste exponent van
10 naar 115 meter kan aanzienlijke onzekerheid geven. De formule corrigeert
alleen hoogte, niet de afstand of terreinverschillen tussen station en park.

## 2. Benaderde curve voor Fryslân

Met `v = v_h` geldt per turbine:

\[
P(v)=\begin{cases}
0 & v<3\\
4300\dfrac{v^3-3^3}{11{,}5^3-3^3} & 3\leq v<11{,}5\\
4300 & 11{,}5\leq v\leq25\\
0 & v>25
\end{cases}
\quad[\mathrm{kW}]
\]

De aanloop is genormaliseerd: bij 3 m/s is de teller nul, bij 11,5 m/s is teller
gelijk aan noemer en wordt 4.300 kW bereikt. Anders dan `(v−3)³` gebruikt dit
model `v³−3³`. Er is geen bewijs dat deze eenvoudige curve nauwkeuriger is dan
een andere benadering voor deze specifieke turbine; het is een transparante
keuze die bij de afgesproken vereenvoudiging past.

De derde macht is geïnspireerd op:

\[
P_\mathrm{wind}=\frac12\rho A v^3,\qquad
P_\mathrm{turbine}=C_p P_\mathrm{wind}
\]

Hier is `ρ` de luchtdichtheid, `A` het rotoroppervlak en `Cₚ` de
omzettingsefficiëntie, die in werkelijkheid met de wind en regeling verandert.
De [U.S. Department of Energy Small Wind Guidebook](https://windexchange.energy.gov/small-wind-guidebook)
beschrijft dit verband. Deze bron ondersteunt de kubische natuurkundige
achtergrond, **niet de exacte genormaliseerde curve of gekozen snelheidgrenzen**.

**3, 11,5 en 25 m/s zijn de in deze sessie afgesproken scenario-aannames.**
Er is geen gecontroleerde fabrikantbron gevonden die deze waarden voor de
4,3 MW-uitvoering bevestigt. Bij precies 25 m/s blijft dit scenario op vol
vermogen; daarboven gaat het abrupt naar nul, overeenkomstig het voorgestelde
raamwerk. Dit model bevat geen stormregeling of herstartvertraging.

## 3. Gepubliceerde curve voor Beabuorren

Voor twee omliggende curvepunten `(v₀, P₀)` en `(v₁, P₁)`:

\[
P(v)=P_0+(P_1-P_0)\frac{v-v_0}{v_1-v_0}
\]

Dit is lineaire interpolatie: een snelheid halverwege twee punten geeft het
vermogen halverwege die punten. De punten komen uit de grafiek voor
[Siemens SWT-1.3-62](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62).
Het is een secundaire bron, geen gecertificeerde fabrikantcurve; de
referentieluchtdichtheid is onbekend. Vanaf 25 m/s wordt het vermogen in dit
model nul, volgens de cut-out in deze datasheet. Dat grensgedrag verschilt dus
bij precies 25 m/s van het gekozen Fryslân-scenario.

## 4. Parken optellen en energie berekenen

\[
P_\mathrm{park}[\mathrm{MW}]=\frac{N\,P_\mathrm{turbine}[\mathrm{kW}]}{1000}
\]

\[
P_\mathrm{samen}(t)=P_\mathrm{Fryslân}(t)+P_\mathrm{Beabuorren}(t)
\]

\[
E_\mathrm{dag}[\mathrm{MWh}]\approx\sum_t\frac{P_\mathrm{minuut}(t)[\mathrm{MW}]}{60}
\]

\[
\mathrm{vollasturen}=\frac{E[\mathrm{MWh}]}{P_\mathrm{nominaal}[\mathrm{MW}]}
\]

Vollasturen zijn het aantal uren dat het park op vol vermogen had moeten draaien
voor dezelfde opbrengst: 382,7 MW voor Fryslân, 10,4 MW voor Beabuorren en
393,1 MW samen. Voor een geselecteerd tijdvak gelden dezelfde formules, met de
som alleen over de gekozen minuten.

`N` is 89 voor Fryslân en 8 voor Beabuorren. Elke minuut duurt 1/60 uur. Alle
turbines van een park krijgen dezelfde modelwind; zogverlies staat in sectie 5. Stilstand,
afregeling, luchtdichtheidcorrectie en individuele turbineverschillen zijn
niet meegenomen. Een ontbrekende minuut in een park maakt de volledige
dagopbrengst onbekend; ontbrekende productie wordt nooit als nul opgeteld.

## 5. Zogverlies

Turbines in het zog van andere turbines vangen tragere en turbulentere wind.
Standaard benaderen we dat met één parkgemiddelde snelheidsverlaging `d`:

\[
v_\mathrm{eff}=v_h(1-d),\qquad
P_\mathrm{turbine}=\begin{cases}
P(v_\mathrm{eff}) & P(v_h)>0\\
0 & \text{anders}
\end{cases}
\]

Fryslân gebruikt `d = 0,05` (89 turbines dicht bij elkaar), Beabuorren
`d = 0,02` (8 turbines). Via de vermogenscurve is het verlies vanzelf het
grootst in de aanloop en klein of nul bij harde wind: bij `v_h = 8 m/s` geeft
5 % minder wind in het Fryslân-model circa 15 % minder vermogen, vanaf
`v_h ≈ 12,1 m/s` niets meer. In- en uitschakelen volgt de ongestoorde wind
`v_h`, zodat het zog de cut-out niet verschuift.

**0,05 en 0,02 zijn gekozen scenario-aannames, niet gekalibreerd op
productiedata of een zogmodel.** Het model negeert windrichting en
turbineopstelling. In werkelijkheid is het verlies veel groter als de wind
langs een rij turbines waait, en vangen de voorste turbines de volle wind. Een
richtingsafhankelijk model, zoals het Jensen/Park-model, vereist geverifieerde
turbineposities; die zijn nog niet opgenomen. Met het vinkje **Zogverlies
meenemen** of `wake=0` in de API wordt de correctie uitgeschakeld.

## 6. Tijd en zichtbare punten

\[
v(t)=v_0+(v_1-v_0)\frac{t-t_0}{t_1-t_0}
\]

De [KNMI-documentatie](https://dataplatform.knmi.nl/dataset/docs/10-minute-in-situ-meteorological-observations-1-0)
beschrijft tienminutengemiddelden met een tijdstempel aan het intervaleinde in
UTC. We plaatsen het gemiddelde op het intervalmidden, vijf minuten eerder,
en interpoleren wind lineair vóór hoogtecorrectie en vermogensberekening.
Een meetgat, ongeldige windwaarde of interval langer dan tien minuten wordt
niet overbrugd. De Nederlandse kalenderdag bevat normaal 1.440 minuten, maar
1.380 of 1.500 tijdens de klokwissel.

De stippen tonen vermogen **berekend uit de oorspronkelijke KNMI-gemiddelden**.
Ze zijn geen gemeten vermogenswaarden. De windgrafiek toont de oorspronkelijke
windgemiddelden als stippen. In de gecombineerde grafiek verschijnt een stip
alleen met waarden voor beide parken op hetzelfde intervalmidden. De stippen
kunnen worden verborgen met de checkbox, zonder data opnieuw op te halen.

De minuutlijn geeft geen extra waargenomen windinformatie. Door niet-lineariteit
is `P(gemiddelde wind)` niet gelijk aan `gemiddeld P(wind)`. Vooral bij de
inschakel- en uitschakelgrenzen blijft er onzekerheid. Het model is bedoeld om
patronen te verkennen, niet om exacte productie of echte minuutfluctuaties te
voorspellen.

## 7. IJking op productiedata Fryslân

De oorspronkelijke keuze, Stavoren met `α = 0,10`, gaf voor 4 december 2025
1,69 GWh terwijl het park ongeveer 4,5 GWh produceerde. Daarom zijn station en
exponent geijkt op dagopbrengsten uit de app van Windpark Fryslân, met het
kubische model en 5 % zogverlies:

| Dag | Productie | Model (Houtribdijk, seizoens-α) | α die dag | Oud (Stavoren, α 0,10) |
| --- | --- | --- | --- | --- |
| 4 december 2025 | ~4,5 GWh | 4,4 GWh | 0,17 | 1,7 GWh |
| 18 december 2025 | 8,8 GWh | 8,9 GWh | 0,18 | 7,5 GWh |
| 19 december 2025 | 5,9 GWh | 5,6 GWh | 0,18 | 2,1 GWh |
| 28 december 2025 | 0,78 GWh | 0,55 GWh | 0,18 | 0,06 GWh |
| 20 juli 2025 | 0,76 GWh | 0,75 GWh | 0,05 | — |
| 22 juli 2025 | 3,2 GWh | 3,4 GWh | 0,05 | — |
| 7 juli 2025 | 1,3 GWh | 5,2 GWh | 0,05 | — |

Gezocht is over acht stations binnen 45 km en een vaste `α` per seizoen.
Houtribdijk gaf in de winter de kleinste afwijking (circa 180 MWh RMS, beste
`α` 0,18); Stavoren haalde op zijn best circa 600 MWh. Houtribdijk ligt midden
in het IJsselmeer en vangt vermoedelijk de wind boven open water beter dan het
kuststation Stavoren. Voor 20 en 22 juli gaf Houtribdijk de beste `α` van 0,04
tot 0,05. Voor 20 juli volgt het model met `α = 0,05` ook het uurverloop uit de
app van Windpark Fryslân (rustige ochtend, piek rond 16–17 uur) met een
gemiddelde afwijking van circa 18 MWh per uur. De cosinus verbindt beide
seizoenswaarden zonder sprong.

Niet meegenomen zijn 1 januari 2026 (6,7 GWh; het model geeft bij de harde wind
van die dag vrijwel vol vermogen, ~9,1 GWh) en 7 juli 2025 (1,3 GWh; ook met
`α = 0` geeft het model nog ~3,9 GWh). Beide verschillen passen bij afregeling of
stilstand, die dit model niet kent. Het model geeft de productie die met de wind
mogelijk is, niet wat het park werkelijk levert.

5 oktober 2025 (circa 2,8 GWh) is ook niet meegenomen voor de dagtotalen: tot
17 uur leverde het park ~5 MWh per uur bij 9 tot 14 m/s op 10 meter, wat op
afregeling wijst. Van 17 tot 24 uur draaide het park op vol vermogen (~2,6 GWh),
het model geeft daar met `α = 0,12` 1,8 GWh. Vooral 21–24 uur blijft te laag: na
zonsondergang wordt de lucht stabiel en neemt de wind sterker toe met de hoogte.
Ook de nachturen van 20 juli liggen hoger dan het model. Een aparte nachtexponent
(circa +0,12) verbetert die uren, maar maakt de decemberdagen 20 tot 60 % te hoog;
met de huidige data is dat niet verantwoord en daarom niet ingebouwd.

Voor 4 december 2025 klopt het dagtotaal (4,4 tegen ~4,5 GWh), maar per uur is
het model te steil: bij weinig wind te laag, rond 16–18 uur op vol vermogen
(~380 MW) waar het park ~300 MW leverde. Getest is een parkcurve die per moment
middelt over ±25 % windspreiding tussen turbines. Die volgt het uurverloop in
december beter en geeft 28 december goed (0,77 GWh), maar maakt 20 en 22 juli
50–60 % te hoog. Over alle uren en dagen samen daalt de gemiddelde afwijking
alleen van circa 64 naar 52 MWh per uur. Dat weegt met deze data niet op tegen
het extra model; de spreiding is daarom niet ingebouwd.

### Herberekening met oktober 2026

In oktober 2026 is de keuze opnieuw getoetst, met tien dagen: de zes dagen
hierboven en 6, 7, 10 en 12 oktober 2026 (0,49 / 1,3 / 8,4 / 1,6 GWh). 13 oktober
2026 is weggelaten, omdat het park die middag tot circa 180 MW is afgeregeld.
Per station is de best passende seizoensformule `α = a + b cos(…)` gezocht:

| Station | Afstand tot park | RMS-afwijking per dag | Beste `α` |
| --- | ---: | ---: | --- |
| Houtribdijk | 43 km | 0,27 GWh | 0,12 + 0,07 cos |
| Gemiddelde Houtribdijk en Stavoren | — | 0,29 GWh | 0,15 + 0,07 cos |
| De Kooy (9 dagen) | 35 km | 0,31 GWh | 0,23 + 0,07 cos |
| Stavoren | 17 km | 0,44 GWh | 0,19 + 0,07 cos |
| Vlieland, Texelhors, Leeuwarden, Terschelling | 33–40 km | 0,48–0,54 GWh | — |

Houtribdijk blijft de beste keuze, ondanks de grotere afstand; de best passende
formule valt vrijwel samen met de gebruikte (0,115 + 0,065 cos). Stavoren meet
structureel minder wind dan het park krijgt en de best passende `α` per dag
wisselt daar sterk (0,08 tot 0,36); boven het IJsselmeer is de verhouding
stabieler. De seizoensformule is op Houtribdijk geijkt: een ander station voor
Fryslân geeft met dezelfde `α` een andere, meestal te lage uitkomst.

**Dit is een kleine steekproef**: vier winter-, twee zomer- en vier herfstdagen.
Het voorjaar is niet gecontroleerd; daar is de cosinus een interpolatie. De
seizoensformule is empirisch en beschrijft niet het weer van de dag: een
stabiele zomernacht of een onstabiele winterdag krijgt dezelfde `α` als de rest
van het seizoen.

### Toetsing op vier jaar dagproductie (2022–2025)

In oktober 2026 is de formule getoetst op de dagproductie uit de app van Windpark
Fryslân voor 2022–2025: 1.442 volledige dagen met KNMI-wind en productie. Afregelen
en stilstand verlagen de productie alleen, dus een kleinste-kwadratenfit op alle
dagen trekt `α` omlaag. Daarom zijn dagen waarop de productie onder een grens maal
het model bleef (en minstens 0,5 GWh lager) als verdacht weggelaten en is opnieuw
gefit tot de selectie stabiel was.

| Wind voor Fryslân | Beste `α` (grens 75 %) | RMS-afwijking per dag | Verdachte dagen |
| --- | --- | ---: | ---: |
| Houtribdijk | 0,110 + 0,065 cos | 0,82 GWh | 418 |
| Hoogste van Houtribdijk en Stavoren per tien minuten | 0,095 + 0,070 cos | 0,77 GWh | 383 |

De hoogste van beide stations sluit beter aan. Meet Stavoren weinig terwijl
Houtribdijk wel wind ziet, of andersom, dan volgt het park de hoogste lijn. De
opsplitsingspagina gebruikt daarom voor Fryslân deze combinatie; Beabuorren houdt
Stavoren.

De seizoensamplitude (circa 0,07) is stabiel, het niveau van `α` niet: dat hangt af
van de grens voor verdachte dagen.

| Grens | Beste `α` (winter / zomer) | Behouden dagen |
| ---: | --- | ---: |
| 65 % | 0,155 / 0,015 | 1.198 |
| 75 % | 0,165 / 0,025 | 1.059 |
| 85 % | 0,180 / 0,050 | 791 |
| geen | 0,135 / 0,0 | 1.442 |

De verdachte dagen liggen verspreid over alle maanden en zijn nauwelijks vaker
weekenddagen. Uit dagtotalen is afregelen dus niet te scheiden van stilstand of
gewone modelspreiding. Bij een grens van 85 % valt de best passende formule samen
met de gebruikte (0,115 + 0,065 cos); die is daarom gehouden. Een scherpere ijking
vraagt uurdata, waarin afregelen te herkennen is als een vlak niveau onder het
vermogen of een plotselinge daling bij aanhoudende wind.

De dagproductie staat in `windprofiel/data/productie_fryslan.csv`; deze toetsing is
te herhalen met `python3 -m windprofiel.ijking` (enkele minuten, zonder nieuwe
aanvragen bij de app van Windpark Fryslân).

## Bronnen en status van de getallen

| Gegeven | Waarde | Onderbouwing |
| --- | --- | --- |
| KNMI-bron | EDR, `10-minute-in-situ-meteorological-observations/1.0` | [Officiële dataset](https://dataplatform.knmi.nl/dataset/10-minute-in-situ-meteorological-observations-1-0), `ff` in m/s, niet handmatig gevalideerd |
| Fryslân | 89 × 4,3 MW | [Exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/) |
| Fryslân-ashoogte | circa 115 m | Afgeleid: 180 m tiphoogte − 130 m rotordiameter / 2, [factsheet](https://www.windparkfryslan.nl/wp-content/uploads/2020/05/Factsheet-Windpark-Fryslan.pdf) |
| Fryslân-grenzen | 3 / 11,5 / 25 m/s | Afgesproken scenario-keuze; niet bevestigd door fabrikant |
| Hoogte-exponenten | Fryslân 0,05 (zomer) tot 0,18 (winter) / 0,20 land | Fryslân geijkt op tien productiedagen (sectie 7); land is een modelkeuze; [achtergrond](https://en.wikipedia.org/wiki/Wind_profile_power_law) |
| Fryslân-station | Houtribdijk (`06258`) | Beste aansluiting op productiedata van de acht onderzochte stations (sectie 7) |
| Beabuorren-station | Stavoren (`06267`) | Dichtstbijzijnde KNMI-station (19 km), niet geijkt op productiedata |
| Beabuorren | 8 turbines, 10,4 MW | [Onderhoudsbedrijf Rengineers](https://rengineers.eu/nieuw/wynpark-beaborren-25-jaar/) |
| Beabuorren-model | SWT-1.3-62 | [The Wind Power](https://www.thewindpower.net/windfarm_en_6263_beabuorren.php), secundaire bron |
| Beabuorren-ashoogte | 60 m | [Lokaal bericht uit 2007](https://tsjerkwert.nl/start-opschaling-van-het-wynpark/); niet bevestigd voor alle acht turbines |
| Beabuorren-curve | Numerieke grafiekpunten, cut-out 25 m/s | [Wind-Turbine-Models](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62), secundaire bron |
| Zogverlies | 5 % Fryslân / 2 % Beabuorren minder wind | Onze scenario-keuze; niet gekalibreerd, geen windrichting of opstelling |

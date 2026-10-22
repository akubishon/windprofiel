# Formules, werking en aannames

Het doel is een eenvoudig, indicatief beeld van vermogensschommelingen over
tientallen minuten en uren. De app berekent geen gemeten elektriciteitsproductie
en reconstrueert geen werkelijke windvlagen per minuut. Alle formules staan ook
in de webapp onder **Formules, werking en bronnen**.

## 1. Wind op ashoogte

```math
v_h(t)=F_{\text{park},m}\;\bar v_{10}(t),\qquad
\bar v_{10}(t)=\tfrac12\left(f\!f_\text{Houtribdijk}(t)+f\!f_\text{Stavoren}(t)\right)
```
`ff` is de KNMI-tienminutenwind, representatief voor 10 m. Beide parken krijgen het gemiddelde
van de twee stations op het IJsselmeer; ontbreekt één van beide, dan blijft dat moment leeg.
`m` is de kalendermaand (Europe/Amsterdam). De factor komt uit de KNMI-heranalyse WINS50
(HARMONIE-AROME, 2,5 km, run zonder windparken), op de parklocatie, over dezelfde uren in
2019–2021:

```math
F_{\text{park},m}=\frac{\sum_{t\in m} v_\text{WINS50}(\text{park},h,t)}{\sum_{t\in m}\bar v_{10}(t)}
```
`h` is 115 m voor Fryslân en 60 m voor Beabuorren. WINS50 heeft niveaus op 100 en 120 m; 115 m
volgt met een machtwet tussen die twee niveaus. Stationswind rond het hele uur is het gemiddelde
van de twee tienminutenintervallen met hun midden vijf minuten ervoor en erna.

F doet twee dingen tegelijk: de toename van de wind met de hoogte boven het park, en het verschil
tussen de stations en de parklocatie (ligging, dijkhoogte van Houtribdijk, de land-zeegrens bij
Stavoren). Daarom is F groter dan de toename met de hoogte alleen. Om te vergelijken met de oude
werkwijze staat F ook als exponent vanaf 10 m: `α = ln F / ln(h/10)`.

WINS50 2019–2021, 26.304 uren:

| Maand | jan | feb | mrt | apr | mei | jun | jul | aug | sep | okt | nov | dec |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| F Fryslân (115 m) | 1,551 | 1,537 | 1,404 | 1,354 | 1,250 | 1,276 | 1,250 | 1,323 | 1,438 | 1,511 | 1,540 | 1,611 |
| als α vanaf 10 m | 0,180 | 0,176 | 0,139 | 0,124 | 0,091 | 0,100 | 0,091 | 0,115 | 0,149 | 0,169 | 0,177 | 0,195 |
| F per WINS50-jaar, laagste–hoogste | 1,53–1,59 | 1,45–1,63 | 1,38–1,42 | 1,29–1,39 | 1,23–1,28 | 1,27–1,29 | 1,22–1,30 | 1,29–1,37 | 1,36–1,52 | 1,46–1,57 | 1,49–1,58 | 1,57–1,63 |
| Alleen hoogtetoename boven het park (WINS50 v₁₁₅/v₁₀) | 1,303 | 1,364 | 1,257 | 1,227 | 1,144 | 1,165 | 1,116 | 1,153 | 1,197 | 1,221 | 1,240 | 1,318 |
| F Beabuorren (60 m) | 1,178 | 1,154 | 1,088 | 1,048 | 1,002 | 0,996 | 1,010 | 1,038 | 1,120 | 1,136 | 1,169 | 1,196 |
| als α vanaf 10 m | 0,091 | 0,080 | 0,047 | 0,026 | 0,001 | −0,002 | 0,005 | 0,021 | 0,063 | 0,071 | 0,087 | 0,100 |

In de zomer neemt de wind boven het IJsselmeer in WINS50 minder toe met de hoogte dan in de winter. Dat seizoenspatroon lijkt op de oude, op productie afgestelde seizoens-α, maar komt hier uit het model, niet uit productie. De oude α werd op Houtribdijk alleen toegepast; dat station meet meer wind dan het gemiddelde van Houtribdijk en Stavoren, dus dezelfde α gaf toen een hogere wind op ashoogte.

**Status.** Geen productiegegeven is gebruikt voor de stationskeuze, de factor of de ashoogte.
WINS50 is een model, geen meting op ashoogte; er is geen onafhankelijke windmeting op 115 m bij
het park. De hoogtevertaling is daarom een onderbouwde aanname. De gevoeligheid (F van het
laagste en het hoogste WINS50-jaar, 109 m ashoogte, één station in plaats van twee) staat in
[vergelijking.md](vergelijking.md). In de kruisvalidatie op WINS50 geeft een vaste factor per
maand enkele procenten minder modelenergie dan de WINS50-wind zelf, omdat F × ff minder spreiding
heeft dan de modelwind; ook dat staat daar.

In de webapp is per park een eigen `α` in te vullen (0 tot 0,6); die vervangt de factor voor
de hele dag, ook in de CSV-export: `v_h = ff × (h/10)^α`. Dat is bedoeld om de gevoeligheid te
zien, niet als betere schatting.

**Oude werkwijze.** Tot oktober 2026 gebruikte het dagprofiel Houtribdijk met
`α = 0,115 + 0,065 cos(2π(n−1)/365)` (0,18 begin januari, 0,05 begin juli) en de opsplitsing per
tien minuten de hoogste van Houtribdijk en Stavoren met dezelfde `α`. Die `α` en die stationskeuzes
waren afgesteld op gemeten productie (sectie 7). Ze blijven beschikbaar als windmethode
`productie_houtribdijk` en `productie_hoogste`; zie [afhankelijkheden.md](afhankelijkheden.md).

## 2. Benaderde curve voor Fryslân

Met `v = v_h` geldt per turbine:

```math
P(v)=\begin{cases}
0 & v<3\\
4300\dfrac{v^3-3^3}{11{,}5^3-3^3} & 3\leq v<11{,}5\\
4300 & 11{,}5\leq v\leq25\\
0 & v>25
\end{cases}
\quad[\mathrm{kW}]
```
De aanloop is genormaliseerd: bij 3 m/s is de teller nul, bij 11,5 m/s is teller
gelijk aan noemer en wordt 4.300 kW bereikt. Anders dan `(v−3)³` gebruikt dit
model `v³−3³`. Er is geen bewijs dat deze eenvoudige curve nauwkeuriger is dan
een andere benadering voor deze specifieke turbine; het is een transparante
keuze die bij de afgesproken vereenvoudiging past.

De derde macht is geïnspireerd op:

```math
P_\mathrm{wind}=\frac12\rho A v^3,\qquad
P_\mathrm{turbine}=C_p P_\mathrm{wind}
```
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

```math
P(v)=P_0+(P_1-P_0)\frac{v-v_0}{v_1-v_0}
```
Dit is lineaire interpolatie: een snelheid halverwege twee punten geeft het
vermogen halverwege die punten. De punten komen uit de grafiek voor
[Siemens SWT-1.3-62](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62).
Het is een secundaire bron, geen gecertificeerde fabrikantcurve; de
referentieluchtdichtheid is onbekend. Vanaf 25 m/s wordt het vermogen in dit
model nul, volgens de cut-out in deze datasheet. Dat grensgedrag verschilt dus
bij precies 25 m/s van het gekozen Fryslân-scenario.

## 4. Parken optellen en energie berekenen

```math
P_\mathrm{park}[\mathrm{MW}]=\frac{N\,P_\mathrm{turbine}[\mathrm{kW}]}{1000}
```
```math
P_\mathrm{samen}(t)=P_\text{Fryslân}(t)+P_\mathrm{Beabuorren}(t)
```
```math
E_\mathrm{dag}[\mathrm{MWh}]=\sum_{i}\frac{P_i[\mathrm{MW}]}{6}
```
```math
\mathrm{vollasturen}=\frac{E[\mathrm{MWh}]}{P_\mathrm{nominaal}[\mathrm{MW}]}
```
Vollasturen zijn het aantal uren dat het park op vol vermogen had moeten draaien
voor dezelfde opbrengst: 382,7 MW voor Fryslân, 10,4 MW voor Beabuorren en
393,1 MW samen. Voor een geselecteerd tijdvak gelden dezelfde formules, met de
som alleen over de gekozen minuten.

`N` is 89 voor Fryslân en 8 voor Beabuorren. `i` loopt over de oorspronkelijke
KNMI-tienminutenintervallen met hun midden in de Nederlandse kalenderdag: 144, of 138 en 150 bij
de klokwissel. Elk interval duurt 1/6 uur. De minuutlijn in de grafiek is alleen weergave; een
geselecteerd tijdvak in de grafiek wordt wel uit die minuutlijn opgeteld. Een ontbrekend interval
maakt de volledige dagopbrengst onbekend; ontbrekende waarden worden nooit als nul opgeteld.

Drie grootheden blijven gescheiden, in de berekening, op de pagina en in de exports:

| Grootheid | Eenheid | Wat erin zit |
| --- | --- | --- |
| Wind op ashoogte | m/s | Stationswind × F (sectie 1) |
| Gemodelleerde mogelijke elektrische opbrengst | MW, MWh | Turbinecurve (sectie 2 en 3), zogverlies (sectie 5), **100 % beschikbaarheid**; geen afregeling, stilstand, netbeperking, elektrische verliezen of luchtdichtheidcorrectie |
| Gemeten productie | MWh per dag | Dagtotalen van Windpark Fryslân, 2022–2025; alleen ter vergelijking |

Van de modelopbrengst gaat 10 % van Fryslân plus heel Beabuorren naar de waterstofsimulatie
(`/opsplitsing`), als bruto aanbod vóór BoP. Het dagprofiel toont dat deel apart.

## 5. Zogverlies

Turbines in het zog van andere turbines vangen tragere en turbulentere wind.
Standaard benaderen we dat met één parkgemiddelde snelheidsverlaging `d`:

```math
v_\mathrm{eff}=v_h(1-d),\qquad
P_\mathrm{turbine}=\begin{cases}
P(v_\mathrm{eff}) & P(v_h)>0\\
0 & \text{anders}
\end{cases}
```
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

```math
v(t)=v_0+(v_1-v_0)\frac{t-t_0}{t_1-t_0}
```
De [KNMI-documentatie](https://dataplatform.knmi.nl/dataset/docs/10-minute-in-situ-meteorological-observations-1-0)
beschrijft tienminutengemiddelden met een tijdstempel aan het intervaleinde in
UTC. We plaatsen het gemiddelde op het intervalmidden, vijf minuten eerder,
en interpoleren wind lineair vóór hoogtecorrectie en vermogensberekening.
Een meetgat, ongeldige windwaarde of interval langer dan tien minuten wordt
niet overbrugd. De Nederlandse kalenderdag bevat normaal 1.440 minuten, maar
1.380 of 1.500 tijdens de klokwissel.

De stippen tonen vermogen **berekend uit de oorspronkelijke KNMI-gemiddelden**.
Ze zijn geen gemeten vermogenswaarden. De windgrafiek toont de wind op ashoogte;
de stippen zijn de oorspronkelijke tienminutenwaarden, vertaald naar ashoogte. In de gecombineerde grafiek verschijnt een stip
alleen met waarden voor beide parken op hetzelfde intervalmidden. De stippen
kunnen worden verborgen met de checkbox, zonder data opnieuw op te halen.

De minuutlijn geeft geen extra waargenomen windinformatie. Door niet-lineariteit
is `P(gemiddelde wind)` niet gelijk aan `gemiddeld P(wind)`. Vooral bij de
inschakel- en uitschakelgrenzen blijft er onzekerheid. Het model is bedoeld om
patronen te verkennen, niet om exacte productie of echte minuutfluctuaties te
voorspellen.

## 7. Oude ijking op productiedata Fryslân (niet meer in gebruik)

Deze sectie beschrijft hoe de vroegere `α` en stationskeuzes op gemeten productie zijn
afgesteld. Ze zijn vervangen door de productie-onafhankelijke methode van sectie 1, omdat een
op productie afgestelde wind daarna niet meer eerlijk met diezelfde productie te vergelijken is.
De oude methode blijft herhaalbaar (`productie_houtribdijk`, `productie_hoogste`,
`python3 -m windprofiel.ijking`); zie [afhankelijkheden.md](afhankelijkheden.md). De oorzaken die
hieronder vroeger aan verschillen werden toegeschreven, zijn niet met aanvullende gegevens
vastgesteld en staan nu als verschil beschreven.

De oorspronkelijke keuze, Stavoren met `α = 0,10`, gaf voor 4 december 2025
1,69 GWh terwijl het park ongeveer 4,5 GWh produceerde. Daarom zijn station en
exponent toen afgesteld op dagopbrengsten uit de app van Windpark Fryslân, met het
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

Gezocht is over acht stations binnen 45 km en een vaste `α` per seizoen; Houtribdijk gaf in de
winter de kleinste afwijking. Bij die afstelling zijn dagen weggelaten waarop de gemeten
productie ver onder het model lag: 1 januari 2026 (6,7 GWh tegen ~9,1 GWh), 7 juli 2025
(1,3 GWh; ook met `α = 0` nog ~3,9 GWh in het model), 5 oktober 2025 (circa 2,8 GWh; tot 17 uur
~5 MWh per uur bij 9 tot 14 m/s op 10 m) en 13 oktober 2026 (uurproductie die middag vlak rond
180 MW). Toen is dat toegeschreven aan afregeling of stilstand. Daarvoor zijn geen gegevens
beschikbaar; het blijft een verschil tussen model en gemeten productie. Dagen waarop het model
lager lag dan de productie, zijn nooit weggelaten. Die eenzijdige selectie trekt de afgestelde
`α` omhoog.

In oktober 2026 is de keuze opnieuw getoetst met tien dagen (6, 7, 10 en 12 oktober 2026 erbij).
Houtribdijk gaf de kleinste RMS-afwijking per dag (0,27 GWh, beste `α` 0,12 + 0,07 cos), het
gemiddelde van Houtribdijk en Stavoren 0,29 GWh, Stavoren 0,44 GWh. **Dit was een kleine
steekproef**: vier winter-, twee zomer- en vier herfstdagen.

### Oude ijking op vier jaar dagproductie (2022–2025)

`ijking.py` past `α = a + b cos(…)` aan op 1.442 dagen met KNMI-wind en productie. De
selectieregel: dagen waarop de productie onder een grens maal het model bleef (en minstens
0,5 GWh lager) tellen niet mee; daarna opnieuw fitten tot de selectie stabiel is. Die dagen
heten hier **dagen met groot verschil (model hoger)**; vroeger ‘verdachte dagen’. De regel
veronderstelt dat alleen het park lager kan uitvallen dan het model, niet het model zelf.

| Wind voor Fryslân | Beste `α` (grens 75 %) | RMS-afwijking per dag | Dagen met groot verschil (model hoger) |
| --- | --- | ---: | ---: |
| Houtribdijk | 0,110 + 0,065 cos | 0,82 GWh | 418 |
| Hoogste van Houtribdijk en Stavoren per tien minuten | 0,095 + 0,070 cos | 0,77 GWh | 383 |

| Grens | Beste `α` (winter / zomer) | Behouden dagen |
| ---: | --- | ---: |
| 65 % | 0,155 / 0,015 | 1.198 |
| 75 % | 0,165 / 0,025 | 1.059 |
| 85 % | 0,180 / 0,050 | 791 |
| geen | 0,135 / 0,0 | 1.442 |

Het niveau van `α` hangt af van de gekozen grens. De grens van 85 % is gekozen omdat de fit
dan samenvalt met de al gebruikte formule: een kringredenering. Bij 85 % blijven 791 van de
1.442 dagen over. De weggelaten dagen liggen verspreid over alle maanden; uit dagtotalen is
niet vast te stellen waardoor de productie daar lager lag dan het model.

`python3 -m windprofiel.ijking` herhaalt deze tabellen met de oude windmethode
`productie_hoogste`, zonder nieuwe aanvragen bij de app van Windpark Fryslân.

## Bronnen en status van de getallen

| Gegeven | Waarde | Onderbouwing |
| --- | --- | --- |
| KNMI-bron | EDR, `10-minute-in-situ-meteorological-observations/1.0` | [Officiële dataset](https://dataplatform.knmi.nl/dataset/10-minute-in-situ-meteorological-observations-1-0), `ff` in m/s, representatief voor 10 m, niet handmatig gevalideerd |
| Stations | Gemiddelde van Houtribdijk (`06258`) en Stavoren (`06267`), beide parken | Stations op het IJsselmeer; best passend bij WINS50 op de parklocatie ([databronnen](databronnen.md#stations)); geen productie |
| Hoogtevertaling | F per park en maand | WINS50 (HARMONIE-AROME), 2019–2021, sectie 1; aanname zonder meting op ashoogte |
| Fryslân | 89 × 4,3 MW | [Exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/) |
| Fryslân-ashoogte | 115 m boven water | ‘Hoogte boven water 180 m’ ([exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/)) − 130 m / 2; 109 m (persbericht 2018) als gevoeligheid ([databronnen](databronnen.md#ashoogte-en-verticale-referentie)) |
| Fryslân-grenzen | 3 / 11,5 / 25 m/s | Afgesproken scenario-keuze; niet bevestigd door fabrikant |
| Beabuorren | 8 turbines, 10,4 MW | [Onderhoudsbedrijf Rengineers](https://rengineers.eu/nieuw/wynpark-beaborren-25-jaar/) |
| Beabuorren-model | SWT-1.3-62 | [The Wind Power](https://www.thewindpower.net/windfarm_en_6263_beabuorren.php), secundaire bron |
| Beabuorren-ashoogte | 60 m | [Lokaal bericht uit 2007](https://tsjerkwert.nl/start-opschaling-van-het-wynpark/); niet bevestigd voor alle acht turbines |
| Beabuorren-curve | Numerieke grafiekpunten, cut-out 25 m/s | [Wind-Turbine-Models](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62), secundaire bron |
| Zogverlies | 5 % Fryslân / 2 % Beabuorren minder wind | Onze scenario-keuze; niet gekalibreerd, geen windrichting of opstelling |
| Beschikbaarheid | 100 % | Modelaanname: mogelijke opbrengst, geen afregeling, stilstand of netbeperking |

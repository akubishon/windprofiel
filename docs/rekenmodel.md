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
gebruikt `h = 115 m, α = 0,18`; Beabuorren `h = 60 m, α = 0,20`.
Deze correctie verandert het niveau van de hele reeks en daarmee, via de
vermogenscurve, ook de grootte van de schommelingen.

De [wind profile power law](https://en.wikipedia.org/wiki/Wind_profile_power_law)
beschrijft de empirische formule en de afhankelijkheid van terrein en
atmosferische stabiliteit. De bron noemt circa 0,11 boven open water in neutrale
omstandigheden. In stabiele winterlucht is de toename met de hoogte groter.
**0,18 voor Fryslân is geijkt op productiedata (sectie 7); 0,20 voor land is een
modelkeuze, geen gemeten exponent voor Beabuorren.** Een vaste exponent van
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

| Dag | Productie | Model (Houtribdijk, α 0,18) | Oud (Stavoren, α 0,10) |
| --- | --- | --- | --- |
| 4 december 2025 | ~4,5 GWh | 4,6 GWh | 1,7 GWh |
| 18 december 2025 | 8,8 GWh | 8,9 GWh | 7,5 GWh |
| 19 december 2025 | 5,9 GWh | 5,7 GWh | 1,9 GWh |
| 28 december 2025 | 0,78 GWh | 0,55 GWh | 0,03 GWh |

Gezocht is over zeven stations binnen 45 km en `α` van 0,05 tot 0,40. Houtribdijk
gaf de kleinste afwijking (circa 180 MWh RMS); Stavoren haalde op zijn best
circa 600 MWh, met een veel hogere exponent. Houtribdijk ligt midden in het
IJsselmeer en vangt vermoedelijk de wind boven open water beter dan het
kuststation Stavoren.

1 januari 2026 (6,7 GWh) is niet meegenomen: de wind was de hele dag even sterk
als op 18 december en elk model geeft vrijwel vol vermogen (~9,1 GWh). Het
verschil past bij afregeling of stilstand, die dit model niet kent.

**Vier dagen is een kleine steekproef**, alle in de winter. Op stabiele
winterdagen is de exponent hoger dan in een onstabiele zomer, dus in de zomer
kan het model overschatten. Meer productiedagen uit andere seizoenen zijn nodig
om dit te controleren.

## Bronnen en status van de getallen

| Gegeven | Waarde | Onderbouwing |
| --- | --- | --- |
| KNMI-bron | EDR, `10-minute-in-situ-meteorological-observations/1.0` | [Officiële dataset](https://dataplatform.knmi.nl/dataset/10-minute-in-situ-meteorological-observations-1-0), `ff` in m/s, niet handmatig gevalideerd |
| Fryslân | 89 × 4,3 MW | [Exploitant](https://www.windparkfryslan.nl/onderwerpen/windturbines/) |
| Fryslân-ashoogte | circa 115 m | Afgeleid: 180 m tiphoogte − 130 m rotordiameter / 2, [factsheet](https://www.windparkfryslan.nl/wp-content/uploads/2020/05/Factsheet-Windpark-Fryslan.pdf) |
| Fryslân-grenzen | 3 / 11,5 / 25 m/s | Afgesproken scenario-keuze; niet bevestigd door fabrikant |
| Hoogte-exponenten | 0,18 Fryslân / 0,20 land | Fryslân geijkt op vier dagen (sectie 7); land is een modelkeuze; [achtergrond](https://en.wikipedia.org/wiki/Wind_profile_power_law) |
| Fryslân-station | Houtribdijk (`06258`) | Beste aansluiting op productiedata van de vijf IJsselmeer- en kuststations (sectie 7) |
| Beabuorren | 8 turbines, 10,4 MW | [Onderhoudsbedrijf Rengineers](https://rengineers.eu/nieuw/wynpark-beaborren-25-jaar/) |
| Beabuorren-model | SWT-1.3-62 | [The Wind Power](https://www.thewindpower.net/windfarm_en_6263_beabuorren.php), secundaire bron |
| Beabuorren-ashoogte | 60 m | [Lokaal bericht uit 2007](https://tsjerkwert.nl/start-opschaling-van-het-wynpark/); niet bevestigd voor alle acht turbines |
| Beabuorren-curve | Numerieke grafiekpunten, cut-out 25 m/s | [Wind-Turbine-Models](https://en.wind-turbine-models.com/turbines/1457-siemens-swt-1-3-62), secundaire bron |
| Zogverlies | 5 % Fryslân / 2 % Beabuorren minder wind | Onze scenario-keuze; niet gekalibreerd, geen windrichting of opstelling |

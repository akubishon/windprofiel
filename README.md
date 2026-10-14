# Windprofiel

Een lokale webapp met datumkeuze voor 2025, historische KNMI-winddata en drie
panelen: Windpark Fryslân, Wynpark Beabuorren en hun gecombineerde vermogen.

## Starten

Python 3.12 of nieuwer met de standaardbibliotheek is voldoende; er zijn geen
externe pakketten nodig. Configureer `KNMI_EDR_API_KEY` via de beveiligde
omgevingsinstellingen voor `api.dataplatform.knmi.nl`. De app houdt de sleutel
op de server, buiten de browser en de repository.

Vanuit de bestaande checkout:

```sh
cd /workspace/windprofiel
python3 -m windprofiel.server --port 8000
```

De server luistert alleen lokaal. Gebruik de bestaande checkout; elke cloudtaak
heeft al een geïsoleerde omgeving, dus maak geen extra Git-worktree voor setup.

## Databron en beperkingen

De app gebruikt de officiële KNMI EDR API en de dataset
`10-minute-in-situ-meteorological-observations` (versie 1.0). Minuutwaarden zijn
lineair geïnterpoleerde tienminutengemiddelden, geen minuutmetingen. Meetgaten
blijven ontbrekend. De Nederlandse kalenderdag volgt zomer- en wintertijd.

Beabuorren gebruikt een gepubliceerde secundaire turbinecurve. Fryslân gebruikt
standaard een expliciet benaderd kubisch model: in de aanloop
`P = 4300 * (v³ - 3³) / (11.5³ - 3³)` kW per turbine, met wind op ashoogte.
Onder 3 m/s is het vermogen nul, van 11,5 tot en met 25 m/s 4.300 kW, boven
25 m/s nul. De drie snelheidgrenzen zijn gekozen scenario-aannames, geen
bevestigde turbinespecificaties. Alle drie de grafieken tonen nu geschat vermogen.
Stippen markeren berekeningen uit oorspronkelijke tienminutengemiddelden; de
minuutlijn ertussen is interpolatie. Zie [formules en bronnen](docs/rekenmodel.md).
Een geüploade passende Fryslân-curve krijgt voorrang op dit model.

Een curve kan via de webapp als JSON worden toegevoegd. Formaat: `model` moet
exact de getoonde turbinenaam zijn; `source` is een HTTPS-bron-URL; `cut_out` is
in m/s; `points` bevat oplopende paren van windsnelheid in m/s en vermogen in kW.
De punten beginnen bij nul vermogen, bereiken het nominale vermogen en eindigen
onder cut-out. Een optioneel tekstveld `status` beschrijft bron en beperkingen.
Formaatvalidatie bewijst niet dat de curve gecertificeerd is. Uploads staan onder
`.cache/curves`; KNMI-antwoorden onder `.cache/knmi`. Deze lokale bestanden en
`.env` zijn uitgesloten van Git.

De app heeft datumkeuze, vorige/volgende dag, stationkeuze, hoverwaarden,
CSV-download en broninformatie. CSV-velden voor ontbrekend vermogen blijven leeg.
Bekijk [bronnen, rekenwijze en validatie](docs/databronnen.md) voor alle aannames.

## Controle

```sh
python3 -m windprofiel.knmi
python3 -m unittest discover -s tests -v
```

De eerste opdracht controleert echte API-toegang. De tweede voert onafhankelijke
unit-tests uit zonder netwerk of sleutel. Bij wijziging van de webapp is ook
`node --check windprofiel/static/app.js` bruikbaar als JavaScript-syntaxcontrole.

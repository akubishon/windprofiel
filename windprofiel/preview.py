"""Maak een zelfstandige HTML-pagina van echte KNMI-dagprofielen."""

import argparse
import json
from datetime import date
from pathlib import Path

from .application import build_profile


def standalone_html(profiles: dict) -> str:
    static = Path(__file__).parent / "static"
    page = (static / "index.html").read_text()
    data = json.dumps({"profiles": profiles}, ensure_ascii=False, allow_nan=False).replace("<", "\\u003c")
    styles = (static / "style.css").read_text()
    script = (static / "app.js").read_text()
    page = page.replace('<link rel="stylesheet" href="./style.css"><script src="./app.js" defer></script>',
                        "<style>" + styles + "</style>")
    # De opsplitsingspagina draait alleen met de Python-server.
    page = page.replace('\n      <a class="page-link" href="/opsplitsing">Elektrolyser opsplitsen: één grote of meerdere modules? →</a>', "")
    page = page.replace('</body>', '<script>window.WINDPROFIEL_PREVIEW=' + data + ';</script>\n<script>' + script + '</script>\n</body>')
    first_day = next(iter(profiles))
    return page.replace('value="2025-01-15"', 'value="' + first_day + '"')


def main():
    parser = argparse.ArgumentParser(description="Exporteer echte KNMI-profielen als zelfstandige HTML.")
    parser.add_argument("--dates", nargs="+", default=["2025-01-15", "2025-03-30", "2025-10-26"])
    parser.add_argument("--output", type=Path, default=Path("index.html"))
    args = parser.parse_args()
    profiles = {day: build_profile(date.fromisoformat(day)) for day in args.dates}
    args.output.write_text(standalone_html(profiles), encoding="utf-8")
    print(f"{args.output}: {len(profiles)} echte KNMI-dagprofielen, zonder API-sleutel.")


if __name__ == "__main__":
    main()

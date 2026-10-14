"""Lokale webapp zonder externe JavaScript- of Python-afhankelijkheden."""

import argparse
import csv
import io
import json
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .application import PARKS, ROOT, build_profile, validate_curve
from .knmi import KNMIClient, KNMIError, load_env_file

STATIC = Path(__file__).parent / "static"


class Handler(BaseHTTPRequestHandler):
    def respond(self, status: int, data: bytes, content_type: str):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(data)

    def json_response(self, status: int, data: dict):
        self.respond(status, json.dumps(data, allow_nan=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        request = urlsplit(self.path)
        if request.path in ("/", "/app.js", "/style.css"):
            name = {"/": "index.html", "/app.js": "app.js", "/style.css": "style.css"}[request.path]
            mime = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}[name]
            self.respond(200, (STATIC / name).read_bytes(), mime + "; charset=utf-8")
            return
        if request.path not in ("/api/stations", "/api/profile", "/api/export.csv"):
            self.json_response(404, {"error": "Niet gevonden."})
            return
        try:
            if request.path == "/api/stations":
                result = KNMIClient(ROOT / ".cache" / "knmi").locations()
                self.json_response(200, {"stations": result.get("features", []), "parks": PARKS})
                return
            query = parse_qs(request.query)
            selected = date.fromisoformat(query.get("date", [""])[0])
            stations = {key: query.get(key, [park["station"]])[0] for key, park in PARKS.items()}
            profile = build_profile(selected, stations, wake=query.get("wake", ["1"])[0] != "0")
            if request.path == "/api/profile":
                self.json_response(200, profile)
                return
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["tijd_Europe_Amsterdam", "fryslan_wind_10m_ms", "beabuorren_wind_10m_ms",
                             "fryslan_wind_ashoogte_ms", "beabuorren_wind_ashoogte_ms",
                             "fryslan_geschat_MW", "beabuorren_geschat_MW", "gecombineerd_geschat_MW"])
            a, b = profile["parks"]["fryslan"], profile["parks"]["beabuorren"]
            for i, timestamp in enumerate(profile["timestamps"]):
                writer.writerow([timestamp, a["wind_ms"][i], b["wind_ms"][i], a["hub_wind_ms"][i], b["hub_wind_ms"][i],
                                 a["power_mw"][i], b["power_mw"][i], profile["combined_mw"][i]])
            self.respond(200, output.getvalue().encode(), "text/csv; charset=utf-8")
        except KNMIError as exc:
            self.json_response(502, {"error": str(exc)})
        except (ValueError, TypeError):
            self.json_response(400, {"error": "Controleer datum (2025), station en vermogenscurve."})

    def do_POST(self):
        path = urlsplit(self.path).path
        park_id = path.removeprefix("/api/curves/")
        if not path.startswith("/api/curves/") or park_id not in PARKS:
            self.json_response(404, {"error": "Niet gevonden."})
            return
        origin = self.headers.get("Origin")
        if origin and urlsplit(origin).netloc != self.headers.get("Host"):
            self.json_response(403, {"error": "Gebruik de webapp om een curve toe te voegen."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 100_000 or self.headers.get_content_type() != "application/json":
                raise ValueError("Lever een JSON-curve aan van maximaal 100 kB.")
            curve = validate_curve(json.loads(self.rfile.read(length)), park_id)
            path = ROOT / ".cache" / "curves" / f"{park_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            # Alleen de twee vaste bestandsnamen; geen pad uit de upload.
            path.write_text(json.dumps(curve, indent=2), encoding="utf-8")
            self.json_response(200, {"saved": True, "model": curve["model"]})
        except (ValueError, TypeError, UnicodeError) as exc:
            self.json_response(400, {"error": str(exc)})


def main():
    parser = argparse.ArgumentParser(description="Start de Windprofiel-webapp.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    load_env_file(ROOT / ".env")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Windprofiel luistert lokaal op poort {args.port}.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

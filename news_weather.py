#!/usr/bin/env python3
"""Fetch latest Fairfax, VA headlines and current/tomorrow weather.

Uses Google News RSS for headlines and Open-Meteo for weather (no API key).
"""
from __future__ import annotations

import argparse
import datetime
import json
import sys
from typing import List, Tuple
from urllib.parse import quote_plus

try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    requests = None
    _HAS_REQUESTS = False

import urllib.request as _urlreq
import urllib.parse as _urlparse
import xml.etree.ElementTree as ET


class _SimpleResponse:
    def __init__(self, body: bytes, status: int = 200, headers=None):
        self._body = body
        self.status_code = status
        self.headers = headers or {}

    @property
    def content(self) -> bytes:
        return self._body

    @property
    def text(self) -> str:
        return self._body.decode('utf-8', errors='replace')

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP status {self.status_code}")


def _http_get(url: str, params: dict | None = None, timeout: int = 10):
    if _HAS_REQUESTS and requests is not None:
        return requests.get(url, params=params, timeout=timeout)

    if params:
        qs = _urlparse.urlencode(params)
        url = url + ("?" + qs)
    req = _urlreq.Request(url, headers={"User-Agent": "news-weather-script/1.0"})
    with _urlreq.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return _SimpleResponse(body, status=resp.getcode(), headers=dict(resp.getheaders()))

DEFAULT_LAT = 38.8462
DEFAULT_LON = -77.3064


def fetch_headlines(query: str = "Fairfax, VA", limit: int = 5) -> List[Tuple[str, str]]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    resp = _http_get(url, timeout=10)
    resp.raise_for_status()
    root = ET.fromstring(resp.content)
    items = []
    for item in root.findall('.//item')[:limit]:
        title = item.findtext('title') or 'No title'
        link = item.findtext('link') or ''
        items.append((title, link))
    return items


WEATHERCODE: dict = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def fetch_weather(lat: float, lon: float) -> dict:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": "true",
        "daily": ",".join(["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "weathercode"]),
        "timezone": "auto",
        "temperature_unit": "fahrenheit",
        "forecast_days": 2,
    }
    url = "https://api.open-meteo.com/v1/forecast"
    resp = _http_get(url, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def mm_to_inches(mm: float) -> float:
    return mm / 25.4


def describe_tomorrow(weather_json: dict) -> str:
    try:
        daily = weather_json["daily"]
        times = daily["time"]
        # tomorrow is index 1 (0 = today)
        idx = 1
        date = times[idx]
        tmax = daily["temperature_2m_max"][idx]
        tmin = daily["temperature_2m_min"][idx]
        precip_mm = daily.get("precipitation_sum", [0, 0])[idx]
        wcode = daily.get("weathercode", [0, 0])[idx]
    except Exception:
        return "Tomorrow's forecast is unavailable."

    precip_in = mm_to_inches(precip_mm)
    wdesc = WEATHERCODE.get(wcode, f"Weather code {wcode}")

    pop_phrase = ""
    if precip_in >= 0.2:
        pop_phrase = "Precipitation likely"
    elif precip_in >= 0.05:
        pop_phrase = "A chance of light precipitation"
    else:
        pop_phrase = "Mostly dry"

    return f"{date}: {wdesc}. High {tmax:.0f}°F, low {tmin:.0f}°F. {pop_phrase} (expected {precip_in:.2f}\" precipitation)."


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Fairfax headlines + weather summary")
    p.add_argument("--lat", type=float, default=DEFAULT_LAT, help="Latitude (default Fairfax)")
    p.add_argument("--lon", type=float, default=DEFAULT_LON, help="Longitude (default Fairfax)")
    p.add_argument("--headlines", type=int, default=5, help="Number of headlines to show")
    args = p.parse_args(argv)

    print("Fetching latest headlines for Fairfax, VA...")
    try:
        headlines = fetch_headlines("Fairfax, VA", limit=args.headlines)
    except Exception as e:
        print(f"Failed to fetch headlines: {e}")
        headlines = []

    print()
    print("Latest headlines:")
    if headlines:
        for i, (title, link) in enumerate(headlines, start=1):
            print(f"{i}. {title}")
            if link:
                print(f"   {link}")
    else:
        print("No headlines available.")

    print()
    print("Fetching weather (Open-Meteo)...")
    try:
        w = fetch_weather(args.lat, args.lon)
    except Exception as e:
        print(f"Failed to fetch weather: {e}")
        return 1

    current = w.get("current_weather") or {}
    temp = current.get("temperature")
    time = current.get("time")
    if temp is not None:
        print(f"Current temperature in Fairfax, VA: {temp:.1f}°F (as of {time})")
    else:
        print("Current temperature unavailable.")

    print()
    print("Tomorrow's outlook:")
    print(describe_tomorrow(w))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

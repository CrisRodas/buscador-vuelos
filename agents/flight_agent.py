"""Agente de busqueda de vuelos nacionales e internacionales.

Usa la Data Access API de Travelpayouts (gratis) si hay TRAVELPAYOUTS_TOKEN;
si no, genera ofertas mock realistas para que todo funcione sin claves.

Endpoint principal: /v1/prices/cheap, que devuelve el billete mas barato
directo, con 1 escala y con 2 escalas para la ruta. Los precios vienen de
una cache (vuelos encontrados por usuarios de Aviasales en los ultimos dias).
Devuelve una lista de dicts normalizados ordenados por precio.
"""
import random
from datetime import datetime, timedelta

import requests

from config import TRAVELPAYOUTS_TOKEN

_API = "http://api.travelpayouts.com"

# Aerolineas de ejemplo para el modo mock
_MOCK_AIRLINES = [
    ("Avianca", "AV"),
    ("LATAM", "LA"),
    ("Copa Airlines", "CM"),
    ("Iberia", "IB"),
    ("American Airlines", "AA"),
    ("Wingo", "P5"),
]

# Cache simple de nombres de aerolinea por codigo IATA
_airline_names: dict[str, str] = {}


def _load_airline_names() -> None:
    """Carga el catalogo de aerolineas de Travelpayouts (una sola vez)."""
    if _airline_names:
        return
    try:
        resp = requests.get(f"{_API}/data/airlines.json", timeout=20)
        resp.raise_for_status()
        for a in resp.json():
            code = a.get("code") or a.get("iata")
            if code and a.get("name"):
                _airline_names[code] = a["name"]
    except Exception as e:
        print(f"[flight_agent] No se pudo cargar catalogo de aerolineas ({e}).")


def _airline_name(code: str) -> str:
    return _airline_names.get(code, code)


def _tp_cheap(origin: str, destination: str, date: str,
              return_date: str | None, currency: str) -> list[dict]:
    """Endpoint /v1/prices/cheap: mas barato directo, 1 y 2 escalas."""
    params = {
        "origin": origin,
        "destination": destination,
        "depart_date": date,
        "currency": currency.lower(),
        "token": TRAVELPAYOUTS_TOKEN,
    }
    if return_date:
        params["return_date"] = return_date
    try:
        resp = requests.get(f"{_API}/v1/prices/cheap", params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") and body.get("data"):
            return _normalize_cheap(body["data"], origin, currency)
    except Exception as e:
        print(f"[flight_agent] cheap fallo ({e}).")
    return []


def _tp_calendar(origin: str, destination: str, date: str,
                 currency: str) -> list[dict]:
    """Endpoint /v1/prices/calendar: precio mas barato por cada dia del mes."""
    params = {
        "origin": origin,
        "destination": destination,
        "depart_date": date,
        "calendar_type": "departure_date",
        "currency": currency.lower(),
        "token": TRAVELPAYOUTS_TOKEN,
    }
    try:
        resp = requests.get(f"{_API}/v1/prices/calendar", params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        if body.get("success") and body.get("data"):
            return _normalize_calendar(body["data"], currency)
    except Exception as e:
        print(f"[flight_agent] calendar fallo ({e}).")
    return []


def _tp_search(origin: str, destination: str, date: str,
               return_date: str | None, currency: str) -> list[dict] | None:
    """Combina cheap + calendar para tener mas opciones. None si todo vacio."""
    _load_airline_names()
    offers = _tp_cheap(origin, destination, date, return_date, currency)
    offers += _tp_calendar(origin, destination, date, currency)
    if not offers:
        print("[flight_agent] Travelpayouts sin resultados para esa ruta/fecha.")
        return None
    return offers


def _mk_offer(info: dict, origin: str, dest: str, stops: int,
              currency: str) -> dict:
    code = info.get("airline", "")
    return {
        "airline": code,
        "airline_name": _airline_name(code),
        "price": float(info.get("price", 0)),
        "currency": currency.upper(),
        "stops": stops,
        "departure": info.get("departure_at", ""),
        "arrival": info.get("return_at", ""),
        "flight_number": info.get("flight_number"),
        "duration_min": 0,  # estos endpoints no dan duracion
        "origin": origin,
        "destination": dest,
        "source": "travelpayouts",
    }


def _normalize_cheap(data: dict, origin: str, currency: str) -> list[dict]:
    """data = { "DEST": { "0": {...}, "1": {...} } }, clave = numero de escalas."""
    offers = []
    for dest, by_stops in data.items():
        for stops_str, info in by_stops.items():
            offers.append(_mk_offer(info, origin, dest, int(stops_str), currency))
    return offers


def _normalize_calendar(data: dict, currency: str) -> list[dict]:
    """data = { "YYYY-MM-DD": { origin, destination, transfers, ... } }."""
    offers = []
    for info in data.values():
        offers.append(_mk_offer(
            info, info.get("origin", ""), info.get("destination", ""),
            int(info.get("transfers", 0)), currency))
    return offers


def _mock_search(origin: str, destination: str, date: str,
                 adults: int, currency: str) -> list[dict]:
    """Genera ofertas simuladas realistas (sin API)."""
    rng = random.Random(f"{origin}{destination}{date}")
    # Acepta 'YYYY-MM' (solo mes) o 'YYYY-MM-DD'
    date_full = f"{date}-01" if len(date) == 7 else date
    try:
        dep_day = datetime.fromisoformat(date_full)
    except ValueError:
        dep_day = datetime.now()
    international = origin[:2] != destination[:2]
    base = rng.randint(180, 650) if international else rng.randint(45, 180)

    offers = []
    for _ in range(rng.randint(5, 8)):
        airline, code = rng.choice(_MOCK_AIRLINES)
        stops = rng.choices([0, 1, 2], weights=[5, 3, 1])[0]
        price = base * (1 - 0.12 * stops) * rng.uniform(0.85, 1.4)
        dur = rng.randint(70, 180) + stops * rng.randint(90, 240)
        dep_hour = rng.randint(5, 22)
        dep = dep_day.replace(hour=dep_hour, minute=rng.choice([0, 15, 30, 45]))
        arr = dep + timedelta(minutes=dur)
        offers.append({
            "airline": code,
            "airline_name": airline,
            "price": round(price * adults, 2),
            "currency": currency.upper(),
            "stops": stops,
            "departure": dep.isoformat(),
            "arrival": arr.isoformat(),
            "flight_number": None,
            "duration_min": dur,
            "origin": origin,
            "destination": destination,
            "source": "mock",
        })
    return offers


def search_flights(origin: str, destination: str, date: str,
                   adults: int = 1, currency: str = "USD",
                   return_date: str | None = None) -> list[dict]:
    """Busca vuelos y los devuelve ordenados por precio (mas barato primero).

    origin/destination: codigos IATA de ciudad (ej. BOG, MAD, MDE).
    date: fecha de salida 'YYYY-MM-DD' o 'YYYY-MM'.
    return_date: opcional, para vuelos de ida y vuelta.
    """
    offers = None
    if TRAVELPAYOUTS_TOKEN:
        offers = _tp_search(origin, destination, date, return_date, currency)
    if not offers:
        offers = _mock_search(origin, destination, date, adults, currency)

    # Quita duplicados por aerolinea + precio + fecha de salida + escalas
    seen = set()
    unique = []
    for o in offers:
        key = (o["airline"], o["price"], o["departure"][:10], o["stops"])
        if key not in seen:
            seen.add(key)
            unique.append(o)
    return sorted(unique, key=lambda o: o["price"])

"""Buscador de vuelos: encuentra los mas economicos y te ayuda a elegir.

Acepta nombres de ciudad ("Bogota", "Madrid") o codigos IATA (BOG, MAD).
Sin argumentos, entra en modo interactivo y te pregunta paso a paso.

Uso:
    python flights.py                                  # modo interactivo
    python flights.py --origin Bogota --destination Madrid --date 2026-12
    python flights.py --origin BOG --destination MDE --date 2026-12 --adults 2
"""
import argparse

from agents.flight_agent import search_flights
from agents.advisor_agent import advise
from agents.places_agent import resolve_city


def _fmt(o: dict) -> str:
    name = o.get("airline_name", o["airline"])
    stops = "Directo" if o["stops"] == 0 else f"{o['stops']} escala(s)"
    if o["duration_min"]:
        h, m = divmod(o["duration_min"], 60)
        dur = f"{h}h{m:02d}m"
    else:
        dur = "-"
    sale = o["departure"][:10] if len(o["departure"]) >= 10 else "-"
    return (f"{name:<22} {o['price']:>9.2f} {o['currency']}  "
            f"{stops:<12} {dur:<8} {sale}  score {o.get('score', '-')}")


def _resolve(label: str, query: str) -> tuple[str, str] | None:
    """Resuelve una ciudad e informa al usuario. None si no se encuentra."""
    found = resolve_city(query)
    if not found:
        print(f"  No reconoci '{query}' como {label}. "
              "Prueba con otro nombre o un codigo IATA (ej. BOG).")
        return None
    code, name = found
    print(f"  {label}: {name} ({code})")
    return found


def run(origin_q: str, destination_q: str, date: str, adults: int,
        currency: str, return_date: str | None, top: int) -> None:
    o = _resolve("Origen", origin_q)
    d = _resolve("Destino", destination_q)
    if not o or not d:
        return
    origin, destination = o[0], d[0]

    print(f"\nBuscando vuelos {origin} -> {destination} el {date} "
          f"({adults} pasajero(s))...")
    offers = search_flights(origin, destination, date, adults, currency,
                            return_date)
    if not offers:
        print("No se encontraron vuelos.")
        return

    result = advise(offers)
    ranked = result["ranked"]
    shown = ranked[:top]

    print(f"\nSe encontraron {len(ranked)} opciones "
          f"(fuente: {ranked[0]['source']}). Muestro las {len(shown)} mejores.\n")
    print(f"  TOP {len(shown)} POR MEJOR RELACION PRECIO/COMODIDAD")
    print("  " + "-" * 72)
    for i, item in enumerate(shown, 1):
        print(f"  {i:>2}. {_fmt(item)}")

    cheapest = min(ranked, key=lambda x: x["price"])
    print(f"\n  Mas barato de todos: {_fmt(cheapest)}")
    print("\n  RECOMENDACION DEL ASESOR:")
    print(f"  {result['advice']}\n")


def _ask(prompt: str, default: str | None = None) -> str:
    """Pregunta en consola, con valor por defecto opcional."""
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val or (default or "")


def interactive() -> None:
    """Flujo paso a paso para quien no quiere recordar los flags."""
    print("\n=== Buscador de vuelos (modo interactivo) ===")
    print("Puedes escribir el nombre de la ciudad o su codigo IATA.\n")
    origin_q = _ask("Ciudad de origen")
    destination_q = _ask("Ciudad de destino")
    date = _ask("Fecha de salida (YYYY-MM-DD o YYYY-MM)")
    return_date = _ask("Fecha de regreso (opcional, Enter para omitir)") or None
    adults = int(_ask("Numero de pasajeros", "1") or 1)
    currency = (_ask("Moneda", "USD") or "USD").upper()
    top = int(_ask("Cuantas opciones mostrar", "10") or 10)

    if not origin_q or not destination_q or not date:
        print("Faltan datos obligatorios (origen, destino y fecha).")
        return
    run(origin_q, destination_q, date, adults, currency, return_date, top)


def main() -> None:
    p = argparse.ArgumentParser(description="Buscador de vuelos economicos")
    p.add_argument("--origin", help="Ciudad o codigo IATA de origen")
    p.add_argument("--destination", help="Ciudad o codigo IATA de destino")
    p.add_argument("--date", help="Fecha de salida YYYY-MM-DD o YYYY-MM")
    p.add_argument("--adults", type=int, default=1, help="Numero de pasajeros")
    p.add_argument("--currency", default="USD", help="Moneda (ej. USD, EUR, COP)")
    p.add_argument("--return-date", dest="return_date", default=None,
                   help="Fecha de regreso (opcional, ida y vuelta)")
    p.add_argument("--top", type=int, default=10,
                   help="Cuantas opciones mostrar (por defecto 10)")
    args = p.parse_args()

    # Si faltan los datos clave, pasa a modo interactivo
    if not args.origin or not args.destination or not args.date:
        interactive()
    else:
        run(args.origin, args.destination, args.date, args.adults,
            args.currency.upper(), args.return_date, args.top)


if __name__ == "__main__":
    main()

"""Agente asesor: analiza las ofertas de vuelo y recomienda cual elegir.

No decide solo por precio: pondera precio, escalas, duracion y horario.
Usa Groq (gratis) para una explicacion en lenguaje natural si hay GROQ_API_KEY;
si no, genera la explicacion con una plantilla local.
"""
import json

import requests

from config import GROQ_API_KEY


def _score(offer: dict, cheapest: float, fastest: int, has_dur: bool) -> float:
    """Puntua una oferta de 0 a 100. Mas alto es mejor.

    Con duracion: precio 55%, duracion 30%, escalas 15%.
    Sin duracion (la API cheap no la da): precio 70%, escalas 30%.
    """
    price_score = cheapest / offer["price"] if offer["price"] else 0
    stop_score = {0: 1.0, 1: 0.7, 2: 0.4}.get(offer["stops"], 0.2)
    if has_dur:
        dur_score = fastest / offer["duration_min"] if offer["duration_min"] else 0
        total = price_score * 0.55 + dur_score * 0.30 + stop_score * 0.15
    else:
        total = price_score * 0.70 + stop_score * 0.30
    return round(total * 100, 1)


def rank_offers(offers: list[dict]) -> list[dict]:
    """Agrega una puntuacion a cada oferta y las ordena de mejor a peor."""
    if not offers:
        return []
    cheapest = min(o["price"] for o in offers)
    durations = [o["duration_min"] for o in offers if o["duration_min"]]
    has_dur = bool(durations)
    fastest = min(durations) if durations else 0
    for o in offers:
        o["score"] = _score(o, cheapest, fastest, has_dur)
    return sorted(offers, key=lambda o: o["score"], reverse=True)


def _fmt_offer(o: dict) -> str:
    name = o.get("airline_name", o["airline"])
    stops = "directo" if o["stops"] == 0 else f"{o['stops']} escala(s)"
    dur = ""
    if o["duration_min"]:
        h, m = divmod(o["duration_min"], 60)
        dur = f", {h}h{m:02d}m"
    sale = f", sale {o['departure'][11:16]}" if len(o["departure"]) >= 16 else ""
    return f"{name}: {o['price']} {o['currency']}, {stops}{dur}{sale}"


def _groq_advice(ranked: list[dict]) -> str | None:
    """Pide a Groq una recomendacion en lenguaje natural. None si falla."""
    listado = "\n".join(f"{i+1}. {_fmt_offer(o)} (score {o['score']})"
                        for i, o in enumerate(ranked[:5]))
    prompt = (
        "Eres un asesor de viajes experto. Con estas opciones de vuelo "
        "(ya puntuadas de 0 a 100 ponderando precio, duracion y escalas), "
        "recomienda cual elegir y explica por que en 3 o 4 frases claras. "
        "Menciona el equilibrio entre precio y comodidad.\n\n"
        f"{listado}\n\n"
        "Responde SOLO en JSON con las claves: recomendacion (texto) y "
        "mejor_opcion (el numero de la lista)."
    )
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = json.loads(resp.json()["choices"][0]["message"]["content"])
        return data.get("recomendacion")
    except Exception as e:
        print(f"[advisor_agent] Groq fallo ({e}); uso explicacion local.")
        return None


def _template_advice(ranked: list[dict]) -> str:
    """Explicacion local sin IA."""
    best = ranked[0]
    cheapest = min(ranked, key=lambda o: o["price"])
    name = best.get("airline_name", best["airline"])
    msg = (f"La mejor opcion global es {name} por su equilibrio entre "
           f"precio ({best['price']} {best['currency']}), "
           f"{'vuelo directo' if best['stops'] == 0 else str(best['stops']) + ' escala(s)'} "
           f"y duracion.")
    if cheapest is not best:
        msg += (f" Si solo te importa el precio, la mas barata es "
                f"{cheapest.get('airline_name', cheapest['airline'])} "
                f"a {cheapest['price']} {cheapest['currency']}, "
                f"pero tiene {cheapest['stops']} escala(s).")
    return msg


def advise(offers: list[dict]) -> dict:
    """Devuelve las ofertas puntuadas y una recomendacion escrita."""
    ranked = rank_offers(offers)
    if not ranked:
        return {"ranked": [], "advice": "No se encontraron vuelos."}
    advice = _groq_advice(ranked) if GROQ_API_KEY else None
    if advice is None:
        advice = _template_advice(ranked)
    return {"ranked": ranked, "advice": advice}

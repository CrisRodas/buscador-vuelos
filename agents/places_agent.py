"""Resolucion de lugares: convierte un nombre de ciudad a su codigo IATA.

Usa el catalogo cities.json de Travelpayouts (nombres en varios idiomas).
Para que sea robusto:
  - cachea el catalogo en disco (temp/cities.json),
  - lo pide comprimido con reintentos,
  - si todo falla, usa un diccionario local de ciudades comunes.
Si no encuentra la ciudad, devuelve None.
"""
import json
import time
import unicodedata

import requests

from config import TEMP_DIR

_API = "http://api.travelpayouts.com"
_CACHE_FILE = TEMP_DIR / "cities.json"

# Respaldo minimo: ciudades frecuentes de LATAM y Espana (nombre -> IATA)
_FALLBACK = {
    "bogota": "BOG", "medellin": "MDE", "cali": "CLO", "cartagena": "CTG",
    "barranquilla": "BAQ", "santa marta": "SMR", "pereira": "PEI",
    "bucaramanga": "BGA", "cucuta": "CUC", "san andres": "ADZ",
    "madrid": "MAD", "barcelona": "BCN", "sevilla": "SVQ", "valencia": "VLC",
    "malaga": "AGP", "bilbao": "BIO", "palma de mallorca": "PMI",
    "mexico": "MEX", "cancun": "CUN", "guadalajara": "GDL", "monterrey": "MTY",
    "lima": "LIM", "buenos aires": "BUE", "santiago": "SCL", "quito": "UIO",
    "guayaquil": "GYE", "panama": "PTY", "sao paulo": "SAO", "rio de janeiro": "RIO",
    "miami": "MIA", "nueva york": "NYC", "new york": "NYC", "orlando": "MCO",
    "los angeles": "LAX", "paris": "PAR", "londres": "LON", "london": "LON",
    "roma": "ROM", "lisboa": "LIS",
}

# Lista de (codigo, [nombres normalizados], etiqueta) para busqueda difusa
_index: list[tuple[str, list[str], str]] = []


def _norm(text: str) -> str:
    """Minusculas y sin acentos para comparar sin falsos negativos."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c)).strip()


def _download_catalog() -> list | None:
    """Descarga cities.json comprimido, con 3 reintentos. None si falla."""
    headers = {"Accept-Encoding": "gzip, deflate"}
    for intento in range(3):
        try:
            resp = requests.get(f"{_API}/data/cities.json",
                                headers=headers, timeout=40)
            resp.raise_for_status()
            data = resp.json()
            try:
                _CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
            except Exception:
                pass  # si no se puede cachear, seguimos igual
            return data
        except Exception as e:
            if intento < 2:
                time.sleep(1.5)
            else:
                print(f"[places_agent] No se pudo descargar el catalogo ({e}).")
    return None


def _load_cities() -> None:
    """Carga el catalogo: cache en disco -> descarga -> respaldo local."""
    if _index:
        return

    data = None
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            data = None
    if data is None:
        data = _download_catalog()

    if data:
        for c in data:
            code = c.get("code")
            if not code:
                continue
            tr = c.get("name_translations", {})
            names = [c.get("name", ""), tr.get("es", ""), tr.get("en", "")]
            norm = [_norm(n) for n in names if n]
            label = tr.get("es") or c.get("name") or code
            _index.append((code, norm, label))
    else:
        # Respaldo: usa el diccionario local
        print("[places_agent] Uso el listado local de ciudades comunes.")
        for name, code in _FALLBACK.items():
            _index.append((code, [_norm(name)], name.title()))


def resolve_city(query: str) -> tuple[str, str] | None:
    """Devuelve (codigo_iata, nombre) para la ciudad buscada, o None.

    Si ya es un codigo IATA de 3 letras, lo acepta tal cual.
    """
    q = query.strip()
    if len(q) == 3 and q.isalpha():
        return q.upper(), q.upper()

    nq = _norm(q)
    # Atajo: respaldo local primero (rapido y sin red)
    if nq in _FALLBACK:
        return _FALLBACK[nq], q.title()

    _load_cities()
    if not _index:
        return None

    # 1) exacta  2) prefijo  3) substring
    for code, names, label in _index:
        if nq in names:
            return code, label
    for code, names, label in _index:
        if any(n.startswith(nq) for n in names):
            return code, label
    for code, names, label in _index:
        if any(nq in n for n in names):
            return code, label
    return None

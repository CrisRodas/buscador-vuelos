"""Agente de destinos: recomienda paises/ciudades turisticas de
Sudamerica y Centroamerica y busca el vuelo mas barato a cada uno.

Mantiene una lista curada de destinos (codigo IATA, pais, atractivo).
Para cada uno consulta el precio mas economico desde el origen dado y
devuelve un top ordenado por precio.
"""
from agents.flight_agent import search_flights

# Tus ciudades de origen habituales (las mas cercanas). (nombre, IATA)
ORIGINS = [
    ("Bogota", "BOG"),
    ("Medellin", "MDE"),
    ("Pereira", "PEI"),
]

# Destinos turisticos curados. (ciudad, IATA, pais, region, atractivo)
DESTINATIONS = [
    # --- Sudamerica ---
    ("Cartagena", "CTG", "Colombia", "Sudamerica", "Ciudad amurallada y playas caribenas"),
    ("Cusco", "CUZ", "Peru", "Sudamerica", "Puerta a Machu Picchu"),
    ("Lima", "LIM", "Peru", "Sudamerica", "Gastronomia de clase mundial"),
    ("Rio de Janeiro", "GIG", "Brasil", "Sudamerica", "Playas, Cristo Redentor y carnaval"),
    ("Buenos Aires", "EZE", "Argentina", "Sudamerica", "Tango, cultura y vida nocturna"),
    ("Santiago", "SCL", "Chile", "Sudamerica", "Andes, vinedos y ciudad moderna"),
    ("Quito", "UIO", "Ecuador", "Sudamerica", "Centro colonial y mitad del mundo"),
    ("Montevideo", "MVD", "Uruguay", "Sudamerica", "Costa tranquila y Ciudad Vieja"),
    ("La Paz", "LPB", "Bolivia", "Sudamerica", "Altiplano y cercania al Salar de Uyuni"),
    ("Medellin", "MDE", "Colombia", "Sudamerica", "Clima primaveral e innovacion"),
    # --- Centroamerica ---
    ("Ciudad de Panama", "PTY", "Panama", "Centroamerica", "Canal, playas y hub de conexiones"),
    ("San Jose", "SJO", "Costa Rica", "Centroamerica", "Naturaleza, volcanes y ecoturismo"),
    ("Guatemala", "GUA", "Guatemala", "Centroamerica", "Antigua colonial y cultura maya"),
    ("San Salvador", "SAL", "El Salvador", "Centroamerica", "Ruta de las flores y surf"),
    ("Managua", "MGA", "Nicaragua", "Centroamerica", "Lagos, volcanes y Granada colonial"),
    ("San Pedro Sula", "SAP", "Honduras", "Centroamerica", "Acceso a islas de la Bahia"),
    ("Cancun", "CUN", "Mexico", "Centroamerica", "Playas del Caribe y zona arqueologica"),
    ("Punta Cana", "PUJ", "Rep. Dominicana", "Centroamerica", "Resorts y playas de arena blanca"),
]


def recommend_destinations(date: str, currency: str = "USD",
                           region: str | None = None, top: int = 8,
                           origins: list[tuple[str, str]] | None = None
                           ) -> list[dict]:
    """Top de destinos con el vuelo mas barato desde tus ciudades cercanas.

    Para cada destino compara todas las ciudades de origen y se queda con
    la mas economica, indicando desde cual sale.

    date: fecha o mes de salida (YYYY-MM-DD o YYYY-MM).
    currency: moneda de los precios.
    region: 'Sudamerica', 'Centroamerica' o None para ambas.
    top: cuantos destinos devolver.
    origins: lista (nombre, IATA); por defecto Bogota, Medellin y Pereira.
    """
    origins = origins or ORIGINS
    origin_codes = {code for _, code in origins}

    destinos = DESTINATIONS
    if region:
        destinos = [d for d in destinos if d[3].lower() == region.lower()]

    resultados = []
    for ciudad, iata, pais, reg, atractivo in destinos:
        if iata in origin_codes:
            continue  # no recomendar una de tus propias ciudades

        mejor = None  # (precio, oferta, nombre_origen, iata_origen)
        for origen_nombre, origen_iata in origins:
            offers = search_flights(origen_iata, iata, date, 1, currency)
            if not offers:
                continue
            barato = min(offers, key=lambda o: o["price"])
            if mejor is None or barato["price"] < mejor[0]:
                mejor = (barato["price"], barato, origen_nombre, origen_iata)

        if mejor is None:
            continue
        _, barato, origen_nombre, origen_iata = mejor
        resultados.append({
            "ciudad": ciudad,
            "iata": iata,
            "pais": pais,
            "region": reg,
            "atractivo": atractivo,
            "desde": origen_nombre,
            "desde_iata": origen_iata,
            "precio": barato["price"],
            "currency": barato["currency"],
            "aerolinea": barato.get("airline_name", barato["airline"]),
            "escalas": barato["stops"],
            "fecha": barato["departure"][:10] if len(barato["departure"]) >= 10 else "",
            "source": barato["source"],
        })

    resultados.sort(key=lambda r: r["precio"])
    return resultados[:top]

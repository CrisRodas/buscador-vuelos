# ✈️ Buscador de vuelos

Encuentra los vuelos nacionales e internacionales mas economicos y recibe una
recomendacion de cual elegir (precio vs. escalas vs. duracion). Incluye una
seccion para explorar destinos turisticos de Sur y Centroamerica desde Bogota,
Medellin o Pereira.

Datos de vuelos via la Data Access API gratuita de
[Travelpayouts](https://www.travelpayouts.com/) (precios de cache).

## Requisitos
- Python 3.11+
- Un token gratis de Travelpayouts

## Instalacion
```bash
pip install -r requirements.txt
cp .env.example .env   # y pega tu TRAVELPAYOUTS_TOKEN
```

Variables de entorno (ver `.env.example`):
- `TRAVELPAYOUTS_TOKEN`: token gratis de Travelpayouts (datos de vuelos).
- `GROQ_API_KEY` (opcional): recomendacion del asesor con IA. Sin ella, usa
  una explicacion local.

## Uso

### Interfaz web (recomendada, sirve en movil)
```bash
streamlit run app.py
```
Dos pestanas: "Buscar vuelo" (ruta puntual) y "Explorar destinos" (top
turistico mas barato desde tus ciudades cercanas).

### Linea de comandos
```bash
# Interactivo (te pregunta paso a paso)
python flights.py

# Con argumentos (acepta nombre de ciudad o codigo IATA)
python flights.py --origin Bogota --destination Madrid --date 2026-12
python flights.py --origin BOG --destination MDE --date 2026-12 --adults 2 --top 5
```

## Estructura
- `app.py` - interfaz web (Streamlit).
- `flights.py` - interfaz de linea de comandos.
- `config.py` - configuracion y lectura de claves.
- `agents/`
  - `flight_agent.py` - busca vuelos en Travelpayouts (con fallback a datos mock).
  - `advisor_agent.py` - puntua las opciones y recomienda cual elegir.
  - `places_agent.py` - convierte nombres de ciudad a codigos IATA.
  - `destinations_agent.py` - top de destinos turisticos de la region.

## Despliegue gratis (Streamlit Community Cloud)
1. Sube el repositorio a GitHub (el `.env` queda ignorado).
2. En [share.streamlit.io](https://share.streamlit.io) conecta tu GitHub y
   elige este repo, con `app.py` como archivo principal.
3. En "Secrets" agrega tu `TRAVELPAYOUTS_TOKEN`.
4. Obtendras una URL `https://<tu-app>.streamlit.app` para laptop y movil.

## Nota sobre los datos
Travelpayouts entrega precios de cache (de los ultimos dias), no en vivo al
segundo. Si una ruta no tiene datos, la app usa una estimacion de respaldo.
Verifica siempre el precio final en la aerolinea o agencia antes de reservar.

"""Buscador de vuelos - interfaz web (optimizada para movil).

Ejecutar en local:
    streamlit run app.py

Desde el movil en la misma WiFi: abre http://<IP-de-tu-laptop>:8501
Para acceso desde cualquier lugar, despliega en Streamlit Community Cloud.
"""
import datetime as dt

import streamlit as st

from agents.flight_agent import search_flights
from agents.advisor_agent import advise
from agents.places_agent import resolve_city
from agents.destinations_agent import recommend_destinations

st.set_page_config(page_title="Vuelos", page_icon="✈️", layout="centered")

st.title("✈️ Mis vuelos")

tab_buscar, tab_destinos = st.tabs(["🔎 Buscar vuelo", "🌎 Explorar destinos"])


def _label(o: dict) -> str:
    name = o.get("airline_name", o["airline"])
    stops = "Directo" if o["stops"] == 0 else f"{o['stops']} escala(s)"
    return f"{name} · {stops}"


# ----------------------- Pestana: Buscar vuelo ------------------------
with tab_buscar:
    st.caption("Busca una ruta puntual y deja que el asesor te ayude a elegir.")
    with st.form("busqueda"):
        origin_q = st.text_input("Origen", placeholder="Ej. Bogota o BOG")
        destination_q = st.text_input("Destino", placeholder="Ej. Madrid o MAD")

        col1, col2 = st.columns(2)
        with col1:
            depart = st.date_input("Fecha de salida", value=dt.date.today())
        with col2:
            use_return = st.checkbox("Ida y vuelta")
            ret = st.date_input("Fecha de regreso", value=dt.date.today(),
                                disabled=not use_return)

        col3, col4 = st.columns(2)
        with col3:
            adults = st.number_input("Pasajeros", min_value=1, max_value=9, value=1)
        with col4:
            currency = st.selectbox("Moneda", ["USD", "EUR", "COP", "MXN"], index=0)

        top = st.slider("Opciones a mostrar", 5, 30, 10)
        submitted = st.form_submit_button("Buscar vuelos", use_container_width=True)

    if submitted:
        o = resolve_city(origin_q) if origin_q else None
        d = resolve_city(destination_q) if destination_q else None

        if not origin_q or not destination_q:
            st.warning("Escribe el origen y el destino.")
        elif not o:
            st.error(f"No reconoci '{origin_q}'. Prueba otro nombre o un codigo IATA.")
        elif not d:
            st.error(f"No reconoci '{destination_q}'. Prueba otro nombre o un codigo IATA.")
        else:
            origin, origin_name = o
            destination, dest_name = d
            return_date = ret.strftime("%Y-%m-%d") if use_return else None

            st.info(f"Buscando: {origin_name} ({origin}) → {dest_name} ({destination})")
            with st.spinner("Consultando precios..."):
                offers = search_flights(origin, destination,
                                        depart.strftime("%Y-%m-%d"),
                                        int(adults), currency, return_date)
                result = advise(offers)

            ranked = result["ranked"]
            if not ranked:
                st.warning("No se encontraron vuelos para esa ruta y fecha. "
                           "Prueba con un mes (sin dia exacto) o otra fecha.")
            else:
                cheapest = min(ranked, key=lambda x: x["price"])
                st.success(f"**Recomendacion:** {result['advice']}")

                m1, m2 = st.columns(2)
                m1.metric("Mas barato",
                          f"{cheapest['price']:.0f} {cheapest['currency']}",
                          _label(cheapest))
                best = ranked[0]
                m2.metric("Mejor equilibrio",
                          f"{best['price']:.0f} {best['currency']}",
                          f"score {best['score']}")

                st.subheader(f"Top {min(top, len(ranked))} opciones")
                for item in ranked[:top]:
                    sale = item["departure"][:10] if len(item["departure"]) >= 10 else "s/f"
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        c1.markdown(f"**{item.get('airline_name', item['airline'])}**  \n"
                                    f"{_label(item)} · sale {sale}")
                        c2.markdown(f"### {item['price']:.0f}\n{item['currency']}")

                st.caption(f"{len(ranked)} opciones · fuente: {ranked[0]['source']}. "
                           "Precios de cache, pueden variar al reservar.")


# --------------------- Pestana: Explorar destinos --------------------
with tab_destinos:
    st.caption("Top de destinos turisticos en Sur y Centroamerica con el "
               "vuelo mas barato desde Bogota, Medellin o Pereira.")
    with st.form("destinos"):
        d_mes = st.date_input("Mes de viaje (aprox.)", value=dt.date.today(),
                              key="dest_date")
        c1, c2 = st.columns(2)
        with c1:
            d_region = st.selectbox("Region",
                                    ["Todas", "Sudamerica", "Centroamerica"])
        with c2:
            d_currency = st.selectbox("Moneda", ["USD", "EUR", "COP"],
                                      index=0, key="dest_curr")
        d_top = st.slider("Cuantos destinos", 3, 15, 8)
        d_submit = st.form_submit_button("Mostrar top destinos",
                                         use_container_width=True)

    if d_submit:
        region = None if d_region == "Todas" else d_region
        # Usamos el mes (YYYY-MM) para maximizar resultados en la cache
        mes = d_mes.strftime("%Y-%m")
        with st.spinner("Buscando los mejores precios a cada destino..."):
            tops = recommend_destinations(mes, d_currency, region, d_top)

        if not tops:
            st.warning("No se encontraron precios ahora mismo. Intenta mas tarde "
                       "o con otro mes.")
        else:
            barato = tops[0]
            st.success(f"🏆 Lo mas barato: **{barato['ciudad']}, {barato['pais']}** "
                       f"desde {barato['desde']} por "
                       f"{barato['precio']:.0f} {barato['currency']}.")

            for i, t in enumerate(tops, 1):
                stops = "Directo" if t["escalas"] == 0 else f"{t['escalas']} escala(s)"
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    c1.markdown(
                        f"**{i}. {t['ciudad']}, {t['pais']}**  \n"
                        f"_{t['atractivo']}_  \n"
                        f"Desde {t['desde']} · {t['aerolinea']} · {stops}")
                    c2.markdown(f"### {t['precio']:.0f}\n{t['currency']}")

            st.caption("Precios de cache (Travelpayouts); pueden variar al reservar. "
                       "Las rutas sin datos usan una estimacion.")

"""Configuracion central del buscador de vuelos."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).parent
TEMP_DIR = ROOT / "temp"
TEMP_DIR.mkdir(exist_ok=True)


def _get(key: str) -> str:
    """Lee una clave del entorno (.env local) o de los secrets de Streamlit.

    Permite usar el mismo codigo en local y desplegado en Streamlit Cloud.
    """
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st  # import diferido: no es dependencia dura
            val = st.secrets.get(key, "")
        except Exception:
            val = ""
    return val.strip()


# Travelpayouts (Data Access API, gratis) para busqueda de vuelos real
TRAVELPAYOUTS_TOKEN = _get("TRAVELPAYOUTS_TOKEN")

# Opcional: Groq para la recomendacion del asesor con IA
GROQ_API_KEY = _get("GROQ_API_KEY")
